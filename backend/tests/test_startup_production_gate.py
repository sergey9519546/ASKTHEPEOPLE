"""Startup refuses production gateway configurations.

`Config.validate()` collected seven refusals but had exactly one non-test call
site -- `services/simulation_preflight.py` -- so none of them stopped a process
from booting. `create_app` re-implemented two credential checks inline and
nothing else.

The consequence was concrete and measured on 2026-10-02: setting
`SOURCE_INGESTION_V1_ENABLED=true` in production switched the mutating source
routes live, created real canonical records, and nothing objected. Only a later
run preflight reported `required_env` as failed, by which point the write path
had already been exposed. The flag exists precisely to prevent that.

These tests boot the real application factory, because that is the seam that
was missing the check. Asserting on `Config.validate()` in isolation would pass
against the same code that does not enforce anything.

Scope note: `create_app` enforces the production *gateway* subset
(`validate_production_gates`), not all of `validate()`. `validate()` also
requires `LLM_API_KEY` and `ZEP_API_KEY`; making those boot requirements would
impose a new restriction on deployments that currently start without them, and
that is a decision for the release operator, not a bug fix.
"""

from __future__ import annotations

import pytest

# `Config` reads its environment in the class body, so every value is frozen at
# import time and patching os.environ afterwards has no effect on it. These
# tests therefore patch the class attributes, which is also the only way to
# exercise the real Config rather than a stand-in.

GATEWAY_KEYS = (
    "DEBUG",
    "SOURCE_INGESTION_V1_ENABLED",
    "DEV_ACTOR_CONTEXT_ENABLED",
    "SOURCE_INGESTION_V1_FORMATS",
)

# A production-shaped baseline: DEBUG off, auth required, valid credentials.
PRODUCTION = {
    "DEBUG": False,
    "SOURCE_INGESTION_V1_ENABLED": False,
    "DEV_ACTOR_CONTEXT_ENABLED": False,
    "SOURCE_INGESTION_V1_FORMATS": [],
}


@pytest.fixture()
def config(monkeypatch):
    """The real Config, forced into a known production configuration."""
    from app.config import Config

    for key, value in PRODUCTION.items():
        monkeypatch.setattr(Config, key, value)
    return Config


def boot(**overrides):
    from app import create_app

    return create_app()


class TestProductionGatewayRefusesUnsafeConfiguration:
    def test_source_ingestion_flag_refuses_to_boot(self, config, monkeypatch):
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_ENABLED", True)
        with pytest.raises(RuntimeError) as caught:
            boot()
        assert "SOURCE_INGESTION_V1_ENABLED" in str(caught.value)

    def test_dev_actor_context_refuses_to_boot(self, config, monkeypatch):
        monkeypatch.setattr(config, "DEV_ACTOR_CONTEXT_ENABLED", True)
        with pytest.raises(RuntimeError) as caught:
            boot()
        assert "DEV_ACTOR_CONTEXT_ENABLED" in str(caught.value)

    def test_unsupported_ingestion_format_refuses_to_boot(self, config, monkeypatch):
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_FORMATS", ["txt", "exe"])
        with pytest.raises(RuntimeError) as caught:
            boot()
        assert "exe" in str(caught.value)

    def test_every_refusal_is_listed_at_once(self, config, monkeypatch):
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_ENABLED", True)
        monkeypatch.setattr(config, "DEV_ACTOR_CONTEXT_ENABLED", True)
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_FORMATS", ["txt", "bogus"])
        with pytest.raises(RuntimeError) as caught:
            boot()
        message = str(caught.value)
        for expected in (
            "SOURCE_INGESTION_V1_ENABLED",
            "DEV_ACTOR_CONTEXT_ENABLED",
            "bogus",
        ):
            assert expected in message, f"{expected} missing from:\n{message}"


class TestSafeConfigurationStillBoots:
    def test_default_production_configuration_boots(self, config):
        assert boot() is not None

    def test_valid_format_allowlist_does_not_enable_ingestion(self, config, monkeypatch):
        # Widening eligibility must not switch ingestion on. The master flag
        # stays the gate.
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_FORMATS", ["txt", "pdf"])
        assert boot() is not None

    def test_debug_environment_is_not_subject_to_the_gateway(self, config, monkeypatch):
        # DEBUG is the canonical local-dev signal; a production rule must not
        # make local development impossible.
        monkeypatch.setattr(config, "DEBUG", True)
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_ENABLED", True)
        assert boot() is not None


class TestGatewayIsNotAToolingRequirement:
    def test_missing_provider_keys_do_not_block_boot(self, config, monkeypatch):
        # LLM_API_KEY and ZEP_API_KEY are capability checks, not safety gates.
        # Boot must not start demanding them.
        monkeypatch.setattr(config, "LLM_API_KEY", "")
        monkeypatch.setattr(config, "ZEP_API_KEY", "")
        assert boot() is not None


class TestValidatorShape:
    def test_gateway_is_empty_for_a_safe_production_config(self, config):
        assert config.validate_production_gates() == []

    def test_gateway_is_empty_when_debug(self, config, monkeypatch):
        monkeypatch.setattr(config, "DEBUG", True)
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_ENABLED", True)
        assert config.validate_production_gates() == []

    def test_every_gateway_refusal_is_also_in_the_full_validator(self, config, monkeypatch):
        # The two cannot be allowed to drift into disagreeing about what is
        # unsafe, or one of them becomes decorative.
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_ENABLED", True)
        monkeypatch.setattr(config, "DEV_ACTOR_CONTEXT_ENABLED", True)
        monkeypatch.setattr(config, "SOURCE_INGESTION_V1_FORMATS", ["txt", "bogus"])

        gateway = config.validate_production_gates()
        full = config.validate()
        assert gateway, "the gateway must report the unsafe configuration"
        for message in gateway:
            # The gateway reads "section 5"; validate() uses the section sign.
            normalized = message.replace("section 5", "§5")
            assert any(normalized in candidate for candidate in full), (
                f"gateway refusal absent from validate(): {message}"
            )
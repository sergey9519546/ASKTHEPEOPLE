"""
Tests for the Phase 1/2/3 hardening configuration keys.

Validates the *spec-intended* behavior of `backend/app/config.py`:
  - REPORT_GENERATION_TIMEOUT is an int, defaults to 900, env-overridable
  - RATELIMIT_DEFAULT / RATELIMIT_LLM_HEAVY / RATELIMIT_LLM_MEDIUM exist

These guard against regressions in the hardening config. If the keys are not
yet present on the branch under test, the asserts below surface that directly.
"""

import importlib
import os

import pytest

from app import config as config_module
from app import create_app
from app.config import Config, _trusted_hosts


def test_report_generation_timeout_is_int_and_defaults_to_900():
    """REPORT_GENERATION_TIMEOUT must be an int whose default is 900 (15 min)."""
    assert hasattr(Config, "REPORT_GENERATION_TIMEOUT"), (
        "Config.REPORT_GENERATION_TIMEOUT is missing (Phase 1 hardening not merged)"
    )
    value = Config.REPORT_GENERATION_TIMEOUT
    assert isinstance(value, int), (
        f"REPORT_GENERATION_TIMEOUT must be int, got {type(value).__name__}: {value!r}"
    )
    assert not isinstance(value, bool), "REPORT_GENERATION_TIMEOUT must not be a bool"
    assert value == 900, f"expected default 900, got {value}"


def test_report_generation_timeout_env_overridable(monkeypatch):
    """Setting REPORT_GENERATION_TIMEOUT in the env must change the resolved value."""
    monkeypatch.setenv("REPORT_GENERATION_TIMEOUT", "123")
    try:
        reloaded = importlib.reload(config_module)
        try:
            value = reloaded.Config.REPORT_GENERATION_TIMEOUT
            assert isinstance(value, int)
            assert value == 123, f"env override not honored, got {value!r}"
        finally:
            # Restore the module so other tests see the original (env-less) default.
            importlib.reload(config_module)
    finally:
        monkeypatch.delenv("REPORT_GENERATION_TIMEOUT", raising=False)


@pytest.mark.parametrize(
    "attr",
    ["RATELIMIT_DEFAULT", "RATELIMIT_LLM_HEAVY", "RATELIMIT_LLM_MEDIUM"],
)
def test_ratelimit_keys_exist_and_are_strings(attr):
    """The three Phase 2 rate-limit config keys must exist and be string limits."""
    assert hasattr(Config, attr), (
        f"Config.{attr} is missing (Phase 2 rate-limiting not merged)"
    )
    value = getattr(Config, attr)
    assert isinstance(value, str) and value.strip(), (
        f"Config.{attr} must be a non-empty string, got {value!r}"
    )


def test_production_auth_requirement_is_validated(monkeypatch):
    monkeypatch.setattr(Config, "REQUIRE_APP_AUTH", True)
    monkeypatch.setattr(Config, "APP_TOKEN", None)

    assert any("APP_TOKEN" in error for error in Config.validate())

    monkeypatch.setattr(
        Config,
        "APP_TOKEN",
        "private-access-key-7b9f3d2c8a6e4f10",
    )
    assert not any("APP_TOKEN" in error for error in Config.validate())

    monkeypatch.setattr(Config, "APP_TOKEN", "weak")
    assert any("APP_TOKEN" in error for error in Config.validate())


@pytest.mark.parametrize(
    "public_build_placeholder",
    ("build-validation-model-key", "build-validation-zep-key"),
)
def test_public_build_placeholders_cannot_be_private_app_credentials(
    monkeypatch,
    public_build_placeholder,
):
    monkeypatch.setattr(Config, "DEBUG", False)
    monkeypatch.setattr(Config, "REQUIRE_APP_AUTH", True)
    monkeypatch.setattr(Config, "SECRET_KEY", public_build_placeholder)
    monkeypatch.setattr(Config, "APP_TOKEN", public_build_placeholder)

    errors = Config.validate()

    assert any("SECRET_KEY" in error for error in errors)
    assert any("APP_TOKEN" in error for error in errors)


def test_application_factory_refuses_required_auth_without_token():
    class MissingRequiredAuthConfig(Config):
        REQUIRE_APP_AUTH = True
        APP_TOKEN = None

    with pytest.raises(RuntimeError, match="APP_TOKEN"):
        create_app(MissingRequiredAuthConfig)


def test_application_factory_refuses_weak_production_credentials():
    class WeakCredentialConfig(Config):
        DEBUG = False
        REQUIRE_APP_AUTH = True
        SECRET_KEY = "strong-secret-key-7b9f3d2c8a6e4f10"
        APP_TOKEN = "weak"
        CORS_ORIGINS = "https://app.example.test"
        TRUSTED_HOSTS = ["app.example.test", "localhost"]

    with pytest.raises(RuntimeError, match="APP_TOKEN"):
        create_app(WeakCredentialConfig)


def test_railway_healthcheck_host_is_exactly_allowed(monkeypatch):
    """Railway readiness must work without weakening the normal host policy."""
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "test-railway-environment")
    monkeypatch.setenv("TRUSTED_HOSTS", "app.example.test")

    trusted_hosts = _trusted_hosts(debug=False)
    assert "healthcheck.railway.app" in trusted_hosts
    assert "*.railway.app" not in trusted_hosts

    class RailwayHealthConfig(Config):
        TESTING = True
        DEBUG = False
        SECRET_KEY = "strong-secret-key-7b9f3d2c8a6e4f10"
        REQUIRE_APP_AUTH = True
        APP_TOKEN = "private-access-key-7b9f3d2c8a6e4f10"
        CORS_ORIGINS = "https://app.example.test"
        TRUSTED_HOSTS = trusted_hosts
        UPLOAD_FOLDER = "/tmp/test-uploads"  # Health check needs writable folder

    client = create_app(RailwayHealthConfig).test_client()

    assert (
        client.get("/health", headers={"Host": "healthcheck.railway.app"}).status_code
        == 200
    )
    assert (
        client.get("/health", headers={"Host": "untrusted.example.test"}).status_code
        == 400
    )

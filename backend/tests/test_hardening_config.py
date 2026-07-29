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
from app.config import Config


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

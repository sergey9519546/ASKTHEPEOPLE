"""
Force backend test isolation by clearing imported env paths.

Some local execution contexts inherit PYTHONPATH from parent shells /
IDE settings, which can bypass this project's venv when pytest imports
backend modules from the project root. This file unsets PYTHONPATH as
early as possible in test collection so imports resolve via the active
Python's sys.path/venv only.

It also keeps `app.config.Config` a stable object across the session; see
_restore_config_class_identity.
"""

import os
import sys

import pytest


def _clear_pythonpath() -> None:
    keys = [key for key in os.environ if key.upper() == "PYTHONPATH"]
    for key in keys:
        del os.environ[key]

    # A defensive fallback for environments that still inject it downstream.
    try:
        sys.path = [part for part in sys.path if part not in (
            r"C:\Users\serge\AppData\Local\Temp\hermes_sandbox_hmt84lxd",
            r"C:\Users\serge\AppData\Local\hermes\hermes-agent",
            r"C:\Users\serge\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages",
        )]
    except Exception:
        pass


_clear_pythonpath()


@pytest.fixture(autouse=True)
def _restore_config_class_identity():
    """Keep `app.config.Config` the same object every test module imported.

    Several tests call `importlib.reload(app.config)` to re-exercise its
    import-time env reads (test_secret_key, test_hardening_config). reload()
    re-runs the module body in the existing module namespace, so the `class
    Config` statement binds a NEW class object — while every module that did
    `from app.config import Config` at collection time still holds the old one.

    From that point on the two diverge, and the divergence is silent:
    `monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", tmp_path)` patches
    the stale class, while production code (which imports Config inside
    functions) reads the fresh one. Storage isolation stops working and tests
    write into the real backend/uploads/simulations. Restoring the identity
    after every test keeps the reload-based tests self-contained.
    """
    import app.config as config_module

    original = config_module.Config
    yield
    if config_module.Config is not original:
        config_module.Config = original

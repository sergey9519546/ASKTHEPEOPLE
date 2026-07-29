"""
Tests for the SECRET_KEY fail-fast logic in `backend/app/config.py`.

`config.py` resolves SECRET_KEY at *import* time:
  - SECRET_KEY env var set            -> use it
  - else FLASK_DEBUG=true             -> random per-restart (dev)
  - else                              -> raise RuntimeError (production guard)

Because that logic runs on import, these tests reload the module under a
controlled environment via `importlib.reload` + `monkeypatch.{setenv,delenv}`.
The repo's `.env` carries a real SECRET_KEY, which would short-circuit the
fail-fast branch; the affected tests therefore neutralize `load_dotenv` before
reloading so only `os.environ` is consulted. We patch `dotenv.load_dotenv`
(the package-level function) because `importlib.reload` re-executes config's
`from dotenv import load_dotenv`, which re-binds the name from `dotenv` — so
patching `app.config.load_dotenv` directly is overwritten on each reload.

An autouse fixture reloads `config` against the real `.env` after every test
so the module is never left mutated for downstream tests.
"""

import importlib

import dotenv
import pytest

from app import config as config_module


def _reload_config():
    """Reload app.config so its import-time env reads pick up current state."""
    return importlib.reload(config_module)


@pytest.fixture(autouse=True)
def _restore_config_after_each():
    """Ensure app.config is reloaded from the real .env after each test.

    Reloading config in a test mutates the shared module; without this
    teardown, subsequent tests (and other modules that captured `Config`
    attributes) could see a poisoned state (random SECRET_KEY, missing
    APP_TOKEN, or even a module that raised at import).
    """
    yield
    # Reload from disk/env as it would be at fresh import. monkeypatch has
    # already reverted env + attribute patches by teardown time, so this
    # restores the production-intended Config.
    importlib.reload(config_module)


def test_secret_key_from_env(monkeypatch):
    """An explicit SECRET_KEY in the environment is used verbatim.

    load_dotenv is neutralized so the repo .env's SECRET_KEY cannot override
    the monkeypatched value (load_dotenv is called with override=True).
    """
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setenv('SECRET_KEY', 'my-test-secret-1234567890')
    cfg = _reload_config()
    assert cfg.Config.SECRET_KEY == 'my-test-secret-1234567890'


def test_secret_key_dev_random_when_debug(monkeypatch):
    """With FLASK_DEBUG=true and no SECRET_KEY, a random key is assigned.

    We neutralize load_dotenv so the repo .env's SECRET_KEY cannot leak in
    and short-circuit the dev-random branch.
    """
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('FLASK_DEBUG', 'true')
    cfg = _reload_config()
    assert cfg.Config.SECRET_KEY                      # a value was assigned
    assert len(cfg.Config.SECRET_KEY) >= 32           # os.urandom(24).hex() -> 48 hex chars
    assert cfg.Config.SECRET_KEY != 'change-me-to-a-random-secret'


def test_secret_key_fails_fast_in_production(monkeypatch):
    """Without SECRET_KEY or FLASK_DEBUG, importing config must raise RuntimeError.

    This is the production guard. The repo .env contains a SECRET_KEY, so we
    patch `dotenv.load_dotenv` to a no-op BEFORE reloading — otherwise
    load_dotenv would populate os.environ from .env and the guard would never
    fire. We patch on the `dotenv` package (not `app.config.load_dotenv`)
    because `importlib.reload` re-executes `from dotenv import load_dotenv`,
    which re-binds the name in app.config from `dotenv` — so the package-level
    reference is the only stable target.
    """
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('FLASK_DEBUG', raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _reload_config()


def test_app_token_optional_and_passthrough(monkeypatch):
    """APP_TOKEN is None when unset (open API) and reflected when set."""
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setenv('SECRET_KEY', 'stable-secret-for-this-test')
    monkeypatch.delenv('APP_TOKEN', raising=False)
    cfg = _reload_config()
    assert cfg.Config.APP_TOKEN is None

    monkeypatch.setenv('APP_TOKEN', 'some-bearer-token')
    cfg = _reload_config()
    assert cfg.Config.APP_TOKEN == 'some-bearer-token'

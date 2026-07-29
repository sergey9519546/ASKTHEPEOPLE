import json
import os

import pytest

from app import create_app
from app.config import Config


@pytest.fixture
def app(tmp_path):
    app = create_app()
    app.config.update({
        "TESTING": True,
        "DEBUG": True,
        "ALLOW_RUNTIME_SETTINGS": False,
        "RUNTIME_SETTINGS_ENV_PATH": str(tmp_path / ".env"),
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_get_settings_never_returns_secret_fragments(client):
    original = Config.LLM_API_KEY
    Config.LLM_API_KEY = "sk-test-prefix-and-secret-suffix"
    try:
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["LLM_API_KEY"] == ""
        assert data["LLM_API_KEY_CONFIGURED"] is True
        assert "prefix" not in response.get_data(as_text=True)
        assert "suffix" not in response.get_data(as_text=True)
        assert data["runtime_settings_enabled"] is False
        assert data["LLM_BASE_URL"] == ""
        assert data["LLM_MODEL_NAME"] == ""
        assert data["allowed_llm_base_urls"] == []
        assert data["allow_private_llm_endpoints"] is False
    finally:
        Config.LLM_API_KEY = original


def test_runtime_settings_mutation_and_test_are_disabled_by_default(client):
    update = client.post("/api/settings", json={"LLM_API_KEY": "new-key"})
    connection_test = client.post("/api/settings/test", json={
        "LLM_API_KEY": "new-key",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_MODEL_NAME": "gpt-4o-mini",
    })
    assert update.status_code == 403
    assert connection_test.status_code == 403
    assert update.get_json()["error"] == "runtime_settings_disabled"


def test_update_settings_when_explicitly_enabled(app, client, monkeypatch):
    app.config.update({
        "ALLOW_RUNTIME_SETTINGS": True,
        "ALLOW_PRIVATE_LLM_ENDPOINTS": True,
        "LLM_ALLOWED_BASE_URLS": (
            "http://127.0.0.1:11434/v1,http://127.0.0.1:1234/v1"
        ),
    })
    originals = {
        "LLM_API_KEY": Config.LLM_API_KEY,
        "LLM_BASE_URL": Config.LLM_BASE_URL,
        "LLM_MODEL_NAME": Config.LLM_MODEL_NAME,
        "ZEP_API_KEY": Config.ZEP_API_KEY,
    }
    env_keys = [
        "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_NAME", "ZEP_API_KEY",
        "BRAVE_SEARCH_API_KEY", "LLM_BOOST_API_KEY",
        "LLM_BOOST_BASE_URL", "LLM_BOOST_MODEL_NAME",
    ]
    env_originals = {key: os.environ.get(key) for key in env_keys}

    try:
        payload = {
            "LLM_API_KEY": "test-primary-key",
            "LLM_BASE_URL": "http://127.0.0.1:11434/v1",
            "LLM_MODEL_NAME": "local-primary",
            "ZEP_API_KEY": "test-zep-key",
            "BRAVE_SEARCH_API_KEY": "test-brave-key",
            "LLM_BOOST_API_KEY": "test-boost-key",
            "LLM_BOOST_BASE_URL": "http://127.0.0.1:1234/v1",
            "LLM_BOOST_MODEL_NAME": "local-boost",
        }
        response = client.post("/api/settings", json=payload)
        assert response.status_code == 200
        response_data = response.get_json()["data"]
        assert response_data["LLM_API_KEY"] == ""
        assert response_data["LLM_API_KEY_CONFIGURED"] is True
        assert response_data["allowed_llm_base_urls"] == [
            "http://127.0.0.1:11434/v1",
            "http://127.0.0.1:1234/v1",
        ]
        assert response_data["allow_private_llm_endpoints"] is True
        assert Config.LLM_BASE_URL == "http://127.0.0.1:11434/v1"

        persisted = open(
            app.config["RUNTIME_SETTINGS_ENV_PATH"], encoding="utf-8"
        ).read()
        assert "LLM_API_KEY=test-primary-key" in persisted
        assert "LLM_BOOST_API_KEY=test-boost-key" in persisted
    finally:
        Config.LLM_API_KEY = originals["LLM_API_KEY"]
        Config.LLM_BASE_URL = originals["LLM_BASE_URL"]
        Config.LLM_MODEL_NAME = originals["LLM_MODEL_NAME"]
        Config.ZEP_API_KEY = originals["ZEP_API_KEY"]
        for key, value in env_originals.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)


def test_base_url_change_cannot_reuse_retained_server_key(app, client):
    app.config.update({
        "ALLOW_RUNTIME_SETTINGS": True,
        "ALLOW_PRIVATE_LLM_ENDPOINTS": True,
        "LLM_ALLOWED_BASE_URLS": "http://127.0.0.1:11434/v1",
    })
    response = client.post("/api/settings", json={
        "LLM_BASE_URL": "http://127.0.0.1:11434/v1",
        "LLM_MODEL_NAME": "attacker-model",
    })
    assert response.status_code == 400
    assert "new API key is required" in response.get_json()["error"]


def test_arbitrary_or_private_base_url_is_rejected(app, client):
    app.config.update({
        "ALLOW_RUNTIME_SETTINGS": True,
        "ALLOW_PRIVATE_LLM_ENDPOINTS": False,
        "LLM_ALLOWED_BASE_URLS": "https://api.openai.com/v1",
    })
    response = client.post("/api/settings", json={
        "LLM_API_KEY": "caller-key",
        "LLM_BASE_URL": "http://169.254.169.254/latest/meta-data",
    })
    assert response.status_code == 400
    assert "allowlist" in response.get_json()["error"]


def test_connection_test_validates_inputs_after_explicit_enable(app, client):
    app.config["ALLOW_RUNTIME_SETTINGS"] = True
    response = client.post("/api/settings/test", json={
        "LLM_BASE_URL": "https://api.openai.com/v1",
    })
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_production_runtime_settings_require_app_token(app, client):
    app.config.update({
        "DEBUG": False,
        "APP_TOKEN": None,
        "ALLOW_RUNTIME_SETTINGS": True,
    })
    response = client.post("/api/settings", json={"LLM_API_KEY": "new-key"})
    assert response.status_code == 403

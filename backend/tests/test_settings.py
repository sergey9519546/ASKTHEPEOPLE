import json
import os
from types import SimpleNamespace

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
        "LLM_API_KEY": "caller-key",
        "LLM_BASE_URL": "https://api.openai.com/v1",
    })
    assert response.status_code == 400
    assert "Model Name is required" in response.get_json()["error"]


def test_zep_connection_test_validates_key(app, client, monkeypatch):
    app.config["ALLOW_RUNTIME_SETTINGS"] = True
    response = client.post("/api/settings/test", json={
        "target": "zep",
        "ZEP_API_KEY": "",
    })
    assert response.status_code == 400
    assert "ZEP_API_KEY is required" in response.get_json()["error"]


def test_production_runtime_settings_require_app_token(app, client):
    app.config["ALLOW_RUNTIME_SETTINGS"] = True
    app.config["REQUIRE_APP_AUTH"] = True
    app.config["APP_TOKEN"] = "valid-token-value-12345678901234567890"

    response = client.get("/api/settings")
    assert response.status_code == 401


@pytest.mark.parametrize("url", [
    "https://gateway.example/v1/messages",
    " https://gateway.example/v1/messages/ ",
    "https://api.anthropic.com",
    "https://api.anthropic.com/v1/messages",
    "https://API.ANTHROPIC.COM:443/v1/",
])
@pytest.mark.parametrize("url_key", ["LLM_BASE_URL", "LLM_BOOST_BASE_URL"])
def test_settings_update_rejects_native_transport_before_normalization(
    app, client, monkeypatch, url, url_key
):
    from app.api import settings

    app.config.update({
        "ALLOW_RUNTIME_SETTINGS": True,
        "LLM_ALLOWED_BASE_URLS": url.strip(),
    })
    key_name = "LLM_BOOST_API_KEY" if url_key == "LLM_BOOST_BASE_URL" else "LLM_API_KEY"
    original_url = Config.LLM_BASE_URL
    original_key = Config.LLM_API_KEY
    original_boost_url = os.environ.get("LLM_BOOST_BASE_URL")
    original_boost_key = os.environ.get("LLM_BOOST_API_KEY")
    monkeypatch.setattr(settings, "_persist_settings", lambda values: pytest.fail("Native settings must not persist"))
    monkeypatch.setattr(settings.socket, "getaddrinfo", lambda *args, **kwargs: pytest.fail("Native transport must reject before DNS"))

    response = client.post("/api/settings", json={url_key: url, key_name: "caller-only-fixture-key"})

    assert response.status_code == 400
    assert "native Anthropic Messages transport is unsupported" in response.get_json()["error"]
    assert Config.LLM_BASE_URL == original_url
    assert Config.LLM_API_KEY == original_key
    assert os.environ.get("LLM_BOOST_BASE_URL") == original_boost_url
    assert os.environ.get("LLM_BOOST_API_KEY") == original_boost_key
    assert not os.path.exists(app.config["RUNTIME_SETTINGS_ENV_PATH"])


@pytest.mark.parametrize("url", [
    "https://gateway.example/v1/messages",
    "https://api.anthropic.com/v1/",
])
def test_settings_connection_rejects_native_transport_before_client(
    app, client, monkeypatch, url
):
    from app.api import settings

    app.config.update({"ALLOW_RUNTIME_SETTINGS": True, "LLM_ALLOWED_BASE_URLS": url})
    monkeypatch.setattr(settings, "LLMClient", lambda **kwargs: pytest.fail("Native transport must not construct OpenAI client"))
    monkeypatch.setattr(settings.socket, "getaddrinfo", lambda *args, **kwargs: pytest.fail("Native transport must reject before DNS"))

    response = client.post("/api/settings/test", json={
        "LLM_API_KEY": "caller-only-fixture-key",
        "LLM_BASE_URL": url,
        "LLM_MODEL_NAME": "claude-offline-fixture",
    })

    assert response.status_code == 400
    assert "native Anthropic Messages transport is unsupported" in response.get_json()["error"]


@pytest.mark.parametrize("url", [
    "https://api.openai.com/v1/chat/completions/",
    "https://anthropic-gateway.example/v1/chat/completions/",
])
def test_settings_connection_accepts_canonical_chat_completion_url(
    app, client, monkeypatch, url
):
    from app.api import settings

    canonical = url.removesuffix("/chat/completions/")
    app.config.update({"ALLOW_RUNTIME_SETTINGS": True, "LLM_ALLOWED_BASE_URLS": canonical})
    monkeypatch.setattr(settings.socket, "getaddrinfo", lambda *args, **kwargs: [
        (2, 1, 6, "", ("8.8.8.8", 443)),
    ])
    captured = {}

    def make_client(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(chat=lambda **kwargs: "Connected")

    monkeypatch.setattr(settings, "LLMClient", make_client)
    response = client.post("/api/settings/test", json={
        "LLM_API_KEY": "caller-only-fixture-key",
        "LLM_BASE_URL": url,
        "LLM_MODEL_NAME": "claude-on-chat-gateway",
    })

    assert response.status_code == 200
    assert captured["base_url"] == canonical
    assert captured["model"] == "claude-on-chat-gateway"
    assert captured["api_key"] == "caller-only-fixture-key"


@pytest.mark.parametrize("boost", [False, True])
def test_saved_chat_endpoint_reaches_factory_without_changing_model(
    app, client, monkeypatch, boost
):
    from app.api import settings
    from app.services.camel_model_factory import resolve_model_config

    prefix = "LLM_BOOST" if boost else "LLM"
    canonical = "https://anthropic-gateway.example/v1"
    app.config.update({"ALLOW_RUNTIME_SETTINGS": True, "LLM_ALLOWED_BASE_URLS": canonical})
    monkeypatch.setattr(settings.socket, "getaddrinfo", lambda *args, **kwargs: [
        (2, 1, 6, "", ("8.8.8.8", 443)),
    ])
    # Register all mutations for teardown before the route changes process state.
    for suffix in ("API_KEY", "BASE_URL", "MODEL_NAME"):
        monkeypatch.setenv(f"{prefix}_{suffix}", (
            "https://previous.example/v1" if suffix == "BASE_URL" else "old-offline-fixture"
        ))
        if not boost:
            monkeypatch.setattr(Config, f"LLM_{suffix}", (
                "https://previous.example/v1" if suffix == "BASE_URL" else "old-offline-fixture"
            ))
    for suffix in ("API_KEY", "BASE_URL", "MODEL_NAME"):
        monkeypatch.delenv(f"LLM_ACTOR_{suffix}", raising=False)

    response = client.post("/api/settings", json={
        f"{prefix}_API_KEY": "caller-only-fixture-key",
        f"{prefix}_BASE_URL": canonical + "/chat/completions/",
        f"{prefix}_MODEL_NAME": "claude-on-chat-gateway",
    })

    assert response.status_code == 200
    assert response.get_json()["data"][f"{prefix}_BASE_URL"] == canonical
    resolved = resolve_model_config("actor", prefer_boost=boost)
    assert resolved.base_url == canonical
    assert resolved.provider_mode == "openai_compatible"
    assert resolved.model_name == "claude-on-chat-gateway"
    assert os.path.isfile(app.config["RUNTIME_SETTINGS_ENV_PATH"])


@pytest.mark.parametrize("url", [
    "https://[invalid/v1",
    "https://gateway.example:invalid/v1",
    "gateway.example/v1",
])
def test_transport_classification_preserves_malformed_url_rejection(
    app, client, monkeypatch, url
):
    from app.api import settings

    app.config["ALLOW_RUNTIME_SETTINGS"] = True
    monkeypatch.setattr(settings.socket, "getaddrinfo", lambda *args, **kwargs: pytest.fail("Invalid URL must reject before DNS"))
    response = client.post("/api/settings/test", json={
        "LLM_API_KEY": "caller-only-fixture-key",
        "LLM_BASE_URL": url,
        "LLM_MODEL_NAME": "offline-fixture",
    })

    assert response.status_code == 400
    assert response.get_json()["success"] is False

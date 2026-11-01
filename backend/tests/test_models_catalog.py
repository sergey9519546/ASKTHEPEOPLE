"""Offline HTTP contracts for the privileged model catalog."""

import socket
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import create_app
from app.config import Config


@pytest.fixture
def catalog(monkeypatch):
    monkeypatch.setattr(Config, "LLM_BASE_URL", "https://catalog.example/v1")
    monkeypatch.setattr(Config, "LLM_API_KEY", "catalog-primary-test-key")
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "catalog-configured-model")
    monkeypatch.setattr(Config, "APP_TOKEN", None)
    monkeypatch.setattr(Config, "REQUIRE_APP_AUTH", False)
    monkeypatch.setattr(Config, "ALLOW_RUNTIME_SETTINGS", False)
    for key in ("LLM_BOOST_BASE_URL", "LLM_BOOST_API_KEY", "LLM_BOOST_MODEL_NAME"):
        monkeypatch.delenv(key, raising=False)

    dns = Mock(return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
    ])
    monkeypatch.setattr(socket, "getaddrinfo", dns)
    provider = Mock()
    provider.models.list.return_value = SimpleNamespace(data=[
        SimpleNamespace(id="catalog-model", owned_by="catalog-owner"),
    ])
    provider.__enter__ = Mock(return_value=provider)
    provider.__exit__ = Mock(return_value=False)
    factory = Mock(return_value=provider)
    monkeypatch.setattr("openai.OpenAI", factory)

    app = create_app()
    app.config.update(
        TESTING=True,
        DEBUG=True,
        ALLOW_PRIVATE_LLM_ENDPOINTS=False,
        LLM_ALLOWED_BASE_URLS="https://catalog.example/v1",
    )
    return SimpleNamespace(
        app=app, client=app.test_client(), dns=dns, factory=factory, provider=provider,
    )


def test_catalog_is_disabled_by_default_without_provider_or_dns_call(catalog):
    response = catalog.client.get("/api/models")

    assert response.status_code == 403
    assert response.get_json() == {"success": False, "error": "runtime_settings_disabled"}
    catalog.factory.assert_not_called()
    catalog.dns.assert_not_called()


@pytest.mark.parametrize("base_url,address", [
    ("https://unlisted.example/v1", "93.184.216.34"),
    ("http://catalog.example/v1", "93.184.216.34"),
    ("https://catalog.example/v1", "127.0.0.1"),
    ("https://catalog.example/v1", "169.254.169.254"),
    ("https://catalog.example/v1", "::1"),
    ("https://user:password@catalog.example/v1", "93.184.216.34"),
    ("https://catalog.example/v1?token=secret", "93.184.216.34"),
    ("https://catalog.example/v1#secret", "93.184.216.34"),
])
def test_enabled_catalog_rejects_unsafe_endpoints(catalog, monkeypatch, base_url, address):
    catalog.app.config.update(ALLOW_RUNTIME_SETTINGS=True, LLM_ALLOWED_BASE_URLS=base_url)
    if "unlisted" in base_url:
        catalog.app.config["LLM_ALLOWED_BASE_URLS"] = "https://catalog.example/v1"
    monkeypatch.setattr(Config, "LLM_BASE_URL", base_url)
    catalog.dns.return_value = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)),
    ]

    response = catalog.client.get("/api/models")

    assert response.status_code == 400
    assert response.get_json()["error"] == "model_catalog_endpoint_rejected"
    assert base_url not in response.get_data(as_text=True)
    catalog.factory.assert_not_called()


def test_production_catalog_requires_control_plane_token(catalog):
    catalog.app.config.update(ALLOW_RUNTIME_SETTINGS=True, DEBUG=False, APP_TOKEN=None)
    response = catalog.client.get("/api/models")
    assert response.status_code == 403
    catalog.factory.assert_not_called()
    catalog.dns.assert_not_called()


@pytest.mark.parametrize("base_url", [
    "https://api.anthropic.com/v1",
    "https://catalog.example/v1/messages",
    "https://catalog.example/v1/messages/",
])
def test_native_transport_is_explicitly_unsupported(catalog, monkeypatch, base_url):
    catalog.app.config.update(ALLOW_RUNTIME_SETTINGS=True, LLM_ALLOWED_BASE_URLS=base_url)
    monkeypatch.setattr(Config, "LLM_BASE_URL", base_url)
    response = catalog.client.get("/api/models")
    assert response.status_code == 400
    assert "native Anthropic Messages transport is unsupported" in response.get_json()["message"]
    assert "models" not in response.get_json().get("data", {})
    catalog.factory.assert_not_called()
    catalog.dns.assert_not_called()


@pytest.mark.parametrize("primary_url,primary_key,expected_status,expected_url,expected_key", [
    ("https://catalog.example/v1", "primary-key", 200, "https://catalog.example/v1", "primary-key"),
    ("https://catalog.example/v1", "", 503, None, None),
    ("", "primary-key", 400, None, None),
    ("", "", 200, "https://boost.example/v1", "boost-key"),
])
def test_catalog_keeps_endpoint_and_key_from_same_configuration(
    catalog, monkeypatch, primary_url, primary_key, expected_status, expected_url, expected_key,
):
    catalog.app.config.update(
        ALLOW_RUNTIME_SETTINGS=True,
        LLM_ALLOWED_BASE_URLS="https://catalog.example/v1,https://boost.example/v1",
    )
    monkeypatch.setattr(Config, "LLM_BASE_URL", primary_url)
    monkeypatch.setattr(Config, "LLM_API_KEY", primary_key)
    monkeypatch.setenv("LLM_BOOST_BASE_URL", "https://boost.example/v1")
    monkeypatch.setenv("LLM_BOOST_API_KEY", "boost-key")
    response = catalog.client.get("/api/models")
    assert response.status_code == expected_status
    if expected_status == 200:
        catalog.factory.assert_called_once_with(api_key=expected_key, base_url=expected_url, timeout=15.0)
        assert response.get_json()["data"]["models"][0]["id"] == "catalog-model"
    else:
        catalog.factory.assert_not_called()
    body = response.get_data(as_text=True)
    for hidden in ("primary-key", "boost-key", "catalog.example", "boost.example", "catalog-configured-model"):
        assert hidden not in body


@pytest.mark.parametrize("failure_stage", ["construct", "list"])
def test_provider_errors_do_not_expose_credentials_or_endpoint_metadata(catalog, failure_stage):
    catalog.app.config["ALLOW_RUNTIME_SETTINGS"] = True
    failure = RuntimeError("catalog-primary-test-key https://catalog.example/v1 catalog-configured-model")
    if failure_stage == "construct":
        catalog.factory.side_effect = failure
    else:
        catalog.provider.models.list.side_effect = failure
    response = catalog.client.get("/api/models")
    assert response.status_code == 502
    assert response.get_json() == {"success": False, "error": "model_catalog_unavailable"}


def test_explicitly_allowed_private_endpoint_uses_matching_key(catalog, monkeypatch):
    catalog.app.config.update(
        ALLOW_RUNTIME_SETTINGS=True, ALLOW_PRIVATE_LLM_ENDPOINTS=True,
        LLM_ALLOWED_BASE_URLS="http://127.0.0.1:11434/v1",
    )
    monkeypatch.setattr(Config, "LLM_BASE_URL", "http://127.0.0.1:11434/v1/chat/completions")
    catalog.dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434))]
    response = catalog.client.get("/api/models")
    assert response.status_code == 200
    catalog.factory.assert_called_once_with(
        api_key="catalog-primary-test-key", base_url="http://127.0.0.1:11434/v1", timeout=15.0,
    )

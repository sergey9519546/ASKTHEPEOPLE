"""Offline transport contracts for the pinned CAMEL adapter, not model quality."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _restore_config_class_identity():
    # Override the shared fixture: these tests intentionally never import the
    # Flask application/configuration or read developer .env files.
    yield


@pytest.fixture
def factory(monkeypatch):
    for key in list(os.environ):
        if key.startswith(("LLM_", "OPENAI_", "ANTHROPIC_", "LANGFUSE_")):
            monkeypatch.delenv(key)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("LANGFUSE_ENABLED", "false")

    def no_network(*args, **kwargs):
        pytest.fail("Provider transport tests must not access the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)

    config = ModuleType("_camel_transport_tests.config")
    config.Config = SimpleNamespace(
        LLM_API_KEY="offline-test-key",
        LLM_BASE_URL="https://gateway.example/v1",
        LLM_MODEL_NAME="anthropic/claude-offline-fixture",
    )
    name = "_camel_transport_tests.services.camel_model_factory"
    path = Path(__file__).parents[1] / "app/services/camel_model_factory.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, config.__name__, config)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def test_claude_gateway_keeps_openai_compatible_transport(factory):
    settings = factory.resolve_model_config("actor")

    assert settings.provider_mode == "openai_compatible"
    assert settings.model_platform == "OPENAI_COMPATIBLE_MODEL"
    assert settings.model_name == "anthropic/claude-offline-fixture"
    assert settings.base_url == "https://gateway.example/v1"


@pytest.mark.parametrize(
    ("url", "expected_mode", "expected_platform"),
    [
        ("https://api.openai.com/v1", "openai", "OPENAI"),
        ("https://api.openai.com/v1/chat/completions", "openai", "OPENAI"),
        ("https://anthropic-gateway.example/v1", "openai_compatible", "OPENAI_COMPATIBLE_MODEL"),
        ("https://provider.example/anthropic/v1", "openai_compatible", "OPENAI_COMPATIBLE_MODEL"),
        ("https://gateway.example/v1?provider=anthropic", "openai_compatible", "OPENAI_COMPATIBLE_MODEL"),
        ("https://api.anthropic.com@gateway.example/v1", "openai_compatible", "OPENAI_COMPATIBLE_MODEL"),
    ],
)
def test_provider_detection_uses_endpoint_contract_not_substrings(
    factory, url, expected_mode, expected_platform
):
    factory.Config.LLM_BASE_URL = url
    settings = factory.resolve_model_config("actor")

    assert (settings.provider_mode, settings.model_platform) == (
        expected_mode, expected_platform
    )


def test_role_and_boost_resolution_are_independent(factory, monkeypatch):
    monkeypatch.setenv("LLM_ACTOR_API_KEY", "actor-key")
    monkeypatch.setenv("LLM_ACTOR_BASE_URL", "https://actor.example/v1/chat/completions")
    monkeypatch.setenv("LLM_ACTOR_MODEL_NAME", "claude-on-openai-gateway")
    monkeypatch.setenv("LLM_BOOST_API_KEY", "boost-key")
    monkeypatch.setenv("LLM_BOOST_BASE_URL", "https://boost.example/v1/")
    monkeypatch.setenv("LLM_BOOST_MODEL_NAME", "boost-fixture")

    actor = factory.resolve_model_config("actor", prefer_boost=True)
    report = factory.resolve_model_config("report", prefer_boost=False)

    assert actor.source_prefix == "LLM_BOOST"
    assert actor.model_name == "boost-fixture"
    assert actor.base_url == "https://boost.example/v1"
    assert report.source_prefix == "LLM_REPORT"
    assert report.model_name == "anthropic/claude-offline-fixture"


@pytest.mark.parametrize("url", [
    "https://gateway.example/v1/messages",
    " https://gateway.example/v1/messages/ ",
    "https://gateway.example/v1/messages?api-version=fixture",
    "https://api.anthropic.com",
    "https://api.anthropic.com/v1/",
    "https://api.anthropic.com/v1/messages",
    "https://API.ANTHROPIC.COM:443/v1",
])
def test_native_messages_fail_before_camel_import(factory, monkeypatch, url):
    factory.Config.LLM_BASE_URL = url
    # Refusal must happen before any SDK construction or provider request.
    monkeypatch.setitem(sys.modules, "camel.models", None)

    settings = factory.resolve_model_config("actor")
    assert settings.provider_mode == "anthropic"
    assert "native Anthropic Messages transport is unsupported" in "; ".join(
        factory.validate_required_model_env("actor")
    )
    with pytest.raises(ValueError, match="native Anthropic Messages transport is unsupported"):
        factory.create_camel_model("actor")


@pytest.mark.parametrize("url", [
    "https://gateway.example/v1",
    "https://gateway.example/v1/chat/completions/",
    "https://api.anthropic.com.gateway.example/v1",
    "https://gateway.example/messages-service/v1",
])
def test_gateway_sdk_request_preserves_configured_endpoint(factory, monkeypatch, url):
    import httpx
    from camel.models import OpenAICompatibleModel

    factory.Config.LLM_BASE_URL = url
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={
            "id": "offline-completion",
            "object": "chat.completion",
            "created": 0,
            "model": factory.Config.LLM_MODEL_NAME,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "offline result"},
                "finish_reason": "stop",
            }],
        })

    # Intercept the SDK's HTTP transport, not our factory or CAMEL selection.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: respond(request))
    model = factory.create_camel_model("actor")
    try:
        assert type(model) is OpenAICompatibleModel
        result = model.run([{"role": "user", "content": "offline fixture"}])
        assert result.choices[0].message.content == "offline result"
        assert len(requests) == 1
        request = requests[0]
        assert request.url.host in {"gateway.example", "api.anthropic.com.gateway.example"}
        expected_path = (
            "/messages-service/v1/chat/completions"
            if "messages-service" in url else "/v1/chat/completions"
        )
        assert request.url.path == expected_path
        assert request.headers["authorization"] == "Bearer offline-test-key"
        assert json.loads(request.content)["model"] == factory.Config.LLM_MODEL_NAME
    finally:
        model._client.close()


def test_role_overrides_reach_pinned_factory(factory, monkeypatch):
    from camel.models import OpenAICompatibleModel

    monkeypatch.setenv("LLM_REPORT_API_KEY", "report-only-key")
    monkeypatch.setenv("LLM_REPORT_BASE_URL", "https://report.example/v1/chat/completions/")
    monkeypatch.setenv("LLM_REPORT_MODEL_NAME", "report-fixture")
    monkeypatch.setenv("LLM_REPORT_TIMEOUT", "9.5")
    monkeypatch.setenv("LLM_REPORT_MAX_RETRIES", "0")
    monkeypatch.setenv("LLM_REPORT_SEMAPHORE", "2")

    settings = factory.resolve_model_config("report")
    model = factory.create_camel_model("report")
    try:
        assert type(model) is OpenAICompatibleModel
        assert str(model.model_type) == "report-fixture"
        assert str(model._client.base_url) == "https://report.example/v1/"
        assert model._client.api_key == "report-only-key"
        assert model._client.timeout == 9.5
        assert model._client.max_retries == 0
        assert settings.semaphore == 2
    finally:
        model._client.close()


def test_boost_uses_its_own_transport_and_credentials(factory, monkeypatch):
    from camel.models import OpenAICompatibleModel

    monkeypatch.setenv("LLM_BOOST_API_KEY", "boost-only-key")
    monkeypatch.setenv("LLM_BOOST_BASE_URL", "https://boost.example/v1/chat/completions/")
    monkeypatch.setenv("LLM_BOOST_MODEL_NAME", "boost-fixture")
    monkeypatch.setenv("LLM_BOOST_TIMEOUT", "8.5")
    monkeypatch.setenv("LLM_BOOST_MAX_RETRIES", "1")
    model = factory.create_camel_model("actor", prefer_boost=True)
    try:
        assert type(model) is OpenAICompatibleModel
        assert str(model.model_type) == "boost-fixture"
        assert str(model._client.base_url) == "https://boost.example/v1/"
        assert model._client.api_key == "boost-only-key"
        assert model._client.timeout == 8.5
        assert model._client.max_retries == 1
    finally:
        model._client.close()

    monkeypatch.setenv("LLM_BOOST_BASE_URL", "https://boost.example/v1/messages")
    assert "actor: native Anthropic Messages transport is unsupported" in "; ".join(
        factory.validate_required_model_env("actor", prefer_boost=True)
    )
    with pytest.raises(ValueError, match="native Anthropic Messages transport is unsupported"):
        factory.create_camel_model("actor", prefer_boost=True)


def test_boost_without_key_falls_back_to_role_config(factory, monkeypatch):
    monkeypatch.setenv("LLM_BOOST_BASE_URL", "https://unused.example/v1/messages")
    monkeypatch.setenv("LLM_ACTOR_MODEL_NAME", "role-fixture")
    settings = factory.resolve_model_config("actor", prefer_boost=True)

    assert settings.source_prefix == "LLM_ACTOR"
    assert settings.model_name == "role-fixture"
    assert factory.validate_required_model_env("actor", prefer_boost=True) == []


def test_missing_credentials_refuse_before_camel_import(factory, monkeypatch):
    factory.Config.LLM_API_KEY = ""
    monkeypatch.setitem(sys.modules, "camel.models", None)

    assert factory.validate_required_model_env("actor") == ["actor: missing API key"]
    with pytest.raises(ValueError, match="missing API key for model creation"):
        factory.create_camel_model("actor")


def test_official_openai_creation_preserves_platform(factory):
    from camel.models import OpenAIModel

    factory.Config.LLM_BASE_URL = "https://api.openai.com/v1/chat/completions/"
    factory.Config.LLM_MODEL_NAME = "gpt-4o-mini"
    model = factory.create_camel_model("report")
    try:
        assert type(model) is OpenAIModel
        assert str(model._client.base_url) == "https://api.openai.com/v1/"
        assert model._client.api_key == "offline-test-key"
    finally:
        model._client.close()

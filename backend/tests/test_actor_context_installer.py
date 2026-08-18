"""Dev/test-gated ActorContext installer tests.

The canonical source-persistence boundary reads ``g.actor_context`` but the
production OIDC/membership resolver behind ADR-0009 is unbuilt. The installer
(``app/services/actor_context_installer.py``) installs a stable LEGACY_DEV
SERVICE scope in DEBUG when ``DEV_ACTOR_CONTEXT_ENABLED`` is set, and no-ops
everywhere else. These tests pin the gate and the end-to-end un-stranding of
the source upload-intent route.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from app import create_app
from app.config import Config
from app.domain.actor_context import ActorType, AuthenticationMethod


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    monkeypatch.setattr(Config, "DEBUG", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_ENABLED", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_FORMATS", ["txt"])
    monkeypatch.setattr(Config, "DEV_ACTOR_CONTEXT_ENABLED", False)
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _enable_persistence(monkeypatch):
    from app.api.routes import source_routes

    monkeypatch.setattr(source_routes, "_persistence_configured", lambda: True)


def _upload_intent(client):
    return client.post(
        "/api/simulation/sources/v1/upload-intent",
        json={"filename": "source.txt", "byte_length": 500},
    )


# --- Construction --- #


def test_build_dev_actor_context_is_valid_and_stable():
    from app.services.actor_context_installer import build_dev_actor_context

    first = build_dev_actor_context()
    second = build_dev_actor_context()

    assert first.actor_type is ActorType.SERVICE
    assert first.authentication_method is AuthenticationMethod.LEGACY_DEV
    assert first.user_id is None
    # Stable across requests so create/lookup round-trip against one scope.
    assert first.organization_id == second.organization_id
    assert first.workspace_id == second.workspace_id
    assert first.project_id == second.project_id
    assert first.actor_id == second.actor_id
    for value in (
        first.organization_id,
        first.workspace_id,
        first.project_id,
        first.actor_id,
        first.request_id,
    ):
        assert isinstance(value, UUID)
        assert value.version == 7


# --- Gate behavior --- #


def test_installer_noop_by_default(client, monkeypatch):
    """Flag off: the canonical boundary must stay fail-closed."""
    _enable_persistence(monkeypatch)
    resp = _upload_intent(client)
    assert resp.status_code == 503
    assert resp.get_json()["error"] == "tenant_context_unavailable"


def test_installer_noop_in_production(monkeypatch):
    """DEBUG=false must never install a synthetic scope, flag or not.

    Production scrubs 5xx error strings, so assert the fail-closed status and
    that the installer hook left ``g.actor_context`` unset.
    """
    monkeypatch.setattr(Config, "DEBUG", False)
    monkeypatch.setattr(Config, "DEV_ACTOR_CONTEXT_ENABLED", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_ENABLED", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_FORMATS", ["txt"])
    monkeypatch.setattr(Config, "REQUIRE_APP_AUTH", False)
    _enable_persistence(monkeypatch)
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    client = app.test_client()

    seen_context = {}

    def capture_actor_context():
        from flask import g

        seen_context["value"] = getattr(g, "actor_context", None)

    with app.test_request_context("/api/simulation/sources/v1/upload-intent"):
        # Force the before_request hooks to run for this context.
        app.preprocess_request()
        capture_actor_context()
    assert seen_context["value"] is None

    resp = _upload_intent(client)
    assert resp.status_code == 503


def test_installer_installs_scope_and_unstrands_upload_intent(client, monkeypatch):
    """DEBUG + flag on: the route passes the tenant gate and reaches the
    repository with the server-derived scope."""
    monkeypatch.setattr(Config, "DEV_ACTOR_CONTEXT_ENABLED", True)
    _enable_persistence(monkeypatch)

    from app.services import source_repository
    from app.services.actor_context_installer import build_dev_actor_context

    dev_scope = build_dev_actor_context()
    captured = {}

    def fake_create_source(**kwargs):
        captured["create_source"] = kwargs
        return {
            "id": dev_scope.project_id,
            "public_id": "src_test",
            "organization_id": kwargs["organization_id"],
            "workspace_id": kwargs["workspace_id"],
            "project_id": kwargs["project_id"],
            "created_by_actor_id": kwargs["created_by_actor_id"],
        }

    def fake_create_source_version(**kwargs):
        captured["create_source_version"] = kwargs
        return {"public_id": "srcv_test", "state": "UPLOADING"}

    monkeypatch.setattr(
        source_repository.SourceRepository,
        "create_source",
        staticmethod(fake_create_source),
        raising=False,
    )
    monkeypatch.setattr(
        source_repository.SourceRepository,
        "create_source_version",
        staticmethod(fake_create_source_version),
        raising=False,
    )

    resp = _upload_intent(client)
    assert resp.status_code == 200, resp.get_json()
    assert captured["create_source"]["organization_id"] == dev_scope.organization_id
    assert captured["create_source"]["workspace_id"] == dev_scope.workspace_id
    assert captured["create_source"]["project_id"] == dev_scope.project_id
    assert captured["create_source"]["created_by_actor_id"] == dev_scope.actor_id


def test_config_refuses_dev_actor_context_in_production(monkeypatch):
    monkeypatch.setattr(Config, "DEBUG", False)
    monkeypatch.setattr(Config, "DEV_ACTOR_CONTEXT_ENABLED", True)
    errors = Config.validate()
    assert any(
        "DEV_ACTOR_CONTEXT_ENABLED" in error and "not allowed in production" in error
        for error in errors
    )

    monkeypatch.setattr(Config, "DEBUG", True)
    errors = Config.validate()
    assert not any("DEV_ACTOR_CONTEXT_ENABLED" in error for error in errors)

"""Tests for the V1 source-ingestion API routes (Task 4 Checkpoint 4B).

The domain kernel (Task 4A) is implemented and tested separately. These tests
prove the HTTP wiring:

- Every mutating endpoint returns 503 ``source_ingestion_unavailable`` while
  ``SOURCE_INGESTION_V1_ENABLED`` is off (the default).
- The capability endpoint is always available and truthfully reports
  ``source_review=UNAVAILABLE`` when disabled.
- When the flag is on (test/dev only), the upload-intent route validates the
  format against the enabled-formats list.
- The production gate refuses startup when the flag is on in production mode.
"""

import pytest

from app import create_app
from app.config import Config


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_ENABLED", False)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_FORMATS", [])
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


# --- Disabled-flag behavior (the default) --- #


def test_capabilities_endpoint_reports_unavailable_when_disabled(client):
    """GET /api/simulation/sources/v1/capabilities is always available and
    truthfully reports UNAVAILABLE when the flag is off."""
    resp = client.get("/api/simulation/sources/v1/capabilities")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["source_review"] == "UNAVAILABLE"
    assert data["enabled"] is False
    assert data["formats"] == []


@pytest.mark.parametrize("method,path,json_body", [
    ("POST", "/api/simulation/sources/v1/upload-intent",
     {"filename": "test.txt", "byte_length": 100}),
    ("GET", "/api/simulation/sources/v1/src_1/status", None),
    ("POST", "/api/simulation/sources/v1/src_1/review",
     {"disposition": "ACCEPTED_SOURCE_CONDITION"}),
    ("POST", "/api/simulation/sources/v1/src_1/deletion", {}),
])
def test_mutating_routes_return_503_when_disabled(client, method, path, json_body):
    """Every mutating route must return 503 source_ingestion_unavailable
    while the flag is off — no production route may be exposed."""
    if method == "GET":
        resp = client.get(path)
    else:
        resp = client.post(path, json=json_body)
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error"] == "source_ingestion_unavailable"
    assert body["source_review"] == "UNAVAILABLE"


# --- Enabled-flag behavior (test/dev mode) --- #


@pytest.fixture
def enabled_client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    monkeypatch.setattr(Config, "DEBUG", True)  # dev/test, not production
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_ENABLED", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_FORMATS", ["txt"])
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def test_capabilities_endpoint_reports_available_when_enabled(enabled_client):
    resp = enabled_client.get("/api/simulation/sources/v1/capabilities")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["source_review"] == "AVAILABLE"
    assert data["enabled"] is True
    assert data["formats"] == ["txt"]


def test_upload_intent_rejects_non_enabled_format(enabled_client):
    """Only formats in SOURCE_INGESTION_V1_FORMATS are accepted."""
    resp = enabled_client.post(
        "/api/simulation/sources/v1/upload-intent",
        json={"filename": "doc.pdf", "byte_length": 100},
    )
    assert resp.status_code == 422
    assert resp.get_json()["error"] == "format_not_enabled"


def test_upload_intent_rejects_missing_filename(enabled_client):
    resp = enabled_client.post(
        "/api/simulation/sources/v1/upload-intent",
        json={"byte_length": 100},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "filename_required"


def test_upload_intent_rejects_invalid_byte_length(enabled_client):
    resp = enabled_client.post(
        "/api/simulation/sources/v1/upload-intent",
        json={"filename": "ok.txt", "byte_length": -1},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_byte_length"


def test_upload_intent_accepts_txt(enabled_client):
    """A valid TXT upload intent returns the structured intent shape."""
    resp = enabled_client.post(
        "/api/simulation/sources/v1/upload-intent",
        json={"filename": "source.txt", "byte_length": 500, "content_type": "text/plain"},
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["state"] == "UPLOADING"
    assert data["format"] == "txt"
    assert data["byte_length"] == 500


def test_persistence_enabled_requires_trusted_tenant_context(enabled_client, monkeypatch):
    """Persistence must fail closed until authentication installs server scope."""
    from app.api.routes import source_routes

    monkeypatch.setattr(source_routes, "_persistence_configured", lambda: True)

    upload = enabled_client.post(
        "/api/simulation/sources/v1/upload-intent",
        json={"filename": "source.txt", "byte_length": 500},
    )
    assert upload.status_code == 503
    assert upload.get_json()["error"] == "tenant_context_unavailable"

    status = enabled_client.get("/api/simulation/sources/v1/src_1/status")
    assert status.status_code == 503
    assert status.get_json()["error"] == "tenant_context_unavailable"

    review = enabled_client.post(
        "/api/simulation/sources/v1/src_1/review",
        json={"disposition": "ACCEPTED_SOURCE_CONDITION"},
    )
    assert review.status_code == 503
    assert review.get_json()["error"] == "tenant_context_unavailable"


def test_review_rejects_invalid_disposition(enabled_client):
    resp = enabled_client.post(
        "/api/simulation/sources/v1/src_1/review",
        json={"disposition": "GARBAGE"},
    )
    assert resp.status_code == 422
    assert resp.get_json()["error"] == "invalid_disposition"


def test_status_and_review_and_deletion_return_501_when_enabled(enabled_client):
    """When the flag is on but the persistence layer isn't wired (the §5
    production blocker), status/review/deletion return 501 Not Implemented
    rather than fabricating records."""
    assert enabled_client.get(
        "/api/simulation/sources/v1/src_1/status"
    ).status_code == 501

    assert enabled_client.post(
        "/api/simulation/sources/v1/src_1/review",
        json={"disposition": "ACCEPTED_SOURCE_CONDITION"},
    ).status_code == 501

    assert enabled_client.post(
        "/api/simulation/sources/v1/src_1/deletion", json={}
    ).status_code == 501


# --- Production gate --- #


def test_production_gate_refuses_source_flag(monkeypatch):
    """Config.validate_credentials must report an error when
    SOURCE_INGESTION_V1_ENABLED is true in production (DEBUG=False)."""
    monkeypatch.setattr(Config, "DEBUG", False)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_ENABLED", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_FORMATS", ["txt"])
    errors = Config.validate()
    source_errors = [e for e in errors if "SOURCE_INGESTION_V1_ENABLED" in e]
    assert len(source_errors) == 1
    assert "not allowed in production" in source_errors[0]


def test_production_gate_rejects_non_txt_formats(monkeypatch):
    """Only txt is an eligible V1 format; pdf/md/etc must be rejected."""
    monkeypatch.setattr(Config, "DEBUG", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_ENABLED", True)
    monkeypatch.setattr(Config, "SOURCE_INGESTION_V1_FORMATS", ["txt", "pdf"])
    errors = Config.validate()
    fmt_errors = [e for e in errors if "unsupported format" in e.lower()]
    assert len(fmt_errors) == 1

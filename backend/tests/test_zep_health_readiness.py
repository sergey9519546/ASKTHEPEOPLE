"""HTTP contract tests for Zep-aware readiness and provider-free liveness."""

from __future__ import annotations

import pytest

from app import create_app
from app.api import health as health_module


@pytest.fixture
def app(tmp_path, monkeypatch):
    app = create_app()
    app.config.update(
        TESTING=True,
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
    )
    monkeypatch.setattr(health_module, "check_database", lambda: True)
    monkeypatch.setattr(health_module, "check_redis", lambda: True)
    monkeypatch.setattr(health_module, "check_celery", lambda: True)
    return app


def _zep_status(*, status: str = "ok", reason: str = "available") -> dict:
    return {
        "status": status,
        "reason": reason,
        "cached": False,
        "stale": False,
        "checked_at": "2026-08-08T00:00:00Z",
        "age_seconds": 0.0,
    }


def test_liveness_never_calls_zep(app, monkeypatch):
    def forbidden():
        raise AssertionError("liveness contacted Zep")

    monkeypatch.setattr(
        health_module,
        "check_zep_dependency",
        forbidden,
        raising=False,
    )

    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert "zep" not in response.get_json()["components"]


def test_readiness_requires_available_zep(app, monkeypatch):
    monkeypatch.setattr(
        health_module,
        "check_zep_dependency",
        lambda: _zep_status(),
        raising=False,
    )

    response = app.test_client().get("/health/readiness")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["scope"] == "web"
    assert payload["revision"]
    assert payload["components"]["zep"] == "ok"
    assert payload["dependencies"]["zep"]["reason"] == "available"
    assert payload["capabilities"]["web_graph_backed"] == "ready"
    assert "graph_backed" not in payload["capabilities"]


@pytest.mark.parametrize(
    "reason",
    [
        "not_configured",
        "authentication_failed",
        "rate_limited",
        "timeout",
        "unavailable",
        "probe_failed",
    ],
)
def test_zep_failure_blocks_readiness_but_not_canonical_service(app, monkeypatch, reason):
    monkeypatch.setattr(
        health_module,
        "check_zep_dependency",
        lambda: _zep_status(status="error", reason=reason),
        raising=False,
    )

    response = app.test_client().get("/health/readiness")
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["status"] == "not_ready"
    assert payload["components"]["storage"] == "ok"
    assert payload["components"]["zep"] == "error"
    assert payload["dependencies"]["zep"]["reason"] == reason
    assert payload["scope"] == "web"
    assert payload["capabilities"]["web_graph_backed"] == "unavailable"

    liveness = app.test_client().get("/health")
    assert liveness.status_code == 200


def test_stale_success_never_qualifies_readiness(app, monkeypatch):
    stale = _zep_status()
    stale["stale"] = True
    stale["cached"] = True
    stale["age_seconds"] = 31.0
    monkeypatch.setattr(
        health_module,
        "check_zep_dependency",
        lambda: stale,
        raising=False,
    )

    response = app.test_client().get("/health/readiness")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["scope"] == "web"
    assert payload["capabilities"]["web_graph_backed"] == "unavailable"


def test_readiness_response_is_never_cacheable(app, monkeypatch):
    monkeypatch.setattr(
        health_module,
        "check_zep_dependency",
        lambda: _zep_status(),
        raising=False,
    )

    response = app.test_client().get("/health/readiness")

    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"

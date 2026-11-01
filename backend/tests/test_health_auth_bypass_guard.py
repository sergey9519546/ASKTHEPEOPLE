"""
Verify that /health and its subpaths (/health/readiness, /health/metrics)
are cleanly accessible without authorization while API routes enforce authentication.
"""
import pytest
from app import create_app

@pytest.fixture
def auth_app(monkeypatch):
    monkeypatch.setenv("REQUIRE_APP_AUTH", "true")
    monkeypatch.setenv("APP_TOKEN", "a_valid_32_character_long_secret_app_token_here")
    monkeypatch.setattr(
        "app.api.health.check_zep_dependency",
        lambda: {
            "status": "ok",
            "reason": "available",
            "cached": False,
            "stale": False,
            "checked_at": "2026-08-08T00:00:00Z",
            "age_seconds": 0.0,
        },
    )
    app = create_app()
    app.config.update({
        "TESTING": True,
        "REQUIRE_APP_AUTH": True,
        "APP_TOKEN": "a_valid_32_character_long_secret_app_token_here",
    })
    yield app

def test_health_routes_accessible_with_require_app_auth(auth_app):
    with auth_app.test_client() as client:
        # 1. Health routes are open without token
        res = client.get("/health")
        assert res.status_code in (200, 503)
        res = client.get("/health/")
        assert res.status_code in (200, 503)
        res = client.get("/health/readiness")
        assert res.status_code in (200, 503)
        res = client.get("/health/metrics")
        assert res.status_code == 200
        assert b"askthepeople" in res.data

        # 2. Non-health API route rejects unauthenticated request
        api_res = client.get("/api/settings")
        assert api_res.status_code == 401
        assert api_res.get_json()["error"] == "unauthorized"

        # 3. Non-health API route accepts valid token
        auth_header = {"Authorization": "Bearer a_valid_32_character_long_secret_app_token_here"}
        auth_res = client.get("/api/settings", headers=auth_header)
        assert auth_res.status_code == 200
        assert auth_res.get_json()["success"] is True

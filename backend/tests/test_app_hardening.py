"""
Tests for the security hardening of `backend/app/__init__.py`.

Covers (without overlapping the dedicated config/rate-limiting suites):
  1. Bearer-token auth guard (`require_auth` before_request hook):
       - explicitly disabled for local development -> routes are open
       - enabled -> missing / wrong token -> 401; correct Bearer -> through
       - health check stays open even when auth is on
  2. `RateLimitExceeded` is handled with a 429 (not swallowed into 500) and
     a dedicated handler is registered on the app.
  3. The global `@errorhandler(Exception)` does not leak internal messages in
     production (DEBUG=False) mode.

App construction follows the same pattern as test_settings.py /
test_rate_limiting.py: `create_app()` then `app.test_client()`.
"""

import pytest

from app import create_app
from flask import jsonify


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def app():
    """A fresh local-development app instance with auth explicitly disabled."""
    app = create_app()
    app.config.update({"TESTING": True})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


# --------------------------------------------------------------------------- #
# 1. Auth guard
# --------------------------------------------------------------------------- #

def test_auth_disabled_by_default_open(client):
    """With no APP_TOKEN, an /api/ route returns its normal status, not 401."""
    # GET /api/settings is a lightweight, non-rate-limited route.
    resp = client.get('/api/settings')
    assert resp.status_code != 401, (
        "auth should be disabled when APP_TOKEN is unset, but got 401"
    )


def test_auth_enabled_blocks_unauthenticated(app):
    """Setting APP_TOKEN must reject requests lacking a bearer token."""
    app.config['APP_TOKEN'] = 'secret'
    client = app.test_client()
    resp = client.get('/api/settings')
    assert resp.status_code == 401
    data = resp.get_json()
    assert data['success'] is False
    assert data['error'] == 'unauthorized'


def test_auth_enabled_blocks_wrong_token(app):
    """A token that does not match APP_TOKEN is rejected with 401."""
    app.config['APP_TOKEN'] = 'secret'
    client = app.test_client()
    resp = client.get('/api/settings', headers={'Authorization': 'Bearer nope'})
    assert resp.status_code == 401


def test_auth_enabled_accepts_correct_bearer(app):
    """The correct `Authorization: Bearer <token>` header passes the guard."""
    app.config['APP_TOKEN'] = 'secret'
    client = app.test_client()
    resp = client.get('/api/settings', headers={'Authorization': 'Bearer secret'})
    assert resp.status_code != 401, (
        f"correct bearer token should not be rejected, got {resp.status_code}"
    )


def test_auth_enabled_token_query_param(app):
    """Query tokens are never accepted on normal API routes."""
    app.config['APP_TOKEN'] = 'secret'
    client = app.test_client()
    resp = client.get('/api/settings?token=secret')
    assert resp.status_code == 401


def test_health_check_open_even_when_auth_enabled(app, monkeypatch):
    """The /health probe must remain reachable for liveness checks."""
    # Monkeypatch redis check to pass when Redis isn't running locally
    monkeypatch.setattr("app.api.health.check_redis", lambda: True)
    app.config['APP_TOKEN'] = 'secret'
    client = app.test_client()
    resp = client.get('/health')
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['status'] == 'ok'
    assert payload['revision']
    assert payload['storage_writable'] is True


def test_health_fails_when_artifact_storage_is_not_writable(app, monkeypatch):
    monkeypatch.setattr("app.os.access", lambda *_args, **_kwargs: False)
    response = app.test_client().get("/health")
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["storage_writable"] is False


def test_health_is_exempt_from_default_rate_limit(app):
    client = app.test_client()
    statuses = [client.get("/health").status_code for _ in range(60)]
    assert set(statuses) == {200}


# --------------------------------------------------------------------------- #
# 2. RateLimitExceeded handler
# --------------------------------------------------------------------------- #

def test_rate_limit_handler_registered(app):
    """A dedicated RateLimitExceeded handler exists on the app (most-specific).

    Flask stores handlers in `error_handler_spec[blueprint][status_code][ExcClass]`.
    A specific RateLimitExceeded handler dispatches before the catch-all
    Exception handler, so rate limits surface as 429 instead of being masked
    into a 500. We confirm that mapping is present on the app.
    """
    try:
        from flask_limiter import RateLimitExceeded
    except ImportError:
        pytest.skip("flask-limiter not installed")
    # Walk every blueprint/status subtree (app-level handlers live under None).
    registered = False
    for _bp, by_status in app.error_handler_spec.items():
        for _status, by_exc in (by_status or {}).items():
            if RateLimitExceeded in (by_exc or {}):
                registered = True
                break
    assert registered, (
        "RateLimitExceeded must have its own handler so it returns 429, not 500"
    )


def test_rate_limited_request_returns_429_not_500(client):
    """Hitting a rate-limited endpoint past its quota yields 429, never 500.

    POST /api/graph/ontology/generate is decorated with RATELIMIT_LLM_HEAVY
    (default 10 per hour). We fire enough requests to blow the quota and
    assert the limiter surfaces as 429 rather than being masked into a 500 by
    the catch-all Exception handler.
    """
    quota = 10  # RATELIMIT_LLM_HEAVY default
    saw_429 = False
    saw_500 = False
    for _ in range(quota + 3):
        resp = client.post('/api/graph/ontology/generate')
        if resp.status_code == 429:
            saw_429 = True
            break
        if resp.status_code == 500:
            saw_500 = True
    assert saw_429, (
        "limiter never returned 429 — handler may be missing or limit not enforced"
    )
    assert not saw_500, (
        "a rate-limited request was swallowed into a 500 by the catch-all "
        "Exception handler instead of returning 429"
    )


def test_rate_limit_uses_trusted_railway_client_ip(app):
    app.config["TRUST_X_REAL_IP"] = True
    client = app.test_client()
    first_client = {"X-Real-IP": "198.51.100.101"}
    second_client = {"X-Real-IP": "198.51.100.102"}

    statuses = [
        client.get("/api/settings", headers=first_client).status_code
        for _ in range(51)
    ]
    assert statuses[-1] == 429
    assert client.get(
        "/api/settings",
        headers=second_client,
    ).status_code != 429


# --------------------------------------------------------------------------- #
# 3. Global error handler must not leak internals in production
# --------------------------------------------------------------------------- #

def test_uncaught_exception_does_not_leak_in_production(app):
    """In DEBUG=False, an uncaught exception returns a generic message, not the raw error."""
    app.config['DEBUG'] = False

    @app.route('/api/_boom')
    def _boom():  # deliberately raises
        raise RuntimeError("DB connection string: postgres://user:pw@internal-host:5432")

    app.test_client()  # ensure app is fully initialized
    client = app.test_client()
    resp = client.get('/api/_boom')

    assert resp.status_code == 500
    data = resp.get_json()
    assert data['success'] is False
    assert data['error'] == 'internal_server_error', (
        f"production error response must not leak internals, got: {data!r}"
    )
    # The raw internal message must not appear in the response body.
    assert 'internal-host' not in resp.get_data(as_text=True)
    assert 'postgres' not in resp.get_data(as_text=True)


def test_uncaught_exception_leaks_in_debug(app):
    """In DEBUG=True the developer-facing message is exposed (sanity check)."""
    app.config['DEBUG'] = True

    @app.route('/api/_boom_debug')
    def _boom_debug():  # deliberately raises
        raise RuntimeError("debug-only-detail-9f3a7c2e")

    client = app.test_client()
    resp = client.get('/api/_boom_debug')
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['error'] == 'debug-only-detail-9f3a7c2e', (
        f"DEBUG mode should expose the message for developers, got: {data!r}"
    )


# --------------------------------------------------------------------------- #
# 3b. strip_traceback_in_production scrubs route-level 500 error strings
# --------------------------------------------------------------------------- #

def test_route_500_error_string_scrubbed_in_production(app):
    """A route that catches its own exception and returns str(e) + traceback as
    a 500 must have both the traceback key and the raw error string scrubbed in
    production (DEBUG=False). This is the M3 fix: str(e) commonly leaks internal
    hostnames, file paths, and upstream API bodies.
    """
    import traceback as _tb

    app.config['DEBUG'] = False

    @app.route('/api/_leak')
    def _leak():
        try:
            raise RuntimeError("internal-secret: postgres://user:pw@db.internal:5432")
        except Exception:
            return jsonify({
                "success": False,
                "error": "internal-secret: postgres://user:pw@db.internal:5432",
                "traceback": _tb.format_exc(),
            }), 500

    client = app.test_client()
    resp = client.get('/api/_leak')
    assert resp.status_code == 500
    data = resp.get_json()
    # traceback key must be removed entirely
    assert 'traceback' not in data, f"traceback key leaked: {data!r}"
    # error string must be replaced with generic message
    assert data['error'] == 'internal_server_error', (
        f"production 500 error must be scrubbed, got: {data!r}"
    )
    # The raw internal detail must not appear anywhere in the response body.
    body = resp.get_data(as_text=True)
    assert 'internal-secret' not in body
    assert 'postgres' not in body
    assert 'db.internal' not in body


def test_route_4xx_error_preserved_in_production(app):
    """4xx client errors keep their error message in production — they are
    informative (bad request, not found) and do not reflect server internals.
    """
    app.config['DEBUG'] = False

    @app.route('/api/_client_error')
    def _client_error():
        return jsonify({"success": False, "error": "bad_request: missing field"}), 400

    client = app.test_client()
    resp = client.get('/api/_client_error')
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['error'] == 'bad_request: missing field', (
        f"4xx error message should be preserved in production, got: {data!r}"
    )


def test_unknown_api_route_is_json_404_not_spa_html(app):
    response = app.test_client().get('/api/definitely-not-a-route')
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json() == {"success": False, "error": "not_found"}


def test_http_exception_status_is_preserved(app):
    from flask import abort

    @app.route('/api/_forbidden')
    def _forbidden():
        abort(403)

    response = app.test_client().get('/api/_forbidden')
    assert response.status_code == 403
    assert response.get_json()["error"] == "forbidden"


def test_request_logging_does_not_include_json_body(app, monkeypatch):
    import app as app_module

    calls = []

    class SpyLogger:
        def debug(self, *args, **kwargs):
            calls.append((args, kwargs))

    monkeypatch.setattr(app_module, "get_logger", lambda _name: SpyLogger())
    app.test_client().post(
        '/api/definitely-not-a-route',
        json={"LLM_API_KEY": "never-log-this-secret"},
    )
    assert "never-log-this-secret" not in repr(calls)


def test_production_security_and_cache_headers(app):
    app.config["DEBUG"] = False
    client = app.test_client()

    response = client.get(
        "/health",
        headers={"X-Forwarded-Proto": "https"},
    )

    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers[
        "Content-Security-Policy"
    ]
    assert response.headers["Strict-Transport-Security"].startswith(
        "max-age=31536000"
    )

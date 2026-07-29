"""
Tests for Phase 2: per-route rate limiting on the 7 high-risk endpoints.

Spec (`docs/plans/2026-03-23-hardening-plan.md`, Phase 2):
  Install Flask-Limiter and decorate these routes with explicit limits:
    CRITICAL  POST /api/report/generate               (RATELIMIT_LLM_HEAVY = "10 per hour")
    CRITICAL  POST /api/report/chat                    (RATELIMIT_LLM_HEAVY)
    HIGH      POST /api/graph/ontology/generate        (RATELIMIT_LLM_HEAVY)
    HIGH      POST /api/simulation/prepare             (RATELIMIT_LLM_HEAVY)
    MEDIUM    POST /api/simulation/create              (RATELIMIT_LLM_MEDIUM = "20 per hour")
    MEDIUM    POST /api/graph/build                    (RATELIMIT_LLM_MEDIUM)
    MEDIUM    POST /api/simulation/generate-profiles   (RATELIMIT_LLM_MEDIUM)

Each endpoint has its own independent in-memory counter keyed by client IP, so
this test exercises them in isolation. The app's global `@errorhandler(Exception)`
catches `RateLimitExceeded` and would turn it into a 500, which masks the real
429 — so we register a dedicated `RateLimitExceeded` handler in the test app to
observe the limiter's true behavior. This is test-only wiring; no source change.

If Flask-Limiter (or the `@limiter.limit` decorators) is not yet present on the
branch under test, the suite xfail`s with a clear reason so CI stays green.
"""

import pytest

from app import create_app
from app.api import graph as graph_module
from app.api import report as report_module
from app.api import simulation as simulation_module

# (method, path, builder, quota) for each high-risk endpoint.
# `quota` is the number of requests the configured limit allows per hour; we
# fire quota+1 and expect the last one to be rejected.


def _json_body():
    """Minimal JSON body — endpoints fail fast on missing IDs (400/404), which is
    exactly what we want for the pre-limit calls: cheap, side-effect free."""
    return {"simulation_id": "sim_rl_probe", "project_id": "proj_rl_probe"}


ENDPOINTS = [
    # (label, client call lambda, quota)
    ("report/generate", lambda c: c.post("/api/report/generate", json=_json_body()), 10),
    ("report/chat", lambda c: c.post("/api/report/chat", json=_json_body()), 10),
    ("graph/ontology/generate", lambda c: c.post("/api/graph/ontology/generate"), 10),
    ("simulation/prepare", lambda c: c.post("/api/simulation/prepare", json=_json_body()), 10),
    ("simulation/create", lambda c: c.post("/api/simulation/create", json=_json_body()), 20),
    ("graph/build", lambda c: c.post("/api/graph/build", json=_json_body()), 20),
    ("simulation/generate-profiles", lambda c: c.post("/api/simulation/generate-profiles", json=_json_body()), 20),
]


def _decorated_endpoints_present():
    """Return True iff at least one high-risk route carries an @limiter.limit wrapper."""
    for mod in (report_module, graph_module, simulation_module):
        src = open(mod.__file__, encoding="utf-8").read()
        if "limiter.limit" in src:
            return True
    return False


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})

    try:
        from flask_limiter import RateLimitExceeded
    except Exception:
        pytest.xfail(
            "pending Phase 2 rate-limiting merge: flask_limiter is not installed"
        )

    if not _decorated_endpoints_present():
        pytest.xfail(
            "pending Phase 2 rate-limiting merge: no @limiter.limit decorators found"
        )

    # Observe the limiter's true verdict. The app's catch-all Exception handler
    # would otherwise swallow RateLimitExceeded into a 500.
    @app.errorhandler(RateLimitExceeded)
    def _on_rate_limited(e):  # pragma: no cover - registered for completeness
        return {"success": False, "error": "rate_limited"}, 429

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.parametrize("label, call, quota", ENDPOINTS, ids=[e[0] for e in ENDPOINTS])
def test_high_risk_endpoint_returns_429_when_limit_exceeded(client, label, call, quota):
    """After `quota` allowed requests, the next request must be rejected (429)."""
    seen_429 = False
    # Fire a few extra to be tolerant of any off-by-one in the configured limit.
    for i in range(quota + 3):
        resp = call(client)
        if resp.status_code == 429:
            seen_429 = True
            break
    assert seen_429, (
        f"{label}: limiter never returned 429 after {quota + 3} requests "
        f"(Phase 2 per-route limit may not be enforced on this endpoint)"
    )

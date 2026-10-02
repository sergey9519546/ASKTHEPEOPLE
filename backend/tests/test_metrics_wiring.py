"""End-to-end: request metrics must record real traffic through the app.

The unit tests in `test_metrics_gate4.py` exercise the registry directly. This
file proves the middleware is actually installed by `create_app` and that a
real request produces a real series with a safe label.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.metrics import REGISTRY  # noqa: E402


@pytest.fixture()
def app_and_registry(monkeypatch):
    """A real app from create_app, with a clean registry."""
    monkeypatch.setenv("SECRET_KEY", "metrics-test-secret-key-0000000000000000")
    monkeypatch.setenv("APP_TOKEN", "metrics-test-token")
    monkeypatch.setenv("FLASK_DEBUG", "true")
    monkeypatch.setenv("USE_SUPABASE_PERSISTENCE", "false")

    from app import create_app

    REGISTRY.reset()
    app = create_app()
    app.config.update(TESTING=True)
    yield app, REGISTRY
    REGISTRY.reset()


def _hook_names(app, attr) -> set:
    """Names of registered hooks.

    Flask wraps some hooks in ``functools.partial``, which has no
    ``__name__``, so unwrap defensively rather than assuming.
    """
    names = set()
    for func in getattr(app, attr, {}).get(None, []):
        target = getattr(func, "func", func)  # partial -> wrapped function
        name = getattr(target, "__name__", None)
        if name:
            names.add(name)
    return names


def test_create_app_installs_the_metrics_hooks(app_and_registry):
    """If the hooks were never registered, every other assertion here would be
    satisfied by an empty registry."""
    app, _ = app_and_registry
    before = _hook_names(app, "before_request_funcs")
    after = _hook_names(app, "after_request_funcs")
    assert "_metrics_start" in before, sorted(before)
    assert "_metrics_finish" in after, sorted(after)


def test_health_request_produces_a_series(app_and_registry):
    app, registry = app_and_registry
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code in (200, 503), "health must answer either way"

    snap = registry.snapshot()
    assert snap["requests"], "no series recorded for a completed request"
    row = snap["requests"][0]
    assert row["method"] == "GET"
    assert row["status_class"] in {"2xx", "5xx"}
    assert row["count"] >= 1
    assert row["total_seconds"] > 0


def test_route_label_is_the_endpoint_not_the_path(app_and_registry):
    """The privacy property, end to end. The recorded route must be Flask's
    endpoint name, never the URL the client asked for."""
    app, registry = app_and_registry
    client = app.test_client()

    client.get("/health?token=secret-value&user=someone@example.com")

    for row in registry.snapshot()["requests"]:
        route = row["route"]
        assert "secret-value" not in route
        assert "someone@example.com" not in route
        assert "?" not in route
        assert not route.startswith("/"), route


def test_metrics_endpoint_reports_recorded_traffic(app_and_registry):
    """Scrape after a request: the exposition must contain that request."""
    app, _ = app_and_registry
    client = app.test_client()

    client.get("/health")
    body = client.get("/health/metrics").get_data(as_text=True)

    assert "askthepeople_http_requests_total{" in body
    # At least one series with a non-zero count.
    counts = [
        int(m.group(1))
        for m in re.finditer(r"askthepeople_http_requests_total\{[^}]*\} (\d+)", body)
    ]
    assert counts and max(counts) >= 1


def test_in_flight_returns_to_zero_after_requests(app_and_registry):
    """A leaked increment would report a permanently growing gauge."""
    app, registry = app_and_registry
    client = app.test_client()
    for _ in range(3):
        client.get("/health")
    assert registry.snapshot()["in_flight"] == 0


def test_exploding_route_still_returns_gauge_to_zero(app_and_registry):
    """The after_request hook must fire on the error path too, or every
    exception would leak one unit of in-flight depth."""
    app, registry = app_and_registry
    client = app.test_client()

    @app.route("/__boom__")
    def _boom():
        raise RuntimeError("deliberate")

    client.get("/__boom__")

    assert registry.snapshot()["in_flight"] == 0
    classes = [row["status_class"] for row in registry.snapshot()["requests"]]
    assert "5xx" in classes, f"an error must be counted as 5xx, got {classes}"
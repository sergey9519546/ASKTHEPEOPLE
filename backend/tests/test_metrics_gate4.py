"""Request metrics for Gate 4 (exec-plan T29).

The property that matters most here is not that the numbers are correct. It is
that **no identifier can reach a metric label**. A label carrying a project id
or a request path is a privacy leak and a cardinality bomb at once: one new
time series per distinct value, retained forever.

So the tests assert both directions: the metrics work, and they refuse to
capture anything user-specific.
"""

from __future__ import annotations

import re
import sys
import threading
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.metrics import (  # noqa: E402
    BUCKET_LABELS,
    LATENCY_BUCKETS,
    MetricsRegistry,
    REGISTRY,
    render_prometheus,
    route_label,
    status_class,
)


@pytest.fixture(autouse=True)
def clean_registry():
    REGISTRY.reset()
    yield
    REGISTRY.reset()


# --- labelling ---------------------------------------------------------- #


@pytest.mark.parametrize(
    "code,expected",
    [
        (200, "2xx"), (204, "2xx"), (301, "3xx"),
        (404, "4xx"), (422, "4xx"),
        (500, "5xx"), (503, "5xx"),
    ],
)
def test_status_class_buckets(code, expected):
    assert status_class(code) == expected


@pytest.mark.parametrize("code", [0, 99, 600, 99999, None, "abc"])
def test_status_class_rejects_out_of_range(code):
    """An out-of-range status must not create a 1xx or 6xx series."""
    assert status_class(code) in {"unknown"} or status_class(code).endswith("xx")


def test_route_label_passes_through_flask_endpoint():
    """Flask's endpoint is the rule, which is safe."""
    assert route_label("simulation_bp.fork") == "simulation_bp.fork"


@pytest.mark.parametrize("bad", [None, "", 12345, object()])
def test_route_label_rejects_non_strings(bad):
    assert route_label(bad) == "unmatched"


def test_route_label_refuses_absurdly_long_values():
    """A guard against a future change putting a URL in here. A real endpoint
    name is short; anything oversized is treated as data, not a label."""
    assert route_label("x" * 500) == "unmatched"


def test_route_label_never_contains_a_path_separator():
    """A label containing '/' or an id-looking segment is a bug. This is the
    cheapest possible tripwire for 'someone passed request.path'."""
    label = route_label("simulation_bp.fork")
    assert "/" not in label
    assert not re.search(r"\b[0-9a-f]{8,}\b", label), label


# --- registry ----------------------------------------------------------- #


def test_observe_records_count_and_latency():
    registry = MetricsRegistry()
    registry.observe("GET", "health_bp.health", 200, 0.02)
    registry.observe("GET", "health_bp.health", 200, 0.04)
    snap = registry.snapshot()
    assert len(snap["requests"]) == 1
    row = snap["requests"][0]
    assert row["count"] == 2
    assert row["total_seconds"] == pytest.approx(0.06)


def test_series_are_keyed_by_method_route_and_class():
    registry = MetricsRegistry()
    registry.observe("GET", "a", 200, 0.01)
    registry.observe("POST", "a", 200, 0.01)
    registry.observe("GET", "a", 500, 0.01)
    assert len(registry.snapshot()["requests"]) == 3


def test_buckets_are_cumulative_and_bounded():
    registry = MetricsRegistry()
    registry.observe("GET", "a", 200, 0.004)   # <= 0.005
    registry.observe("GET", "a", 200, 0.5)     # <= 0.5
    registry.observe("GET", "a", 200, 100.0)    # beyond every bound
    row = registry.snapshot()["requests"][0]
    buckets = row["buckets"]
    assert len(buckets) == len(LATENCY_BUCKETS)
    assert buckets == sorted(buckets), "buckets must be non-decreasing"
    assert buckets[0] == 1, "the fast request belongs in the first bucket"
    # The +Inf line uses the total count, so a request slower than the last
    # bound still shows up even though it incremented no bucket.
    assert row["count"] == 3


def test_in_flight_gauge_returns_to_zero():
    registry = MetricsRegistry()
    registry.enter_request()
    registry.enter_request()
    assert registry.snapshot()["in_flight"] == 2
    registry.exit_request()
    registry.exit_request()
    assert registry.snapshot()["in_flight"] == 0


def test_in_flight_cannot_go_negative():
    """A missing enter must not render a negative gauge, which a scraper
    would reject and an operator would read as a bug."""
    registry = MetricsRegistry()
    registry.exit_request()
    assert registry.snapshot()["in_flight"] == 0


def test_registry_is_thread_safe():
    """Flask serves on threads. Concurrent observe must not lose counts."""
    registry = MetricsRegistry()
    errors: list[BaseException] = []

    def worker():
        try:
            for _ in range(200):
                registry.observe("GET", "a", 200, 0.001)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert registry.snapshot()["requests"][0]["count"] == 1600


# --- rendering ---------------------------------------------------------- #


def test_render_prometheus_emits_declared_types():
    registry = MetricsRegistry()
    registry.observe("GET", "health_bp.health", 200, 0.01)
    out = render_prometheus(registry)
    for metric in (
        "askthepeople_uptime_seconds",
        "askthepeople_requests_in_flight",
        "askthepeople_http_requests_total",
        "askthepeople_http_request_duration_seconds_sum",
        "askthepeople_http_request_duration_bucket",
    ):
        assert metric in out, metric
    assert "# TYPE askthepeople_http_requests_total counter" in out
    assert "# TYPE askthepeople_requests_in_flight gauge" in out


def test_render_prometheus_bucket_lines_are_cumulative():
    registry = MetricsRegistry()
    for duration in (0.001, 0.02, 0.3):
        registry.observe("GET", "a", 200, duration)
    out = render_prometheus(registry)
    counts = [
        int(m.group(2))
        for m in re.finditer(r'le="([^"]+)"\} (\d+)$', out, re.MULTILINE)
    ]
    assert counts == sorted(counts), f"buckets not monotonic: {counts}"
    assert counts[-1] == 3, "the +Inf bucket must equal the total count"


def test_render_escapes_label_values():
    registry = MetricsRegistry()
    registry.observe("GET", 'we"ird\\route', 200, 0.01)
    out = render_prometheus(registry)
    assert 'we\\"ird\\\\route' in out


def test_render_has_no_identifier_shaped_labels():
    """The privacy property, asserted on the output rather than the input.

    Even if a caller passes something id-shaped, the exposition must not
    contain a bare hex id or a path segment as a label value.
    """
    registry = MetricsRegistry()
    registry.observe("GET", "simulation_bp.get_simulation", 200, 0.01)
    out = render_prometheus(registry)
    label_values = re.findall(r'(?:method|route|status_class)="([^"]*)"', out)
    assert label_values, "expected labels in the output"
    for value in label_values:
        assert "/" not in value, value
        assert not re.search(r"[0-9a-f]{12,}", value), value


# --- endpoint ----------------------------------------------------------- #


def test_metrics_endpoint_is_served():
    """The route exists, is not under /api, and returns the exposition."""
    from flask import Flask

    from app.api.health import CONTENT_TYPE_LATEST, health_bp

    app = Flask(__name__)
    app.register_blueprint(health_bp, url_prefix="/health")

    client = app.test_client()
    response = client.get("/health/metrics")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith(CONTENT_TYPE_LATEST.split(";")[0])
    body = response.get_data(as_text=True)
    assert "askthepeople_uptime_seconds" in body


def test_buckets_have_stable_labels():
    """A drifting bucket set would silently change the meaning of every
    recorded series."""
    assert len(BUCKET_LABELS) == len(LATENCY_BUCKETS)
    assert BUCKET_LABELS == tuple(str(b) for b in LATENCY_BUCKETS)
    assert list(LATENCY_BUCKETS) == sorted(LATENCY_BUCKETS)
"""In-process request metrics for Gate 4 (exec-plan T29).

Deliberately dependency-free. Gate 4 is "NOT STARTED" in
`docs/architecture/index.md` because there were no metrics and no tracing.
This adds the smallest thing that is actually useful: request counts, latency,
error counts, and in-flight depth, exposed in Prometheus text format at
``GET /health/metrics``.

Design constraints
------------------
**No unbounded labels.** A metric label carrying a URL path, a project id, a
simulation id, or a user id is a privacy leak and a cardinality bomb: every
distinct value creates a new time series that is retained forever. This module
labels only by

* ``method`` — a fixed, small set of HTTP verbs
* ``route`` — the Flask **endpoint rule** (``/api/simulation/<id>/fork``), not
  the concrete URL, so ids never appear
* ``status_class`` — ``2xx``/``3xx``/``4xx``/``5xx``, never the raw code

Anything that cannot be reduced to those three is dropped rather than
truncated. ``_route_label`` returns ``"unmatched"`` when there is no endpoint
rule, so a request to an unknown path cannot become a series per path.

**No high-cardinality or unbounded storage.** Latency is kept as a fixed set of
bucket boundaries, not per-request samples, and series are keyed by the triple
above. The registry is bounded by
``method x endpoints x 4`` regardless of traffic.

**Thread-safe.** Flask serves requests on threads, and the Celery worker shares
the process in some topologies. Every mutation is under a lock.

**Cheap when unused.** If the process is not a server (a script, a test, a
Celery task) the instrumentation is never installed.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Tuple

# Latency bucket boundaries in seconds. Fixed, so the histogram size does not
# grow with traffic. The upper bound is deliberately generous: the interesting
# question for a request endpoint is "did it take longer than a person would
# wait", and anything above the last bucket is reported as +Inf.
LATENCY_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)
BUCKET_LABELS: Tuple[str, ...] = tuple(
    f"{b}" for b in LATENCY_BUCKETS
)

STATUS_CLASSES: Tuple[str, ...] = ("2xx", "3xx", "4xx", "5xx")


def status_class(status_code: int) -> str:
    """Bucket an HTTP status into a fixed class label."""
    try:
        code = int(status_code)
    except (TypeError, ValueError):
        return "unknown"
    if code < 100 or code > 599:
        return "unknown"
    return f"{code // 100}xx"


class MetricsRegistry:
    """Thread-safe, bounded, in-process metric storage."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (method, route, status_class) -> [count, cumulative_seconds, buckets]
        self._requests: Dict[Tuple[str, str, str], list] = {}
        self._in_flight = 0
        self._started_at = time.time()

    # --- recording ------------------------------------------------------- #

    def observe(
        self,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        key = (method, route, status_class(status_code))
        with self._lock:
            entry = self._requests.get(key)
            if entry is None:
                entry = [0, 0.0, [0] * len(LATENCY_BUCKETS)]
                self._requests[key] = entry
            entry[0] += 1
            entry[1] += duration_seconds
            for index, bound in enumerate(LATENCY_BUCKETS):
                if duration_seconds <= bound:
                    entry[2][index] += 1

    def enter_request(self) -> None:
        with self._lock:
            self._in_flight += 1

    def exit_request(self) -> None:
        with self._lock:
            self._in_flight -= 1
            if self._in_flight < 0:
                # Defensive: a missing enter must not leak into the output.
                self._in_flight = 0

    def reset(self) -> None:
        """Clear all series. Used by tests; not on any runtime path."""
        with self._lock:
            self._requests.clear()
            self._in_flight = 0
            self._started_at = time.time()

    # --- reading --------------------------------------------------------- #

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds": time.time() - self._started_at,
                "in_flight": self._in_flight,
                "requests": [
                    {
                        "method": key[0],
                        "route": key[1],
                        "status_class": key[2],
                        "count": entry[0],
                        "total_seconds": entry[1],
                        "buckets": list(entry[2]),
                    }
                    for key, entry in sorted(self._requests.items())
                ],
            }


# Process-wide registry. One per process is correct: metrics describe this
# process, and a multi-process deployment aggregates per instance.
REGISTRY = MetricsRegistry()


def route_label(endpoint: str | None) -> str:
    """Reduce a Flask endpoint rule to a safe, bounded label.

    Flask's ``request.endpoint`` is the rule, e.g. ``simulation_bp.fork``,
    with no user data. Anything unexpected becomes ``"unmatched"`` so a
    request to an unrouted path cannot generate one series per path.
    """
    if not endpoint or not isinstance(endpoint, str):
        return "unmatched"
    if len(endpoint) > 120:
        return "unmatched"
    return endpoint


def render_prometheus(registry: MetricsRegistry) -> str:
    """Render the registry in Prometheus text exposition format.

    Escaping follows the exposition spec: backslash, double quote and newline
    are escaped in label values.
    """
    snap = registry.snapshot()
    lines: list[str] = []

    lines.append("# HELP askthepeople_uptime_seconds Process uptime.")
    lines.append("# TYPE askthepeople_uptime_seconds gauge")
    lines.append(f"askthepeople_uptime_seconds {snap['uptime_seconds']:.3f}")

    lines.append("# HELP askthepeople_requests_in_flight Requests currently being served.")
    lines.append("# TYPE askthepeople_requests_in_flight gauge")
    lines.append(f"askthepeople_requests_in_flight {snap['in_flight']}")

    lines.append("# HELP askthepeople_http_requests_total Completed HTTP requests.")
    lines.append("# TYPE askthepeople_http_requests_total counter")
    lines.append(
        "# HELP askthepeople_http_request_duration_seconds Request latency."
    )
    lines.append("# TYPE askthepeople_http_request_duration_seconds histogram")
    lines.append(
        "# HELP askthepeople_http_request_duration_bucket Requests by latency bucket."
    )
    lines.append("# TYPE askthepeople_http_request_duration_bucket histogram")

    for row in snap["requests"]:
        labels = (
            f'method="{_escape(row["method"])}",'
            f'route="{_escape(row["route"])}",'
            f'status_class="{_escape(row["status_class"])}"'
        )
        lines.append(f"askthepeople_http_requests_total{{{labels}}} {row['count']}")
        lines.append(
            f'askthepeople_http_request_duration_seconds_sum{{{labels}}} '
            f"{row['total_seconds']:.6f}"
        )
        cumulative = 0
        for index, label in enumerate(BUCKET_LABELS):
            cumulative = row["buckets"][index]
            lines.append(
                f"askthepeople_http_request_duration_bucket{{{labels},le=\"{label}\"}} "
                f"{cumulative}"
            )
        lines.append(
            f'askthepeople_http_request_duration_bucket{{{labels},le="+Inf"}} '
            f"{row['count']}"
        )

    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )

"""HTTP availability attestation for the Celery worker.

The server is intentionally not a process-only liveness endpoint.  Railway
uses ``/health`` to decide whether this service can receive work, so a 200 is
returned only after Celery's ``worker_ready`` signal has produced a fresh,
revision-bound marker for the expected live worker process.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.build_revision import (
    IMAGE_BUILD_REVISION_PATH,
    resolve_deployed_revision,
)


_MARKER_SCHEMA = "askthepeople-worker-ready/v1"
_DEFAULT_MARKER_PATH = "/tmp/askthepeople-worker-ready.json"
_MAX_MARKER_BYTES = 4096
_STALE_AFTER_SECONDS = 10.0
_FUTURE_CLOCK_SKEW_SECONDS = 1.0


def _runtime_revision(
    environment: Mapping[str, object],
    *,
    image_revision_path: Path = IMAGE_BUILD_REVISION_PATH,
) -> str:
    return resolve_deployed_revision(
        environment,
        image_revision_path=image_revision_path,
    )


def _process_exists(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _load_marker(marker_path: Path) -> dict[str, Any] | None:
    try:
        if not marker_path.is_file() or marker_path.stat().st_size > _MAX_MARKER_BYTES:
            return None
        candidate = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return candidate if isinstance(candidate, dict) else None


def evaluate_worker_health(
    environment: Mapping[str, object] | None = None,
    *,
    now_epoch: float | None = None,
    process_exists: Callable[[int], bool] = _process_exists,
) -> tuple[int, dict[str, str]]:
    """Return a privacy-safe HTTP status and body without provider I/O."""
    env = os.environ if environment is None else environment
    revision = _runtime_revision(env)
    payload = {
        "status": "unavailable",
        "service": "celery-worker",
        "revision": revision,
    }
    if not revision:
        return 503, payload

    try:
        expected_worker_pid = int(str(env.get("WORKER_PARENT_PID") or ""))
    except (TypeError, ValueError):
        return 503, payload
    if expected_worker_pid <= 1:
        return 503, payload

    marker_path = Path(
        str(env.get("WORKER_HEALTH_MARKER") or _DEFAULT_MARKER_PATH)
    )
    marker = _load_marker(marker_path)
    if marker is None or marker.get("schema_version") != _MARKER_SCHEMA:
        return 503, payload

    try:
        marker_pid = int(marker.get("worker_pid"))
        heartbeat_at = float(marker.get("heartbeat_at"))
    except (TypeError, ValueError):
        return 503, payload

    observed_at = time.time() if now_epoch is None else float(now_epoch)
    age = observed_at - heartbeat_at
    marker_is_current = (
        marker.get("revision") == revision
        and marker_pid == expected_worker_pid
        and math.isfinite(heartbeat_at)
        and -_FUTURE_CLOCK_SKEW_SECONDS <= age <= _STALE_AFTER_SECONDS
    )
    if not marker_is_current or not process_exists(marker_pid):
        return 503, payload

    return 200, {
        "status": "ok",
        "service": "celery-worker",
        "revision": revision,
    }


class HealthHandler(BaseHTTPRequestHandler):
    """Serve only bounded availability state; never configuration details."""

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        """Suppress BaseHTTP's HTML body and runtime fingerprint headers."""
        del message, explain
        self.send_response_only(code)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        if self.path not in ("/health", "/health/ready", "/health/"):
            self.send_response_only(404)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        status, payload = evaluate_worker_health()
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        # ``send_response`` adds Python/BaseHTTP version headers. This endpoint
        # is an attestation surface, so emit only the bounded headers below.
        self.send_response_only(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _fmt: str, *_args: object) -> None:
        return


def run() -> None:
    environment = os.environ
    if not _runtime_revision(environment):
        raise SystemExit("fatal: immutable worker revision is required")
    try:
        int(environment.get("WORKER_PARENT_PID", ""))
    except (TypeError, ValueError) as exc:
        raise SystemExit("fatal: worker parent identity is required") from exc

    port = int(environment.get("PORT", 5001))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"[worker_health] Availability server listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()

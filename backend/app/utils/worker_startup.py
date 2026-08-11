"""Pure, no-network startup validation for graph/report Celery workers."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from .build_revision import IMAGE_BUILD_REVISION_PATH, resolve_deployed_revision


_MARKER_SCHEMA = "askthepeople-worker-ready/v1"
_DEFAULT_MARKER_PATH = "/tmp/askthepeople-worker-ready.json"
_MAX_MARKER_BYTES = 4096


class WorkerStartupConfigurationError(RuntimeError):
    """Raised before a worker starts with incomplete graph configuration."""


def validate_worker_zep_configuration(environment: Mapping[str, object]) -> None:
    """Require a non-empty Zep key without contacting any provider."""
    if not str(environment.get("ZEP_API_KEY") or "").strip():
        raise WorkerStartupConfigurationError(
            "ZEP_API_KEY is required for graph-backed worker tasks"
        )


def resolve_worker_runtime_revision(
    environment: Mapping[str, object],
    *,
    image_revision_path: Path = IMAGE_BUILD_REVISION_PATH,
) -> str:
    """Return the image-owned revision only when all identity sources agree."""
    return resolve_deployed_revision(
        environment,
        image_revision_path=image_revision_path,
    )


def _require_redis_url(name: str, value: object) -> None:
    candidate = str(value or "").strip()
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        raise WorkerStartupConfigurationError(
            f"{name} must use redis:// or rediss://"
        ) from None
    if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
        raise WorkerStartupConfigurationError(
            f"{name} must use redis:// or rediss://"
        )


def validate_worker_configuration(environment: Mapping[str, object]) -> None:
    """Fail closed on local configuration only; never contact a dependency."""
    validate_worker_zep_configuration(environment)
    if not str(environment.get("LLM_API_KEY") or "").strip():
        raise WorkerStartupConfigurationError(
            "LLM_API_KEY is required for graph/report worker tasks"
        )

    redis_url = environment.get("REDIS_URL")
    if not str(redis_url or "").strip():
        raise WorkerStartupConfigurationError(
            "REDIS_URL is required for durable worker coordination"
        )
    _require_redis_url("REDIS_URL", redis_url)
    _require_redis_url(
        "CELERY_BROKER_URL",
        environment.get("CELERY_BROKER_URL") or redis_url,
    )
    _require_redis_url(
        "CELERY_RESULT_BACKEND",
        environment.get("CELERY_RESULT_BACKEND") or redis_url,
    )

    if not resolve_worker_runtime_revision(environment):
        raise WorkerStartupConfigurationError(
            "immutable runtime revision is required for worker attestation"
        )

    configured_marker = str(environment.get("WORKER_HEALTH_MARKER") or "").strip()
    if configured_marker and configured_marker != _DEFAULT_MARKER_PATH:
        raise WorkerStartupConfigurationError(
            "WORKER_HEALTH_MARKER must use the dedicated runtime marker path"
        )


def _worker_marker_path(environment: Mapping[str, object]) -> Path:
    return Path(
        str(environment.get("WORKER_HEALTH_MARKER") or _DEFAULT_MARKER_PATH)
    )


def publish_worker_ready_marker(
    environment: Mapping[str, object],
    *,
    worker_pid: int,
    now_epoch: float | None = None,
) -> None:
    """Atomically publish a bounded marker after Celery reports readiness."""
    revision = resolve_worker_runtime_revision(environment)
    if not revision:
        raise WorkerStartupConfigurationError(
            "immutable runtime revision is required for worker attestation"
        )
    if worker_pid <= 1:
        raise WorkerStartupConfigurationError(
            "valid worker process identity is required for worker attestation"
        )

    marker_path = _worker_marker_path(environment)
    temporary_path = marker_path.with_name(
        f".{marker_path.name}.{worker_pid}.tmp"
    )
    marker = {
        "schema_version": _MARKER_SCHEMA,
        "worker_pid": worker_pid,
        "revision": revision,
        "heartbeat_at": time.time() if now_epoch is None else float(now_epoch),
    }
    try:
        temporary_path.write_text(
            json.dumps(marker, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary_path, marker_path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def clear_worker_ready_marker(environment: Mapping[str, object]) -> bool:
    """Unconditionally clear a marker before a new worker boot is validated."""
    marker_path = _worker_marker_path(environment)
    try:
        marker_path.unlink()
    except FileNotFoundError:
        return False
    except IsADirectoryError:
        return False
    return True


def remove_worker_ready_marker(
    environment: Mapping[str, object],
    *,
    worker_pid: int,
) -> bool:
    """Remove the marker only when it still belongs to this worker process."""
    marker_path = _worker_marker_path(environment)
    try:
        if marker_path.stat().st_size > _MAX_MARKER_BYTES:
            return False
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(marker, dict) or marker.get("worker_pid") != worker_pid:
        return False
    try:
        marker_path.unlink()
    except FileNotFoundError:
        return False
    return True

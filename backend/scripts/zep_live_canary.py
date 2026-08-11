"""Operator CLI for dry-running or dispatching the worker-owned Zep canary."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.zep_live_canary import (  # noqa: E402
    RotationEvidenceError,
    validate_rotation_evidence,
)

_MAX_EVIDENCE_BYTES = 64 * 1024
_EXIT_CODES = {0, 2, 3, 4, 5}
_GRAPH_ID_RE = re.compile(r"^atp_canary_v1_\d{8}t\d{6}z_[0-9a-f]{24}$")
_RESULT_REASONS = {
    "canary_dispatch_failed",
    "canary_failed",
    "canary_identity_failed",
    "canary_journal_unavailable",
    "canary_lock_unavailable",
    "canary_not_enabled",
    "canary_run_identity_invalid",
    "canary_passed",
    "cleanup_journal_unavailable",
    "cleanup_not_confirmed",
    "cleanup_owner_unverified",
    "cleanup_verification_unavailable",
    "deployment_revision_mismatch",
    "episode_processing_failed",
    "episode_processing_timeout",
    "episode_submission_unconfirmed",
    "explicit_execute_required",
    "graph_create_unconfirmed",
    "graph_verification_failed",
    "ontology_verification_failed",
    "prior_cleanup_pending",
    "redis_configuration_required",
    "rotation_evidence_invalid",
    "task_result_invalid",
    "zep_client_configuration_failed",
    "zep_configuration_required",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate rotation evidence and optionally dispatch the protected canary."
    )
    parser.add_argument("--evidence-file", required=True, type=Path)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly dispatch the canary to the deployed Celery worker.",
    )
    parser.add_argument("--wait-seconds", type=int, default=240)
    return parser


def _load_evidence(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file() or path.stat().st_size > _MAX_EVIDENCE_BYTES:
            raise RotationEvidenceError("rotation_evidence_invalid")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RotationEvidenceError("rotation_evidence_invalid") from exc
    if not isinstance(payload, dict):
        raise RotationEvidenceError("rotation_evidence_invalid")
    return validate_rotation_evidence(payload)


def _dispatch(*, evidence: dict[str, Any], wait_seconds: int = 240) -> dict[str, Any]:
    from app.tasks.zep_canary_tasks import run_zep_live_canary_task

    result = run_zep_live_canary_task.apply_async(kwargs={"evidence": evidence})
    payload = result.get(timeout=wait_seconds)
    if not isinstance(payload, dict):
        return {"exit_code": 5, "state": "BLOCKED", "reason": "task_result_invalid"}
    return payload


def _safe_print(payload: dict[str, Any]) -> None:
    allowed = {
        key: payload[key]
        for key in ("exit_code", "state", "reason", "graph_id")
        if key in payload
    }
    print(json.dumps(allowed, sort_keys=True, separators=(",", ":")))


def _task_result_is_safe(payload: Any) -> bool:
    if not isinstance(payload, dict) or not set(payload).issubset(
        {"exit_code", "state", "reason", "graph_id"}
    ):
        return False
    exit_code = payload.get("exit_code")
    state = payload.get("state")
    reason = payload.get("reason")
    graph_id = payload.get("graph_id")
    if exit_code not in _EXIT_CODES or reason not in _RESULT_REASONS:
        return False
    if graph_id is not None and (
        not isinstance(graph_id, str) or not _GRAPH_ID_RE.fullmatch(graph_id)
    ):
        return False
    functional_failures = {
        "canary_failed",
        "graph_create_unconfirmed",
        "ontology_verification_failed",
        "episode_submission_unconfirmed",
        "episode_processing_failed",
        "episode_processing_timeout",
        "graph_verification_failed",
    }
    cleanup_failures = {
        "cleanup_journal_unavailable",
        "cleanup_not_confirmed",
        "cleanup_owner_unverified",
        "cleanup_verification_unavailable",
        "prior_cleanup_pending",
    }
    blocked_reasons = {
        "canary_identity_failed",
        "canary_journal_unavailable",
        "canary_lock_unavailable",
        "canary_not_enabled",
        "canary_run_identity_invalid",
        "deployment_revision_mismatch",
        "explicit_execute_required",
        "redis_configuration_required",
        "rotation_evidence_invalid",
        "zep_client_configuration_failed",
        "zep_configuration_required",
    }
    matrix = {
        0: state == "CLEAN" and reason == "canary_passed" and graph_id is not None,
        2: state == "CLEAN" and reason in functional_failures and graph_id is not None,
        3: state == "CLEANUP_PENDING"
        and reason in cleanup_failures
        and graph_id is not None,
        4: state == "BLOCKED"
        and reason == "rotation_evidence_invalid"
        and graph_id is None,
        5: state == "BLOCKED" and reason in blocked_reasons and graph_id is None,
    }
    return matrix.get(exit_code, False)


def main(
    argv: list[str] | None = None,
    *,
    dispatch: Callable[..., dict[str, Any]] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        evidence = _load_evidence(args.evidence_file)
    except RotationEvidenceError:
        result = {
            "exit_code": 4,
            "state": "BLOCKED",
            "reason": "rotation_evidence_invalid",
        }
        _safe_print(result)
        return 4
    if not args.execute:
        result = {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "explicit_execute_required",
        }
        _safe_print(result)
        return 5
    try:
        dispatch_fn = dispatch or (
            lambda **kwargs: _dispatch(wait_seconds=args.wait_seconds, **kwargs)
        )
        result = dispatch_fn(evidence=evidence)
    except Exception:
        result = {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "canary_dispatch_failed",
        }
    if not _task_result_is_safe(result):
        result = {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "task_result_invalid",
        }
    exit_code = result["exit_code"]
    _safe_print(result)
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())

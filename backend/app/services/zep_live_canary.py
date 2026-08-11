"""Fail-closed, worker-owned live canary for the derived Zep graph index.

The module deliberately exposes no HTTP surface.  It accepts only a closed
rotation-evidence document, runs with a fixed fictional fixture, and records a
sanitized state journal in the deployment's restricted Redis instance.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import Field
from zep_cloud import EpisodeData, EntityEdgeSourceTarget
from zep_cloud.client import Zep
from zep_cloud.external_clients.ontology import EdgeModel, EntityModel, EntityText

from ..utils.build_revision import resolve_deployed_revision
from ..utils.task_retry import is_retryable_task_exception


CANARY_FIXTURE = (
    "CanarySensorAlpha is a fictional CanarySensor. "
    "CanaryHubBeta is a fictional CanaryHub. "
    "CanarySensorAlpha ReportsTo CanaryHubBeta. "
    "This is an automated deployment fixture and describes no real person or system."
)
CANARY_GRAPH_NAME = "Protected Zep live canary"
CANARY_SOURCE_DESCRIPTION = "Automated fictional deployment fixture."
JOURNAL_KEY = "askthepeople:zep-live-canary:v1:journal"
LOCK_KEY = "askthepeople:zep-live-canary:v1:lock"
LOCK_TTL_SECONDS = 600
REQUEST_OPTIONS = {"timeout_in_seconds": 10, "max_retries": 0}
TOTAL_TIMEOUT_SECONDS = 180.0
EPISODE_TIMEOUT_SECONDS = 120.0
CLEANUP_TIMEOUT_SECONDS = 60.0
POLL_SECONDS = 2.0
SAFE_READ_DELAYS = (0.5, 1.0)

_EVIDENCE_FIELDS = {
    "schema_version",
    "incident_id",
    "provider",
    "old_credentials_revoked",
    "old_credentials_revoked_at",
    "replacement_issued",
    "replacement_issued_at",
    "web_updated",
    "web_updated_at",
    "worker_updated",
    "worker_updated_at",
    "web_restarted",
    "web_restarted_at",
    "worker_restarted",
    "worker_restarted_at",
    "provider_usage_reviewed_through",
    "rotated_by",
    "independently_verified_by",
    "verified_at",
    "deployment_revision",
    "restricted_evidence_ref",
}
_TRUE_FIELDS = {
    "old_credentials_revoked",
    "replacement_issued",
    "web_updated",
    "worker_updated",
    "web_restarted",
    "worker_restarted",
}
_TIMESTAMP_FIELDS = {
    "old_credentials_revoked_at",
    "replacement_issued_at",
    "web_updated_at",
    "worker_updated_at",
    "web_restarted_at",
    "worker_restarted_at",
    "provider_usage_reviewed_through",
    "verified_at",
}
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_REVISION_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
_EVIDENCE_REF_RE = re.compile(
    r"^(?:incident|ticket|vault)://[A-Za-z0-9][A-Za-z0-9._/-]{2,159}$"
)
_GRAPH_ID_RE = re.compile(r"^atp_canary_v1_\d{8}t\d{6}z_[0-9a-f]{24}$")
_RUN_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_PENDING_CLEANUP_STATES = {
    "CREATE_REQUESTED",
    "GRAPH_CREATED",
    "ONTOLOGY_REQUESTED",
    "ONTOLOGY_VERIFIED",
    "EPISODE_REQUESTED",
    "EPISODE_ACKNOWLEDGED",
    "EPISODE_PROCESSED",
    "GRAPH_VERIFIED",
    "DELETE_REQUESTED",
    "RECONCILING",
    "CLEANUP_PENDING",
}
_JOURNAL_FIELDS = {
    "schema_version",
    "state",
    "run_id",
    "deployment_revision",
    "graph_id",
    "owner_marker",
    "updated_at",
    "reason",
    "terminal_result",
}
_FUNCTIONAL_FAILURE_REASONS = {
    "canary_failed",
    "graph_create_unconfirmed",
    "ontology_verification_failed",
    "episode_submission_unconfirmed",
    "episode_processing_failed",
    "episode_processing_timeout",
    "graph_verification_failed",
}
_CLEANUP_REASONS = {
    "cleanup_journal_unavailable",
    "cleanup_not_confirmed",
    "cleanup_owner_unverified",
    "cleanup_verification_unavailable",
    "prior_cleanup_pending",
}
_JOURNAL_REASONS = (
    _FUNCTIONAL_FAILURE_REASONS
    | _CLEANUP_REASONS
    | {
        "preflight_complete",
        "create_requested",
        "graph_created",
        "ontology_requested",
        "ontology_verified",
        "episode_requested",
        "episode_acknowledged",
        "episode_processed",
        "graph_verified",
        "delete_requested",
        "canary_passed",
    }
)


class CanarySensor(EntityModel):
    """A fictional deployment-canary sensor."""

    canary_note: EntityText = Field(
        default=None,
        description="Fictional deployment-canary classification.",
    )


class CanaryHub(EntityModel):
    """A fictional deployment-canary hub."""

    canary_note: EntityText = Field(
        default=None,
        description="Fictional deployment-canary classification.",
    )


class ReportsTo(EdgeModel):
    """Connects the fictional canary sensor to its fictional canary hub."""


class RotationEvidenceError(ValueError):
    """The closed rotation-evidence contract was not satisfied."""


class _CanaryFailure(RuntimeError):
    """Internal failure carrying only a stable public-safe reason."""


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RotationEvidenceError("rotation_evidence_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RotationEvidenceError("rotation_evidence_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise RotationEvidenceError("rotation_evidence_invalid")
    return parsed.astimezone(UTC)


def validate_rotation_evidence(
    evidence: Mapping[str, Any],
    *,
    utcnow: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Validate and copy the exact non-secret rotation-evidence v1 schema."""
    if not isinstance(evidence, Mapping) or set(evidence) != _EVIDENCE_FIELDS:
        raise RotationEvidenceError("rotation_evidence_invalid")
    if evidence.get("schema_version") != "zep-rotation-evidence/v1":
        raise RotationEvidenceError("rotation_evidence_invalid")
    if (
        evidence.get("incident_id")
        != "public-historical-provider-credentials-2026-07-29"
        or evidence.get("provider") != "zep-cloud"
    ):
        raise RotationEvidenceError("rotation_evidence_invalid")
    if any(evidence.get(field) is not True for field in _TRUE_FIELDS):
        raise RotationEvidenceError("rotation_evidence_invalid")

    rotated_by = evidence.get("rotated_by")
    verified_by = evidence.get("independently_verified_by")
    if (
        not isinstance(rotated_by, str)
        or not _IDENTIFIER_RE.fullmatch(rotated_by)
        or not isinstance(verified_by, str)
        or not _IDENTIFIER_RE.fullmatch(verified_by)
        or rotated_by.casefold() == verified_by.casefold()
    ):
        raise RotationEvidenceError("rotation_evidence_invalid")
    revision = evidence.get("deployment_revision")
    evidence_ref = evidence.get("restricted_evidence_ref")
    if not isinstance(revision, str) or not _REVISION_RE.fullmatch(revision):
        raise RotationEvidenceError("rotation_evidence_invalid")
    if not isinstance(evidence_ref, str) or not _EVIDENCE_REF_RE.fullmatch(
        evidence_ref
    ):
        raise RotationEvidenceError("rotation_evidence_invalid")

    timestamps = {
        field: _parse_utc_timestamp(evidence.get(field)) for field in _TIMESTAMP_FIELDS
    }
    replacement = timestamps["replacement_issued_at"]
    revoked = timestamps["old_credentials_revoked_at"]
    verified = timestamps["verified_at"]
    if replacement < revoked:
        raise RotationEvidenceError("rotation_evidence_invalid")
    if timestamps["web_updated_at"] < replacement:
        raise RotationEvidenceError("rotation_evidence_invalid")
    if timestamps["worker_updated_at"] < replacement:
        raise RotationEvidenceError("rotation_evidence_invalid")
    if timestamps["web_restarted_at"] < timestamps["web_updated_at"]:
        raise RotationEvidenceError("rotation_evidence_invalid")
    if timestamps["worker_restarted_at"] < timestamps["worker_updated_at"]:
        raise RotationEvidenceError("rotation_evidence_invalid")
    if timestamps["provider_usage_reviewed_through"] < max(
        timestamps["web_restarted_at"], timestamps["worker_restarted_at"]
    ):
        raise RotationEvidenceError("rotation_evidence_invalid")
    if verified < max(
        timestamps["web_restarted_at"],
        timestamps["worker_restarted_at"],
        timestamps["provider_usage_reviewed_through"],
    ):
        raise RotationEvidenceError("rotation_evidence_invalid")
    now = (utcnow or (lambda: datetime.now(UTC)))()
    if verified > now.astimezone(UTC):
        raise RotationEvidenceError("rotation_evidence_invalid")
    return dict(evidence)


def make_canary_graph_id(
    now: datetime,
    *,
    token_hex: Callable[[int], str] = secrets.token_hex,
) -> str:
    """Create the one allowed internal graph-ID shape for this canary."""
    timestamp = now.astimezone(UTC).strftime("%Y%m%dt%H%M%Sz")
    nonce = token_hex(12)
    if not re.fullmatch(r"[0-9a-f]{24}", nonce):
        raise ValueError("canary_nonce_invalid")
    return f"atp_canary_v1_{timestamp}_{nonce}"


def owner_marker(graph_id: str) -> str:
    """Return the exact graph description that authorizes canary cleanup."""
    return f"atp_zep_live_canary_owner:v1:{graph_id}"


def _terminal_journal_key(run_id: str) -> str:
    return f"{JOURNAL_KEY}:terminal:{run_id}"


def _run_id_is_valid(run_id: Any) -> bool:
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        return False
    try:
        return str(uuid.UUID(run_id)) == run_id
    except ValueError:
        return False


def _is_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _status_code(exc: Exception) -> int | None:
    value = getattr(exc, "status_code", None)
    return value if isinstance(value, int) else None


def _redis_factory(redis_url: str):
    import redis

    return redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )


def _client_factory(*, api_key: str, timeout: float):
    return Zep(api_key=api_key, timeout=timeout)


def _terminal_result_is_safe(result: Any, *, graph_id: str) -> bool:
    if not isinstance(result, dict) or set(result) != {
        "exit_code",
        "state",
        "reason",
        "graph_id",
    }:
        return False
    if result.get("state") != "CLEAN" or result.get("graph_id") != graph_id:
        return False
    exit_code = result.get("exit_code")
    reason = result.get("reason")
    return bool(
        (exit_code == 0 and reason == "canary_passed")
        or (exit_code == 2 and reason in _FUNCTIONAL_FAILURE_REASONS)
    )


def _terminal_result(*, exit_code: int, reason: str, graph_id: str) -> dict[str, Any]:
    result = {
        "exit_code": exit_code,
        "state": "CLEAN",
        "reason": reason,
        "graph_id": graph_id,
    }
    if not _terminal_result_is_safe(result, graph_id=graph_id):
        raise _CanaryFailure("canary_journal_unavailable")
    return result


def _read_journal(redis_client, *, key: str = JOURNAL_KEY) -> dict[str, Any] | None:
    raw = redis_client.get(key)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if not isinstance(raw, str) or len(raw) > 4096:
        raise _CanaryFailure("canary_journal_invalid")
    try:
        record = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise _CanaryFailure("canary_journal_invalid") from exc
    if not isinstance(record, dict) or set(record) != _JOURNAL_FIELDS:
        raise _CanaryFailure("canary_journal_invalid")
    state = record.get("state")
    graph_id = record.get("graph_id")
    if (
        record.get("schema_version") != "zep-live-canary-journal/v2"
        or state not in (_PENDING_CLEANUP_STATES | {"PREFLIGHTED", "CLEAN"})
        or not _run_id_is_valid(record.get("run_id"))
        or not isinstance(record.get("deployment_revision"), str)
        or not _REVISION_RE.fullmatch(record["deployment_revision"])
        or not isinstance(graph_id, str)
        or not _GRAPH_ID_RE.fullmatch(graph_id)
        or record.get("owner_marker") != owner_marker(graph_id)
        or record.get("reason") not in _JOURNAL_REASONS
    ):
        raise _CanaryFailure("canary_journal_invalid")
    try:
        _parse_utc_timestamp(record.get("updated_at"))
    except RotationEvidenceError as exc:
        raise _CanaryFailure("canary_journal_invalid") from exc
    terminal_result = record.get("terminal_result")
    if state == "CLEAN":
        if (
            not _terminal_result_is_safe(terminal_result, graph_id=graph_id)
            or terminal_result["reason"] != record["reason"]
        ):
            raise _CanaryFailure("canary_journal_invalid")
    elif terminal_result is not None:
        raise _CanaryFailure("canary_journal_invalid")
    return record


def _write_journal(
    redis_client,
    *,
    state: str,
    run_id: str,
    deployment_revision: str,
    graph_id: str,
    marker: str,
    now: datetime,
    reason: str,
    terminal_result: dict[str, Any] | None = None,
) -> None:
    if (
        state not in (_PENDING_CLEANUP_STATES | {"PREFLIGHTED", "CLEAN"})
        or not _run_id_is_valid(run_id)
        or not _REVISION_RE.fullmatch(deployment_revision)
        or not _GRAPH_ID_RE.fullmatch(graph_id)
        or marker != owner_marker(graph_id)
        or reason not in _JOURNAL_REASONS
        or (
            state == "CLEAN"
            and (
                not _terminal_result_is_safe(terminal_result, graph_id=graph_id)
                or terminal_result["reason"] != reason
            )
        )
        or (state != "CLEAN" and terminal_result is not None)
    ):
        raise _CanaryFailure("canary_journal_unavailable")
    record = {
        "schema_version": "zep-live-canary-journal/v2",
        "state": state,
        "run_id": run_id,
        "deployment_revision": deployment_revision,
        "graph_id": graph_id,
        "owner_marker": marker,
        "updated_at": _utc_text(now),
        "reason": reason,
        "terminal_result": terminal_result,
    }
    try:
        written = redis_client.set(
            JOURNAL_KEY,
            json.dumps(record, sort_keys=True, separators=(",", ":")),
        )
    except Exception as exc:
        raise _CanaryFailure("canary_journal_unavailable") from exc
    if written is False:
        raise _CanaryFailure("canary_journal_unavailable")
    if state == "CLEAN":
        try:
            terminal_written = redis_client.set(
                _terminal_journal_key(run_id),
                json.dumps(record, sort_keys=True, separators=(",", ":")),
            )
        except Exception as exc:
            raise _CanaryFailure("canary_journal_unavailable") from exc
        if terminal_written is False:
            raise _CanaryFailure("canary_journal_unavailable")


def _try_write_journal(redis_client, **kwargs) -> bool:
    """Best-effort journal write used only while provider cleanup must continue."""
    try:
        _write_journal(redis_client, **kwargs)
    except Exception:
        return False
    return True


def _release_lock(redis_client, token: str) -> None:
    script = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('del', KEYS[1]) else return 0 end"
    )
    try:
        redis_client.eval(script, 1, LOCK_KEY, token)
    except Exception:
        pass


def _safe_read(
    operation: Callable[[], Any],
    *,
    sleep: Callable[[float], None],
) -> Any:
    for attempt in range(3):
        try:
            return operation()
        except Exception as exc:
            if attempt == 2 or not is_retryable_task_exception(exc):
                raise
            sleep(SAFE_READ_DELAYS[attempt])
    raise AssertionError("unreachable")


def _ontology_is_exact(response: Any) -> bool:
    entity_types = getattr(response, "entity_types", None)
    edge_types = getattr(response, "edge_types", None)
    if not isinstance(entity_types, Sequence) or not isinstance(edge_types, Sequence):
        return False
    if len(entity_types) != 2 or {
        getattr(item, "name", None) for item in entity_types
    } != {
        "CanarySensor",
        "CanaryHub",
    }:
        return False
    if len(edge_types) != 1 or getattr(edge_types[0], "name", None) != "ReportsTo":
        return False
    source_targets = getattr(edge_types[0], "source_targets", None)
    return bool(
        isinstance(source_targets, Sequence)
        and len(source_targets) == 1
        and getattr(source_targets[0], "source", None) == "CanarySensor"
        and getattr(source_targets[0], "target", None) == "CanaryHub"
    )


def _graph_is_exact(nodes: Any, edges: Any, episode_uuid: str) -> bool:
    if not isinstance(nodes, Sequence) or len(nodes) != 2:
        return False
    if not isinstance(edges, Sequence) or len(edges) != 1:
        return False
    nodes_by_name = {getattr(node, "name", None): node for node in nodes}
    if set(nodes_by_name) != {"CanarySensorAlpha", "CanaryHubBeta"}:
        return False
    sensor = nodes_by_name["CanarySensorAlpha"]
    hub = nodes_by_name["CanaryHubBeta"]
    if "CanarySensor" not in (getattr(sensor, "labels", None) or []):
        return False
    if "CanaryHub" not in (getattr(hub, "labels", None) or []):
        return False
    edge = edges[0]
    return bool(
        getattr(edge, "name", None) == "ReportsTo"
        and getattr(edge, "source_node_uuid", None) == getattr(sensor, "uuid_", None)
        and getattr(edge, "target_node_uuid", None) == getattr(hub, "uuid_", None)
        and (getattr(edge, "episodes", None) or []) == [episode_uuid]
    )


def _cleanup_graph(
    *,
    client,
    redis_client,
    graph_id: str,
    marker: str,
    run_id: str,
    deployment_revision: str,
    terminal_result: dict[str, Any],
    utcnow: Callable[[], datetime],
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
    normal_delete: bool,
    allow_delete: bool = True,
) -> tuple[bool, str, bool]:
    del normal_delete
    deadline = monotonic() + CLEANUP_TIMEOUT_SECONDS

    def write(state: str, reason: str, *, terminal=None) -> bool:
        return _try_write_journal(
            redis_client,
            state=state,
            run_id=run_id,
            deployment_revision=deployment_revision,
            graph_id=graph_id,
            marker=marker,
            now=utcnow(),
            reason=reason,
            terminal_result=terminal,
        )

    try:
        graph = _safe_read(
            lambda: client.graph.get(
                graph_id,
                request_options=REQUEST_OPTIONS,
            ),
            sleep=sleep,
        )
    except Exception as exc:
        if _status_code(exc) == 404:
            journal_ok = write(
                "CLEAN", terminal_result["reason"], terminal=terminal_result
            )
            return True, "graph_absent", journal_ok
        journal_ok = write("CLEANUP_PENDING", "cleanup_verification_unavailable")
        return False, "cleanup_verification_unavailable", journal_ok

    if (
        getattr(graph, "graph_id", None) != graph_id
        or getattr(graph, "description", None) != marker
    ):
        journal_ok = write("CLEANUP_PENDING", "cleanup_owner_unverified")
        return False, "cleanup_owner_unverified", journal_ok

    if not allow_delete:
        journal_ok = write("CLEANUP_PENDING", "cleanup_not_confirmed")
        return False, "cleanup_not_confirmed", journal_ok

    # This durable intent is written before the one allowed delete mutation.
    # A journal outage must not prevent owner-verified cleanup from continuing.
    write("DELETE_REQUESTED", "delete_requested")

    try:
        client.graph.delete(
            graph_id,
            request_options=REQUEST_OPTIONS,
        )
    except Exception:
        # Delete acknowledgement is ambiguous. Never replay the mutation; only
        # confirm absence until the bounded cleanup deadline.
        pass

    while monotonic() <= deadline:
        try:
            graph = _safe_read(
                lambda: client.graph.get(
                    graph_id,
                    request_options=REQUEST_OPTIONS,
                ),
                sleep=sleep,
            )
        except Exception as exc:
            if _status_code(exc) == 404:
                journal_ok = write(
                    "CLEAN", terminal_result["reason"], terminal=terminal_result
                )
                return True, "canary_clean", journal_ok
            journal_ok = write("CLEANUP_PENDING", "cleanup_verification_unavailable")
            return False, "cleanup_verification_unavailable", journal_ok
        if (
            getattr(graph, "graph_id", None) != graph_id
            or getattr(graph, "description", None) != marker
        ):
            journal_ok = write("CLEANUP_PENDING", "cleanup_owner_unverified")
            return False, "cleanup_owner_unverified", journal_ok
        if monotonic() >= deadline:
            break
        sleep(POLL_SECONDS)

    journal_ok = write("CLEANUP_PENDING", "cleanup_not_confirmed")
    return False, "cleanup_not_confirmed", journal_ok


def _journal_gate_result(
    prior: dict[str, Any] | None,
    *,
    run_id: str,
    deployment_revision: str,
) -> dict[str, Any] | None:
    if prior is None:
        return None
    if prior["run_id"] == run_id:
        if prior["deployment_revision"] != deployment_revision:
            return {
                "exit_code": 5,
                "state": "BLOCKED",
                "reason": "deployment_revision_mismatch",
            }
        if prior["state"] == "CLEAN":
            return dict(prior["terminal_result"])
        return None
    if prior["state"] != "CLEAN":
        return {
            "exit_code": 3,
            "state": "CLEANUP_PENDING",
            "reason": "prior_cleanup_pending",
            "graph_id": prior["graph_id"],
        }
    return None


def run_protected_zep_canary(
    *,
    evidence: Mapping[str, Any],
    run_id: str,
    execute: bool = False,
    environ: Mapping[str, str] = os.environ,
    redis_factory: Callable[[str], Any] = _redis_factory,
    client_factory: Callable[..., Any] = _client_factory,
    utcnow: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    token_hex: Callable[[int], str] = secrets.token_hex,
) -> dict[str, Any]:
    """Run the protected canary and return only a sanitized terminal result."""
    if execute is not True:
        return {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "explicit_execute_required",
        }
    try:
        closed_evidence = validate_rotation_evidence(evidence, utcnow=utcnow)
    except RotationEvidenceError:
        return {
            "exit_code": 4,
            "state": "BLOCKED",
            "reason": "rotation_evidence_invalid",
        }
    if not _run_id_is_valid(run_id):
        return {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "canary_run_identity_invalid",
        }
    if environ.get("ZEP_LIVE_CANARY_ENABLED", "").casefold() != "true":
        return {"exit_code": 5, "state": "BLOCKED", "reason": "canary_not_enabled"}
    runtime_revision = resolve_deployed_revision(environ)
    expected_revision = environ.get("ZEP_CANARY_DEPLOYMENT_REVISION", "")
    if (
        not runtime_revision
        or (expected_revision and expected_revision != runtime_revision)
        or runtime_revision != closed_evidence["deployment_revision"]
    ):
        return {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "deployment_revision_mismatch",
        }
    redis_url = environ.get("REDIS_URL", "")
    if not redis_url or redis_url.startswith("memory://"):
        return {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "redis_configuration_required",
        }
    try:
        redis_client = redis_factory(redis_url)
        prior_terminal = _read_journal(
            redis_client,
            key=_terminal_journal_key(run_id),
        )
        if prior_terminal is not None:
            if (
                prior_terminal["state"] != "CLEAN"
                or prior_terminal["run_id"] != run_id
                or prior_terminal["deployment_revision"] != runtime_revision
            ):
                raise _CanaryFailure("canary_journal_invalid")
            return dict(prior_terminal["terminal_result"])
        prior = _read_journal(redis_client)
    except Exception:
        return {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "canary_journal_unavailable",
        }
    gate_result = _journal_gate_result(
        prior,
        run_id=run_id,
        deployment_revision=runtime_revision,
    )
    if gate_result is not None:
        return gate_result

    lock_token = token_hex(16)
    try:
        acquired = redis_client.set(
            LOCK_KEY,
            lock_token,
            nx=True,
            ex=LOCK_TTL_SECONDS,
        )
    except Exception:
        acquired = False
    if not acquired:
        return {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "canary_lock_unavailable",
        }

    try:
        try:
            prior_terminal = _read_journal(
                redis_client,
                key=_terminal_journal_key(run_id),
            )
            if prior_terminal is not None:
                if (
                    prior_terminal["state"] != "CLEAN"
                    or prior_terminal["run_id"] != run_id
                    or prior_terminal["deployment_revision"] != runtime_revision
                ):
                    raise _CanaryFailure("canary_journal_invalid")
                return dict(prior_terminal["terminal_result"])
            prior = _read_journal(redis_client)
        except Exception:
            return {
                "exit_code": 5,
                "state": "BLOCKED",
                "reason": "canary_journal_unavailable",
            }
        gate_result = _journal_gate_result(
            prior,
            run_id=run_id,
            deployment_revision=runtime_revision,
        )
        if gate_result is not None:
            return gate_result
        if prior and prior.get("run_id") == run_id and prior.get("state") != "CLEAN":
            candidate_graph_id = prior.get("graph_id")
            candidate_marker = prior.get("owner_marker")
            if (
                not isinstance(candidate_graph_id, str)
                or not _GRAPH_ID_RE.fullmatch(candidate_graph_id)
                or candidate_marker != owner_marker(candidate_graph_id)
            ):
                return {
                    "exit_code": 5,
                    "state": "BLOCKED",
                    "reason": "canary_journal_unavailable",
                }
            graph_id = candidate_graph_id
            marker = candidate_marker
            resume_state = prior["state"]
        else:
            try:
                graph_id = make_canary_graph_id(utcnow(), token_hex=token_hex)
            except ValueError:
                return {
                    "exit_code": 5,
                    "state": "BLOCKED",
                    "reason": "canary_identity_failed",
                }
            marker = owner_marker(graph_id)
            resume_state = None

        # The credential is deliberately not read until every evidence,
        # revision, journal, and distributed-lock gate above has passed.
        api_key = environ.get("ZEP_API_KEY", "")
        if not isinstance(api_key, str) or not api_key.strip():
            return {
                "exit_code": 5,
                "state": "BLOCKED",
                "reason": "zep_configuration_required",
            }
        try:
            client = client_factory(api_key=api_key, timeout=10.0)
        except Exception:
            return {
                "exit_code": 5,
                "state": "BLOCKED",
                "reason": "zep_client_configuration_failed",
            }

        if resume_state is not None and resume_state != "PREFLIGHTED":
            recovery_reason = {
                "CREATE_REQUESTED": "graph_create_unconfirmed",
                "GRAPH_CREATED": "canary_failed",
                "ONTOLOGY_REQUESTED": "ontology_verification_failed",
                "ONTOLOGY_VERIFIED": "ontology_verification_failed",
                "EPISODE_REQUESTED": "episode_submission_unconfirmed",
                "EPISODE_ACKNOWLEDGED": "episode_processing_failed",
                "EPISODE_PROCESSED": "graph_verification_failed",
                "GRAPH_VERIFIED": "graph_verification_failed",
                "DELETE_REQUESTED": "canary_failed",
                "RECONCILING": "canary_failed",
                "CLEANUP_PENDING": "canary_failed",
            }[resume_state]
            recovered_terminal = _terminal_result(
                exit_code=2,
                reason=recovery_reason,
                graph_id=graph_id,
            )
            cleaned, cleanup_reason, cleanup_journal_ok = _cleanup_graph(
                client=client,
                redis_client=redis_client,
                graph_id=graph_id,
                marker=marker,
                run_id=run_id,
                deployment_revision=runtime_revision,
                terminal_result=recovered_terminal,
                utcnow=utcnow,
                monotonic=monotonic,
                sleep=sleep,
                normal_delete=False,
                allow_delete=resume_state
                not in {"DELETE_REQUESTED", "RECONCILING", "CLEANUP_PENDING"},
            )
            if cleaned and cleanup_journal_ok:
                return recovered_terminal
            return {
                "exit_code": 3,
                "state": "CLEANUP_PENDING",
                "reason": (
                    cleanup_reason
                    if cleanup_journal_ok
                    else "cleanup_journal_unavailable"
                ),
                "graph_id": graph_id,
            }

        try:
            _write_journal(
                redis_client,
                state="PREFLIGHTED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="preflight_complete",
            )
        except _CanaryFailure:
            return {
                "exit_code": 5,
                "state": "BLOCKED",
                "reason": "canary_journal_unavailable",
            }

        started = monotonic()
        failure_reason = "canary_failed"
        try:
            _write_journal(
                redis_client,
                state="CREATE_REQUESTED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="create_requested",
            )
            try:
                client.graph.create(
                    graph_id=graph_id,
                    name=CANARY_GRAPH_NAME,
                    description=marker,
                    request_options=REQUEST_OPTIONS,
                )
            except Exception as exc:
                raise _CanaryFailure("graph_create_unconfirmed") from exc
            _write_journal(
                redis_client,
                state="GRAPH_CREATED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="graph_created",
            )

            _write_journal(
                redis_client,
                state="ONTOLOGY_REQUESTED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="ontology_requested",
            )
            try:
                client.graph.set_ontology(
                    graph_ids=[graph_id],
                    entities={
                        "CanarySensor": CanarySensor,
                        "CanaryHub": CanaryHub,
                    },
                    edges={
                        "ReportsTo": (
                            ReportsTo,
                            [
                                EntityEdgeSourceTarget(
                                    source="CanarySensor",
                                    target="CanaryHub",
                                )
                            ],
                        )
                    },
                    request_options=REQUEST_OPTIONS,
                )
                ontology_response = _safe_read(
                    lambda: client.graph.list_entity_types(
                        graph_id=graph_id,
                        request_options=REQUEST_OPTIONS,
                    ),
                    sleep=sleep,
                )
            except Exception as exc:
                raise _CanaryFailure("ontology_verification_failed") from exc
            if not _ontology_is_exact(ontology_response):
                raise _CanaryFailure("ontology_verification_failed")
            _write_journal(
                redis_client,
                state="ONTOLOGY_VERIFIED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="ontology_verified",
            )

            _write_journal(
                redis_client,
                state="EPISODE_REQUESTED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="episode_requested",
            )
            try:
                acknowledgements = client.graph.add_batch(
                    graph_id=graph_id,
                    episodes=[
                        EpisodeData(
                            data=CANARY_FIXTURE,
                            type="text",
                            source_description=CANARY_SOURCE_DESCRIPTION,
                        )
                    ],
                    request_options=REQUEST_OPTIONS,
                )
            except Exception as exc:
                raise _CanaryFailure("episode_submission_unconfirmed") from exc
            if (
                not isinstance(acknowledgements, Sequence)
                or isinstance(acknowledgements, (str, bytes))
                or len(acknowledgements) != 1
            ):
                raise _CanaryFailure("episode_submission_unconfirmed")
            episode_uuid = getattr(acknowledgements[0], "uuid_", None) or getattr(
                acknowledgements[0], "uuid", None
            )
            if not _is_uuid(episode_uuid):
                raise _CanaryFailure("episode_submission_unconfirmed")
            _write_journal(
                redis_client,
                state="EPISODE_ACKNOWLEDGED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="episode_acknowledged",
            )

            episode_deadline = min(
                started + TOTAL_TIMEOUT_SECONDS,
                monotonic() + EPISODE_TIMEOUT_SECONDS,
            )
            while monotonic() < episode_deadline:
                try:
                    episode = _safe_read(
                        lambda: client.graph.episode.get(
                            uuid_=episode_uuid,
                            request_options=REQUEST_OPTIONS,
                        ),
                        sleep=sleep,
                    )
                except Exception as exc:
                    raise _CanaryFailure("episode_processing_failed") from exc
                if getattr(episode, "uuid_", None) != episode_uuid:
                    raise _CanaryFailure("episode_processing_failed")
                if getattr(episode, "processed", False) is True:
                    break
                sleep(POLL_SECONDS)
            else:
                raise _CanaryFailure("episode_processing_timeout")
            _write_journal(
                redis_client,
                state="EPISODE_PROCESSED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="episode_processed",
            )

            graph_deadline = started + TOTAL_TIMEOUT_SECONDS
            while monotonic() < graph_deadline:
                try:
                    nodes = _safe_read(
                        lambda: client.graph.node.get_by_graph_id(
                            graph_id,
                            limit=100,
                            request_options=REQUEST_OPTIONS,
                        ),
                        sleep=sleep,
                    )
                    edges = _safe_read(
                        lambda: client.graph.edge.get_by_graph_id(
                            graph_id,
                            limit=100,
                            request_options=REQUEST_OPTIONS,
                        ),
                        sleep=sleep,
                    )
                except Exception as exc:
                    raise _CanaryFailure("graph_verification_failed") from exc
                if _graph_is_exact(nodes, edges, episode_uuid):
                    break
                sleep(min(POLL_SECONDS, max(0.0, graph_deadline - monotonic())))
            else:
                raise _CanaryFailure("graph_verification_failed")
            _write_journal(
                redis_client,
                state="GRAPH_VERIFIED",
                run_id=run_id,
                deployment_revision=runtime_revision,
                graph_id=graph_id,
                marker=marker,
                now=utcnow(),
                reason="graph_verified",
            )
            success_terminal = _terminal_result(
                exit_code=0,
                reason="canary_passed",
                graph_id=graph_id,
            )
            cleaned, cleanup_reason, cleanup_journal_ok = _cleanup_graph(
                client=client,
                redis_client=redis_client,
                graph_id=graph_id,
                marker=marker,
                run_id=run_id,
                deployment_revision=runtime_revision,
                terminal_result=success_terminal,
                utcnow=utcnow,
                monotonic=monotonic,
                sleep=sleep,
                normal_delete=True,
            )
            if not cleaned or not cleanup_journal_ok:
                return {
                    "exit_code": 3,
                    "state": "CLEANUP_PENDING",
                    "reason": (
                        cleanup_reason
                        if cleanup_journal_ok
                        else "cleanup_journal_unavailable"
                    ),
                    "graph_id": graph_id,
                }
            return success_terminal
        except _CanaryFailure as exc:
            candidate_reason = str(exc)
            failure_reason = (
                candidate_reason
                if candidate_reason in _FUNCTIONAL_FAILURE_REASONS
                else "canary_failed"
            )
        except Exception:
            failure_reason = "canary_failed"

        _try_write_journal(
            redis_client,
            state="RECONCILING",
            run_id=run_id,
            deployment_revision=runtime_revision,
            graph_id=graph_id,
            marker=marker,
            now=utcnow(),
            reason=failure_reason,
        )
        failure_terminal = _terminal_result(
            exit_code=2,
            reason=failure_reason,
            graph_id=graph_id,
        )
        try:
            cleaned, cleanup_reason, cleanup_journal_ok = _cleanup_graph(
                client=client,
                redis_client=redis_client,
                graph_id=graph_id,
                marker=marker,
                run_id=run_id,
                deployment_revision=runtime_revision,
                terminal_result=failure_terminal,
                utcnow=utcnow,
                monotonic=monotonic,
                sleep=sleep,
                normal_delete=False,
            )
        except Exception:
            return {
                "exit_code": 3,
                "state": "CLEANUP_PENDING",
                "reason": "cleanup_journal_unavailable",
                "graph_id": graph_id,
            }
        if cleaned and cleanup_journal_ok:
            return failure_terminal
        if cleaned and not cleanup_journal_ok:
            return {
                "exit_code": 3,
                "state": "CLEANUP_PENDING",
                "reason": "cleanup_journal_unavailable",
                "graph_id": graph_id,
            }
        return {
            "exit_code": 3,
            "state": "CLEANUP_PENDING",
            "reason": (
                cleanup_reason if cleanup_journal_ok else "cleanup_journal_unavailable"
            ),
            "graph_id": graph_id,
        }
    finally:
        _release_lock(redis_client, lock_token)

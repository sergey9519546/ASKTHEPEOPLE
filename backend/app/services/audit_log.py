"""Append-only audit log for cross-aggregate state transitions.

Required by ADR-0012 (canonical persistence), the incident-response doc
(affected-run lookup), and state-machines.md:405-406 — "every transition
records actor, reason, timestamp, prior version, and resulting version."

Today this writes JSONL to ``UPLOAD_FOLDER/audit/audit.log`` with atomic
appends (open mode ``"a"`` is atomic for line-sized writes on POSIX, and on
Windows for the single-writer web process). The interface is deliberately
shaped to map 1:1 onto a future ``audit_events`` PostgreSQL table when gate 3
lands — same column names, same semantics — so the migration is a storage
swap, not a redesign.

Guarantees:
- **Append-only.** This module exposes no update or delete. The file is
  opened in append mode; there is no truncation or rewrite path.
- **Best-effort, never raises.** An audit failure must not break the
  operation it was recording; every public call swallows OSError and logs.
  (Auditing is observability, not a transaction participant until gate 3's
  outbox lands.)
- **PII-safe.** ``before``/``after`` snapshots are caller-supplied summaries
  (status / version / counts), never request bodies or source content. The
  incident-response doc and the no-body-logging policy both depend on this.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('askthepeople.audit')

# Single write lock across the process. The web runs --workers 1; under that
# topology the GIL already serializes appends, but the lock keeps the JSONL
# line-integrity guarantee explicit and survives a future move to a thread
# pool. Cross-process coordination is a gate-3 concern (PostgreSQL).
_write_lock = threading.Lock()


def _audit_path() -> str:
    """Resolve the audit-log path under UPLOAD_FOLDER."""
    return os.path.join(Config.UPLOAD_FOLDER, "audit", "audit.log")


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(_audit_path()), exist_ok=True)


def record_event(
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    reason: Optional[str] = None,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one audit event. Never raises.

    Args:
        action: What happened — a stable verb (``project.created``,
            ``simulation.status_changed``, ``task.failed``, etc.).
        entity_type: The aggregate kind (``project``, ``simulation``,
            ``task``, ``export``).
        entity_id: The aggregate's identifier.
        actor: Who caused it (``system``, a future user id, ``worker``).
        reason: Human-readable reason (required for admin overrides per
            state-machines.md:34).
        before / after: Small summary snapshots of the prior and resulting
            state (status, version, counts). Keep these PII-free.
        metadata: Optional structured detail.
    """
    event = {
        # ISO-8601 with explicit timezone — required by state-machines.md:31.
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor": actor,
        "reason": reason,
        "before": _safe_summary(before),
        "after": _safe_summary(after),
        "metadata": metadata or {},
    }
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    try:
        with _write_lock:
            _ensure_dir()
            with open(_audit_path(), "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except OSError as exc:
        # Best-effort: log and continue. The operation being audited must
        # not fail because the audit log was unwritable.
        logger.warning("audit_log append failed for %s/%s: %s", entity_type, entity_id, exc)


def _safe_summary(snapshot: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Drop any oversized or non-serializable value from a snapshot so a bad
    caller cannot bloat the log or crash the append."""
    if snapshot is None:
        return None
    safe: Dict[str, Any] = {}
    for key, value in snapshot.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, dict):
            safe[key] = _safe_summary(value)
        elif isinstance(value, (list, tuple, set)):
            safe[key] = list(value)[:20]
        else:
            safe[key] = str(value)[:200]
    return safe


def find_events(
    *,
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Read-side lookup for incident response (``INCIDENT_RESPONSE.md``
    affected-run lookup). Returns matching events newest-first.

    Scans the JSONL file. This is O(lines) and intended for incident-time
    inspection, not hot-path reads; when gate 3 lands a PostgreSQL
    ``audit_events`` table with indexes this becomes an indexed query.
    """
    matches: List[Dict[str, Any]] = []
    try:
        with _write_lock:
            path = _audit_path()
            if not os.path.exists(path):
                return []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entity_id and event.get("entity_id") != entity_id:
                        continue
                    if entity_type and event.get("entity_type") != entity_type:
                        continue
                    if action and event.get("action") != action:
                        continue
                    matches.append(event)
                    if len(matches) >= limit:
                        break
    except OSError as exc:
        logger.warning("audit_log read failed: %s", exc)
        return []
    # Newest first — the file is append-order (oldest first).
    matches.reverse()
    return matches


def find_affected_runs(entity_id: str, entity_type: str = "simulation") -> List[Dict[str, Any]]:
    """Convenience: every audit event touching one entity — the input to the
    incident-response "find every run affected by X" procedure."""
    return find_events(entity_id=entity_id, entity_type=entity_type, limit=1000)

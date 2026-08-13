"""PostgreSQL-backed repository for the durable run control plane.

Connects the pure-domain kernel in ``app/domain/run_attempt.py`` to the
``runs``, ``run_stages``, and ``run_events`` tables created by migration
``a1b2c3d4e5f6``. Follows the same raw-SQL-via-``text()`` pattern as
``project_repository.py`` — the alembic migration is the authoritative
schema, and the repository maps rows to/from the domain ``RunSnapshot``
model.

The repository is opt-in (same as ``ProjectRepository``): it activates
only when ``Config.USE_SUPABASE_PERSISTENCE`` is ``True``. Until then the
domain kernel is exercised through its pure functions without persistence.

Key operations:
- ``create_run`` — insert a new run snapshot at DRAFT, return the row.
- ``get_run`` — load a run by its physical UUID or public ``run_…`` id.
- ``apply_transition`` — optimistic-concurrency state transition: load the
  current snapshot, call the domain transition policy, and CAS-write the
  new state + version. Records a ``run_events`` row in the same transaction.
- ``list_runs`` — scoped by organization/workspace.

All writes use ``version`` as the optimistic-concurrency guard: the UPDATE
includes ``WHERE id = :id AND version = :expected_version``, and the row
count must be 1 — otherwise the transition contended and the caller retries.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine

from ..config import Config
from ..domain.identifiers import new_public_id, new_uuid7
from ..domain.run_attempt import (
    RunCommandKind,
    RunGuardFacts,
    RunSnapshot,
    RunState,
    decide_run_transition,
)

logger = logging.getLogger(__name__)


def _ensure_psycopg_driver(url: str) -> str:
    """Same conversion as ProjectRepository — force psycopg3 driver."""
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunRepository:
    """PostgreSQL repository for durable runs, stages, and events."""

    _engine: Optional[Engine] = None

    @classmethod
    def _get_engine(cls) -> Engine:
        if cls._engine is None:
            database_url = Config.DATABASE_URL
            if not database_url or database_url.startswith("sqlite"):
                raise RuntimeError("canonical_store_not_configured")
            cls._engine = create_engine(
                _ensure_psycopg_driver(database_url), future=True
            )
        return cls._engine

    # --- create --- #

    @classmethod
    def create_run(
        cls,
        *,
        organization_id: UUID,
        workspace_id: UUID,
        run_config_id: UUID,
        parent_run_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Insert a new run at DRAFT state, return the row as a dict."""
        run_id = new_uuid7()
        now = _utc_now()
        engine = cls._get_engine()
        with engine.begin() as conn:
            # Public identity is independent from the physical UUIDv7. This
            # prevents the caller-visible alias from leaking row identity.
            public_id = new_public_id("run", run_id)
            conn.execute(text("""
                INSERT INTO dw_runs (
                    id, public_id, organization_id, workspace_id,
                    run_config_id, parent_run_id, state, version,
                    current_stage_code, stop_fence,
                    human_respondents, is_forecast, output_origin,
                    created_at, updated_at
                ) VALUES (
                    :id, :public_id, :org_id, :ws_id,
                    :cfg_id, :parent_id, :state, :version,
                    NULL, 0,
                    0, false, 'synthetic',
                    :now, :now
                )
            """), {
                "id": run_id,
                "public_id": public_id,
                "org_id": organization_id,
                "ws_id": workspace_id,
                "cfg_id": run_config_id,
                "parent_id": parent_run_id,
                "state": RunState.DRAFT.value,
                "version": 1,
                "now": now,
            })
        return cls.get_run(run_id)

    # --- read --- #

    @classmethod
    def get_run(cls, run_id: UUID) -> Optional[Dict[str, Any]]:
        """Load a run by its physical UUID."""
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_runs WHERE id = :id
            """), {"id": run_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def get_run_by_public_id(cls, public_id: str) -> Optional[Dict[str, Any]]:
        """Load a run by its public ``run_…`` identifier."""
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_runs WHERE public_id = :public_id
            """), {"public_id": public_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def list_runs(
        cls, *, organization_id: UUID, workspace_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List runs scoped by organization (and optionally workspace)."""
        engine = cls._get_engine()
        with engine.connect() as conn:
            if workspace_id:
                rows = conn.execute(text("""
                    SELECT * FROM dw_runs
                    WHERE organization_id = :org_id AND workspace_id = :ws_id
                    ORDER BY created_at DESC LIMIT :limit
                """), {"org_id": organization_id, "ws_id": workspace_id, "limit": limit})
            else:
                rows = conn.execute(text("""
                    SELECT * FROM dw_runs
                    WHERE organization_id = :org_id
                    ORDER BY created_at DESC LIMIT :limit
                """), {"org_id": organization_id, "limit": limit})
            return [dict(r) for r in rows.mappings()]

    # --- transition (the core optimistic-concurrency write) --- #

    @classmethod
    def apply_transition(
        cls,
        run_id: UUID,
        *,
        command: RunCommandKind,
        guards: RunGuardFacts,
        actor_type: str,
        actor_id: UUID,
        idempotency_key: str,
        reason_code: str,
    ) -> Dict[str, Any]:
        """Apply a domain transition with optimistic concurrency.

        Loads the current snapshot, calls ``decide_run_transition`` (the pure
        domain policy — no target_state; the command determines the target),
        and CAS-writes the new state + version. Records a ``run_events`` row
        in the same transaction. Raises if the version changed (concurrent
        write) or the domain policy rejects the transition.
        """
        engine = cls._get_engine()
        with engine.begin() as conn:
            # Lock the row for the duration of the transaction.
            current = conn.execute(text("""
                SELECT * FROM dw_runs WHERE id = :id FOR UPDATE
            """), {"id": run_id}).mappings().first()
            if not current:
                raise ValueError("run_not_found")

            current_dict = dict(current)
            from_state = RunState(current_dict["state"])
            expected_version = current_dict["version"]

            # Build the snapshot for the domain policy.
            snapshot = RunSnapshot(
                id=current_dict["id"],
                public_id=current_dict["public_id"],
                organization_id=current_dict["organization_id"],
                workspace_id=current_dict["workspace_id"],
                run_config_id=current_dict["run_config_id"],
                parent_run_id=current_dict.get("parent_run_id"),
                state=from_state,
                version=expected_version,
                current_stage_code=None,
                stop_fence=current_dict.get("stop_fence", 0),
            )

            # Run the pure domain transition policy. The command determines
            # the target state and event type — no caller-supplied target.
            transition = decide_run_transition(
                snapshot=snapshot,
                command=command,
                guards=guards,
            )

            new_version = transition.next_version
            now = _utc_now()

            # Optimistic-concurrency CAS write.
            result = conn.execute(text("""
                UPDATE dw_runs SET
                    state = :new_state,
                    version = :new_version,
                    updated_at = :now
                WHERE id = :id AND version = :expected_version
            """), {
                "id": run_id,
                "new_state": transition.to_state.value,
                "new_version": new_version,
                "expected_version": expected_version,
                "now": now,
            })
            if result.rowcount != 1:
                raise RuntimeError("run_version_conflict")

            # Record the transition event in the same transaction.
            event_id = new_uuid7()
            conn.execute(text("""
                INSERT INTO dw_run_events (
                    id, run_id, command, from_state, to_state,
                    next_version, event_type,
                    actor_type, actor_id,
                    idempotency_key, reason_code,
                    guard_payload, occurred_at
                ) VALUES (
                    :id, :run_id, :command, :from_state, :to_state,
                    :next_version, :event_type,
                    :actor_type, :actor_id,
                    :idempotency_key, :reason_code,
                    :guard_payload, :occurred_at
                )
            """), {
                "id": event_id,
                "run_id": run_id,
                "command": transition.command.value,
                "from_state": transition.from_state.value,
                "to_state": transition.to_state.value,
                "next_version": new_version,
                "event_type": transition.event_type.value,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "idempotency_key": idempotency_key,
                "reason_code": reason_code,
                "guard_payload": json.dumps({}, default=str),
                "occurred_at": now,
            })

            # Return the updated row.
            updated = conn.execute(text("""
                SELECT * FROM dw_runs WHERE id = :id
            """), {"id": run_id}).mappings().first()
            return dict(updated)

    # --- events (cursor-based read for reconnect) --- #

    @classmethod
    def get_run_events(
        cls, run_id: UUID, *, after_version: int = 0, limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Cursor-based event read: events after ``after_version``, oldest
        first. Used by the WebSocket reconnect path to catch up on missed
        transitions."""
        engine = cls._get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT * FROM dw_run_events
                WHERE run_id = :run_id AND next_version > :after_version
                ORDER BY next_version ASC LIMIT :limit
            """), {"run_id": run_id, "after_version": after_version, "limit": limit})
            return [dict(r) for r in rows.mappings()]

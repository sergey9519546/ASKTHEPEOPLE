"""PostgreSQL-backed repository for the path aggregate (Task 6).

Connects the pure-domain kernel in ``app/domain/possible_path.py`` to the
``dw_path_sets``, ``dw_paths``, and ``dw_path_set_reviews`` tables created by
migration ``b2c3d4e5f6a7``. Same raw-SQL pattern as RunRepository /
SourceRepository.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config import Config
from ..domain.identifiers import new_public_id, new_uuid7

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PathRepository:
    """PostgreSQL repository for path sets, paths, and reviews."""

    _engine: Optional[Engine] = None

    @classmethod
    def _get_engine(cls) -> Engine:
        if cls._engine is None:
            database_url = Config.DATABASE_URL
            if not database_url or database_url.startswith("sqlite"):
                raise RuntimeError("canonical_store_not_configured")
            from .run_repository import _ensure_psycopg_driver
            from sqlalchemy import create_engine
            cls._engine = create_engine(
                _ensure_psycopg_driver(database_url), future=True
            )
        return cls._engine

    # --- path set --- #

    @classmethod
    def create_path_set(
        cls,
        *,
        organization_id: UUID,
        workspace_id: UUID,
        run_id: UUID,
        status: str,
        content_sha256: str,
    ) -> Dict[str, Any]:
        ps_id = new_uuid7()
        now = _utc_now()
        public_id = new_public_id("path_set", ps_id)
        engine = cls._get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dw_path_sets (
                    id, public_id, organization_id, workspace_id,
                    run_id, status, content_sha256, version,
                    created_at, updated_at
                ) VALUES (
                    :id, :public_id, :org_id, :ws_id,
                    :run_id, :status, :content_sha256, 1,
                    :now, :now
                )
            """), {
                "id": ps_id, "public_id": public_id,
                "org_id": organization_id, "ws_id": workspace_id,
                "run_id": run_id, "status": status,
                "content_sha256": content_sha256, "now": now,
            })
        return cls.get_path_set(ps_id)

    @classmethod
    def get_path_set(cls, path_set_id: UUID) -> Optional[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_path_sets WHERE id = :id
            """), {"id": path_set_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def get_path_set_by_public_id(cls, public_id: str) -> Optional[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_path_sets WHERE public_id = :public_id
            """), {"public_id": public_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def list_path_sets_for_run(cls, run_id: UUID) -> List[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT * FROM dw_path_sets WHERE run_id = :run_id
                ORDER BY created_at DESC
            """), {"run_id": run_id})
            return [dict(r) for r in rows.mappings()]

    # --- individual paths --- #

    @classmethod
    def create_path(
        cls,
        *,
        path_set_id: UUID,
        organization_id: UUID,
        workspace_id: UUID,
        run_id: UUID,
        display_code: str,
        title: str,
        branch_trigger: str,
        bounded_rationale: str,
        scenario_frame: str,
        content_json: Dict[str, Any],
        content_sha256: str,
        distinctness_sha256: str,
    ) -> Dict[str, Any]:
        path_id = new_uuid7()
        now = _utc_now()
        public_id = new_public_id("path", path_id)
        # Semantic lineage is server-issued and independent of the physical
        # row ID. The full revision/lineage resolver remains behind the Task
        # 6 persistence gate; this transition repository must never derive a
        # semantic alias from a physical UUID. The semantic namespace is
        # ``path_sem_`` (Task 6 §"Semantic lineage identity"), not the
        # ``path_set_`` public-ID namespace.
        semantic_id = f"path_sem_{new_uuid7().hex}"
        engine = cls._get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dw_paths (
                    id, public_id, semantic_id,
                    organization_id, workspace_id,
                    run_id, path_set_id,
                    display_code, title,
                    branch_trigger, bounded_rationale, scenario_frame,
                    content_json, content_sha256, distinctness_sha256,
                    origin, created_at
                ) VALUES (
                    :id, :public_id, :semantic_id,
                    :org_id, :ws_id,
                    :run_id, :path_set_id,
                    :display_code, :title,
                    :branch_trigger, :bounded_rationale, :scenario_frame,
                    CAST(:content_json AS JSON), :content_sha256, :distinctness_sha256,
                    'GENERATED_GENERATED', :now
                )
            """), {
                "id": path_id, "public_id": public_id, "semantic_id": semantic_id,
                "org_id": organization_id, "ws_id": workspace_id,
                "run_id": run_id, "path_set_id": path_set_id,
                "display_code": display_code, "title": title,
                "branch_trigger": branch_trigger,
                "bounded_rationale": bounded_rationale,
                "scenario_frame": scenario_frame,
                "content_json": json.dumps(content_json),
                "content_sha256": content_sha256,
                "distinctness_sha256": distinctness_sha256,
                "now": now,
            })
        return cls.get_path(path_id)

    @classmethod
    def get_path(cls, path_id: UUID) -> Optional[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_paths WHERE id = :id
            """), {"id": path_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def list_paths_for_set(cls, path_set_id: UUID) -> List[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT * FROM dw_paths WHERE path_set_id = :ps_id
                ORDER BY display_code ASC
            """), {"ps_id": path_set_id})
            return [dict(r) for r in rows.mappings()]

    # --- path set review --- #

    @classmethod
    def create_review(
        cls,
        *,
        path_set_id: UUID,
        reviewer_actor_id: UUID,
        items: List[Dict[str, Any]],
        content_sha256: str,
    ) -> Dict[str, Any]:
        review_id = new_uuid7()
        now = _utc_now()
        engine = cls._get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dw_path_set_reviews (
                    id, path_set_id, reviewer_actor_id,
                    items_json, content_sha256, reviewed_at
                ) VALUES (
                    :id, :ps_id, :reviewer_id,
                    CAST(:items_json AS JSON), :content_sha256, :reviewed_at
                )
            """), {
                "id": review_id, "ps_id": path_set_id,
                "reviewer_id": reviewer_actor_id,
                "items_json": json.dumps(items),
                "content_sha256": content_sha256,
                "reviewed_at": now,
            })
            row = conn.execute(text("""
                SELECT * FROM dw_path_set_reviews WHERE id = :id
            """), {"id": review_id}).mappings().first()
            return dict(row)

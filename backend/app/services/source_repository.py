"""PostgreSQL-backed repository for the source-ingestion aggregate.

Connects the pure-domain kernel in ``app/domain/source_ingestion.py`` to the
``sources``, ``source_versions``, ``source_segments``, and ``source_candidates``
tables created by migration ``a1b2c3d4e5f6``. Follows the same raw-SQL pattern
as ``project_repository.py`` and ``run_repository.py``.

Opt-in via ``Config.USE_SUPABASE_PERSISTENCE``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine

from ..config import Config
from ..domain.source_ingestion import SourceIngestionState

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceRepository:
    """PostgreSQL repository for the source-ingestion aggregate."""

    _engine: Optional[Engine] = None

    @classmethod
    def _get_engine(cls) -> Engine:
        if cls._engine is None:
            database_url = Config.DATABASE_URL
            if not database_url or database_url.startswith("sqlite"):
                raise RuntimeError("canonical_store_not_configured")
            from .run_repository import _ensure_psycopg_driver
            cls._engine = create_engine(
                _ensure_psycopg_driver(database_url), future=True
            )
        return cls._engine

    # --- source --- #

    @classmethod
    def create_source(
        cls,
        *,
        organization_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        display_name: str,
        created_by_actor_id: UUID,
    ) -> Dict[str, Any]:
        """Insert a new source aggregate at version 1."""
        source_id = uuid4()
        now = _utc_now()
        public_id = f"src_{source_id.hex}"
        engine = cls._get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dw_sources (
                    id, public_id, organization_id, workspace_id, project_id,
                    display_name, current_version_id, version,
                    created_by_actor_id, created_at, updated_at
                ) VALUES (
                    :id, :public_id, :org_id, :ws_id, :project_id,
                    :display_name, NULL, 1,
                    :actor_id, :now, :now
                )
            """), {
                "id": source_id, "public_id": public_id,
                "org_id": organization_id, "ws_id": workspace_id,
                "project_id": project_id, "display_name": display_name,
                "actor_id": created_by_actor_id, "now": now,
            })
        return cls.get_source(source_id)

    @classmethod
    def get_source(cls, source_id: UUID) -> Optional[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_sources WHERE id = :id
            """), {"id": source_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def get_source_by_public_id(cls, public_id: str) -> Optional[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_sources WHERE public_id = :public_id
            """), {"public_id": public_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def list_sources(
        cls, *, organization_id: UUID, workspace_id: UUID, project_id: UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT * FROM dw_sources
                WHERE organization_id = :org_id
                  AND workspace_id = :ws_id
                  AND project_id = :project_id
                ORDER BY created_at DESC LIMIT :limit
            """), {
                "org_id": organization_id, "ws_id": workspace_id,
                "project_id": project_id, "limit": limit,
            })
            return [dict(r) for r in rows.mappings()]

    # --- source version --- #

    @classmethod
    def create_source_version(
        cls,
        *,
        source_id: UUID,
        organization_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        version_number: int,
        state: SourceIngestionState,
        original_filename_display: str,
        declared_media_type: str,
        created_by_actor_id: UUID,
    ) -> Dict[str, Any]:
        """Insert a new source version (the upload/scan/parse/review record)."""
        version_id = uuid4()
        now = _utc_now()
        public_id = f"srcv_{version_id.hex}"
        engine = cls._get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dw_source_versions (
                    id, public_id, organization_id, workspace_id, project_id,
                    source_id, version_number, state,
                    original_filename_display, declared_media_type,
                    detected_media_type, raw_object_ref, processed_object_ref,
                    raw_byte_length, normalized_byte_length, normalized_token_count,
                    scanner_name, scanner_version, scanner_definitions_version,
                    parser_name, parser_version,
                    processing_fence, deletion_fence,
                    version, created_by_actor_id, created_at, updated_at
                ) VALUES (
                    :id, :public_id, :org_id, :ws_id, :project_id,
                    :source_id, :version_number, :state,
                    :filename, :media_type,
                    NULL, NULL, NULL,
                    NULL, NULL, NULL,
                    NULL, NULL, NULL,
                    NULL, NULL,
                    0, 0,
                    1, :actor_id, :now, :now
                )
            """), {
                "id": version_id, "public_id": public_id,
                "org_id": organization_id, "ws_id": workspace_id,
                "project_id": project_id,
                "source_id": source_id, "version_number": version_number,
                "state": state.value,
                "filename": original_filename_display,
                "media_type": declared_media_type,
                "actor_id": created_by_actor_id, "now": now,
            })
            # Point the source's current_version_id at the new version.
            conn.execute(text("""
                UPDATE dw_sources SET current_version_id = :version_id, updated_at = :now
                WHERE id = :source_id
            """), {"version_id": version_id, "source_id": source_id, "now": now})
        return cls.get_source_version(version_id)

    @classmethod
    def get_source_version(cls, version_id: UUID) -> Optional[Dict[str, Any]]:
        engine = cls._get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM dw_source_versions WHERE id = :id
            """), {"id": version_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def update_source_version_state(
        cls,
        version_id: UUID,
        *,
        new_state: SourceIngestionState,
        expected_version: int,
        **optional_fields,
    ) -> Dict[str, Any]:
        """CAS-update a source version's state with optimistic concurrency.

        Additional fields (scanner_name, parser_name, raw_object_ref, etc.)
        can be supplied as keyword args and are written alongside the state.
        """
        engine = cls._get_engine()
        now = _utc_now()
        # Build the SET clause from the optional fields.
        set_parts = ["state = :new_state", "version = :new_version", "updated_at = :now"]
        params: Dict[str, Any] = {
            "id": version_id, "new_state": new_state.value,
            "new_version": expected_version + 1,
            "expected_version": expected_version, "now": now,
        }
        field_map = {
            "detected_media_type", "raw_object_ref", "processed_object_ref",
            "raw_byte_length", "normalized_byte_length", "normalized_token_count",
            "scanner_name", "scanner_version", "scanner_definitions_version",
            "parser_name", "parser_version",
            "processing_fence", "deletion_fence",
        }
        for key, value in optional_fields.items():
            if key in field_map:
                set_parts.append(f"{key} = :{key}")
                params[key] = value

        set_clause = ", ".join(set_parts)
        with engine.begin() as conn:
            result = conn.execute(text(f"""
                UPDATE dw_source_versions SET {set_clause}
                WHERE id = :id AND version = :expected_version
            """), params)
            if result.rowcount != 1:
                raise RuntimeError("source_version_conflict")
            row = conn.execute(text("""
                SELECT * FROM dw_source_versions WHERE id = :id
            """), {"id": version_id}).mappings().first()
            return dict(row)

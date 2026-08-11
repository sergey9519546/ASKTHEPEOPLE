"""SQLAlchemy-backed project repository.

This is the canonical-store implementation per ADR-0012. The class
mirrors `models.project.ProjectManager`'s public API (create_project,
save_project, get_project, list_projects, delete_project, save_file_to_project,
get_project_files, save_extracted_text, get_extracted_text) so the rest of
the codebase keeps its call sites unchanged. Each method returns the same
shapes (a `Project` dataclass, a file-metadata dict, a list of file paths,
plain text) — the storage substrate underneath is the only thing that differs.

The repository is opt-in: `ProjectManager` falls through to the
filesystem path unless `Config.USE_SUPABASE_PERSISTENCE` is `True`. In
production that flag is `True` and DATABASE_URL points at Supabase
Postgres; locally the same code runs against the docker container the
README tells you to start.

Why raw SQL via SQLAlchemy `text()` rather than ORM models:

* The alembic migration `384c98f88d53_initial_schema.py` is the
  authoritative schema; the ORM models in `app.db.schema` are a
  partial stub that does not match the migration (e.g. the migration
  uses Integer autoincrement primary keys + `project_id` varchar,
  the ORM uses Uuid + `organization_id`). Resolving the drift is a
  follow-up PR. In the meantime, raw SQL keeps this repository
  unambiguous about which schema it is talking to, and a future
  validator can lint every query against the migration.
* The repository is small enough (7 queries) that an ORM buys
  little. Readability is the priority.
"""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, bindparam, create_engine, text
from sqlalchemy.engine import Engine

from ..config import Config
from ..models.project import Project, ProjectStatus
from ..utils.task_retry import is_retryable_task_exception
from .supabase_client import StorageUnavailable, is_storage_configured, storage

logger = logging.getLogger(__name__)


class CanonicalSourceReadError(RuntimeError):
    """Sanitized canonical-object read failure with an explicit retry class."""

    def __init__(self, *, retryable: bool) -> None:
        super().__init__("canonical_source_read_failed")
        self.retryable = retryable


def _storage_status_code(exc: BaseException) -> Optional[int]:
    """Normalize provider status fields without relying on provider messages."""
    candidates = (
        getattr(exc, "status_code", None),
        getattr(exc, "status", None),
        getattr(getattr(exc, "response", None), "status_code", None),
        getattr(getattr(exc, "response", None), "status", None),
    )
    for value in candidates:
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _storage_object_is_missing(exc: BaseException) -> bool:
    status = _storage_status_code(exc)
    if status == 404:
        return True
    code = str(getattr(exc, "code", "")).casefold()
    return code in {"404", "notfound", "not_found", "nosuchkey", "nosuchobject"}


def _storage_read_is_retryable(exc: BaseException) -> bool:
    status = _storage_status_code(exc)
    if status is not None:
        return status == 429 or status >= 500
    return is_retryable_task_exception(exc)


# Storage keys are operator-scoped per ADR-0012:
#   core/{env}/{project_id}/approved/{safe_filename}
# `env` is the deployment environment so a single Supabase project can host
# staging + prod without cross-talk; locally it is the FLASK_ENV value
# (default "dev"). Tenant isolation (the org/workspace layer per data-model.md)
# is a follow-up PR; today the project_id is the only scope we have.
def _approved_key(project_id: str, safe_filename: str, *, env: Optional[str] = None) -> str:
    environment = env or os.environ.get("FLASK_ENV", "dev")
    return f"core/{environment}/{project_id}/approved/{safe_filename}"


class ProjectRepository:
    """Postgres + Supabase-Storage backed implementation of ProjectManager.

    All public methods are classmethods so callers do not need to
    instantiate. The class is stateless beyond holding a single
    SQLAlchemy `Engine` keyed on `Config.DATABASE_URL` — the engine
    is process-wide and connection-pooled internally.
    """

    _engine: Optional[Engine] = None

    @classmethod
    def _get_engine(cls) -> Engine:
        if cls._engine is None:
            database_url = Config.DATABASE_URL
            if not database_url:
                raise RuntimeError(
                    "Config.DATABASE_URL is not set; cannot use the canonical store."
                )
            # SQLAlchemy defaults to psycopg2 for `postgresql://` URLs.
            # This project uses psycopg3 (`psycopg[binary]`), so we
            # explicitly pick the psycopg dialect when the URL does not
            # already specify one. The conversion matches what
            # `app.db.get_engine` would do for the same URL.
            if database_url.startswith("postgresql://") and "+" not in database_url.split("://", 1)[0]:
                database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
            elif database_url.startswith("postgres://"):
                database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
            cls._engine = create_engine(database_url, future=True)
        return cls._engine

    @staticmethod
    def _graph_build_delivery_lock_key(project_id: str, task_id: str) -> int:
        """Map one delivery identity to PostgreSQL's signed bigint keyspace."""
        digest = hashlib.sha256(
            f"{project_id}\0{task_id}".encode("utf-8")
        ).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    @classmethod
    @contextmanager
    def graph_build_delivery_fence(cls, project_id: str, task_id: str):
        """Hold one session-level advisory lock across the Zep mutation."""
        engine = cls._get_engine()
        if getattr(engine.dialect, "name", None) != "postgresql":
            raise RuntimeError("canonical_graph_delivery_fence_requires_postgresql")

        lock_key = cls._graph_build_delivery_lock_key(project_id, task_id)
        connection = engine.connect()
        acquired = False
        try:
            connection.execute(
                text("SELECT pg_advisory_lock(:lock_key)"),
                {"lock_key": lock_key},
            )
            acquired = True
            yield
        finally:
            if acquired:
                try:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:lock_key)"),
                        {"lock_key": lock_key},
                    )
                except Exception:
                    logger.error(
                        "canonical graph delivery advisory unlock failed",
                        extra={"privacy_safe": True},
                    )
            try:
                connection.close()
            except Exception:
                logger.error(
                    "canonical graph delivery connection close failed",
                    extra={"privacy_safe": True},
                )

    # ------------------------------------------------------------------
    # Schema-aware helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_project(row) -> Project:
        """Translate a SQL row into the legacy `Project` dataclass.

        `row` is a SQLAlchemy Row mapping (dict-like). The shape of
        the row must match the SELECT in `get_project` / `list_projects`.
        """
        # Row supports both mapping-style and attribute access; use
        # mapping access for clarity.
        try:
            status_value = row["status"]
        except (KeyError, IndexError):
            status_value = ProjectStatus.CREATED.value
        try:
            status = ProjectStatus(status_value)
        except ValueError:
            status = ProjectStatus.CREATED

        def _str(value) -> str:
            if value is None:
                return ""
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)

        return Project(
            project_id=row["project_id"],
            name=row.get("name") or "Unnamed Project",
            status=status,
            created_at=_str(row.get("created_at")),
            updated_at=_str(row.get("updated_at")),
            files=[],  # populated by get_project_files on demand
            total_text_length=int(row.get("total_text_length") or 0),
            ontology=None,  # ontology now lives in the `ontologies` table
            analysis_summary=row.get("analysis_summary"),
            graph_id=row.get("graph_id"),
            graph_build_task_id=row.get("graph_build_task_id"),
            simulation_requirement=row.get("simulation_requirement"),
            chunk_size=int(row.get("chunk_size") or 500),
            chunk_overlap=int(row.get("chunk_overlap") or 50),
            error=row.get("error"),
        )

    @staticmethod
    def _load_latest_completed_ontology(conn, project_id: int) -> Optional[Dict[str, Any]]:
        """Load the latest ontology using the integer FK in the legacy migration."""
        result = conn.execute(
            text(
                """
                SELECT result_json
                FROM ontologies
                WHERE project_id = :project_id
                  AND status = :status
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """
            ).columns(result_json=JSON),
            {"project_id": project_id, "status": "completed"},
        ).scalar_one_or_none()
        return result if isinstance(result, dict) else None

    @staticmethod
    def _persist_completed_ontology(
        conn,
        project_id: str,
        ontology: Dict[str, Any],
        ontology_task_id: Optional[str],
    ) -> None:
        """Persist an ontology against ``projects.id`` in the canonical schema."""
        internal_project_id = conn.execute(
            text("SELECT id FROM projects WHERE project_id = :project_id"),
            {"project_id": project_id},
        ).scalar_one_or_none()
        if internal_project_id is None:
            raise LookupError("canonical_project_not_found")

        latest_ontology = conn.execute(
            text(
                """
                SELECT result_json
                FROM ontologies
                WHERE project_id = :project_id
                  AND status = :status
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """
            ).columns(result_json=JSON),
            {"project_id": internal_project_id, "status": "completed"},
        ).scalar_one_or_none()
        if latest_ontology == ontology:
            return
        if not ontology_task_id:
            raise ValueError("canonical_ontology_producer_missing")

        now = datetime.now()
        statement = text(
            """
            INSERT INTO ontologies (
                project_id, task_id, status, result_json, error,
                created_at, updated_at
            ) VALUES (
                :project_id, :task_id, :status, :result_json, :error,
                :created_at, :updated_at
            )
            """
        ).bindparams(bindparam("result_json", type_=JSON))
        conn.execute(
            statement,
            {
                "project_id": internal_project_id,
                "task_id": ontology_task_id,
                "status": "completed",
                "result_json": ontology,
                "error": None,
                "created_at": now,
                "updated_at": now,
            },
        )

    # ------------------------------------------------------------------
    # Public API — mirrors ProjectManager
    # ------------------------------------------------------------------

    @classmethod
    def create_project(cls, name: str = "Unnamed Project") -> Project:
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now()
        with cls._get_engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO projects (
                        project_id, name, status,
                        created_at, updated_at,
                        total_text_length, chunk_size, chunk_overlap
                    ) VALUES (
                        :project_id, :name, :status,
                        :created_at, :updated_at,
                        :total_text_length, :chunk_size, :chunk_overlap
                    )
                    """
                ),
                {
                    "project_id": project_id,
                    "name": name,
                    "status": ProjectStatus.CREATED.value,
                    "created_at": now,
                    "updated_at": now,
                    "total_text_length": 0,
                    "chunk_size": 500,
                    "chunk_overlap": 50,
                },
            )
            row = conn.execute(
                text(
                    """
                    SELECT project_id, name, status,
                           created_at, updated_at,
                           total_text_length, chunk_size, chunk_overlap,
                           analysis_summary, simulation_requirement,
                           graph_id, graph_build_task_id, error
                    FROM projects WHERE project_id = :project_id
                    """
                ),
                {"project_id": project_id},
            ).mappings().one()
        logger.info("Created project %s in canonical store", project_id)
        return cls._row_to_project(row)

    @classmethod
    def save_project(
        cls,
        project: Project,
        *,
        _audit_status_change: bool = True,
        _ontology_task_id: Optional[str] = None,
    ) -> None:
        """Upsert the project row. Atomic per ADR-0012; no partial reads."""
        # The dataclass stores files + ontology as part of its payload,
        # but those live in their own tables now (`sources`, `ontologies`).
        # We only persist the columns the `projects` schema carries.
        with cls._get_engine().begin() as conn:
            existing = conn.execute(
                text("SELECT 1 FROM projects WHERE project_id = :pid"),
                {"pid": project.project_id},
            ).first()
            if existing is None:
                # New project (the dataclass was constructed in memory).
                conn.execute(
                    text(
                        """
                        INSERT INTO projects (
                            project_id, name, status,
                            created_at, updated_at,
                            total_text_length, chunk_size, chunk_overlap,
                            analysis_summary, simulation_requirement,
                            graph_id, graph_build_task_id, error
                        ) VALUES (
                            :project_id, :name, :status,
                            :created_at, :updated_at,
                            :total_text_length, :chunk_size, :chunk_overlap,
                            :analysis_summary, :simulation_requirement,
                            :graph_id, :graph_build_task_id, :error
                        )
                        """
                    ),
                    {
                        "project_id": project.project_id,
                        "name": project.name,
                        "status": (
                            project.status.value
                            if isinstance(project.status, ProjectStatus)
                            else str(project.status)
                        ),
                        "created_at": _from_iso(project.created_at) or datetime.now(),
                        "updated_at": datetime.now(),
                        "total_text_length": project.total_text_length,
                        "chunk_size": project.chunk_size,
                        "chunk_overlap": project.chunk_overlap,
                        "analysis_summary": project.analysis_summary,
                        "simulation_requirement": project.simulation_requirement,
                        "graph_id": project.graph_id,
                        "graph_build_task_id": project.graph_build_task_id,
                        "error": project.error,
                    },
                )

            else:
                conn.execute(
                    text(
                        """
                        UPDATE projects SET
                            name = :name,
                            status = :status,
                            updated_at = :updated_at,
                            total_text_length = :total_text_length,
                            chunk_size = :chunk_size,
                            chunk_overlap = :chunk_overlap,
                            analysis_summary = :analysis_summary,
                            simulation_requirement = :simulation_requirement,
                            graph_id = :graph_id,
                            graph_build_task_id = :graph_build_task_id,
                            error = :error
                        WHERE project_id = :project_id
                        """
                    ),
                    {
                        "project_id": project.project_id,
                        "name": project.name,
                        "status": (
                            project.status.value
                            if isinstance(project.status, ProjectStatus)
                            else str(project.status)
                        ),
                        "updated_at": datetime.now(),
                        "total_text_length": project.total_text_length,
                        "chunk_size": project.chunk_size,
                        "chunk_overlap": project.chunk_overlap,
                        "analysis_summary": project.analysis_summary,
                        "simulation_requirement": project.simulation_requirement,
                        "graph_id": project.graph_id,
                        "graph_build_task_id": project.graph_build_task_id,
                        "error": project.error,
                    },
                )

            if isinstance(project.ontology, dict):
                cls._persist_completed_ontology(
                    conn,
                    project.project_id,
                    project.ontology,
                    _ontology_task_id,
                )

    @classmethod
    def begin_graph_build(
        cls,
        project_id: str,
        task_id: str,
        *,
        chunk_size: int,
        chunk_overlap: int,
        expected_status: ProjectStatus,
        expected_task_id: Optional[str],
        force: bool,
    ) -> bool:
        """CAS-start a build from the route's exact canonical snapshot."""
        try:
            expected_status = ProjectStatus(expected_status)
        except ValueError:
            return False
        eligible_statuses = {
            ProjectStatus.ONTOLOGY_GENERATED,
            ProjectStatus.FAILED,
            ProjectStatus.GRAPH_COMPLETED,
        }
        if force:
            eligible_statuses.add(ProjectStatus.GRAPH_BUILDING)
        if expected_status not in eligible_statuses:
            return False
        with cls._get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE projects SET status = :building_status, graph_id = NULL,
                        graph_build_task_id = :task_id, error = NULL,
                        chunk_size = :chunk_size, chunk_overlap = :chunk_overlap,
                        updated_at = :updated_at
                    WHERE project_id = :project_id
                      AND status = :expected_status
                      AND ((:expected_task_id IS NULL
                            AND graph_build_task_id IS NULL)
                           OR graph_build_task_id = :expected_task_id)
                      AND (:force = TRUE OR status != :building_status)
                    """
                ),
                {
                    "project_id": project_id,
                    "task_id": task_id,
                    "building_status": ProjectStatus.GRAPH_BUILDING.value,
                    "expected_status": expected_status.value,
                    "expected_task_id": expected_task_id,
                    "force": force,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "updated_at": datetime.now(),
                },
            )
        return result.rowcount == 1

    @classmethod
    def complete_graph_build(
        cls, project_id: str, expected_task_id: str, graph_id: str
    ) -> bool:
        """CAS-publish a completed graph only for its active task owner."""
        with cls._get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE projects SET status = :completed_status, graph_id = :graph_id,
                        error = NULL, updated_at = :updated_at
                    WHERE project_id = :project_id
                      AND graph_build_task_id = :expected_task_id
                      AND status = :building_status
                    """
                ),
                {
                    "project_id": project_id,
                    "expected_task_id": expected_task_id,
                    "graph_id": graph_id,
                    "building_status": ProjectStatus.GRAPH_BUILDING.value,
                    "completed_status": ProjectStatus.GRAPH_COMPLETED.value,
                    "updated_at": datetime.now(),
                },
            )
        return result.rowcount == 1

    @classmethod
    def ensure_graph_build_owner(cls, project_id: str, expected_task_id: str) -> bool:
        """Claim a ready unassigned graph build or retain its active owner."""
        with cls._get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE projects SET status = :building_status,
                        graph_build_task_id = :expected_task_id, graph_id = NULL,
                        error = NULL, updated_at = :updated_at
                    WHERE project_id = :project_id
                      AND ((graph_build_task_id = :expected_task_id
                            AND status = :building_status)
                           OR (graph_build_task_id IS NULL
                               AND status = :ready_status))
                    """
                ),
                {
                    "project_id": project_id,
                    "expected_task_id": expected_task_id,
                    "building_status": ProjectStatus.GRAPH_BUILDING.value,
                    "ready_status": ProjectStatus.ONTOLOGY_GENERATED.value,
                    "updated_at": datetime.now(),
                },
            )
        return result.rowcount == 1

    @classmethod
    def fail_graph_build(
        cls, project_id: str, expected_task_id: str, error: str
    ) -> bool:
        """CAS-fail a graph build only for its active task owner."""
        with cls._get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE projects SET status = :failed_status, graph_id = NULL,
                        error = :error, updated_at = :updated_at
                    WHERE project_id = :project_id
                      AND graph_build_task_id = :expected_task_id
                      AND status = :building_status
                    """
                ),
                {
                    "project_id": project_id,
                    "expected_task_id": expected_task_id,
                    "error": error,
                    "building_status": ProjectStatus.GRAPH_BUILDING.value,
                    "failed_status": ProjectStatus.FAILED.value,
                    "updated_at": datetime.now(),
                },
            )
        return result.rowcount == 1

    @classmethod
    def unwind_graph_build_dispatch(
        cls, project_id: str, expected_task_id: str, previous: Dict[str, Any]
    ) -> bool:
        """Restore a pre-dispatch state only if this dispatch still owns it."""
        status = previous["status"]
        if isinstance(status, ProjectStatus):
            status = status.value
        with cls._get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE projects SET status = :status, graph_id = :graph_id,
                        graph_build_task_id = :previous_task_id, error = :error,
                        updated_at = :updated_at
                    WHERE project_id = :project_id
                      AND graph_build_task_id = :expected_task_id
                      AND status = :building_status
                    """
                ),
                {
                    "project_id": project_id,
                    "expected_task_id": expected_task_id,
                    "previous_task_id": previous["graph_build_task_id"],
                    "status": status,
                    "graph_id": previous["graph_id"],
                    "error": previous["error"],
                    "building_status": ProjectStatus.GRAPH_BUILDING.value,
                    "updated_at": datetime.now(),
                },
            )
        return result.rowcount == 1

    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        with cls._get_engine().connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, project_id, name, status,
                           created_at, updated_at,
                           total_text_length, chunk_size, chunk_overlap,
                           analysis_summary, simulation_requirement,
                           graph_id, graph_build_task_id, error
                    FROM projects WHERE project_id = :pid
                    """
                ),
                {"pid": project_id},
            ).mappings().one_or_none()
            if row is None:
                return None
            project = cls._row_to_project(row)
            project.ontology = cls._load_latest_completed_ontology(conn, row["id"])
            project.files = cls.get_project_files(project_id)
            return project

    @classmethod
    def list_projects(cls, limit: int = 50) -> List[Project]:
        with cls._get_engine().connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, project_id, name, status,
                           created_at, updated_at,
                           total_text_length, chunk_size, chunk_overlap,
                           analysis_summary, simulation_requirement,
                           graph_id, graph_build_task_id, error
                    FROM projects
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
            projects = []
            for row in rows:
                project = cls._row_to_project(row)
                project.ontology = cls._load_latest_completed_ontology(conn, row["id"])
                projects.append(project)
            return projects

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        """Hard-delete the project row and any source files in storage.

        The `sources` table has `ondelete=CASCADE` on its FK to projects,
        so removing the project row removes the source rows in the same
        transaction. Storage objects are then best-effort deleted — the
        canonical record is the database row, and a sweep job can clean
        orphan storage objects later.
        """
        with cls._get_engine().begin() as conn:
            project_row = conn.execute(
                text("SELECT id FROM projects WHERE project_id = :pid"),
                {"pid": project_id},
            ).first()
            if project_row is None:
                return False
            project_pk = project_row[0]
            source_keys = [
                (r[0], Config.SUPABASE_STORAGE_BUCKET_UPLOADS)
                for r in conn.execute(
                    text("SELECT file_path FROM sources WHERE project_id = :pk"),
                    {"pk": project_pk},
                ).all()
            ]
            conn.execute(
                text("DELETE FROM projects WHERE project_id = :pid"),
                {"pid": project_id},
            )

        for key, bucket in source_keys:
            try:
                storage.delete(bucket=bucket, key=key)
            except StorageUnavailable:
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Project storage cleanup unavailable "
                    "project_id=%s exception_type=%s",
                    project_id,
                    type(exc).__name__,
                )
        return True

    @classmethod
    def save_file_to_project(
        cls, project_id: str, file_storage, original_filename: str
    ) -> Dict[str, str]:
        """Persist the upload to Supabase Storage + record a `sources` row.

        Returns the same dict shape as the filesystem path
        (`original_filename`, `saved_filename`, `path`, `size`,
        `content_hash`) so the call sites in `api/routes/*.py` do not
        need to change. The `path` field carries the Storage key, not
        a filesystem path — anything that later opens it as a file must
        go through `get_project_files` → `storage.download`.
        """
        data = file_storage.read()
        if not data:
            raise ValueError("Uploaded file is empty")

        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        key = _approved_key(project_id, safe_filename)

        bucket = Config.SUPABASE_STORAGE_BUCKET_UPLOADS
        if not is_storage_configured():
            raise StorageUnavailable(
                "ProjectRepository.save_file_to_project requires Supabase Storage; "
                "set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (cloud) or "
                "SUPABASE_S3_ENDPOINT (local MinIO) when USE_SUPABASE_PERSISTENCE=true."
            )

        result = storage.upload(
            bucket=bucket,
            key=key,
            data=data,
            content_type=getattr(file_storage, "mimetype", None) or "application/octet-stream",
        )

        content_hash = hashlib.sha256(data).hexdigest()

        with cls._get_engine().begin() as conn:
            project_pk = conn.execute(
                text("SELECT id FROM projects WHERE project_id = :pid"),
                {"pid": project_id},
            ).scalar_one_or_none()
            if project_pk is None:
                raise LookupError(
                    f"Cannot attach file: project {project_id} not found in canonical store"
                )
            conn.execute(
                text(
                    """
                    INSERT INTO sources (
                        project_id, filename, original_filename, file_path,
                        file_size, content_hash, upload_date
                    ) VALUES (
                        :project_id, :filename, :original_filename, :file_path,
                        :file_size, :content_hash, :upload_date
                    )
                    """
                ),
                {
                    "project_id": project_pk,
                    "filename": safe_filename,
                    "original_filename": original_filename,
                    "file_path": key,  # Storage key, not a filesystem path
                    "file_size": result.size,
                    "content_hash": content_hash,
                    "upload_date": datetime.now(),
                },
            )

        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": key,
            "size": result.size,
            "content_hash": content_hash,
        }

    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        """Return Storage keys (the `path` field), not filesystem paths."""
        with cls._get_engine().connect() as conn:
            keys = conn.execute(
                text(
                    """
                    SELECT s.file_path
                    FROM sources s
                    JOIN projects p ON p.id = s.project_id
                    WHERE p.project_id = :pid
                    ORDER BY s.upload_date ASC
                    """
                ),
                {"pid": project_id},
            ).scalars().all()
            return list(keys)

    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        """Persist extracted text in a Storage object."""
        if not is_storage_configured():
            raise StorageUnavailable(
                "save_extracted_text requires Supabase Storage in canonical mode"
            )
        key = _approved_key(project_id, "extracted_text.txt")
        storage.upload(
            bucket=Config.SUPABASE_STORAGE_BUCKET_UPLOADS,
            key=key,
            data=text.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )

    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        if not is_storage_configured():
            raise CanonicalSourceReadError(retryable=False)
        key = _approved_key(project_id, "extracted_text.txt")
        try:
            return storage.download(
                bucket=Config.SUPABASE_STORAGE_BUCKET_UPLOADS, key=key
            ).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            if _storage_object_is_missing(exc):
                return None
            raise CanonicalSourceReadError(
                retryable=_storage_read_is_retryable(exc)
            ) from None


def _from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

"""
Project Context Management
Used for persistent project state on the server to avoid passing large amounts of data between frontend interfaces.
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.safe_path import SafePathError, safe_join


def _audit(**kwargs):
    """Lazy import of audit_log.record_event to avoid a circular import
    (services/__init__ eagerly imports graph_builder → models.task → services)."""
    from ..services.audit_log import record_event
    record_event(**kwargs)


def _try_lock_graph_build_file(lock_file) -> bool:
    """Attempt a non-blocking cross-process lock for one graph-build file."""
    if os.name == "nt":
        import msvcrt

        try:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    import fcntl

    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _acquire_graph_build_lock_with_deadline(lock_file, *, timeout_seconds: float) -> None:
    """Acquire a graph-build lock or fail closed within a bounded interval."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        if _try_lock_graph_build_file(lock_file):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("graph_build_lock_unavailable")
        time.sleep(0.02)


def _acquire_graph_build_delivery_lock(lock_file) -> None:
    """Block until this process exclusively owns the provider-mutation fence.

    This lock deliberately has no application-level expiry.  The operating
    system releases the byte-range lock if the worker process exits, including
    a hard worker loss, while a live owner must retain it until the synchronous
    provider mutation has finished.
    """
    while not _try_lock_graph_build_file(lock_file):
        time.sleep(0.02)


def _unlock_graph_build_file(lock_file) -> None:
    if os.name == "nt":
        import msvcrt

        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


class ProjectStatus(str, Enum):
    """Project Status"""
    CREATED = "created"              # Newly created, files uploaded
    ONTOLOGY_GENERATED = "ontology_generated"  # Ontology generated
    GRAPH_BUILDING = "graph_building"    # Graph building in progress
    GRAPH_COMPLETED = "graph_completed"  # Graph building completed
    FAILED = "failed"                # Failed


@dataclass
class Project:
    """Project Data Model"""
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    
    # File Information
    files: List[Dict[str, str]] = field(default_factory=list)  # [{filename, path, size}]
    total_text_length: int = 0
    
    # Ontology Information (populated after Endpoint 1 generation)
    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None
    
    # Graph Information (populated after Endpoint 2 completion)
    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None
    
    # Configurations
    simulation_requirement: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Error Information
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": self.files,
            "total_text_length": self.total_text_length,
            "ontology": self.ontology,
            "analysis_summary": self.analysis_summary,
            "graph_id": self.graph_id,
            "graph_build_task_id": self.graph_build_task_id,
            "simulation_requirement": self.simulation_requirement,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create from dictionary"""
        status = data.get('status', 'created')
        if isinstance(status, str):
            status = ProjectStatus(status)
        
        return cls(
            project_id=data['project_id'],
            name=data.get('name', 'Unnamed Project'),
            status=status,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            files=data.get('files', []),
            total_text_length=data.get('total_text_length', 0),
            ontology=data.get('ontology'),
            analysis_summary=data.get('analysis_summary'),
            graph_id=data.get('graph_id'),
            graph_build_task_id=data.get('graph_build_task_id'),
            simulation_requirement=data.get('simulation_requirement'),
            chunk_size=data.get('chunk_size', 500),
            chunk_overlap=data.get('chunk_overlap', 50),
            error=data.get('error')
        )


class ProjectManager:
    """Project Manager - Responsible for persistent storage and retrieval of projects.

    When `Config.USE_SUPABASE_PERSISTENCE` is `True`, every public
    method delegates to `services.project_repository.ProjectRepository`,
    which writes through to Supabase Postgres + Storage per
    `docs/architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md`.
    Otherwise the legacy filesystem path is used so local dev and tests
    that do not stand up a Supabase backend keep working unchanged.
    """

    # Root directory for project storage (filesystem path only)
    PROJECTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'projects')
    GRAPH_BUILD_LOCK_TIMEOUT_SECONDS = 5.0

    @classmethod
    def _using_canonical_store(cls) -> bool:
        """True when the canonical Supabase-backed path is active.

        This is read on every call so the choice can be flipped at
        deploy time without restarting the process. Tests that want
        to exercise the legacy path assert `Config.USE_SUPABASE_PERSISTENCE`
        is False; canonical-mode tests assert the inverse.
        """
        return bool(getattr(Config, "USE_SUPABASE_PERSISTENCE", False))

    @classmethod
    def _delegate_to_canonical(cls, method_name: str, *args, **kwargs):
        """Forward a call to `ProjectRepository.<method_name>`.

        Imported lazily to keep `models.project` importable in tests
        that do not want the Supabase stack to import, and to avoid
        a circular import (project_repository imports models.project).
        """
        from ..services.project_repository import ProjectRepository

        method = getattr(ProjectRepository, method_name)
        return method(*args, **kwargs)
    
    @classmethod
    def _ensure_projects_dir(cls):
        """Ensure projects directory exists"""
        os.makedirs(cls.PROJECTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_project_dir(cls, project_id: str) -> str:
        """Get project directory path"""
        return safe_join(cls.PROJECTS_DIR, project_id)
    
    @classmethod
    def _get_project_meta_path(cls, project_id: str) -> str:
        """Get project metadata file path"""
        return os.path.join(cls._get_project_dir(project_id), 'project.json')
    
    @classmethod
    def _get_project_files_dir(cls, project_id: str) -> str:
        """Get project file storage directory"""
        return os.path.join(cls._get_project_dir(project_id), 'files')
    
    @classmethod
    def _get_project_text_path(cls, project_id: str) -> str:
        """Get extracted text storage path for project"""
        return os.path.join(cls._get_project_dir(project_id), 'extracted_text.txt')

    @staticmethod
    def _atomic_write_text(path: str, text: str) -> None:
        """Write text atomically: write to a temp file in the same directory,
        fsync, then os.replace onto the final path.

        A crash mid-write to `path` directly can leave a truncated/corrupt
        canonical record (audit §5 P1 "Non-atomic file persistence").
        os.replace is atomic on both POSIX and Windows, so a reader either
        sees the complete previous record or the complete new one — never a
        partial write. The temp file lives in the same directory so the
        rename stays within one filesystem.
        """
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=".tmp-", suffix=os.path.basename(path), dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            # Best-effort cleanup of the orphaned temp file on any failure;
            # the canonical record at `path` is untouched.
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

    @classmethod
    def create_project(cls, name: str = "Unnamed Project") -> Project:
        """
        Create a new project

        Args:
            name: Project name

        Returns:
            Newly created Project object
        """
        if cls._using_canonical_store():
            return cls._delegate_to_canonical("create_project", name)

        cls._ensure_projects_dir()
        
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        
        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now
        )
        
        # Create project directory structure
        project_dir = cls._get_project_dir(project_id)
        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(files_dir, exist_ok=True)
        
        # Save project metadata
        cls.save_project(project)

        _audit(
            action="project.created",
            entity_type="project",
            entity_id=project_id,
            after={"name": name, "status": ProjectStatus.CREATED.value},
        )
        return project

    @classmethod
    def save_project(
        cls,
        project: Project,
        *,
        _audit_status_change: bool = True,
        _ontology_task_id: Optional[str] = None,
    ) -> None:
        """Save project metadata atomically (audit §5 P1 non-atomic write fix).

        Records an audit event only when the status actually changes (avoids
        log spam from repeated saves that don't transition state).
        """
        if cls._using_canonical_store():
            return cls._delegate_to_canonical(
                "save_project",
                project,
                _audit_status_change=_audit_status_change,
                _ontology_task_id=_ontology_task_id,
            )

        prior_status: Optional[str] = None
        if _audit_status_change:
            existing = cls.get_project(project.project_id)
            if existing is not None:
                prior_status = (
                    existing.status.value
                    if isinstance(existing.status, ProjectStatus)
                    else str(existing.status)
                )

        project.updated_at = datetime.now().isoformat()
        meta_path = cls._get_project_meta_path(project.project_id)
        payload = json.dumps(project.to_dict(), ensure_ascii=False, indent=2)
        cls._atomic_write_text(meta_path, payload)

        new_status = (
            project.status.value
            if isinstance(project.status, ProjectStatus)
            else str(project.status)
        )
        if _audit_status_change and prior_status is not None and prior_status != new_status:
            _audit(
                action="project.status_changed",
                entity_type="project",
                entity_id=project.project_id,
                before={"status": prior_status},
                after={"status": new_status},
            )

    @classmethod
    @contextmanager
    def _graph_build_lock(cls, project_id: str):
        """Serialize graph-build state transitions for the legacy file store."""
        lock_path = os.path.join(cls._get_project_dir(project_id), ".graph-build.lock")
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with open(lock_path, "a+b") as lock_file:
            lock_file.seek(0)
            lock_file.write(b"0")
            lock_file.flush()
            _acquire_graph_build_lock_with_deadline(
                lock_file,
                timeout_seconds=cls.GRAPH_BUILD_LOCK_TIMEOUT_SECONDS,
            )
            try:
                yield
            finally:
                _unlock_graph_build_file(lock_file)

    @classmethod
    @contextmanager
    def graph_build_delivery_fence(cls, project_id: str, task_id: str):
        """Serialize one Celery delivery through the provider mutation.

        The legacy store uses an OS-owned cross-process file lock.  Canonical
        deployments delegate to a PostgreSQL advisory lock held on one session.
        Both lock types are released automatically when a lost worker process
        relinquishes its operating-system/database session resources.
        """
        if cls._using_canonical_store():
            canonical_fence = cls._delegate_to_canonical(
                "graph_build_delivery_fence",
                project_id,
                task_id,
            )
            with canonical_fence:
                yield
            return

        lock_path = os.path.join(
            cls._get_project_dir(project_id),
            ".graph-build-delivery.lock",
        )
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with open(lock_path, "a+b") as lock_file:
            lock_file.seek(0)
            lock_file.write(b"0")
            lock_file.flush()
            _acquire_graph_build_delivery_lock(lock_file)
            try:
                yield
            finally:
                _unlock_graph_build_file(lock_file)

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
        """CAS-start a graph build from the route's exact observed snapshot."""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical(
                "begin_graph_build",
                project_id,
                task_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                expected_status=expected_status,
                expected_task_id=expected_task_id,
                force=force,
            )
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
        with cls._graph_build_lock(project_id):
            project = cls.get_project(project_id)
            if (
                project is None
                or project.status != expected_status
                or project.graph_build_task_id != expected_task_id
            ):
                return False
            project.status = ProjectStatus.GRAPH_BUILDING
            project.graph_id = None
            project.graph_build_task_id = task_id
            project.error = None
            project.chunk_size = chunk_size
            project.chunk_overlap = chunk_overlap
            cls.save_project(project)
            return True

    @classmethod
    def complete_graph_build(
        cls, project_id: str, expected_task_id: str, graph_id: str
    ) -> bool:
        """Publish completion only if the caller still owns this graph build."""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical(
                "complete_graph_build", project_id, expected_task_id, graph_id
            )
        with cls._graph_build_lock(project_id):
            project = cls.get_project(project_id)
            if (
                project is None
                or project.status != ProjectStatus.GRAPH_BUILDING
                or project.graph_build_task_id != expected_task_id
            ):
                return False
            project.status = ProjectStatus.GRAPH_COMPLETED
            project.graph_id = graph_id
            project.error = None
            cls.save_project(project)
            return True

    @classmethod
    def ensure_graph_build_owner(cls, project_id: str, expected_task_id: str) -> bool:
        """Claim a ready unassigned build or confirm its active task owner."""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical(
                "ensure_graph_build_owner", project_id, expected_task_id
            )
        with cls._graph_build_lock(project_id):
            project = cls.get_project(project_id)
            if project is None:
                return False
            same_active_owner = (
                project.graph_build_task_id == expected_task_id
                and project.status == ProjectStatus.GRAPH_BUILDING
            )
            ready_unassigned = (
                project.graph_build_task_id is None
                and project.status == ProjectStatus.ONTOLOGY_GENERATED
            )
            if not (same_active_owner or ready_unassigned):
                return False
            project.status = ProjectStatus.GRAPH_BUILDING
            project.graph_build_task_id = expected_task_id
            project.graph_id = None
            project.error = None
            cls.save_project(project)
            return True

    @classmethod
    def fail_graph_build(
        cls, project_id: str, expected_task_id: str, error: str
    ) -> bool:
        """CAS-fail a graph build only while ``expected_task_id`` owns it."""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical(
                "fail_graph_build", project_id, expected_task_id, error
            )
        with cls._graph_build_lock(project_id):
            project = cls.get_project(project_id)
            if (
                project is None
                or project.status != ProjectStatus.GRAPH_BUILDING
                or project.graph_build_task_id != expected_task_id
            ):
                return False
            project.status = ProjectStatus.FAILED
            project.graph_id = None
            project.error = error
            cls.save_project(project)
            return True

    @classmethod
    def unwind_graph_build_dispatch(
        cls, project_id: str, expected_task_id: str, previous: Dict[str, Any]
    ) -> bool:
        """Undo a dispatch only while its task identity still owns the project."""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical(
                "unwind_graph_build_dispatch", project_id, expected_task_id, previous
            )
        with cls._graph_build_lock(project_id):
            project = cls.get_project(project_id)
            if (
                project is None
                or project.status != ProjectStatus.GRAPH_BUILDING
                or project.graph_build_task_id != expected_task_id
            ):
                return False
            project.status = previous["status"]
            project.graph_id = previous["graph_id"]
            project.graph_build_task_id = previous["graph_build_task_id"]
            project.error = previous["error"]
            cls.save_project(project)
            return True
    
    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        """
        Get project

        Args:
            project_id: Project ID

        Returns:
            Project object, None if it doesn't exist
        """
        if cls._using_canonical_store():
            return cls._delegate_to_canonical("get_project", project_id)

        meta_path = cls._get_project_meta_path(project_id)
        
        if not os.path.exists(meta_path):
            return None
        
        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return Project.from_dict(data)
    
    @classmethod
    def list_projects(cls, limit: int = 50) -> List[Project]:
        """
        List all projects

        Args:
            limit: Return limit

        Returns:
            List of projects, ordered by creation time descending
        """
        if cls._using_canonical_store():
            return cls._delegate_to_canonical("list_projects", limit)

        cls._ensure_projects_dir()
        
        projects = []
        for project_id in os.listdir(cls.PROJECTS_DIR):
            try:
                project = cls.get_project(project_id)
            except SafePathError:
                # Ignore malformed entries/symlinks placed in the storage root
                # rather than letting one entry break the entire listing.
                continue
            if project:
                projects.append(project)
        
        # Order by creation time descending
        projects.sort(key=lambda p: p.created_at, reverse=True)
        
        return projects[:limit]
    
    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        """
        Delete project and all its files

        Args:
            project_id: Project ID

        Returns:
            True if successful
        """
        if cls._using_canonical_store():
            return cls._delegate_to_canonical("delete_project", project_id)

        project_dir = cls._get_project_dir(project_id)

        if not os.path.exists(project_dir):
            return False

        # Record the deletion BEFORE the rmtree so the audit event exists even
        # if the removal itself fails partway (hard delete is destructive and
        # non-recoverable — the audit trail is the only record left).
        _audit(
            action="project.deleted",
            entity_type="project",
            entity_id=project_id,
            reason="hard_delete",
        )
        shutil.rmtree(project_dir)
        return True
    
    @classmethod
    def save_file_to_project(cls, project_id: str, file_storage, original_filename: str) -> Dict[str, str]:
        """
        Save uploaded file to project directory

        Hashes the source bytes (sha256) at ingest so the canonical record
        carries a content fingerprint usable by the export provenance layer
        (ADR-0008). The hash is computed from the persisted file, so it
        reflects exactly what is stored, not just what was streamed.

        Args:
            project_id: Project ID
            file_storage: Flask FileStorage object
            original_filename: Original filename

        Returns:
            File information dictionary {filename, path, size, content_hash}
        """
        if cls._using_canonical_store():
            return cls._delegate_to_canonical(
                "save_file_to_project", project_id, file_storage, original_filename
            )

        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(files_dir, exist_ok=True)

        # Generate safe filename
        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(files_dir, safe_filename)

        # Save file
        file_storage.save(file_path)

        # Get file size and sha256 of the persisted bytes.
        file_size = os.path.getsize(file_path)
        hasher = hashlib.sha256()
        with open(file_path, "rb") as stored:
            for chunk in iter(lambda: stored.read(65536), b""):
                hasher.update(chunk)
        content_hash = hasher.hexdigest()

        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": file_path,
            "size": file_size,
            "content_hash": content_hash,
        }
    
    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        """Save extracted text atomically (audit §5 P1 non-atomic write fix)."""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical("save_extracted_text", project_id, text)

        text_path = cls._get_project_text_path(project_id)
        cls._atomic_write_text(text_path, text)
    
    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        """Get extracted text"""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical("get_extracted_text", project_id)

        text_path = cls._get_project_text_path(project_id)
        
        if not os.path.exists(text_path):
            return None
        
        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        """Get all file paths for the project"""
        if cls._using_canonical_store():
            return cls._delegate_to_canonical("get_project_files", project_id)

        files_dir = cls._get_project_files_dir(project_id)
        
        if not os.path.exists(files_dir):
            return []
        
        return [
            os.path.join(files_dir, f) 
            for f in os.listdir(files_dir) 
            if os.path.isfile(os.path.join(files_dir, f))
        ]


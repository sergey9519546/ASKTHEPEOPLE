"""Server-owned Decision Workspace identity and relationship resolution."""

import json
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum
from typing import Annotated, BinaryIO, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)

from app.domain.decision_workspace import TruthBundle
from app.models.project import ProjectManager
from app.services.report_agent import ReportManager
from app.services.simulation_manager import SimulationManager

ServerId = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"),
]
WorkspaceId = Annotated[
    str,
    StringConstraints(pattern=r"^workspace_[0-9a-f]{32}$"),
]

_LOCK_TIMEOUT_SECONDS = 10.0
_LOCK_RETRY_SECONDS = 0.01


def _try_lock_file(lock_file: BinaryIO) -> None:
    lock_file.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(lock_file: BinaryIO) -> None:
    lock_file.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def _workspace_manifest_lock(project_dir: str) -> Iterator[None]:
    """Serialize first-manifest creation across threads and processes."""
    lock_path = os.path.join(project_dir, ".workspace_manifest.lock")
    try:
        # Open separately so path-bearing OSError details can be normalized
        # before the handle enters its guaranteed-close context below.
        lock_file = open(lock_path, "a+b")  # noqa: SIM115
    except OSError:
        raise RuntimeError("workspace_manifest_lock_unavailable") from None

    with lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()

        deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
        while True:
            try:
                _try_lock_file(lock_file)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "workspace_manifest_lock_unavailable"
                    ) from None
                time.sleep(_LOCK_RETRY_SECONDS)

        try:
            yield
        finally:
            try:
                _unlock_file(lock_file)
            except OSError:
                # Closing the descriptor releases an OS-owned advisory lock.
                pass


class CapabilityAvailability(str, Enum):
    ABSENT = "ABSENT"
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class WorkspaceCapabilityAvailability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    sources: CapabilityAvailability = CapabilityAvailability.ABSENT
    source_review: CapabilityAvailability = CapabilityAvailability.UNAVAILABLE
    run: CapabilityAvailability = CapabilityAvailability.ABSENT
    paths: CapabilityAvailability = CapabilityAvailability.UNAVAILABLE
    brief: CapabilityAvailability = CapabilityAvailability.ABSENT
    comparison: CapabilityAvailability = CapabilityAvailability.UNAVAILABLE


class StoredWorkspaceIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    workspace_id: WorkspaceId
    project_id: ServerId
    manifest_version: Literal[1]
    storage_status: Literal["TRANSITION"]


class DecisionWorkspaceManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    workspace_id: WorkspaceId
    project_id: ServerId
    decision_id: None = None
    decision_identity_status: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    manifest_version: Literal[1] = 1
    storage_status: Literal["TRANSITION"] = "TRANSITION"
    simulation_ids: tuple[ServerId, ...] = ()
    report_ids: tuple[ServerId, ...] = ()
    availability: WorkspaceCapabilityAvailability = Field(
        default_factory=WorkspaceCapabilityAvailability
    )
    truth: TruthBundle = Field(default_factory=TruthBundle.synthetic)


class WorkspaceProjectNotFound(LookupError):
    """Raised when a workspace is requested for a missing project."""


class WorkspaceManifestConflict(ValueError):
    """Raised when stored workspace identity metadata is invalid."""


class DecisionWorkspaceService:
    def __init__(
        self,
        project_manager=ProjectManager,
        simulation_manager_factory=SimulationManager,
        report_manager=ReportManager,
    ) -> None:
        self._project_manager = project_manager
        self._simulation_manager_factory = simulation_manager_factory
        self._report_manager = report_manager

    def resolve_by_project(self, project_id: str) -> DecisionWorkspaceManifest:
        if self._project_manager.get_project(project_id) is None:
            raise WorkspaceProjectNotFound(project_id)

        project_dir = self._project_manager._get_project_dir(project_id)
        manifest_path = os.path.join(project_dir, "workspace_manifest.json")
        identity = None
        if not os.path.exists(manifest_path):
            with _workspace_manifest_lock(project_dir):
                if not os.path.exists(manifest_path):
                    identity = StoredWorkspaceIdentity(
                        workspace_id=f"workspace_{uuid.uuid4().hex}",
                        project_id=project_id,
                        manifest_version=1,
                        storage_status="TRANSITION",
                    )
                    payload = json.dumps(
                        identity.model_dump(),
                        ensure_ascii=False,
                        indent=2,
                    )
                    self._project_manager._atomic_write_text(
                        manifest_path, payload
                    )

        if identity is None:
            try:
                with open(manifest_path, "r", encoding="utf-8") as stored_file:
                    identity = StoredWorkspaceIdentity.model_validate_json(
                        stored_file.read()
                    )
            except (UnicodeError, ValidationError) as exc:
                raise WorkspaceManifestConflict(
                    "stored_workspace_manifest_invalid"
                ) from exc
            if identity.project_id != project_id:
                raise WorkspaceManifestConflict(
                    "stored_workspace_manifest_project_mismatch"
                )

        simulations = self._simulation_manager_factory().list_simulations(
            project_id=project_id
        )
        simulation_ids = tuple(
            sorted(simulation.simulation_id for simulation in simulations)
        )
        related_simulation_ids = set(simulation_ids)
        reports = self._report_manager.list_reports(limit=1000)
        report_ids = tuple(
            sorted(
                report.report_id
                for report in reports
                if report.simulation_id in related_simulation_ids
            )
        )
        availability = WorkspaceCapabilityAvailability(
            sources=(
                CapabilityAvailability.AVAILABLE
                if self._project_manager.get_project_files(project_id)
                else CapabilityAvailability.ABSENT
            ),
            run=(
                CapabilityAvailability.AVAILABLE
                if simulation_ids
                else CapabilityAvailability.ABSENT
            ),
            brief=(
                CapabilityAvailability.AVAILABLE
                if report_ids
                else CapabilityAvailability.ABSENT
            ),
        )

        return DecisionWorkspaceManifest(
            **identity.model_dump(),
            simulation_ids=simulation_ids,
            report_ids=report_ids,
            availability=availability,
        )

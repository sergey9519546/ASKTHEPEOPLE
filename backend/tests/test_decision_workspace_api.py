import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from flask import Flask

from app.api import simulation_bp
from app.api.routes import workspace_routes
from app.application import (
    decision_workspace_service as workspace_service_module,
)
from app.application.decision_workspace_service import (
    DecisionWorkspaceManifest,
    DecisionWorkspaceService,
)
from app.models.project import ProjectManager


def _client():
    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    return app.test_client()


def test_workspace_route_is_registered() -> None:
    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")

    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/simulation/workspaces/by-project/<project_id>" in rules


def test_missing_project_returns_stable_not_found(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))

    response = _client().get(
        "/api/simulation/workspaces/by-project/proj_missing"
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "project_not_found",
    }


def test_service_atomically_persists_and_reuses_server_workspace_id(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project(name="Workspace identity")
    atomic_writes = []
    original_atomic_write = ProjectManager._atomic_write_text

    def record_atomic_write(path: str, text: str) -> None:
        atomic_writes.append((path, text))
        original_atomic_write(path, text)

    monkeypatch.setattr(ProjectManager, "_atomic_write_text", record_atomic_write)

    class NoSimulations:
        def list_simulations(self, project_id=None):
            return []

    class NoReports:
        @classmethod
        def list_reports(cls, limit=50):
            return []

    service = DecisionWorkspaceService(
        project_manager=ProjectManager,
        simulation_manager_factory=NoSimulations,
        report_manager=NoReports,
    )

    first = service.resolve_by_project(project.project_id)
    second = service.resolve_by_project(project.project_id)

    assert first.workspace_id == second.workspace_id
    assert re.fullmatch(r"workspace_[0-9a-f]{32}", first.workspace_id)
    assert len(atomic_writes) == 1
    manifest_path = (
        tmp_path / "projects" / project.project_id / "workspace_manifest.json"
    )
    expected_stored = {
        "workspace_id": first.workspace_id,
        "project_id": project.project_id,
        "manifest_version": 1,
        "storage_status": "TRANSITION",
    }
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == expected_stored
    assert manifest_path.read_text(encoding="utf-8") == json.dumps(
        expected_stored,
        ensure_ascii=False,
        indent=2,
    )


def test_simultaneous_first_resolution_returns_one_persisted_winner(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project(name="Concurrent identity")
    manifest_path = (
        tmp_path / "projects" / project.project_id / "workspace_manifest.json"
    )
    initial_checks = threading.Barrier(2)
    check_count = 0
    check_count_lock = threading.Lock()
    original_exists = workspace_service_module.os.path.exists

    def synchronize_initial_absence_check(path) -> bool:
        nonlocal check_count
        if str(path) != str(manifest_path):
            return original_exists(path)
        with check_count_lock:
            check_count += 1
            current_check = check_count
        exists = original_exists(path)
        if current_check <= 2:
            initial_checks.wait(timeout=5)
        return exists

    monkeypatch.setattr(
        "app.application.decision_workspace_service.os.path.exists",
        synchronize_initial_absence_check,
    )

    class NoSimulations:
        def list_simulations(self, project_id=None):
            return []

    class NoReports:
        @classmethod
        def list_reports(cls, limit=50):
            return []

    service = DecisionWorkspaceService(
        project_manager=ProjectManager,
        simulation_manager_factory=NoSimulations,
        report_manager=NoReports,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        manifests = tuple(
            executor.map(
                lambda _: service.resolve_by_project(project.project_id),
                range(2),
            )
        )

    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    issued_workspace_ids = {manifest.workspace_id for manifest in manifests}
    assert issued_workspace_ids == {persisted["workspace_id"]}


def test_endpoint_does_not_accept_or_override_workspace_or_decision_identity(
    monkeypatch,
) -> None:
    server_workspace_id = "workspace_0123456789abcdef0123456789abcdef"

    class FakeService:
        def resolve_by_project(self, project_id: str):
            assert project_id == "proj_123"
            return DecisionWorkspaceManifest(
                workspace_id=server_workspace_id,
                project_id=project_id,
            )

    monkeypatch.setattr(workspace_routes, "workspace_service", FakeService())

    response = _client().get(
        "/api/simulation/workspaces/by-project/proj_123",
        json={
            "workspace_id": "workspace_ffffffffffffffffffffffffffffffff",
            "decision_id": "decision_client_supplied",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["workspace_id"] == server_workspace_id
    assert response.get_json()["data"]["decision_id"] is None
    assert (
        _client()
        .post("/api/simulation/workspaces/by-project/proj_123", json={})
        .status_code
        == 405
    )


@pytest.mark.parametrize(
    "stored_text",
    [
        "{not-json",
        json.dumps(
            {
                "workspace_id": "workspace_0123456789abcdef0123456789abcdef",
                "project_id": "proj_123",
                "manifest_version": 1,
                "storage_status": "TRANSITION",
                "unexpected": True,
            }
        ),
        json.dumps(
            {
                "workspace_id": "workspace_NOT_VALID",
                "project_id": "proj_123",
                "manifest_version": 1,
                "storage_status": "TRANSITION",
            }
        ),
        json.dumps(
            {
                "workspace_id": "workspace_0123456789abcdef0123456789abcdef",
                "project_id": "proj_other",
                "manifest_version": 1,
                "storage_status": "TRANSITION",
            }
        ),
    ],
)
def test_invalid_stored_manifest_returns_conflict_without_overwrite(
    monkeypatch, tmp_path, stored_text: str
) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project(name="Stored conflict")
    manifest_path = (
        tmp_path / "projects" / project.project_id / "workspace_manifest.json"
    )
    manifest_path.write_text(
        stored_text.replace("proj_123", project.project_id),
        encoding="utf-8",
    )
    original = manifest_path.read_text(encoding="utf-8")

    response = _client().get(
        f"/api/simulation/workspaces/by-project/{project.project_id}"
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": "workspace_manifest_conflict",
    }
    assert manifest_path.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    "missing_field",
    [
        "workspace_id",
        "project_id",
        "manifest_version",
        "storage_status",
    ],
)
def test_stored_manifest_missing_any_required_field_conflicts_without_overwrite(
    monkeypatch, tmp_path, missing_field: str
) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project(name="Missing stored identity field")
    manifest_path = (
        tmp_path / "projects" / project.project_id / "workspace_manifest.json"
    )
    stored_identity = {
        "workspace_id": "workspace_0123456789abcdef0123456789abcdef",
        "project_id": project.project_id,
        "manifest_version": 1,
        "storage_status": "TRANSITION",
    }
    del stored_identity[missing_field]
    original = json.dumps(stored_identity, ensure_ascii=False, indent=2)
    manifest_path.write_text(original, encoding="utf-8")

    response = _client().get(
        f"/api/simulation/workspaces/by-project/{project.project_id}"
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": "workspace_manifest_conflict",
    }
    assert manifest_path.read_text(encoding="utf-8") == original


def test_relationships_are_filtered_sorted_and_never_collapsed(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project(name="Related records")

    class Simulations:
        def list_simulations(self, project_id=None):
            assert project_id == project.project_id
            return [
                SimpleNamespace(simulation_id="sim_b"),
                SimpleNamespace(simulation_id="sim_a"),
            ]

    class Reports:
        @classmethod
        def list_reports(cls, limit=50):
            assert limit == 1000
            return [
                SimpleNamespace(report_id="report_z", simulation_id="sim_b"),
                SimpleNamespace(report_id="report_unrelated", simulation_id="sim_x"),
                SimpleNamespace(report_id="report_a", simulation_id="sim_a"),
            ]

    service = DecisionWorkspaceService(
        project_manager=ProjectManager,
        simulation_manager_factory=Simulations,
        report_manager=Reports,
    )

    manifest = service.resolve_by_project(project.project_id)

    assert manifest.simulation_ids == ("sim_a", "sim_b")
    assert manifest.report_ids == ("report_a", "report_z")


@pytest.mark.parametrize(
    ("has_sources", "has_simulation", "has_report", "expected_dynamic"),
    [
        (False, False, False, ("ABSENT", "ABSENT", "ABSENT")),
        (True, False, False, ("AVAILABLE", "ABSENT", "ABSENT")),
        (False, True, False, ("ABSENT", "AVAILABLE", "ABSENT")),
        (True, True, True, ("AVAILABLE", "AVAILABLE", "AVAILABLE")),
    ],
)
def test_capability_availability_follows_record_presence(
    monkeypatch,
    tmp_path,
    has_sources: bool,
    has_simulation: bool,
    has_report: bool,
    expected_dynamic: tuple[str, str, str],
) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project(name="Capability states")
    if has_sources:
        source_path = (
            tmp_path / "projects" / project.project_id / "files" / "source.txt"
        )
        source_path.write_text("source", encoding="utf-8")

    class Simulations:
        def list_simulations(self, project_id=None):
            return (
                [SimpleNamespace(simulation_id="sim_1")]
                if has_simulation
                else []
            )

    class Reports:
        @classmethod
        def list_reports(cls, limit=50):
            return (
                [SimpleNamespace(report_id="report_1", simulation_id="sim_1")]
                if has_report
                else []
            )

    manifest = DecisionWorkspaceService(
        project_manager=ProjectManager,
        simulation_manager_factory=Simulations,
        report_manager=Reports,
    ).resolve_by_project(project.project_id)

    sources, run, brief = expected_dynamic
    assert manifest.availability.model_dump(mode="json") == {
        "sources": sources,
        "source_review": "UNAVAILABLE",
        "run": run,
        "paths": "UNAVAILABLE",
        "brief": brief,
        "comparison": "UNAVAILABLE",
    }


def test_manifest_contains_complete_synthetic_truth_bundle(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project(name="Truth bundle")

    class NoSimulations:
        def list_simulations(self, project_id=None):
            return []

    class NoReports:
        @classmethod
        def list_reports(cls, limit=50):
            return []

    manifest = DecisionWorkspaceService(
        project_manager=ProjectManager,
        simulation_manager_factory=NoSimulations,
        report_manager=NoReports,
    ).resolve_by_project(project.project_id)

    assert manifest.truth.model_dump() == {
        "output_origin": "synthetic",
        "human_respondent_count": 0,
        "is_forecast": False,
        "is_public_opinion_measure": False,
        "is_causal_evidence": False,
        "source_role": "starting_conditions_only",
        "human_validation_scope": "external_to_synthetic_run",
    }


def test_unexpected_service_failure_returns_stable_non_leaking_error(
    monkeypatch,
) -> None:
    class FailingService:
        def resolve_by_project(self, project_id: str):
            raise RuntimeError("private filesystem detail")

    monkeypatch.setattr(workspace_routes, "workspace_service", FailingService())

    response = _client().get(
        "/api/simulation/workspaces/by-project/proj_123"
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "success": False,
        "error": "workspace_manifest_unavailable",
    }
    assert b"private filesystem detail" not in response.data
    assert b"Traceback" not in response.data


def test_unexpected_presentation_failure_uses_same_stable_500(
    monkeypatch,
) -> None:
    class InvalidManifest:
        def model_dump(self, mode=None):
            raise RuntimeError("private serialization detail")

    class InvalidManifestService:
        def resolve_by_project(self, project_id: str):
            return InvalidManifest()

    monkeypatch.setattr(
        workspace_routes,
        "workspace_service",
        InvalidManifestService(),
    )

    response = _client().get(
        "/api/simulation/workspaces/by-project/proj_123"
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "success": False,
        "error": "workspace_manifest_unavailable",
    }
    assert b"private serialization detail" not in response.data
    assert b"Traceback" not in response.data

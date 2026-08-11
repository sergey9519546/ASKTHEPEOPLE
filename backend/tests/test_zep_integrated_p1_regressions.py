"""Integrated regressions for graph delivery and report identity P1s.

These tests never construct a provider client.  The graph builder and report
agent doubles are the provider boundary; the assertions exercise the real
Celery task and task-state code around that boundary.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from app.models.project import Project, ProjectManager, ProjectStatus
from app.models.task import TaskManager, TaskStatus
from app.services.graph_builder import GraphBuildProviderError
from app.services.project_repository import ProjectRepository
from app.services.report_agent import ReportStatus
from app.tasks import graph_tasks, report_tasks


def _graph_project(task_id: str) -> Project:
    return Project(
        project_id="project-integrated-race",
        name="Canonical source",
        status=ProjectStatus.GRAPH_BUILDING,
        created_at="2026-08-11T00:00:00Z",
        updated_at="2026-08-11T00:00:00Z",
        ontology={"entity_types": [], "edge_types": []},
        graph_build_task_id=task_id,
    )


class _GraphTaskRecorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.completions: list[tuple[str, dict]] = []
        self.failures: list[tuple[str, str]] = []

    def update_task(self, _task_id: str, **_changes) -> None:
        return None

    def complete_task(self, task_id: str, result: dict) -> None:
        with self._lock:
            self.completions.append((task_id, result))

    def fail_task(self, task_id: str, error: str, **_changes) -> None:
        with self._lock:
            self.failures.append((task_id, error))

    def get_task(self, _task_id: str):
        return None


def test_same_celery_delivery_is_serialized_before_provider_mutation(
    tmp_path,
    monkeypatch,
):
    """Two concurrent deliveries with one Celery id mutate Zep only once."""
    task_id = "same-celery-delivery"
    project = _graph_project(task_id)
    state_lock = threading.Lock()
    task_recorder = _GraphTaskRecorder()
    provider_entries: list[str] = []
    provider_entries_lock = threading.Lock()
    first_provider_entered = threading.Event()
    duplicate_provider_entered = threading.Event()
    allow_first_provider_to_finish = threading.Event()
    results: list[dict] = []
    failures: list[BaseException] = []

    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(ProjectManager, "_using_canonical_store", lambda: False)
    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: task_recorder)

    def get_project(_project_id: str):
        with state_lock:
            return Project.from_dict(project.to_dict())

    def ensure_owner(_project_id: str, expected_task_id: str) -> bool:
        with state_lock:
            return (
                project.status is ProjectStatus.GRAPH_BUILDING
                and project.graph_build_task_id == expected_task_id
            )

    def complete_build(
        _project_id: str,
        expected_task_id: str,
        graph_id: str,
    ) -> bool:
        with state_lock:
            if (
                project.status is not ProjectStatus.GRAPH_BUILDING
                or project.graph_build_task_id != expected_task_id
            ):
                return False
            project.status = ProjectStatus.GRAPH_COMPLETED
            project.graph_id = graph_id
            return True

    class _BlockingBuilder:
        def build_graph(self, **request):
            with provider_entries_lock:
                provider_entries.append(request["graph_id"])
                entry_number = len(provider_entries)
            if entry_number == 1:
                first_provider_entered.set()
                assert allow_first_provider_to_finish.wait(timeout=3)
            else:
                duplicate_provider_entered.set()
            return {
                "success": True,
                "graph_id": request["graph_id"],
                "graph_info": {},
            }

    monkeypatch.setattr(ProjectManager, "get_project", get_project)
    monkeypatch.setattr(ProjectManager, "ensure_graph_build_owner", ensure_owner)
    monkeypatch.setattr(ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(ProjectManager, "complete_graph_build", complete_build)
    monkeypatch.setattr(ProjectManager, "fail_graph_build", lambda *_args: False)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _BlockingBuilder)

    def deliver() -> None:
        try:
            results.append(
                graph_tasks.build_graph_task.run(
                    project_id=project.project_id,
                    task_id=task_id,
                )
            )
        except BaseException as exc:  # captured for an assertion in this thread
            failures.append(exc)

    first = threading.Thread(target=deliver)
    second = threading.Thread(target=deliver)
    first.start()
    assert first_provider_entered.wait(timeout=2)
    second.start()

    duplicate_reached_provider = duplicate_provider_entered.wait(timeout=0.3)
    allow_first_provider_to_finish.set()
    first.join(timeout=3)
    second.join(timeout=3)

    assert not first.is_alive()
    assert not second.is_alive()
    assert duplicate_reached_provider is False
    assert provider_entries == [
        graph_tasks._stable_graph_id(project.project_id, task_id)
    ]
    assert failures == []
    assert len(results) == 2
    assert all(result["success"] is True for result in results)


def test_canonical_graph_delivery_fence_uses_one_session_advisory_lock(
    monkeypatch,
):
    """Canonical deliveries hold a Postgres-owned lock through the mutation."""
    calls: list[tuple[str, dict]] = []

    class _Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))

        def close(self) -> None:
            calls.append(("close", {}))

    class _Dialect:
        name = "postgresql"

    class _Engine:
        dialect = _Dialect()

        def connect(self):
            calls.append(("connect", {}))
            return _Connection()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    with ProjectRepository.graph_build_delivery_fence(
        "project-canonical-fence",
        "task-canonical-fence",
    ):
        calls.append(("provider_mutation", {}))

    assert "pg_advisory_lock" in calls[1][0]
    assert calls[2] == ("provider_mutation", {})
    assert "pg_advisory_unlock" in calls[3][0]
    assert calls[1][1]["lock_key"] == calls[3][1]["lock_key"]
    assert calls[-1] == ("close", {})


def test_late_same_id_graph_failure_cannot_downgrade_completed_task(
    tmp_path,
    monkeypatch,
):
    """A losing delivery cannot replace the winner's terminal success."""
    task_id = "graph-late-terminal-downgrade"
    project = _graph_project(task_id)
    manager = TaskManager()
    manager._tasks.pop(task_id, None)
    monkeypatch.setattr(manager, "_get_redis", lambda: None)
    manager.create_task("graph_build", task_id=task_id)
    winning_result = {
        "success": True,
        "graph_id": graph_tasks._stable_graph_id(project.project_id, task_id),
    }

    class _LosingBuilder:
        def build_graph(self, **request):
            manager.complete_task(task_id, result=winning_result)
            raise GraphBuildProviderError(
                "graph_processing_failed",
                graph_id=request["graph_id"],
                retry_safe=False,
            )

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(ProjectManager, "_using_canonical_store", lambda: False)
    monkeypatch.setattr(ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(ProjectManager, "ensure_graph_build_owner", lambda *_a: True)
    monkeypatch.setattr(ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(ProjectManager, "fail_graph_build", lambda *_a: False)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _LosingBuilder)

    try:
        with pytest.raises(RuntimeError, match="^graph_build_superseded$"):
            graph_tasks.build_graph_task.run(
                project_id=project.project_id,
                task_id=task_id,
            )

        persisted = manager.get_task(task_id)
        assert persisted.status is TaskStatus.COMPLETED
        assert persisted.result == winning_result
        assert persisted.error is None
        assert persisted.public_error is None
        assert persisted.progress == 100
        assert persisted.message == "Task completed"
    finally:
        manager._tasks.pop(task_id, None)


def test_exhausted_initial_project_read_still_attempts_owned_failure_cas(
    tmp_path,
    monkeypatch,
):
    """Known dispatch identity is enough to close a stranded GRAPH_BUILDING."""
    task_id = "graph-exhausted-initial-read"
    manager = _GraphTaskRecorder()
    project_failures: list[tuple[str, str, str]] = []

    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(ProjectManager, "_using_canonical_store", lambda: False)
    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda _id: (_ for _ in ()).throw(
            ConnectionError("private canonical read failure")
        ),
    )
    monkeypatch.setattr(
        ProjectManager,
        "fail_graph_build",
        lambda project_id, expected_task_id, error: project_failures.append(
            (project_id, expected_task_id, error)
        )
        or True,
    )
    monkeypatch.setattr(
        graph_tasks,
        "GraphBuilderService",
        lambda: (_ for _ in ()).throw(
            AssertionError("provider must not run after canonical read failure")
        ),
    )
    monkeypatch.setattr(
        graph_tasks.build_graph_task.request,
        "retries",
        3,
        raising=False,
    )

    with pytest.raises(RuntimeError, match="^graph_build_failed$"):
        graph_tasks.build_graph_task.run(
            project_id="project-exhausted-initial-read",
            task_id=task_id,
        )

    assert project_failures == [
        (
            "project-exhausted-initial-read",
            task_id,
            "graph_build_failed",
        )
    ]
    assert manager.failures == [(task_id, "graph_build_failed")]


class _ReportTaskRecorder:
    def __init__(self, task) -> None:
        self.task = task
        self.updates: list[tuple[str, dict]] = []
        self.completions: list[tuple[str, dict]] = []
        self.failures: list[tuple[str, str, dict]] = []

    def get_task(self, _task_id: str):
        return self.task

    def update_task(self, task_id: str, **changes) -> None:
        self.updates.append((task_id, changes))

    def complete_task(self, task_id: str, result: dict) -> None:
        self.completions.append((task_id, result))

    def fail_task(self, task_id: str, error: str, **changes) -> None:
        self.failures.append((task_id, error, changes))


def test_report_worker_rejects_queued_graph_metadata_drift_before_generation(
    monkeypatch,
):
    """The current project graph cannot silently replace the queued graph."""
    simulation_id = "simulation-report-metadata-drift"
    report_id = "report-metadata-drift"
    task_id = "task-report-metadata-drift"
    manager = _ReportTaskRecorder(
        SimpleNamespace(
            status=TaskStatus.PENDING,
            result=None,
            metadata={
                "simulation_id": simulation_id,
                "report_id": report_id,
                "graph_id": "graph-when-queued",
            },
        )
    )
    simulation = SimpleNamespace(
        simulation_id=simulation_id,
        project_id="project-report-metadata-drift",
        graph_id=None,
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="graph-current",
        simulation_requirement="Canonical decision A",
    )
    agent_constructions: list[dict] = []

    class _ForbiddenAgent:
        def __init__(self, **request) -> None:
            agent_constructions.append(request)

        def generate_report(self, **_request):
            raise AssertionError("metadata drift must fail before generation")

    from app.models import project as project_module
    from app.services import simulation_manager

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        simulation_manager.SimulationManager,
        "get_simulation",
        lambda _self, _id: simulation,
    )
    monkeypatch.setattr(
        project_module.ProjectManager,
        "get_project",
        lambda _id: project,
    )
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenAgent)

    with pytest.raises(RuntimeError, match="^report_graph_scope_mismatch$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation_id,
            report_id=report_id,
            task_id=task_id,
        )

    assert agent_constructions == []
    assert manager.completions == []
    assert manager.failures == [
        (
            task_id,
            "report_graph_scope_mismatch",
            {"public_error": "report_graph_scope_mismatch"},
        )
    ]


def test_report_worker_rejects_missing_queued_identity_metadata(
    monkeypatch,
):
    """A real queued task cannot execute without its server-owned identity."""
    simulation_id = "simulation-report-metadata-missing"
    report_id = "report-metadata-missing"
    task_id = "task-report-metadata-missing"
    manager = _ReportTaskRecorder(
        SimpleNamespace(
            status=TaskStatus.PENDING,
            result=None,
            metadata={},
        )
    )
    simulation = SimpleNamespace(
        simulation_id=simulation_id,
        project_id="project-report-metadata-missing",
        graph_id="graph-report-metadata-missing",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id=simulation.graph_id,
        simulation_requirement="Canonical decision A",
    )
    agent_constructions: list[dict] = []

    class _ForbiddenAgent:
        def __init__(self, **request) -> None:
            agent_constructions.append(request)

    from app.models import project as project_module
    from app.services import simulation_manager

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        simulation_manager.SimulationManager,
        "get_simulation",
        lambda _self, _id: simulation,
    )
    monkeypatch.setattr(
        project_module.ProjectManager,
        "get_project",
        lambda _id: project,
    )
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenAgent)

    with pytest.raises(RuntimeError, match="^report_task_identity_missing$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation_id,
            report_id=report_id,
            task_id=task_id,
        )

    assert agent_constructions == []
    assert manager.completions == []
    assert manager.failures == [
        (
            task_id,
            "report_task_identity_missing",
            {"public_error": "report_task_identity_missing"},
        )
    ]


def test_processing_report_redelivery_repairs_exact_saved_artifact_without_regeneration(
    monkeypatch,
):
    """A save-before-ack crash repairs the envelope and never calls the LLM."""
    simulation_id = "simulation-report-saved-before-ack"
    report_id = "report-saved-before-ack"
    task_id = "task-report-saved-before-ack"
    graph_id = "graph-report-saved-before-ack"
    requirement = "Canonical decision A"
    manager = _ReportTaskRecorder(
        SimpleNamespace(
            status=TaskStatus.PROCESSING,
            result=None,
            metadata={
                "simulation_id": simulation_id,
                "report_id": report_id,
                "graph_id": graph_id,
            },
        )
    )
    simulation = SimpleNamespace(
        simulation_id=simulation_id,
        project_id="project-report-saved-before-ack",
        graph_id=graph_id,
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id=graph_id,
        simulation_requirement=requirement,
    )
    saved_report = SimpleNamespace(
        status=ReportStatus.COMPLETED,
        report_id=report_id,
        simulation_id=simulation_id,
        graph_id=graph_id,
        simulation_requirement=requirement,
    )
    agent_constructions: list[dict] = []

    class _ForbiddenAgent:
        def __init__(self, **request) -> None:
            agent_constructions.append(request)

    from app.models import project as project_module
    from app.services import simulation_manager

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        simulation_manager.SimulationManager,
        "get_simulation",
        lambda _self, _id: simulation,
    )
    monkeypatch.setattr(
        project_module.ProjectManager,
        "get_project",
        lambda _id: project,
    )
    monkeypatch.setattr(
        report_tasks.ReportManager,
        "get_report",
        lambda _id: saved_report,
    )
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenAgent)

    result = report_tasks.generate_report_task.run(
        simulation_id=simulation_id,
        report_id=report_id,
        task_id=task_id,
    )

    expected_result = {
        "report_id": report_id,
        "simulation_id": simulation_id,
        "graph_id": graph_id,
        "status": "completed",
    }
    assert result == {"success": True, "report_id": report_id}
    assert agent_constructions == []
    assert manager.completions == [(task_id, expected_result)]
    assert manager.failures == []


def test_report_worker_rejects_generated_artifact_for_a_different_decision(
    monkeypatch,
):
    """Initial completion and replay use the same decision identity rule."""
    simulation_id = "simulation-report-decision-drift"
    report_id = "report-decision-drift"
    task_id = "task-report-decision-drift"
    manager = _ReportTaskRecorder(None)
    simulation = SimpleNamespace(
        simulation_id=simulation_id,
        project_id="project-report-decision-drift",
        graph_id="graph-report-decision-drift",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id=simulation.graph_id,
        simulation_requirement="Canonical decision A",
    )

    class _WrongDecisionAgent:
        def __init__(self, **_request) -> None:
            pass

        def generate_report(self, **_request):
            return SimpleNamespace(
                status=ReportStatus.COMPLETED,
                report_id=report_id,
                simulation_id=simulation_id,
                graph_id=simulation.graph_id,
                simulation_requirement="Different decision B",
            )

    from app.models import project as project_module
    from app.services import simulation_manager

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        simulation_manager.SimulationManager,
        "get_simulation",
        lambda _self, _id: simulation,
    )
    monkeypatch.setattr(
        project_module.ProjectManager,
        "get_project",
        lambda _id: project,
    )
    monkeypatch.setattr(report_tasks, "ReportAgent", _WrongDecisionAgent)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation_id,
            report_id=report_id,
            task_id=task_id,
        )

    assert manager.completions == []
    assert manager.failures == [
        (
            task_id,
            "report_generation_failed",
            {"public_error": "report_generation_failed"},
        )
    ]

"""Durability contracts for terminal report-task deliveries."""

from types import SimpleNamespace

import pytest
from app.models.project import ProjectManager
from app.services.report_agent import Report, ReportManager, ReportStatus
from app.services.simulation_manager import SimulationManager
from app.tasks import report_tasks


class _CompletedTaskManager:
    def __init__(self, task) -> None:
        self.task = task
        self.updates = []
        self.completions = []
        self.failures = []

    def get_task(self, _task_id):
        return self.task

    def update_task(self, task_id, **changes) -> None:
        self.updates.append((task_id, changes))

    def complete_task(self, task_id, result) -> None:
        self.completions.append((task_id, result))

    def fail_task(self, task_id, error, **kwargs) -> None:
        self.failures.append((task_id, error, kwargs))


def _terminal_task(*, simulation_id: str, report_id: str, graph_id: str):
    identity = {
        "simulation_id": simulation_id,
        "report_id": report_id,
        "graph_id": graph_id,
    }
    return SimpleNamespace(
        status=report_tasks.TaskStatus.COMPLETED,
        result=dict(identity),
        metadata=dict(identity),
    )


def _context(*, simulation_id: str, graph_id: str, requirement: str):
    simulation = SimpleNamespace(
        simulation_id=simulation_id,
        project_id=f"project-{simulation_id}",
        graph_id=graph_id,
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id=graph_id,
        simulation_requirement=requirement,
    )
    return simulation, project


def _patch_context(monkeypatch, *, simulation, project) -> None:
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda _project_id: project,
    )


def test_report_task_acknowledges_late_and_rejects_worker_loss():
    assert report_tasks.generate_report_task.acks_late is True
    assert report_tasks.generate_report_task.reject_on_worker_lost is True


def test_completed_redelivery_rejects_missing_report_artifact_without_downgrade(
    monkeypatch,
    tmp_path,
):
    simulation_id = "simulation-terminal-artifact-missing"
    report_id = "report-terminal-artifact-missing"
    graph_id = "project-graph"
    simulation, project = _context(
        simulation_id=simulation_id,
        graph_id=graph_id,
        requirement="Canonical decision.",
    )
    task_manager = _CompletedTaskManager(
        _terminal_task(
            simulation_id=simulation_id,
            report_id=report_id,
            graph_id=graph_id,
        )
    )

    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(tmp_path))
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_tasks,
        "ReportAgent",
        lambda **_context: (_ for _ in ()).throw(
            AssertionError("ReportAgent constructed for completed delivery")
        ),
    )
    _patch_context(monkeypatch, simulation=simulation, project=project)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation_id,
            report_id=report_id,
            task_id="task-terminal-artifact-missing",
        )

    assert task_manager.updates == []
    assert task_manager.completions == []
    assert task_manager.failures == []


def test_completed_redelivery_never_downgrades_on_authoritative_context_failure(
    monkeypatch,
):
    simulation_id = "simulation-terminal-context-missing"
    report_id = "report-terminal-context-missing"
    graph_id = "project-graph"
    simulation, _project = _context(
        simulation_id=simulation_id,
        graph_id=graph_id,
        requirement="Canonical decision.",
    )
    task_manager = _CompletedTaskManager(
        _terminal_task(
            simulation_id=simulation_id,
            report_id=report_id,
            graph_id=graph_id,
        )
    )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: None)

    with pytest.raises(RuntimeError, match="^report_project_not_found$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation_id,
            report_id=report_id,
            task_id="task-terminal-context-missing",
        )

    assert task_manager.updates == []
    assert task_manager.completions == []
    assert task_manager.failures == []


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        pytest.param("simulation_id", "different-simulation", id="simulation"),
        pytest.param("graph_id", "different-graph", id="graph"),
        pytest.param(
            "simulation_requirement",
            "Different decision context.",
            id="decision-context",
        ),
    ],
)
def test_completed_redelivery_rejects_mismatched_report_artifact_without_downgrade(
    monkeypatch,
    tmp_path,
    field,
    wrong_value,
):
    simulation_id = "simulation-terminal-artifact-mismatch"
    report_id = "report-terminal-artifact-mismatch"
    graph_id = "project-graph"
    requirement = "Canonical decision."
    simulation, project = _context(
        simulation_id=simulation_id,
        graph_id=graph_id,
        requirement=requirement,
    )
    task_manager = _CompletedTaskManager(
        _terminal_task(
            simulation_id=simulation_id,
            report_id=report_id,
            graph_id=graph_id,
        )
    )
    report_fields = {
        "report_id": report_id,
        "simulation_id": simulation_id,
        "graph_id": graph_id,
        "simulation_requirement": requirement,
    }
    report_fields[field] = wrong_value

    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(tmp_path))
    ReportManager.save_report(
        Report(status=ReportStatus.COMPLETED, **report_fields)
    )
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_tasks,
        "ReportAgent",
        lambda **_context: (_ for _ in ()).throw(
            AssertionError("ReportAgent constructed for completed delivery")
        ),
    )
    _patch_context(monkeypatch, simulation=simulation, project=project)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation_id,
            report_id=report_id,
            task_id="task-terminal-artifact-mismatch",
        )

    assert task_manager.updates == []
    assert task_manager.completions == []
    assert task_manager.failures == []


def test_completion_reread_requires_matching_report_artifact_without_downgrade(
    monkeypatch,
    tmp_path,
):
    simulation_id = "simulation-completion-reread-artifact"
    report_id = "report-completion-reread-artifact"
    graph_id = "project-graph"
    requirement = "Canonical decision."
    simulation, project = _context(
        simulation_id=simulation_id,
        graph_id=graph_id,
        requirement=requirement,
    )

    class _CompletionRaceTaskManager(_CompletedTaskManager):
        def __init__(self) -> None:
            super().__init__(None)
            self.read_count = 0

        def get_task(self, _task_id):
            self.read_count += 1
            if self.read_count == 1:
                return None
            return _terminal_task(
                simulation_id=simulation_id,
                report_id=report_id,
                graph_id=graph_id,
            )

        def complete_task(self, _task_id, _result) -> None:
            raise RuntimeError("PRIVATE_COMPLETION_AUDIT_FAILURE")

        def fail_task(self, _task_id, _error, **_kwargs) -> None:
            raise AssertionError("completed task was downgraded")

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **request):
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation_id,
                graph_id=graph_id,
                status=ReportStatus.COMPLETED,
            )

    task_manager = _CompletionRaceTaskManager()
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(tmp_path))
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)
    _patch_context(monkeypatch, simulation=simulation, project=project)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation_id,
            report_id=report_id,
            task_id="task-completion-reread-artifact",
        )

    assert task_manager.failures == []

"""Focused contract tests for authoritative report-worker context."""

from types import SimpleNamespace

import pytest

from app.models.project import ProjectManager
from app.services.report_agent import ReportStatus
from app.services.simulation_manager import SimulationManager
from app.tasks import report_tasks


class _RecordingTaskManager:
    def __init__(self) -> None:
        self.updates = []
        self.completions = []
        self.failures = []

    def update_task(self, task_id, **changes) -> None:
        self.updates.append((task_id, changes))

    def get_task(self, task_id):
        return None

    def complete_task(self, task_id, result) -> None:
        self.completions.append((task_id, result))

    def fail_task(self, task_id, error, **kwargs) -> None:
        self.failures.append((task_id, error, kwargs))


def test_duplicate_completed_delivery_short_circuits_before_report_agent(
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-already-completed",
        project_id="project-already-completed",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _CompletedTaskManager(_RecordingTaskManager):
        def get_task(self, task_id):
            return SimpleNamespace(
                status=report_tasks.TaskStatus.COMPLETED,
                result={
                    "simulation_id": "simulation-already-completed",
                    "report_id": "report-already-completed",
                    "graph_id": "project-graph",
                },
                metadata={
                    "simulation_id": "simulation-already-completed",
                    "report_id": "report-already-completed",
                    "graph_id": "project-graph",
                },
            )

    task_manager = _CompletedTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("ReportAgent constructed for completed delivery")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)
    monkeypatch.setattr(
        report_tasks.ReportManager,
        "get_report",
        lambda _report_id: SimpleNamespace(
            status=ReportStatus.COMPLETED,
            report_id="report-already-completed",
            simulation_id=simulation.simulation_id,
            graph_id=project.graph_id,
            simulation_requirement="Canonical decision.",
        ),
    )
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

    assert report_tasks.generate_report_task.run(
        simulation_id="simulation-already-completed",
        report_id="report-already-completed",
        task_id="task-already-completed",
    ) == {"success": True, "report_id": "report-already-completed"}
    assert task_manager.updates == []
    assert task_manager.completions == []
    assert task_manager.failures == []


def test_completed_redelivery_wrong_graph_fails_against_authoritative_project(
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-completed-wrong-graph",
        project_id="project-completed-wrong-graph",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _CompletedTaskManager(_RecordingTaskManager):
        def get_task(self, task_id):
            return SimpleNamespace(
                status=report_tasks.TaskStatus.COMPLETED,
                result={
                    "simulation_id": simulation.simulation_id,
                    "report_id": "report-completed-wrong-graph",
                    "graph_id": "different-graph",
                },
                metadata={
                    "simulation_id": simulation.simulation_id,
                    "report_id": "report-completed-wrong-graph",
                    "graph_id": "different-graph",
                },
            )

    task_manager = _CompletedTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("ReportAgent constructed for wrong graph delivery")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)
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

    with pytest.raises(RuntimeError, match="^report_graph_scope_mismatch$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-completed-wrong-graph",
            task_id="task-completed-wrong-graph",
        )

    assert task_manager.updates == []
    assert task_manager.completions == []
    assert task_manager.failures == []


@pytest.mark.parametrize(
    ("persisted_result", "persisted_metadata"),
    [
        pytest.param(
            {
                "simulation_id": "simulation-completed-mismatch",
                "report_id": "different-report-id",
            },
            {
                "simulation_id": "simulation-completed-mismatch",
                "report_id": "report-completed-mismatch",
            },
            id="result-report-mismatch",
        ),
        pytest.param(
            {
                "simulation_id": "simulation-completed-mismatch",
                "report_id": "report-completed-mismatch",
            },
            {
                "simulation_id": "different-simulation-id",
                "report_id": "report-completed-mismatch",
            },
            id="metadata-simulation-mismatch",
        ),
    ],
)
def test_completed_redelivery_identity_mismatch_fails_without_downgrade_or_agent(
    monkeypatch,
    persisted_result,
    persisted_metadata,
):
    class _CompletedTaskManager(_RecordingTaskManager):
        def get_task(self, task_id):
            return SimpleNamespace(
                status=report_tasks.TaskStatus.COMPLETED,
                result=persisted_result,
                metadata=persisted_metadata,
            )

    task_manager = _CompletedTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("ReportAgent constructed for mismatched delivery")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: (_ for _ in ()).throw(
            AssertionError("context resolved for mismatched completed delivery")
        ),
    )

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id="simulation-completed-mismatch",
            report_id="report-completed-mismatch",
            task_id="task-completed-mismatch",
        )

    assert task_manager.updates == []
    assert task_manager.completions == []
    assert task_manager.failures == []


@pytest.mark.parametrize(
    "agent_result",
    [
        pytest.param(None, id="none"),
        pytest.param(
            SimpleNamespace(
                report_id="report-invalid-result",
                status=ReportStatus.FAILED,
            ),
            id="failed-status",
        ),
        pytest.param(
            SimpleNamespace(
                report_id="different-report-id",
                status=ReportStatus.COMPLETED,
                simulation_id="simulation-invalid-report-result",
                graph_id="project-graph",
            ),
            id="wrong-report-identity",
        ),
        pytest.param(
            SimpleNamespace(
                report_id="report-invalid-result",
                status=ReportStatus.COMPLETED,
                simulation_id="different-simulation-id",
                graph_id="project-graph",
            ),
            id="wrong-simulation-identity",
        ),
        pytest.param(
            SimpleNamespace(
                report_id="report-invalid-result",
                status=ReportStatus.COMPLETED,
                simulation_id="simulation-invalid-report-result",
                graph_id="different-graph-id",
            ),
            id="wrong-graph-identity",
        ),
        pytest.param(
            SimpleNamespace(
                report_id="report-invalid-result",
                status=ReportStatus.COMPLETED,
            ),
            id="missing-authoritative-identities",
        ),
    ],
)
def test_worker_rejects_noncompleted_or_wrong_report_result(
    monkeypatch,
    agent_result,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-invalid-report-result",
        project_id="project-invalid-report-result",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _RecordingTaskManager()

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **_request):
            return agent_result

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-invalid-result",
            task_id="task-invalid-result",
        )

    assert task_manager.completions == []
    assert task_manager.failures == [
        (
            "task-invalid-result",
            "report_generation_failed",
            {"public_error": "report_generation_failed"},
        )
    ]


def test_completion_exception_does_not_downgrade_already_completed_task(
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-completion-race",
        project_id="project-completion-race",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _CompletionRaceTaskManager(_RecordingTaskManager):
        def __init__(self) -> None:
            super().__init__()
            self.read_count = 0

        def complete_task(self, task_id, result) -> None:
            raise RuntimeError("PRIVATE_COMPLETION_AUDIT_FAILURE")

        def get_task(self, task_id):
            self.read_count += 1
            if self.read_count == 1:
                return None
            return SimpleNamespace(
                status=report_tasks.TaskStatus.COMPLETED,
                result={
                    "simulation_id": "simulation-completion-race",
                    "report_id": "report-completion-race",
                    "graph_id": "project-graph",
                },
            )

        def fail_task(self, task_id, error, **kwargs) -> None:
            raise AssertionError("completed task was downgraded")

    task_manager = _CompletionRaceTaskManager()

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **request):
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation.simulation_id,
                graph_id=project.graph_id,
                status=ReportStatus.COMPLETED,
                simulation_requirement=project.simulation_requirement,
            )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_tasks.ReportManager,
        "get_report",
        lambda _report_id: SimpleNamespace(
            status=ReportStatus.COMPLETED,
            report_id="report-completion-race",
            simulation_id=simulation.simulation_id,
            graph_id=project.graph_id,
            simulation_requirement="Canonical decision.",
        ),
    )
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)

    assert report_tasks.generate_report_task.run(
        simulation_id=simulation.simulation_id,
        report_id="report-completion-race",
        task_id="task-completion-race",
    ) == {"success": True, "report_id": "report-completion-race"}
    assert task_manager.failures == []


def test_completion_exception_rejects_completed_reread_with_wrong_identity(
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-completion-wrong-identity",
        project_id="project-completion-wrong-identity",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _WrongIdentityCompletionTaskManager(_RecordingTaskManager):
        def __init__(self) -> None:
            super().__init__()
            self.read_count = 0

        def complete_task(self, task_id, result) -> None:
            raise RuntimeError("PRIVATE_COMPLETION_AUDIT_FAILURE")

        def get_task(self, task_id):
            self.read_count += 1
            if self.read_count == 1:
                return None
            return SimpleNamespace(
                status=report_tasks.TaskStatus.COMPLETED,
                result={
                    "simulation_id": simulation.simulation_id,
                    "report_id": "report-completion-wrong-identity",
                    "graph_id": "different-graph",
                },
            )

        def fail_task(self, task_id, error, **kwargs) -> None:
            raise AssertionError("ambiguous completed task was downgraded")

    task_manager = _WrongIdentityCompletionTaskManager()

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **request):
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation.simulation_id,
                graph_id=project.graph_id,
                status=ReportStatus.COMPLETED,
                simulation_requirement=project.simulation_requirement,
            )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-completion-wrong-identity",
            task_id="task-completion-wrong-identity",
        )

    assert task_manager.failures == []


@pytest.mark.parametrize("lookup_raises", [False, True])
def test_completion_exception_does_not_downgrade_when_task_state_is_ambiguous(
    monkeypatch,
    lookup_raises,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-completion-ambiguous",
        project_id="project-completion-ambiguous",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _AmbiguousCompletionTaskManager(_RecordingTaskManager):
        def __init__(self) -> None:
            super().__init__()
            self.read_count = 0

        def complete_task(self, task_id, result) -> None:
            raise RuntimeError("PRIVATE_COMPLETION_STORAGE_FAILURE")

        def get_task(self, task_id):
            self.read_count += 1
            if lookup_raises and self.read_count > 1:
                raise ConnectionError("PRIVATE_TASK_REREAD_FAILURE")
            return None

    task_manager = _AmbiguousCompletionTaskManager()

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **request):
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation.simulation_id,
                graph_id=project.graph_id,
                status=ReportStatus.COMPLETED,
                simulation_requirement=project.simulation_requirement,
            )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-completion-ambiguous",
            task_id="task-completion-ambiguous",
        )

    assert task_manager.failures == []


def test_completion_exception_fails_task_only_when_reread_is_nonterminal(
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-completion-nonterminal",
        project_id="project-completion-nonterminal",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _NonterminalCompletionTaskManager(_RecordingTaskManager):
        def complete_task(self, task_id, result) -> None:
            raise RuntimeError("PRIVATE_COMPLETION_STORAGE_FAILURE")

        def get_task(self, task_id):
            return SimpleNamespace(
                status=report_tasks.TaskStatus.PROCESSING,
                metadata={
                    "simulation_id": simulation.simulation_id,
                    "report_id": "report-completion-nonterminal",
                    "graph_id": project.graph_id,
                },
            )

    task_manager = _NonterminalCompletionTaskManager()

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **request):
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation.simulation_id,
                graph_id=project.graph_id,
                status=ReportStatus.COMPLETED,
                simulation_requirement=project.simulation_requirement,
            )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-completion-nonterminal",
            task_id="task-completion-nonterminal",
        )

    assert task_manager.failures == [
        (
            "task-completion-nonterminal",
            "report_generation_failed",
            {"public_error": "report_generation_failed"},
        )
    ]


def test_worker_builds_agent_only_from_authoritative_project_context(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="simulation-authoritative",
        project_id="project-authoritative",
        graph_id="project-graph",
    )
    # Deliberately has no ``decision_text`` attribute: the persisted field is
    # ``simulation_requirement``.
    project = SimpleNamespace(
        project_id="project-authoritative",
        graph_id="project-graph",
        simulation_requirement="  Canonical decision text.  ",
    )
    task_manager = _RecordingTaskManager()
    captured = {}

    class _ReportAgent:
        def __init__(self, **context) -> None:
            captured["context"] = context

        def generate_report(self, **request):
            captured["request"] = request
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation.simulation_id,
                graph_id=project.graph_id,
                status=ReportStatus.COMPLETED,
                simulation_requirement=project.simulation_requirement.strip(),
            )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, simulation_id: (
            simulation if simulation_id == simulation.simulation_id else None
        ),
    )
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda project_id: project if project_id == project.project_id else None,
    )
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)

    result = report_tasks.generate_report_task.run(
        simulation_id=simulation.simulation_id,
        report_id="report-authoritative",
        task_id="task-authoritative",
        user_prompt="payload user prompt must be ignored",
        custom_instructions="payload instructions must be ignored",
        graph_id="payload-graph",
        decision_text="payload decision text",
        simulation_requirement="payload simulation requirement",
    )

    assert captured["context"] == {
        "graph_id": "project-graph",
        "simulation_id": "simulation-authoritative",
        "simulation_requirement": "Canonical decision text.",
    }
    assert captured["request"] == {
        "report_id": "report-authoritative",
        "generation_lease": None,
    }
    assert result == {"success": True, "report_id": "report-authoritative"}
    assert task_manager.completions == [
        (
            "task-authoritative",
            {
                "report_id": "report-authoritative",
                "simulation_id": simulation.simulation_id,
                "graph_id": project.graph_id,
                "status": "completed",
            },
        )
    ]
    assert task_manager.failures == []


def test_missing_simulation_fails_with_stable_code(monkeypatch):
    task_manager = _RecordingTaskManager()
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: None,
    )

    with pytest.raises(RuntimeError, match="^report_simulation_not_found$"):
        report_tasks.generate_report_task.run(
            simulation_id="simulation-private-caller-value",
            report_id="report-missing-simulation",
            task_id="task-missing-simulation",
        )

    assert task_manager.failures == [
        (
            "task-missing-simulation",
            "report_simulation_not_found",
            {"public_error": "report_simulation_not_found"},
        )
    ]


def test_missing_project_fails_with_stable_code(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="simulation-with-missing-project",
        project_id="project-private-caller-value",
        graph_id="unused-graph",
    )
    task_manager = _RecordingTaskManager()
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: None)

    with pytest.raises(RuntimeError, match="^report_project_not_found$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-missing-project",
            task_id="task-missing-project",
        )

    assert task_manager.failures == [
        (
            "task-missing-project",
            "report_project_not_found",
            {"public_error": "report_project_not_found"},
        )
    ]


def test_blank_project_requirement_fails_before_agent_construction(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="simulation-blank-requirement",
        project_id="project-blank-requirement",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="  \t\r\n  ",
    )
    task_manager = _RecordingTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("agent constructed for a blank requirement")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)

    with pytest.raises(
        RuntimeError,
        match="^report_simulation_requirement_missing$",
    ):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-blank-requirement",
            task_id="task-blank-requirement",
        )

    assert task_manager.failures == [
        (
            "task-blank-requirement",
            "report_simulation_requirement_missing",
            {"public_error": "report_simulation_requirement_missing"},
        )
    ]


def test_non_string_project_requirement_fails_with_stable_code(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="simulation-invalid-requirement",
        project_id="project-invalid-requirement",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement=None,
    )
    task_manager = _RecordingTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("agent constructed for an invalid requirement")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)

    with pytest.raises(
        RuntimeError,
        match="^report_simulation_requirement_missing$",
    ):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-invalid-requirement",
            task_id="task-invalid-requirement",
        )

    assert task_manager.failures == [
        (
            "task-invalid-requirement",
            "report_simulation_requirement_missing",
            {"public_error": "report_simulation_requirement_missing"},
        )
    ]


def test_missing_project_graph_fails_without_simulation_or_payload_fallback(
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-missing-project-graph",
        project_id="project-missing-graph",
        graph_id="simulation-fallback-must-not-be-used",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id=None,
        simulation_requirement="Canonical decision.",
    )
    task_manager = _RecordingTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("agent constructed without an authoritative graph")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)

    with pytest.raises(RuntimeError, match="^report_graph_id_missing$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-missing-project-graph",
            task_id="task-missing-project-graph",
            graph_id="payload-fallback-must-not-be-used",
        )

    assert task_manager.failures == [
        (
            "task-missing-project-graph",
            "report_graph_id_missing",
            {"public_error": "report_graph_id_missing"},
        )
    ]


def test_simulation_graph_mismatch_fails_closed(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="simulation-graph-mismatch",
        project_id="project-graph-mismatch",
        graph_id="simulation-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _RecordingTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("agent constructed across graph scopes")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)

    with pytest.raises(RuntimeError, match="^report_graph_scope_mismatch$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-graph-mismatch",
            task_id="task-graph-mismatch",
            graph_id="project-graph",
        )

    assert task_manager.failures == [
        (
            "task-graph-mismatch",
            "report_graph_scope_mismatch",
            {"public_error": "report_graph_scope_mismatch"},
        )
    ]


def test_provider_failure_is_sanitized_in_logs_task_state_and_exception(monkeypatch):
    decision_canary = "PRIVATE_DECISION_CANARY"
    provider_canary = "PRIVATE_PROVIDER_RESPONSE_CANARY"
    credential_canary = "sk-private-credential-canary"
    instruction_canary = "PRIVATE_CLIENT_INSTRUCTION_CANARY"
    simulation = SimpleNamespace(
        simulation_id="simulation-provider-failure",
        project_id="project-provider-failure",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement=decision_canary,
    )
    task_manager = _RecordingTaskManager()

    class _FailingReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **_request):
            raise RuntimeError(
                " | ".join(
                    (
                        provider_canary,
                        credential_canary,
                        decision_canary,
                        instruction_canary,
                    )
                )
            )

    class _RecordingLogger:
        def __init__(self) -> None:
            self.records = []

        def _record(self, level, message, args) -> None:
            self.records.append((level, message % args if args else message))

        def info(self, message, *args, **_kwargs) -> None:
            self._record("info", message, args)

        def error(self, message, *args, **_kwargs) -> None:
            self._record("error", message, args)

    recording_logger = _RecordingLogger()
    monkeypatch.setattr(report_tasks, "logger", recording_logger)
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _FailingReportAgent)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-provider-failure",
            task_id="task-provider-failure",
            user_prompt=instruction_canary,
            custom_instructions=instruction_canary,
        )

    assert task_manager.failures == [
        (
            "task-provider-failure",
            "report_generation_failed",
            {"public_error": "report_generation_failed"},
        )
    ]
    observable_text = repr((recording_logger.records, task_manager.failures))
    for sensitive_value in (
        decision_canary,
        provider_canary,
        credential_canary,
        instruction_canary,
    ):
        assert sensitive_value not in observable_text


def test_worker_uses_immutable_celery_request_id_over_payload_task_id(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="simulation-task-identity",
        project_id="project-task-identity",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _RecordingTaskManager()

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **request):
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation.simulation_id,
                graph_id=project.graph_id,
                status=ReportStatus.COMPLETED,
                simulation_requirement=project.simulation_requirement,
            )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)

    report_tasks.generate_report_task.apply(
        kwargs={
            "simulation_id": simulation.simulation_id,
            "report_id": "report-task-identity",
            "task_id": "mutable-payload-task-id",
        },
        task_id="immutable-celery-request-id",
    ).get(propagate=True)

    assert task_manager.updates[0][0] == "immutable-celery-request-id"
    assert task_manager.completions[0][0] == "immutable-celery-request-id"
    assert task_manager.failures == []


def test_padded_project_graph_id_fails_instead_of_being_passed_or_normalized(
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-padded-project-graph",
        project_id="project-padded-graph",
        graph_id=None,
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="  project-graph  ",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _RecordingTaskManager()

    class _ForbiddenReportAgent:
        def __init__(self, **_context) -> None:
            raise AssertionError("agent constructed with a padded graph ID")

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _ForbiddenReportAgent)

    with pytest.raises(RuntimeError, match="^report_graph_id_missing$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-padded-project-graph",
            task_id="task-padded-project-graph",
        )

    assert task_manager.failures == [
        (
            "task-padded-project-graph",
            "report_graph_id_missing",
            {"public_error": "report_graph_id_missing"},
        )
    ]


def test_initial_task_state_failure_is_sanitized_inside_worker_boundary(monkeypatch):
    storage_canary = "PRIVATE_TASK_UPDATE_STORAGE_CANARY"

    class _UpdateFailingTaskManager(_RecordingTaskManager):
        def update_task(self, task_id, **changes) -> None:
            raise RuntimeError(storage_canary)

    class _RecordingLogger:
        def __init__(self) -> None:
            self.records = []

        def info(self, message, *args, **_kwargs) -> None:
            self.records.append(message % args if args else message)

        def error(self, message, *args, **_kwargs) -> None:
            self.records.append(message % args if args else message)

    task_manager = _UpdateFailingTaskManager()
    recording_logger = _RecordingLogger()
    monkeypatch.setattr(report_tasks, "logger", recording_logger)
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: (_ for _ in ()).throw(
            AssertionError("context lookup ran after task-state initialization failed")
        ),
    )

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id="simulation-update-failure",
            report_id="report-update-failure",
            task_id="task-update-failure",
        )

    assert task_manager.failures == [
        (
            "task-update-failure",
            "report_generation_failed",
            {"public_error": "report_generation_failed"},
        )
    ]
    assert storage_canary not in repr(
        (recording_logger.records, task_manager.failures)
    )


def test_failure_persistence_error_cannot_replace_stable_worker_failure(monkeypatch):
    persistence_canary = "PRIVATE_FAIL_TASK_STORAGE_CANARY"
    simulation = SimpleNamespace(
        simulation_id="simulation-fail-task-error",
        project_id="project-fail-task-error",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _FailurePersistenceUnavailable(_RecordingTaskManager):
        def fail_task(self, task_id, error, **kwargs) -> None:
            raise RuntimeError(persistence_canary)

    class _FailingReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **_request):
            raise ConnectionError("private provider response")

    class _RecordingLogger:
        def __init__(self) -> None:
            self.records = []

        def info(self, message, *args, **_kwargs) -> None:
            self.records.append(message % args if args else message)

        def error(self, message, *args, **_kwargs) -> None:
            self.records.append(message % args if args else message)

    task_manager = _FailurePersistenceUnavailable()
    recording_logger = _RecordingLogger()
    monkeypatch.setattr(report_tasks, "logger", recording_logger)
    monkeypatch.setattr(report_tasks, "TaskManager", lambda: task_manager)
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
    monkeypatch.setattr(report_tasks, "ReportAgent", _FailingReportAgent)

    with pytest.raises(RuntimeError, match="^report_generation_failed$"):
        report_tasks.generate_report_task.run(
            simulation_id=simulation.simulation_id,
            report_id="report-fail-task-error",
            task_id="task-fail-task-error",
        )

    assert persistence_canary not in repr(recording_logger.records)

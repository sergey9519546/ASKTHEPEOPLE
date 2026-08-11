"""Canonical graph-input reads must distinguish absence from dependency failure."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from celery.exceptions import Retry

from app.services import project_repository
from app.models.project import ProjectStatus
from app.models.task import TaskStatus
from app.tasks import graph_tasks


class _StorageFailure(Exception):
    def __init__(self, *, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class _FailingStorage:
    def __init__(self, failure: Exception) -> None:
        self.failure = failure

    def download(self, **_kwargs) -> bytes:
        raise self.failure


class _TaskManager:
    def __init__(self) -> None:
        self.updates = []
        self.failures = []

    def update_task(self, task_id, **kwargs) -> None:
        self.updates.append((task_id, kwargs))

    def fail_task(self, task_id, error, **kwargs) -> None:
        self.failures.append((task_id, error, kwargs))


def _building_project():
    return SimpleNamespace(
        project_id="project-1",
        name="Canonical project",
        status=ProjectStatus.GRAPH_BUILDING,
        graph_id=None,
        graph_build_task_id="task-1",
        ontology={"entity_types": [], "edge_types": []},
        chunk_size=500,
        chunk_overlap=50,
    )


def test_canonical_source_transient_read_is_typed_retryable_and_sanitized(
    monkeypatch,
):
    raw_failure = _StorageFailure(
        status=503,
        code="ServiceUnavailable",
        message="raw provider response must stay private",
    )
    monkeypatch.setattr(project_repository, "is_storage_configured", lambda: True)
    monkeypatch.setattr(project_repository, "storage", _FailingStorage(raw_failure))

    with pytest.raises(RuntimeError, match="^canonical_source_read_failed$") as caught:
        project_repository.ProjectRepository.get_extracted_text("project-1")

    assert type(caught.value).__name__ == "CanonicalSourceReadError"
    assert caught.value.retryable is True
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert "raw provider response" not in str(caught.value)


def test_canonical_source_explicit_not_found_remains_absent(monkeypatch):
    raw_failure = _StorageFailure(
        status=404,
        code="NoSuchKey",
        message="provider-specific missing object response",
    )
    monkeypatch.setattr(project_repository, "is_storage_configured", lambda: True)
    monkeypatch.setattr(project_repository, "storage", _FailingStorage(raw_failure))

    assert project_repository.ProjectRepository.get_extracted_text("project-1") is None


def test_canonical_source_unconfigured_storage_is_not_reported_as_absent(monkeypatch):
    monkeypatch.setattr(project_repository, "is_storage_configured", lambda: False)

    with pytest.raises(RuntimeError, match="^canonical_source_read_failed$") as caught:
        project_repository.ProjectRepository.get_extracted_text("project-1")

    assert type(caught.value).__name__ == "CanonicalSourceReadError"
    assert caught.value.retryable is False


def test_canonical_source_deterministic_read_failure_is_typed_but_not_retryable(
    monkeypatch,
):
    raw_failure = _StorageFailure(
        status=403,
        code="AccessDenied",
        message="raw authorization response must stay private",
    )
    monkeypatch.setattr(project_repository, "is_storage_configured", lambda: True)
    monkeypatch.setattr(project_repository, "storage", _FailingStorage(raw_failure))

    with pytest.raises(RuntimeError, match="^canonical_source_read_failed$") as caught:
        project_repository.ProjectRepository.get_extracted_text("project-1")

    assert type(caught.value).__name__ == "CanonicalSourceReadError"
    assert caught.value.retryable is False
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert "raw authorization response" not in str(caught.value)


def test_graph_worker_retries_transient_canonical_source_read_before_provider_mutation(
    monkeypatch,
):
    project = _building_project()
    task_manager = _TaskManager()
    retry_calls = []
    project_failures = []
    source_failure = project_repository.CanonicalSourceReadError(retryable=True)
    source_failure.__cause__ = ConnectionError(
        "raw canonical storage response must stay private"
    )

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "get_project", lambda _project_id: project
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "ensure_graph_build_owner",
        lambda _project_id, _task_id: True,
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_extracted_text",
        lambda _project_id: (_ for _ in ()).throw(source_failure),
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "fail_graph_build",
        lambda *args: project_failures.append(args) or True,
    )
    monkeypatch.setattr(
        graph_tasks,
        "GraphBuilderService",
        lambda: (_ for _ in ()).throw(
            AssertionError("source retry must happen before provider mutation")
        ),
    )
    monkeypatch.setattr(graph_tasks.build_graph_task.request, "retries", 0, raising=False)

    def retry(**kwargs):
        retry_calls.append(kwargs)
        raise Retry()

    monkeypatch.setattr(graph_tasks.build_graph_task, "retry", retry)

    with pytest.raises(Retry):
        graph_tasks.build_graph_task.run(
            project_id="project-1",
            task_id="task-1",
        )

    assert len(retry_calls) == 1
    assert str(retry_calls[0]["exc"]) == "canonical_source_read_failed"
    assert retry_calls[0]["countdown"] == 1
    assert project_failures == []
    assert task_manager.failures == []
    assert task_manager.updates == [
        (
            "task-1",
            {
                "status": TaskStatus.PROCESSING,
                "progress": 5,
                "message": "Initializing graph build...",
            },
        )
    ]


def test_graph_worker_retries_transient_project_or_ontology_read_before_ownership(
    monkeypatch,
):
    class OperationalError(Exception):
        pass

    task_manager = _TaskManager()
    retry_calls = []
    raw_failure = OperationalError("raw database response must stay private")

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_project",
        lambda _project_id: (_ for _ in ()).throw(raw_failure),
    )
    monkeypatch.setattr(
        graph_tasks,
        "GraphBuilderService",
        lambda: (_ for _ in ()).throw(
            AssertionError("canonical-input retry must precede provider mutation")
        ),
    )
    monkeypatch.setattr(graph_tasks.build_graph_task.request, "retries", 0, raising=False)

    def retry(**kwargs):
        retry_calls.append(kwargs)
        raise Retry()

    monkeypatch.setattr(graph_tasks.build_graph_task, "retry", retry)

    with pytest.raises(Retry):
        graph_tasks.build_graph_task.run(
            project_id="project-1",
            task_id="task-1",
        )

    assert len(retry_calls) == 1
    assert str(retry_calls[0]["exc"]) == "canonical_graph_input_read_failed"
    assert "raw database response" not in str(retry_calls[0]["exc"])
    assert retry_calls[0]["countdown"] == 1
    assert task_manager.updates == []
    assert task_manager.failures == []


def test_graph_worker_treats_explicit_source_absence_as_stable_terminal(
    monkeypatch,
):
    project = _building_project()
    task_manager = _TaskManager()
    project_failures = []

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "get_project", lambda _project_id: project
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "ensure_graph_build_owner",
        lambda _project_id, _task_id: True,
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "get_extracted_text", lambda _project_id: None
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "fail_graph_build",
        lambda *args: project_failures.append(args) or True,
    )
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "retry",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("explicit absence must not retry")
        ),
    )
    monkeypatch.setattr(
        graph_tasks,
        "GraphBuilderService",
        lambda: (_ for _ in ()).throw(
            AssertionError("explicit absence must precede provider mutation")
        ),
    )

    with pytest.raises(RuntimeError, match="^graph_build_failed$"):
        graph_tasks.build_graph_task.run(
            project_id="project-1",
            task_id="task-1",
        )

    assert project_failures == [("project-1", "task-1", "graph_build_failed")]
    assert task_manager.failures == [
        (
            "task-1",
            "graph_build_failed",
            {"public_error": "graph_build_failed"},
        )
    ]

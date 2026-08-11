"""Retry-safety coverage for the Celery-owned Zep graph build workflow."""

import importlib.util

import pytest
from celery.exceptions import Retry

from app.models.project import Project, ProjectStatus
from app.services import graph_builder
from app.services.graph_builder import GraphBuilderService, GraphInfo
from app.tasks import graph_tasks


class _TaskManager:
    def __init__(self):
        self.updates = []
        self.completions = []
        self.failures = []

    def update_task(self, task_id, **kwargs):
        self.updates.append((task_id, kwargs))

    def complete_task(self, task_id, result):
        self.completions.append((task_id, result))

    def fail_task(self, task_id, error, **kwargs):
        self.failures.append((task_id, error, kwargs))


def _project(name="Server owned name"):
    return Project(
        project_id="project-1",
        name=name,
        status=ProjectStatus.ONTOLOGY_GENERATED,
        created_at="2026-08-08T00:00:00Z",
        updated_at="2026-08-08T00:00:00Z",
        ontology={"entity_types": [], "edge_types": []},
        chunk_size=42,
        chunk_overlap=7,
    )


def test_sync_build_reuses_the_caller_supplied_graph_id_after_safe_pre_episode_failure(monkeypatch):
    service = GraphBuilderService.__new__(GraphBuilderService)
    created_ids = []
    should_fail = {"value": True}

    service.create_graph = lambda graph_id, graph_name: created_ids.append(graph_id) or graph_id

    def set_ontology(graph_id, ontology):
        if should_fail["value"]:
            raise ConnectionError("provider reset")

    service.set_ontology = set_ontology
    service.add_text_batches = lambda *args, **kwargs: ["episode-1"]
    service._wait_for_episodes = lambda *args, **kwargs: None
    service._get_graph_info = lambda graph_id: GraphInfo(graph_id, 0, 0, [])
    monkeypatch.setattr(
        "app.services.graph_builder.TextProcessor.split_text",
        lambda text, chunk_size, chunk_overlap: [text],
    )

    with pytest.raises(RuntimeError) as first_failure:
        service.build_graph(
            graph_id="atp_stable_worker_id",
            text="canonical source",
            ontology={"entity_types": [], "edge_types": []},
            graph_name="server label",
            chunk_size=42,
            chunk_overlap=7,
        )

    assert getattr(first_failure.value, "retry_safe", False) is True
    should_fail["value"] = False
    result = service.build_graph(
        graph_id="atp_stable_worker_id",
        text="canonical source",
        ontology={"entity_types": [], "edge_types": []},
        graph_name="server label",
        chunk_size=42,
        chunk_overlap=7,
    )

    assert result["graph_id"] == "atp_stable_worker_id"
    assert created_ids == ["atp_stable_worker_id", "atp_stable_worker_id"]
    assert len(set(created_ids)) == 1


def test_sync_build_marks_episode_ingestion_failures_not_safe_to_retry(monkeypatch):
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.create_graph = lambda graph_id, graph_name: graph_id
    service.set_ontology = lambda graph_id, ontology: None
    service.add_text_batches = lambda *args, **kwargs: (_ for _ in ()).throw(
        ConnectionError("ambiguous episode submission")
    )
    monkeypatch.setattr(
        "app.services.graph_builder.TextProcessor.split_text",
        lambda text, chunk_size, chunk_overlap: [text],
    )

    with pytest.raises(RuntimeError) as failure:
        service.build_graph(
            graph_id="atp_stable_worker_id",
            text="canonical source",
            ontology={"entity_types": [], "edge_types": []},
            graph_name="server label",
            chunk_size=42,
            chunk_overlap=7,
        )

    assert getattr(failure.value, "retry_safe", True) is False


def test_episode_wait_raises_stable_error_on_poll_failure(monkeypatch):
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = type(
        "Client",
        (), {"graph": type("Graph", (), {"episode": type("Episode", (), {"get": staticmethod(lambda **kwargs: (_ for _ in ()).throw(ConnectionError("body")))})})},
    )()

    timestamps = iter([0, 0, 0, 2])
    monkeypatch.setattr(graph_builder.time, "time", lambda: next(timestamps))
    monkeypatch.setattr(graph_builder.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="graph_processing_failed"):
        service._wait_for_episodes(["episode-1"], timeout=1)


def test_episode_wait_raises_stable_error_on_timeout():
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = type(
        "Client",
        (), {"graph": type("Graph", (), {"episode": type("Episode", (), {"get": staticmethod(lambda **kwargs: type("Result", (), {"processed": False})())})})},
    )()

    with pytest.raises(RuntimeError, match="graph_processing_timeout"):
        service._wait_for_episodes(["episode-1"], timeout=0)


def test_worker_uses_server_project_name_and_server_generated_graph_id(monkeypatch):
    project = _project()
    task_manager = _TaskManager()
    calls = []

    class _Builder:
        def build_graph(self, **kwargs):
            calls.append(kwargs)
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    graph_tasks.build_graph_task.run(
        project_id="project-1",
        graph_name="untrusted client graph label",
        task_id="server-task-1",
        graph_id="untrusted client graph id",
    )

    assert calls[0]["graph_name"] == "Server owned name"
    assert calls[0]["graph_id"].startswith("atp_")
    assert calls[0]["graph_id"] != "untrusted client graph id"


def test_worker_uses_safe_graph_name_fallback(monkeypatch):
    project = _project(name="   ")
    calls = []

    class _Builder:
        def build_graph(self, **kwargs):
            calls.append(kwargs)
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    monkeypatch.setattr(graph_tasks, "TaskManager", _TaskManager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    graph_tasks.build_graph_task.run(project_id="project-1", task_id="server-task-1")

    assert calls[0]["graph_name"] == "Source graph"


def test_worker_reuses_stable_graph_id_across_safe_celery_retry(eager_celery, monkeypatch):
    project = _project()
    calls = []

    class _Builder:
        def build_graph(self, **kwargs):
            calls.append(kwargs["graph_id"])
            if len(calls) == 1:
                failure = graph_builder.GraphBuildProviderError(
                    "graph_create_phase_failed",
                    graph_id=kwargs["graph_id"],
                    retry_safe=True,
                )
                failure.__cause__ = ConnectionError("provider reset")
                raise failure
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    monkeypatch.setattr(graph_tasks, "TaskManager", _TaskManager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(Retry):
        graph_tasks.build_graph_task.apply(
            kwargs={"project_id": "project-1", "task_id": "server-task-1"},
            task_id="celery-build-1",
        ).get(propagate=True)
    result = graph_tasks.build_graph_task.apply(
        kwargs={"project_id": "project-1", "task_id": "server-task-1"},
        task_id="celery-build-1",
    ).get(propagate=True)

    assert result["graph_id"] == calls[0]
    assert calls == [calls[0], calls[0]]


@pytest.fixture
def eager_celery(monkeypatch):
    from app.celery_app import celery_app

    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    return celery_app


def test_worker_does_not_retry_ambiguous_episode_failure(eager_celery, monkeypatch):
    project = _project()
    task_manager = _TaskManager()

    class _AmbiguousEpisodeFailure(ConnectionError):
        retry_safe = False

    class _Builder:
        def build_graph(self, **kwargs):
            raise _AmbiguousEpisodeFailure("episode submission may have succeeded")

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(RuntimeError, match="graph_build_failed"):
        graph_tasks.build_graph_task.apply(
            kwargs={"project_id": "project-1", "task_id": "server-task-1"},
            task_id="server-task-1",
        ).get(propagate=True)

    assert task_manager.completions == []
    assert task_manager.failures == [
        ("server-task-1", "graph_build_failed", {"public_error": "graph_build_failed"})
    ]


def test_retry_exhaustion_persists_terminal_state_without_graph_id(monkeypatch):
    project = _project()
    project.graph_id = "must-not-remain-visible"
    task_manager = _TaskManager()
    saved = []

    class _Builder:
        def build_graph(self, **kwargs):
            failure = graph_builder.GraphBuildProviderError(
                "graph_create_phase_failed",
                graph_id=kwargs["graph_id"],
                retry_safe=True,
            )
            failure.__cause__ = TimeoutError("provider timeout")
            raise failure

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: saved.append((value.status, value.graph_id)))
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)
    monkeypatch.setattr(graph_tasks.build_graph_task.request, "retries", 3, raising=False)

    with pytest.raises(RuntimeError, match="graph_build_failed"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="server-task-1")

    assert saved[-1] == (ProjectStatus.FAILED, None)
    assert task_manager.failures == [
        ("server-task-1", "graph_build_failed", {"public_error": "graph_build_failed"})
    ]


def test_task_state_store_failure_is_guarded_and_never_provider_retried(monkeypatch):
    class _UnavailableTaskManager(_TaskManager):
        def update_task(self, task_id, **kwargs):
            raise ConnectionError("canonical task store unavailable")

    manager = _UnavailableTaskManager()
    project = _project()
    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "ensure_graph_build_owner", lambda *_args: True
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "fail_graph_build", lambda *_args: True, raising=False
    )

    with pytest.raises(RuntimeError, match="graph_build_failed"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="server-task-1")

    assert manager.failures == [
        ("server-task-1", "graph_build_failed", {"public_error": "graph_build_failed"})
    ]


def test_progress_store_failure_is_not_misclassified_as_provider_retry(
    eager_celery, monkeypatch
):
    project = _project()

    class _ProgressUnavailable(_TaskManager):
        def update_task(self, task_id, **kwargs):
            super().update_task(task_id, **kwargs)
            if len(self.updates) > 1:
                raise ConnectionError("canonical progress store unavailable")

    class _Builder:
        def build_graph(self, **kwargs):
            kwargs["progress_callback"](10, "Graph created")

    manager = _ProgressUnavailable()
    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(RuntimeError, match="graph_build_failed"):
        graph_tasks.build_graph_task.apply(
            kwargs={"project_id": "project-1", "task_id": "server-task-1"}
        ).get(propagate=True)


def test_shared_retry_classifier_has_its_own_module():
    assert importlib.util.find_spec("app.utils.task_retry") is not None

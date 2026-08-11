"""Final safety regressions for the Celery-owned source graph worker."""

import hashlib
from types import SimpleNamespace

import pytest

from app import create_app
from app.api import graph as graph_api
from app.config import Config
from app.models.project import Project, ProjectStatus
from app.services import graph_builder
from app.services.graph_builder import GraphBuilderService, GraphInfo
from app.tasks import graph_tasks


class _TaskManager:
    def __init__(self, *, complete_error=None):
        self.complete_error = complete_error
        self.updates = []
        self.completions = []
        self.failures = []

    def create_task(self, *args, **kwargs):
        return "route-task-1"

    def update_task(self, task_id, **kwargs):
        self.updates.append((task_id, kwargs))

    def complete_task(self, task_id, result):
        if self.complete_error:
            raise self.complete_error
        self.completions.append((task_id, result))

    def fail_task(self, task_id, error, **kwargs):
        self.failures.append((task_id, error, kwargs))


def _project(*, task_id=None):
    return Project(
        project_id="project-1",
        name="Canonical project name",
        status=(
            ProjectStatus.GRAPH_BUILDING
            if task_id is not None
            else ProjectStatus.ONTOLOGY_GENERATED
        ),
        created_at="2026-08-08T00:00:00Z",
        updated_at="2026-08-08T00:00:00Z",
        ontology={"entity_types": [], "edge_types": []},
        chunk_size=42,
        chunk_overlap=7,
        graph_build_task_id=task_id,
    )


def _successful_builder(calls):
    class _Builder:
        def build_graph(self, **kwargs):
            calls.append(kwargs)
            return {
                "success": True,
                "graph_id": kwargs["graph_id"],
                "graph_info": {},
            }

    return _Builder


@pytest.fixture
def graph_client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


@pytest.fixture
def eager_celery(monkeypatch):
    from app.celery_app import celery_app

    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    return celery_app


def test_build_route_only_enqueues_server_task_identity(graph_client, monkeypatch):
    class _RouteProject:
        project_id = "project-1"
        name = "Canonical project name"
        status = ProjectStatus.ONTOLOGY_GENERATED
        chunk_size = 42
        chunk_overlap = 7
        graph_build_task_id = None
        graph_id = None
        error = None

        @property
        def ontology(self):
            raise AssertionError("HTTP route must not read ontology")

    project = _RouteProject()
    dispatches = []
    manager = _TaskManager()
    monkeypatch.setattr(graph_api, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_extracted_text",
        lambda _id: (_ for _ in ()).throw(
            AssertionError("HTTP route must not read extracted text")
        ),
    )
    monkeypatch.setattr(graph_api.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "apply_async",
        lambda **kwargs: dispatches.append(kwargs),
    )
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "delay",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("route must dispatch with explicit Celery task_id")
        ),
    )

    response = graph_client.post(
        "/api/graph/build",
        json={"project_id": "project-1", "graph_name": "hostile client label"},
    )

    assert response.status_code == 202
    assert dispatches == [{
        "kwargs": {"project_id": "project-1"},
        "task_id": "route-task-1",
    }]
    assert project.graph_build_task_id == "route-task-1"


def test_worker_graph_id_uses_celery_request_id_not_mutable_project_task_id(
    eager_celery, monkeypatch
):
    project = _project(task_id=None)
    calls = []
    monkeypatch.setattr(graph_tasks, "TaskManager", _TaskManager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source"
    )
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _successful_builder(calls))

    graph_tasks.build_graph_task.apply(
        kwargs={"project_id": "project-1", "task_id": "mutable-payload-id"},
        task_id="immutable-celery-id",
    ).get(propagate=True)

    expected = graph_tasks._stable_graph_id("project-1", "immutable-celery-id")
    assert calls[0]["graph_id"] == expected


def test_stale_worker_is_failed_as_superseded_without_mutating_newer_project(
    monkeypatch,
):
    project = _project(task_id="newer-task-id")
    original = (project.status, project.graph_id, project.error)
    manager = _TaskManager()
    saves = []
    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_extracted_text",
        lambda _id: (_ for _ in ()).throw(
            AssertionError("superseded task must not load source")
        ),
    )
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", saves.append)
    monkeypatch.setattr(
        graph_tasks,
        "GraphBuilderService",
        lambda: (_ for _ in ()).throw(
            AssertionError("superseded task must not contact Zep")
        ),
    )

    with pytest.raises(RuntimeError, match="graph_build_superseded"):
        graph_tasks.build_graph_task.run(
            project_id="project-1", task_id="older-task-id"
        )

    assert (project.status, project.graph_id, project.error) == original
    assert saves == []
    assert manager.failures == [
        (
            "older-task-id",
            "graph_build_superseded",
            {"public_error": "graph_build_superseded"},
        )
    ]


def _owner_marker(graph_id):
    digest = hashlib.sha256(f"source-graph:{graph_id}".encode()).hexdigest()
    return f"source_graph_owner:{digest}"


class _Conflict(Exception):
    status_code = 409


def _conflict_service(*, description, episodes):
    service = GraphBuilderService.__new__(GraphBuilderService)

    class _Graph:
        episode = SimpleNamespace(
            get_by_graph_id=lambda **kwargs: episodes,
        )

        @staticmethod
        def create(**kwargs):
            raise _Conflict("provider body must stay private")

        @staticmethod
        def get(**kwargs):
            return SimpleNamespace(description=description)

    service.client = SimpleNamespace(graph=_Graph())
    return service


def test_create_conflict_reuses_only_exact_owned_empty_graph():
    graph_id = "atp_safe_conflict"
    service = _conflict_service(description=_owner_marker(graph_id), episodes=[])

    assert service.create_graph(graph_id, "Server name") == graph_id


def test_create_conflict_with_wrong_marker_never_inspects_episodes():
    service = GraphBuilderService.__new__(GraphBuilderService)

    class _Graph:
        episode = SimpleNamespace(
            get_by_graph_id=lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("wrong marker must stop before episode lookup")
            )
        )

        @staticmethod
        def create(**kwargs):
            raise _Conflict("conflict")

        @staticmethod
        def get(**kwargs):
            return SimpleNamespace(description="wrong-marker")

    service.client = SimpleNamespace(graph=_Graph())

    with pytest.raises(RuntimeError, match="graph_create_conflict_unsafe") as failure:
        service.create_graph("atp_conflict", "Server name")

    assert not isinstance(failure.value.__cause__, AssertionError)


@pytest.mark.parametrize(
    ("description", "episodes"),
    [
        ("hostile_graph_owner", []),
        (_owner_marker("atp_conflict"), [SimpleNamespace(uuid_="existing")]),
    ],
)
def test_create_conflict_rejects_wrong_marker_or_existing_episode(
    description, episodes
):
    service = _conflict_service(description=description, episodes=episodes)

    with pytest.raises(RuntimeError, match="graph_create_conflict_unsafe") as failure:
        service.create_graph("atp_conflict", "Server name")

    assert getattr(failure.value, "retry_safe", True) is False


@pytest.mark.parametrize(
    "batch_result",
    [
        [],
        None,
        [SimpleNamespace(uuid_=None)],
        [SimpleNamespace(uuid_="confirmed"), SimpleNamespace()],
    ],
)
def test_add_batch_requires_nonempty_all_uuid_acknowledgement(
    batch_result, monkeypatch
):
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = SimpleNamespace(
        graph=SimpleNamespace(add_batch=lambda **kwargs: batch_result)
    )
    monkeypatch.setattr(graph_builder.time, "sleep", lambda _seconds: None)

    with pytest.raises(
        RuntimeError, match="graph_episode_submission_unconfirmed"
    ) as failure:
        service.add_text_batches("graph-1", ["source chunk"])

    assert getattr(failure.value, "retry_safe", True) is False


def test_empty_chunks_cannot_complete(monkeypatch):
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.create_graph = lambda graph_id, graph_name: graph_id
    service.set_ontology = lambda graph_id, ontology: None
    service.add_text_batches = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("empty chunks must be rejected before submission")
    )
    monkeypatch.setattr(graph_builder.TextProcessor, "split_text", lambda *args: [])

    with pytest.raises(
        RuntimeError, match="graph_episode_submission_unconfirmed"
    ) as failure:
        service.build_graph(
            graph_id="graph-1",
            text="source",
            ontology={},
            graph_name="Server name",
            chunk_size=42,
            chunk_overlap=7,
        )

    assert getattr(failure.value, "retry_safe", True) is False


def test_transient_episode_poll_recovers_internally_without_resubmission(
    monkeypatch,
):
    service = GraphBuilderService.__new__(GraphBuilderService)
    poll_attempts = []
    submissions = []
    service.create_graph = lambda graph_id, graph_name: graph_id
    service.set_ontology = lambda graph_id, ontology: None
    service.add_text_batches = lambda *args, **kwargs: (
        submissions.append(args[0]) or ["episode-1"]
    )

    def poll(**kwargs):
        poll_attempts.append(kwargs)
        if len(poll_attempts) == 1:
            raise ConnectionError("temporary reset")
        return SimpleNamespace(processed=True)

    service.client = SimpleNamespace(
        graph=SimpleNamespace(episode=SimpleNamespace(get=poll))
    )
    service._get_graph_info = lambda graph_id: GraphInfo(graph_id, 0, 0, [])
    monkeypatch.setattr(graph_builder.TextProcessor, "split_text", lambda *args: ["source"])
    monkeypatch.setattr(graph_builder.time, "sleep", lambda _seconds: None)

    result = service.build_graph(
        graph_id="graph-1",
        text="source",
        ontology={},
        graph_name="Server name",
        chunk_size=42,
        chunk_overlap=7,
    )

    assert result["success"] is True
    assert submissions == ["graph-1"]
    assert len(poll_attempts) == 2


def test_transient_episode_poll_exhaustion_is_terminal_without_resubmission(
    monkeypatch,
):
    service = GraphBuilderService.__new__(GraphBuilderService)
    poll_attempts = []
    submissions = []
    service.create_graph = lambda graph_id, graph_name: graph_id
    service.set_ontology = lambda graph_id, ontology: None
    service.add_text_batches = lambda *args, **kwargs: (
        submissions.append(args[0]) or ["episode-1"]
    )
    service.client = SimpleNamespace(
        graph=SimpleNamespace(
            episode=SimpleNamespace(
                get=lambda **kwargs: (
                    poll_attempts.append(kwargs),
                    (_ for _ in ()).throw(ConnectionError("still unavailable")),
                )[1]
            )
        )
    )
    monkeypatch.setattr(graph_builder.TextProcessor, "split_text", lambda *args: ["source"])
    monkeypatch.setattr(graph_builder.time, "sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="graph_processing_failed") as failure:
        service.build_graph(
            graph_id="graph-1",
            text="source",
            ontology={},
            graph_name="Server name",
            chunk_size=42,
            chunk_overlap=7,
        )

    assert getattr(failure.value, "retry_safe", True) is False
    assert submissions == ["graph-1"]
    assert len(poll_attempts) == 3


def test_task_completion_store_failure_preserves_completed_project(
    monkeypatch, caplog
):
    project = _project(task_id="task-1")
    manager = _TaskManager(
        complete_error=ConnectionError("canonical task store unavailable")
    )
    saves = []
    calls = []
    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source"
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "save_project",
        lambda value: saves.append((value.status, value.graph_id, value.error)),
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _successful_builder(calls))

    with pytest.raises(
        RuntimeError, match="graph_task_completion_persistence_failed"
    ):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert project.status is ProjectStatus.GRAPH_COMPLETED
    assert project.graph_id == calls[0]["graph_id"]
    assert saves[-1][0] is ProjectStatus.GRAPH_COMPLETED
    assert all(status is not ProjectStatus.FAILED for status, _, _ in saves)
    assert "graph_task_completion_persistence_failed" in caplog.text


def test_project_completion_save_failure_logs_reconciliation_id_even_if_fail_save_fails(
    monkeypatch, caplog
):
    project = _project(task_id="task-1")
    manager = _TaskManager()
    calls = []
    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "ensure_graph_build_owner", lambda *_args: True
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source"
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "complete_graph_build",
        lambda *_args: (_ for _ in ()).throw(
            OSError("source text and provider body must not be logged")
        ),
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "fail_graph_build",
        lambda *_args: (_ for _ in ()).throw(
            OSError("source text and provider body must not be logged")
        ),
        raising=False,
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _successful_builder(calls))

    with pytest.raises(RuntimeError, match="graph_build_persistence_failed"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    reconciliation_id = calls[0]["graph_id"]
    assert project.status is ProjectStatus.GRAPH_BUILDING
    assert project.graph_id is None
    assert f"graph_id={reconciliation_id}" in caplog.text
    assert "source text and provider body" not in caplog.text

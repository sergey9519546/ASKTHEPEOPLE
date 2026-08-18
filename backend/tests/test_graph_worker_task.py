"""Focused coverage for the Celery-owned source graph build workflow."""

from unittest.mock import ANY

import pytest
from celery.exceptions import Retry

from app.models.project import Project, ProjectStatus
from app.services.graph_builder import GraphBuilderService, GraphInfo
from app.tasks import graph_tasks
from app.utils.zep_paging import _fetch_page_with_retry


class _RecordingTaskManager:
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


def _project():
    return Project(
        project_id="project-1",
        name="Canonical source",
        status=ProjectStatus.ONTOLOGY_GENERATED,
        created_at="2026-08-08T00:00:00Z",
        updated_at="2026-08-08T00:00:00Z",
        ontology={"entity_types": [], "edge_types": []},
        chunk_size=42,
        chunk_overlap=7,
    )


def test_ontology_worker_uses_immutable_celery_delivery_id(
    eager_celery,
    monkeypatch,
):
    project = _project()
    manager = _RecordingTaskManager()
    saves = []

    class _Generator:
        # Mirrors the real OntologyGenerator.generate signature
        # (document_texts: List[str], simulation_requirement: str,
        #  additional_context: Optional[str]). If the task ever regresses to
        # passing a raw string or an unexpected `requirements=` keyword, this
        # raises TypeError and the test fails — pinning the call shape.
        def generate(
            self,
            document_texts,
            simulation_requirement=None,
            additional_context=None,
        ):
            assert isinstance(document_texts, list), (
                "task must pass document_texts as a list"
            )
            return {
                "entity_types": [],
                "edge_types": [],
                "analysis_summary": "safe summary",
            }

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "save_project",
        lambda value, **kwargs: saves.append(kwargs),
    )
    monkeypatch.setattr(graph_tasks, "OntologyGenerator", _Generator)

    result = graph_tasks.generate_ontology_task.apply(
        kwargs={
            "project_id": "project-1",
            "text": "harmless source",
            "task_id": "mutable-payload-id",
        },
        task_id="immutable-celery-id",
    ).get(propagate=True)

    assert result == {"success": True, "project_id": "project-1"}
    assert manager.updates[0][0] == "immutable-celery-id"
    assert manager.completions[0][0] == "immutable-celery-id"
    assert saves == [{"_ontology_task_id": "immutable-celery-id"}]


def test_ontology_task_runs_against_real_generator_contract(
    eager_celery,
    monkeypatch,
):
    """Pin the task to the REAL OntologyGenerator contract (no mock).

    The task previously called ``generator.generate(text, requirements=...)``
    (wrong signature) and checked ``result.get("success")`` while reading
    ``result["ontology"]``/``result["summary"]`` — none of which match the real
    generator, which takes ``(document_texts: List[str], simulation_requirement,
    additional_context)`` and returns ``{entity_types, edge_types,
    analysis_summary}``. Tests passed because the fake generator encoded the
    task's wrong assumption.

    This test runs the REAL OntologyGenerator end-to-end (only the LLM
    transport is stubbed, so no network call in CI). If the task ever regresses
    to a wrong call shape it raises TypeError; if it reads the wrong result
    shape the project is left FAILED instead of ONTOLOGY_GENERATED.
    """
    import app.services.ontology_generator as og_module

    project = _project()
    manager = _RecordingTaskManager()
    saves = []

    class _FakeLLM:
        def chat_with_registry_prompt(self, **kwargs):
            return {
                "data": {
                    "entity_types": [
                        {"name": "Commuter", "description": "A regular bus user"},
                        {
                            "name": "CityOfficial",
                            "description": "A transport official",
                        },
                    ],
                    "edge_types": [
                        {"name": "affected_by", "description": "relationship"},
                    ],
                    "analysis_summary": "synthetic summary",
                }
            }

    # The real OntologyGenerator() constructor builds LLMClient(prefer_boost=True).
    # Swap that transport for a stub so the real generate() runs its signature,
    # _validate_and_process, and return shape without a network call.
    monkeypatch.setattr(og_module, "LLMClient", lambda **kwargs: _FakeLLM())

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "save_project",
        lambda value, **kwargs: saves.append((value, kwargs)),
    )

    result = graph_tasks.generate_ontology_task.apply(
        kwargs={
            "project_id": "project-1",
            "text": "What could happen if the city raises bus fares?",
            "requirements": "What could happen if the city raises bus fares?",
            "task_id": "ontology-real-contract",
        },
        task_id="ontology-real-contract",
    ).get(propagate=True)

    assert result == {"success": True, "project_id": "project-1"}
    assert project.status == ProjectStatus.ONTOLOGY_GENERATED
    assert project.analysis_summary == "synthetic summary"
    # The real generator adds Person/Organization fallbacks, so the persisted
    # ontology is structurally valid and non-empty.
    entity_names = {e["name"] for e in project.ontology["entity_types"]}
    assert {"Commuter", "CityOfficial", "Person", "Organization"} <= entity_names
    assert "affected_by" in {e["name"] for e in project.ontology["edge_types"]}
    assert manager.completions[0][0] == "ontology-real-contract"
    assert manager.completions[0][1]["ontology"] == project.ontology


def test_synchronous_build_runs_the_complete_zep_sequence_and_returns_data():
    """The worker-owned service operation is synchronous and serializable."""
    service = GraphBuilderService.__new__(GraphBuilderService)
    calls = []
    service.create_graph = lambda graph_id, name: calls.append(
        ("create", graph_id, name)
    ) or graph_id
    service.set_ontology = lambda graph_id, ontology: calls.append(
        ("ontology", graph_id, ontology)
    )
    service.add_text_batches = lambda graph_id, chunks, batch_size, progress_callback: (
        calls.append(("episodes", graph_id, chunks, batch_size)) or ["episode-1"]
    )
    service._wait_for_episodes = lambda episode_ids, progress_callback: calls.append(
        ("wait", episode_ids)
    )
    service._get_graph_info = lambda graph_id: calls.append(("info", graph_id)) or GraphInfo(
        graph_id=graph_id,
        node_count=2,
        edge_count=1,
        entity_types=["Person"],
    )

    result = service.build_graph(
        graph_id="graph-1",
        text="canonical extracted source",
        ontology={"entity_types": [], "edge_types": []},
        graph_name="Worker graph",
        chunk_size=42,
        chunk_overlap=7,
        batch_size=1,
    )

    assert result == {
        "success": True,
        "graph_id": "graph-1",
        "graph_info": {
            "graph_id": "graph-1",
            "node_count": 2,
            "edge_count": 1,
            "entity_types": ["Person"],
        },
        "chunks_processed": 1,
    }
    assert [call[0] for call in calls] == ["create", "ontology", "episodes", "wait", "info"]


def test_graph_paging_retry_does_not_log_provider_response_bodies(caplog):
    secret_provider_body = "provider response: canonical extracted source"

    def unavailable_page():
        raise OSError(secret_provider_body)

    with pytest.raises(OSError, match="canonical extracted source"):
        _fetch_page_with_retry(
            unavailable_page,
            max_retries=1,
            page_description="worker graph info",
        )

    assert secret_provider_body not in caplog.text


def test_worker_loads_canonical_inputs_and_persists_completed_graph(monkeypatch):
    project = _project()
    manager = _RecordingTaskManager()
    saved = []
    builder_calls = []

    class _Builder:
        def build_graph(self, **kwargs):
            builder_calls.append(kwargs)
            return {
                "success": True,
                "graph_id": kwargs["graph_id"],
                "graph_info": {},
            }

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_extracted_text",
        lambda project_id: "canonical extracted source",
    )
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: saved.append(value.status))
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    result = graph_tasks.build_graph_task.run(
        project_id="project-1",
        graph_name="Client label only",
        task_id="task-1",
        text="untrusted payload must not be used",
        ontology={"entity_types": [{"name": "untrusted"}]},
        graph_id="untrusted-graph-id",
    )

    assert result["success"] is True
    assert project.status is ProjectStatus.GRAPH_COMPLETED
    assert project.graph_id == builder_calls[0]["graph_id"]
    assert saved == [ProjectStatus.GRAPH_BUILDING, ProjectStatus.GRAPH_COMPLETED]
    assert builder_calls == [{
        "graph_id": ANY,
        "text": "canonical extracted source",
        "ontology": project.ontology,
        "graph_name": "Canonical source",
        "chunk_size": 42,
        "chunk_overlap": 7,
        "progress_callback": ANY,
    }]
    assert manager.completions == [("task-1", result)]


def test_worker_fails_closed_with_a_stable_error_when_completion_persistence_fails(monkeypatch):
    project = _project()
    manager = _RecordingTaskManager()
    saves = []

    class _Builder:
        def build_graph(self, **kwargs):
            return {"success": True, "graph_id": "zep-created-before-save", "graph_info": {}}

    def save_project(value):
        saves.append(value.status)

    def complete_graph_build(*_args):
        raise OSError("provider response included canonical extracted source")

    def fail_graph_build(_project_id, _expected_task_id, error):
        project.status = ProjectStatus.FAILED
        project.error = error
        project.graph_id = None
        saves.append(project.status)
        return True

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical extracted source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", save_project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager, "complete_graph_build", complete_graph_build
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "fail_graph_build",
        fail_graph_build,
        raising=False,
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(RuntimeError, match="graph_build_persistence_failed"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert saves == [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED]
    assert project.status is ProjectStatus.FAILED
    assert project.error == "graph_build_persistence_failed"
    assert project.graph_id is None
    assert manager.failures == [
        ("task-1", "graph_build_persistence_failed", {"public_error": "graph_build_failed"})
    ]


@pytest.fixture
def eager_celery(monkeypatch):
    from app.celery_app import celery_app

    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    return celery_app


def test_worker_retries_only_transient_provider_failures(eager_celery, monkeypatch):
    project = _project()
    manager = _RecordingTaskManager()

    class _Builder:
        def build_graph(self, **kwargs):
            raise ConnectionError("provider reset")

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical extracted source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(Retry):
        graph_tasks.build_graph_task.apply(
            kwargs={"project_id": "project-1", "task_id": None}
        ).get(propagate=True)


def test_worker_does_not_retry_deterministic_provider_failures(eager_celery, monkeypatch):
    project = _project()
    manager = _RecordingTaskManager()

    class _Unauthorized(Exception):
        status_code = 401

    class _Builder:
        def build_graph(self, **kwargs):
            raise _Unauthorized("credentials must not be disclosed")

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda project_id: "canonical extracted source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(RuntimeError, match="graph_build_failed"):
        graph_tasks.build_graph_task.apply(
            kwargs={"project_id": "project-1", "task_id": "task-1"},
            task_id="task-1",
        ).get(propagate=True)

    assert manager.failures == [
        ("task-1", "graph_build_failed", {"public_error": "graph_build_failed"})
    ]

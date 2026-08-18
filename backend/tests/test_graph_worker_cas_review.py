"""Review regressions for graph-build acknowledgements, fencing, and dispatch."""

import hashlib
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from sqlalchemy import JSON, bindparam, create_engine, text

from app import create_app
from app.api import graph as graph_api
from app.config import Config
from app.models import project as project_module
from app.models import task as task_module
from app.models.project import Project, ProjectManager, ProjectStatus
from app.models.task import TaskManager, TaskStatus
from app.services import graph_builder
from app.services.graph_builder import GraphBuilderService
from app.services.project_repository import ProjectRepository
from app.tasks import graph_tasks
from app.utils import zep_paging


class _TaskManager:
    def __init__(self, complete_error=None):
        self.complete_error = complete_error
        self.created = []
        self.updates = []
        self.completions = []
        self.failures = []

    def create_task(self, *args, **kwargs):
        self.created.append((args, kwargs))
        return "task-1"

    def update_task(self, task_id, **kwargs):
        self.updates.append((task_id, kwargs))

    def complete_task(self, task_id, result):
        if self.complete_error:
            raise self.complete_error
        self.completions.append((task_id, result))

    def get_task(self, task_id):
        return SimpleNamespace(status=TaskStatus.PROCESSING)

    def fail_task(self, task_id, error, **kwargs):
        self.failures.append((task_id, error, kwargs))


def _project(task_id="task-1"):
    return Project(
        project_id="project-1",
        name="Canonical project",
        status=ProjectStatus.GRAPH_BUILDING,
        created_at="2026-08-08T00:00:00Z",
        updated_at="2026-08-08T00:00:00Z",
        ontology={"entity_types": [], "edge_types": []},
        chunk_size=42,
        chunk_overlap=7,
        graph_build_task_id=task_id,
    )


def test_partial_episode_acknowledgement_is_terminal(monkeypatch):
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = SimpleNamespace(
        graph=SimpleNamespace(
            add_batch=lambda **kwargs: [
                SimpleNamespace(uuid_="00000000-0000-0000-0000-000000000001")
            ]
        )
    )
    monkeypatch.setattr(graph_builder.time, "sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="graph_episode_submission_unconfirmed"):
        service.add_text_batches("graph-1", ["first", "second"], batch_size=2)


@pytest.mark.parametrize(
    ("source_name", "expected_name"),
    [
        ("CanaryPerson", "CanaryPerson"),
        ("CanaryRelationship", "CanaryRelationship"),
        ("canary_person", "CanaryPerson"),
        ("canary relationship", "CanaryRelationship"),
    ],
)
def test_ontology_type_names_preserve_existing_pascal_case(source_name, expected_name):
    assert graph_builder._to_pascal_case(source_name) == expected_name


def test_complete_graph_build_rejects_a_superseded_task_without_publishing(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    project = _project(task_id="newer-task")
    ProjectManager.save_project(project)

    completed = ProjectManager.complete_graph_build(
        project.project_id,
        expected_task_id="older-task",
        graph_id="atp_old_graph",
    )

    persisted = ProjectManager.get_project(project.project_id)
    assert completed is False
    assert persisted.status is ProjectStatus.GRAPH_BUILDING
    assert persisted.graph_build_task_id == "newer-task"
    assert persisted.graph_id is None


def test_fail_graph_build_rejects_a_superseded_task_without_mutating_it(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    newer = _project(task_id="newer-task")
    newer.graph_id = "atp_newer_in_progress"
    ProjectManager.save_project(newer)

    failed = ProjectManager.fail_graph_build(
        newer.project_id,
        expected_task_id="older-task",
        error="graph_processing_failed",
    )

    persisted = ProjectManager.get_project(newer.project_id)
    assert failed is False
    assert persisted.status is ProjectStatus.GRAPH_BUILDING
    assert persisted.graph_build_task_id == "newer-task"
    assert persisted.graph_id == "atp_newer_in_progress"
    assert persisted.error is None


def test_fail_graph_build_marks_the_current_owner_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    current = _project(task_id="task-1")
    current.graph_id = "must-not-remain-client-visible"
    ProjectManager.save_project(current)

    failed = ProjectManager.fail_graph_build(
        current.project_id,
        expected_task_id="task-1",
        error="graph_processing_failed",
    )

    persisted = ProjectManager.get_project(current.project_id)
    assert failed is True
    assert persisted.status is ProjectStatus.FAILED
    assert persisted.graph_build_task_id == "task-1"
    assert persisted.graph_id is None
    assert persisted.error == "graph_processing_failed"


def test_legacy_non_force_begin_cas_allows_only_one_stale_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    project = _project(task_id=None)
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    ProjectManager.save_project(project)

    first_started = ProjectManager.begin_graph_build(
        project.project_id,
        "task-first",
        chunk_size=42,
        chunk_overlap=7,
        expected_status=ProjectStatus.ONTOLOGY_GENERATED,
        expected_task_id=None,
        force=False,
    )
    stale_second_started = ProjectManager.begin_graph_build(
        project.project_id,
        "task-second",
        chunk_size=42,
        chunk_overlap=7,
        expected_status=ProjectStatus.ONTOLOGY_GENERATED,
        expected_task_id=None,
        force=False,
    )

    persisted = ProjectManager.get_project(project.project_id)
    assert first_started is True
    assert stale_second_started is False
    assert persisted.status is ProjectStatus.GRAPH_BUILDING
    assert persisted.graph_build_task_id == "task-first"


def test_legacy_force_begin_cas_rejects_a_stale_owner_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    project = _project(task_id="task-original")
    ProjectManager.save_project(project)

    replacement_started = ProjectManager.begin_graph_build(
        project.project_id,
        "task-replacement",
        chunk_size=42,
        chunk_overlap=7,
        expected_status=ProjectStatus.GRAPH_BUILDING,
        expected_task_id="task-original",
        force=True,
    )
    stale_force_started = ProjectManager.begin_graph_build(
        project.project_id,
        "task-stale-force",
        chunk_size=42,
        chunk_overlap=7,
        expected_status=ProjectStatus.GRAPH_BUILDING,
        expected_task_id="task-original",
        force=True,
    )

    persisted = ProjectManager.get_project(project.project_id)
    assert replacement_started is True
    assert stale_force_started is False
    assert persisted.status is ProjectStatus.GRAPH_BUILDING
    assert persisted.graph_build_task_id == "task-replacement"


def test_legacy_dispatch_unwind_never_overwrites_worker_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    completed = _project(task_id="task-1")
    completed.status = ProjectStatus.GRAPH_COMPLETED
    completed.graph_id = graph_tasks._stable_graph_id("project-1", "task-1")
    ProjectManager.save_project(completed)

    restored = ProjectManager.unwind_graph_build_dispatch(
        "project-1",
        "task-1",
        {
            "status": ProjectStatus.ONTOLOGY_GENERATED,
            "graph_id": None,
            "graph_build_task_id": None,
            "error": "graph_dispatch_failed",
        },
    )

    persisted = ProjectManager.get_project("project-1")
    assert restored is False
    assert persisted.status is ProjectStatus.GRAPH_COMPLETED
    assert persisted.graph_build_task_id == "task-1"
    assert persisted.graph_id == completed.graph_id


def test_graph_task_requeues_on_worker_loss_without_global_celery_changes():
    assert graph_tasks.build_graph_task.acks_late is True
    assert graph_tasks.build_graph_task.reject_on_worker_lost is True


def test_task_completion_audit_failure_never_downgrades_real_completed_task(
    monkeypatch,
):
    monkeypatch.setenv("REDIS_URL", "memory://")
    manager = TaskManager()
    task_id = "graph-completion-audit-regression"
    manager._tasks.pop(task_id, None)
    manager.create_task("graph_build", task_id=task_id)
    result = {"success": True, "graph_id": "atp_completed"}

    def fail_completion_audit(**event):
        if event.get("action") == "task.completed":
            raise RuntimeError("audit sink unavailable after task write")

    monkeypatch.setattr(task_module, "_audit", fail_completion_audit)

    graph_tasks._complete_task_envelope(manager, task_id, result, "project-1")

    persisted = manager.get_task(task_id)
    assert persisted.status is TaskStatus.COMPLETED
    assert persisted.result == result
    assert persisted.error is None
    manager._tasks.pop(task_id, None)


def test_ensure_owner_never_reopens_a_completed_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    completed = _project(task_id="task-1")
    completed.status = ProjectStatus.GRAPH_COMPLETED
    completed.graph_id = graph_tasks._stable_graph_id("project-1", "task-1")
    ProjectManager.save_project(completed)

    claimed = ProjectManager.ensure_graph_build_owner("project-1", "task-1")

    persisted = ProjectManager.get_project("project-1")
    assert claimed is False
    assert persisted.status is ProjectStatus.GRAPH_COMPLETED
    assert persisted.graph_id == completed.graph_id


def test_repository_owner_claim_requires_building_same_owner_or_ready_unassigned(monkeypatch):
    calls = []

    class _Result:
        rowcount = 1

    class _Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return _Result()

    class _Begin:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        def begin(self):
            return _Begin()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    assert ProjectRepository.ensure_graph_build_owner("project-1", "task-1") is True
    statement, params = calls[0]
    assert "graph_build_task_id = :expected_task_id" in statement
    assert "status = :building_status" in statement
    assert "graph_build_task_id IS NULL" in statement
    assert "status = :ready_status" in statement
    assert params["ready_status"] == ProjectStatus.ONTOLOGY_GENERATED.value


def test_repository_begin_graph_build_uses_snapshot_cas_and_rowcount(monkeypatch):
    calls = []
    rowcounts = iter([1, 0])

    class _Result:
        def __init__(self):
            self.rowcount = next(rowcounts)

    class _Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return _Result()

    class _Begin:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        def begin(self):
            return _Begin()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    kwargs = {
        "chunk_size": 42,
        "chunk_overlap": 7,
        "expected_status": ProjectStatus.ONTOLOGY_GENERATED,
        "expected_task_id": None,
        "force": False,
    }
    assert ProjectRepository.begin_graph_build(
        "project-1", "task-first", **kwargs
    ) is True
    assert ProjectRepository.begin_graph_build(
        "project-1", "task-second", **kwargs
    ) is False

    statement, params = calls[0]
    assert "status = :expected_status" in statement
    assert "graph_build_task_id IS NULL" in statement
    assert "graph_build_task_id = :expected_task_id" in statement
    assert ":force" in statement
    assert "status != :building_status" in statement
    assert params["expected_status"] == ProjectStatus.ONTOLOGY_GENERATED.value
    assert params["expected_task_id"] is None
    assert params["force"] is False


def test_repository_completion_uses_conditional_task_ownership_update(monkeypatch):
    calls = []

    class _Result:
        rowcount = 1

    class _Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return _Result()

    class _Begin:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        def begin(self):
            return _Begin()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    assert ProjectRepository.complete_graph_build(
        "project-1", expected_task_id="task-1", graph_id="atp_graph"
    ) is True
    statement, params = calls[0]
    assert "graph_build_task_id = :expected_task_id" in statement
    assert "status = :building_status" in statement
    assert params["expected_task_id"] == "task-1"


def test_repository_failure_uses_conditional_task_ownership_update(monkeypatch):
    calls = []
    rowcounts = iter([1, 0])

    class _Result:
        def __init__(self):
            self.rowcount = next(rowcounts)

    class _Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return _Result()

    class _Begin:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        def begin(self):
            return _Begin()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    assert ProjectRepository.fail_graph_build(
        "project-1",
        expected_task_id="task-1",
        error="graph_processing_failed",
    ) is True
    statement, params = calls[0]
    assert "graph_build_task_id = :expected_task_id" in statement
    assert "status = :building_status" in statement
    assert "graph_id = NULL" in statement
    assert params["expected_task_id"] == "task-1"
    assert params["error"] == "graph_processing_failed"
    assert ProjectRepository.fail_graph_build(
        "project-1",
        expected_task_id="task-1",
        error="graph_processing_failed",
    ) is False


def test_worker_does_not_publish_or_complete_after_mid_build_supersession(monkeypatch):
    older = _project(task_id="task-1")
    newer = _project(task_id="task-2")
    state = {"project": older}
    manager = _TaskManager()
    saved = []

    class _Builder:
        def build_graph(self, **kwargs):
            state["project"] = newer
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: state["project"])
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: saved.append(value))
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "complete_graph_build",
        lambda project_id, expected_task_id, graph_id: False,
        raising=False,
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(RuntimeError, match="graph_build_superseded"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert state["project"] is newer
    assert newer.status is ProjectStatus.GRAPH_BUILDING
    assert manager.completions == []
    assert manager.failures[-1] == (
        "task-1", "graph_build_superseded", {"public_error": "graph_build_superseded"}
    )


def test_worker_terminal_failure_does_not_overwrite_mid_build_supersession(monkeypatch):
    older = _project(task_id="task-1")
    newer = _project(task_id="task-2")
    state = {"project": older}
    manager = _TaskManager()

    class _Builder:
        def build_graph(self, **kwargs):
            state["project"] = newer
            raise graph_builder.GraphBuildProviderError(
                "graph_processing_failed",
                graph_id=kwargs["graph_id"],
                retry_safe=False,
            )

    def save_project(value):
        state["project"] = value

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: state["project"])
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", save_project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "fail_graph_build",
        lambda project_id, expected_task_id, error: False,
        raising=False,
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(RuntimeError, match="graph_build_superseded"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert state["project"] is newer
    assert newer.status is ProjectStatus.GRAPH_BUILDING
    assert newer.graph_build_task_id == "task-2"
    assert newer.error is None
    assert manager.completions == []


def test_duplicate_completed_delivery_returns_existing_success_without_provider_call(monkeypatch):
    project = _project(task_id="task-1")
    project.status = ProjectStatus.GRAPH_COMPLETED
    project.graph_id = graph_tasks._stable_graph_id("project-1", "task-1")
    manager = _TaskManager()

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_extracted_text",
        lambda _id: (_ for _ in ()).throw(
            AssertionError("completed redelivery must not reload source")
        ),
    )
    monkeypatch.setattr(
        graph_tasks,
        "GraphBuilderService",
        lambda: (_ for _ in ()).throw(
            AssertionError("completed redelivery must not contact provider")
        ),
    )

    result = graph_tasks.build_graph_task.run(
        project_id="project-1", task_id="task-1"
    )

    assert result == {
        "success": True,
        "graph_id": project.graph_id,
        "status": "completed",
    }
    assert project.status is ProjectStatus.GRAPH_COMPLETED
    assert manager.completions == [("task-1", result)]
    assert manager.updates == []


def test_canonical_worker_loads_latest_completed_ontology_from_migration_shape(monkeypatch):
    ontology = {"entity_types": [{"name": "CanaryPerson"}], "edge_types": []}
    calls = []
    sql_calls = []

    class _Result:
        def __init__(self, statement):
            self.statement = statement
            self.rowcount = 1

        def mappings(self):
            return self

        def one_or_none(self):
            return {
                "id": 17,
                "project_id": "project-1",
                "name": "Canonical project",
                "status": ProjectStatus.GRAPH_BUILDING.value,
                "created_at": None,
                "updated_at": None,
                "total_text_length": 6,
                "chunk_size": 42,
                "chunk_overlap": 7,
                "analysis_summary": None,
                "simulation_requirement": None,
                "graph_id": None,
                "graph_build_task_id": "task-1",
                "error": None,
            }

        def scalar_one_or_none(self):
            return ontology

        def scalars(self):
            return self

        def all(self):
            return []

    class _Connection:
        def execute(self, statement, params):
            sql_calls.append((str(statement), params))
            return _Result(str(statement))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def close(self):
            return None

    class _Context:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        dialect = SimpleNamespace(name="postgresql")

        def connect(self):
            return _Connection()

        def begin(self):
            return _Context()

    class _Builder:
        def build_graph(self, **kwargs):
            calls.append(kwargs)
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    monkeypatch.setattr(Config, "USE_SUPABASE_PERSISTENCE", True)
    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())
    monkeypatch.setattr(ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(graph_tasks, "TaskManager", _TaskManager)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert calls[0]["ontology"] == ontology
    ontology_reads = [
        (statement, params)
        for statement, params in sql_calls
        if "FROM ontologies" in statement
    ]
    assert len(ontology_reads) == 1
    statement, params = ontology_reads[0]
    assert "project_id = :project_id" in statement
    assert "status = :status" in statement
    assert "ORDER BY updated_at DESC, id DESC" in statement
    assert params == {"project_id": 17, "status": "completed"}


def test_canonical_worker_executes_against_integer_ontology_fk_schema(monkeypatch):
    ontology = {"entity_types": [{"name": "CanaryPerson"}], "edge_types": []}
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id VARCHAR(64) NOT NULL UNIQUE,
                    name VARCHAR(255), status VARCHAR(50) NOT NULL,
                    created_at DATETIME, updated_at DATETIME,
                    total_text_length INTEGER NOT NULL,
                    chunk_size INTEGER NOT NULL, chunk_overlap INTEGER NOT NULL,
                    analysis_summary TEXT, simulation_requirement TEXT,
                    graph_id VARCHAR(64), graph_build_task_id VARCHAR(64), error TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE ontologies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    task_id VARCHAR(64), status VARCHAR(50) NOT NULL,
                    result_json JSON, error TEXT,
                    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL, upload_date DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO projects (
                    project_id, name, status, created_at, updated_at,
                    total_text_length, chunk_size, chunk_overlap,
                    graph_build_task_id
                ) VALUES (
                    :project_id, :name, :status, CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP, 6, 42, 7, :task_id
                )
                """
            ),
            {
                "project_id": "project-1",
                "name": "Canonical project",
                "status": ProjectStatus.GRAPH_BUILDING.value,
                "task_id": "task-1",
            },
        )
        project_pk = conn.execute(
            text("SELECT id FROM projects WHERE project_id = 'project-1'")
        ).scalar_one()
        ontology_insert = text(
            """
            INSERT INTO ontologies (
                project_id, task_id, status, result_json, error,
                created_at, updated_at
            ) VALUES (
                :project_id, :task_id, :status, :result_json, NULL,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ).bindparams(bindparam("result_json", type_=JSON))
        conn.execute(
            ontology_insert,
            {
                "project_id": project_pk,
                "task_id": "ontology-task-1",
                "status": "completed",
                "result_json": ontology,
            },
        )

    calls = []

    class _Builder:
        def build_graph(self, **kwargs):
            calls.append(kwargs)
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    monkeypatch.setattr(Config, "USE_SUPABASE_PERSISTENCE", True)
    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: engine)
    monkeypatch.setattr(
        ProjectRepository,
        "graph_build_delivery_fence",
        lambda *_args: nullcontext(),
    )
    monkeypatch.setattr(ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(graph_tasks, "TaskManager", _TaskManager)
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    assert ProjectRepository.get_project("project-1").ontology == ontology

    result = graph_tasks.build_graph_task.run(
        project_id="project-1",
        task_id="task-1",
    )

    assert calls[0]["ontology"] == ontology
    assert result["success"] is True
    with engine.connect() as conn:
        persisted = conn.execute(
            text(
                """
                SELECT status, graph_id, graph_build_task_id
                FROM projects WHERE project_id = 'project-1'
                """
            )
        ).one()
    assert persisted.status == ProjectStatus.GRAPH_COMPLETED.value
    assert persisted.graph_id == result["graph_id"]
    assert persisted.graph_build_task_id == "task-1"


def test_repository_save_project_persists_ontology_with_integer_project_fk(monkeypatch):
    ontology = {"entity_types": [{"name": "CanaryPerson"}], "edge_types": []}
    project = _project(task_id=None)
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = ontology
    calls = []

    class _Result:
        def __init__(self, statement):
            self.statement = statement
            self.rowcount = 1

        def first(self):
            return (1,)

        def scalar_one_or_none(self):
            return 17

    class _Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return _Result(str(statement))

    class _Context:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        def begin(self):
            return _Context()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    ProjectRepository.save_project(
        project,
        _ontology_task_id="ontology-task-1",
    )

    ontology_writes = [
        (statement, params)
        for statement, params in calls
        if "INSERT INTO ontologies" in statement
    ]
    assert len(ontology_writes) == 1
    _, params = ontology_writes[0]
    assert params["project_id"] == 17
    assert params["task_id"] == "ontology-task-1"
    assert params["status"] == "completed"
    assert params["result_json"] == ontology


def test_repository_repeat_save_does_not_duplicate_unchanged_ontology(monkeypatch):
    ontology = {"entity_types": [{"name": "CanaryPerson"}], "edge_types": []}
    project = _project(task_id=None)
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = ontology
    calls = []
    state = {"latest": None}

    class _Result:
        def __init__(self, scalar=None):
            self._scalar = scalar
            self.rowcount = 1

        def first(self):
            return (1,)

        def scalar_one_or_none(self):
            return self._scalar

    class _Connection:
        def execute(self, statement, params):
            sql = str(statement)
            calls.append((sql, params))
            if "SELECT id FROM projects" in sql:
                return _Result(17)
            if "SELECT result_json" in sql:
                return _Result(state["latest"])
            if "INSERT INTO ontologies" in sql:
                state["latest"] = params["result_json"]
            return _Result()

    class _Context:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        def begin(self):
            return _Context()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    ProjectRepository.save_project(
        project,
        _ontology_task_id="ontology-task-1",
    )
    ProjectRepository.save_project(project)

    ontology_writes = [
        statement for statement, _params in calls if "INSERT INTO ontologies" in statement
    ]
    assert len(ontology_writes) == 1


def test_repository_changed_ontology_without_producer_identity_fails_closed(
    monkeypatch,
):
    project = _project(task_id=None)
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "NewType"}], "edge_types": []}
    calls = []

    class _Result:
        rowcount = 1

        def first(self):
            return (1,)

        def scalar_one_or_none(self):
            return {"entity_types": [{"name": "OldType"}], "edge_types": []}

    class _Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return _Result()

    class _Context:
        def __enter__(self):
            return _Connection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Engine:
        def begin(self):
            return _Context()

    monkeypatch.setattr(ProjectRepository, "_get_engine", lambda: _Engine())

    with pytest.raises(ValueError, match="canonical_ontology_producer_missing"):
        ProjectRepository.save_project(project)

    assert not any("INSERT INTO ontologies" in statement for statement, _ in calls)


def test_generate_ontology_threads_server_task_identity_into_canonical_save(
    monkeypatch,
):
    project = _project(task_id=None)
    project.status = ProjectStatus.CREATED
    manager = _TaskManager()
    saves = []

    class _Generator:
        def generate(
            self,
            document_texts,
            simulation_requirement=None,
            additional_context=None,
        ):
            return {
                "entity_types": [],
                "edge_types": [],
                "analysis_summary": "server summary",
            }

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "save_project",
        lambda value, **kwargs: saves.append((value, kwargs)),
    )
    monkeypatch.setattr(graph_tasks, "OntologyGenerator", _Generator)

    graph_tasks.generate_ontology_task.run(
        project_id="project-1",
        text="canonical source",
        task_id="ontology-task-1",
    )

    assert saves[0][1] == {"_ontology_task_id": "ontology-task-1"}


def test_completion_exception_accepts_only_exact_persisted_completion(monkeypatch):
    project = _project(task_id="task-1")
    manager = _TaskManager()
    stable_graph_id = graph_tasks._stable_graph_id("project-1", "task-1")
    failure_calls = []

    class _Builder:
        def build_graph(self, **kwargs):
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    def complete_then_raise(project_id, expected_task_id, graph_id):
        project.status = ProjectStatus.GRAPH_COMPLETED
        project.graph_id = graph_id
        project.graph_build_task_id = expected_task_id
        raise RuntimeError("audit sink unavailable after canonical write")

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "ensure_graph_build_owner", lambda *_args: True)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "complete_graph_build", complete_then_raise)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "fail_graph_build",
        lambda *args, **kwargs: failure_calls.append((args, kwargs)) or True,
        raising=False,
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    result = graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert result["success"] is True
    assert result["graph_id"] == stable_graph_id
    assert manager.completions == [("task-1", result)]
    assert failure_calls == []


def test_retry_publication_failure_cas_fails_the_owned_project(monkeypatch):
    project = _project(task_id="task-1")
    manager = _TaskManager()
    failure_calls = []

    class _Builder:
        def build_graph(self, **kwargs):
            failure = graph_builder.GraphBuildProviderError(
                "graph_create_phase_failed",
                graph_id=kwargs["graph_id"],
                retry_safe=True,
            )
            failure.__cause__ = ConnectionError("transient provider reset")
            raise failure

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "ensure_graph_build_owner", lambda *_args: True)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "fail_graph_build",
        lambda project_id, expected_task_id, error: failure_calls.append(
            (project_id, expected_task_id, error)
        )
        or True,
        raising=False,
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)
    monkeypatch.setattr(graph_tasks.build_graph_task.request, "retries", 0, raising=False)
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "retry",
        lambda **kwargs: (_ for _ in ()).throw(ConnectionError("broker unavailable")),
    )

    with pytest.raises(RuntimeError, match="graph_build_retry_dispatch_failed"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert failure_calls == [
        ("project-1", "task-1", "graph_build_retry_dispatch_failed")
    ]
    assert manager.failures[-1][1] == "graph_build_retry_dispatch_failed"


def test_initial_task_update_failure_happens_after_ownership_and_cas_fails(monkeypatch):
    project = _project(task_id="task-1")
    events = []

    class _UnavailableTaskManager(_TaskManager):
        def update_task(self, task_id, **kwargs):
            events.append("task-update")
            raise ConnectionError("task store unavailable")

    manager = _UnavailableTaskManager()

    def get_project(_project_id):
        events.append("project-load")
        return project

    def ensure_owner(*_args):
        events.append("ownership-claim")
        return True

    def fail_owner(project_id, expected_task_id, error):
        events.append(("project-fail", project_id, expected_task_id, error))
        return True

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", get_project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "ensure_graph_build_owner", ensure_owner)
    monkeypatch.setattr(graph_tasks.ProjectManager, "fail_graph_build", fail_owner, raising=False)

    with pytest.raises(RuntimeError, match="graph_build_failed"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert events[:3] == ["project-load", "ownership-claim", "task-update"]
    assert events[3] == ("project-fail", "project-1", "task-1", "graph_build_failed")


class _TransientGraphReadError(Exception):
    status_code = 503


def _graph_info_retry_service(node_read):
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = SimpleNamespace(
        graph=SimpleNamespace(
            node=SimpleNamespace(get_by_graph_id=node_read),
            edge=SimpleNamespace(get_by_graph_id=lambda *args, **kwargs: []),
        )
    )
    service.create_graph = lambda graph_id, graph_name: graph_id
    service.set_ontology = lambda graph_id, ontology: None
    service.add_text_batches = lambda *args, **kwargs: [
        "00000000-0000-0000-0000-000000000001"
    ]
    service._wait_for_episodes = lambda *args, **kwargs: None
    return service


def test_graph_info_paging_recovers_from_status_aware_transient_reads(monkeypatch):
    reads = []

    def read_nodes(*args, **kwargs):
        reads.append((args, kwargs))
        if len(reads) < 3:
            raise _TransientGraphReadError("provider body")
        return []

    service = _graph_info_retry_service(read_nodes)
    monkeypatch.setattr(graph_builder.TextProcessor, "split_text", lambda *_args: ["source"])
    monkeypatch.setattr(zep_paging.time, "sleep", lambda _seconds: None)

    result = service.build_graph(
        graph_id="atp_graph_info",
        text="source",
        ontology={"entity_types": [], "edge_types": []},
        graph_name="server name",
        chunk_size=42,
        chunk_overlap=7,
    )

    assert result["success"] is True
    assert len(reads) == 3


def test_graph_info_paging_exhaustion_is_terminal_without_whole_build_replay(monkeypatch):
    reads = []
    creates = []

    def read_nodes(*args, **kwargs):
        reads.append((args, kwargs))
        raise _TransientGraphReadError("provider body")

    service = _graph_info_retry_service(read_nodes)
    service.create_graph = lambda graph_id, graph_name: creates.append(graph_id) or graph_id
    monkeypatch.setattr(graph_builder.TextProcessor, "split_text", lambda *_args: ["source"])
    monkeypatch.setattr(zep_paging.time, "sleep", lambda _seconds: None)

    with pytest.raises(
        graph_builder.GraphBuildProviderError,
        match="graph_post_mutation_failed",
    ) as failure:
        service.build_graph(
            graph_id="atp_graph_info",
            text="source",
            ontology={"entity_types": [], "edge_types": []},
            graph_name="server name",
            chunk_size=42,
            chunk_overlap=7,
        )

    assert failure.value.retry_safe is False
    assert len(reads) == 3
    assert creates == ["atp_graph_info"]


@pytest.fixture
def graph_client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def test_route_begin_conflict_fails_only_new_task_and_never_enqueues(
    graph_client, monkeypatch
):
    project = _project(task_id=None)
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    manager = _TaskManager()
    begin_calls = []

    monkeypatch.setattr(graph_api, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)

    def lose_begin_cas(*args, **kwargs):
        begin_calls.append((args, kwargs))
        return False

    monkeypatch.setattr(
        graph_api.ProjectManager,
        "begin_graph_build",
        lose_begin_cas,
    )
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "apply_async",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("a lost begin CAS must never enqueue")
        ),
    )

    response = graph_client.post(
        "/api/graph/build",
        json={"project_id": "project-1", "chunk_size": 42, "chunk_overlap": 7},
    )

    assert response.status_code == 409
    assert response.get_json() == {"success": False, "error": "graph_build_conflict"}
    assert manager.failures == [
        (
            "task-1",
            "graph_build_conflict",
            {"public_error": "graph_build_conflict"},
        )
    ]
    args, kwargs = begin_calls[0]
    assert args == ("project-1", "task-1")
    assert kwargs == {
        "chunk_size": 42,
        "chunk_overlap": 7,
        "expected_status": ProjectStatus.ONTOLOGY_GENERATED,
        "expected_task_id": None,
        "force": False,
    }
    assert project.status is ProjectStatus.ONTOLOGY_GENERATED


def test_active_graph_build_cannot_be_force_superseded(graph_client, monkeypatch):
    project = _project(task_id="active-task")
    original = (project.status, project.graph_build_task_id, project.graph_id)

    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_api,
        "TaskManager",
        lambda: (_ for _ in ()).throw(
            AssertionError("active ownership must be rejected before task creation")
        ),
    )

    response = graph_client.post(
        "/api/graph/build",
        json={"project_id": "project-1", "force": True},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": "graph_build_conflict",
    }
    assert (project.status, project.graph_build_task_id, project.graph_id) == original


def test_completed_graph_cannot_be_replaced_without_versioned_swap(
    graph_client,
    monkeypatch,
):
    project = _project(task_id=None)
    project.status = ProjectStatus.GRAPH_COMPLETED
    project.graph_id = "atp_last_good_graph"

    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_api,
        "TaskManager",
        lambda: (_ for _ in ()).throw(
            AssertionError("unsafe rebuild must be rejected before task creation")
        ),
    )

    response = graph_client.post(
        "/api/graph/build",
        json={"project_id": "project-1", "force": True},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": "graph_rebuild_unavailable",
    }
    assert project.graph_id == "atp_last_good_graph"


@pytest.mark.parametrize(
    ("method", "path", "error"),
    [
        ("post", "/api/graph/project/project-1/reset", "graph_reset_unavailable"),
        ("delete", "/api/graph/project/project-1", "project_deletion_unavailable"),
    ],
)
def test_active_graph_build_cannot_be_reset_or_deleted(
    graph_client,
    monkeypatch,
    method,
    path,
    error,
):
    project = _project(task_id="active-task")
    original = (project.status, project.graph_build_task_id, project.graph_id)
    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "save_project",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("active graph state must not be overwritten")
        ),
    )
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "delete_project",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("active project must not be deleted")
        ),
    )

    response = getattr(graph_client, method)(path)

    assert response.status_code == 409
    assert response.get_json() == {"success": False, "error": error}
    assert (project.status, project.graph_build_task_id, project.graph_id) == original


def test_route_unwinds_project_and_task_when_broker_dispatch_fails(graph_client, monkeypatch, tmp_path):
    project = _project(task_id=None)
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    manager = _TaskManager()
    saves = []

    monkeypatch.setattr(graph_api, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_api.ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(graph_api.ProjectManager, "save_project", lambda value: saves.append((value.status, value.graph_build_task_id, value.error)))
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "apply_async",
        lambda **kwargs: (_ for _ in ()).throw(ConnectionError("broker body must stay private")),
    )

    response = graph_client.post("/api/graph/build", json={"project_id": "project-1"})

    assert response.status_code == 503
    assert response.get_json() == {"success": False, "error": "graph_dispatch_failed"}
    assert project.status is ProjectStatus.ONTOLOGY_GENERATED
    assert project.graph_build_task_id is None
    assert project.error == "graph_dispatch_failed"
    assert manager.failures == [
        ("task-1", "graph_dispatch_failed", {"public_error": "graph_dispatch_failed"})
    ]
    assert all(status is not ProjectStatus.GRAPH_BUILDING for status, _, _ in saves[-1:])


def test_force_rebuild_preserves_prior_completed_graph_without_dispatch(graph_client, monkeypatch, tmp_path):
    project = _project(task_id=None)
    project.status = ProjectStatus.GRAPH_COMPLETED
    project.graph_id = "atp_prior_completed"
    manager = _TaskManager()

    monkeypatch.setattr(graph_api, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_api.ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(graph_api.ProjectManager, "save_project", lambda value: None)
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "apply_async",
        lambda **kwargs: (_ for _ in ()).throw(ConnectionError("broker body must stay private")),
    )

    response = graph_client.post(
        "/api/graph/build", json={"project_id": "project-1", "force": True}
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": "graph_rebuild_unavailable",
    }
    assert project.status is ProjectStatus.GRAPH_COMPLETED
    assert project.graph_id == "atp_prior_completed"
    assert project.graph_build_task_id is None
    assert manager.failures == []


def test_route_unexpected_setup_error_is_sanitized(graph_client, monkeypatch):
    project = _project(task_id=None)
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    manager = _TaskManager()

    monkeypatch.setattr(graph_api, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_api.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "begin_graph_build",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError("source content and broker body must stay private")
        ),
    )

    response = graph_client.post("/api/graph/build", json={"project_id": "project-1"})

    assert response.status_code == 500
    assert response.get_json() == {"success": False, "error": "graph_build_setup_failed"}


def test_graph_build_lock_deadline_fails_closed_when_lock_never_acquires(monkeypatch):
    monkeypatch.setattr(project_module, "_try_lock_graph_build_file", lambda _file: False, raising=False)

    with pytest.raises(RuntimeError, match="graph_build_lock_unavailable"):
        project_module._acquire_graph_build_lock_with_deadline(
            object(), timeout_seconds=0
        )


def _owner_marker(graph_id):
    digest = hashlib.sha256(f"source-graph:{graph_id}".encode()).hexdigest()
    return f"source_graph_owner:{digest}"


def test_create_conflict_retries_transient_verification_read(monkeypatch):
    graph_id = "atp_owned"
    reads = []

    class _Conflict(Exception):
        status_code = 409

    class _Graph:
        episode = SimpleNamespace(get_by_graph_id=lambda **kwargs: [])

        @staticmethod
        def create(**kwargs):
            raise _Conflict("conflict")

        @staticmethod
        def get(**kwargs):
            reads.append(kwargs)
            if len(reads) == 1:
                raise ConnectionError("transient provider body")
            return SimpleNamespace(description=_owner_marker(graph_id))

    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = SimpleNamespace(graph=_Graph())
    monkeypatch.setattr(graph_builder.time, "sleep", lambda _seconds: None)

    assert service.create_graph(graph_id, "server name") == graph_id
    assert len(reads) == 2


def test_create_conflict_accepts_only_an_empty_sdk_episode_response():
    graph_id = "atp_owned_response"

    class _Conflict(Exception):
        status_code = 409

    class _Graph:
        episode = SimpleNamespace(
            get_by_graph_id=lambda **kwargs: SimpleNamespace(episodes=[])
        )

        @staticmethod
        def create(**kwargs):
            raise _Conflict("conflict")

        @staticmethod
        def get(**kwargs):
            return SimpleNamespace(description=_owner_marker(graph_id))

    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = SimpleNamespace(graph=_Graph())

    assert service.create_graph(graph_id, "server name") == graph_id


@pytest.mark.parametrize(
    "episode_response",
    [
        SimpleNamespace(episodes=None),
        SimpleNamespace(episodes=[SimpleNamespace(uuid_="existing")]),
        SimpleNamespace(),
    ],
)
def test_create_conflict_rejects_nonempty_or_malformed_sdk_episode_response(episode_response):
    graph_id = "atp_owned_response"

    class _Conflict(Exception):
        status_code = 409

    class _Graph:
        episode = SimpleNamespace(get_by_graph_id=lambda **kwargs: episode_response)

        @staticmethod
        def create(**kwargs):
            raise _Conflict("conflict")

        @staticmethod
        def get(**kwargs):
            return SimpleNamespace(description=_owner_marker(graph_id))

    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = SimpleNamespace(graph=_Graph())

    with pytest.raises(RuntimeError, match="graph_create_conflict_unsafe"):
        service.create_graph(graph_id, "server name")


def test_task_completion_failure_best_effort_fails_task_but_keeps_project_completed(monkeypatch):
    project = _project()
    manager = _TaskManager(complete_error=ConnectionError("task store body"))
    saves = []

    class _Builder:
        def build_graph(self, **kwargs):
            return {"success": True, "graph_id": kwargs["graph_id"], "graph_info": {}}

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_project", lambda _id: project)
    monkeypatch.setattr(graph_tasks.ProjectManager, "get_extracted_text", lambda _id: "source")
    monkeypatch.setattr(graph_tasks.ProjectManager, "save_project", lambda value: saves.append(value.status))
    def complete_graph_build(project_id, expected_task_id, graph_id):
        project.status = ProjectStatus.GRAPH_COMPLETED
        project.graph_id = graph_id
        project.error = None
        return True

    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "complete_graph_build",
        complete_graph_build,
        raising=False,
    )
    monkeypatch.setattr(graph_tasks, "GraphBuilderService", _Builder)

    with pytest.raises(RuntimeError, match="graph_task_completion_persistence_failed"):
        graph_tasks.build_graph_task.run(project_id="project-1", task_id="task-1")

    assert project.status is ProjectStatus.GRAPH_COMPLETED
    assert manager.failures == [
        (
            "task-1",
            "graph_task_completion_persistence_failed",
            {"public_error": "graph_task_completion_persistence_failed"},
        )
    ]

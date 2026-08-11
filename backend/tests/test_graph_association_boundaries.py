"""Fail-closed project-to-graph association seams for provider-backed routes.

These checks deliberately stop at server-owned project association.  They do
not claim tenant authorization, which remains a separate release blocker.
"""

import logging
from types import SimpleNamespace

import pytest

from app import create_app
from app.api import report as report_api
from app.api.routes import entity_routes, prep_routes
from app.config import Config
from app.models.project import ProjectManager, ProjectStatus
from app.services import project_repository
from app.tasks import graph_tasks


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _project(graph_id="graph-owned"):
    return SimpleNamespace(
        project_id="project-owned",
        graph_id=graph_id,
        status=ProjectStatus.GRAPH_COMPLETED,
        simulation_requirement="Should weekend service change?",
    )


def test_create_simulation_rejects_client_graph_outside_project_association(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda project_id: _project() if project_id == "project-owned" else None,
    )
    created = []
    monkeypatch.setattr(
        prep_routes,
        "SimulationManager",
        lambda: SimpleNamespace(
            create_simulation=lambda **kwargs: created.append(kwargs)
        ),
    )

    response = client.post(
        "/api/simulation/create",
        json={"project_id": "project-owned", "graph_id": "graph-attacker"},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "graph_not_available_for_project",
    }
    assert created == []


def test_prepare_rejects_legacy_simulation_graph_before_provider_read(
    client,
    monkeypatch,
):
    monkeypatch.setattr(Config, "DECISION_LENS_V1_ENABLED", True)
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda project_id: _project() if project_id == "project-owned" else None,
    )
    state = SimpleNamespace(
        simulation_id="simulation-legacy",
        project_id="project-owned",
        graph_id="graph-attacker",
        status="created",
        entities_count=0,
        entity_types=[],
    )
    monkeypatch.setattr(
        prep_routes,
        "SimulationManager",
        lambda: SimpleNamespace(get_simulation=lambda _simulation_id: state),
    )
    monkeypatch.setattr(
        prep_routes,
        "ZepEntityReader",
        lambda: pytest.fail("provider must not be reached for an unassociated graph"),
    )

    response = client.post(
        "/api/simulation/prepare",
        json={"simulation_id": "simulation-legacy"},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "graph_not_available_for_project",
    }


def test_prepare_storage_value_error_is_sanitized(client, monkeypatch):
    monkeypatch.setattr(Config, "DECISION_LENS_V1_ENABLED", True)
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda project_id: _project() if project_id == "project-owned" else None,
    )
    state = SimpleNamespace(
        simulation_id="simulation-owned",
        project_id="project-owned",
        graph_id="graph-owned",
        status="created",
        entities_count=0,
        entity_types=[],
    )
    monkeypatch.setattr(
        prep_routes,
        "SimulationManager",
        lambda: SimpleNamespace(get_simulation=lambda _simulation_id: state),
    )
    monkeypatch.setattr(
        ProjectManager,
        "get_extracted_text",
        lambda _project_id: (_ for _ in ()).throw(
            ValueError("storage-secret-detail")
        ),
    )
    monkeypatch.setattr(
        prep_routes,
        "ZepEntityReader",
        lambda: pytest.fail("provider must not be reached after storage failure"),
    )

    response = client.post(
        "/api/simulation/prepare",
        json={"simulation_id": "simulation-owned"},
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "simulation_prepare_unavailable",
    }
    assert "storage-secret-detail" not in response.get_data(as_text=True)


def test_generate_profiles_requires_exact_project_graph_association(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda project_id: _project() if project_id == "project-owned" else None,
    )
    monkeypatch.setattr(
        prep_routes,
        "ZepEntityReader",
        lambda: pytest.fail("provider must not be reached for an unassociated graph"),
    )

    response = client.post(
        "/api/simulation/generate-profiles",
        json={"project_id": "project-owned", "graph_id": "graph-attacker"},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "graph_not_available_for_project",
    }


@pytest.mark.parametrize(
    "path",
    [
        "/api/simulation/entities/graph-attacker",
        "/api/simulation/entities/graph-attacker/entity-1",
        "/api/simulation/entities/graph-attacker/by-type/Person",
    ],
)
def test_entity_reads_reject_unassociated_graph_before_provider_access(
    client,
    monkeypatch,
    path,
):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda project_id: _project() if project_id == "project-owned" else None,
    )
    monkeypatch.setattr(
        entity_routes,
        "ZepEntityReader",
        lambda: pytest.fail("provider must not be reached for an unassociated graph"),
    )

    response = client.get(f"{path}?project_id=project-owned")

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "graph_not_available_for_project",
    }


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (
            "/api/report/tools/search",
            {
                "project_id": "project-owned",
                "graph_id": "graph-attacker",
                "query": "weekend service",
            },
        ),
        (
            "/api/report/tools/statistics",
            {"project_id": "project-owned", "graph_id": "graph-attacker"},
        ),
    ],
)
def test_report_graph_tools_reject_unassociated_graph_before_provider_access(
    client,
    monkeypatch,
    path,
    body,
):
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda project_id: _project() if project_id == "project-owned" else None,
    )
    monkeypatch.setattr(
        report_api,
        "ZepToolsService",
        lambda: pytest.fail("provider must not be reached for an unassociated graph"),
    )

    response = client.post(path, json=body)

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "graph_not_available_for_project",
    }


def test_entity_provider_failure_is_sanitized(client, monkeypatch):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: _project())

    class FailingReader:
        def filter_defined_entities(self, **_kwargs):
            raise RuntimeError("provider-secret-detail")

    monkeypatch.setattr(entity_routes, "ZepEntityReader", FailingReader)

    response = client.get(
        "/api/simulation/entities/graph-owned?project_id=project-owned"
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "graph_entity_read_unavailable",
    }
    assert "provider-secret-detail" not in response.get_data(as_text=True)
    assert "traceback" not in response.get_data(as_text=True).lower()


def test_report_graph_tool_provider_failure_is_sanitized(client, monkeypatch):
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: _project())

    class FailingTools:
        def search_graph(self, **_kwargs):
            raise RuntimeError("provider-secret-detail")

    monkeypatch.setattr(report_api, "ZepToolsService", FailingTools)

    response = client.post(
        "/api/report/tools/search",
        json={
            "project_id": "project-owned",
            "graph_id": "graph-owned",
            "query": "weekend service",
        },
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "graph_search_unavailable",
    }
    assert "provider-secret-detail" not in response.get_data(as_text=True)
    assert "traceback" not in response.get_data(as_text=True).lower()


def test_project_lookup_failure_is_sanitized_before_provider_access(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        ProjectManager,
        "get_project",
        lambda _project_id: (_ for _ in ()).throw(
            RuntimeError("postgres://admin:secret@private-host/project")
        ),
    )
    monkeypatch.setattr(
        report_api,
        "ZepToolsService",
        lambda: pytest.fail("provider must not be reached when storage is unavailable"),
    )

    response = client.post(
        "/api/report/tools/statistics",
        json={"project_id": "project-owned", "graph_id": "graph-owned"},
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "project_lookup_unavailable",
    }
    body = response.get_data(as_text=True)
    assert "postgres" not in body
    assert "private-host" not in body


class _OntologyTaskManager:
    def __init__(self):
        self.failures = []

    def update_task(self, *_args, **_kwargs):
        return None

    def fail_task(self, task_id, error, **kwargs):
        self.failures.append((task_id, error, kwargs))

    def complete_task(self, *_args, **_kwargs):
        return None


def test_ontology_task_store_initialization_error_is_collapsed(monkeypatch):
    def unavailable_task_manager():
        raise RuntimeError("redis://private-host/task-store-secret")

    monkeypatch.setattr(graph_tasks, "TaskManager", unavailable_task_manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_project",
        lambda _project_id: pytest.fail(
            "canonical project storage must not be reached after task-store failure"
        ),
    )

    with pytest.raises(RuntimeError, match="^ontology_generation_failed$") as exc_info:
        graph_tasks.generate_ontology_task.run(
            project_id="project-owned",
            text="harmless source",
            task_id="ontology-task",
        )

    assert "private-host" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_project_cleanup_does_not_log_raw_storage_exception(
    monkeypatch,
    caplog,
):
    class QueryResult:
        def __init__(self, *, first=None, rows=None):
            self._first = first
            self._rows = rows or []

        def first(self):
            return self._first

        def all(self):
            return self._rows

    class Connection:
        def execute(self, statement, _params):
            sql = str(statement)
            if "SELECT id FROM projects" in sql:
                return QueryResult(first=(7,))
            if "SELECT file_path FROM sources" in sql:
                return QueryResult(rows=[("project-owned/source.txt",)])
            if "DELETE FROM projects" in sql:
                return QueryResult()
            raise AssertionError(f"unexpected query: {sql}")

    class BeginContext:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_args):
            return False

    class Engine:
        def begin(self):
            return BeginContext()

    monkeypatch.setattr(
        project_repository.ProjectRepository,
        "_get_engine",
        classmethod(lambda _cls: Engine()),
    )
    monkeypatch.setattr(
        project_repository.storage,
        "delete",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("storage-provider-secret-detail")
        ),
    )

    with caplog.at_level(logging.WARNING, logger=project_repository.__name__):
        deleted = project_repository.ProjectRepository.delete_project(
            "project-owned"
        )

    assert deleted is True
    assert "storage-provider-secret-detail" not in caplog.text


def test_ontology_provider_error_result_is_not_persisted_or_returned_raw(
    monkeypatch,
):
    manager = _OntologyTaskManager()
    project = _project(graph_id=None)
    project.status = ProjectStatus.CREATED

    class FailingGenerator:
        def generate(self, _text, requirements=None):
            assert requirements is None
            return {"success": False, "error": "provider-secret-detail"}

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "save_project",
        lambda _project, **_kwargs: None,
    )
    monkeypatch.setattr(graph_tasks, "OntologyGenerator", FailingGenerator)

    result = graph_tasks.generate_ontology_task.run(
        project_id="project-owned",
        text="harmless source",
        task_id="ontology-task",
    )

    assert result == {"success": False, "error": "ontology_generation_failed"}
    assert manager.failures == [
        (
            "ontology-task",
            "ontology_generation_failed",
            {"public_error": "ontology_generation_failed"},
        )
    ]
    assert "provider-secret-detail" not in repr(result)


def test_ontology_provider_exception_is_collapsed_to_stable_task_failure(
    monkeypatch,
):
    manager = _OntologyTaskManager()
    project = _project(graph_id=None)
    project.status = ProjectStatus.CREATED

    class FailingGenerator:
        def generate(self, _text, requirements=None):
            raise RuntimeError("provider-secret-detail")

    monkeypatch.setattr(graph_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(
        graph_tasks.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(graph_tasks, "OntologyGenerator", FailingGenerator)

    with pytest.raises(RuntimeError, match="^ontology_generation_failed$"):
        graph_tasks.generate_ontology_task.run(
            project_id="project-owned",
            text="harmless source",
            task_id="ontology-task",
        )

    assert manager.failures == [
        (
            "ontology-task",
            "ontology_generation_failed",
            {"public_error": "ontology_generation_failed"},
        )
    ]


def test_ontology_task_envelope_failure_does_not_downgrade_persisted_success(
    monkeypatch,
):
    class CompletionFailingManager(_OntologyTaskManager):
        def complete_task(self, *_args, **_kwargs):
            raise RuntimeError("redis-secret-detail")

    manager = CompletionFailingManager()
    project = _project(graph_id=None)
    project.status = ProjectStatus.CREATED
    saves = []

    class SuccessfulGenerator:
        def generate(self, _text, requirements=None):
            return {
                "success": True,
                "ontology": {"entity_types": [], "edge_types": []},
                "summary": "bounded summary",
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
        lambda value, **kwargs: saves.append((value.status, kwargs)),
    )
    monkeypatch.setattr(graph_tasks, "OntologyGenerator", SuccessfulGenerator)

    with pytest.raises(RuntimeError, match="^ontology_generation_failed$"):
        graph_tasks.generate_ontology_task.run(
            project_id="project-owned",
            text="harmless source",
            task_id="ontology-task",
        )

    assert project.status == ProjectStatus.ONTOLOGY_GENERATED
    assert saves == [
        (
            ProjectStatus.ONTOLOGY_GENERATED,
            {"_ontology_task_id": "ontology-task"},
        )
    ]

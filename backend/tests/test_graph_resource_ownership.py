"""Authorization boundary for provider-backed graph resources.

Graph identifiers are provider capabilities, not tenant/project authority.  Every
read or destructive request must first resolve a canonical, server-owned project
and prove that the requested graph is the graph currently associated with it.
"""

from types import SimpleNamespace

import pytest

from app import create_app
from app.api import graph as graph_api
from app.config import Config
from app.models.project import ProjectStatus


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _completed_project(graph_id: str = "graph-owned"):
    return SimpleNamespace(
        project_id="proj_owned",
        status=ProjectStatus.GRAPH_COMPLETED,
        graph_id=graph_id,
    )


def test_graph_read_rejects_provider_id_without_project_authority(
    client,
    monkeypatch,
):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda _project_id: pytest.fail("project lookup must not run without an id"),
    )
    monkeypatch.setattr(
        graph_api,
        "GraphBuilderService",
        lambda **_kwargs: pytest.fail("provider must not be reached"),
    )

    response = client.get("/api/graph/data/graph-owned")

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "project_id_required",
    }


def test_graph_read_rejects_graph_not_associated_with_canonical_project(
    client,
    monkeypatch,
):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda project_id: _completed_project() if project_id == "proj_owned" else None,
    )
    monkeypatch.setattr(
        graph_api,
        "GraphBuilderService",
        lambda **_kwargs: pytest.fail("provider must not be reached"),
    )

    response = client.get("/api/graph/data/graph-attacker?project_id=proj_owned")

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "graph_not_available_for_project",
    }


def test_graph_read_uses_only_the_exact_canonical_graph_association(
    client,
    monkeypatch,
):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    provider_reads = []
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda project_id: _completed_project() if project_id == "proj_owned" else None,
    )

    class FakeBuilder:
        def __init__(self, api_key):
            assert api_key == "test-zep-key"

        def get_graph_data(self, graph_id):
            provider_reads.append(graph_id)
            return {"graph_id": graph_id, "nodes": [], "edges": []}

    monkeypatch.setattr(graph_api, "GraphBuilderService", FakeBuilder)

    response = client.get("/api/graph/data/graph-owned?project_id=proj_owned")

    assert response.status_code == 200
    assert provider_reads == ["graph-owned"]
    assert response.get_json()["data"]["graph_id"] == "graph-owned"


def test_graph_read_provider_failure_is_stable_and_sanitized(
    client,
    monkeypatch,
):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda _project_id: _completed_project(),
    )

    class FailingBuilder:
        def __init__(self, api_key):
            assert api_key == "test-zep-key"

        def get_graph_data(self, _graph_id):
            raise RuntimeError("provider-secret-detail")

    monkeypatch.setattr(graph_api, "GraphBuilderService", FailingBuilder)

    response = client.get("/api/graph/data/graph-owned?project_id=proj_owned")

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "graph_read_unavailable",
    }
    assert "provider-secret-detail" not in response.get_data(as_text=True)
    assert "traceback" not in response.get_data(as_text=True).lower()


def test_graph_delete_fails_closed_when_no_owned_delete_state_exists(
    client,
    monkeypatch,
):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    project = _completed_project()
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        graph_api,
        "GraphBuilderService",
        lambda **_kwargs: pytest.fail("provider deletion must not be attempted"),
    )

    response = client.delete("/api/graph/delete/graph-owned?project_id=proj_owned")

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "graph_delete_unavailable",
    }
    assert project.status == ProjectStatus.GRAPH_COMPLETED
    assert project.graph_id == "graph-owned"


def test_graph_delete_rejects_mismatched_graph_before_unavailable_state(
    client,
    monkeypatch,
):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda _project_id: _completed_project(),
    )
    monkeypatch.setattr(
        graph_api,
        "GraphBuilderService",
        lambda **_kwargs: pytest.fail("provider deletion must not be attempted"),
    )

    response = client.delete("/api/graph/delete/graph-attacker?project_id=proj_owned")

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "graph_not_available_for_project",
    }

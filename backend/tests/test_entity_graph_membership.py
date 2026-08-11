"""Security regressions for graph-scoped entity detail reads."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from app import create_app
from app.api.routes import entity_routes
from app.config import Config
from app.models.project import ProjectManager, ProjectStatus
from app.services import zep_entity_reader
from app.services.zep_entity_reader import ZepEntityReader


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _project():
    return SimpleNamespace(
        project_id="project-owned",
        graph_id="graph-owned",
        status=ProjectStatus.GRAPH_COMPLETED,
    )


def _node(node_uuid: str, name: str):
    return SimpleNamespace(
        uuid_=node_uuid,
        name=name,
        labels=["Entity", "Person"],
        summary=f"{name} summary",
        attributes={"private": f"{name} attributes"},
    )


def _edge(edge_uuid: str, fact: str, source_uuid: str, target_uuid: str):
    return SimpleNamespace(
        uuid_=edge_uuid,
        name="RELATES_TO",
        fact=fact,
        source_node_uuid=source_uuid,
        target_node_uuid=target_uuid,
        attributes={},
    )


def _reader(node_api, edge_api=None) -> ZepEntityReader:
    reader = object.__new__(ZepEntityReader)
    reader.client = SimpleNamespace(
        graph=SimpleNamespace(node=node_api, edge=edge_api)
    )
    return reader


def test_entity_detail_cannot_return_a_foreign_graph_node(
    client,
    monkeypatch,
):
    provider_calls = []
    owned_node = _node("entity-owned", "Owned entity")
    foreign_node = _node("entity-foreign", "Foreign secret entity")

    class NodeApi:
        def get_by_graph_id(self, graph_id, **_kwargs):
            provider_calls.append(("list", graph_id))
            assert graph_id == "graph-owned"
            return [owned_node]

        def get(self, *, uuid_):
            provider_calls.append(("global-get", uuid_))
            assert uuid_ == "entity-foreign"
            return foreign_node

        def get_entity_edges(self, *, node_uuid):
            provider_calls.append(("global-edges", node_uuid))
            return []

    reader = _reader(NodeApi())
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: _project())
    monkeypatch.setattr(entity_routes, "ZepEntityReader", lambda: reader)

    response = client.get(
        "/api/simulation/entities/graph-owned/entity-foreign"
        "?project_id=project-owned"
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": "entity_not_found",
    }
    assert provider_calls == [("list", "graph-owned")]
    assert "Foreign secret entity" not in response.get_data(as_text=True)


def test_entity_membership_provider_failure_is_sanitized(
    client,
    monkeypatch,
    caplog,
):
    provider_secret = "provider-secret-detail"

    class NodeApi:
        def get_by_graph_id(self, _graph_id, **_kwargs):
            raise RuntimeError(provider_secret)

        def get(self, *, uuid_):
            return _node(uuid_, "Owned entity")

        def get_entity_edges(self, *, node_uuid):
            assert node_uuid == "entity-owned"
            return []

    reader = _reader(NodeApi())
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: _project())
    monkeypatch.setattr(entity_routes, "ZepEntityReader", lambda: reader)

    with caplog.at_level(logging.WARNING):
        response = client.get(
            "/api/simulation/entities/graph-owned/entity-owned"
            "?project_id=project-owned"
        )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "graph_entity_read_unavailable",
    }
    assert provider_secret not in response.get_data(as_text=True)
    assert provider_secret not in caplog.text


def test_entity_detail_excludes_foreign_graph_edge_facts(
    client,
    monkeypatch,
):
    provider_calls = []
    owned_node = _node("entity-owned", "Owned entity")
    related_node = _node("entity-related", "Related entity")
    owned_edge = _edge(
        "edge-owned",
        "owned-safe-fact",
        "entity-owned",
        "entity-related",
    )
    foreign_edge = _edge(
        "edge-foreign",
        "foreign-secret-fact",
        "entity-owned",
        "entity-foreign",
    )

    class NodeApi:
        def get_by_graph_id(self, graph_id, **_kwargs):
            provider_calls.append(("list-nodes", graph_id))
            return [owned_node, related_node]

        def get_entity_edges(self, *, node_uuid):
            provider_calls.append(("global-edges", node_uuid))
            return [owned_edge, foreign_edge]

    class EdgeApi:
        def get_by_graph_id(self, graph_id, **_kwargs):
            provider_calls.append(("list-edges", graph_id))
            return [owned_edge]

    reader = _reader(NodeApi(), EdgeApi())
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: _project())
    monkeypatch.setattr(entity_routes, "ZepEntityReader", lambda: reader)

    response = client.get(
        "/api/simulation/entities/graph-owned/entity-owned"
        "?project_id=project-owned"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert [edge["fact"] for edge in payload["data"]["related_edges"]] == [
        "owned-safe-fact"
    ]
    assert provider_calls == [
        ("list-nodes", "graph-owned"),
        ("list-edges", "graph-owned"),
    ]
    assert "foreign-secret-fact" not in response.get_data(as_text=True)
    assert "entity-foreign" not in response.get_data(as_text=True)


def test_entity_edge_inventory_failure_is_sanitized_and_fails_closed(
    client,
    monkeypatch,
    caplog,
):
    provider_secret = "edge-provider-secret-detail"
    owned_node = _node("entity-owned", "Owned entity")

    class NodeApi:
        def get_by_graph_id(self, _graph_id, **_kwargs):
            return [owned_node]

        def get_entity_edges(self, *, node_uuid):
            assert node_uuid == "entity-owned"
            raise RuntimeError(provider_secret)

    class EdgeApi:
        def get_by_graph_id(self, _graph_id, **_kwargs):
            raise RuntimeError(provider_secret)

    reader = _reader(NodeApi(), EdgeApi())
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: _project())
    monkeypatch.setattr(entity_routes, "ZepEntityReader", lambda: reader)
    monkeypatch.setattr(zep_entity_reader.time, "sleep", lambda _seconds: None)

    with caplog.at_level(logging.WARNING):
        response = client.get(
            "/api/simulation/entities/graph-owned/entity-owned"
            "?project_id=project-owned"
        )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "graph_entity_read_unavailable",
    }
    assert provider_secret not in response.get_data(as_text=True)
    assert provider_secret not in caplog.text


def test_node_edge_helper_propagates_failure_without_raw_logging(
    monkeypatch,
    caplog,
):
    provider_secret = "global-edge-provider-secret-detail"

    class NodeApi:
        def get_entity_edges(self, *, node_uuid):
            assert node_uuid == "entity-owned"
            raise RuntimeError(provider_secret)

    reader = _reader(NodeApi())
    monkeypatch.setattr(zep_entity_reader.time, "sleep", lambda _seconds: None)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(
            RuntimeError,
            match="^graph_entity_edge_read_unavailable$",
        ) as exc_info:
            reader.get_node_edges("entity-owned")

    assert exc_info.value.__cause__ is None
    assert provider_secret not in str(exc_info.value)
    assert provider_secret not in caplog.text

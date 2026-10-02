"""Typed request boundary and control-flow preservation for ``app/api/graph.py``.

Exec-plan T26, slice 4. ``graph.py`` is the highest-risk route module in the
repository: it owns the source-upload seam (``validate_file_upload`` ->
``ProjectManager.save_file_to_project`` -> ``safe_join``) and the graph-mutation
seam (``GraphBuilderService``). Three properties are pinned here, and the second
and third matter more than the first.

1. **Reachability.** AGENTS.md rule 2 records that a handler in a route module
   can be an unreachable, hand-synced copy that only tests call directly, which
   would make a typing pass on it prove nothing. These tests resolve the real
   ``url_map`` against the module's AST, so an unregistered handler or a
   doubly-registered URL fails here rather than passing silently.

2. **The boundary narrows nothing.** ``POST /api/graph/build`` is the only route
   in the module that reads a JSON body, so ``BuildGraphRequest`` is the only
   model. It rejects wrong JSON types without coercing them, keeps the module's
   own ``{"success": false, "error": ...}`` envelope instead of switching to
   RFC-7807 Problem Details, and leaves every condition the handler already
   reported to the handler.

3. **Containment is not replaced by shape.** The traversal and ownership tests
   assert that a hostile ``project_id`` still reaches ``ProjectManager``, and
   therefore still reaches ``safe_join``, rather than being short-circuited at
   the schema. A shape check cannot tell whether a path stays inside its root;
   if one ever starts doing that job, these tests fail.
"""

import ast
import inspect

import pytest

from app import create_app
from app.api import graph as graph_api
from app.api import templates as templates_api
from app.config import Config
from app.models.project import ProjectStatus
from app.services.claim_boundary import (
    graph_record_disclosure,
    synthetic_output_disclosure,
)
from app.tasks import graph_tasks


ERROR = "graph_build_request_invalid"

ROUTE_HANDLERS = [
    "get_project",
    "list_projects",
    "delete_project",
    "reset_project",
    "generate_ontology",
    "build_graph",
    "get_task",
    "list_tasks",
    "get_graph_data",
    "delete_graph",
]

# The blueprint serves eleven URLs but graph.py defines ten handlers: the extra
# one is owned by another module. Stated here so the count difference is a
# recorded decision rather than a discrepancy for the next reader to find.
BLUEPRINT_URL_COUNT = 11
FOREIGN_BLUEPRINT_ENDPOINTS = {"list_templates"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _ast_route_handlers():
    """Top-level functions in graph.py carrying a blueprint ``route`` decorator."""
    tree = ast.parse(inspect.getsource(graph_api))
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "route"
            for decorator in node.decorator_list
        )
    ]


def _blueprint_rule_pairs(app):
    return [
        (rule.rule, method)
        for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith("graph.")
        for method in rule.methods
        if method not in {"HEAD", "OPTIONS"}
    ]


def _owned_endpoint_names(app):
    return {
        name.split(".", 1)[1]
        for name, view in app.view_functions.items()
        if name.startswith("graph.")
        and view.__module__ == graph_api.__name__
    }


# ---------------------------------------------------------------------------
# 1. Reachability
# ---------------------------------------------------------------------------


def test_every_route_handler_in_the_module_is_a_registered_endpoint():
    handlers = _ast_route_handlers()

    assert handlers == ROUTE_HANDLERS, (
        "the set of route-decorated handlers in graph.py changed; a typing pass "
        "is only complete once the new handler has been considered too"
    )
    app = create_app()
    for name in handlers:
        assert f"graph.{name}" in app.view_functions, (
            f"graph.py defines {name} but no endpoint graph.{name} is registered; "
            "it would be an unreachable copy that only direct calls could reach"
        )


def test_graph_urls_are_not_registered_twice():
    app = create_app()
    pairs = _blueprint_rule_pairs(app)

    duplicates = sorted({pair for pair in pairs if pairs.count(pair) > 1})
    assert not duplicates, f"the same graph URL is registered twice: {duplicates}"
    assert len(pairs) == BLUEPRINT_URL_COUNT


def test_the_eleventh_graph_url_is_owned_by_another_module():
    """Accounts for the handler-count/URL-count difference of one.

    ``/api/graph/templates`` is served by ``app/api/templates.py``. If that
    handler were ever duplicated into graph.py, the two would fight over one
    endpoint and one of them would be dead.
    """
    app = create_app()

    foreign = {
        name.split(".", 1)[1]
        for name, view in app.view_functions.items()
        if name.startswith("graph.") and view.__module__ != graph_api.__name__
    }

    assert foreign == FOREIGN_BLUEPRINT_ENDPOINTS
    assert foreign <= set(vars(templates_api))
    assert len(_owned_endpoint_names(app)) == len(ROUTE_HANDLERS)


# ---------------------------------------------------------------------------
# 2. The typed boundary on POST /api/graph/build
# ---------------------------------------------------------------------------


MALFORMED_BODIES = [
    {"project_id": {"nested": "object"}},
    {"project_id": ["a", "list"]},
    {"project_id": 7},
    {"project_id": "project-1", "force": "yes"},
    {"project_id": "project-1", "force": 1},
    {"project_id": "project-1", "chunk_size": "500"},
    {"project_id": "project-1", "chunk_overlap": 1.5},
]


@pytest.mark.parametrize(
    "body", MALFORMED_BODIES, ids=[str(sorted(body)) for body in MALFORMED_BODIES]
)
def test_graph_build_rejects_wrong_json_type_without_coercing(client, body):
    """Pydantic would coerce every one of these; the boundary must not.

    ``force: "yes"`` becoming True invents a rebuild intent the client never
    stated as a boolean, and ``chunk_size: "500"`` becoming 500 feeds a string
    into the worker's splitter bound.
    """
    response = client.post("/api/graph/build", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"success": False, "error": ERROR}


@pytest.mark.parametrize("body", [["not", "an", "object"], "a bare string", 7])
def test_graph_build_rejects_a_non_object_body_with_the_app_envelope(client, body):
    """A non-object body is a client error and must answer like one.

    Before the typed boundary the handler called ``.get`` on whatever
    ``request.get_json()`` returned, and the resulting ``AttributeError`` was
    swallowed by its own ``except Exception``, answering 500. The status moves to
    400; the envelope does not move to RFC-7807 Problem Details.
    """
    response = client.post("/api/graph/build", json=body)

    assert response.status_code == 400
    payload = response.get_json()
    assert payload == {"success": False, "error": ERROR}
    assert "detail" not in payload and "instance" not in payload


def test_graph_build_missing_project_id_keeps_the_handler_error(client):
    """The schema must not take over a condition the handler already reports.

    Making ``project_id`` required, or adding ``min_length`` to it, would
    replace ``"Please provide project_id"`` with ``graph_build_request_invalid``
    and break every client that branches on it.
    """
    response = client.post("/api/graph/build", json={})

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "Please provide project_id",
    }


class _RecordingTaskManager:
    def __init__(self, task_id="route-task-1"):
        self._task_id = task_id
        self.failures = []

    def create_task(self, *_args, **_kwargs):
        return self._task_id

    def fail_task(self, task_id, error, **kwargs):
        self.failures.append((task_id, error, kwargs))


def _ontology_project():
    class _Project:
        project_id = "project-1"
        status = ProjectStatus.ONTOLOGY_GENERATED
        graph_id = None
        graph_build_task_id = None
        error = None
        chunk_size = 42
        chunk_overlap = 7

    return _Project()


@pytest.fixture
def build_dispatch(client, monkeypatch):
    """Wire /build down to the Celery dispatch and record what reaches it."""
    dispatches = []
    monkeypatch.setattr(
        graph_api.ProjectManager, "get_project", lambda _id: _ontology_project()
    )
    monkeypatch.setattr(
        graph_api.ProjectManager, "begin_graph_build", lambda *_a, **_kw: True
    )
    monkeypatch.setattr(graph_api.ProjectManager, "save_project", lambda *_a, **_kw: None)
    monkeypatch.setattr(graph_api, "TaskManager", _RecordingTaskManager)
    monkeypatch.setattr(
        graph_tasks.build_graph_task,
        "apply_async",
        lambda **kwargs: dispatches.append(kwargs),
    )
    return dispatches


def test_graph_build_accepts_a_well_formed_body(client, build_dispatch):
    response = client.post(
        "/api/graph/build",
        json={"project_id": "project-1", "chunk_size": 42, "chunk_overlap": 7},
    )

    assert response.status_code == 202
    assert build_dispatch == [
        {"kwargs": {"project_id": "project-1"}, "task_id": "route-task-1"}
    ]


def test_graph_build_ignores_unknown_keys_at_the_handler_not_the_schema(
    client,
    build_dispatch,
):
    """``extra="ignore"`` is what keeps the AGENTS.md rule 5 guarantee testable.

    The canaries must survive the seam so the handler can be observed discarding
    them. Refusing them at the schema would make the provenance guarantee pass
    without ever being exercised.
    """
    response = client.post(
        "/api/graph/build",
        json={
            "project_id": "project-1",
            "graph_name": "PRIVATE_CLIENT_LABEL",
            "simulation_id": "PRIVATE_SIMULATION_ID",
        },
    )

    assert response.status_code == 202
    assert build_dispatch == [
        {"kwargs": {"project_id": "project-1"}, "task_id": "route-task-1"}
    ]
    body = response.get_data(as_text=True)
    assert "PRIVATE_CLIENT_LABEL" not in body
    assert "PRIVATE_SIMULATION_ID" not in body


def test_graph_build_traversal_project_id_still_reaches_the_safe_path_layer(
    client,
    monkeypatch,
):
    """Shape validation must not pre-empt ``safe_join``.

    ``project_id`` is the path segment that reaches
    ``ProjectManager._get_project_dir`` -> ``safe_join``
    (``app/models/project.py:218``). If the schema ever started rejecting
    traversal-looking values, containment would be enforced by a string rule
    instead of by the primitive that actually resolves the path, and that
    primitive would silently stop being exercised.
    """
    looked_up = []
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda project_id: looked_up.append(project_id),
    )

    response = client.post("/api/graph/build", json={"project_id": "../../etc"})

    assert looked_up == ["../../etc"], (
        "the typed boundary intercepted a value that must reach the path "
        "chokepoint unchanged"
    )
    assert response.status_code == 404


def test_graph_build_validation_failure_is_still_rate_limited(client):
    """``@enforce_schema`` must sit inside ``@limiter.limit``.

    Otherwise a malformed body is the cheapest way to probe the endpoint, for
    free. A distinct trusted-IP key is used so the shared in-memory limiter
    counter is left as other tests expect to find it.
    """
    client.application.config.update(TRUST_X_REAL_IP=True)
    headers = {"X-Real-IP": "203.0.113.77"}

    statuses = [
        client.post(
            "/api/graph/build",
            json={"project_id": {"not": "a string"}},
            headers=headers,
        ).status_code
        for _ in range(23)
    ]

    assert 429 in statuses, (
        "malformed bodies were never charged against the route limit; "
        "@enforce_schema is applied outside @limiter.limit"
    )


# ---------------------------------------------------------------------------
# 3. Control flow the typing pass must not have disturbed
# ---------------------------------------------------------------------------


def test_graph_data_resolves_ownership_before_the_provider_dependency_check(
    client,
    monkeypatch,
):
    """``_resolve_owned_graph`` runs before ``Config.ZEP_API_KEY`` is read.

    With the provider unconfigured, an unassociated graph still answers
    ``project_id_required`` rather than the dependency code, which is what shows
    the authorization seam does not sit behind a capability check.
    """
    monkeypatch.setattr(Config, "ZEP_API_KEY", "")
    monkeypatch.setattr(
        graph_api,
        "GraphBuilderService",
        lambda **_kwargs: pytest.fail("provider must not be reached"),
    )

    response = client.get("/api/graph/data/graph-attacker")

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "project_id_required",
    }


def test_graph_delete_resolves_ownership_before_answering_unavailable(
    client,
    monkeypatch,
):
    """The fail-closed delete is still behind the ownership check.

    ``delete_graph`` answers ``graph_delete_unavailable`` unconditionally, but
    only once a server-owned project has vouched for the graph. A 400 here
    proves the vouching still gates the response.
    """
    monkeypatch.setattr(Config, "ZEP_API_KEY", "")
    monkeypatch.setattr(
        graph_api,
        "GraphBuilderService",
        lambda **_kwargs: pytest.fail("provider deletion must not be attempted"),
    )

    response = client.delete("/api/graph/delete/graph-attacker")

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "project_id_required",
    }


def test_graph_data_disclosure_is_still_attached_to_every_record(client, monkeypatch):
    """The truth disclosure on the graph read is not a typing concern.

    Pinned here because editing this module is exactly the kind of change that
    quietly rewrites a response assembly, and the disclosure is load-bearing
    under the product truth contract.
    """
    project = type(
        "Project",
        (),
        {"status": ProjectStatus.GRAPH_COMPLETED, "graph_id": "graph-owned"},
    )()
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda project_id: project if project_id == "proj_owned" else None,
    )

    class FakeBuilder:
        def __init__(self, api_key):
            assert api_key == "test-zep-key"

        def get_graph_data(self, graph_id):
            return {"graph_id": graph_id, "nodes": [], "edges": [{"fact": "F"}]}

    monkeypatch.setattr(graph_api, "GraphBuilderService", FakeBuilder)

    response = client.get("/api/graph/data/graph-owned?project_id=proj_owned")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["disclosure"] == synthetic_output_disclosure()
    edge = payload["data"]["edges"][0]
    for key, value in graph_record_disclosure("F").items():
        assert edge[key] == value


def test_ontology_generate_keeps_its_input_policy_codes(client):
    """The upload route must not have been given a JSON-body schema.

    It is ``multipart/form-data``, so ``enforce_schema`` -- which reads only the
    JSON body -- would validate nothing while appearing to guard the highest-risk
    route in the module. Its fields are already bounded by ``input_policy`` and
    its bytes by ``validate_file_upload``; both stay exactly where they are.
    """
    response = client.post("/api/graph/ontology/generate", data={})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"] == "missing_required_field"

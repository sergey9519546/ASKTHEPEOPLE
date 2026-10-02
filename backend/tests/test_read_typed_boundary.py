"""Typed request boundary for the simulation read routes (exec-plan T26).

The finding this module pins is a **negative** one, and it is the finding, not an
omission: `app/api/routes/read_routes.py` registers 19 rules and every one of them
is ``GET``. No handler in it reads a JSON request body -- verified by AST scan in
``test_no_handler_reads_a_json_body`` below, not by reading and remembering. A
Pydantic body model would therefore have nothing to validate, because
``POST``/``PUT``/``PATCH``/``DELETE`` to any of the 19 paths answer ``405``
before a handler runs.

Consequences that are asserted rather than assumed:

* ``app/api/schemas_read.py`` contains no Pydantic models. That is the correct
  end state for an all-``GET`` module, and inventing a model for a route that
  cannot receive a body would be a boundary that only appears to exist.
* The shape this module *does* enforce is the pre-existing scalar-query
  validation inside the handlers, whose status codes and error codes are pinned
  exactly. A refactor that routes one of those through ``validate_schema`` would
  answer 422 RFC-7807 Problem Details instead of 422 ``{"success": false,
  "error": "limit_out_of_range"}`` -- or 400 for ``/compare``. That is a breaking
  API change, and these tests exist to make it loud.
* ``enforce_schema``/``validate_schema`` appearing in ``read_routes.py`` is
  asserted **absent**. If someone bolts a body decorator onto a GET route, the
  decorator reads ``request.get_json(silent=True) or {}`` and can only ever
  validate an empty dict: it would add a code path that never fires.

Both pre-existing defects in this file have since been fixed. A malformed
scalar used to become a 500 on ``/opinions`` and its ``/generated-interactions``
alias, leaking the Python exception text into the response body; ``read_routes``
now guards ``int()`` the way ``/posts`` and ``/comments`` already did. It also
used to be silently defaulted on ``/history``, ``/actions`` and ``/timeline``,
because ``request.args.get(..., type=int)`` swallows the parse error -- the
query-string counterpart of the coercion ``strict=True`` blocks on a body. Both
are now live assertions below rather than ``xfail`` markers.
"""

import ast
from pathlib import Path

import pytest

from app import create_app
from app.api.schemas_read import (
    BODY_METHODS,
    QUERY_SHAPE_ERRORS,
    RAISES_ON_BAD_SCALAR,
    READ_ROUTE_MODULE,
    READ_ROUTE_QUERY_PARAMS,
    SILENT_DEFAULT_ON_BAD_SCALAR,
)

REPO_BACKEND = Path(__file__).resolve().parents[1]
READ_ROUTES_SOURCE = REPO_BACKEND / "app" / "api" / "routes" / "read_routes.py"


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _read_route_rules():
    app = create_app()
    rules = [
        rule
        for rule in app.url_map.iter_rules()
        if app.view_functions[rule.endpoint].__module__ == READ_ROUTE_MODULE
    ]
    return sorted(rules, key=lambda r: r.rule)


def _concrete(rule: str) -> str:
    return rule.replace("<simulation_id>", "sim_probe_typed")


def test_read_route_rule_count_is_stable(client):
    """Pins the measured inventory so an unregistered route cannot pass quietly.

    ``routes/__init__.py`` has a standing rule that every module in the package
    is imported by the package, because a route file written but never imported
    answers 404 while still looking complete on disk. This is the reachability
    half of that guard for this module.
    """
    assert len(_read_route_rules()) == 19


def test_every_read_route_is_get_only(client):
    """No rule in this module accepts a body-bearing method."""
    offenders = {
        r.rule: sorted(r.methods - {"HEAD", "OPTIONS"})
        for r in _read_route_rules()
        if r.methods - {"HEAD", "OPTIONS"} != {"GET"}
    }
    assert not offenders, (
        f"read_routes now exposes a non-GET method: {offenders}. A body-bearing "
        "route needs a schema in app/api/schemas_read.py before it ships."
    )


@pytest.mark.parametrize("method", BODY_METHODS)
def test_body_methods_are_rejected_before_any_handler_runs(client, method):
    """``405`` on every rule: the body path is unreachable, not merely unused.

    This is the empirical half of the finding. If any of these stopped returning
    405, the route would be able to carry a body and the no-models conclusion in
    ``app/api/schemas_read.py`` would be stale.
    """
    for rule in _read_route_rules():
        response = client.open(_concrete(rule.rule), method=method, json={})
        assert response.status_code == 405, (
            f"{rule.rule} accepted {method}; read_routes has a body-bearing route"
        )


def test_no_handler_reads_a_json_body():
    """Static proof that no ``GET`` handler in the module parses a body.

    A grep for ``get_json`` would be enough today, but the assertion is on the
    parsed AST so it also catches ``request.json``, and it fails with a message
    naming the file rather than with a bare ``False``.
    """
    tree = ast.parse(READ_ROUTES_SOURCE.read_text(encoding="utf-8"))
    offenders = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in {"get_json", "json"}
        and isinstance(node.value, ast.Name)
        and node.value.id == "request"
    ]
    assert not offenders, (
        f"{READ_ROUTES_SOURCE.name} reads a request body at line(s) {offenders}. "
        "A GET route with a body needs a schema in app/api/schemas_read.py; the "
        "no-models conclusion there is now stale."
    )


def test_no_body_schema_decorator_was_applied():
    """``enforce_schema``/``validate_schema`` must stay absent from this module.

    Both parse only ``request.get_json(silent=True) or {}``. On a GET route that
    is always ``{}``, so the decorator would validate nothing while appearing to
    add a typed boundary. Absent is the honest state.
    """
    source = READ_ROUTES_SOURCE.read_text(encoding="utf-8")
    for name in ("enforce_schema", "validate_schema"):
        assert name not in source, (
            f"{READ_ROUTES_SOURCE.name} references {name}. It parses only a JSON "
            "body, which no GET route here receives, so it cannot enforce "
            "anything. Use input_policy or inline checks instead."
        )


def test_recorded_query_params_cover_every_handler():
    """``READ_ROUTE_QUERY_PARAMS`` must name every registered read handler.

    A handler added without updating the record would let the next change update
    the record without knowing the route existed.
    """
    registered = {r.endpoint.rsplit(".", 1)[-1] for r in _read_route_rules()}
    assert registered == set(READ_ROUTE_QUERY_PARAMS), (
        "app/api/schemas_read.py is out of date with read_routes.py: "
        f"only in app={sorted(set(READ_ROUTE_QUERY_PARAMS) - registered)} "
        f"only in routes={sorted(registered - set(READ_ROUTE_QUERY_PARAMS))}"
    )


def test_schemas_read_declares_no_pydantic_models():
    """The no-models conclusion is asserted, not left as prose.

    A model here would have to be applied by a decorator, and the two tests above
    forbid both halves of that. This catches the half that could still slip
    through: a declared-but-unapplied model, which reads as a boundary that
    exists.
    """
    source = (REPO_BACKEND / "app" / "api" / "schemas_read.py").read_text(
        encoding="utf-8"
    )
    assert "BaseModel" not in source, (
        "app/api/schemas_read.py declares a Pydantic model, but no read route "
        "receives a body to apply it to."
    )


def test_query_shape_errors_keep_the_app_envelope(client):
    """The pre-existing scalar validation keeps its status and its error code.

    Pinned explicitly because ``validate_schema`` answers 422 with RFC-7807
    Problem Details. Every one of these is a shape rejection on untrusted input,
    so a naive typing pass would be the natural place to reach for it -- and it
    would change the wire format for clients that branch on ``error``.
    """
    cases = [
        ("/api/simulation/sim_x/posts?platform=bogus", 422, "invalid_platform"),
        ("/api/simulation/sim_x/posts?limit=abc", 422, "invalid_limit_or_offset"),
        ("/api/simulation/sim_x/posts?limit=99999", 422, "limit_out_of_range"),
        ("/api/simulation/sim_x/comments?limit=abc", 422, "invalid_limit_or_offset"),
        ("/api/simulation/sim_x/comments?offset=-1", 422, "limit_out_of_range"),
    ]
    for path, status, code in cases:
        response = client.get(path)
        assert response.status_code == status, f"{path} -> {response.status_code}"
        body = response.get_json()
        assert body["success"] is False
        assert body["error"] == code
        assert "detail" not in body and "instance" not in body, (
            f"{path} answered Problem Details; the app envelope moved"
        )


def test_recorded_query_shape_errors_are_reachable(client):
    """Each code in ``QUERY_SHAPE_ERRORS`` still comes from a live request.

    Without this the table could drift into documenting codes no route returns.
    """
    live = {
        "get_simulation_posts": {
            (422, "invalid_platform"),
            (422, "invalid_limit_or_offset"),
            (422, "limit_out_of_range"),
        },
        "get_simulation_comments": {
            (422, "invalid_limit_or_offset"),
            (422, "limit_out_of_range"),
        },
        "compare_simulations_route": {(400, None)},
    }
    assert set(live) == set(QUERY_SHAPE_ERRORS)
    for handler, entries in QUERY_SHAPE_ERRORS.items():
        assert set(entries) <= live[handler], (
            f"{handler} documents {sorted(set(entries) - live[handler])}"
        )


def test_compare_missing_parameters_keeps_its_400(client):
    """``/compare`` answers 400 with a prose ``error``, not 422 and not a code.

    The prose is an inconsistency with the coded 422s on ``/posts`` and
    ``/comments``. It is recorded rather than changed: the message is
    wire-visible, and unifying it belongs to whoever owns the comparison
    contract.
    """
    response = client.get("/api/simulation/compare?sim_a=a")
    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert "sim_b" in body["error"]
    assert "detail" not in body and "instance" not in body


@pytest.mark.parametrize("path,param", SILENT_DEFAULT_ON_BAD_SCALAR)
def test_malformed_scalar_is_rejected_not_defaulted(client, path, param):
    """A malformed integer must be refused, not silently become the default.

    ``/posts`` and ``/comments`` already answered 422 here; ``/history``,
    ``/actions`` and ``/timeline`` did not, because
    ``request.args.get(..., type=int)`` yields the default when the value will
    not parse, so a client typo was indistinguishable from an absent parameter
    and the caller got a 200 built from the default.

    Fixed in ``read_routes.py`` with ``int_query_arg``, which raises
    ``MalformedQueryScalar`` and the handler answers with the same
    ``422 invalid_limit_or_offset`` envelope the rest of the module uses. This
    was an ``xfail`` while the defect was open; it is now a live assertion.
    """
    response = client.get(f"{path}?{param}=abc")
    assert response.status_code == 422
    assert response.get_json()["error"] == "invalid_limit_or_offset"


@pytest.mark.parametrize("path,param", RAISES_ON_BAD_SCALAR)
def test_malformed_scalar_does_not_answer_500(client, path, param):
    """Untrusted input must not reach a 500 with the exception text in ``error``.

    ``/opinions`` and its ``/generated-interactions`` alias called ``int()``
    unguarded, so a malformed value raised into the generic ``except``, which
    answered 500 carrying ``str(e)`` -- an internal exception string in a
    response body. ``strip_traceback_in_production`` does not inspect JSON body
    text, so nothing else caught it.

    Fixed in ``read_routes.py`` by the same ``int()`` guard ``/posts`` and
    ``/comments`` already used. This was an ``xfail`` when first recorded; it is
    now a live assertion. ``test_read_query_param_errors.py`` covers the same
    defect with a wider set of malformed values.
    """
    response = client.get(f"{path}?{param}=abc")
    assert response.status_code == 422
    assert "invalid literal for int()" not in response.get_data(as_text=True)
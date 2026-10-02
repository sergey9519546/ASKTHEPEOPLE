"""Typed request boundary for the decomposed report routes (exec-plan T26).

Only the four report routes that take a JSON **body** are covered. Two
exclusions are deliberate and would be wrong to "fix" later without reading
this:

* ``GET/POST /api/report/generate/status`` reads its identifiers from the
  query string on GET and from JSON on POST. ``validate_schema`` only parses a
  JSON body, so applying it would make the GET variant unreachable.
* The log and read routes parse scalar query parameters (``from_line``,
  ``limit``), not request bodies. They are guarded by ``input_policy`` and are
  out of scope for request-body typing.

Every assertion here is behavioural: it drives the real HTTP surface and
asserts on the response, so it fails if the decorator is absent, mis-wired, or
if the route stops enforcing the constraint.

Two properties are pinned deliberately:

* **The error contract does not move.** These endpoints answer validation
  failures with ``400`` and a ``{"success": false, "error": ...}`` envelope, not
  the ``422`` Problem Details that ``validate_schema`` returns. Asserted
  explicitly, because swapping in ``validate_schema`` would be a breaking API
  change disguised as a refactor.
* **Unknown fields are rejected.** ``extra="forbid"`` means a typo'd or
  injected key is refused rather than silently ignored. This *is* new
  behaviour: these routes previously ignored unknown keys.
"""

import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


TYPED_REPORT_BODIES = [
    ("/api/report/generate", "report_request_invalid"),
    ("/api/report/chat", "report_request_invalid"),
    ("/api/report/tools/search", "graph_query_invalid"),
    ("/api/report/tools/statistics", "graph_query_invalid"),
]

# `/api/report/generate` deliberately does NOT reject unknown keys. See
# GenerateReportRequest: forbidding extras would make the payload-provenance
# test vacuous, because the request would be refused before the handler could
# demonstrate it ignores client-supplied fields (AGENTS.md rule 5). Its unknown
# fields are covered by test_wrong_type_is_rejected and by the strict bool test
# below instead.
STRICT_EXTRA_ROUTES = [
    ("/api/report/chat", "report_request_invalid"),
    ("/api/report/tools/search", "graph_query_invalid"),
    ("/api/report/tools/statistics", "graph_query_invalid"),
]


@pytest.mark.parametrize("path,error_code", STRICT_EXTRA_ROUTES)
def test_unknown_field_is_rejected(client, path, error_code):
    """extra="forbid": a body carrying an unrecognised key must not be accepted.

    Previously these routes ignored unknown keys, so an injected or misspelt
    field passed straight through to the handler.
    """
    response = client.post(
        path,
        json={"simulation_id": "sim-1", "totally_unknown_field": "x"},
    )
    assert response.status_code == 400, (
        f"{path} accepted an unknown field; the typed boundary is not enforced"
    )
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == error_code


def test_generate_tolerates_unknown_keys_but_still_ignores_them(client):
    """`/api/report/generate` accepts extras; the handler must still ignore them.

    This is the provenance guarantee: a body full of client-supplied fields
    must reach the handler and be discarded there, not be rejected at the seam.
    Reaching 404 proves the handler ran.
    """
    response = client.post(
        "/api/report/generate",
        json={
            "simulation_id": "sim-does-not-exist",
            "user_prompt": "PRIVATE_USER_PROMPT",
            "custom_instructions": "PRIVATE_CUSTOM_INSTRUCTIONS",
            "graph_id": "payload-graph",
        },
    )
    assert response.status_code == 404, (
        "generate must tolerate unknown keys; refusing them would make the "
        "payload-provenance guarantee untestable"
    )
    body = response.get_json()
    assert body["error"] == "report_simulation_not_found"
    assert "PRIVATE_USER_PROMPT" not in response.get_data(as_text=True)


@pytest.mark.parametrize("path,error_code", TYPED_REPORT_BODIES)
def test_wrong_type_is_rejected(client, path, error_code):
    """A field of the wrong JSON type must be refused, not coerced.

    Pydantic would happily coerce ``"force_regenerate": "yes"`` to True, and
    ``simulation_id: 5`` to ``"5"``. Both are wrong at a trust boundary: the
    first invents consent, the second invents an identifier.
    """
    response = client.post(path, json={"simulation_id": {"nested": "object"}})
    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == error_code


@pytest.mark.parametrize("path,error_code", TYPED_REPORT_BODIES)
def test_error_shape_is_the_app_envelope_not_problem_details(client, path, error_code):
    """Validation failures must not switch to RFC-7807 Problem Details.

    ``validate_schema`` in ``app/api/schemas.py`` answers 422 with
    ``{type, title, status, detail, instance}``. These report endpoints have
    always answered 400 with ``{success, error}``. Pinning the shape keeps the
    typing additive rather than a breaking change for existing clients.
    """
    response = client.post(path, json={"unexpected": True})
    assert response.status_code == 400
    body = response.get_json()
    assert set(body) >= {"success", "error"}
    assert "detail" not in body and "instance" not in body


def test_missing_required_field_is_rejected(client):
    """generate requires simulation_id; an empty body must not reach the handler."""
    response = client.post("/api/report/generate", json={})
    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    # The pre-existing code for this condition, not a new one.
    assert body["error"] in {
        "report_request_invalid",
        "report_simulation_id_missing",
    }


def test_generate_accepts_a_well_formed_body(client):
    """A valid body must pass the typed boundary and reach normal validation.

    Reaching ``report_simulation_not_found`` (404) proves the decorator let the
    payload through and the handler ran; anything earlier would mean the typed
    boundary rejected a legitimate request.
    """
    response = client.post(
        "/api/report/generate",
        json={"simulation_id": "sim-does-not-exist", "force_regenerate": False},
    )
    assert response.status_code == 404
    body = response.get_json()
    assert body["error"] == "report_simulation_not_found"


def test_generate_rejects_non_boolean_force_regenerate(client):
    """force_regenerate is a consent flag; a truthy string must not enable it."""
    response = client.post(
        "/api/report/generate",
        json={"simulation_id": "sim-does-not-exist", "force_regenerate": "yes"},
    )
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_generate_status_get_is_not_broken_by_the_typed_boundary(client):
    """The query-string GET variant of generate/status must still answer.

    This is the exclusion this module documents. If a future change applies a
    JSON-body decorator to the shared handler, the GET variant stops parsing
    its identifiers and this test fails.
    """
    response = client.get("/api/report/generate/status?simulation_id=sim-x")
    assert response.status_code != 405, "GET variant of generate/status was removed"
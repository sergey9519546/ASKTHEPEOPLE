"""Typed request boundary for the interview and export route modules (T26, slice 3).

Five handlers behind ten registered URLs are typed. Two handlers behind two
further URLs are deliberately not, and the exclusion is a decision rather than
an oversight:

* ``GET /api/simulation/<simulation_id>/config/download`` and
  ``GET /api/simulation/script/<script_name>/download`` read a path parameter
  and no request body. ``enforce_schema`` parses a JSON body only, so a model
  there could never fire and would add nothing but a second error envelope.

Every assertion drives the real HTTP surface, so each one fails if the
decorator is absent, mis-wired, or moved above the rate limiter.

Four properties are pinned deliberately.

* **The error contract does not move.** These routes answer 400 with
  ``{"success": false, "error": ...}``, not the 422 Problem Details that
  ``validate_schema`` returns. Each route reuses the code it already emitted
  for a body it could not use -- ``invalid_text_field`` on the three
  prompt-bearing interview handlers (the code ``bounded_text`` raises for a
  wrong-typed field), ``Please provide simulation_id`` on the history handler
  and ``No results to export`` on the export handler, which are the only 400s
  those two ever produced. Inventing a code would have been a breaking change
  dressed as a refactor.
* **Shape is enforced at the seam, meaning stays with the handler.** Prompt
  length, batch size and the timeout range still answer with ``input_policy``'s
  own codes. Those codes are asserted below precisely so that duplicating the
  bounds here would fail.
* **Coercion is blocked.** ``strict=True`` is what stops ``"yes"`` becoming
  True and ``5`` becoming ``"5"``.
* **Unknown keys are refused.** This *is* new behaviour: every route here
  previously ignored them. ``extra="forbid"`` is safe for all ten because every
  key any caller or test sends is a key the handler already reads -- the
  evidence is in ``app/api/schemas_interview_export.py`` and in the
  ``extra="forbid"`` acceptance tests below. Compare ``GenerateReportRequest``,
  which must use ``extra="ignore"`` because a provenance test needs its
  client-supplied canaries to reach the handler in order to be discarded.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import create_app
from app.api.routes import export_routes, interview_routes
from app.services.claim_boundary import synthetic_output_disclosure
from app.utils.input_policy import INTERVIEW_BATCH_MAX, INTERVIEW_PROMPT_MAX

SINGLE_URLS = [
    "/api/simulation/generated-response",
    "/api/simulation/interview",
]
BATCH_URLS = [
    "/api/simulation/generated-response/batch",
    "/api/simulation/interview/batch",
]
ALL_URLS = [
    "/api/simulation/generated-response/all",
    "/api/simulation/interview/all",
]
HISTORY_URLS = [
    "/api/simulation/generated-response/history",
    "/api/simulation/interview/history",
]
EXPORT_URLS = [
    "/api/simulation/sim_123/export/generated-responses",
    "/api/simulation/sim_123/export/survey",
]

TEXT_FIELD_INVALID = "invalid_text_field"
SIMULATION_ID_MISSING = "Please provide simulation_id"
NO_RESULTS = "No results to export"

INTERVIEW_BODY_ROUTES = [
    (path, TEXT_FIELD_INVALID) for path in SINGLE_URLS + BATCH_URLS + ALL_URLS
]
HISTORY_BODY_ROUTES = [(path, SIMULATION_ID_MISSING) for path in HISTORY_URLS]
EXPORT_BODY_ROUTES = [(path, NO_RESULTS) for path in EXPORT_URLS]
TYPED_BODY_ROUTES = (
    INTERVIEW_BODY_ROUTES + HISTORY_BODY_ROUTES + EXPORT_BODY_ROUTES
)

# The handler answers an unsupported platform itself, after its input_policy
# pass and before any environment check. Reaching that message is the witness
# that a payload survived the typed boundary. The single-follow-up handler
# capitalises its sentence and the other two do not, so this is matched as a
# fragment rather than a whole string.
UNSUPPORTED_PLATFORM = "platform parameter can only be 'twitter' or 'reddit'"
ENV_NOT_RUNNING = "Simulation environment not running"

# Exactly what Step5Interaction.vue sends for a batch follow-up.
FRONTEND_SINGLE = {
    "simulation_id": "sim_123",
    "agent_id": 0,
    "prompt": "What concern might this profile raise?",
}
FRONTEND_BATCH = {
    "simulation_id": "sim_123",
    "questions": [{"agent_id": 0, "prompt": "What concern might this profile raise?"}],
    "bypass_prompt_optimization": False,
}
FRONTEND_ALL = {
    "simulation_id": "sim_123",
    "prompt": "What concern might this profile raise?",
}


@pytest.fixture()
def app():
    application = create_app()
    application.config.update(
        TESTING=True,
        DEBUG=True,
        APP_TOKEN=None,
        # The limiter is a module-level singleton with in-memory storage, so
        # its counters outlive one create_app(). Disable it for isolation
        # rather than inherit another module's exhausted "10 per hour" bucket.
        RATELIMIT_ENABLED=False,
    )
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _assert_envelope(response, path, error_code):
    assert response.status_code == 400, (
        f"{path} did not answer 400 for a typed-boundary violation"
    )
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == error_code, (
        f"{path} changed its error code; the typed boundary must reuse the "
        f"code the handler already returned for this condition"
    )


# A concrete path parameter stands in for the rule's converter token, so the
# reachability check below compares like with like.
RULE_FOR_URL = {path: path.replace("sim_123", "<simulation_id>") for path in EXPORT_URLS}


@pytest.mark.parametrize("path,error_code", TYPED_BODY_ROUTES)
def test_typed_route_is_registered_on_the_real_app(app, path, error_code):
    """A handler that is defined but not registered answers 404 forever.

    Reachability is asserted here rather than assumed from a source read: the
    Flask shorthand decorators are easy to lose track of.
    """
    rules = {
        rule.rule
        for rule in app.url_map.iter_rules()
        if "/api/simulation" in rule.rule
    }
    assert RULE_FOR_URL.get(path, path) in rules, (
        f"{path} is not registered on the real app"
    )


@pytest.mark.parametrize("path,error_code", TYPED_BODY_ROUTES)
def test_unknown_field_is_rejected(client, path, error_code):
    """extra="forbid": an unrecognised key must be refused, not passed through.

    Previously all ten routes ignored unknown keys, so an injected or misspelt
    field reached the handler.
    """
    response = client.post(path, json={"totally_unknown_field": "x"})
    _assert_envelope(response, path, error_code)


@pytest.mark.parametrize("path,error_code", TYPED_BODY_ROUTES)
def test_error_shape_is_the_app_envelope_not_problem_details(
    client, path, error_code
):
    """A violation must not switch the endpoint to RFC-7807 Problem Details."""
    response = client.post(path, json={"unexpected": True})
    _assert_envelope(response, path, error_code)
    body = response.get_json()
    assert "detail" not in body and "instance" not in body
    assert "title" not in body and "type" not in body


@pytest.mark.parametrize(
    "path,error_code,payload",
    [
        (path, TEXT_FIELD_INVALID, {"simulation_id": {"nested": "object"}})
        for path in SINGLE_URLS + BATCH_URLS + ALL_URLS
    ]
    + [
        (path, SIMULATION_ID_MISSING, {"simulation_id": {"nested": "object"}})
        for path in HISTORY_URLS
    ]
    + [(path, NO_RESULTS, {"results": "not-a-list"}) for path in EXPORT_URLS],
)
def test_wrong_json_type_is_rejected(client, path, error_code, payload):
    """A field of the wrong JSON type must be refused, never coerced."""
    response = client.post(path, json=payload)
    _assert_envelope(response, path, error_code)


@pytest.mark.parametrize(
    "path,error_code",
    [(path, TEXT_FIELD_INVALID) for path in SINGLE_URLS + BATCH_URLS + ALL_URLS]
    + [(path, SIMULATION_ID_MISSING) for path in HISTORY_URLS],
)
def test_numeric_identifier_is_not_coerced_into_a_string(client, path, error_code):
    """``simulation_id: 5`` must not become ``"5"``.

    Inventing an identifier from a number is the coercion that matters most at
    this seam: every downstream lookup, filename and log line would carry an
    id the client never sent.
    """
    response = client.post(path, json={"simulation_id": 5})
    _assert_envelope(response, path, error_code)


@pytest.mark.parametrize(
    "path,error_code,payload",
    [
        *[
            (
                path,
                TEXT_FIELD_INVALID,
                {**FRONTEND_SINGLE, "bypass_prompt_optimization": "yes"},
            )
            for path in SINGLE_URLS
        ],
        *[
            (
                path,
                TEXT_FIELD_INVALID,
                {
                    "simulation_id": "sim_123",
                    "questions": [
                        {"agent_id": 0, "prompt": "q", "raw": "yes"}
                    ],
                },
            )
            for path in BATCH_URLS
        ],
        *[
            (
                path,
                TEXT_FIELD_INVALID,
                {**FRONTEND_ALL, "raw": "yes"},
            )
            for path in ALL_URLS
        ],
    ],
)
def test_truthy_string_is_not_coerced_into_a_flag(client, path, error_code, payload):
    """A flag must arrive as a JSON boolean or not at all.

    ``raw`` and ``bypass_prompt_optimization`` are read only under
    ``Config.DEBUG``, but they are real flags: coercing ``"yes"`` to True would
    grant a prompt-optimisation bypass the client never asked for. The batch
    case uses an item-level flag, so the nested model is proved strict too.
    """
    response = client.post(path, json=payload)
    _assert_envelope(response, path, error_code)


@pytest.mark.parametrize("path", BATCH_URLS)
def test_batch_item_identifier_is_not_coerced(client, path):
    """The nested question model is strict as well as the outer one."""
    response = client.post(
        path,
        json={"simulation_id": "sim_123", "questions": [{"agent_id": "0", "prompt": "q"}]},
    )
    _assert_envelope(response, path, TEXT_FIELD_INVALID)


@pytest.mark.parametrize("path", BATCH_URLS)
def test_batch_item_shape_is_enforced(client, path):
    """An unrecognised key inside a question item is refused.

    The item dict is forwarded verbatim over IPC to the child process, so an
    unchecked key is an unchecked instruction channel.
    """
    response = client.post(
        path,
        json={
            "simulation_id": "sim_123",
            "questions": [{"agent_id": 0, "prompt": "q", "injected": "x"}],
        },
    )
    _assert_envelope(response, path, TEXT_FIELD_INVALID)


@pytest.mark.parametrize(
    "path,payload",
    [
        *[(path, FRONTEND_SINGLE) for path in SINGLE_URLS],
        *[(path, FRONTEND_BATCH) for path in BATCH_URLS],
        *[(path, FRONTEND_ALL) for path in ALL_URLS],
    ],
)
def test_frontend_payload_reaches_the_handler(client, monkeypatch, path, payload):
    """A real caller payload must survive the boundary untouched.

    Reaching the handler's own "environment not running" 400 proves the
    decorator let the payload through. Any earlier 400 would mean the typed
    boundary had started rejecting documented requests.
    """
    monkeypatch.setattr(
        interview_routes.SimulationRunner,
        "check_env_alive",
        lambda _simulation_id: False,
    )
    response = client.post(path, json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert ENV_NOT_RUNNING in body["error"]
    assert body["error"] != TEXT_FIELD_INVALID, (
        f"{path} rejected a documented payload at the seam"
    )


@pytest.mark.parametrize(
    "path,error_code",
    [(path, TEXT_FIELD_INVALID) for path in SINGLE_URLS + BATCH_URLS + ALL_URLS],
)
def test_platform_check_stays_with_the_handler(client, path, error_code):
    """``platform`` is typed as a string, not constrained to an enum.

    The handlers already reject an unsupported value with their own wording.
    Constraining it in the model would move that answer onto a different code,
    which is a breaking change rather than a typing change.
    """
    payload = {**FRONTEND_SINGLE, "platform": "mastodon"}
    if path in BATCH_URLS:
        payload = {**FRONTEND_BATCH, "platform": "mastodon"}
    elif path in ALL_URLS:
        payload = {**FRONTEND_ALL, "platform": "mastodon"}
    response = client.post(path, json=payload)
    assert response.status_code == 400
    assert UNSUPPORTED_PLATFORM in response.get_json()["error"]


@pytest.mark.parametrize("path", HISTORY_URLS)
def test_history_body_reaches_the_handler(client, monkeypatch, path):
    """The history handler runs no input_policy pass; the body must still land."""
    monkeypatch.setattr(
        interview_routes.SimulationRunner,
        "get_interview_history",
        lambda **_kwargs: [],
    )
    response = client.post(
        path,
        json={"simulation_id": "sim_123", "platform": "reddit", "agent_id": 3, "limit": 5},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["count"] == 0
    assert body["disclosure"] == synthetic_output_disclosure()


@pytest.mark.parametrize("path", EXPORT_URLS)
def test_export_body_reaches_the_handler(client, monkeypatch, path):
    """A valid export body must produce a CSV, not a typed-boundary 400."""
    monkeypatch.setattr(
        export_routes,
        "ZepToolsService",
        lambda: SimpleNamespace(),
    )
    response = client.post(
        path,
        json={
            "results": [
                {
                    "agent_name": "Generated profile 7",
                    "profession": "rider",
                    "answer": "I might change routes.",
                }
            ]
        },
    )
    assert response.status_code == 200
    assert b"MODEL_GENERATED" in response.data


@pytest.mark.parametrize(
    "path,expected_error",
    [
        *[(path, "missing_required_field") for path in SINGLE_URLS + ALL_URLS],
        *[(path, SIMULATION_ID_MISSING) for path in BATCH_URLS + HISTORY_URLS],
        *[(path, NO_RESULTS) for path in EXPORT_URLS],
    ],
)
def test_empty_body_still_gets_the_handlers_own_answer(client, path, expected_error):
    """No field is required in the models.

    The handlers own the "missing X" responses and their codes; making a field
    required would collapse two distinct 400s into one and break clients that
    branch on them. On the history route the handler's answer and the seam's
    code are the same string by construction, which is why that route reuses
    it rather than inventing one.
    """
    response = client.post(path, json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == expected_error


@pytest.mark.parametrize("path,error_code", TYPED_BODY_ROUTES)
def test_non_object_body_is_rejected_as_a_client_error(client, path, error_code):
    """A bare list or string body is a 400, not a 500.

    A non-object body yields a validation error with an empty ``loc``; the seam
    must not index into it.
    """
    for body in ([1, 2, 3], "a string body"):
        response = client.post(path, json=body)
        _assert_envelope(response, path, error_code)


@pytest.mark.parametrize("path", SINGLE_URLS + ALL_URLS)
def test_prompt_length_bound_stays_with_input_policy(client, path):
    """The model carries no max_length; ``bounded_text`` still owns the bound.

    If the bound were duplicated here the code would become
    ``invalid_text_field`` and this assertion would fail, which is exactly the
    regression this test exists to prevent.
    """
    payload = FRONTEND_ALL if path in ALL_URLS else FRONTEND_SINGLE
    response = client.post(
        path,
        json={**payload, "prompt": "x" * (INTERVIEW_PROMPT_MAX + 1)},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "text_field_too_long"


@pytest.mark.parametrize("path", BATCH_URLS)
def test_batch_item_cap_stays_with_input_policy(client, path):
    """The model carries no item cap; ``validate_item_count`` still owns it."""
    response = client.post(
        path,
        json={
            "simulation_id": "sim_123",
            "questions": [
                {"agent_id": index, "prompt": "q"}
                for index in range(INTERVIEW_BATCH_MAX + 1)
            ],
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "too_many_items"


@pytest.mark.parametrize("path,error_code", INTERVIEW_BODY_ROUTES)
def test_timeout_range_stays_with_input_policy(client, path, error_code):
    """An in-range violation of the range is the handler's, not the seam's."""
    payload = {**FRONTEND_ALL, "timeout": 0}
    if path in SINGLE_URLS:
        payload = {**FRONTEND_SINGLE, "timeout": 0}
    elif path in BATCH_URLS:
        payload = {**FRONTEND_BATCH, "timeout": 0}
    response = client.post(path, json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "integer_field_out_of_range"
    assert body["error"] != error_code


@pytest.mark.parametrize("path", BATCH_URLS)
def test_legacy_interviews_alias_is_a_supported_key(client, monkeypatch, path):
    """``interviews`` is the legacy alias the handler still reads.

    ``extra="forbid"`` would reject it as an unknown key and break a documented
    payload, so the model declares both names.
    """
    monkeypatch.setattr(
        interview_routes.SimulationRunner,
        "check_env_alive",
        lambda _simulation_id: False,
    )
    response = client.post(
        path,
        json={"simulation_id": "sim_123", "interviews": [{"agent_id": 0, "prompt": "q"}]},
    )
    assert response.status_code == 400
    assert ENV_NOT_RUNNING in response.get_json()["error"]


def test_config_download_takes_no_body_and_still_answers(client):
    """Deliberately untyped: a path-parameter GET with no request body.

    ``enforce_schema`` parses a JSON body, so a model here could never fire.
    Asserting the route still answers is the guard against someone adding one
    later for symmetry.
    """
    response = client.get(
        "/api/simulation/sim_absent_typed_boundary/config/download"
    )
    assert response.status_code == 404
    assert "does not exist" in response.get_json()["error"]


def test_script_download_takes_no_body_and_still_answers(client):
    """Deliberately untyped, same reason as the config download above."""
    response = client.get("/api/simulation/script/not-a-real-script.py/download")
    assert response.status_code == 400
    assert response.get_json()["error"].startswith("Unknown script")
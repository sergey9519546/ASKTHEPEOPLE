"""Typed request boundary for the entity and settings route modules (T26 slice 2).

Two of the six routes in scope take a JSON body and are typed. The other four
are deliberately not, and the exclusions are decisions that would be wrong to
"fix" later without reading this:

* All three `entity_routes` handlers are GET-only. They read path parameters and
  the scalar query strings ``entity_types`` and ``enrich``, and none of them
  calls ``request.get_json``. ``enforce_schema`` parses a JSON body, so a schema
  there could never fire and could only add a second error envelope.
* ``GET /api/settings`` reads no body.

What is asserted here is behavioural against the real HTTP surface, so each test
fails if the decorator is absent, mis-wired, or reordered.

Three properties are pinned deliberately:

* **The feature gate still comes first.** ``ALLOW_RUNTIME_SETTINGS`` defaults
  off, and both mutating routes answer ``403 runtime_settings_disabled`` before
  anything parses the body. A route-level decorator on these two would invert
  that and answer 400 for a malformed body, leaking whether a body parses.
* **The error contract does not move to Problem Details.** These routes answer
  400 with ``{"success": false, "error": ...}``, not the 422 that
  ``validate_schema`` returns.
* **Shape is enforced at the seam; semantics stay with the handler.** Maximum
  lengths, control characters, the operator URL allowlist and the
  "a new API key is required" rule all still answer with the handler's own
  messages, which is the proof that ``strict=True`` here added typing without
  taking ownership of meaning.
"""

from __future__ import annotations

import inspect
import os

import pytest

from app import create_app
from app.api import settings as settings_module
from app.api.routes import entity_routes
from app.api.schemas_entity_settings import (
    SETTINGS_REQUEST_INVALID,
    MUTABLE_PROVIDER_KEYS,
    ProviderConnectionTestRequest,
    ProviderSettingsUpdateRequest,
)
from app.config import Config

ENTITY_ROUTES = [
    "/api/simulation/entities/<graph_id>",
    "/api/simulation/entities/<graph_id>/<entity_uuid>",
    "/api/simulation/entities/<graph_id>/by-type/<entity_type>",
]

SETTINGS_WRITE_ROUTES = ["/api/settings", "/api/settings/test"]

_TOUCHED_CONFIG_ATTRS = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL_NAME",
    "ZEP_API_KEY",
)
_TOUCHED_ENV_KEYS = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL_NAME",
    "ZEP_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "LLM_BOOST_API_KEY",
    "LLM_BOOST_BASE_URL",
    "LLM_BOOST_MODEL_NAME",
)


@pytest.fixture()
def app(tmp_path):
    application = create_app()
    application.config.update(
        TESTING=True,
        DEBUG=True,
        APP_TOKEN=None,
        # The limiter is a module-level singleton with in-memory storage, so its
        # counters outlive a single create_app(). Disable it for isolation
        # rather than inherit another test module's exhausted buckets.
        RATELIMIT_ENABLED=False,
        ALLOW_RUNTIME_SETTINGS=False,
        RUNTIME_SETTINGS_ENV_PATH=str(tmp_path / ".env"),
    )
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runtime_app(app):
    """The same app with the control plane explicitly enabled and isolated."""
    config_originals = {key: getattr(Config, key) for key in _TOUCHED_CONFIG_ATTRS}
    env_originals = {key: os.environ.get(key) for key in _TOUCHED_ENV_KEYS}
    app.config.update(
        ALLOW_RUNTIME_SETTINGS=True,
        ALLOW_PRIVATE_LLM_ENDPOINTS=True,
        LLM_ALLOWED_BASE_URLS="http://127.0.0.1:11434/v1",
    )
    yield app
    for key, value in config_originals.items():
        setattr(Config, key, value)
    for key, value in env_originals.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture()
def runtime_client(runtime_app):
    return runtime_app.test_client()


# ---------------------------------------------------------------------------
# entity_routes: GET-only, no request body, no schema
# ---------------------------------------------------------------------------


def test_every_entity_route_is_registered(app):
    """`entity_routes` shipped once unimported and every route answered 404.

    A grep for `.route(` is not evidence of reachability, so this asserts the
    URL map directly rather than trusting the decorator.
    """
    rules = {
        rule.rule
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/simulation/entities")
    }
    assert rules == set(ENTITY_ROUTES)


def test_every_entity_route_answers_from_its_handler(client):
    """Each route reaches its own handler, proven by the handler's own code.

    A missing route answers 404 with an HTML body; these answer 400 with the
    app envelope because `resolve_project_graph` rejects the absent
    ``project_id`` before any provider access.
    """
    paths = [
        "/api/simulation/entities/graph-1",
        "/api/simulation/entities/graph-1/entity-1",
        "/api/simulation/entities/graph-1/by-type/Person",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 400, path
        assert response.get_json() == {
            "success": False,
            "error": "project_id_required",
        }, path


def test_entity_routes_do_not_parse_a_json_body(client):
    """No entity route calls `request.get_json`, so none may gain a body schema.

    If a future change adds a JSON-body decorator to this module, a GET carrying
    a body would start being refused on shape alone.
    """
    source = inspect.getsource(entity_routes)
    assert "get_json" not in source
    assert "enforce_schema" not in source

    for path in (
        "/api/simulation/entities/graph-1",
        "/api/simulation/entities/graph-1/entity-1",
    ):
        response = client.get(path, json={"unexpected": {"nested": True}})
        assert response.status_code == 400
        assert response.get_json()["error"] == "project_id_required"


@pytest.mark.parametrize("path", ENTITY_ROUTES)
def test_entity_routes_are_get_only(client, path):
    """These three routes are read paths; a write verb must not be routed."""
    concrete = (
        path.replace("<graph_id>", "graph-1")
        .replace("<entity_uuid>", "entity-1")
        .replace("<entity_type>", "Person")
    )
    response = client.post(concrete, json={})
    assert response.status_code == 405


def test_entity_query_parameters_are_left_to_the_handler(client):
    """`entity_types` and `enrich` are scalars the handler parses itself.

    Pinned so the no-schema decision for this module is a stated contract rather
    than an omission someone re-litigates with a model.
    """
    source = inspect.getsource(entity_routes)
    assert "request.args.get('entity_types')" in source
    assert "request.args.get('enrich', 'true')" in source


# ---------------------------------------------------------------------------
# GET /api/settings: no request body, no schema
# ---------------------------------------------------------------------------


def test_get_settings_reads_no_body(client):
    response = client.get("/api/settings", json={"LLM_API_KEY": "unexpected"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["LLM_API_KEY"] == ""


# ---------------------------------------------------------------------------
# The feature gate stays ahead of the typed boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", SETTINGS_WRITE_ROUTES)
@pytest.mark.parametrize(
    "payload",
    [
        {"LLM_API_KEY": "new-key"},
        {"totally_unknown_field": "x"},
        [1, 2, 3],
    ],
    ids=["allowlisted", "unknown-key", "non-object"],
)
def test_disabled_control_plane_answers_403_for_every_body(client, path, payload):
    """With ALLOW_RUNTIME_SETTINGS off, the gate answers before the body parses.

    A route-level `enforce_schema` would answer 400 for the last two payloads,
    which tells an unauthenticated caller whether their JSON was well formed.
    """
    response = client.post(path, json=payload)
    assert response.status_code == 403, path
    assert response.get_json()["error"] == "runtime_settings_disabled"


@pytest.mark.parametrize("path", SETTINGS_WRITE_ROUTES)
def test_unparseable_body_still_gets_the_gate(client, path):
    """A body that is not JSON at all is still gated, not schema-rejected."""
    response = client.post(path, data="not-json", content_type="text/plain")
    assert response.status_code == 403
    assert response.get_json()["error"] == "runtime_settings_disabled"


# ---------------------------------------------------------------------------
# The typed boundary itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", SETTINGS_WRITE_ROUTES)
def test_unknown_field_is_rejected(runtime_client, path):
    """extra="forbid": an unrecognised key is refused instead of silently dropped.

    These routes previously ignored unknown keys, and the ignore produced a
    misleading answer rather than a silent success: posting only
    ``totally_unknown_field`` to the connection test returned "API Key is
    required to run test", which reads as an operator who forgot to paste a key
    rather than a body the route does not recognise at all.
    """
    response = runtime_client.post(path, json={"totally_unknown_field": "x"})
    assert response.status_code == 400
    body = response.get_json()
    assert body == {"success": False, "error": SETTINGS_REQUEST_INVALID}


@pytest.mark.parametrize(
    "payload",
    [
        {"LLM_API_KEY": {"nested": "object"}},
        {"LLM_MODEL_NAME": ["a", "b"]},
    ],
    ids=["object-for-string", "array-for-string"],
)
def test_wrong_type_is_refused_not_coerced(runtime_client, payload):
    """`strict=True`: a wrong JSON type is refused, never coerced to a string.

    Without it Pydantic would turn `LLM_API_KEY: 5` into `"5"` and hand a
    five-character credential to the env file and `os.environ`.
    """
    response = runtime_client.post("/api/settings", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"] == SETTINGS_REQUEST_INVALID


@pytest.mark.parametrize(
    "payload",
    [{"LLM_API_KEY": 5}, {"LLM_API_KEY": True}, {"LLM_API_KEY": 1.5}],
    ids=["int", "bool", "float"],
)
def test_scalar_is_not_coerced_into_a_credential(runtime_client, payload):
    """A number or a bool must not become a string the persist path would write."""
    response = runtime_client.post("/api/settings", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"] == SETTINGS_REQUEST_INVALID


def test_connection_test_target_is_not_coerced(runtime_client):
    """`target` selects the provider branch; `1` must not silently become "1"."""
    response = runtime_client.post("/api/settings/test", json={"target": 1})
    assert response.status_code == 400
    assert response.get_json()["error"] == SETTINGS_REQUEST_INVALID


@pytest.mark.parametrize("path", SETTINGS_WRITE_ROUTES)
def test_non_object_body_is_refused(runtime_client, path):
    """A JSON array or scalar body is not a settings document."""
    for payload in ([1, 2, 3], "settings", 7):
        response = runtime_client.post(path, json=payload)
        assert response.status_code == 400, (path, payload)
        assert response.get_json()["error"] == SETTINGS_REQUEST_INVALID


@pytest.mark.parametrize("path", SETTINGS_WRITE_ROUTES)
def test_error_shape_is_the_app_envelope_not_problem_details(runtime_client, path):
    """Typing must not switch these routes to RFC-7807 Problem Details."""
    response = runtime_client.post(path, json={"unknown": True})
    assert response.status_code == 400
    body = response.get_json()
    assert set(body) == {"success", "error"}
    assert "detail" not in body and "instance" not in body


# ---------------------------------------------------------------------------
# Well-formed bodies still reach the handler
# ---------------------------------------------------------------------------


def test_well_formed_update_reaches_the_handler(runtime_client):
    """Exactly the shape `SettingsModal.vue` posts, unchanged.

    `form.value` holds the eight mutable keys and nothing else, and `save()`
    posts it verbatim, so this is the real client's payload.
    """
    response = runtime_client.post("/api/settings", json={
        "LLM_API_KEY": "boundary-test-key",
        "LLM_BASE_URL": "",
        "LLM_MODEL_NAME": "",
        "ZEP_API_KEY": "",
        "BRAVE_SEARCH_API_KEY": "",
        "LLM_BOOST_API_KEY": "",
        "LLM_BOOST_BASE_URL": "",
        "LLM_BOOST_MODEL_NAME": "",
    })
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "Settings saved successfully"
    assert body["data"]["LLM_API_KEY"] == ""


def test_minimal_update_still_persists(runtime_client):
    response = runtime_client.post("/api/settings", json={"LLM_API_KEY": "minimal-key"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_well_formed_connection_test_reaches_the_handler(runtime_client):
    """Passing the schema must land on the handler's own "Model Name" check.

    That check runs before any URL resolution or provider call, so reaching its
    message proves the payload traversed the typed boundary.
    """
    response = runtime_client.post("/api/settings/test", json={
        "LLM_API_KEY": "caller-key",
        "LLM_BASE_URL": "https://api.openai.com/v1",
    })
    assert response.status_code == 400
    assert "Model Name is required" in response.get_json()["error"]


def test_zep_branch_is_still_selected(runtime_client):
    response = runtime_client.post("/api/settings/test", json={
        "target": "zep",
        "ZEP_API_KEY": "",
    })
    assert response.status_code == 400
    assert "ZEP_API_KEY is required" in response.get_json()["error"]


def test_absent_target_still_defaults_to_the_llm_branch(runtime_client):
    """`target` is optional so the handler keeps owning the "llm" default.

    Landing on the operator allowlist rule rather than the schema code proves
    the payload crossed the boundary and reached URL validation.
    """
    response = runtime_client.post("/api/settings/test", json={
        "LLM_API_KEY": "caller-key",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_MODEL_NAME": "gpt-4o-mini",
    })
    assert response.status_code == 400
    assert "allowlist" in response.get_json()["error"]


# ---------------------------------------------------------------------------
# Semantics stay with the handler
# ---------------------------------------------------------------------------


def test_maximum_length_is_still_the_handler_rule(runtime_client):
    """Length bounds are not shape. `_clean_value` must keep answering them."""
    response = runtime_client.post(
        "/api/settings", json={"LLM_API_KEY": "x" * 9000}
    )
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error == "LLM_API_KEY is too long"
    assert error != SETTINGS_REQUEST_INVALID


def test_control_characters_are_still_the_handler_rule(runtime_client):
    response = runtime_client.post(
        "/api/settings", json={"LLM_MODEL_NAME": "bad\nvalue"}
    )
    assert response.status_code == 400
    assert "invalid control characters" in response.get_json()["error"]


def test_url_allowlist_is_still_the_handler_rule(runtime_client):
    response = runtime_client.post("/api/settings", json={
        "LLM_API_KEY": "caller-key",
        "LLM_BASE_URL": "http://169.254.169.254/latest/meta-data",
    })
    assert response.status_code == 400
    assert "allowlist" in response.get_json()["error"]


def test_explicit_null_is_still_a_string_requirement(runtime_client):
    """`null` passes the shape check and is refused by the handler as before.

    Guards the specific regression to avoid: switching the handler to read
    `request.validated_data` would make an explicit `null` mean "absent" and
    start accepting a body this route has always refused.
    """
    response = runtime_client.post("/api/settings", json={"LLM_API_KEY": None})
    assert response.status_code == 400
    assert response.get_json()["error"] == "LLM_API_KEY must be a string"


def test_empty_object_is_still_the_handlers_empty_rule(runtime_client):
    """An empty object must not be absorbed by the boundary."""
    response = runtime_client.post("/api/settings", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "No settings were provided"


def test_non_json_object_body_is_still_the_handlers_rule(runtime_client):
    """`enforce_schema` coerces an absent body to `{}`, so the handler's own
    non-object check has to stay reachable for a non-JSON body."""
    response = runtime_client.post(
        "/api/settings", data="not-json", content_type="text/plain"
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "JSON object required"


# ---------------------------------------------------------------------------
# Model configuration, pinned so the decisions cannot drift silently
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [ProviderSettingsUpdateRequest, ProviderConnectionTestRequest],
)
def test_models_are_strict_and_forbid_extras(model):
    assert model.model_config["strict"] is True
    assert model.model_config["extra"] == "forbid"


def test_mutable_keys_match_the_handler_allowlist():
    """The schema and the handler's allowlist loop must not drift apart.

    A key in one and not the other means either an unvalidated mutation or a
    field that validates but can never be persisted.
    """
    assert set(MUTABLE_PROVIDER_KEYS) == set(settings_module._ALL_MUTABLE_KEYS)


def test_update_model_covers_every_mutable_key():
    assert set(ProviderSettingsUpdateRequest.model_fields) == set(
        MUTABLE_PROVIDER_KEYS
    )


def test_connection_test_model_covers_every_key_the_handler_reads():
    handler_source = inspect.getsource(settings_module._test_settings_body)
    read_keys = {
        f'data.get("{key}"'
        for key in ProviderConnectionTestRequest.model_fields
    }
    for needle in read_keys:
        assert needle in handler_source, needle
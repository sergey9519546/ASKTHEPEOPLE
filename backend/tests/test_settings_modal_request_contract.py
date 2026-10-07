"""The frontend settings payload must satisfy the backend's `extra="forbid"`.

`ProviderSettingsUpdateRequest` and `ProviderConnectionTestRequest`
(`app/api/schemas_entity_settings.py`) are declared `extra="forbid"`. That is the
right call for credentials, and it has a sharp consequence: a body carrying any
key the schema does not name is refused with `400 settings_request_invalid`
rather than ignored.

`frontend/src/components/SettingsModal.vue` currently satisfies that, but only
by construction, not by contract:

* `form` is a fixed 8-key literal and `save()` posts `form.value` verbatim, so
  the posted keys are exactly `MUTABLE_PROVIDER_KEYS`;
* `loadSettings` hydrates the form with `Object.keys(form.value).forEach(...)`,
  writing key by key from the GET response.

Both are load-bearing and neither is pinned by a test. `SettingsModal.vue` has
no test at all. The specific latent break is hydration: `GET /api/settings`
returns `runtime_settings_enabled`, `allowed_llm_base_urls`,
`allow_private_llm_endpoints` and four `*_CONFIGURED` booleans, and **none** of
those are in `MUTABLE_PROVIDER_KEYS`. Rewriting line 515 as

    form.value = data;                       // or Object.assign(form.value, data)

would make `save()` post read-only keys, and every save would fail 400 with a
code the modal surfaces as a bare "Settings could not be saved." No test would
fail, because the assertion that currently prevents it lives in the shape of the
source rather than in a check.

So this module pins the invariant from both ends:

* the frontend's posted key sets, read out of the SFC, against the backend's
  declared fields; and
* the route's real behaviour for a body carrying an unknown key.

The vacuity guards at the end matter as much as the assertions. A source-parsing
contract test can pass by collecting nothing, so `test_the_key_extractor_can_fail`
and `test_this_module_can_actually_fail` assert that the extraction is capable
of failing and that the behavioural check is live.
"""

import os
import re
from pathlib import Path

import pytest

from app import create_app
from app.api.schemas_entity_settings import (
    MUTABLE_PROVIDER_KEYS,
    ProviderConnectionTestRequest,
    ProviderSettingsUpdateRequest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODAL = REPO_ROOT / "frontend" / "src" / "components" / "SettingsModal.vue"

# Keys `GET /api/settings` returns for display only. None is mutable, so none may
# ever reach `save()`. Read from the handler rather than hardcoded, so adding a
# read-only field there fails this test rather than passing it unnoticed.
_READ_ONLY_RESPONSE_KEYS = (
    "runtime_settings_enabled",
    "allowed_llm_base_urls",
    "allow_private_llm_endpoints",
)

_CONFIG_ATTRS = ("ALLOW_RUNTIME_SETTINGS", "ALLOW_PRIVATE_LLM_ENDPOINTS", "LLM_ALLOWED_BASE_URLS")


def _modal_source() -> str:
    return MODAL.read_text(encoding="utf-8")


def _form_keys(source: str) -> list[str]:
    """Keys of the `form` ref literal that `save()` posts."""
    block = re.search(r"const form = ref\(\{(.*?)\}\);", source, re.S)
    assert block, "SettingsModal.vue no longer declares `const form = ref({...})`"
    return re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*):", block.group(1), re.M)


def _connection_test_keys(source: str) -> list[str]:
    """Keys the modal posts to `POST /api/settings/test`."""
    call = re.search(r"testConnection\(\{(.*?)\}\)", source, re.S)
    assert call, "SettingsModal.vue no longer calls testConnection({...})"
    return re.findall(r"([A-Z][A-Z0-9_]*)\s*:", call.group(1))


def _save_payload_argument(source: str) -> str:
    """The expression `save()` hands to `updateSettings`."""
    call = re.search(r"updateSettings\(([^)]*)\)", source, re.S)
    assert call, "SettingsModal.vue no longer calls updateSettings(...)"
    return call.group(1).strip()


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not MODAL.is_file(), reason="SettingsModal.vue not present")
def test_form_keys_equal_the_backend_mutable_allowlist():
    """The posted key set must equal `MUTABLE_PROVIDER_KEYS` exactly.

    Equality, not containment. An extra key is a hard 400 under
    `extra="forbid"`; a missing key means a setting the UI offers can never be
    saved, which is the quieter failure of the two.
    """
    keys = set(_form_keys(_modal_source()))
    mutable = set(MUTABLE_PROVIDER_KEYS)

    assert keys - mutable == set(), (
        "SettingsModal.save() posts keys the settings schema forbids, so every "
        f"save answers 400 settings_request_invalid: {sorted(keys - mutable)}"
    )
    assert mutable - keys == set(), (
        "the backend accepts these settings keys but the modal has no field for "
        f"them, so they can never be set from the UI: {sorted(mutable - keys)}"
    )


@pytest.mark.skipif(not MODAL.is_file(), reason="SettingsModal.vue not present")
def test_save_posts_the_form_verbatim():
    """`save()` must post `form.value`, not a widened or replaced object.

    `updateSettings({ ...form.value, ...something })` is the shape that smuggles
    read-only GET keys past the key-set check above.
    """
    argument = _save_payload_argument(_modal_source())
    assert argument == "form.value", (
        f"save() posts {argument!r}; only `form.value` verbatim keeps the posted "
        "key set equal to the form literal the test above pins"
    )


@pytest.mark.skipif(not MODAL.is_file(), reason="SettingsModal.vue not present")
def test_hydration_is_key_driven_and_never_wholesale():
    """`loadSettings` must not assign the GET response into `form` wholesale.

    `form.value = data` / `Object.assign(form.value, data)` would copy
    `*_CONFIGURED`, `runtime_settings_enabled`, `allowed_llm_base_urls` and
    `allow_private_llm_endpoints` into the posted payload. Those are read-only
    and not in `MUTABLE_PROVIDER_KEYS`, so each save becomes a 400.

    `form.value[key] = ...` is matched by neither pattern: the bracket sits
    between `value` and `=`, so only whole-object assignment trips them.
    """
    source = _modal_source()

    wholesale = [
        source[max(0, m.start() - 60): m.start() + 60].replace("\n", " ")
        for m in re.finditer(r"form\.value\s*=", source)
    ]
    assign = [
        source[max(0, m.start() - 40): m.start() + 60].replace("\n", " ")
        for m in re.finditer(r"Object\.assign\(\s*form\.value", source)
    ]
    assert not wholesale and not assign, (
        "loadSettings assigns the GET response into form as a whole, which puts "
        f"read-only keys into the save payload: {wholesale + assign}"
    )

    assert re.search(r"Object\.keys\(form\.value\)", source), (
        "form hydration is no longer driven by Object.keys(form.value); the "
        "key-by-key loop is what keeps read-only response keys out of the payload"
    )


@pytest.mark.skipif(not MODAL.is_file(), reason="SettingsModal.vue not present")
def test_no_read_only_response_key_is_posted():
    """The read-only GET keys must not appear anywhere in the save payload."""
    source = _modal_source()
    for key in _READ_ONLY_RESPONSE_KEYS:
        assert key not in _form_keys(source), (
            f"{key} is read-only but is present in the form literal save() posts"
        )


@pytest.mark.skipif(not MODAL.is_file(), reason="SettingsModal.vue not present")
def test_connection_test_payload_is_accepted_by_its_schema():
    """`runConnectionTest` must post only keys `ProviderConnectionTestRequest` names."""
    posted = set(_connection_test_keys(_modal_source()))
    accepted = set(ProviderConnectionTestRequest.model_fields)
    assert posted <= accepted, (
        "the connection test posts keys its schema forbids: "
        f"{sorted(posted - accepted)}"
    )


# ---------------------------------------------------------------------------
# The route's real behaviour
# ---------------------------------------------------------------------------


@pytest.fixture()
def runtime_client(tmp_path):
    """The app with the control plane open, isolated from the real environment."""
    from app.config import Config

    originals = {key: getattr(Config, key) for key in _CONFIG_ATTRS}
    application = create_app()
    application.config.update(
        TESTING=True,
        DEBUG=True,
        APP_TOKEN=None,
        RATELIMIT_ENABLED=False,
        ALLOW_RUNTIME_SETTINGS=True,
        ALLOW_PRIVATE_LLM_ENDPOINTS=True,
        RUNTIME_SETTINGS_ENV_PATH=str(tmp_path / ".env"),
    )
    yield application.test_client()
    for key, value in originals.items():
        setattr(Config, key, value)


def test_a_body_carrying_a_read_only_key_is_refused(runtime_client):
    """The `extra="forbid"` contract is live on this route, not aspirational.

    `runtime_settings_enabled` is exactly what a wholesale `form.value = data`
    would introduce, so it is the representative payload.
    """
    response = runtime_client.post(
        "/api/settings",
        json={"LLM_API_KEY": "sk-test", "runtime_settings_enabled": True},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "settings_request_invalid"


def test_the_form_payload_as_posted_is_accepted(runtime_client):
    """The eight keys the modal actually sends must clear the boundary.

    Without this, a schema that forbade everything would satisfy the test above.
    """
    payload = {key: "value" for key in MUTABLE_PROVIDER_KEYS}
    response = runtime_client.post("/api/settings", json=payload)
    assert response.status_code != 400 or response.get_json().get(
        "error"
    ) != "settings_request_invalid", (
        "the payload the modal posts is rejected by its own schema"
    )


def test_the_feature_gate_still_precedes_the_schema(tmp_path):
    """A malformed body must 403, not 400, while runtime settings are off.

    The gate answering first is deliberate: a route-level schema decorator would
    answer 400 for an unparseable body from an unauthenticated caller, revealing
    whether their JSON parsed.
    """
    application = create_app()
    application.config.update(
        TESTING=True,
        DEBUG=True,
        APP_TOKEN=None,
        RATELIMIT_ENABLED=False,
        ALLOW_RUNTIME_SETTINGS=False,
        RUNTIME_SETTINGS_ENV_PATH=str(tmp_path / ".env"),
    )
    response = application.test_client().post("/api/settings", json={"bogus": 1})
    assert response.status_code == 403
    assert response.get_json()["error"] == "runtime_settings_disabled"


# ---------------------------------------------------------------------------
# Vacuity guards
# ---------------------------------------------------------------------------


def test_the_key_extractor_can_fail():
    """A wrong-shaped SFC must not yield the real key set and pass by default."""
    # Empty object: no keys, so a `form_keys == MUTABLE_PROVIDER_KEYS` style
    # equality cannot pass on a file where the literal went missing.
    assert _form_keys("const form = ref({});") == []

    # A genuine but different literal yields exactly its own keys -- the
    # extractor is reading the source, not returning a constant.
    assert _form_keys(
        'const form = ref({\n  LLM_API_KEY: "",\n  ZEP_API_KEY: "",\n});'
    ) == ["LLM_API_KEY", "ZEP_API_KEY"]

    # And the real file must not look like either of those.
    assert len(_form_keys(_modal_source())) >= 8


def test_this_module_can_actually_fail():
    """`extra="forbid"` must reject an unknown key on this route specifically.

    Guards the two behavioural tests above: if the schema were ever loosened, or
    the route stopped being typed, they would pass while asserting nothing.
    """
    assert ProviderSettingsUpdateRequest.model_config.get("extra") == "forbid"

    application = create_app()
    application.config.update(
        TESTING=True,
        DEBUG=True,
        APP_TOKEN=None,
        RATELIMIT_ENABLED=False,
        ALLOW_RUNTIME_SETTINGS=True,
        RUNTIME_SETTINGS_ENV_PATH=str(Path(os.environ.get("TMP", "/tmp")) / ".env"),
    )
    response = application.test_client().post("/api/settings", json={"not_a_setting": "x"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "settings_request_invalid"
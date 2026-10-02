"""
Typed request schemas for the entity and settings route modules (exec-plan T26,
slice 2). Separate from `schemas.py` because another writer owns that file.

Scope is SHAPE only. What stays with `settings.py`:

* the `ALLOW_RUNTIME_SETTINGS` feature gate and its 403,
* `_clean_value`: control characters, per-key maximum lengths, the
  string-only requirement for keys the caller omitted,
* `_validate_base_url`: operator allowlist, HTTPS, DNS resolution, private and
  reserved address rejection,
* the "no settings were provided" and "a new API key is required" rules,
* the ZEP-versus-LLM branch selection and every provider call.

`strict=True` matters because every field here is compared against, or written
to, something an operator trusts. Without it Pydantic coerces `target: 1` to
`"1"` and `LLM_API_KEY: 5` to `"5"`; a coerced credential is still a credential,
and a coerced branch selector silently picks a provider the caller did not name.

`entity_routes` gets no model and that is a finding, not an omission. All three
of its routes are GET, they read only path parameters plus the scalar query
strings `entity_types` and `enrich`, and none of them calls `request.get_json`.
A JSON-body schema on a GET route cannot fire: `enforce_schema` reads the body,
there is none, and the route's scalar query handling would be unaffected while
its error envelope gained nothing. `GET /api/simulation/entities/...` answering
404 from an unimported module (see `routes/__init__.py`) is a registration
bug, not a typing gap; the coverage for it is in
`tests/test_entity_settings_typed_boundary.py`.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

SETTINGS_REQUEST_INVALID = "settings_request_invalid"

# Wire names are fixed by `_SECRET_KEYS`, `_TEXT_KEYS`, `_URL_KEYS` in
# `api/settings.py`, which is what the handler's allowlist loop iterates. If
# `ProviderSettingsUpdateRequest` and that loop ever disagree about which keys
# are mutable, one of them silently stops validating or persisting something, so
# the test module asserts this tuple against `_ALL_MUTABLE_KEYS`.
MUTABLE_PROVIDER_KEYS = (
    "LLM_API_KEY",
    "ZEP_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "LLM_BOOST_API_KEY",
    "LLM_MODEL_NAME",
    "LLM_BOOST_MODEL_NAME",
    "LLM_BASE_URL",
    "LLM_BOOST_BASE_URL",
)


class ProviderSettingsUpdateRequest(BaseModel):
    """Shape of `POST /api/settings`. Every field is optional.

    Optional rather than required so the handler keeps ownership of "nothing
    was provided": an empty object must still reach it and answer
    "No settings were provided" rather than being swallowed here.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    LLM_API_KEY: Optional[str] = None
    ZEP_API_KEY: Optional[str] = None
    BRAVE_SEARCH_API_KEY: Optional[str] = None
    LLM_BOOST_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: Optional[str] = None
    LLM_BOOST_MODEL_NAME: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_BOOST_BASE_URL: Optional[str] = None


class ProviderConnectionTestRequest(BaseModel):
    """Shape of `POST /api/settings/test`.

    `target` is a branch selector, not a free-form string: the handler reads it
    with `data.get("target", "llm")` and compares it to `"zep"`. An absent field
    keeps that default, so it stays optional and the handler keeps reading the
    raw body.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    target: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    ZEP_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_MODEL_NAME: Optional[str] = None
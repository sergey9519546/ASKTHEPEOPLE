"""Every /api path the frontend calls must resolve to a registered route.

This is the gap that let the entity endpoints ship broken: `entity_routes.py`
existed but was never imported in `routes/__init__.py`, so
`GET /api/simulation/entities/<graph_id>` answered 404 while the suite stayed
green — the tests asserted handler behaviour, and nothing asserted the URL the
client actually requests is mounted.

The path list is read out of `frontend/src` rather than hardcoded, so adding a
call in the Vue app extends this check automatically instead of silently
falling outside it.
"""

import re
from pathlib import Path

import pytest
from werkzeug.exceptions import MethodNotAllowed, NotFound

from app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

# '/api/...' or `...${expr}/api/...` in single, double or template quotes.
_API_PATH = re.compile(r"""['"`](/api/[^'"`\s]*)['"`]""")

# Werkzeug's default converter matches one segment and rejects '/', so a
# template hole becomes one concrete segment.
_TEMPLATE_HOLE = re.compile(r"\$\{[^}]*\}")

_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")

# create_app registers `/api/<path:path>` -> api_not_found so that a misspelled
# API URL returns JSON 404 instead of the SPA shell. It matches *everything*
# under /api, so a naive "does this path match a rule" check can never fail.
# Matching this endpoint is the definition of unmounted, not of mounted.
_CATCH_ALL_ENDPOINT = "api_not_found"


def _resolves_to_a_real_route(adapter, path: str) -> bool:
    """True only when `path` matches a rule other than the /api catch-all.

    Asking werkzeug which methods it accepts first, rather than probing verbs
    blindly: a blind probe raises MethodNotAllowed for the catch-all (which is
    GET-only) and that exception carries no rule, so there is no way to tell a
    real POST endpoint from the catch-all rejecting POST.
    """
    try:
        methods = adapter.allowed_methods(path)
    except NotFound:
        return False

    for method in methods:
        if method in ("HEAD", "OPTIONS"):
            continue
        try:
            rule, _ = adapter.match(path, method=method, return_rule=True)
        except (NotFound, MethodNotAllowed):
            continue
        if rule.endpoint != _CATCH_ALL_ENDPOINT:
            return True
    return False


def _frontend_api_paths() -> set[str]:
    """Collect every literal /api path referenced by application source."""
    paths: set[str] = set()
    for source in FRONTEND_SRC.rglob("*"):
        if source.suffix not in {".js", ".ts", ".vue"}:
            continue
        # Spec files deliberately reference ids that do not exist; they still
        # exercise real routes, but excluding them keeps this about app code.
        if "__tests__" in source.parts:
            continue
        for match in _API_PATH.findall(source.read_text(encoding="utf-8", errors="ignore")):
            paths.add(match)
    return paths


@pytest.mark.skipif(not FRONTEND_SRC.is_dir(), reason="frontend/src not present")
def test_every_frontend_api_path_is_mounted():
    app = create_app()
    adapter = app.url_map.bind("localhost")

    unmounted = []
    for raw in sorted(_frontend_api_paths()):
        candidate = _TEMPLATE_HOLE.sub("sample-id", raw)
        # A trailing template hole can also collapse to nothing meaningful;
        # skip anything that still is not a concrete path.
        if "${" in candidate or "*" in candidate:
            continue

        if not _resolves_to_a_real_route(adapter, candidate):
            unmounted.append(raw)

    assert not unmounted, (
        "frontend calls these paths but no route is registered for them: "
        + ", ".join(unmounted)
    )


@pytest.mark.skipif(not FRONTEND_SRC.is_dir(), reason="frontend/src not present")
def test_the_check_can_actually_fail():
    """Guard against the vacuous version of this test.

    Every path under /api matches the catch-all rule, so a check that only asks
    "did this match any rule" passes for a URL that does not exist. If this
    assertion ever breaks, the contract test above is no longer proving
    anything.
    """
    app = create_app()
    adapter = app.url_map.bind("localhost")

    assert _resolves_to_a_real_route(adapter, "/api/simulation/list")
    assert not _resolves_to_a_real_route(adapter, "/api/definitely/not/mounted")


@pytest.mark.skipif(not FRONTEND_SRC.is_dir(), reason="frontend/src not present")
def test_the_harvester_actually_finds_paths():
    """Guard against the check silently passing because it collected nothing."""
    paths = _frontend_api_paths()
    assert len(paths) > 20, f"expected the frontend to call many endpoints, found {paths}"

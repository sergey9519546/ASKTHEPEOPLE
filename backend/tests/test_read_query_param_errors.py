"""Query-parameter validation on the read routes (found during exec-plan T26).

`read_routes.py` guarded `limit`/`offset` on `/posts` and `/comments` but not on
the opinions handler, which serves both `/opinions` and `/generated-interactions`:

    limit = int(request.args.get('limit', 1000))

A non-numeric value raised `ValueError`, was caught by the handler's blanket
`except Exception`, and was answered with `error_response(str(e), status=500)`.
Two defects in one response:

1. **Wrong status class.** Client input error reported as a server fault.
2. **Exception text disclosed.** The body carried
   `"invalid literal for int() with base 10: 'abc'"`. `AGENTS.md` §7 scrubs
   *tracebacks* on 5xx via `strip_traceback_in_production`, but that hook does
   not inspect JSON body text, so a `str(e)` in `error` passes through
   untouched.

The same input on the sibling routes already answered
`422 invalid_limit_or_offset`, so this was a live inconsistency as well as a
leak.

These tests pin the corrected behaviour at the HTTP surface, including the
absence of the exception text -- a status-code assertion alone would pass while
the disclosure remained.
"""

import pytest

from app import create_app

OPINION_ROUTES = [
    "/api/simulation/sim-x/opinions",
    "/api/simulation/sim-x/generated-interactions",
]

BAD_SCALARS = ["abc", "", "1.5", "0x10", "null", " ", "1e3", "--1"]

EXCEPTION_FRAGMENTS = [
    "invalid literal",
    "int()",
    "base 10",
    "Traceback",
    "ValueError",
    "TypeError",
]


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.mark.parametrize("path", OPINION_ROUTES)
@pytest.mark.parametrize("value", BAD_SCALARS)
def test_non_numeric_limit_is_a_client_error_not_a_server_fault(client, path, value):
    """A malformed `limit` is a 4xx. It must never be a 5xx."""
    response = client.get(f"{path}?limit={value}")
    assert response.status_code != 500, (
        f"{path}?limit={value!r} answered 500; client input error is reported "
        "as a server fault"
    )
    assert response.status_code == 422, (
        f"{path}?limit={value!r} answered {response.status_code}; expected 422 "
        "to match /posts and /comments"
    )


@pytest.mark.parametrize("path", OPINION_ROUTES)
@pytest.mark.parametrize("value", BAD_SCALARS)
def test_exception_text_is_not_disclosed(client, path, value):
    """No Python exception detail may appear in the response body.

    The status-code test above would pass with the disclosure still present, so
    this is asserted separately.
    """
    response = client.get(f"{path}?limit={value}")
    body = response.get_data(as_text=True)
    for fragment in EXCEPTION_FRAGMENTS:
        assert fragment not in body, (
            f"{path}?limit={value!r} leaked {fragment!r} to the client: {body[:200]}"
        )


@pytest.mark.parametrize("path", OPINION_ROUTES)
def test_error_envelope_is_the_app_shape(client, path):
    """Failures keep the `{success, error}` envelope with a stable code."""
    response = client.get(f"{path}?limit=abc")
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == "invalid_limit_or_offset"


@pytest.mark.parametrize("path", OPINION_ROUTES)
def test_negative_limit_is_rejected(client, path):
    """A negative limit is out of range, not silently treated as a tail slice."""
    response = client.get(f"{path}?limit=-1")
    assert response.status_code == 422
    assert response.get_json()["error"] == "limit_out_of_range"


@pytest.mark.parametrize("path", OPINION_ROUTES)
@pytest.mark.parametrize("value", ["0", "1", "1000"])
def test_valid_limits_are_not_rejected(client, path, value):
    """The guard must not reject limits the route previously accepted."""
    response = client.get(f"{path}?limit={value}")
    assert response.status_code != 422, f"{path}?limit={value} was wrongly rejected"


@pytest.mark.parametrize("path", OPINION_ROUTES)
def test_absent_limit_still_uses_the_default(client, path):
    """No `limit` at all must behave as before, using the documented default."""
    response = client.get(path)
    assert response.status_code in (200, 404), (
        f"{path} with no limit answered {response.status_code}; the default path "
        "must be unchanged"
    )


def test_sibling_routes_keep_their_existing_contract(client):
    """/posts and /comments already answered 422; the fix must not move them."""
    for path in ("/api/simulation/sim-x/posts", "/api/simulation/sim-x/comments"):
        response = client.get(f"{path}?limit=abc")
        assert response.status_code == 422
        assert response.get_json()["error"] == "invalid_limit_or_offset"

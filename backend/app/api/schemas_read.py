"""Request-shape record for `api/routes/read_routes.py` (exec-plan T26).

This module deliberately holds **no Pydantic models**, and adding one here
without new evidence would be inventing a boundary. Measured against the real
app on 2026-10-02, `read_routes.py` registers 19 rules, every one of them `GET`,
and not one handler reads a JSON request body. A body schema would have nothing
to validate: `POST`, `PUT`, `PATCH`, and `DELETE` to any of the 19 paths answer
`405 method_not_allowed` before a handler runs, and both `enforce_schema` and
`validate_schema` parse only `request.get_json`.

So what is recorded here is the shape that actually exists -- scalar query
parameters validated inside the handlers -- and the error codes those handlers
already return. Two jobs:

1. `READ_ROUTE_QUERY_PARAMS` is the inventory a change must update when it adds
   or removes a read parameter. Keyed by view function, because three handlers
   serve two URLs each. `tests/test_read_typed_boundary.py` checks it against the
   live `url_map`, so a route that is silently unregistered cannot pass.
2. `QUERY_SHAPE_ERRORS` is the contract any future typing must preserve. The
   database-backed readers answer `invalid_platform`, `invalid_limit_or_offset`,
   and `limit_out_of_range` at 422; `/compare` answers 400. Substituting
   RFC-7807 Problem Details -- which is what `validate_schema` does -- would be a
   breaking API change wearing the costume of a refactor.

Two scalar parameters are **not** shape-checked today. They are recorded rather
than fixed because both answers are wire-visible and changing either is an API
change outside this slice:

* `/history?limit=abc`, `/actions?limit=abc`, and `/timeline?start_round=abc` go
  through `request.args.get(..., type=int)`, which yields the default when the
  value will not parse. A typo silently becomes the default instead of an error.
* `/opinions?limit=abc`, and the same handler's `/generated-interactions` alias,
  call `int()` directly, so a malformed value raises and is answered 500 with the
  raw exception text in `error`. `/posts` and `/comments` answer that identical
  input 422.

`tests/test_read_typed_boundary.py` marks both behaviours `xfail(strict=False)`:
the intent is recorded, and correcting either turns an xfail into a pass rather
than breaking the build.
"""

from __future__ import annotations

from typing import Optional, Tuple

READ_ROUTE_MODULE = "app.api.routes.read_routes"

BODY_METHODS: Tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")

READ_ROUTE_QUERY_PARAMS: dict[str, Tuple[str, ...]] = {
    "get_simulation": (),
    "list_simulations": ("project_id",),
    "get_simulation_history": ("limit",),
    "get_simulation_profiles": ("platform",),
    "get_simulation_profiles_realtime": ("platform",),
    "get_simulation_config_realtime": (),
    "get_simulation_config": (),
    "search_simulation_observations": ("q", "platform", "agent_id", "limit"),
    "get_simulation_metrics": ("force",),
    "compare_simulations_route": ("sim_a", "sim_b", "force"),
    "get_run_status_detail": ("platform",),
    "get_simulation_actions": (
        "limit",
        "offset",
        "platform",
        "agent_id",
        "round_num",
        "include_followers",
    ),
    "get_simulation_timeline": ("start_round", "end_round"),
    "get_agent_stats": (),
    "get_simulation_posts": ("platform", "limit", "offset"),
    "get_simulation_comments": ("post_id", "limit", "offset"),
    "get_simulation_opinions": ("limit",),
}

QUERY_SHAPE_ERRORS: dict[str, Tuple[Tuple[int, Optional[str]], ...]] = {
    "get_simulation_posts": (
        (422, "invalid_platform"),
        (422, "invalid_limit_or_offset"),
        (422, "limit_out_of_range"),
    ),
    "get_simulation_comments": (
        (422, "invalid_limit_or_offset"),
        (422, "limit_out_of_range"),
    ),
    # None: /compare answers a prose sentence in `error`, not a code.
    "compare_simulations_route": ((400, None),),
}

# Routes that used to substitute the default for a malformed scalar. All three
# now answer 422 invalid_limit_or_offset via read_routes.int_query_arg, matching
# /posts and /comments. Kept as data so test_read_typed_boundary.py can assert
# the behaviour at the HTTP surface.
SILENT_DEFAULT_ON_BAD_SCALAR: Tuple[Tuple[str, str], ...] = (
    ("/api/simulation/history", "limit"),
    ("/api/simulation/sim_x/actions", "limit"),
    ("/api/simulation/sim_x/timeline", "start_round"),
)

# Routes that used to answer 500 with the Python exception text in `error`.
# strip_traceback_in_production scrubs tracebacks but never inspects JSON body
# text, so error_response(str(e), ...) leaked. Now guarded, answering 422.
RAISES_ON_BAD_SCALAR: Tuple[Tuple[str, str], ...] = (
    ("/api/simulation/sim_x/opinions", "limit"),
    ("/api/simulation/sim_x/generated-interactions", "limit"),
)
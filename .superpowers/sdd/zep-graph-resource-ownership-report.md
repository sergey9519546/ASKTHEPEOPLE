# Graph resource ownership hardening report

## State legend

- **CURRENT** — implemented and verified in this working tree.
- **PARTIAL** — locally implemented but not release-complete.
- **TARGET** — required durable production behavior.
- **TRANSITION** — remaining work to reach the target.

## Outcome

- **CURRENT:** `GET /api/graph/data/<graph_id>` requires `project_id`, resolves
  it through `ProjectManager`, and reaches ZEP only when the canonical project
  is `graph_completed` and its `graph_id` exactly matches the requested ID.
- **CURRENT:** missing project authority, missing projects, mismatched graph
  associations, dependency failures, and provider read failures use stable
  error codes. Provider exception text and tracebacks are not returned.
- **CURRENT:** `DELETE /api/graph/delete/<graph_id>` applies the same ownership
  check, then returns `503 graph_delete_unavailable` without constructing a ZEP
  client or mutating either store.
- **TARGET:** destructive graph operations need a durable, owner-fenced delete
  state machine with reconciliation for ambiguous provider outcomes before the
  endpoint can be enabled.
- **PARTIAL:** frontend graph readers still use only `graph_id`; their request
  contract must add the canonical `project_id` before this change can ship.

## TDD evidence

The focused tests were written and run before the route implementation.

- **RED:** `pytest tests/test_graph_resource_ownership.py -q` collected six
  tests and produced the expected security failures: five failed and one
  pre-existing positive-path behavior passed. The failures showed that the old
  routes reached the provider without project authority, deleted directly, and
  returned raw provider failure details.
- **GREEN:** the same command passed `6/6` after the minimal route change.
- **Integration:** the ownership, claim-boundary, and graph-worker matrix passed
  `106/106` using a sandbox-writable `--basetemp` directory.
- **Static check:** Ruff's fatal-error selection passed for the graph route,
  focused ownership tests, and affected claim-boundary test. The new ownership
  test also passed the full Ruff rule set and was Ruff-formatted.

No provider or other network operation was made. Tests used local Flask clients
and provider test doubles only.

## Transition requirements

1. Pass canonical `project_id` from every frontend graph-data caller.
2. Add a first-class graph-deletion operation with an operation owner, durable
   pending/terminal states, compare-and-set transitions, retry classification,
   and reconciliation of ambiguous provider outcomes.
3. Keep provider deletion disabled until those transitions exist in both the
   filesystem transition store and canonical repository.

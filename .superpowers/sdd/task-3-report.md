# Task 3 report — Server-owned workspace manifest

## Status

`COMPLETE_WITH_TEST_RUNNER_CLEANUP_CONCERN`

All required Task 3 behaviors are implemented and verified. The focused suite
passes all 16 tests when pytest uses a workspace-local base temp directory. The
exact focused command also executed all 16 tests as passes, but pytest then
exited nonzero while attempting to clean an inaccessible pre-existing Windows
temp symlink; details are under Concerns.

## Files changed

- `backend/app/application/__init__.py`
- `backend/app/application/decision_workspace_service.py`
- `backend/app/api/routes/workspace_routes.py`
- `backend/app/api/routes/__init__.py`
- `backend/tests/test_decision_workspace_api.py`
- `.superpowers/sdd/task-3-report.md`

No code was added to or changed in `backend/app/api/simulation.py`. No database
migration, dependency, thread, subprocess, LLM call, or unrelated worktree
change was introduced.

## RED and GREEN evidence

Commands below ran from `backend/` unless otherwise stated. Tests using
`tmp_path` include `--basetemp=.pytest-tmp-task3` because the environment's
default pytest temp root is not accessible.

1. Route registration (required behavior 10)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_workspace_route_is_registered -q`
   - Result: `1 failed`; the expected workspace URL was absent from the Flask
     URL map.
   - GREEN: the same command.
   - Result: `1 passed` after adding `workspace_routes.py` and importing it from
     `api/routes/__init__.py`.

2. Stable missing-project response (required behavior 1)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_missing_project_returns_stable_not_found -q --basetemp=.pytest-tmp-task3`
   - Result: `1 failed`; the placeholder route returned HTTP 501 instead of
     HTTP 404.
   - GREEN: the same command.
   - Result: `1 passed`; the route returned exactly
     `{"success": false, "error": "project_not_found"}`.

3. Atomic, stable server identity (required behavior 2)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_service_atomically_persists_and_reuses_server_workspace_id -q --basetemp=.pytest-tmp-task3`
   - Result: `1 failed` with the intentional `NotImplementedError` before
     identity persistence existed.
   - GREEN: the same command.
   - Result: `1 passed`; the test verifies the workspace-ID regex, one call to
     `ProjectManager._atomic_write_text`, the exact identity-only JSON, and
     reuse of the same ID on a second resolution.

4. No client-owned workspace or decision identity (required behaviors 3 and 8)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_endpoint_does_not_accept_or_override_workspace_or_decision_identity -q --basetemp=.pytest-tmp-task3`
   - Result: `1 failed`; GET still returned HTTP 501 before successful typed
     presentation existed.
   - GREEN: the same command.
   - Result: `1 passed`; a GET body cannot override the service-issued
     workspace ID, `decision_id` is null, and POST returns 405. The response
     model fixes `decision_identity_status` to `UNAVAILABLE`.

5. Stored identity conflicts fail closed (required behavior 4)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_invalid_stored_manifest_returns_conflict_without_overwrite -q --basetemp=.pytest-tmp-task3`
   - Result: `4 failed`; invalid JSON, an extra field, and a bad workspace ID
     escaped as validation errors, while a project mismatch returned 200.
   - GREEN: the same command.
   - Result: `4 passed`; every case returns the stable 409 body and the stored
     bytes remain unchanged.

6. Deterministic relationships (required behavior 5)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_relationships_are_filtered_sorted_and_never_collapsed -q --basetemp=.pytest-tmp-task3`
   - Result: `1 failed` because the typed manifest had no relationship fields.
   - GREEN: the same command.
   - Result: `1 passed`; multiple simulations and related reports are sorted,
     and the unrelated report is excluded.

7. Capability availability matrix (required behavior 6)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_capability_availability_follows_record_presence -q --basetemp=.pytest-tmp-task3`
   - Result: `4 failed` because the typed manifest had no availability model.
   - GREEN: the same command.
   - Result: `4 passed`; source, run, and brief presence rules and all three
     fixed `UNAVAILABLE` future capabilities match the brief.

8. Complete synthetic truth (required behavior 7)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_manifest_contains_complete_synthetic_truth_bundle -q --basetemp=.pytest-tmp-task3`
   - Result: `1 failed` because the manifest had no truth field.
   - GREEN: the same command.
   - Result: `1 passed`; all seven `TruthBundle.synthetic()` values match
     exactly.

9. Stable, non-leaking unexpected failure (required behavior 9)
   - RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_unexpected_service_failure_returns_stable_non_leaking_error -q --basetemp=.pytest-tmp-task3`
   - Result: `1 failed`; the private service exception escaped.
   - GREEN: the same command.
   - Result: `1 passed`; the response is the exact stable 500 JSON without
     exception text or traceback.
   - Self-review RED: `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py::test_unexpected_presentation_failure_uses_same_stable_500 -q --basetemp=.pytest-tmp-task3`
   - Result: `1 failed`; serialization errors occurred after the route's try
     block.
   - Self-review GREEN: the same command.
   - Result: `1 passed` after moving typed presentation inside the protected
     route boundary.

## Final verification

- Focused suite:
  `.\.venv\Scripts\pytest tests/test_decision_workspace_api.py -q --basetemp=.pytest-tmp-task3`
  - Result: `16 passed in 1.55s`.
- Contract regressions (the exact command from the brief):
  `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py tests/test_api_schemas.py -q`
  - Result: `1379 passed in 2.37s`.
- Documentation baseline, run from the repository root:
  `python tools/validate_docs.py`
  - Result: `PASS`, 0 warnings, 0 errors.

## Self-review

- `StoredWorkspaceIdentity`, `DecisionWorkspaceManifest`, and the nested
  capability response model are frozen, strict Pydantic v2 models that forbid
  extra fields.
- Workspace IDs use exactly `^workspace_[0-9a-f]{32}$`; project, simulation,
  and report IDs use the same 1–128 character server-ID pattern as
  `app.domain.decision_workspace`.
- Only the four identity metadata keys are persisted. Relationship,
  availability, decision, and truth data are derived for each response.
- `ProjectManager.get_project`, `SimulationManager.list_simulations` with the
  project filter, `ReportManager.list_reports(limit=1000)`, and
  `ProjectManager.get_project_files` are the only record-resolution APIs used.
- Simulation and report IDs are emitted as deterministic JSON arrays without
  selecting a canonical record. Report filtering uses only related simulation
  IDs.
- `decision_id` cannot be supplied or derived and remains null.
- Error responses contain only stable codes. Both service and presentation
  failures are covered by the non-leaking 500 boundary.
- `git diff --check` passes for the Task 3 code/test files.
- Unrelated dirty work was preserved and excluded from Task 3 staging.

## Commit

Task 3 deliverables are intended for one isolated commit. The resulting SHA is
reported in the agent handoff because a commit cannot contain its own final
SHA without changing that SHA.

## Concerns

- Running the exact focused command without `--basetemp` executes all 16 tests
  as passes, then pytest exits with `PermissionError: [WinError 5]` while
  cleaning
  `C:\Users\serge\AppData\Local\Temp\pytest-of-serge\pytest-current`.
  The workspace-local base-temp run is clean and verifies every focused
  behavior; this is a host temp-directory cleanup issue, not a test failure.
- The shared worktree contains substantial unrelated pre-existing and
  concurrent changes. They remain untouched and will not be staged.

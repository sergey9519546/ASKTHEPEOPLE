# Task 2 report — Typed product-truth and provenance contracts

## Status

`DONE_WITH_CONCERNS`

The four requested domain/test files and all review fixes are complete. The
final focused domain and API-schema verification collected 1,379 tests and
passed all 1,379. The separate pre-existing provenance-route regression hangs
at `test_start_route_defaults_to_observation_store_without_graph_write`; that
hang is localized outside the Task 2 domain module.

Deliverable commits:

- `27254e9` (`feat: add typed decision workspace truth contracts`)
- `edd24b5` (`fix: enforce decision workspace provenance allowlist`)

## Files changed

- `backend/app/domain/__init__.py`
- `backend/app/domain/decision_workspace.py`
- `backend/tests/domain/__init__.py`
- `backend/tests/domain/test_decision_workspace.py`
- `.superpowers/sdd/task-2-report.md` (this required report)

No route, persistence, dependency, or unrelated dirty-work file was modified.

## RED and GREEN evidence

All commands below ran from `backend/`.

1. Locked synthetic truth serialization
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_synthetic_truth_bundle_serializes_to_locked_values -q`
     - Result: `1 failed`; expected `ModuleNotFoundError: No module named 'app.domain'` because the new domain contract did not yet exist.
   - GREEN: same command.
     - Result: `1 passed`.

2. Locked truth values reject overrides
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_truth_bundle_rejects_overrides_of_locked_values -q`
     - Result: `7 failed`; every case reported `DID NOT RAISE ValidationError` while the fields were minimally typed.
   - GREEN: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q`
     - Result at this cycle: `8 passed` after changing all seven fields to their required `Literal` types.

3. Allowed source-segment support edge
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_source_segment_may_support_starting_condition -q`
     - Result: `1 failed`; expected import failure because the provenance types did not yet exist.
   - GREEN: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q`
     - Result at this cycle: `9 passed`.

4. Direct source-to-path support is forbidden
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_source_segment_may_not_support_possible_path -q`
     - Result: `1 failed`; expected import failure because `ProvenanceViolation` did not yet exist.
   - GREEN: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q`
     - Result at this cycle: `10 passed`; stable message matched `source_to_path_forbidden`.

5. Arbitrary unlisted edge is forbidden
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_arbitrary_unlisted_provenance_edge_is_forbidden -q`
     - Result: `1 failed`; the temporary fallback raised `NotImplementedError` rather than the contract exception.
   - GREEN: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q`
     - Result at this cycle: `11 passed`; the closed ten-triple allowlist and stable `provenance_edge_forbidden` fallback were active.

6. Possible-path contract
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_possible_path_includes_ordered_synthetic_steps_and_truth -q`
     - Result: `1 failed`; expected import failure because path types did not yet exist.
   - GREEN: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q`
     - Result at this cycle: `12 passed`; a valid path carried its step tuple and complete default truth bundle.
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_possible_path_rejects_invalid_stable_ids -q`
     - Result: `6 failed`; empty and 129-character path/run/step IDs were initially accepted.
   - GREEN: focused file result at this cycle: `18 passed` after applying the required 1–128 character bounds.
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_possible_path_rejects_labels_outside_p_number_format -q`
     - Result: `3 failed`; malformed labels were initially accepted.
   - GREEN: focused file result at this cycle: `21 passed` after enforcing `^P-\d{2}$`.
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_possible_path_requires_at_least_one_step -q`
     - Result: `1 failed`; an empty tuple was initially accepted.
   - GREEN: focused file result at this cycle: `22 passed` after setting tuple `min_length=1`.
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_path_step_sequence_starts_at_one -q`
     - Result: `1 failed`; sequence zero was initially accepted.
   - GREEN: focused file result at this cycle: `23 passed` after setting `ge=1`.
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_possible_paths_and_steps_require_synthetic_origin -q`
     - Result: `2 failed`; `USER_STATED` was initially accepted for a step and path.
   - GREEN: focused file result at this cycle: `25 passed` after using the required synthetic-origin `Literal` on both models.
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_possible_path_text_fields_enforce_contract_limits -q`
     - Result: `4 failed`; empty and 1,201-character statements/reasons were initially accepted.
   - GREEN: focused file result at this cycle: `29 passed` after applying 1–1,200 character bounds.

7. Frozen models reject assignment
   - RED: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py::test_domain_models_reject_assignment -q`
     - Result: `4 failed`; assignment was accepted by each temporarily mutable model.
   - GREEN/final focused command: `.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q`
     - Result: `33 passed in 0.56s` after restoring `ConfigDict(frozen=True, extra="forbid")` on every model.

## Regression result

Command run exactly from `backend/`:

`.\.venv\Scripts\pytest tests/test_provenance_separation.py tests/test_api_schemas.py -q`

Observed result: the process remained running with no output after approximately
63 seconds. It was explicitly terminated rather than left hanging. There was
no pass/fail summary to report.

## Self-review findings

- `EpistemicOrigin`, `EpistemicRole`, and `ProvenanceRelation` exactly match the V1 members in the brief; `EXTERNAL_HUMAN_EVIDENCE` was not added.
- The provenance validator uses exactly the ten allowed triples. Direct source-segment support of a possible path has its dedicated stable error; every other unlisted triple has the generic stable error.
- All four Pydantic models are frozen and reject extra fields. Required ID, label, sequence, statement, origin, step-count, and truth constraints match the specified interfaces.
- No likelihood, score, confidence, winner, ranking, generic parent ID, persistence, route, rendering, or dependency behavior was introduced.
- `git diff --check` passed for the four deliverable files.
- The repository documentation validator passed before implementation with zero warnings and zero errors.

## Concerns

- `tests/test_provenance_separation.py` remains unverified as a whole because
  its fourth test hangs in the existing start-route behavior. The new domain
  contracts are not imported by that route, and this was reviewed as an
  unrelated concern rather than a Task 2 code defect.
- The shared worktree contains substantial unrelated pre-existing changes; they were preserved and excluded from Task 2 staging/commit scope.

## Final controller verification

Command:

`\.venv\Scripts\pytest tests/domain/test_decision_workspace.py tests/test_api_schemas.py -q`

Observed result: `1379 passed in 2.42s`.

## Review-fix evidence (2026-08-08)

- RED: `backend\\.venv\\Scripts\\pytest tests\\domain\\test_decision_workspace.py::test_all_allowed_provenance_triples_pass -q`
  - Result: `1 failed, 9 passed`. The required `SOURCE_ASSET --CONTAINS--> SOURCE_SEGMENT` triple raised `provenance_edge_forbidden`; the implementation had an incorrect `DECISION --SUPPORTS--> SOURCE_ASSET` entry instead.
- GREEN: `backend\\.venv\\Scripts\\pytest tests\\domain\\test_decision_workspace.py -q`
  - Result: `1376 passed in 1.36s`. This includes all ten allowed triples and every one of the 1,286 unlisted role/relation/role triples. The direct `SOURCE_SEGMENT --SUPPORTS--> POSSIBLE_PATH` case is asserted as `source_to_path_forbidden`; all other unlisted triples are asserted as `provenance_edge_forbidden`.
- Regression: `backend\\.venv\\Scripts\\pytest tests\\test_api_schemas.py -q`
  - Result: `3 passed in 1.41s`.

The known hanging start-route provenance test was not run.

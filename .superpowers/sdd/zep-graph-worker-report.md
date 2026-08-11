# Zep graph worker repair report

Status: DONE

## RED evidence

### Final fix wave

The final safety regressions were added in
`backend/tests/test_graph_worker_final_fixes.py` before this wave's production
changes.

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_final_fixes.py -q --basetemp .pytest-zep-final-red-2
```

Observed result: **14 failed, 1 passed in 2.08s**. The failures proved that the
HTTP route still read extracted text/ontology and used `.delay()` with a client
graph label; the worker preferred mutable payload/project task identities over
the Celery request ID; stale workers were not fenced; hostile/stale 409s were
accepted; empty/malformed episode acknowledgements and empty chunks could
complete; transient polling was not retried internally; task-completion store
failure downgraded the completed project; and reconciliation logging was
missing after project completion persistence failure. The one pass was the
already-present behavior that accepted an empty 409; the hostile/stale cases
failed and demonstrated why unconditional acceptance was unsafe.

The exact marker-before-episode ordering was then tightened with a separate
RED slice:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_final_fixes.py::test_create_conflict_with_wrong_marker_never_inspects_episodes -q --basetemp .pytest-zep-marker-order-red
```

Observed result: **1 failed in 1.93s** because the implementation queried
episodes even after detecting the wrong ownership marker.

The review-fix tests were added in
`backend/tests/test_graph_worker_retry_safety.py` before the repair.

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_retry_safety.py -q --basetemp .pytest-zep-review-red
```

Observed result: **7 failed in 4.30s**. The failures proved that the service
did not accept a stable graph ID, polling errors and timeouts were swallowed,
the worker trusted the payload graph name and did not supply a server graph
ID, ambiguous episode failure was retried, and the shared retry classifier had
no clean utility module.

A second vertical slice covered task-progress persistence inside the provider
call boundary:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_retry_safety.py::test_progress_store_failure_is_not_misclassified_as_provider_retry -q --basetemp .pytest-zep-progress-red-2
```

Observed result: **1 failed in 1.22s** because a canonical progress-store
`ConnectionError` raised `celery.exceptions.Retry` as though it were a Zep
provider failure.

## GREEN evidence

### Final fix wave

Focused final-fix suite after implementation:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_final_fixes.py -q --basetemp .pytest-zep-final-green-1
```

Observed result: **15 passed in 1.76s**. The marker-order slice then passed
independently: **1 passed in 1.68s**.

Final bounded graph/retry/route regression run:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_final_fixes.py tests\test_graph_worker_retry_safety.py tests\test_graph_worker_task.py tests\test_zep_retry_policy.py tests\test_task_retry_classification.py tests\test_runtime_regressions.py::test_graph_wait_reports_elapsed_time_without_name_error tests\test_rate_limiting.py -q --basetemp .pytest-zep-final-regressions-3
```

Observed result: **75 passed, 1 third-party warning in 15.50s**.

Touched-file Ruff passed for all final-wave Python files except
`app/api/graph.py`:

```powershell
cd backend
& 'C:\Users\serge\AppData\Roaming\Python\Python314\Scripts\ruff.exe' check app/services/graph_builder.py app/tasks/graph_tasks.py app/utils/task_retry.py tests/test_graph_worker_task.py tests/test_graph_worker_retry_safety.py tests/test_graph_worker_final_fixes.py
```

Observed result: **All checks passed**. Including `app/api/graph.py` reports
three pre-existing findings outside this route change: two unused imports and
the existing unused `additional_context` local at line 227. `git diff --check`
passed (Git emitted only the repository's existing LF/CRLF notices).

Focused review suite:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_retry_safety.py tests\test_graph_worker_task.py -q --basetemp .pytest-zep-review-focused-green
```

Observed result: **17 passed in 1.13s**. After adding the final progress-store
boundary case, its exact GREEN command was:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_retry_safety.py::test_progress_store_failure_is_not_misclassified_as_provider_retry -q --basetemp .pytest-zep-progress-green
```

Observed result: **1 passed in 0.99s**.

Relevant bounded regressions:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_retry_safety.py tests\test_graph_worker_task.py tests\test_zep_retry_policy.py tests\test_task_retry_classification.py tests\test_resource_bounds.py tests\test_runtime_regressions.py::test_graph_wait_reports_elapsed_time_without_name_error -q --basetemp .pytest-zep-review-regressions
```

Observed result: **83 passed, 1 third-party warning in 15.27s**.

Touched-file Ruff:

```powershell
cd backend
& 'C:\Users\serge\AppData\Roaming\Python\Python314\Scripts\ruff.exe' check app/services/graph_builder.py app/tasks/graph_tasks.py app/tasks/simulation_tasks.py app/utils/task_retry.py app/utils/zep_paging.py tests/test_graph_worker_task.py tests/test_graph_worker_retry_safety.py
```

Observed result: **All checks passed**.

## Touched files

Final fix wave:

- `backend/app/api/graph.py`
- `backend/app/services/graph_builder.py`
- `backend/app/tasks/graph_tasks.py`
- `backend/app/utils/task_retry.py`
- `backend/tests/test_graph_worker_task.py`
- `backend/tests/test_graph_worker_retry_safety.py`
- `backend/tests/test_graph_worker_final_fixes.py` (new)
- `.superpowers/sdd/zep-graph-worker-report.md`

Earlier repair-wave files retained below:

- `backend/app/services/graph_builder.py`
- `backend/app/tasks/graph_tasks.py`
- `backend/app/tasks/simulation_tasks.py`
- `backend/app/utils/task_retry.py`
- `backend/app/utils/zep_paging.py`
- `backend/tests/test_graph_worker_task.py`
- `backend/tests/test_graph_worker_retry_safety.py`
- `.superpowers/sdd/zep-graph-worker-report.md`

## Design decisions

- The HTTP build route now persists the server task ID and calls
  `apply_async(kwargs={"project_id": ...}, task_id=task_id)`. It neither reads
  canonical graph inputs nor accepts/forwards `graph_name`.
- The worker treats `self.request.id` as authoritative; `task_id` remains only
  for direct unit-test calls. A project pointing to a different task fences the
  stale worker with `graph_build_superseded` and leaves the newer project state
  untouched.
- A graph-create 409 is reusable only when the fetched graph description
  exactly equals the SHA-256-derived ownership marker and
  `episode.get_by_graph_id(graph_id=..., lastn=1)` returns an empty sequence.
  Marker mismatch, malformed verification, or any episode is terminal.
- Every `add_batch` response must be a non-empty sequence and every returned
  episode must carry a non-empty UUID. Empty chunks and unconfirmed submission
  terminate with `graph_episode_submission_unconfirmed`.
- Episode status polling uses the shared bounded transient-retry helper. The
  task does not replay after episode submission, so neither recovery nor
  exhaustion can resubmit a batch.
- Project completion and task-envelope completion are deliberately asymmetric:
  if the project save succeeds and task completion fails, the completed project
  and graph identity are preserved and the worker raises
  `graph_task_completion_persistence_failed`. If the project save fails, the
  client-visible graph ID is cleared, FAILED is attempted, and the deterministic
  reconciliation graph ID is logged without provider/source text.

- The worker derives one server-owned graph ID from the canonical graph-build
  task identity. Celery retries reuse it; a provider 409 on create is treated
  as idempotent completion of that same create operation.
- Create and ontology failures carry `retry_safe=True`. Episode submission,
  processing wait, and graph-info failures carry `retry_safe=False`, because
  replaying the whole build could duplicate non-idempotent episode ingestion.
- Poll errors raise `graph_processing_failed`; bounded wait expiration raises
  `graph_processing_timeout`.
- The graph label comes only from `project.name`, with `Source graph` as the
  empty/non-string fallback. Payload `graph_name` and graph IDs are ignored.
- Retry classification lives in `app/utils/task_retry.py`. The graph worker
  applies it only to exceptions from the provider-build call and separately
  tags progress persistence failures so canonical/task-store outages never
  enter the provider retry path.
- Terminal failure clears `project.graph_id` before saving `FAILED`. The
  sanitized operator log may retain the incomplete derived ID for
  reconciliation, but it is not exposed in the project record.
- The unused `build_graph_async` daemon-thread worker and its raw exception log
  were deleted. No live Zep request or local credential was used.

## Remaining concerns

- This bounded repair does not add a provider deletion/reconciliation
  workflow. An incomplete derived graph can still require operator cleanup;
  the stable ID makes that cleanup identifiable without exposing source text
  or provider response bodies.

## CAS review-fix slice

Status: DONE

### New RED evidence

The review regressions were added first in
`backend/tests/test_graph_worker_cas_review.py`.

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py -q --basetemp .pytest-zep-cas-review-red-2
```

Observed result: **8 failed in 2.26s**. The failures showed partial episode
acknowledgements could be accepted, no legacy/canonical conditional completion
method existed, an old worker could publish after mid-build supersession,
broker dispatch failure returned a raw 500 and left state stale, 409
verification reads did not retry, and task-envelope completion failure left
the task record in processing.

The installed SDK's `EpisodeResponse.episodes` shape then received its own
test-first cycle:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_create_conflict_accepts_only_an_empty_sdk_episode_response -q --basetemp .pytest-zep-sdk-shape-red
```

Observed result: **1 failed in 2.36s** because the safe empty response was
treated as a malformed non-sequence.

Finally, the PascalCase ontology canary ran RED before the normalizer change:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_ontology_type_names_preserve_existing_pascal_case -q --basetemp .pytest-zep-pascal-red
```

Observed result: **4 failed in 2.06s** because no preserving normalizer existed
at module scope (the nested implementation used `str.capitalize()` and would
have changed `CanaryPerson` to `Canaryperson`).

### New GREEN evidence

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py -q --basetemp .pytest-zep-cas-review-final
```

Observed result: **16 passed in 2.17s**.

Final relevant graph/retry/route regression run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py tests\test_graph_worker_final_fixes.py tests\test_graph_worker_retry_safety.py tests\test_graph_worker_task.py tests\test_zep_retry_policy.py tests\test_task_retry_classification.py tests\test_resource_bounds.py tests\test_runtime_regressions.py::test_graph_wait_reports_elapsed_time_without_name_error -q --basetemp .pytest-zep-cas-final-regressions
```

Observed result: **118 passed in 11.07s**, with one existing third-party
`huggingface_hub` deprecation warning.

Touched-file Ruff passed:

```powershell
& 'C:\Users\serge\AppData\Roaming\Python\Python314\Scripts\ruff.exe' check app/services/graph_builder.py app/tasks/graph_tasks.py app/models/project.py app/services/project_repository.py tests/test_graph_worker_cas_review.py
```

`git diff --check` passed for the bounded paths; Git printed only LF/CRLF
working-copy notices. `app/api/graph.py` retains the three pre-existing Ruff
findings documented above; no unrelated cleanup was made.

### CAS review design

- Every `add_batch` acknowledgement must match the submitted chunk count and
  every acknowledgement ID must parse as a UUID.
- Legacy completion uses a per-project cross-process file lock around
  read/check/atomic save. Canonical completion uses a single conditional SQL
  update matching `project_id`, `graph_build_task_id`, and `GRAPH_BUILDING`.
  The repository SQL and `rowcount` contract are explicitly tested.
- The worker claims only an unassigned task (or confirms itself) before
  provider work, and conditionally completes afterward. A task superseded
  while the provider is running cannot publish or complete.
- Dispatch failure uses a stable `graph_dispatch_failed` response, fails the
  task envelope best-effort, and conditionally restores the pre-dispatch
  project snapshot. A force-rebuild dispatch failure restores an already
  completed graph and status.
- 409 verification retries only bounded provider reads and recognizes the
  actual SDK `EpisodeResponse(episodes=[])` shape. Nonempty, `None`, or
  malformed responses remain terminal.
- If the project is already completed but `TaskManager.complete_task` fails,
  the worker preserves the project completion and best-effort fails the task
  envelope with `graph_task_completion_persistence_failed`.
- `_to_pascal_case` uppercases only the first character of normalized parts,
  preserving an already-Pascal type name while still converting snake_case.

### CAS review touched files

- `backend/app/api/graph.py`
- `backend/app/models/project.py` (bounded graph-build ownership methods only)
- `backend/app/services/project_repository.py` (bounded conditional ownership
  methods only)
- `backend/app/services/graph_builder.py`
- `backend/app/tasks/graph_tasks.py`
- `backend/tests/test_graph_worker_cas_review.py`
- `.superpowers/sdd/zep-graph-worker-report.md`

### Final route and lock hardening

Two final RED cases were added to `test_graph_worker_cas_review.py`:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_route_unexpected_setup_error_is_sanitized tests\test_graph_worker_cas_review.py::test_graph_build_lock_deadline_fails_closed_when_lock_never_acquires -q --basetemp .pytest-zep-route-lock-red
```

Observed result: **2 failed in 2.21s**. The route returned the raw exception
and traceback, and the legacy lock had no bounded acquisition helper.

GREEN:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py -q --basetemp .pytest-zep-route-lock-green
```

Observed result: **18 passed in 2.14s**. The final relevant regression command
from the CAS review then passed **120 tests in 11.77s**, with only the same
third-party deprecation warning. The route now logs only `exception_type` and
returns `graph_build_setup_failed`; the legacy file lock has a five-second
monotonic deadline and fails closed as `graph_build_lock_unavailable`.

## Final ownership, redelivery, and canonical-store review wave

Status: DONE

### RED evidence

The expanded review suite was written before this wave's production changes:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py -q --basetemp .pytest-zep-final-review-red
```

Observed result: **14 failed, 18 passed in 2.71s**. Twelve failures directly
proved the missing failure CAS, permissive completed-owner reclaim, permissive
canonical owner SQL, stale-worker terminal overwrite, duplicate-delivery
rebuild, absent canonical ontology hydration/write-through, ambiguous
completion downgrade, unguarded retry publication, and pre-ownership task
update. Two graph-info cases initially had omitted required chunk parameters;
that test-only setup was corrected before production paging changes.

The corrected graph-info slice then produced the intended clean RED:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_graph_info_paging_recovers_from_status_aware_transient_reads tests\test_graph_worker_cas_review.py::test_graph_info_paging_exhaustion_is_terminal_without_whole_build_replay -q --basetemp .pytest-zep-graph-info-red
```

Observed result: **2 failed in 2.34s**. A status-503 read failed after one call,
and exhaustion made one read rather than the required bounded three.

Canonical ontology idempotence received a separate RED cycle:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_repository_repeat_save_does_not_duplicate_unchanged_ontology -q --basetemp .pytest-zep-ontology-idempotence-red
```

Observed result: **1 failed in 2.20s** because two identical saves appended two
completed ontology rows.

Finally, an executable in-memory schema matching the migration's integer
`projects.id -> ontologies.project_id` relationship ran RED:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_canonical_worker_executes_against_integer_ontology_fk_schema -q --basetemp .pytest-zep-canonical-sql-red-2
```

Observed result: **1 failed in 2.09s** because the raw JSON result was not
typed on read and the canonical project loaded `ontology=None`.

### GREEN evidence

Focused final suite:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py -q --basetemp .pytest-zep-final-review-green-2
```

Observed result: **34 passed in 2.04s**.

Final graph, retry, route, resource-bound, runtime, and rate-limit regression
run:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py tests\test_graph_worker_final_fixes.py tests\test_graph_worker_retry_safety.py tests\test_graph_worker_task.py tests\test_zep_retry_policy.py tests\test_task_retry_classification.py tests\test_resource_bounds.py tests\test_runtime_regressions.py::test_graph_wait_reports_elapsed_time_without_name_error tests\test_rate_limiting.py -q --basetemp .pytest-zep-final-review-regressions-3
```

Observed result: **143 passed, 1 existing third-party warning in 17.91s**.
The warning is the existing `huggingface_hub` environment-variable
deprecation; there were no resource-bound or temporary-directory failures in
the stable rerun.

Touched-file Ruff:

```powershell
& 'C:\Users\serge\AppData\Roaming\Python\Python314\Scripts\ruff.exe' check app/models/project.py app/services/project_repository.py app/services/graph_builder.py app/tasks/graph_tasks.py app/utils/task_retry.py app/utils/zep_paging.py tests/test_graph_worker_cas_review.py tests/test_graph_worker_final_fixes.py tests/test_graph_worker_retry_safety.py tests/test_graph_worker_task.py
```

Observed result: **All checks passed**.

### Final design

- Terminal project failure now uses `fail_graph_build(project_id,
  expected_task_id, error)` in both stores. Legacy mode locks, rereads, checks
  `GRAPH_BUILDING` plus task ownership, and atomically writes. Canonical mode
  uses one conditional `UPDATE` with the same status/task fence and checks
  `rowcount`. A stale worker that loses the CAS reports supersession and never
  mutates the replacement task's project.
- Owner confirmation accepts only the same active `GRAPH_BUILDING` task or an
  unassigned `ONTOLOGY_GENERATED` project. Exact completed redelivery returns
  the stable existing graph result before task progress, source reads, owner
  mutation, or provider calls.
- Completion-write exceptions trigger a fresh canonical reread. Only the
  exact task ID, `GRAPH_COMPLETED` status, and stable graph ID prove success;
  all other states continue through fenced compensation.
- If Celery retry publication itself fails, the worker records a stable
  `graph_build_retry_dispatch_failed` terminal state through the same CAS.
  The initial task-progress update also occurs only after canonical load and
  ownership, so its failure can be fenced truthfully.
- Post-ingestion node/edge page reads now use bounded status-aware retry for
  429/5xx and established I/O failures. Exhaustion remains post-mutation and
  never replays graph creation or episode ingestion.
- Canonical project reads hydrate the latest completed ontology from
  `ontologies.result_json` through the migration's integer project FK.
  Canonical saves append a recoverable ontology version only when its JSON
  meaning differs from the latest completed version; repeated unchanged saves
  are no-ops. Explicit SQL JSON typing is exercised against an in-memory
  migration-shaped schema.

### Final-wave touched files

- `backend/app/models/project.py` (bounded graph ownership/failure CAS only)
- `backend/app/services/project_repository.py` (bounded canonical CAS and
  ontology version persistence/load only)
- `backend/app/tasks/graph_tasks.py`
- `backend/app/utils/zep_paging.py`
- `backend/tests/test_graph_worker_cas_review.py`
- `backend/tests/test_graph_worker_final_fixes.py` (CAS-aware test doubles)
- `backend/tests/test_graph_worker_retry_safety.py` (CAS-aware test double)
- `backend/tests/test_graph_worker_task.py` (CAS-aware test double)
- `.superpowers/sdd/zep-graph-worker-brief.md`
- `.superpowers/sdd/zep-graph-worker-report.md`

No live Zep call or local credential was used. No file was staged or committed.
The remaining bounded concern is unchanged: incomplete derived graphs still
need operator reconciliation because this repair intentionally does not add a
provider deletion workflow.

## Concurrent dispatch and final durability closure

Status: DONE

### RED evidence

The begin-CAS, unwind-race, late-ack, and completion-reconciliation regressions
ran before their production changes:

```powershell
cd backend
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_legacy_non_force_begin_cas_allows_only_one_stale_snapshot tests\test_graph_worker_cas_review.py::test_legacy_force_begin_cas_rejects_a_stale_owner_snapshot tests\test_graph_worker_cas_review.py::test_repository_begin_graph_build_uses_snapshot_cas_and_rowcount tests\test_graph_worker_cas_review.py::test_route_begin_conflict_fails_only_new_task_and_never_enqueues tests\test_graph_worker_cas_review.py::test_legacy_dispatch_unwind_never_overwrites_worker_completion tests\test_graph_worker_cas_review.py::test_graph_task_requeues_on_worker_loss_without_global_celery_changes tests\test_graph_worker_cas_review.py::test_task_completion_audit_failure_never_downgrades_real_completed_task -q --basetemp .pytest-zep-begin-cas-red
```

Observed result: **7 failed in 2.40s**. Both stores lacked the snapshot-aware
begin signature, the route returned dispatch 503 after a lost claim, legacy
unwind overwrote an already completed graph, the graph task early-acked, and a
real TaskManager completion followed by audit failure was downgraded to FAILED.

Ontology producer provenance ran as a separate RED slice:

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py::test_repository_save_project_persists_ontology_with_integer_project_fk tests\test_graph_worker_cas_review.py::test_repository_repeat_save_does_not_duplicate_unchanged_ontology tests\test_graph_worker_cas_review.py::test_repository_changed_ontology_without_producer_identity_fails_closed tests\test_graph_worker_cas_review.py::test_generate_ontology_threads_server_task_identity_into_canonical_save -q --basetemp .pytest-zep-ontology-provenance-red
```

Observed result: **4 failed in 2.15s**. The repository rejected the new private
producer argument, changed ontology data without an identity was accepted, and
the ontology task did not pass its server task ID to canonical persistence.

### GREEN evidence

Exact new slice: **11 passed in 1.96s**.

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py -q --basetemp .pytest-zep-final-p1-focused-1
```

Observed result: **43 passed in 2.00s**.

```powershell
.\.venv\Scripts\pytest.exe tests\test_graph_worker_cas_review.py tests\test_graph_worker_final_fixes.py tests\test_graph_worker_retry_safety.py tests\test_graph_worker_task.py tests\test_zep_retry_policy.py tests\test_task_retry_classification.py tests\test_resource_bounds.py tests\test_runtime_regressions.py::test_graph_wait_reports_elapsed_time_without_name_error tests\test_rate_limiting.py -q --basetemp .pytest-zep-final-p1-regressions-1
```

Observed result: **152 passed, 1 existing third-party warning in 10.47s**.

Ruff passed on every changed production/test file other than the three already
documented unrelated findings in `app/api/graph.py`; that route passed with
`F401,F841` ignored. No new Ruff finding was introduced. `git diff --check`
passed; Git emitted only the repository's existing LF/CRLF notices.

### Closure design

- `begin_graph_build` now receives `expected_status`, `expected_task_id`, and
  `force`. Legacy mode compares them while holding the per-project lock;
  canonical mode uses one conditional update with null-safe ownership,
  expected status, and non-force building exclusion. Concurrent non-force or
  stale-force callers lose the CAS without superseding the winner.
- A lost route claim fails only its newly created task as
  `graph_build_conflict`, returns 409, and never calls `apply_async`. Dispatch
  unwind now requires both its task identity and `GRAPH_BUILDING`, matching the
  canonical predicate and preserving a completion written during an ambiguous
  broker response.
- `build_graph_task` sets `acks_late=True` and
  `reject_on_worker_lost=True` locally. Its stable graph identity and existing
  duplicate/terminal fences make redelivery safe without changing global
  Celery policy.
- Task-envelope completion exceptions reread canonical task state. Persisted
  `COMPLETED` returns success; only confirmed PENDING/PROCESSING may be failed
  best-effort; terminal or unreadable state is never downgraded.
- Ontology generation passes its effective server task ID through a private
  canonical save argument. Changed versions store that exact ID and fail
  closed when it is absent, while unchanged ontology saves remain no-ops.

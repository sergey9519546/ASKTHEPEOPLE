# Protected Zep live-canary delivery report

Status: STRICT REPAIR VERIFIED LOCALLY / LIVE EXECUTION BLOCKED

## Implementation evidence

- The closed evidence validator, fixed fixture/ontology, internal graph ID,
  exact owner marker, run-bound Redis lock/journal v2, provider sequence,
  intent reconciliation, cleanup, and sanitized result contract are
  implemented in `backend/app/services/zep_live_canary.py`.
- Evidence validation and independent-verifier/revision binding are at
  `backend/app/services/zep_live_canary.py:151-216`.
- The ten-minute Redis lock, preflight journal, pending-cleanup refusal, and
  last-gate credential read are at
  `backend/app/services/zep_live_canary.py:490-634`.
- SDK mutation/read/verification and bounded materialization polling are at
  `backend/app/services/zep_live_canary.py:640-806`.
- Owner-safe one-shot delete and 404 confirmation are at
  `backend/app/services/zep_live_canary.py:393-487`.
- The Celery task is late-acked, rejects worker-loss acknowledgement, and
  derives the required run identity from `self.request.id` at
  `backend/app/tasks/zep_canary_tasks.py:10-23`; worker registration is at
  `backend/app/celery_app.py:25-30`.
- The CLI defaults to no dispatch, exposes only `--execute`, reads no provider
  credential, validates task results before printing, and returns the canary
  exit code at `backend/scripts/zep_live_canary.py:24-169`.
- Focused protection tests are in
  `backend/tests/test_zep_live_canary.py:1-665` and
  `backend/tests/test_zep_live_canary_task_cli.py:1-163`.

## TDD evidence

Initial RED:

```text
.\.venv\Scripts\pytest.exe tests\test_zep_live_canary.py tests\test_zep_live_canary_task_cli.py -q --basetemp .pytest-zep-canary-red-2
22 failed; missing service, task, and CLI produced the intended failures.
```

Initial GREEN:

```text
.\.venv\Scripts\pytest.exe tests\test_zep_live_canary.py tests\test_zep_live_canary_task_cli.py -q --basetemp .pytest-zep-canary-green-1
22 passed.
```

Strict-review RED:

```text
.\.venv\Scripts\pytest.exe tests\test_zep_live_canary.py -q --basetemp .pytest-zep-canary-red-review
4 failed / 17 passed, proving second graph identity on redelivery, one-shot
graph read, cleanup skipped on journal failure, and deterministic 403 retry.
```

Strict-review GREEN plus added mutation ambiguity coverage:

```text
.\.venv\Scripts\pytest.exe tests\test_zep_live_canary.py tests\test_zep_live_canary_task_cli.py -q --basetemp .pytest-zep-canary-green-3
30 passed.
```

The tests construct only local fakes. No Zep client call reached a network.

Final strict-repair TDD evidence:

```text
43 focused tests: 34 failed / 9 passed before implementation.
44 focused tests: 44 passed after the repairs.
The terminal-history regression separately failed before per-run terminal
retention and passed after it.
```

Cross-lane regression verification:

```text
.\.venv\Scripts\pytest.exe tests\test_zep_live_canary.py tests\test_zep_live_canary_task_cli.py tests\test_zep_retry_policy.py tests\test_zep_health_readiness.py tests\test_zep_deployment_diagnostics.py tests\test_zep_dependency_status.py tests\test_report_worker_dispatch.py tests\test_report_worker_context.py tests\test_graph_worker_task.py tests\test_graph_worker_retry_safety.py tests\test_graph_worker_final_fixes.py tests\test_graph_worker_cas_review.py tests\services\test_zep_tools.py tests\services\test_zep_tools_local_search.py tests\services\test_zep_tools_insight_forge.py -q --basetemp .pytest-zep-canary-regression
243 passed in 5.07s.
```

Static and documentation verification:

```text
ruff check <five touched Python files>
All checks passed!

ruff format --check <five touched Python files>
5 files already formatted

python tools/validate_docs.py
Warnings: 0; Errors: 0; RESULT: PASS
```

## Security and privacy result

- The canary fixture is fictional and fixed in code; no user/customer content
  can enter the operation.
- Zep remains mandatory for graph-backed availability, but this canary writes
  only a disposable derived graph. Canonical records do not depend on it.
- All task/CLI/journal reasons and exit/state/graph combinations are closed,
  stable codes. Provider and Redis exception strings are discarded.
- The CLI rejects malformed worker results, including invalid graph IDs,
  instead of printing them.
- A journal outage after provider mutation cannot prevent owner-safe cleanup;
  inability to durably record the final state returns exit 3.
- Late-ack redelivery reuses the Celery UUID. Terminal redelivery returns the
  retained result without key/client access; intent redelivery reconciles and
  cleans without replaying an uncertain mutation.

## Live execution decision

**BLOCKED.** No live canary was executed and no credential was inspected,
printed, hashed, or partially disclosed. The open public-credential incident's
rotation and independent-verification release gate must be satisfied first.

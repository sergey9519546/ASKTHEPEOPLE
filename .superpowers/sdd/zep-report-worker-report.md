# Zep report worker repair report

Status: DONE WITH ENVIRONMENTAL RUFF LIMITATION

## Scope and touched files

- `backend/app/tasks/report_tasks.py`
- `backend/app/api/report.py`
- `backend/app/services/report_agent.py`
- `backend/app/services/zep_tools.py`
- `backend/app/utils/response.py`
- `backend/app/__init__.py` (only the controlled 5xx scrub integration; the
  concurrent health-prefix change was preserved)
- `backend/tests/test_report_worker_context.py` (new)
- `backend/tests/test_report_worker_dispatch.py` (new)
- `backend/tests/test_logging_policy.py`
- `backend/tests/services/test_report_agent_generate_report.py`
- `backend/tests/services/test_zep_tools.py`
- `.superpowers/sdd/zep-report-worker-report.md`

No graph/readiness worker, project model, configuration, Supabase, evaluation,
or simulation API file was edited for this slice. Nothing was staged or
committed. No live Zep call or local/compromised credential was used.

## Implemented behavior

- The worker short-circuits a duplicate completed Celery delivery before
  `ReportAgent`, but only after resolving the authoritative project graph
  read-only. Persisted result/metadata simulation, report, and graph identities
  must all match the delivery and project; a missing or mismatched identity
  fails closed without terminal downgrade (`report_tasks.py:31-55`,
  `:100-160`).
- The stripped persisted project `simulation_requirement` and exact project
  `graph_id` are authoritative. Missing/padded graphs fail with
  `report_graph_id_missing`; a present simulation graph must match exactly or
  fail with `report_graph_scope_mismatch` (`report_tasks.py:80-105`). Payload
  decision/graph/requirement/prompt overrides are discarded (`report_tasks.py:43-46`).
- `ReportAgent.generate_report` is captured. Only an actual
  `ReportStatus.COMPLETED` artifact whose report, simulation, and graph
  identities all exactly match the server-resolved context completes the task;
  missing or mismatched identity becomes `report_generation_failed`
  (`report_tasks.py:58-71`, `:169-180`).
- A completion persistence exception re-reads task state. A confirmed completed
  state is accepted only when its persisted simulation, report, and
  authoritative graph identities also match; a mismatch is ambiguous and never
  downgraded. The completed task result stores all three identities. Confirmed
  pending/processing state is failed best effort, while missing, unreadable, or
  other terminal state is never overwritten (`report_tasks.py:181-239`).
- The route releases its process-local lease after successful dispatch. It
  creates tasks with `report_generate:<simulation_id>` and an explicit
  candidate ID; if `create_task` returns another in-flight task ID, it returns
  that task and does not enqueue (`report.py:232-264`). It dispatches only
  server-owned simulation/report IDs and uses the task ID as Celery delivery ID
  (`report.py:266-275`).
- Task creation, lease assignment, worker import, and dispatch share one
  cleanup boundary. The candidate task identity is bound before `create_task`,
  so even a post-write audit exception best-effort fails that exact task and a
  retry cannot reuse a phantom PENDING record. Any successful existing-ID
  return replaces the candidate before later cleanup. All lease releases are
  guarded, and the client receives stable sanitized `503
  report_dispatch_failed` (`report.py:44-70`, `:233-304`).
- Malformed/non-object JSON is `400 report_request_invalid`; missing IDs and
  server records use stable codes. Project graph/scope/requirement validation
  happens before task or lease creation (`report.py:118-194`).
- Production 5xx scrubbing preserves only the closed allowlist pair
  `report_dispatch_failed`/503 through an opaque in-process marker. Arbitrary
  body/header/attribute markers, arbitrary codes, and wrong statuses remain
  `internal_server_error` (`response.py:8-39`, `app/__init__.py:296-322`).
- Report-agent tool/provider exceptions log only exception class, raw LLM
  responses log only length, model-generated section titles are absent from
  operational logs, and failed report state is the stable
  `report_generation_failed` even in debug (`report_agent.py:1316-1328`,
  `:1513-1523`, `:1627-1687`, `:2137-2165`).
- The Zep tools logger captured by each report console now emits only stable
  operation codes and exception types for provider, retrieval, file, and model
  failures. Raw provider bodies and exception strings therefore cannot reappear
  through the successful console-log endpoints (`zep_tools.py:539-579`,
  `:658-672`, `:1337-1352`; `report_agent.py:393-403`). Provider failure
  summaries returned to report generation are also stable user-safe wording,
  never raw exception or provider response text (`zep_tools.py:1608-1721`).

## RED evidence

The original context repair recorded clean REDs for authoritative project
context, missing simulation/project, blank/non-string requirement, missing or
padded project graph, graph mismatch, payload override exclusion, secret-bearing
provider failure, immutable Celery identity, server-only dispatch, route graph
validation, dispatch/task-store failure cleanup, and failure-persistence
sanitization. Those failures are retained in the focused tests at
`test_report_worker_context.py:325-924` and
`test_report_worker_dispatch.py:53-1000`.

The strict-review additions were also run alone before their production change:

| RED behavior | Exact observed failure |
|---|---|
| successful dispatch releases lease | expected one release, observed `[]`; `1 failed` |
| idempotent duplicate does not enqueue | response used a new report ID and omitted `already_queued`; `1 failed in 2.06s` |
| invalid agent result | `None`, `FAILED`, and wrong identity all completed without raising; `3 failed in 1.22s` |
| completion already persisted | raised `report_generation_failed` instead of preserving completed state; `1 failed in 1.17s` |
| ambiguous completion reread | `fail_task` was called despite unknown state; `1 failed in 1.20s` |
| duplicate completed delivery | entered generation and raised `report_generation_failed`; `1 failed in 1.17s` |
| completed redelivery identity mismatch | mismatched persisted report/simulation identity returned success; `2 failed in 1.29s` |
| post-create lease assignment failure | exact created task was not failed; `1 failed in 1.97s` |
| production-safe stable 503 | middleware changed `report_dispatch_failed` to `internal_server_error`; `1 failed in 2.13s` |
| malformed/non-object JSON | both cases returned 503 instead of 400; `2 failed in 2.19s` |
| missing route records | descriptive raw strings appeared instead of stable codes; `2 failed in 2.10s` |
| tool exception sanitization | raw provider canary was returned/logged; `1 failed in 1.08s` |
| outline exception sanitization | raw provider canary appeared in the error log; `1 failed in 1.01s` |
| raw model response logging | response canary appeared in debug logs; `1 failed in 1.00s` |
| report generation exception logging | raw exception canary appeared in logs; `1 failed in 1.00s` |
| debug failure persistence | raw exception became `report.error`; `1 failed in 0.99s` |
| model-generated title logging | title canary appeared in warning/error logs; `1 failed in 1.01s` |
| completed artifact wrong simulation/graph or missing identity | worker returned success and completed the task; `3 failed` |
| completion reread with wrong persisted identity | worker returned false success after the completion exception; `1 failed` |
| task create post-write audit failure | retry returned `202 already_queued` for a task that was never dispatched; `1 failed` |
| raw Zep exception in report console | successful console-log endpoint returned the provider-body canary; `1 failed` |
| completed redelivery/reread wrong graph | worker accepted a completed task whose persisted graph disagreed with the authoritative project; `2 failed` |
| synthetic probe provider failure summary | raw provider body flowed into all three failure summaries; `3 failed` |

## GREEN and regression evidence

- Focused worker/route/security/agent command: `68 passed`.
- Broader report/API/privacy command: `74 passed in 2.95s`.
- Zep retry/tools regressions: `34 passed`.
- TaskManager idempotency regressions: `2 passed in 2.88s`.
- Production files compiled with `python -m py_compile`: pass.
- `python tools/validate_docs.py`: `Warnings: 0`, `Errors: 0`, `RESULT: PASS`.
- Scoped `git diff --check` and new-test trailing-whitespace scan: pass.

## Ruff limitation

Touched-file `uvx ruff check ...` was attempted and produced no lint findings
because it could not initialize the existing uv cache:
`Access is denied ... uv\\cache\\sdists-v9\\.git (os error 5)`. The required
escalated retry was automatically rejected because the approval usage limit was
exhausted. No workaround was attempted.

## Concerns and honest architecture status

- This is not a durable cross-process workflow claim. `TaskManager.create_task`
  scans its process-local `_tasks` for the idempotency key
  (`models/task.py:302-308`), and its own lookup documentation acknowledges the
  process-local scan (`models/task.py:343-344`). The route protection is useful
  for the current process but not a durable distributed uniqueness guarantee.
- The coordinator is explicitly process-local
  (`report_generation_coordinator.py:63-64`), the route now releases its lease
  after dispatch, and the worker still receives `generation_lease=None`
  (`report_tasks.py:108-111`). Durable leasing/fencing remains separate work.
- Verification basetemp folders remain untracked in the shared workspace. Per
  the bounded review instruction, no cleanup was attempted.

## 2026-08-11 durability addendum

Status: DONE — OFFLINE ONLY

This bounded follow-up changed only
`backend/app/tasks/report_tasks.py`, added
`backend/tests/test_report_worker_durability.py`, and updated the two existing
success fixtures in `backend/tests/test_report_worker_context.py`. It did not
touch routes, graph/readiness/canary/deployment/security code, call Zep, stage,
or commit anything.

Implemented behavior:

- `generate_report_task` now declares `acks_late=True` and
  `reject_on_worker_lost=True`.
- A completed delivery is successful only when both the terminal task identity
  and the persisted `ReportManager` artifact match the report ID, simulation
  ID, authoritative project graph ID, completed status, and stripped canonical
  `simulation_requirement`.
- A completion-exception reread applies the same persisted-artifact check. A
  missing, corrupt, or mismatched artifact is treated as ambiguous and cannot
  downgrade a terminal task.
- Once the worker observes a completed delivery, later authoritative-context
  resolution failures also cannot write a lower task state.

TDD evidence:

- Initial focused RED: `6 failed` — the two Celery delivery flags were false;
  missing and mismatched report artifacts returned success; completion reread
  accepted terminal task metadata without an artifact.
- Follow-up terminal-state RED: `1 failed` — a missing authoritative project
  caused `fail_task` to downgrade an already-completed delivery.
- Focused GREEN: `7 passed in 1.13s`.
- Final broad report/task regression: `101 passed, 1 xfailed in 14.69s`. The
  xfail is the pre-existing report-generation-timeout expectation.
- Scoped Ruff on the implementation and new durability tests passed with the
  legacy task-envelope `BLE001` findings excluded; those broad persistence and
  task-boundary catches predate this addendum. `py_compile` and scoped
  `git diff --check` passed.

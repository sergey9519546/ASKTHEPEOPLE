# Zep integrated graph/report P1 fixes — implementation evidence

**Status:** scoped implementation complete; repository release remains **NO-GO**
until the parent audit closes the independent credential, deployment, tenancy,
ingestion, and live-canary blockers.

**Network/provider safety:** no Zep, LLM, Redis, database, or other network call
was made in this lane. Provider boundaries were replaced with deterministic
in-process fakes.

## Behaviors implemented

1. A graph task now holds one delivery fence across the complete synchronous
   provider mutation. The legacy store uses an OS-owned cross-process file lock
   (`backend/app/models/project.py:62`, `backend/app/models/project.py:382`);
   canonical PostgreSQL uses a session advisory lock whose connection remains
   open through the mutation (`backend/app/services/project_repository.py:142`).
   The Celery task acquires that fence before executing any graph-build logic
   (`backend/app/tasks/graph_tasks.py:61`). A lost process releases either lock
   through the OS/database session rather than leaving a permanent claim.
2. Task terminal outcomes are monotonic. A late delivery cannot change
   `COMPLETED` to `FAILED` or replace the coupled result/error fields
   (`backend/app/models/task.py:475`). Audit events are emitted only when the
   requested terminal transition actually became current
   (`backend/app/models/task.py:570`, `backend/app/models/task.py:602`).
3. Exhausted canonical project reads still attempt the known
   `project_id`/Celery-task-id owner-CAS failure transition. A missing local
   project object no longer skips recovery and strand `GRAPH_BUILDING`
   (`backend/app/tasks/graph_tasks.py:466`).
4. Report workers verify queued server-owned simulation/report/graph metadata
   against authoritative simulation/project state before constructing the
   report agent. Missing metadata fails closed
   (`backend/app/tasks/report_tasks.py:181`).
5. Initial report completion now requires the generated artifact to retain the
   exact canonical decision text as well as report, simulation, and graph
   identities (`backend/app/tasks/report_tasks.py:56`).
6. Every report delivery checks for an exact already-saved completed artifact.
   A `PENDING`/`PROCESSING` redelivery repairs its task envelope and returns
   without regeneration, closing the save-before-ack crash window
   (`backend/app/tasks/report_tasks.py:193`).

## Strict TDD evidence

The production changes followed observed RED failures:

- Initial integrated reproduction: **4 failed** — duplicate same-ID provider
  mutation, `COMPLETED → FAILED`, queued graph drift, and wrong-decision
  artifact acceptance.
- Canonical advisory-fence contract: **1 failed** with the expected missing
  method.
- Second crash-window reproduction: **3 failed** — skipped owner-CAS recovery,
  missing queued identity accepted, and saved report regenerated.

The focused regression file is
`backend/tests/test_zep_integrated_p1_regressions.py:56-590`. It contains eight
tests covering both storage fence implementations and every defect above.

Final scoped verification after all shared-lane edits settled:

```text
170 passed in 15.11s
```

The matrix includes task durability, all graph worker/retry/CAS/source-read
tests, all report worker context/dispatch/durability tests, and the eight new
integrated regressions. Targeted `ruff` checks for import/unused defects passed,
and Python bytecode compilation passed for every changed production module and
the integrated regression file.

An earlier all-backend observation reached **9,299 passing** tests but had 29
live-canary fixture/revision-contract failures outside this lane. Those failures
were repaired by the parent lane after that observation; per orchestration
direction, the final all-backend acceptance run is owned by the parent and was
not duplicated here.

## Explicit limits

- The PostgreSQL advisory-lock path is contract-tested with a fake SQLAlchemy
  engine; it has not been exercised against a live database in this lane.
- This fence prevents concurrent delivery mutation. It does not replace the
  target durable attempt/lease/fencing-token state machine from ADR-0003.
- The protected Zep canary remains blocked until credential rotation evidence
  is independently verified.
- Graph-ID authorization gaps in other routes, graph reset/delete during an
  active build, report-route early reuse/unsorted lookup, and historical UI
  graph selection were reported separately to the parent audit and are not
  represented as fixed here.

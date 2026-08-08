# Task 5 Brief Independent-Review Fix Report

Status: READY FOR RE-REVIEW

Date: 2026-08-08

## Findings closed

The brief now resolves the independent review findings without claiming
production implementation:

1. Forced-RLS operations use three purpose-bound service principals and
   bounded worker, dispatcher, and reaper seams.
2. Stage-local automatic retry is distinct from run-level
   `FAILED_RETRYABLE -> QUEUED -> PREPARING` retry.
3. The flag gates new canonical creation/start while preserving acknowledged-
   run reads, events, stop, delivery, heartbeat, and recovery.
4. OIDC/ActorContext-bound WebSocket tickets use a shared Redis nonce record
   and atomic Lua compare-and-delete consumption; APP_TOKEN-era process memory
   is not authority.
5. Lease claim verifies the exact outbox row, active run/current stage, stop
   fence, no stop/terminal state, and one active attempt before provider work.
6. `WorkerRunCommandKind` is closed and purpose/command authorization is
   exhaustive.
7. Identifier arity matches the landed independent-alias implementation and
   the full AGENTS authority hierarchy is present.
8. `tools/validate_task5_brief.py` locks the duplicated run/stage graphs, Task
   6 gate, service, ticket, retry, and feature-flag boundaries.

## Verification

```text
python tools/validate_task5_brief.py
Task 5 brief contract: PASS
Run states: 20; run edges: 40; stages: 9; attempt states: 9; attempt edges: 10

python tools/validate_docs.py
Warnings: 0
Errors: 0
RESULT: PASS

uvx ruff check tools/validate_task5_brief.py
All checks passed!
```

Named approvals, tenant/OIDC/RLS persistence, service-principal deployment,
PostgreSQL migrations, object storage, Task 6 verification, recovery evidence,
and production cutover remain explicit blockers.

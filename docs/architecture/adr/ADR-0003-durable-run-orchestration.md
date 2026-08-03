---
title: "ADR-0003: Durable, resumable run orchestration"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "2"
applies_to: "backend/app/tasks/, backend/app/services/simulation_manager.py, backend/app/services/simulation_runner.py, backend/app/services/simulation_ipc.py"
audit_relevance: "P0 'Preparation runs in a local daemon thread', P1 'Process-local runtime ownership prevents safe scaling', P1 'Duplicated destructive start/restart lifecycle block', P1 'Contradictory lifecycle semantics'"
---
# ADR-0003: Durable, resumable run orchestration

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

A complete run spans source extraction, review gates, profile proposals,
scenario construction, multiple model/simulation calls, validators, brief
generation, and exports. Synchronous HTTP handlers and best-effort local
processes cannot provide reliable cancellation, recovery, idempotent retries,
or a complete audit history.

## Decision

Introduce a `RunOrchestrator` interface and execute the stage graph as a durable
workflow. Temporal is the reference implementation, not a mandatory vendor.
Activities receive IDs, reload authoritative state, emit append-only events,
heartbeat, use bounded retries, and are idempotent. Completed runs are
immutable; reruns create new run IDs.

## Consequences

The system gains operational complexity and requires workflow-version
discipline. Long-running work becomes observable and recoverable. The UI can
close/reconnect without losing work. Stop and retry semantics become explicit.

## Alternatives considered

1. Continue Python subprocesses and SQLite flags. Rejected for production
   reliability.
2. Use a basic queue only. Insufficient unless it also provides durable state,
   cancellation, timers, history, and replay-equivalent recovery.
3. Keep requests open over WebSocket. Rejected; transport is not workflow
   durability.

## Verification

Worker-kill tests, replay/recovery tests, duplicate-message tests, stop-at-each-
stage tests, and disaster-recovery exercise.

## References

- [Temporal documentation](https://docs.temporal.io/) — Reference implementation for durable, resumable workflow orchestration; the architecture requires an interface rather than vendor lock-in.
- [OpenTelemetry documentation](https://opentelemetry.io/docs/) — Vendor-neutral traces, metrics, and logs.

## Project-specific implication (baseline `8b616dc7`)

The current code has two execution paths in production. Both are PARTIAL
against this ADR; gate 2 is owned by `askthepeople-orchestration-engineer`.

### Celery path — PARTIAL

[`backend/app/celery_app.py`](../../../backend/app/celery_app.py) configures
Celery against the Redis broker and result backend. The single registered
task is
[`run_simulation_task`](../../../backend/app/tasks/simulation_tasks.py:16),
which calls
`SimulationRunner.start_simulation(...)`
([`simulation_tasks.py:55`](../../../backend/app/tasks/simulation_tasks.py:55))
and polls every 0.5 s for status
([`simulation_tasks.py:69-116`](../../../backend/app/tasks/simulation_tasks.py:69)).
The Celery task has the right shape — task ID, retries, exception handling,
shared task manager updates — but the polling loop is a smell. Reaching
this ADR requires push-based event delivery, durable heartbeats, and a
fencing token.

### In-process daemon thread — release-blocker (audit P0)

The preparation endpoint in
[`backend/app/api/simulation.py`](../../../backend/app/api/simulation.py)
still creates a `threading.Thread(..., daemon=True)` to run preparation
work. The audit's P0 finding is binding: **the web route MUST enqueue
work and return; it MUST NOT create threads or own long-running
execution**. The route must be replaced with a `POST /api/simulations/{id}/preparations`
returning `202 Accepted` with a `Location: /api/jobs/{job_id}` header
and an idempotency key. The job system must provide the full
contract listed in this ADR.

### Hourly cleanup daemon thread — release-blocker (audit pattern)

[`_task_cleanup_worker`](../../../backend/app/__init__.py:229) is a second
in-process daemon thread that runs forever from `create_app()`. It is the
same pattern as the P0 finding and must be replaced with a worker-owned
job.

### Process-local runtime ownership — release-blocker (audit P1)

The runner stores active resources in class-level process memory (processes,
monitor threads, queues, file handles, run state, follower engines,
follower agents). The audit requires that ownership transfer to a
dedicated simulation worker process with a persistent lease and heartbeat
and a fencing token. The contract from this ADR — activities reload
authoritative state, emit append-only events, heartbeat, use bounded
retries, and are idempotent — applies.

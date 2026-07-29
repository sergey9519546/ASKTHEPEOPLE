---
title: "ADR-0003: Durable, resumable run orchestration"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
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

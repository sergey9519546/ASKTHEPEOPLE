---
title: "Execution Plan 04 — Durable Orchestration and Path Engine"
status: "Operational"
version: "1.0.0"
owner: "AI Platform + Workflow + Research"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
---

# Execution Plan 04 — durable orchestration and path engine

## Objective

Replace best-effort monolithic simulation/report generation with a durable,
versioned, typed stage workflow that produces four to eight materially distinct
possible paths and a complete Coverage Ledger.

## Dependencies

- immutable approved run configuration;
- prompt/model registries;
- target database and event model;
- `RunOrchestrator` ADR;
- OASIS/CAMEL adapter boundary.

## Workstreams

### A. Orchestrator interface

Wrap current runners behind a domain interface. Implement durable history,
recovery, retries, timers, cancellation, status, and idempotent stage
activities. Temporal is the reference implementation.

### B. Run and stage state machines

Implement server-side transitions, event sequence, optimistic concurrency,
stop/retry semantics, and plain-language states.

### C. Provider adapters

Implement:

- model adapter;
- optional retrieval/graph adapter;
- OASIS/CAMEL simulation adapter;
- usage/cost normalization;
- exact model/release identity;
- safe error mapping;
- kill switches.

### D. Stage S08 — independent path generation

Generate each path from a frozen scenario frame without seeing prose from other
paths. Output structured path objects with approved input IDs.

### E. Stage S09 — cross-path synthesis

Compute recurrence within the synthetic run, differences, conflicts, missing
information, duplicates, and assumption dependency. Never convert recurrence
to public support.

### F. Stage S10 — disconfirmation and validation

Create falsifiers and non-leading questions for each consideration.

### G. Deterministic validators

Require:

- schema;
- truth language;
- epistemic edges;
- source grounding;
- profile integrity;
- path coverage;
- distinctness;
- output safety;
- cost/size.

### H. Coverage Ledger

Record every selected state/profile/rule as covered, intentionally excluded
with reason, or incomplete. Brief generation is blocked on unexplained gaps.

### I. Assumption comparison

Create matched run variants. Render what changed and why in plain language.
No sensitivity score or probability.

### J. Observability and budgets

Trace each stage with safe metadata. Enforce token, path, retry, duration,
concurrency, and organization budgets.

## Chaos and failure testing

- kill workers after every activity boundary;
- duplicate workflow messages;
- provider timeout/rate limit/malformed output;
- unavailable validator;
- stop during path generation;
- partial OASIS output;
- model alias drift;
- cost exhaustion;
- database/object-store transient failure.

## Acceptance evidence

- acknowledged runs survive worker/process restart;
- retries do not duplicate paths/events/cost records;
- stop works at each active state;
- exact releases/manifests are recorded;
- all paths pass coverage/distinctness/truth/provenance;
- no source directly supports a path outcome;
- no graph metric is public support;
- incomplete runs cannot produce a final brief;
- canary and rollback work.

## Rollback

Keep the current runner available only for read/replay of legacy fixtures during
transition. New production runs use the orchestrator. Rollback restores the
previous workflow code/release set; persisted event history remains readable.

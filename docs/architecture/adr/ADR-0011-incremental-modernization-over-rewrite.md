---
title: "ADR-0011: Incremental Modernization Over Framework Rewrite"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "all gates; this ADR defines the rollout order"
applies_to: "all changes to backend/, frontend/, docs/, and the deployment topology"
---

# ADR-0011: Incremental modernization over framework rewrite

## Context

The current implementation is a Vue/Vite frontend and Flask/Python backend with
OASIS/CAMEL, Zep, SQLite/JSONL artifacts, and provider-specific integration.
The product requires major methodological, domain, security, data, workflow,
and observability changes. A simultaneous framework rewrite would combine
product-category risk with migration risk and would make behavioral regression
harder to localize.

## Decision

Modernize incrementally behind explicit interfaces. Preserve Vue and Flask
unless a measured constraint justifies replacement. Introduce, in dependency
order:

1. canonical domain schemas and truth invariants;
2. server-enforced tenancy and authorization;
3. secure source-ingestion boundaries;
4. a `RunOrchestrator` interface around current runners;
5. immutable prompt/model/validator releases;
6. canonical transactional and object persistence;
7. provider, graph-memory, and OASIS/CAMEL adapters;
8. observability, release evidence, and rollback;
9. replacement of legacy feed/persona surfaces with the route grammar.

A framework migration requires a separate accepted ADR containing benchmark
evidence, compatibility impact, migration sequence, rollback, and ownership.

## Consequences

- Truth and security controls can land before a broad rewrite.
- Old and new paths may temporarily coexist and require dual-read or shadow
  verification.
- Compatibility adapters become deliberate migration seams rather than
  permanent leakage into the domain.
- The team must delete legacy paths after cutover; indefinite dual systems are
  not acceptable.

## Rejected alternatives

- **Immediate full rewrite:** rejected because it couples too many unknowns and
  delays product-truth enforcement.
- **Leave the current architecture unchanged:** rejected because mutable local
  artifacts and direct provider coupling do not meet the production target.
- **Frontend-only redesign:** rejected because the highest risks are semantic,
  methodological, authorization, workflow, and provenance failures.

## Verification

- Repository census records actual current boundaries and divergences.
- Contract tests prove adapters preserve canonical schemas.
- Each migration phase has a feature flag, data-verification step, and rollback.
- Legacy paths are removed only after parity and production evidence.
- No document or release claim describes a target component as already live.

## Project-specific implication (baseline `8b616dc7`)

This ADR is the rollout order for the 6-gate refactor defined in
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` §13](../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md#13-highest-value-implementation-order)
and recorded in
[`docs/architecture/index.md` §"Gaps to the target architecture"](../index.md).

### Gate ownership

| Gate | Theme | Owner agent | Status (baseline `8b616dc7`) |
|---|---|---|---|
| 0 | Immediate correctness and security | `askthepeople-security-reviewer` | NOT STARTED |
| 1 | Typed API boundary | `askthepeople-architect` | NOT STARTED |
| 2 | Durable workflows | `askthepeople-orchestration-engineer` | NOT STARTED |
| 3 | Canonical persistence and provenance | `askthepeople-persistence-engineer` | NOT STARTED |
| 4 | Scale and operations | `askthepeople-release-operator` | NOT STARTED |
| 5 | Advanced simulation methodology | `askthepeople-ai-eval-steward` + `askthepeople-architect` | NOT STARTED |

The dependency order in this ADR — truth, tenancy, ingestion, durable
orchestration, prompt/model registries, persistence, adapters,
observability, route grammar — is preserved by the gate ordering above.
Gates 0–3 are scoped-blocking for production release. Gates 4–5 are
post-launch hardening.

### Current state matches the order

- Truth and disclosure invariants are already in the contract and
  the README (gate 0 first deliverable). The wire-level enforcement
  is already in `create_app()` (CSP, CORS, security headers,
  traceback stripping, no body logging, SafePathError → 400, rate
  limit → 429). What is **not yet** in place: the P0 path-escape
  fix, the P0 prompt-prefixing fix, the in-product refusal flow, the
  claim registry, and the zero-trust ingestion state machine.
- The Flask blueprint layout already mirrors the planned
  per-resource decomposition target
  ([`backend/app/api/__init__.py:13-17`](../../../backend/app/api/__init__.py:13))
  — auth, graph, simulation, report, settings. The decomposition
  must move routes from `simulation.py` into resource-named modules.
- Celery is already wired
  ([`backend/app/celery_app.py`](../../../backend/app/celery_app.py))
  and the simulation task is registered
  ([`backend/app/tasks/simulation_tasks.py`](../../../backend/app/tasks/simulation_tasks.py:16)).
  What is **not yet** in place: idempotency keys, leases, fencing,
  heartbeats, push-based event delivery, retry classification.
- File-based JSON persists project, simulation, and report state.
  What is **not yet** in place: PostgreSQL with row-level security,
  outbox events, object storage with tenant-prefixed keys.

### Repository census — first deliverable

The
[`docs/exec-plans/00-repository-census-and-governance.md`](../../exec-plans/00-repository-census-and-governance.md)
is the first deliverable of this ADR. It must run against the
current baseline (`8b616dc7`) and produce a per-aggregate divergence
report from the doc-system baseline (`c33a6a91`). The 30-commit gap
between the two baselines is recorded in
[`docs/archive/legacy-2026-07-29/README.md`](../../archive/legacy-2026-07-29/README.md)
and must be expanded to a full census before any release claim
cites the new authority docs as already-live.

### What is not allowed by this ADR

- A framework migration (e.g. replacing Flask with FastAPI, or Vue
  with Svelte) without a separate accepted ADR containing benchmark
  evidence, compatibility impact, migration sequence, rollback, and
  ownership.
- Indefinite dual systems. Old and new paths may temporarily
  coexist, but legacy paths are deleted after cutover.
- A "framework rewrite PR" that combines product-category risk with
  migration risk.
- Describing a target component as already live in any document or
  release claim.

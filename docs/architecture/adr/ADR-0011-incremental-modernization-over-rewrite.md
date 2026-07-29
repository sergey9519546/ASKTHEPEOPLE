---
title: "ADR-0011: Incremental Modernization Over Framework Rewrite"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
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

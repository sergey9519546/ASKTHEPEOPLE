---
title: "Architecture Decision Records"
status: "Normative"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
---

# Architecture Decision Records

ADRs record decisions that constrain implementation and product behavior.
Accepted ADRs are immutable. A later ADR may supersede one, but MUST preserve
the original for audit.

## ADR lifecycle

```text
PROPOSED → ACCEPTED → SUPERSEDED
              ↘ DEPRECATED
PROPOSED → REJECTED
```

Each ADR includes context, decision, consequences, alternatives, and
verification. A code change that contradicts an accepted ADR requires a new
ADR in the same pull request.

## Index

| ADR | Decision | Status |
|---|---|---|
| [0001](ADR-0001-product-category-and-truth-contract.md) | Product category and truth contract | Accepted |
| [0002](ADR-0002-epistemic-ledger.md) | Epistemic Ledger as a domain primitive | Accepted |
| [0003](ADR-0003-durable-run-orchestration.md) | Durable, resumable run orchestration | Accepted |
| [0004](ADR-0004-provider-adapters-and-prompt-registry.md) | Provider adapters and immutable prompt registry | Accepted |
| [0005](ADR-0005-zero-trust-source-ingestion.md) | Zero-trust source ingestion | Accepted |
| [0006](ADR-0006-route-map-list-parity.md) | Route map/list semantic parity | Accepted |
| [0007](ADR-0007-human-validation-boundary.md) | External human-validation boundary | Accepted |
| [0008](ADR-0008-export-provenance.md) | Truth-preserving exports and provenance | Accepted |
| [0009](ADR-0009-multi-tenant-isolation.md) | Defense-in-depth tenant isolation | Accepted |
| [0010](ADR-0010-no-chain-of-thought-retention.md) | No hidden chain-of-thought retention | Accepted |
| [0011](ADR-0011-incremental-modernization-over-rewrite.md) | Incremental modernization over framework rewrite | Accepted |
| [0012](ADR-0012-canonical-transactional-and-object-persistence.md) | Canonical transactional and object persistence | Accepted |

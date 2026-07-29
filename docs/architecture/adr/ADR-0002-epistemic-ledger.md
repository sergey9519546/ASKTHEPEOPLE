---
title: "ADR-0002: Epistemic Ledger as a domain primitive"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
---
# ADR-0002: Epistemic Ledger as a domain primitive

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

ASKTHEPEOPLE combines user statements, uploaded source material, declared
assumptions, model-generated content, system metadata, and—potentially in a
later phase—external human findings. Without a typed origin and relation model,
the interface can accidentally present a source as evidence for a generated
outcome or a run record as a citation.

## Decision

Create an Epistemic Ledger. Every meaningful assertion has an origin and role.
Every relation uses a constrained enum. The domain layer and database reject
relationships that cross the Product Truth Contract, including source-to-path
proof, generated-profile-to-sample membership, or run-record-to-citation.

The ledger is required for briefs, route maps, exports, API serialization, and
external human evidence.

## Consequences

The data model becomes more explicit and some legacy artifacts require
migration. Generation stages must output IDs, not unstructured prose alone.
The benefit is auditable separation among source provenance, synthetic
generation, and human evidence.

## Alternatives considered

1. Store links in ad hoc JSON. Rejected because constraints cannot be reliably
   enforced or queried.
2. Use a generic graph database as the authority. Rejected for the initial
   system of record; graph projection may be derived, but domain validation
   belongs in transactional data.
3. Rely on prompt instructions. Rejected because model behavior is not a
   security or integrity boundary.

## Verification

Property-based relation tests; database constraint tests; route/export
serialization tests; migration reconciliation report.

## References

- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [C2PA Technical Specifications](https://spec.c2pa.org/specifications/) — Cryptographically verifiable provenance structure; provenance does not prove that content is true.

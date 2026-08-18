---
title: "ADR-0002: Epistemic Ledger as a domain primitive"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "1 (data model) and 3 (persistence)"
applies_to: "every persisted fact, every prompt-output pair, every report section, every export row"
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

## Project-specific implication (baseline `8b616dc7`)

The Epistemic Ledger is **not yet implemented**. See
[`docs/architecture/data-model.md` §"Epistemic Ledger — TARGET"](../data-model.md)
for the per-aggregate gap and
[`docs/product/PRODUCT_TRUTH_CONTRACT.md` §"Epistemic Ledger"](../../product/PRODUCT_TRUTH_CONTRACT.md)
for the origin types, epistemic roles, and allowed/prohibited
relationships that the data model must enforce.

The current closest analogue is the `report_evidence` service
([`backend/app/services/report_evidence.py`](../../../backend/app/services/report_evidence.py))
which carries a per-source-type evidence score. That score is a
heuristic by source type, NOT a calibrated confidence or a citation,
and is acknowledged as such in
[`docs/product/SUCCESS_METRICS.md`](../../product/SUCCESS_METRICS.md).

Reaching the ledger requires:

- Every persisted fact to carry an `origin` (USER_STATED,
  SOURCE_EXTRACTED, ASSUMPTION_DECLARED, GENERATED_GENERATED,
  EXTERNAL_HUMAN_EVIDENCE, SYSTEM_METADATA) and an `epistemic_role`.
- A domain validation layer that rejects the prohibited
  relationships (`SOURCE SEGMENT -> proves -> POSSIBLE PATH`,
  `GENERATED PROFILE -> is member of -> SAMPLE`, etc.) at write
  time.
- Property-based or exhaustive relationship tests in the test
  corpus.
- Closing the audit's P1 finding "Client-supplied export data can
  fabricate provenance" so the export route cannot bypass the
  ledger by accepting arbitrary rows. See
  [`docs/architecture/adr/ADR-0008-export-provenance.md`](ADR-0008-export-provenance.md).

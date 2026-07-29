---
title: "ADR-0008: Truth-preserving exports and provenance"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
---
# ADR-0008: Truth-preserving exports and provenance

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

Screenshots, copied passages, PDFs, shared links, and API outputs can lose the
interface context that explains synthetic origin. Provenance metadata can also
be misrepresented as proof that content is accurate.

## Decision

Generate exports from canonical domain data. Require visible truth disclosure,
machine-readable origin metadata, content hashes, exact run/prompt/model/
validator versions, and human-edit records. Use signed manifests and adopt C2PA
where the target format and tooling support it. State explicitly that
provenance proves declared origin/integrity, not factual truth.

## Consequences

Exports may fail rather than omit disclosures. Consumers receive better audit
data. C2PA support is format-dependent and does not replace visible labels or
method documentation.

## Alternatives considered

1. Add a footer only. Rejected because cropping/copying can remove it.
2. Metadata only. Rejected because users may never inspect metadata.
3. Watermark every page heavily. Rejected as a universal requirement; visible
   headers/footers and component labels are more usable, with watermarking
   available for high-risk formats.

## Verification

Export golden tests, metadata parser tests, clipboard tests, social-card tests,
signature verification, and disclosure-stripping adversarial tests.

## References

- [C2PA Technical Specifications](https://spec.c2pa.org/specifications/) — Cryptographically verifiable provenance structure; provenance does not prove that content is true.
- [European Commission Article 50 transparency guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems) — Final July 2026 guidance on transparency obligations that apply from 2 August 2026.

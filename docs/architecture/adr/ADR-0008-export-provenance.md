---
title: "ADR-0008: Truth-preserving exports and provenance"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "5"
applies_to: "backend/app/services/export_service.py, all export routes, all generated report files"
audit_relevance: "P1 'Client-supplied export data can fabricate provenance', P2 'Nested report-directory scans'"
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

## Project-specific implication (baseline `8b616dc7`)

The audit's P1 finding "Client-supplied export data can fabricate
provenance" is the deepest hazard against this ADR in the current code.
Resolving it is gate 5, owned by
`askthepeople-ai-eval-steward`.

### Current export path — PARTIAL (audit P1)

[`backend/app/services/export_service.py`](../../../backend/app/services/export_service.py)
(15 KB) and the export route accept arbitrary `results` rows from the
caller. The route does not require canonical record IDs and does not
verify that the rows belong to the referenced simulation. A caller can
submit:

```json
{
  "results": [
    { "respondent_id": "fake-1", "answer": "looks like a real answer", "evidence_score": 0.7 }
  ],
  "format": "csv"
}
```

and receive a CSV under the ASKTHEPEOPLE wordmark. The server cannot
prove those rows originated from the referenced simulation. The fields
`respondent_id` and `evidence_score` are also the exact terms the
prohibits in public APIs.

### Required correction (per audit)

The client should send canonical record IDs:

```json
{
  "response_ids": ["response_01", "response_02"],
  "format": "csv"
}
```

The server MUST:

1. Authorize the caller.
2. Retrieve canonical records.
3. Confirm they belong to the same attempt.
4. Generate the export.
5. Add the truth contract.
6. Add a provenance manifest.
7. Hash the output.
8. Record the export event.
9. Return an immutable export ID.

### Disclosure-block requirement

The Truth Rail disclosure block (see
§"Truth-preserving detached artifacts") MUST be rendered on every
exported file. CSV MUST add it as a fixed footer row; JSON MUST add it
as a top-level `_disclosure` field; PDF and DOCX MUST add a header and a
footer. The disclosure block MUST also be present in social-card and
email-template exports.

### Current per-simulation directory scan — PARTIAL (audit P2)

The simulation listing route enriches each simulation by scanning report
directories and opening metadata files. The audit's P2 finding "Nested
report-directory scans" identifies the O(simulation_count ×
report_directory_count) cost. Persisted indexed fields
(`simulation.latest_report_id`, `simulation.latest_report_status`,
`report.simulation_id`, `report.created_at`) are **TARGET**.

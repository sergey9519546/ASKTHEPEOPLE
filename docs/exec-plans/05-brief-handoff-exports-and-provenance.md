---
title: "Execution Plan 05 — Brief, Handoff, Exports, and Provenance"
status: "Operational"
version: "1.0.0"
owner: "Product + Content + Export Platform"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
---

# Execution Plan 05 — brief, handoff, exports, and provenance

## Objective

Turn validated structured paths into an editorial decision brief, safe
follow-up modes, a real-human research handoff, and truth-preserving detached
artifacts.

## Dependencies

- completed validated run;
- route grammar and content system;
- export/provenance ADR;
- use policy and claim registry.

## Workstreams

### A. Decision brief

Render in required order:

1. decision;
2. what this synthetic run surfaced;
3. possible paths;
4. what changed paths;
5. conflicts and missing information;
6. what this does not tell you;
7. questions to validate with people;
8. run record.

Limitations appear before diagnostics. No KPI cards or fake evidence scores.

### B. Route exploration

Implement map/list from the same schema. Add direct labels, equal route weights,
human-validation break, keyboard/touch behavior, mobile list default, and
comparison mode.

### C. Follow-up modes

Separate:

- explain the brief;
- generate fictional profile response;
- generate fictional group response.

Fictional response modes carry persistent labels and cannot appear as human
quotations.

### D. Decision-owner conclusion

Allow a named human owner to write a separate conclusion. AI editing occurs
only on request. Store original and revisions separately from the synthetic
brief.

### E. Human-research handoff

Generate:

- decision and purpose;
- assumptions requiring evidence;
- conflicting paths;
- disconfirming questions;
- participant/recruitment considerations without claiming representativeness;
- interview/workshop/survey/observation/pilot suggestions;
- instrument draft;
- evidence that would change the decision;
- blank human-findings section.

State that no validation occurred in the application.

### F. Export service

Support approved formats through canonical domain data. Add visible header and
footer, component-level labels, clipboard suffix, social card, machine metadata,
content hash, and manifest.

### G. Provenance

Generate signed manifest and optional C2PA assertions where supported. Make
clear that provenance is origin/integrity, not truth.

### H. Revocation

Share links and exports can be revoked after incident, deletion, policy breach,
or superseding correction. The audit record remains.

## Tests

- golden brief/export fixtures;
- route map/list parity;
- truth and terminology linter;
- clipboard and screenshot-context test;
- disclosure crop/strip adversarial test;
- PDF/print accessibility;
- CSV formula injection;
- manifest verification;
- share expiration/revocation;
- human handoff expert review.

## Acceptance evidence

- every brief section derives from approved structured objects;
- no citations imply source support for synthetic conclusions;
- every export has visible and machine-readable truth;
- fictional responses cannot be mistaken for human quotes;
- human-validation boundary remains external;
- handoff judged usable by independent researcher;
- C2PA/provenance language does not claim truth;
- exports revoke and delete correctly.

## Rollback

Disable generation of a faulty export type while preserving validated in-app
briefs. Restore prior template/release and revoke affected artifacts. Never
fall back to an export without disclosure or provenance validation.

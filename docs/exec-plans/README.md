---
title: "Execution Plans"
status: "Operational"
version: "1.0.0"
owner: "Program Lead + Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "Every milestone"
research_cutoff: "2026-07-29"
---

# Execution plans

These plans translate the normative documentation into dependency-ordered
delivery. They are living operational records. Completed work requires
evidence, not a checkbox or verbal claim.

## Execution standard

Each plan MUST maintain:

- objective and non-goals;
- current-state evidence;
- dependencies;
- work breakdown;
- data/schema/API changes;
- security/privacy/accessibility impact;
- evaluation and test requirements;
- migration and rollback;
- acceptance evidence;
- unresolved decisions and accountable owner.

## Order

| Plan | Outcome |
|---|---|
| [00](00-repository-census-and-governance.md) | Verified baseline, decision lock, and documentation governance |
| [01](01-truth-layer-and-foundations.md) | Product truth, terminology, design tokens, and domain invariants |
| [02](02-tenancy-data-and-secure-ingestion.md) | Tenant-safe data plane and hostile-document pipeline |
| [03](03-method-inputs-and-review.md) | Decision, conditions, assumptions, uncertainties, and profiles |
| [04](04-durable-orchestration-and-path-engine.md) | Versioned AI stages, durable runs, paths, and coverage |
| [05](05-brief-handoff-exports-and-provenance.md) | Decision brief, follow-up, research handoff, and detached truth |
| [06](06-security-privacy-observability-and-operations.md) | Production risk, privacy, telemetry, deletion, incident, and deployment controls |
| [07](07-evals-accessibility-and-release.md) | Comprehensive evaluation, comprehension, accessibility, and release proof |

Plan 00 gates all later plans. Plans 01 and 02 can proceed in parallel after
the census. Plans 03–05 are ordered. Plan 06 begins with Plan 00 and continues
through the program. Plan 07 begins early with test fixtures and completes last.

## Evidence repository

Store evidence under a release-specific path such as:

```text
artifacts/release/<release-id>/
├── manifests/
├── migrations/
├── tests/
├── evals/
├── accessibility/
├── security/
├── privacy/
├── visual-fidelity/
├── comprehension/
├── performance/
├── rollback/
└── approvals/
```

Production content MUST NOT be copied into this directory unless expressly
authorized and redacted.

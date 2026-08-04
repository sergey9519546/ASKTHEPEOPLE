---
title: "Execution Plans"
status: "Operational"
version: "1.1.0"
owner: "Program Lead + Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "Per gate; at minimum quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
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


---

## Project-specific implementation status (baseline `8b616dc7`)

This directory is the operational program for the 6-gate refactor.
All 8 numbered plans (00-07) plus this README are project-specific
at the current baseline.

**Owner:** The 8 plans are owned by the corresponding Mavis
specialist agents per [`AGENTS.md`](../../AGENTS.md). This README is
owned by `askthepeople-release-operator` and
`askthepeople-architect`.

**Current state at the baseline:** all 8 plans are **NOT STARTED**.
The first deliverable is the
[`00-repository-census-and-governance.md`](00-repository-census-and-governance.md)
census, which must run against the current baseline and produce a
per-aggregate divergence report from the doc-system baseline before
any work in any plan begins.

**Key file:line references:**

- The Flask application factory:
  [`backend/app/__init__.py:25`](../../backend/app/__init__.py:25).
- The Flask blueprint registration:
  [`backend/app/api/__init__.py:13-17`](../../backend/app/api/__init__.py:13).
- The partially decomposed simulation controller:
  [`backend/app/api/simulation.py`](../../backend/app/api/simulation.py)
  (read routes + shared helpers) and
  [`backend/app/api/routes/`](../../backend/app/api/routes/)
  (write/lifecycle handlers).
- The model layer:
  [`backend/app/models/project.py:18-310`](../../backend/app/models/project.py),
  [`backend/app/models/task.py:21-387`](../../backend/app/models/task.py).
- The service layer (largest files):
  [`backend/app/services/report_agent.py:1`](../../backend/app/services/report_agent.py) (114 KB),
  [`backend/app/services/simulation_runner.py:1`](../../backend/app/services/simulation_runner.py) (82 KB),
  [`backend/app/services/zep_tools.py:1`](../../backend/app/services/zep_tools.py) (76 KB).
- The task and Celery layer:
  [`backend/app/tasks/simulation_tasks.py:16`](../../backend/app/tasks/simulation_tasks.py:16),
  [`backend/app/celery_app.py:21`](../../backend/app/celery_app.py:21).
- The frontend:
  `frontend/src/` (Vue 3 + Vite + D3).
- The release evidence layout described above is **TARGET**; the
  current repository has no `artifacts/release/` directory.

**Evidence path:** the production-content exclusion rule is
preserved; reaching the contract requires the release evidence
directory and a per-release evidence bundle. Gate 4 + gate 5.

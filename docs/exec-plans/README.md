---
title: "Execution Plans"
status: "Operational"
version: "1.2.0"
owner: "Program Lead + Architecture Council"
last_reviewed: "2026-10-01"
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
| [08](08-harvest-framework-engineering-fixes.md) | Gate 1–3 accelerators harvested from the framework-engineering review |
| [09](09-source-material-workflow-improvements.md) | Source-material workflow: decision-only mode, URL ingestion, auto-research |

Plan 00 gates all later plans. Plans 01 and 02 can proceed in parallel after
the census. Plans 03–05 are ordered. Plan 06 begins with Plan 00 and continues
through the program. Plan 07 begins early with test fixtures and completes
last. Plans 08 and 09 are accelerators layered onto gates 1–3 and the
source-material workflow respectively; they depend on the plans whose work
they harvest (08 follows 03–05, 09 follows 05) and do not gate any plan.

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
All 10 numbered plans (00-09) plus this README are project-specific
at the current baseline.

**Owner:** The 8 plans are owned by the corresponding Mavis
specialist agents per [`AGENTS.md`](../../AGENTS.md). This README is
owned by `askthepeople-release-operator` and
`askthepeople-architect`.

**Current state (2026-10-01):** release gate status is recorded in exactly one
place — [`../architecture/index.md` § Status of record](../architecture/index.md#status-of-record).
Do not read gate status from this directory. Each plan below carries its own
`status:` front-matter field and a status-reconciliation block where one has
been re-verified against the code; those are the authoritative per-plan claims.

| Plan | `status:` | Note |
|---|---|---|
| [00](00-repository-census-and-governance.md) | Operational | Census run; see [`../archive/legacy-2026-07-29/README.md`](../archive/legacy-2026-07-29/README.md) for the baseline gap record |
| [01](01-truth-layer-and-foundations.md) | Operational | Truth contract now lives in ADR-0001; this plan is the historical path to it |
| [02](02-tenancy-data-and-secure-ingestion.md) | Operational | Partially landed; source ingestion is behind `SOURCE_INGESTION_V1_ENABLED` (`backend/app/config.py:232-233`) |
| [03](03-method-inputs-and-review.md) | Operational | Partially landed; behavioural modules ship but three have no production importer |
| [04](04-durable-orchestration-and-path-engine.md) | Operational | Partially landed; fenced leases and heartbeats are in `backend/app/models/task.py` |
| [05](05-brief-handoff-exports-and-provenance.md) | Operational | Partially landed; export provenance derives from canonical attempt records |
| [06](06-security-privacy-observability-and-operations.md) | Operational | Partially landed; gate 4 observability remains NOT STARTED |
| [07](07-evals-accessibility-and-release.md) | Operational | Partially landed; eval suite runs in CI, release gate closed |
| [08](08-harvest-framework-engineering-fixes.md) | Partially Delivered | 4 of 5 fixes done — see its status-reconciliation block |
| [09](09-source-material-workflow-improvements.md) | Partially Delivered | Tiers 1 and 2 shipped; Tier 3 not started |

Plans 00-07 are `status: "Operational"`, meaning "this is the procedure," not
"this is finished." An earlier revision of this README claimed all eight plans
were NOT STARTED; that was wrong and had been for some time.

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

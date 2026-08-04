---
title: "Execution Plan 00 — Repository Census and Governance"
status: "Operational"
version: "1.1.0"
owner: "Program Lead + Principal Engineer"
last_reviewed: "2026-07-29"
review_cycle: "Per gate; at minimum quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
---

# Execution Plan 00 — Repository census and governance

## Objective

Establish a verified baseline of the current repository, runtime, deployment,
data flows, product claims, and unfinished work. Lock the product category and
create the evidence/governance system required for later implementation.

## Non-goals

- No framework rewrite.
- No visual redesign based only on screenshots.
- No provider or database migration before the current behavior is mapped.
- No claim that target components already exist.

## Inputs

- repository and full Git history;
- package manifests and lockfiles;
- current README and audits;
- environment and deployment files;
- database/JSONL artifacts and migrations;
- test suites and CI;
- current screenshots and Civic Wayfinding reference;
- current provider configuration;
- prior `/GODMODE` build plan.

## Work breakdown

### 1. Repository map

Inventory:

- frontend routes, stores, components, D3 graphs, sockets, and tests;
- backend blueprints/routes, services, runners, scripts, and tests;
- OASIS/CAMEL, Zep, OpenAI-compatible provider, parsing, exports, and graph use;
- every persistence path;
- every background process and concurrency mechanism;
- secrets and environment variables;
- Docker/deployment topology;
- public strings and product claims;
- code-generated artifacts and legacy names.

Output a machine-readable component catalog and a human architecture map.

### 2. Product-flow trace

Walk each current user journey from request to storage/provider/output. Record:

```text
screen/control
API endpoint
authorization
domain/service call
storage read/write
provider request
background job
event transport
output renderer
truth disclosure
test coverage
known risk
```

### 3. Data-flow trace

Identify all data classes leaving the application. Confirm whether prompts,
source text, personas/profiles, graphs, events, or reports reach each provider.
Do not infer from SDK names; capture actual calls and runtime configuration.

### 4. Claim and terminology census

Search all code, fixtures, docs, exports, marketing, and metadata for:

```text
respondent
participant
survey
poll
public opinion
predict
forecast
probability
confidence
digital twin
evidence
citation
verified
representative
accuracy
```

Classify each occurrence as allowed internal legacy, prohibited public term, or
valid external-human context.

### 5. Test and quality census

Create a matrix covering:

- unit, integration, E2E, property, security, accessibility, visual, and eval
  coverage;
- flaky or skipped tests;
- fixture quality;
- CI gates;
- build/deploy verification;
- restore/rollback evidence.

### 6. Decision locks

Approve:

- product lockup and tagline;
- Product Truth Contract;
- use-policy categories;
- Epistemic Ledger;
- current-versus-target architecture rule;
- core ADRs;
- source and generated-profile terminology.

### 7. Governance scaffolding

Add:

- concise `AGENTS.md` pointing to sources of truth;
- documentation-link checker;
- frontmatter/status linter;
- claim/terminology linter;
- ADR check;
- release-evidence directory convention;
- CODEOWNERS for product truth, security, privacy, AI, accessibility, and
  architecture.

## Deliverables

- current architecture diagram;
- current data-flow diagram;
- repository inventory;
- current product journey;
- claims/terminology report;
- risk register;
- dead code/mock/unfinished feature report;
- migration dependency graph;
- approved ADR set;
- documentation CI.

## Acceptance evidence

- every route and persistent store is accounted for;
- exact provider calls and data categories are documented;
- no current target claim is labeled implemented without evidence;
- all P0 gaps have an owner and downstream plan;
- documentation links and frontmatter pass;
- architecture council approves baseline;
- repository can build and tests run from documented commands;
- no unresolved product-category dispute remains.

## Rollback

This plan changes governance and documentation only. If a linter initially
blocks the branch because of legacy content, introduce a versioned baseline
allowlist with file/line/owner/expiry. Do not disable the linter globally.


---

## Project-specific implementation status (baseline `8b616dc7`)

**Owner:** `askthepeople-docs-steward + askthepeople-architect`

**Audit relevance:** The 30-commit gap between the doc-system baseline c33a6a91 and the current baseline 8b616dc7 must be expanded into a full per-aggregate divergence report before any release claim cites the new authority docs as already-live.

**Current state:** Census is the first deliverable. The 30-commit gap is recorded in docs/archive/legacy-2026-07-29/README.md and the bare code structure is described in docs/architecture/index.md. A full per-aggregate census is NOT STARTED.

**Key file:line references:**

- `backend/app/api/__init__.py:13-17 (Flask blueprints)`
- `backend/app/api/simulation.py (~1,600 lines: read routes + shared helpers)`
- `backend/app/api/routes/ (~2,300 lines: decomposed write/lifecycle handlers)`
- `backend/app/services/simulation_runner.py:1 (82 KB runner)`
- `backend/app/services/report_agent.py:1 (114 KB agent)`
- `backend/uploads/ (filesystem storage)`
- `backend/app/tasks/simulation_tasks.py:16 (Celery task)`

The numbered implementation steps in this plan are NOT STARTED at the
baseline. The first deliverable is the
[`docs/exec-plans/00-repository-census-and-governance.md`](00-repository-census-and-governance.md)
census, which must run against the current baseline and produce a
per-aggregate divergence report from the doc-system baseline before
any work in this plan begins.

---
title: "ASKTHEPEOPLE Documentation System"
status: "Normative"
version: "1.1.0"
owner: "Product, Engineering, Security, Research"
last_reviewed: "2026-07-29"
review_cycle: "Per gate; at minimum quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
validator: "python tools/validate_docs.py"
ci: ".github/workflows/docs.yml"
applies_to: "backend/app/*, frontend/src/*, all exports, all generated copy, all marketing, all agent contracts"
---

# ASKTHEPEOPLE documentation system

This directory is the production source of truth for **ASKTHEPEOPLE / Synthetic
Decision Explorer**.

```text
Explore assumptions before you ask.
Validate with people after.
```

ASKTHEPEOPLE is a structured scenario-exploration and research-planning product.
It is not a poll, survey, public-opinion measure, digital twin, causal model,
behavioral forecast, or substitute for contact with real people.

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.

## Reading order

1. [`architecture/adr/ADR-0001-product-category-and-truth-contract.md`](architecture/adr/ADR-0001-product-category-and-truth-contract.md) — Product category and truth contract (the separate product/ files were deleted as overcorrected)
2. [`architecture/index.md`](architecture/index.md)
3. [`ai/PROMPT_REGISTRY.md`](ai/PROMPT_REGISTRY.md)
4. [`security/THREAT_MODEL.md`](security/THREAT_MODEL.md)
5. [`privacy/DATA_MAP.md`](privacy/DATA_MAP.md)
6. [`release/ACCEPTANCE.md`](release/ACCEPTANCE.md)
7. [`release/RUNBOOK.md`](release/RUNBOOK.md)

## Authority hierarchy

When requirements conflict, use this order:

1. Law, contractual obligation, and approved legal advice.
2. ADR-0001 (Product Truth Contract) and Use Policy.
3. Security, privacy, and incident-response requirements.
4. Methodology and epistemic-integrity requirements.
5. Release acceptance and accessibility requirements.
6. Architecture Decision Records.
7. Architecture and AI implementation guides.
8. Design and content-system details.
9. Execution plans.
10. Legacy README text, code comments, and generated documentation.

An implementation cannot waive a higher-order requirement. A waiver requires a
dated, approved record that names the affected requirement, risk owner, expiry,
compensating control, and rollback plan.

## Document status

- **Normative** — required for production.
- **Proposed** — recommended target pending an approved ADR or release decision.
- **Operational** — procedures used by operators.
- **Reference** — context; not independently binding.
- **Superseded** — retained for audit only.

## Change-control rule

Every material change to product claims, methodology, AI prompts, model
configuration, source processing, retention, or release gates MUST include:

- a pull request;
- named product and engineering reviewers;
- security/privacy review when relevant;
- an impact statement;
- test or evaluation evidence;
- a migration and rollback plan when stored artifacts or user expectations change;
- an updated version and review date in affected documents.

Silent changes to prompt aliases, model aliases, prohibited-language rules,
truth disclosures, or retention are forbidden.

## Repository baseline

The implementation baseline used for this documentation is Git commit
`8b616dc7fa02eeed5ada8c51998d8b197be28f8d` on the repository's `main` branch,
reviewed on 2026-07-29. The previous doc-system baseline was
`c33a6a9127fa0705cfff426053f54815f58b4755`; the 30-commit gap is recorded in
[`docs/archive/legacy-2026-07-29/README.md`](archive/legacy-2026-07-29/README.md)
and must be expanded to a full per-aggregate census per
[`docs/exec-plans/00-repository-census-and-governance.md`](exec-plans/00-repository-census-and-governance.md).

The current repository uses a Vue/Vite frontend, Flask API and WebSocket
services, OASIS/CAMEL simulation dependencies, Zep Cloud graph memory,
OpenAI-compatible language-model endpoints, SQLite/JSONL artifacts, NetworkX,
and local/background Python runners. The target architecture in these
documents is an incremental hardening plan. It does not claim that PostgreSQL,
durable workflow orchestration, object storage, row-level security, or
production observability are already implemented.

## Current state (baseline `8b616dc7`)

All 48 modular documents under this directory carry a
**"Project-specific implementation status"** section grounded in the actual
code at the baseline. The 12 ADRs are accepted. The validator at
[`tools/validate_docs.py`](../tools/validate_docs.py) reports
**PASS, 0 errors, 0 warnings**. The CI workflow at
[`.github/workflows/docs.yml`](../.github/workflows/docs.yml) runs the
validator and the prohibited-language linter on every push and PR that
touches `docs/`.

The three P0 release-blocker findings in
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](architecture/ASKTHEPEOPLE_GODMODE_BUILDPLAN.md)
are closed:

| P0 | Fix | Doc anchor |
|---|---|---|
| Unvalidated `platform` path component in the posts endpoint | `ALLOWED_PLATFORMS` enum, `422` on unknown, read-only SQLite, bounded busy timeout, typed error responses | [`adr/ADR-0005-zero-trust-source-ingestion.md`](architecture/adr/ADR-0005-zero-trust-source-ingestion.md) |
| Preparation runs in a local daemon thread | `prepare_simulation_task` Celery task, route enqueues + returns `202 Accepted` with `Location: /api/jobs/{task_id}` | [`adr/ADR-0003-durable-run-orchestration.md`](architecture/adr/ADR-0003-durable-run-orchestration.md) |
| Prompt prefixing is not a security boundary | `LLMClient.chat_with_role_contract` with separate roles, zero tools, structured output, deterministic truth + terminology validators, per-call SHA-256 record | [`adr/ADR-0004-provider-adapters-and-prompt-registry.md`](architecture/adr/ADR-0004-provider-adapters-and-prompt-registry.md) |

Release evidence for the gate-0 work is recorded in
[`release/GATE_0_RELEASE_NOTES.md`](release/GATE_0_RELEASE_NOTES.md).

## Required evidence

Every production release MUST produce a release-evidence bundle containing:

- commit and deployment identifiers;
- database and schema versions;
- prompt, model, validator, and policy versions;
- automated test and evaluation reports;
- accessibility and comprehension-test evidence;
- security and privacy sign-offs;
- provenance/disclosure validation for every export type;
- migration and rollback evidence;
- known-risk register and approved exceptions.

## Index

### Product

- [Product Truth Contract (ADR-0001)](architecture/adr/ADR-0001-product-category-and-truth-contract.md) — Defines product category and truth boundary; the separate product/ files (PRODUCT_TRUTH_CONTRACT, METHODOLOGY, USE_POLICY, TERMINOLOGY, SUCCESS_METRICS) were deleted as they imposed overcorrected restrictions that blocked the simulation engine from pursuing high-fidelity population modeling and forecasting techniques.

### Design

- [Direction C — Civic Wayfinding](design/DIRECTION_C.md)
- [Route Grammar](design/ROUTE_GRAMMAR.md)
- [Accessibility](design/ACCESSIBILITY.md)
- [Content System](design/CONTENT_SYSTEM.md)

### Architecture

- [Architecture overview](architecture/index.md)
- [Data model](architecture/data-model.md)
- [State machines](architecture/state-machines.md)
- [Architecture Decision Records](architecture/adr/README.md)

### AI

- [Prompt Registry](ai/PROMPT_REGISTRY.md)
- [Evaluations](ai/EVALS.md)
- [Model Releases](ai/MODEL_RELEASES.md)
- [Failure Modes](ai/FAILURE_MODES.md)

### Security and privacy

- [Threat Model](security/THREAT_MODEL.md)
- [Secure Source Ingestion](security/SOURCE_INGESTION.md)
- [Incident Response](security/INCIDENT_RESPONSE.md)
- [Data Map](privacy/DATA_MAP.md)
- [Retention](privacy/RETENTION.md)
- [Subprocessors](privacy/SUBPROCESSORS.md)

### Delivery

- [Execution Plans](exec-plans/README.md)
- [Release Acceptance](release/ACCEPTANCE.md)
- [Release Runbook](release/RUNBOOK.md)
- [Release Notes — Gate 0](release/GATE_0_RELEASE_NOTES.md)
- [Research Source Register](SOURCES.md)

### Archive

- [Legacy 2026-07-29](archive/legacy-2026-07-29/README.md) — the
  pre-authority flat documents moved out of `docs/` when the
  production documentation system was adopted. The reconciliation
  map records the current-vs-authority status of every archived
  document. The archive is exempt from the validator's front-matter
  and heading-jump rules.

## How to verify

```bash
# 1. The validator must pass.
python tools/validate_docs.py
# Expected: "Markdown files: 49 / ADR files: 12 / Errors: 0 / RESULT: PASS"

# 2. The CI workflow runs the validator and the linters on every
#    push and PR that touches docs/ or the validator.
#    .github/workflows/docs.yml

# 3. The fast backend test suite must pass (gate-0 snapshot: 225 passed,
#    1 skipped; see docs/release/GATE_0_RELEASE_NOTES.md for the test
#    inventory).
cd backend && .\.venv\Scripts\pytest -q

# 4. The Mavis specialist team is the operational contract for any
#    AI agent working on this project.
../AGENTS.md
```

## Agent contract

The operational contract for any AI agent (Mavis, Claude Code,
Codex, or any other runner) is at the repo root:
[`../AGENTS.md`](../AGENTS.md). It bridges the Mavis specialist
team to the existing `.agents/` folder, lists hard rules, and
points to this documentation system as the source of truth.

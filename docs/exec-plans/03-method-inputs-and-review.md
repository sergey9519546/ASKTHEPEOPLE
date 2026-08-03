---
title: "Execution Plan 03 — Method Inputs and Review"
status: "Operational"
version: "1.1.0"
owner: "Research + Product + Frontend/Domain Leads"
last_reviewed: "2026-07-29"
review_cycle: "Per gate; at minimum quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
---

# Execution Plan 03 — method inputs and review

## Objective

Implement the reviewed input model: actionable decision, starting conditions,
assumptions, critical uncertainties, generated profiles/decision lenses, and
the immutable “Check this run” gate.

## Dependencies

- truth layer and terminology;
- tenant data model and source segments;
- use-policy engine;
- prompt registry and eval harness skeleton.

## Workstreams

### A. Decision intake

Implement required fields and decision-quality review. The model proposes
edits; user text is never silently overwritten. Block ambiguous multi-decision
questions and prohibited intended uses.

### B. Source-to-condition ledger

Build the review ledger with:

```text
source location
candidate condition
system interpretation
ambiguity/conflict
accept/edit/assumption/reject
```

Source map is optional and never the default proof interface.

### C. Assumption register

Support categories, falsifiers, validation methods, review status, sensitivity,
and scope. Generated assumptions are proposals.

### D. Critical uncertainties

Allow selection of two to four uncertainties with two to four materially
different states. Provide duplicate/overlap detection and explain why each
could change the decision.

### E. Generated profiles / decision lenses

Implement structured fields only: constraints, incentives, access,
information, switching costs, and criteria. Remove or hide legacy names,
avatars, biographies, and first-person quotes.

Add profile-integrity validation and sensitive-attribute review.

### F. Coverage plan

Before generation, create a coverage matrix mapping selected uncertainty states,
profiles, and scenario rules to candidate paths. The matrix has no
probabilities.

### G. Check this run

Create an editorial review page summarizing:

- decision and intended use;
- source versions and approved conditions;
- assumptions and falsifiers;
- selected uncertainties/states;
- generated profiles;
- scenario rules;
- policy and truth statements;
- model/provider data-transfer notice.

The user explicitly approves the configuration. Starting a run freezes a
content hash.

### H. Revision semantics

A material edit after approval creates a new decision/configuration version.
Existing completed runs remain unchanged.

## AI stages

Implement and evaluate S00–S07 only:

- policy proposal;
- decision review;
- condition extraction/conflict review;
- assumption gaps;
- uncertainties;
- profiles;
- scenario candidates.

Each stage has bounded inputs, schemas, validators, and review.

## Comprehension research

Test whether users understand:

- source role;
- assumption vs condition;
- profile vs real person;
- uncertainty state vs prediction;
- what will be frozen;
- why human validation is still required.

## Acceptance evidence

- blocked decisions cannot start a run;
- every generated input is visibly a proposal until approved;
- profiles contain no prohibited personification;
- coverage matrix is complete;
- check page and configuration hash match;
- edits create a new version;
- sensitive-attribute cases require review;
- comprehension thresholds pass;
- stage evals and human research review pass.

## Rollback

The new input model may be feature-flagged. Legacy persona-based runs remain
read-only and labeled legacy. New runs cannot fall back to unreviewed persona
generation.


---

## Project-specific implementation status (baseline `8b616dc7`)

**Owner:** `askthepeople-architect + askthepeople-ai-eval-steward`

**Audit relevance:** Strict request schemas (Pydantic with extra=forbid), the Epistemic Ledger, the policy engine, the decision-review state machine. Gate 1 work.

**Current state:** Pydantic is in use (config.py and model files) but the request schemas are not strict. The Epistemic Ledger is NOT IMPLEMENTED. The policy engine is NOT IMPLEMENTED. The decision-review state machine is NOT IMPLEMENTED.

**Key file:line references:**

- `backend/app/config.py (Pydantic config)`
- `backend/app/services/claim_boundary.py:1 (3 KB claim boundary)`
- `backend/app/services/validation_engine.py:1 (14 KB validation engine)`

The numbered implementation steps in this plan are NOT STARTED at the
baseline. The first deliverable is the
[`docs/exec-plans/00-repository-census-and-governance.md`](00-repository-census-and-governance.md)
census, which must run against the current baseline and produce a
per-aggregate divergence report from the doc-system baseline before
any work in this plan begins.

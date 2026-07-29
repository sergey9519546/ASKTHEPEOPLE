---
title: "Execution Plan 01 — Truth Layer and Foundations"
status: "Operational"
version: "1.0.0"
owner: "Product Truth Lead + Frontend/Domain Leads"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
---

# Execution Plan 01 — Truth layer and foundations

## Objective

Make the Product Truth Contract impossible to bypass in core schemas, APIs,
interface copy, exports, and tests. Establish Direction C tokens and accessible
component primitives before feature expansion.

## Dependencies

- Plan 00 baseline and ADR approval.
- Approved product lockup and terminology.
- Agreed Vue/Flask migration strategy.

## Workstreams

### A. Domain invariants

Create central enums and validators for:

- synthetic origin;
- human respondent count zero;
- non-forecast status;
- external human-validation scope;
- epistemic origins, roles, and relations;
- prohibited claim language;
- immutable completed runs.

Add database constraints where the current store allows them and domain checks
for all writes. Define target PostgreSQL migrations in parallel.

### B. API contracts

Add explicit truth fields to run, brief, export, and share payloads. Remove or
deprecate ambiguous public fields. Generate OpenAPI and contract tests.

Legacy compatibility responses MUST retain the truth fields and deprecation
warnings.

### C. Truth Rail and contextual copy

Implement a non-dismissible Truth Rail in the app shell and one contextual
statement per workflow screen. It must:

- appear early in DOM order;
- remain visible without obscuring focus;
- collapse to two readable mobile lines;
- never be a dismissible banner;
- survive print and screenshots.

### D. Design tokens

Create code-owned tokens for:

- charcoal, paper, transfer white, signal yellow, teal, orange, error colors;
- typography roles;
- spacing, rule thickness, focus treatment, motion timing;
- sharp geometry and surface semantics;
- z-index and sticky offsets.

Migrate components incrementally. Do not add a generic card system that
contradicts Direction C.

### E. Content linter

Lint:

- source strings;
- generated fixtures;
- export templates;
- API descriptions;
- analytics event names;
- documentation and marketing.

Support contextual allowlists only for policy text that explains a prohibited
term. Every allowlist item has owner and expiry.

### F. Core accessible primitives

Implement and test:

- button/link/input/textarea/select/checkbox/radio;
- error summary and field error;
- disclosure;
- modal and nonmodal inspector;
- step navigation;
- Truth Rail;
- status message;
- route/list tabs;
- data table;
- notification/status region.

### G. Detached-content disclosure

Add reusable disclosure components and metadata serializers for:

- clipboard;
- print;
- PDF/Markdown/JSON prototypes;
- social preview;
- share link.

## Data and migration

Add explicit truth columns to existing run/artifact records. Migration must:

- set historical synthetic runs to the locked values;
- identify artifacts whose origin cannot be established;
- mark unverifiable legacy artifacts as `LEGACY_UNVERIFIED`;
- prevent those artifacts from being exported as current briefs;
- record migration evidence.

## Tests

- property tests for truth invariants;
- API contract tests;
- snapshot tests for Truth Rail states;
- keyboard/focus tests;
- mobile and 200% zoom visual tests;
- terminology corpus;
- clipboard/export disclosure tests;
- migration reconciliation.

## Acceptance evidence

- invariant bypass attempts fail from API, worker, admin, and migration paths;
- all primary screens have correct truth copy;
- no focus is obscured by sticky elements;
- zero critical/high terminology findings;
- all detached artifact prototypes preserve disclosure;
- historical migration is reconciled;
- Direction C component catalog and reference screenshots exist;
- product-truth and accessibility owners approve.

## Rollback

Feature-flag the new shell by organization only during internal migration.
Database truth fields are forward-only and must not be rolled back to ambiguous
states. UI rollback may return to the prior layout only if the Truth Rail and
truth fields remain.

---
title: "Execution Plan 07 — Evals, Accessibility, and Release"
status: "Operational"
version: "1.0.0"
owner: "Release Lead + QA + Research + Accessibility"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
---

# Execution Plan 07 — evals, accessibility, and release

## Objective

Produce the evidence required to release the product without unresolved truth,
methodology, AI, security, privacy, accessibility, reliability, or visual
quality defects.

## Workstreams

### Test architecture

Implement unit, property, integration, contract, workflow, E2E, visual,
accessibility, security, performance, chaos, and restore suites. Replace weak
fixtures with realistic bounded cases.

### AI evaluations

Run every stage suite against exact prompt/model/schema/validator releases.
Compare candidate and active releases. Complete human expert review and
adversarial testing.

### Comprehension research

Moderated studies cover:

- synthetic origin and zero human respondents;
- not a forecast;
- source role;
- profiles are not people;
- route geometry has no likelihood meaning;
- run records are not citations;
- human validation is external.

No recurring critical misunderstanding is acceptable.

### Accessibility

- WCAG 2.2 AA audit;
- automated scan;
- keyboard;
- NVDA, VoiceOver, TalkBack;
- 320px and zoom/reflow;
- reduced motion;
- focus not obscured;
- route map/list parity;
- accessible exports.

### Visual fidelity

Compare the accepted Direction C reference and implementation. Maintain a
fidelity ledger for typography, color, geometry, hierarchy, surface semantics,
route grammar, content, responsive behavior, and motion.

### Performance and reliability

- representative load;
- API and event SLOs;
- workflow backlog/recovery;
- provider degradation;
- upload limits;
- export rendering;
- backup/restore;
- cost ceilings.

### Release evidence and review

Assemble the release bundle, run the acceptance checklist, resolve P0/P1 issues,
obtain named approvals, execute canary, monitor, and complete post-release
verification.

## Pilot and beta research thresholds

Pilot:

- at least eight moderated participants across relevant user roles;
- zero critical truth misunderstanding;
- all observed route-semantic misunderstandings corrected before beta.

Beta:

- at least twenty moderated participants;
- ≥95% correctly identify outputs as synthetic;
- ≥95% state zero human respondents;
- ≥95% state not a forecast;
- ≥90% understand source material does not validate outcomes;
- ≥95% understand human validation is external;
- zero users act on route color/width/order as likelihood after completing the
  tested workflow.

Sample sizes are product research gates, not statistical guarantees.

## Release blockers

- any Product Truth Contract breach;
- any prohibited-use escape in critical corpus;
- any hallucinated source location;
- any cross-tenant failure;
- any export missing disclosure;
- any unresolved P0/P1 accessibility or workflow defect;
- any unapproved severe AI regression;
- any active provider without completed privacy/security record;
- inability to rollback or restore;
- any recurring critical comprehension misunderstanding.

## Acceptance evidence

The complete evidence bundle satisfies
[`release/ACCEPTANCE.md`](../release/ACCEPTANCE.md), and the deployment follows
[`release/RUNBOOK.md`](../release/RUNBOOK.md). No team may declare completion
from build/test success alone.

## Rollback

Canary rollback is rehearsed before promotion. A post-release critical failure
activates the relevant kill switch and restores the last approved application,
prompt, model, validator, template, or policy release while preserving audit
history.

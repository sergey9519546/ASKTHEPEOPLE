---
title: "ADR-0007: External human-validation boundary"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
---
# ADR-0007: External human-validation boundary

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

The product can generate questions for human research but does not recruit or
measure people. Allowing a synthetic run to transition into a state named
“validated” would overstate evidence and blur the distinction between generated
paths and empirical findings.

## Decision

The synthetic workflow terminates at `Prepare human validation`. It produces a
research handoff. No synthetic run can have human-validation status
`COMPLETED`. A later external human-evidence module, if built, is a separate
workflow, evidence class, permission set, and method record.

## Consequences

The application cannot market a one-click validation loop. Real research
requires recruitment, consent/privacy procedures, field dates, instruments,
analysis, and accountable human judgment. This boundary increases integrity and
creates a clear future integration contract.

## Alternatives considered

1. Embed a synthetic “validation agent.” Rejected.
2. Mark internal consistency as validation. Rejected.
3. Integrate a real research panel immediately. Deferred; such a module requires
   separate operational, ethical, privacy, and methodological design.

## Verification

State-machine constraint; export wording test; handoff usability review; zero
synthetic runs with completed human validation.

## References

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) — Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [OECD Strategic Foresight Toolkit for Resilient Public Policy](https://www.oecd.org/en/publications/foresight-toolkit-for-resilient-public-policy_bcdd9304-en.html) — Scenario and stress-testing guidance that treats disruptions and alternative futures as hypothetical, not predictions.

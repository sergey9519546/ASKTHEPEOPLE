---
title: "ADR-0007: External human-validation boundary"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "all gates; this ADR is a permanent constraint"
applies_to: "all run lifecycle states, all report sections, all exports, the research handoff"
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

## Project-specific implication (baseline `8b616dc7`)

This ADR is enforced by the
[`docs/product/PRODUCT_TRUTH_CONTRACT.md`](../../product/PRODUCT_TRUTH_CONTRACT.md)
truth invariants:

```text
run.humanRespondentCount MUST equal 0
run.isForecast MUST equal false
run.outputOrigin MUST equal "synthetic"
run.humanValidationStatus MUST NOT become "completed" inside the synthetic workflow
```

The data invariants are **TARGET** — the current code does not yet
store these fields as non-nullable columns with database CHECK
constraints. The text disclosures are already present in the
contract, in the README, and in the report. The handoff
content (questions for human validation) is produced by
[`services/report_agent.py`](../../../backend/app/services/report_agent.py)
(114 KB).

### Terminal-state constraint

The state machines in
[`docs/architecture/state-machines.md`](../state-machines.md) include
"Prepare human validation" as a terminal state for the synthetic
workflow. A run reaching this state MUST NOT be re-entered; a new
external human-evidence module, if built, is a separate workflow,
evidence class, permission set, and method record.

### No silent transition into "validated"

The audit's P1 finding "Contradictory lifecycle semantics" identifies
the present risk: a `close_environment` route marks the simulation
`COMPLETED` regardless of outcome. Reaching this ADR requires that
the close route cannot mark a synthetic run as validated. The fix
lands with the durable workflow in gate 2 (see
[`adr/ADR-0003-durable-run-orchestration.md`](ADR-0003-durable-run-orchestration.md))
and the canonical persistence layer in gate 3.

### External human-evidence module — out of scope for v1

If a future module imports external human findings, the
`EXTERNAL_HUMAN_EVIDENCE` origin in the Epistemic Ledger
([`adr/ADR-0002-epistemic-ledger.md`](ADR-0002-epistemic-ledger.md))
is the typed edge. The module MUST NOT mutate, complete, or
re-enter any synthetic run; it MUST store findings in a separate
aggregate, with a separate permission set, a separate method
record, and a separate UI surface.

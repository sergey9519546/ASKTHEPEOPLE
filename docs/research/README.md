---
title: "Research Documents"
status: "Normative Reference"
version: "1.0.0"
created: "2026-08-18"
owner: "askthepeople-architect + askthepeople-ai-eval-steward"
last_reviewed: "2026-08-18"
---

# Research Documents

This directory contains the normative reference documents for ASKTHEPEOPLE's
synthetic decision-exploration methodology, profile system, scenario rules, and
starting-conditions protocol.

## Documents

| Document | Purpose | Status |
|---|---|---|
| [`synthetic-decision-lenses.md`](synthetic-decision-lenses.md) | Comprehensive library of 24 decision lenses with schema, design rules, and anti-patterns | Normative Reference v1.0.0 |
| [`scenario-rules.md`](scenario-rules.md) | Channel architecture, timing, participation rules, conflict resolution, stop conditions, path branching, cross-path analysis, disconfirmation protocol | Normative Reference v1.0.0 |
| [`starting-conditions.md`](starting-conditions.md) | Initialization protocol from decision intake through run manifest freeze, with template catalog | Normative Reference v1.0.0 |
| [`persona-depth-analysis.md`](persona-depth-analysis.md) | Analysis of whether to expand persona complexity; tiered depth strategy | Analysis v1.0.0 |
| [`big-five-integration.md`](big-five-integration.md) | Big Five personality model integration for behavioral coupling | Reference |
| [`demographic-data-sources.md`](demographic-data-sources.md) | Demographic data sources for profile generation | Reference |
| [`temporal-simulation-architecture.md`](temporal-simulation-architecture.md) | Temporal simulation architecture for multi-stage runs | Research |

## Quick Reference

### Profile Selection

- **Minimum viable set:** GP-01, GP-02, GP-07, GP-24
- **Standard set (6-8):** Add based on decision context (see profile doc)
- **Deep analysis (10-12):** Include edge-condition and challenger lenses

### Pre-Run Checklist (Step 04)

```bash
python tools/check_assumptions_before_continuing.py \
    --manifest backend/uploads/simulations/{id}/manifest.json \
    --profiles backend/app/services/fixtures/synthetic_decision_lenses.json
```

### Truth Contract Reminder

All profiles, scenarios, and runs MUST carry:
- `output_origin: "synthetic"`
- `human_respondent_count: 0`
- `is_forecast: false`
- `is_public_opinion_measure: false`
- `is_causal_evidence: false`

No profile may claim to represent, measure, predict, or validate any real person or population.

## References

- [`docs/product/METHODOLOGY.md`](../product/METHODOLOGY.md) — Methodological framework
- [`docs/product/PRODUCT_TRUTH_CONTRACT.md`](../product/PRODUCT_TRUTH_CONTRACT.md) — Claim boundary and truth invariants
- [`docs/architecture/index.md`](../architecture/index.md) — System architecture

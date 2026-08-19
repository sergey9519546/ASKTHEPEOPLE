---
title: "ADR-0001: Product category and truth contract"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "all gates; this ADR is the framing decision"
applies_to: "all product copy, all generated output, all exports, all marketing"
---
# ADR-0001: Product category and truth contract

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

The current name can imply that the application already asked people, while the
system actually generates model-based profiles, actions, and reports. The
current repository explicitly states that there are zero human respondents and
that outputs are not surveys, public-opinion measures, forecasts, predictions,
or digital twins. A visual disclaimer alone is insufficient because product
names, exports, API consumers, and screenshots can remove context.

## Decision

Classify ASKTHEPEOPLE as a **Synthetic Decision Explorer** for structured
scenario exploration and research planning. Bind the wordmark to the descriptor
and tagline. Enforce the Product Truth Contract in domain schemas, UI,
generated output, exports, analytics, and marketing.

The synthetic workflow has immutable facts: human respondent count equals zero,
output origin is synthetic, the run is not a forecast, sources inform starting
conditions only, and human validation occurs outside the run.

## Consequences

This decision narrows near-term market claims but produces a defensible product.
The team cannot market synthetic actor counts as sample size or output
agreement as public support. Product work must include claim linting,
comprehension testing, and truth-preserving exports. Any future human-research
module must remain separately typed and documented.

## Alternatives considered

1. Continue as a “crowd intelligence simulation engine.” Rejected because it
   suggests population representation and forecasting without evidence.
2. Rename to a generic AI research product. Potentially valid, but not required
   if the current name is always bound to the descriptor.
3. Rely on terms-of-service disclaimers. Rejected because truth must be visible
   during the workflow and in detached artifacts.

## Verification

Automated invariant tests; terminology linter; export validation; moderated
truth-comprehension study; marketing claim review.

## References

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) — Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.

## Project-specific implication (baseline `8b616dc7`)

This ADR defines the product category and truth contract inline (the separate
`docs/product/PRODUCT_TRUTH_CONTRACT.md` file was deleted as it imposed
overcorrected restrictions that prevented the simulation engine from pursuing
high-fidelity population modeling, forecasting, and calibration techniques).

The truth boundary is operationalized by the prohibited-language linter in
[`.github/workflows/docs.yml`](../../../.github/workflows/docs.yml).

Key file:line references:

- The naked ASKTHEPEOPLE wordmark is currently visible alone in
  legacy route names
  ([`audit P2`](../../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md#5-release-blocking-findings)):
  `/interview`, `/interview/all`, `/interview/batch`, `/opinions`,
  `/export/survey`, and the `interviews_count`,
  `export_survey_results` fields. These will receive the deprecation
  header per the audit when gate 1 lands.
- The Truth Rail and per-screen contextual statements are **not yet
  rendered** in `frontend/src/`. The frontend is a Vue 3 + Vite + D3
  application and the Civic Wayfinding design system
  ([`docs/design/DIRECTION_C.md`](../../design/DIRECTION_C.md)) is
  implemented in CSS and SVG only. The Truth Rail is gate 5 / exec
  plan
  [`docs/exec-plans/05-brief-handoff-exports-and-provenance.md`](../../exec-plans/05-brief-handoff-exports-and-provenance.md).
- The disclaimer text in [`README.md:9-12`](../../../README.md) is the
  current strongest in-repo embodiment of the lockup:
  > "Human respondents: 0. Evidence type: synthetic. Not a survey,
  > public-opinion measure, forecast, prediction, or digital twin."

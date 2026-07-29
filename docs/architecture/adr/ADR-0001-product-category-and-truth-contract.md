---
title: "ADR-0001: Product category and truth contract"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
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

---
title: "ADR-0006: Route map/list semantic parity"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
---
# ADR-0006: Route map/list semantic parity

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

The civic-wayfinding visual metaphor is useful but can exclude screen-reader,
keyboard, low-vision, mobile, print, and cognitively diverse users. SVG geometry
can also imply unsupported probability or evidence.

## Decision

The semantic route list is the source of truth. The SVG map is a synchronized
visual representation generated from the same typed data. All path information
and actions are available in the list. Route geometry follows the Route Grammar
and carries no quantitative meaning.

## Consequences

The implementation must maintain parity tests and cannot optimize only for a
visual canvas. Mobile defaults to the list. Visual complexity is constrained,
which improves comprehension and export quality.

## Alternatives considered

1. SVG-only visualization with alt text. Rejected because a single alternative
   description is not equivalent to an interactive multi-path structure.
2. Separate map and list implementations. Rejected due to semantic drift.
3. Remove the map entirely. Not chosen because the metaphor adds value when
   bounded and accessible.

## Verification

Schema-to-list/map snapshot tests, keyboard and screen-reader tests, mobile
reflow review, and comprehension tests for route semantics.

## References

- [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/) — Current accessibility conformance target for the product.
- [ONS Service Manual — Using colours in charts](https://service-manual.ons.gov.uk/data-visualisation/colours/using-colours-in-charts) — Color restraint, contrast, and non-color redundancy for data and route visualization.

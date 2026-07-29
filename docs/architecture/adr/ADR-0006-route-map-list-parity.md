---
title: "ADR-0006: Route map/list semantic parity"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "1 (typed API boundary) and 5 (comprehension testing)"
applies_to: "frontend/src/, all generated route content, all exports"
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

## Project-specific implication (baseline `8b616dc7`)

The Civic Wayfinding design direction
([`docs/design/DIRECTION_C.md`](../../design/DIRECTION_C.md)) is
implemented in CSS and SVG. The semantic route list required by this
ADR is **TARGET**.

### Current state — PARTIAL

- Frontend is a Vue 3 + Vite + vue-router + Pinia application
  served by
  [`backend/app/__init__.py:317-325`](../../../backend/app/__init__.py:317)
  from `frontend/dist/`.
- Route visualization uses D3 to render paths from a JSON
  configuration; the design is documented in
  [`docs/design/ROUTE_GRAMMAR.md`](../../design/ROUTE_GRAMMAR.md).
- The semantic route list as a first-class accessible alternative
  is **not yet rendered**. There is no parity test asserting that
  every fact and action in the visual map is reachable in the list
  by keyboard and screen reader.
- The Route Grammar document calls out the qualitative-only
  constraint ("Line width, color, position, spacing, order, count
  and placement never communicate probability, support,
  prevalence, confidence, or rank") but there is no automated
  check enforcing it on rendered SVG.

### Required correction (per this ADR and the design docs)

- A canonical semantic route list at the API or JSON-LD level
  that the visual map and the list view both consume.
- A parity test in CI that asserts every node, edge, and action
  in the visual map has a corresponding list entry, and vice
  versa.
- Keyboard-only navigation of every map fact and action.
- Screen-reader-only navigation of every map fact and action.
- Mobile-defaults to the list.
- Color/contrast conformance per WCAG 2.2 (see
  [`docs/design/ACCESSIBILITY.md`](../../design/ACCESSIBILITY.md)).
- A comprehension-test program that confirms users understand
  that route geometry carries no quantitative meaning.

Owned by `askthepeople-frontend-steward`, gate 1 (API) and gate 5
(comprehension testing).

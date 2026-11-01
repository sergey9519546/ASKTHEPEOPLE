---
title: "Rig-aligned simulation workspace proposal"
status: "Proposed"
version: "0.1.0"
owner: "Product + Frontend + Accessibility"
last_reviewed: "2026-11-01"
review_cycle: "Before implementation or material direction change"
research_cutoff: "2026-11-01"
---

# Rig-aligned simulation workspace proposal

## Scope and provenance

**TRANSITION:** this records the design direction produced by workflow
`dwfrun-fc14b217-0833-4f6c-9b88-e5e627a84a71` against commit `823549f`, with
coordinator corrections from subsequent source inspection. The workflow's
primary deliverable is titled *Rig-aligned simulation workspace proposal*.
This document is a corrected integration summary, not a verbatim artifact export.
It is a proposal, not implemented UX or acceptance evidence.

Read [Direction C](DIRECTION_C.md), [Accessibility](ACCESSIBILITY.md),
[Content System](CONTENT_SYSTEM.md), and
[ADR-0006](../architecture/adr/ADR-0006-route-map-list-parity.md) as governing
requirements. This proposal supersedes none of them. The original Rig reference
was supplied locally; its commercial fonts and assets are not licensed by this
proposal for copying or redistribution. Generic glassmorphism and the earlier
Liquid Data direction are excluded.

## Recommended direction

**TARGET:** organize the simulation workspace around three clear functions:
preparation/navigation, recorded activity, and selected-record inspection.
These are information zones, not a requirement to force three columns on every
screen. Retain the existing shell and its focus/split/free layouts. On small
screens, make activity and inspection sequential views with predictable focus
return rather than compressed side-by-side panels.

Use ink/paper fields, precise rules, strong editorial headings, and restrained
signal-red wayfinding. Keep the currently loaded Staatliches/Barlow fonts for the
first slice. Any move to the documented Archivo Narrow/Source Sans 3 pairing
requires separate dependency, licensing, layout and accessibility review.
Do not import Rig's marketing hero or continuous decorative animation into a
working research interface.

The permanent Truth Rail remains shell-owned and non-dismissible. Generated
records are not human observations, forecasts, agreement measurements, purchase
likelihoods, or validation of a business decision. Source relationships must not
be redrawn as action dependencies or real-world causal relationships.

## Verified source boundaries and corrections

| Status | Source finding | Evidence |
|---|---|---|
| CURRENT | Loaded fonts are Staatliches and Barlow. | [`design-tokens.css`](../../frontend/src/assets/design-tokens.css), font imports |
| CURRENT | The shell owns the Truth Rail; journey navigation and the panel tablist have distinct keyboard semantics. | [`DesktopShell.vue`](../../frontend/src/components/DesktopShell.vue), [`DesktopDock.vue`](../../frontend/src/components/DesktopDock.vue), [`DesktopTaskbar.vue`](../../frontend/src/components/DesktopTaskbar.vue) |
| CURRENT | Simulation WebSocket state frames are emitted on a two-second polling loop and include at most ten recent actions. This is a bounded snapshot, not complete delivery. | [`ws.py`](../../backend/app/api/ws.py), `_SIM_POLL_INTERVAL`, `_MAX_RECENT_ACTIONS`, `_simulation_state_frame`, `simulation_ws` |
| PARTIAL | Client action identity prefers a server ID but falls back to a composite containing the incoming array index. Stable cross-snapshot identity is not established by that fallback. | [`Step3Simulation.vue`](../../frontend/src/components/Step3Simulation.vue), `actionIdentity`, `mergeActions` |
| CURRENT | Initial saved-action loading exists; it must be traced with server pagination/retention before claiming complete replay. | [`Step3Simulation.vue`](../../frontend/src/components/Step3Simulation.vue), `loadSavedActions` |
| CURRENT | A completed-run fork control exists. It is not proof of a changed-assumption or paired-analysis workflow. | [`ForkRunControl.vue`](../../frontend/src/components/ForkRunControl.vue), [`SimulationRunView.vue`](../../frontend/src/views/SimulationRunView.vue), `canBranch` |
| CURRENT | Split layout already exists and places the active panel beside another panel. Structured record comparison remains a separate capability. | [`useDesktop.js`](../../frontend/src/composables/useDesktop.js), `LAYOUT_MODES` and layout contract |
| TARGET | Map/list parity is required by ADR-0006. Direction C documents a gap; a documentation statement alone is not a fresh exhaustive proof of code absence. | [ADR-0006](../architecture/adr/ADR-0006-route-map-list-parity.md), [Direction C](DIRECTION_C.md) |

The workflow's description of an action ledger as the canonical record is
rejected for the first slice. Use **recent recorded activity** and disclose
incomplete or unavailable history. Do not interpret a WebSocket arrival as an
actor's thinking time or as the time an action occurred. Reconnect recovery,
backfill, ordering and duplicate suppression require explicit tests.

## First implementation slice — TARGET

1. **Activity reading mode:** let a user hold the displayed list while incoming
   updates continue to be collected within a documented bounded buffer. Label
   this as holding the view, not pausing the simulation. Expose a clear return to
   current activity and an honest overflow/history-unavailable state.
2. **Selected-record inspection:** show only recorded fields and explicit
   references. Preserve selection while new rows arrive; return keyboard focus
   to the originating row on close. Show absent data as unavailable, not inferred.
3. **Run-state clarity:** distinguish starting, receiving updates, reconnecting,
   failed, interrupted, stopped and completed states from the actual response
   contract. An inactive connection must not imply that the simulation stopped.
4. **Existing fork affordance:** retain the completed-run branch control and its
   current request contract. Do not advertise editing assumptions, live parameter
   manipulation or automatic side-by-side differences until supported and tested.

Before implementing the first two items, settle record identity and a bounded
buffer policy with the runtime owner. A view hold must never silently discard
records while implying completeness. Do not add a new canonical store or
invent a client-only provenance ID as a server identity.

## Motion and interaction contract — TARGET

| Trigger | Presentation | Reduced motion / keyboard equivalent |
|---|---|---|
| Newly received recorded action | Brief row reveal, only for a record not previously displayed | Immediate insertion; restrained batched status announcement |
| User selects a record | Short focus/selection transition into inspection | Immediate selection, visible focus and predictable return |
| Reading view is held | Static held-view label and incoming-record indicator | Same state in text; no simulation-paused claim |
| Connection is lost or restored | Explicit connection status; preserve inspected content | Text update, no flashing or forced scrolling |
| Terminal state received | Stable outcome label; stop live-arrival motion | Immediate final state, no fabricated completion celebration |
| Empty or unavailable history | Explain which condition applies and offer valid recovery | Fully operable controls and readable status |

Use the documented short state-transition timing as a design target, not a
measured implementation result. Avoid continuous pulses, agent swarms,
confidence colors, inferred causal threads and animation rates that imply
probability or compute load. Preserve the distinct navigation and tablist
keyboard contracts, visible focus, product target-size standard, high-contrast
behavior, and small-screen reading order.

## Acceptance and evidence limits

Required before an implementation is called complete:

- Component tests for hold/resume-view, selected-record stability, buffer overflow,
  duplicates, ordering, missing IDs, reconnection and terminal-state transitions.
- Contract tests for actual server action limits, identity and backfill behavior;
  no complete-ledger wording unless completeness is proven.
- Browser checks at narrow and desktop widths, keyboard-only operation, zoom,
  reduced motion and forced colors; screen-reader checks recorded separately.
- Production build, frontend suite, standalone truth linter, docs validation and
  the repository verification command. A skipped check remains explicitly skipped.
- Human review of whether the interface communicates generated origin and avoids
  quantitative or predictive interpretations; no comprehension evidence exists
  from this workflow.

The workflow's test-count claim was stale. Use current command output rather
than copying counts from the artifact. A direct coordinator run of
`node tools/lint_frontend_truth.mjs` after the workflow returned nonzero with
copy violations and no Truth Rail gaps. Passing Vitest therefore must not be
reported as a passing standalone truth scan. These copy findings require a
separate scoped review; do not weaken the linter or remove required disclosures.

Server heartbeat alignment, full action-history completeness, font rights,
manual accessibility acceptance and structured comparison behavior were not
established by the design workflow. Source inspection is not live runtime proof.

## Impact, approval and rollback

No code, font dependencies, API contracts, product claims, default settings or
retention policy changes are authorized by this document. Named product,
engineering and accessibility reviewers have not been assigned; no human
approval is asserted. A later implementation requires a reviewed PR with the
acceptance evidence above and applicable security/privacy review.

The first slice should be independently revertible to the current run view
without mutating run artifacts. A documentation rollback removes this proposal
and its index link; it does not revert the committed simulator foundations.
Production population routing remains blocked pending acceptance of
[ADR-0015](../architecture/adr/ADR-0015-experimental-population-runtime.md).

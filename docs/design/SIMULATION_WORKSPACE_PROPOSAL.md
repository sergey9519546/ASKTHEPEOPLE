---
title: "Rig-aligned simulation workspace proposal"
status: "Proposed"
version: "0.3.0"
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
| TRANSITION | The client projects allowlisted public action data into a bounded reader. Server IDs are preferred; no-ID matching remains a local heuristic and does not establish cross-snapshot identity. | [`useRunActivity.js`](../../frontend/src/composables/useRunActivity.js), [`Step3Simulation.vue`](../../frontend/src/components/Step3Simulation.vue) |
| TRANSITION | The client exposes connecting, connected, reconnecting and disconnected WebSocket states separately from the server-side run status. A disconnected client does not establish that the run stopped. | [`ws.js`](../../frontend/src/api/ws.js), [`Step3Simulation.vue`](../../frontend/src/components/Step3Simulation.vue), [`Step3RunWayfinder.vue`](../../frontend/src/components/Step3RunWayfinder.vue) |
| TRANSITION | The transient `Process/new` route is accepted only while the Home form handoff exists in memory. It redirects to Home on a fresh load, and the desktop restore skips stale `new` panels because they have no resumable project ID. | [`router/index.js`](../../frontend/src/router/index.js), [`useDesktop.js`](../../frontend/src/composables/useDesktop.js), [`pendingUpload.js`](../../frontend/src/store/pendingUpload.js) |
| TRANSITION | Saved activity reads the first page with `limit=200, offset=0`; the server supports offset/limit but this change adds no cursor or complete-history guarantee. | [`Step3Simulation.vue`](../../frontend/src/components/Step3Simulation.vue), [`read_routes.py`](../../backend/app/api/routes/read_routes.py), `get_simulation_actions` |
| CURRENT | A completed-run fork control exists. It is not proof of a changed-assumption or paired-analysis workflow. | [`ForkRunControl.vue`](../../frontend/src/components/ForkRunControl.vue), [`SimulationRunView.vue`](../../frontend/src/views/SimulationRunView.vue), `canBranch` |
| CURRENT | Split layout already exists and places the active panel beside another panel. Structured record comparison remains a separate capability. | [`useDesktop.js`](../../frontend/src/composables/useDesktop.js), `LAYOUT_MODES` and layout contract |
| TARGET | Map/list parity is required by ADR-0006. Direction C documents a gap; a documentation statement alone is not a fresh exhaustive proof of code absence. | [ADR-0006](../architecture/adr/ADR-0006-route-map-list-parity.md), [Direction C](DIRECTION_C.md) |

The workflow's description of an action ledger as the canonical record is
rejected for the first slice. Use **recent recorded activity** and disclose
incomplete or unavailable history. Do not interpret a WebSocket arrival as an
actor's thinking time or as the time an action occurred. The bounded client
change has tests for reconnect handling, ordering and duplicate suppression;
server-side backfill completeness remains unasserted.

## First implementation slice — TRANSITION (bounded recent-activity reader)

Implemented as a bounded transition; this records current implementation and
does not assert proposal approval:

- A new `useRunActivity` composable retains up to 200 projected public records,
  bounds remembered identities to that window, assigns monotonic local display
  keys, and keeps a held snapshot and selected record as separate copies.
  `frontend/src/composables/useRunActivity.js` explicitly labels no-ID matching
  as heuristic and does not claim complete event identity. It accepts only
  allowlisted public fields; retention is by record count, not payload bytes or
  string/array length.
- `Step3Simulation.vue` requests the existing saved-action endpoint with
  `limit=200, offset=0`, continues state/action ingestion while the view is held,
  ingests terminal-frame actions before stopping, and rejects stale callbacks or
  async replies after retry/run changes/unmount. Reconnect preserves the held
  view and selected record; a new run resets them.
- `Step3RunWayfinder.vue` provides Hold view / Show latest, an explicit statement
  that holding the view does not pause the run, pending/overflow/eviction and
  history-unavailable messages, and an Inspect record control. The list count is
  “shown,” not total actions or people.
- `RunActivityInspector.vue` displays the copied public record fields and
  explicit public references, marks fallback identity as local, renders text
  literally, and restores focus to the originating row or toolbar on close.

The interaction remains a bounded view over recent snapshots and a bounded first
page of saved history. `backend/app/api/ws.py` sends at most ten recent actions
per state frame; the current action API offers offset/limit but no asserted
complete-history cursor in this change. Missing server IDs mean the heuristic
cannot prove two equal actions from different snapshots are the same event.
An old held snapshot is preserved for reading, but Show latest returns only the
retained current window. A history-fetch failure is not represented as an empty
run. No pause request, API/schema change, server identity, full replay guarantee,
or durable buffer was added.

## Run connection status — TRANSITION

The resilient WebSocket helper reports `connecting`, `connected`,
`reconnecting`, and `disconnected` transitions to the simulation screen. The
run screen presents these as connection status, independently of the saved
runner status. A transport error during automatic retry is shown as
`reconnecting`, not as a stopped run; a disconnected connection states that
the server-side run may still be continuing and offers a manual reconnect.
An update-error frame is identified separately from an open/closed transport.
Status callbacks are guarded by the same run-session and socket generations as
activity frames, so an invalidated socket cannot overwrite current status.

This is client connection feedback only. It adds no server status endpoint,
does not prove delivery completeness, and is not evidence that the underlying
run is progressing or has stopped.

## Transient new-workspace route recovery — TRANSITION

The Home submission handoff is held in module memory, while the desktop saves
panel routes for reload. `Process/new` is therefore not a resumable destination.
The router now sends a fresh load of that route back to Home unless the pending
form handoff exists; desktop restoration also drops old `Process/new` entries,
while retaining a completed project's real ID route. When the error is rendered
without a retryable recovery action, the UI no longer offers a misleading
“Try again” that would attempt to load the placeholder ID.

This does not persist the decision text or uploaded files. A reload before
project creation completes still requires the user to submit again from Home.

## Remaining workspace contract — TARGET

1. **Activity reading mode:** let a user hold the displayed list while incoming
   updates continue to be collected within a documented bounded buffer. Label
   this as holding the view, not pausing the simulation. Expose a clear return to
   current activity and an honest overflow/history-unavailable state.
2. **Selected-record inspection:** show only recorded fields and explicit
   references. Preserve selection while new rows arrive; return keyboard focus
   to the originating row on close. Show absent data as unavailable, not inferred.
3. **Run-state clarity:** distinguish starting, receiving updates, reconnecting,
   failed, interrupted, stopped and completed states from the actual response
   contract. The connection states are now exposed in the client; the remaining
   run lifecycle labels still require validation against the actual response
   contract. An inactive connection must not imply that the simulation stopped.
4. **Existing fork affordance:** retain the completed-run branch control and its
   current request contract. Do not advertise editing assumptions, live parameter
   manipulation or automatic side-by-side differences until supported and tested.

The first two items have a bounded partial implementation, not complete-history
or accessibility acceptance. The local identity and buffer policy are explicit
heuristics; validate any stronger identity or backfill contract with the runtime
owner before extending it. A view hold must never silently discard records while
implying completeness. Do not add a new canonical store or treat a client-only
display key as a server identity.

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

Implementation verification for the bounded slice (2026-11-01): the five
focused activity suites passed **76 tests across five files**; the full frontend
suite passed **390 tests across 38 files**; and the production build completed
successfully. `npm run verify` passed gates 1–5, including **10,032 backend
tests passed, 1 skipped, 1 xfailed**; gate 6 was skipped because gitleaks is not
installed locally. The backend run emitted two warnings (a dependency
deprecation and a Windows pytest-cache permission warning).

Browser checks used a temporary local Vite harness with synthetic records, not
a live backend. Keyboard activation opened inspection, focus moved to its
heading, and closing returned focus to the originating row. Holding the view
preserved its snapshot while a new action arrived; Show latest displayed the
retained current window. At 390 px the activity layout remained one column with
no horizontal overflow; at 1365 px it used two columns. Reduced-motion and
forced-colors media modes were emulated. axe-core 4.12.1 reported zero
violations, 25 passes, and one incomplete check; a status-chip contrast issue
found in the first browser pass was corrected. The standalone axe CLI could not
start because its bundled ChromeDriver 151 did not match installed Chrome 156;
axe-core was run in the integrated browser instead. No screen-reader or human
accessibility evaluation was performed.

The standalone truth linter reports the same **six copy violations and zero
Truth Rail gaps** on the clean `HEAD` baseline and this worktree; the measured
delta is **zero**. Existing findings are in `frontend/index.html`,
`frontend/public/mark.svg`, `frontend/public/social-card.svg`,
`frontend/src/components/Step4Report.vue`, and
`frontend/src/views/NotFoundView.vue`. Do not silence or weaken those findings
as part of this slice. `python tools/validate_docs.py` passed with zero warnings
and errors after this document update. The Vitest harness uses synthetic
fixtures; it is not live backend, screen-reader, or human comprehension
evidence.

Follow-on verification (2026-11-01): the frontend suite passed **396 tests in
38 files** with Vitest limited to one worker, and the production build and docs
validator passed. The frontend truth linter still reports the same six
pre-existing violations and zero Truth Rail gaps. In the full `npm run verify`
attempt, gates 1, 2, 4 and 5 passed; gate 3 exhausted process/JavaScript heap
memory under its default worker count, despite the standalone one-worker suite
passing, and gate 6 was skipped because gitleaks is not installed locally.
Native Python Playwright verification confirmed that opening `/process/new`
without the in-memory handoff redirects to `/` and does not render the missing-
decision alert. Restoring stale desktop-panel state is covered separately by a
desktop-store test.


## Impact, approval and rollback

This proposal does not itself authorize code, font dependency, API contract,
product claim, default setting or retention-policy changes. The bounded slice
remains a transition, not acceptance of the broader design; named product,
engineering and accessibility reviewers have not been assigned, and no human
approval is asserted. A reviewed PR with the acceptance evidence above and
applicable security/privacy review is still required before treating the broader
design as accepted.

The first slice should be independently revertible to the current run view
without mutating run artifacts. A documentation rollback removes this proposal
and its index link; it does not revert the committed simulator foundations.
Production population routing remains blocked pending acceptance of
[ADR-0015](../architecture/adr/ADR-0015-experimental-population-runtime.md).

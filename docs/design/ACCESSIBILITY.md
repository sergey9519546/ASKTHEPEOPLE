---
title: "Accessibility"
status: "Normative"
version: "1.2.0"
owner: "Accessibility Lead + Frontend Engineering"
last_reviewed: "2026-10-02"
review_cycle: "Every release"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P1 'Inconsistent request validation'"
applies_to: "every UI surface, every generated route, every report, every export"
---

# Accessibility

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.

## Conformance target

ASKTHEPEOPLE MUST conform to **WCAG 2.2 Level AA** across authenticated and
public surfaces. The product adopts selected stronger internal standards where
they materially reduce error:

- interactive targets SHOULD be at least 44×44 CSS pixels; WCAG 2.2 AA's
  24×24 minimum is the legal floor, not the design objective;
- focus SHOULD be fully visible, not merely partially visible;
- all route meaning MUST have a nonvisual equivalent;
- no critical workflow may require drag, hover, fine pointer precision, color
  discrimination, or animation.

Conformance statements require completed testing and named scope. “Built with
accessible components” is not a conformance claim.

## Semantic architecture

- Each page has one descriptive `h1`.
- Landmark regions are named and stable.
- Workflow progress uses an ordered list with current-step semantics.
- Status changes use appropriate live regions without replaying entire screens.
- Errors are associated with fields and summarized at the top.
- Tables use real table semantics.
- The route list is authoritative; SVG is supplementary.
- Disclosure controls use buttons with `aria-expanded` and `aria-controls`.
- The Truth Rail appears early in reading order and does not repeat on every
  focus change.

## Keyboard contract

Every function MUST be operable with keyboard alone. Required behaviors:

- logical focus order follows visual and task order;
- skip link moves to main content;
- sticky headers and rails never obscure focus;
- `Escape` closes dialogs and drawers when safe;
- focus returns to the invoking control;
- destructive or irreversible actions require an explicit confirmation;
- keyboard shortcuts are documented, remappable when single-character, and
  disabled in text inputs;
- map interactions have list/button equivalents.

### Workspace shell bindings

These are the bindings of the workspace chrome described in
[`DIRECTION_C.md`](DIRECTION_C.md) ledger entries D6 to D9. The rationale is
in [`UX_REDESIGN_2026.md`](UX_REDESIGN_2026.md).

**Journey spine** (`frontend/src/components/DesktopDock.vue`) — a `<nav>`
labelled `Journey`, not a tablist, so it carries no tab keyboard contract. Each
entry is a `<button>` in an `<ol>` with `aria-current="step"` on the current
position and `aria-disabled` while locked. The collapse toggle is a `<button>`
with `aria-expanded` and `aria-controls`. `Tab` reaches every entry; no arrow-key
roving applies, because a sequence is not a set of tabs.

**Panel switcher** (`frontend/src/components/DesktopTaskbar.vue`) — a real
tablist, so it takes the full tab contract:

| Key | Behavior |
|---|---|
| `Tab` | Enters the tablist once, on the selected tab; roving `tabindex` keeps one stop |
| `ArrowRight` / `ArrowLeft` | Move focus to the next / previous tab, wrapping |
| `Home` / `End` | Move focus to the first / last tab |
| `Enter` or `Space` | Activate the focused tab and move the workspace selection with it |
| `Delete` or `Backspace` | Close **only** the focused panel, then move focus to its neighbour |

Activation is **manual**, not automatic. A panel may be running a polling loop
or a heavy render, and auto-switching on focus would make arrowing past it
expensive. `Delete` closes one panel, never the workspace.

**Panel resize grip** (`frontend/src/components/DesktopWindow.vue`) — a
focusable `role="separator"` with `aria-orientation="horizontal"`, rendered only
in the free layout:

| Key | Behavior |
|---|---|
| `ArrowRight` / `ArrowLeft` | Widen / narrow by 16px, floor 320px |
| `ArrowDown` / `ArrowUp` | Grow / shrink by 16px, floor 240px |
| `Shift` with any arrow | Same, at a 48px step |

**Placement menu** (`frontend/src/components/DesktopWindow.vue`) — a
`Placement` button with `aria-haspopup="menu"` in the window title bar, offering
fill, centre, left half, and right half. This is the single-pointer,
non-drag alternative that WCAG 2.2 SC 2.5.7 Dragging Movements requires; a
modifier held while arrowing does not satisfy it.

**Shell shortcuts** (`frontend/src/components/DesktopShell.vue`), all suppressed
while focus is in a text input:

| Key | Behavior |
|---|---|
| `Ctrl` / `Cmd` + `W` | Close the active panel |
| `Alt` + `` ` `` | Cycle panels backwards or forwards, with `Shift` |
| `Ctrl` + `K` | Open the command palette |

Two chords the workspace deliberately does **not** take, because they belong to
the browser and a workspace must never stand between a person and the tab they
meant to open or close:

| Key | Left to the browser because |
|---|---|
| `Ctrl` + `Tab` / `Ctrl` + `Shift` + `Tab` | Browser tab switching. An earlier draft of this design bound it to panel cycling; that was withdrawn. |
| `Ctrl` + `W` outside the app frame | Closing the browser tab. The binding above only fires while the workspace has focus. |

Every panel switch cross-fades through the View Transitions API, not just the
keyboard one. The transition lives in `focusWindow` in `useDesktop.js` so the
switcher, the journey spine, and the URL watcher all animate identically, and
the workspace canvas carries `view-transition-name: workspace-canvas` so the
cross-fade is scoped to the content rather than re-animating the truth rail,
masthead, spine, and switcher underneath it.

**Known gaps in the contract above.** The Placement menu declares
`role="menu"` with `role="menuitem"` children but has no roving focus, no
arrow-key movement, and no `Escape` handler. The resize grip carries no
`aria-valuenow`, `aria-valuemin`, or `aria-valuemax`, so a screen reader
announces that it resizes without saying how large the panel currently is.
Both are recorded as PARTIAL below and must not be read as conformance claims.

## Dialogs and overlays

Modal dialogs MUST follow the WAI-ARIA Authoring Practices pattern:

- focus moves into the dialog;
- tab order remains inside while open;
- background is inert;
- dialog has an accessible name and, where useful, description;
- `Escape` closes unless doing so would corrupt an operation;
- focus returns to the invoker or next logical element;
- initial focus placement reflects dialog content and consequence.

Prefer inline disclosure or a nonmodal inspector when a modal is not necessary.

## Visual requirements

- Body text contrast meets 4.5:1; large text meets 3:1.
- Meaningful component boundaries and graphics meet 3:1.
- Focus uses a two-tone treatment that remains visible on paper, charcoal, and
  yellow.
- Text remains readable at 200% zoom without loss of content or function.
- Layout reflows at 320 CSS pixels without two-dimensional scrolling except
  genuinely two-dimensional data with an equivalent list.
- Users can increase text spacing without clipping.
- Color is never the only indicator of route, state, error, or selection.
- Error, warning, synthetic, and complete states have distinct text labels.

## Motion and vestibular safety

- Honor `prefers-reduced-motion`.
- Do not use parallax, zooming backgrounds, continuous route movement, particle
  systems, pulsing nodes, or animated “thinking.”
- Route drawing is optional, lasts no more than 220 ms by default, and resolves
  instantly under reduced motion.
- No essential timing, ordering, or status information depends on animation.
- User-triggered motion has a pause/stop mechanism when it lasts more than five
  seconds.

## Forms and authentication

- Labels remain visible; placeholders are not labels.
- Required and optional status is stated in text.
- Instructions precede the control they govern.
- Error messages explain the problem and exact next action.
- Previously entered values are preserved when safe after validation failure.
- Authentication does not require a cognitive-function test without an
  accessible alternative.
- Password managers and paste are not blocked.
- Timeouts warn users and allow extension except where security prohibits it.

## Accessibility acceptance

Target **WCAG 2.2 AA** as the minimum and adopt selected AAA practices where practical. W3C recommends WCAG 2.2 as the current conformance target.([WCAG 2.2](https://www.w3.org/TR/WCAG22/))

Required:

- semantic headings and landmarks;
- list view equivalent for every route fact;
- full keyboard operation;
- visible two-color focus treatment across dark and paper fields;
- no focused element obscured by sticky UI;
- 44×44 CSS px product standard for primary pointer targets, even though WCAG AA permits a smaller minimum in defined cases; 44×44 is the enhanced target.([WCAG 2.2 Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html))
- no color-only meaning;
- minimum 3:1 non-text contrast for meaningful graphical objects and UI states;
- screen-reader labels for route IDs and relationships;
- focus trap, `Escape`, inert background, and focus restoration in modal dialogs;
- no hover-only or tooltip-only essential content;
- `prefers-reduced-motion` support;
- zoom/reflow at 200% and 400% where applicable;
- no two-dimensional scrolling for primary workflow content at 320px;
- accessible authentication without memory or puzzle barriers;
- error summary linked to fields;
- status messages announced without moving focus unnecessarily.

### Required manual test matrix

- Keyboard only, desktop
- NVDA + Firefox or Chrome on Windows
- VoiceOver + Safari on macOS/iOS
- 200% zoom on desktop
- 320px viewport
- Reduced motion
- High contrast / forced colors
- Touch target review
- PDF/print reading order

Automated accessibility tests are necessary but not sufficient.

## Motion

Use one signature motion cue:

- selected route draws from origin to endpoint in 160–220ms;
- branch nodes appear without bounce;
- state changes use short opacity/position transitions;
- no continuous pulses, moving particles, animated network “thinking,” or avatar typing;
- reduced-motion mode renders final state immediately.

Motion communicates sequence only. It must never imply probability, urgency, intelligence, or certainty.

## Testing program

## Accessibility testing

CI:

- semantic lint;
- automated axe checks on key routes;
- color-token contrast tests;
- keyboard-focused component tests;
- reduced-motion tests;
- export heading/reading-order checks where automatable.

Manual before release:

- keyboard traversal with visible focus;
- NVDA/Firefox or Chrome;
- VoiceOver/Safari;
- 320px and 200% zoom;
- route map/list parity;
- dialog focus containment and restoration;
- live status announcements;
- forced-colors mode;
- PDF or share-view reading order.

Zero critical or serious accessibility defects are permitted at launch.

## Visual fidelity testing

The design concept and rendered implementation must be compared directly.

Required viewport set:

- concept/native desktop size where available;
- 1440×900;
- 1280×800;
- 1024×768;
- 390×844;
- 320×568.

Create a fidelity ledger with:

| Area | Concept evidence | Render evidence | Mismatch | Fix/status |
|---|---|---|---|---|
| Truth Rail | five hard cells | screenshot | … | … |
| Step spine | active yellow block | screenshot | … | … |
| Route grammar | equal-weight lines | screenshot | … | … |
| Brief typography | editorial paper field | screenshot | … | … |
| Inspector | dark 320–360px rail | screenshot | … | … |
| Mobile list | one mode, no horizontal pan | screenshot | … | … |

Passing builds, unit tests, or “looks close” do not replace visual inspection.

## Assistive-technology matrix

At minimum before public beta:

| Platform | Browser | Assistive technology | Scope |
|---|---|---|---|
| Windows | Chrome or Edge current | NVDA current | Full primary workflow |
| macOS | Safari current | VoiceOver | Full primary workflow |
| iOS | Safari current | VoiceOver | Mobile workflow and exports |
| Android | Chrome current | TalkBack | Mobile workflow |
| Keyboard only | Current Chromium + Safari | none | All interactive surfaces |
| Zoom/reflow | Current Chromium | 200% and 400% | All primary surfaces |
| Reduced motion | OS + browser preference | none | All animated surfaces |

Versions MUST be recorded in the release evidence.

## Accessibility defect severity

| Severity | Example | Release effect |
|---|---|---|
| P0 | Cannot complete workflow without mouse; truth disclosure inaccessible | Block release |
| P1 | Focus trapped/lost; route content missing from screen reader | Block release |
| P2 | Noncritical contrast or announcement defect with workaround | Requires approved remediation date |
| P3 | Minor consistency issue | Track normally |

## Acceptance evidence

- automated axe-compatible scan with zero critical/serious findings in covered
  surfaces;
- complete keyboard walkthrough;
- named screen-reader results;
- 320px and 200% zoom screenshots;
- focus-not-obscured evidence with sticky Truth Rail;
- map/list parity tests;
- reduced-motion capture;
- accessible PDF/export review when exports are included in the release.

## References

- [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/) - Current accessibility conformance target for the product.
- [WAI-ARIA APG - Modal Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) - Required modal focus, inert-background, Escape, and focus-restoration behavior.

---

## Project-specific accessibility status (baseline `8b616dc7`)

The accessibility standards in this doc are normative. The
current frontend is a Vue 3 + Vite application. There is **no
automated accessibility check** in CI and **no comprehension-
test program**. Gate 1 + gate 5, owned by
`askthepeople-frontend-steward` and
`askthepeople-ai-eval-steward`.

Gate status is not stated here beyond the two gate identifiers this section
already carried. The single authoritative statement of gate status is
[architecture/index.md § Status of record](../architecture/index.md#status-of-record).

Status vocabulary is the legend defined in
[architecture/index.md](../architecture/index.md#state-legend-used-in-this-document).

### CURRENT

- **Focus-not-obscured by default.** In the default `focus` panel layout there
  is no floating chrome to occlude a focused control, because there is no
  floating chrome (WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum), AA).
- **No critical workflow requires a drag.** Panel resizing is reachable from
  the keyboard, and placement is reachable through a single-pointer menu, so
  dragging is never the only route to any operation (SC 2.5.7 Dragging
  Movements, AA).
- **A control-height scale anchored on the WCAG 2.2 minimum.** `--target-min:
  1.5rem` encodes the 24px floor, with `--control-h-sm`, `--control-h-md`, and
  `--control-h-lg` as the sizes actually used, and a `.u-target` helper that
  expands an icon-only control's hit area without changing what is visible
  (SC 2.5.8 Target Size (Minimum), AA).
- **One focus-ring definition, plus raised-contrast modes.** `--focus-ring-color`,
  `--focus-ring-width`, and `--focus-ring-offset` are declared once in the token
  layer, and `@media (prefers-contrast: more)` and `@media (forced-colors:
  active)` blocks reassert borders and the focus ring (SC 2.4.7 Focus Visible,
  AA; SC 1.4.11 Non-text Contrast, AA).
- **Shell semantics match shell behavior.** The journey spine is a `<nav>` with
  `aria-current="step"`; the panel switcher implements the tab pattern it
  declares, including `aria-controls`, a matching `tabpanel`, roving `tabindex`,
  and arrow-key movement; panels are `role="tabpanel"` labelled by the tab that
  opens them (SC 4.1.2 Name, Role, Value).
- **Secondary text clears the AA floor on every ink field.** `--paper-dim` is
  `#908d85`, measuring 4.52:1 on `--ink-raised` and 5.04 to 5.78:1 on the other
  three. The previous `#817e76` fell to 3.70:1 on raised surfaces. A test
  recomputes every text pairing out of `design-tokens.css` rather than trusting
  a table, so this cannot silently regress (SC 1.4.3 Contrast, Minimum, AA).
- **One `h1` per route view.** A shared `ViewHeader.vue` owns it, and the panel
  title bar is no longer a heading, so the outline no longer runs h2 then h1
  inside every window (SC 2.4.6 Headings and Labels, AA).
- **Motion is guarded.** `prefers-reduced-motion` is honored, and the View
  Transitions cross-fade falls back to a no-op rather than to a degraded
  animation (SC 2.3.3 Animation from Interactions, AAA).

### PARTIAL

- **SC 1.4.11 on structural rules.** `--line-dark` measures 1.46 to 1.86:1 on
  the four ink fields, below the 3:1 floor, and it draws every band separator,
  panel edge, and input border in the shell. A compliant value now ships as
  `--line-structural` (`#6b716e`, 3.01 to 3.84:1) and `prefers-contrast: more`
  selects it, but it is deliberately not the default: at roughly three times the
  current luminance, applying it to every border would stop the ink fields
  reading as one dark mass. Adopting it is a one-token change.
- **Focus ring on paper fields.** `--attention` on `--paper` is 1.20:1. The
  palette has no compliant ring for its own paper fields.
- **Target size: AA floor met, product standard not.** `--target-min` encodes
  24px, which is the WCAG AA floor. This document and
  [`DIRECTION_C.md`](DIRECTION_C.md) both state 44 by 44 as the product's
  enhanced target; `--control-h-md` is 2.25rem and `--control-h-sm` is 1.75rem.
  The gap is not closed.
- **The Placement menu is an incomplete menu widget.** No roving focus, no arrow
  keys, no `Escape`.
- **The resize grip reports no value.** No `aria-valuenow`,
  `aria-valuemin`, or `aria-valuemax`.
- **A heading inside a live region.** `InteractionView.vue`'s loading-state
  section is `role="status"` with `aria-live="polite"` and carries a heading
  inside it. That heading was an `<h1>` when this entry was first recorded and
  has since been demoted to `<h2>`, which closes the duplicate-`h1` problem the
  entry originally described. A heading inside a polite live region is still
  incorrect: the announcement fires on content change rather than on
  navigation, so the heading is read out as a status message.
- **Focus-ring tokens are declared but not consumed.** The pre-existing global
  `:focus-visible` rule still hard-codes the same two lengths, so there is one
  *named* definition and not yet zero hard-coded copies.
- **One view footer restates the permanent disclosure** that the shell's Truth
  Rail already carries.

### TARGET

- **A semantic route list as the canonical accessible alternative to the visual
  map**, and the parity test that would prove it. Required by
  [`adr/ADR-0006-route-map-list-parity.md`](../architecture/adr/ADR-0006-route-map-list-parity.md)
  and **still not done**. There is no canonical list at the API or JSON-LD level
  that the visual map and the list view both consume, and no automated check
  that every map fact has a list entry and vice versa. The October 2026 shell
  redesign does not advance this requirement.
- **WCAG 2.2 conformance evidence.** No automated scan, no named screen-reader
  results, no focus-not-obscured capture, no forced-colors capture, no
  comprehension testing. Conformance is **not** claimed by this document.
- **44 by 44 primary pointer targets** across every control family.
- **The disclosure block attached automatically** to every detached artifact:
  exports, social cards, and share previews.
- **Comprehension testing** confirming users understand that route geometry
  carries no quantitative meaning.

### Current state — PARTIAL (overall)

- Frontend is Vue 3 + Vite + vue-router. Built into `frontend/dist/` and served
  by the `serve_frontend` catch-all in `create_app`
  ([`backend/app/__init__.py`](../../backend/app/__init__.py)). The
  previously cited `:317-325` no longer resolves and was corrected here on
  2026-10-02.
- The accessibility conformance target is WCAG 2.2; no
  conformance evidence is recorded.
- The Truth Rail renders once in the desktop shell. The
  per-screen contextual statements remain **not yet rendered**.
- The disclosure block required by the contract is not
  automatically attached to exports, social cards, or share
  previews.

### Required correction (per this doc and the audit)

- WCAG 2.2 conformance verified by automated and manual
  testing on every release.
- A semantic route list as the canonical accessible
  alternative to the visual map (see ADR-0006).
- Truth Rail rendering in the frontend, with the disclosure
  block automatically attached to every detached artifact.
- Comprehension-test program confirming users understand the
  qualitative-only nature of the routes.
- Keyboard-only and screen-reader-only navigation of every map
  fact and action.
- Color/contrast conformance with non-color redundancy.

### Release evidence

The release evidence bundle required by
[`docs/release/ACCEPTANCE.md`](../release/ACCEPTANCE.md) MUST
include the accessibility conformance report and the
comprehension-test results.

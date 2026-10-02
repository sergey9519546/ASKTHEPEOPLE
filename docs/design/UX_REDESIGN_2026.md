---
title: "Workspace shell UX redesign — rationale record"
status: "Reference"
version: "1.1.0"
owner: "askthepeople-frontend-steward"
last_reviewed: "2026-10-02"
review_cycle: "Quarterly"
research_cutoff: "2026-10-02"
baseline_commit: "11eba8c"
applies_to: "frontend/src/components/DesktopShell.vue, DesktopMasthead.vue, DesktopDock.vue, DesktopTaskbar.vue, DesktopWindow.vue, ViewHeader.vue, frontend/src/composables/useDesktop.js, frontend/src/assets/design-tokens.css, and the five route views that mount ViewHeader"
---

# Workspace shell UX redesign — rationale record

> **Document authority.** This document is a rationale record, not a design
> authority. [Direction C](DIRECTION_C.md) remains the design direction,
> [Accessibility](ACCESSIBILITY.md) remains the conformance target, and
> [ADR-0001](../architecture/adr/ADR-0001-product-category-and-truth-contract.md)
> remains the truth boundary. Where this record and either of those disagree,
> they win. Status vocabulary is the four-state legend defined in
> [architecture/index.md](../architecture/index.md#state-legend-used-in-this-document).
> **Gate status is not asserted here.** The single authoritative statement of
> gate status is
> [architecture/index.md § Status of record](../architecture/index.md#status-of-record).

## Scope

This record covers one change: a redesign of the **UX layer** of the workspace
shell — the four chrome bands (Truth Rail, masthead, journey spine, panel
switcher) and the panel canvas — plus the extraction of a shared view header
that five route views now mount.

**The visual theme is unchanged and was not up for review.** Ink and paper
fields, signal red as a wayfinding edge, attention yellow reserved for focus
and small marks, the Staatliches-plus-Barlow pairing, square corners, hard
offset shadows, and the absence of gradients, glass, and glow are all exactly
as [Direction C](DIRECTION_C.md) specifies them. The rationale is simple: the
palette and the geometry were not what made the workspace hard to use. The
problem was that the shell asked a person to *manage windows* while they were
trying to *think about a decision*, and that several of its surfaces carried
semantics that did not match what they did. A restyle would have hidden those
defects behind a pleasant surface. Changing the interaction model and leaving
the theme alone makes the defects visible and then fixes them.

## Method, and how to read the citations

Every citation below is either `file:line` or `file` plus a symbol name.

The Vue components and the test files cited here were still uncommitted
working-tree content when this record was written, so they are cited by **file
and symbol**. That is not a shortcut: the repository's own contract prefers a
symbol reference over a line number that might be wrong, and a line number
pinned against a file still in motion is wrong within the hour. The tree moved
twice under this documentation pass — once by a commit landing mid-read, once
by an edit growing a cited file by seventeen lines — and every citation that
had been pinned by line survived only because it was re-measured immediately
before it was written.

Files cited with pinned lines:

- [`frontend/src/composables/useDesktop.js`](../../frontend/src/composables/useDesktop.js) — 504 lines, unmodified across the whole redesign.
- [`frontend/src/assets/design-tokens.css`](../../frontend/src/assets/design-tokens.css) — pinned lines in the `:root` token block, the base control rules, and the legacy surface rules are stable. **The tail of this file was still being edited when this record was written**, so the helper classes and the `prefers-contrast` / `forced-colors` blocks are cited by symbol and by their opening line only. That file grew by seventeen lines during this documentation pass and moved three of the anchors first pinned here; that is the drift this choice avoids.
- [`frontend/src/components/TruthRail.vue`](../../frontend/src/components/TruthRail.vue) — unmodified across the whole redesign.

## Problems found

Each problem is stated with the code as it stands after the change, and the
prior behaviour it replaced. The prior behaviour is described in prose because
the previous revision is in git history, not in the tree.

### P1 — The journey spine shipped collapsed

`DesktopShell.vue` declares `dockCollapsed` as a `ref` defaulting to `false`
and keeps it `false` until the viewport drops below the `min-width: 1080px`
media query, at which point `updateDockRoom` sets it to the query's inverse.
The collapsed column is `--band-spine-collapsed: 3.25rem`
(`design-tokens.css:88`), and in that state `DesktopDock.vue`'s
`.journey-spine.is-collapsed .spine-entry` rule collapses the row to a single
centred column while the step index span stays `aria-hidden`. The visible
result was a narrow strip of bare numerals.

Prior behaviour: `dockCollapsed` defaulted to `true` and the spine rendered as
a 3rem column of two-letter codes with no labels and no explanation. A
first-time user was given no orientation at all.

### P2 — Floating cascade was the default panel layout

`useDesktop.js:25-26` still defines `CASCADE_STEP` and `CASCADE_ORIGIN`, and
`nextCascade()` (`useDesktop.js:144-151`) assigns every newly opened panel an
offset from the previous one; `openApp` seeds that geometry into the panel
record (`useDesktop.js:242`, `:251-252`). But that geometry is now only
consulted in the free layout: `DesktopWindow.vue`'s `windowStyle` computed
returns an empty object for any mode that is not `free`, and
`DesktopShell.vue`'s `renderedPanels` computed returns exactly one panel in the
focus layout. `LAYOUT_MODES` is `["focus", "split", "free"]` with
`DEFAULT_LAYOUT_MODE = "focus"` (`useDesktop.js:113-114`).

Prior behaviour: the cascade was the layout a user got without asking for it.
Because the journey is sequential — each step consumes what the previous step
produced — a pile of floating windows meant z-order, occlusion, and window
management competing with the decision itself.

### P3 — The panel switcher declared a tab pattern and implemented none of it

`DesktopTaskbar.vue`'s tab container carries `role="tablist"`, each tab carries
`role="tab"`, `aria-selected`, `aria-controls="panel-body-{key}"`, and a roving
`:tabindex`, and `onTablistKeydown` handles `ArrowRight`, `ArrowLeft`, `Home`,
`End`, `Delete`, and `Backspace`. `DesktopWindow.vue` renders the matching
`role="tabpanel"` with `:aria-labelledby="panel-tab-{key}"` and an `:id` that
matches the tab's `aria-controls`.

Prior behaviour: the roles were present and the behaviour was not — no
`aria-controls`, no matching `tabpanel`, no roving `tabindex`, and no
arrow-key movement. Assistive technology was told this was a tab interface
and then given none of the tab contract. Activation is also now manual rather
than automatic, which is the deliberate choice recorded in the component's own
doc comment: auto-switching on focus would force a panel with a polling loop or
a heavy render to re-render every time the user arrowed past it.

### P4 — The only way to place a panel was to drag it

`DesktopWindow.vue`'s `window-resize` element is a focusable `role="separator"`
with `aria-orientation="horizontal"`, an `aria-label` naming the panel and the
keyboard affordance, and `onResizeKeydown` handling `ArrowRight`, `ArrowLeft`,
`ArrowDown`, and `ArrowUp` with a `Shift` coarser step and hard minimums. The
window title bar also carries a `Placement` button (`aria-haspopup="menu"`) that
opens a `role="menu"` of four `role="menuitem"` options — fill, centre, left
half, right half — applied by `applyPosition` without any pointer drag.

Prior behaviour: the resize grip was a passive corner graphic that only
responded to `pointerdown`/`pointermove`/`pointerup`, and panel size was
reachable no other way.

### P5 — The masthead carried a clock

`DesktopMasthead.vue` is now a four-cell orientation band: the product lockup
with its descriptor, the workspace name, the step position, and a single resume
affordance. `nextStep` is computed from `journeyState()` and is `null` unless
there is a genuinely launchable step ahead, in which case the Next button is
not rendered at all.

Prior behaviour: the band carried a wall clock re-rendered on a fifteen-second
timer. It had no bearing on any decision this product supports, and mutating
visible text on a timer is a live-region hazard for no benefit.

### P6 — Five hand-written headers had drifted apart

`ViewHeader.vue` is a single component; `MainView.vue`, `SimulationView.vue`,
`SimulationRunView.vue`, `ReportView.vue`, and `InteractionView.vue` each mount
it and each bind `:step` to `appById(...)` rather than to a locally typed
number.

Prior behaviour: each of the five views hand-wrote the row. The copies had
drifted into three different status vocabularies, seven naked-wordmark
truth-contract violations, five `STEP 0X/05` counters that contradicted the
shell's own six-step numbering, four duplicated truth-rail restatements in view
footers, and five duplicate skip links. The truth-contract ratchet in
`frontend/src/__tests__/product-truth-guard.spec.js` carries the retirement
note for exactly those seven entries; four of the five view footers were
deleted, and `InteractionView.vue`'s `app-footer-mini` is the one that remains.

### P7 — Heading order ran backwards inside every window

`DesktopWindow.vue`'s title is a `<span class="window-title">` carrying the
`:id` that the panel is `aria-labelledby`. `ViewHeader.vue` owns the view's
single `<h1>` (`<h1 class="header-step-name">`).

Prior behaviour: the panel title bar was an `<h2>` that sat **before** the
view's own `<h1>`, so every window presented the document outline as h2 → h1.

### P8 — The in-window step rail duplicated the shell's numbering

`MainView.vue` keeps a workflow rail, and it is explicitly scoped: the `<nav>`
carries `aria-label="Steps inside this workspace"` and a visible caption
reading `Steps inside this workspace`. That is correct and intended — the
sources panel is a genuine five-step workflow nested inside the six-step shell
journey. Two levels, two jobs, no duplicated numbering.

Prior behaviour: the rail restated the journey without saying which level it
was describing, so the same numerals meant two different things on one screen.

### P9 — The token layer was incomplete and had a dead import

All `file:line` references in this section point at
[`frontend/src/assets/design-tokens.css`](../../frontend/src/assets/design-tokens.css).

The token file now defines `--space-9: 6rem` and `--space-10: 8rem`
(`design-tokens.css:108-109`), a control-height scale with `--target-min: 1.5rem`
and `--control-h-sm` / `--control-h-md` / `--control-h-lg`
(`design-tokens.css:115-118`), shell band geometry `--band-truth`,
`--band-masthead`, `--band-spine`, `--band-spine-collapsed`, and
`--band-switcher` (`design-tokens.css:124-128`), `--edge-wayfinding: 3px`
(`design-tokens.css:133`), a single focus-ring definition — `--focus-ring-color`,
`--focus-ring-width`, `--focus-ring-offset`
(`design-tokens.css:135-139`) — a five-step leading scale
(`design-tokens.css:158-162`), and prose measure tokens `--measure-prose: 68ch`
and `--measure-tight: 46ch` (`design-tokens.css:167-168`). The helper classes are
`.u-target` (`design-tokens.css:1000`) and `.u-prose`
(`design-tokens.css:1016`). It also carries
`@media (prefers-contrast: more)` (`design-tokens.css:1022`),
`@media (forced-colors: active)` (`design-tokens.css:1050`), and
`@media (prefers-reduced-motion: reduce)` (`design-tokens.css:1084`).

> **Correction, 2026-10-02 (citation sweep).** Two claims in the paragraph this
> replaces were wrong and are removed rather than re-pointed:
> **`.u-stack` and `.u-cluster` do not exist.** A search of
> `frontend/src/**` for either class name returns nothing — they are not in
> `design-tokens.css` and no component uses them. The paragraph also cited
> `design-tokens.css` at line numbers that had all drifted (the file was
> restructured after this record was written); every anchor above was
> re-measured. An earlier version of this paragraph pointed at `:69-70`,
> `:76-79`, `:85-89`, `:94`, `:98-100`, `:119-123`, `:128-129`, `:1067`,
> `:1083`, `:1089`, `:1096`, `:1103`, and `:1128` — **none** of which contained
> the token it named.

The panel scroll containers now cross-fade instead of travelling: the
`.panel-wrapper, .panel-container` rule transitions `opacity` only
(`design-tokens.css:680-706`). The `.btn` rule takes its height from the control
scale rather than from padding arithmetic (`design-tokens.css:335-361`, with
`min-height: var(--control-h-md)` at `design-tokens.css:343`), and `.btn:active`
is a 1px settle rather than a scale (`design-tokens.css:370-377`).

Prior behaviour: `--space-10` was already referenced by `CommandPalette.vue` and
silently fell back to nothing, because it was never declared. Two malformed
`@import ""…"";` lines never parsed. Panel switching animated `transform` on the
scroll container itself, so every switch moved the thing the user was reading.
The button press was a `scale(0.985)`, which resamples the label mid-press.

### P10 — Panel switching cut instead of cross-fading

`DesktopShell.vue`'s `withPanelTransition` calls
`document.startViewTransition` only when the browser exposes it **and**
`prefers-reduced-motion` is not set, and otherwise runs the update directly —
a no-op fallback, not a degraded animation. The transition duration and easing
are declared in the shell's unscoped style block under
`@media (prefers-reduced-motion: no-preference)`.

Same-document view transitions reached Baseline in October 2025 and Vue has no
first-party support, so the glue is hand-rolled. There is deliberately no
hand-written overlap animation: keeping both panels in the DOM at once is
exactly what causes reading-position loss and focus confusion.

Two details are load-bearing and were wrong in the first pass. The transition
lives in `focusWindow` in `useDesktop.js`, not in the shell, because the shell is
only one of three callers — an early version animated the keyboard shortcut
while tab clicks cut instantly, which is worse than not animating at all. And
the workspace canvas carries `view-transition-name: workspace-canvas`: without a
name the browser transitions the whole document root, which would cross-fade
all four orientation bands on every switch, re-animating the surfaces the user
is reading in order to orient themselves exactly when that stops mattering. A
test asserts the name is declared once and that every `::view-transition-*`
rule in the stylesheet refers to that same subject, because transition CSS that
names nothing is silently dead.

### P11 — The entry view led with a diagram instead of the task

`Home.vue` is now decision-first: the composer is the first thing in the
document, source material and extra context sit behind native `<details>`
disclosures, and the former four-stage animated CSS diagram is replaced by a
static ordered sequence strip that keeps both required statements verbatim in
visible text — that spacing shows sequence only and not time or likelihood, and
that validation with people happens outside the generated run. Skeleton loading
regions now use `aria-busy` on the region with the announcement moved to a
visually-hidden `role="status"` paragraph, and the shimmer itself is
`aria-hidden`. The only animation left in the file is that skeleton shimmer,
and it is disabled under reduced motion.

Prior behaviour: the view opened with a tall animated four-stage diagram, and
both loading regions put `role="status"` on the skeleton container.

## Decisions and the accessibility criteria each one addresses

Criteria are WCAG 2.2. "SC" is a success criterion; the level is given where
it is not AA.

| # | Decision | Criteria addressed |
|---|---|---|
| 1 | The journey spine is the only journey navigation, open by default, using `<nav>` plus `aria-current="step"` | SC 4.1.2 Name, Role, Value; SC 2.4.11 Focus Not Obscured (Minimum), AA |
| 2 | Default panel layout is `focus` (one at a time); `split` and `free` remain available; `tiled` renamed `split` | SC 2.4.11 AA; SC 2.5.7 Dragging Movements, AA, by removing the drag from the default path |
| 3 | The panel switcher is a real tablist: `aria-controls`, matching `tabpanel`, roving `tabindex`, arrow keys, `Home` / `End`, `Delete` | SC 4.1.2; SC 2.1.1 Keyboard |
| 4 | Keyboard resize grip plus a single-pointer Placement menu | SC 2.5.7 Dragging Movements, AA |
| 5 | Masthead is an orientation band; the wall clock is gone | SC 4.1.2; live-region hygiene under SC 4.1.3 Status Messages |
| 6 | One shared `ViewHeader.vue` replaces five hand-written headers | SC 4.1.2; SC 2.4.6 Headings and Labels, AA |
| 7 | Panel title bar is no longer a heading; the shared header owns the single `h1` | SC 2.4.6 Headings and Labels, AA |
| 8 | The in-window rail is scoped as "Steps inside this workspace" | SC 1.3.1 Info and Relationships, A |
| 9 | Token layer: target-size scale, one focus ring, band geometry, contrast and forced-colors blocks | SC 2.5.8 Target Size (Minimum), AA; SC 1.4.11 Non-text Contrast, AA; SC 2.4.7 Focus Visible, AA; SC 1.4.6 Contrast (Enhanced) |
| 10 | View Transitions cross-fade, guarded by reduced motion, with a no-op fallback | SC 2.3.3 Animation from Interactions, AAA; SC 2.2.2 Pause, Stop, Hide |
| 11 | Decision-first entry view; static sequence strip; `aria-busy` skeletons | SC 4.1.2; SC 1.3.1; SC 2.2.2 |

Three notes on how the criteria were read, because the reading matters:

- **SC 2.5.7 requires a single-pointer, non-drag alternative.** A modifier held
  while arrowing does not satisfy it. That is why decision 4 makes the grip a
  real focusable `separator` with its own key handling rather than a graphic
  with a keyboard modifier, and why the Placement menu exists at all.
- **SC 2.5.8's AA minimum is 24 by 24 CSS pixels; 44 by 44 is the product's own
  enhanced target.** `--target-min: 1.5rem` encodes the legal floor, and the
  three `--control-h-*` heights encode what is actually used. The gap between
  the floor and the product standard is still open; see *Accepted,
  unresolved*.
- **SC 1.4.11 applies to UI components and meaningful graphical objects at 3:1,
  and SC 1.4.3 applies to text at 4.5:1.** The contrast table below is
  partitioned accordingly, because a pairing can pass one and fail the other
  and reporting a single verdict would hide that.

## Contrast, computed against the actual palette

### Method

Relative luminance per WCAG 2.2: for each 8-bit channel `c`,
`c' = c/12.92` when `c <= 0.03928`, otherwise
`c' = ((c + 0.055)/1.055) ^ 2.4`; then
`L = 0.2126R + 0.7152G + 0.0722B`. Contrast ratio is
`(L_lighter + 0.05) / (L_darker + 0.05)`.

Every luminance below was computed from the hex values declared in
`design-tokens.css:10-46`, not copied from a table. Two worked examples:

```text
ink        #111513  R=17  -> 17/255 = 0.066667 > 0.03928
                           (0.066667 + 0.055)/1.055 = 0.115324
                           0.115324 ^ 2.4            = 0.005605
                           L = 0.2126(0.005605) + 0.7152(0.007499) + 0.0722(0.006512)
                             = 0.001192 + 0.005364 + 0.000470 = 0.007025

paper      #f2ebdd  R=242 -> 242/255 = 0.949020 > 0.03928
                           (0.949020 + 0.055)/1.055 = 0.951678
                           0.951678 ^ 2.4            = 0.887923
                           L = 0.2126(0.887923) + 0.7152(0.830770) + 0.0722(0.723055)
                             = 0.188778 + 0.594168 + 0.052205 = 0.835144

paper on ink-deep  = (0.835144 + 0.05) / (0.004832 + 0.05)
                   = 0.885144 / 0.054832 = 16.14 : 1
```

### Relative luminance

| Token | Hex | R | G | B | L |
|---|---|---:|---:|---:|---:|
| `--ink` | `#111513` | 17 | 21 | 19 | 0.007025 |
| `--ink-deep` | `#0c100f` | 12 | 16 | 15 | 0.004832 |
| `--ink-soft` | `#1a1f1d` | 26 | 31 | 29 | 0.012883 |
| `--ink-raised` | `#232825` | 35 | 40 | 37 | 0.020085 |
| `--paper` | `#f2ebdd` | 242 | 235 | 221 | 0.835144 |
| `--paper-muted` | `#c7c0b3` | 199 | 192 | 179 | 0.530961 |
| `--paper-dim` | `#908d85` | 144 | 141 | 133 | 0.266725 |
| `--signal` | `#f04b3d` | 240 | 75 | 61 | 0.238943 |
| `--signal-text` | `#982d24` | 152 | 45 | 36 | 0.086795 |
| `--attention` | `#ffd51d` | 255 | 213 | 29 | 0.689372 |
| `--line-dark` | `#3c423f` | 60 | 66 | 63 | 0.052160 |
| `--line-structural` | `#6b716e` | 107 | 113 | 110 | 0.160618 |

### Structural rules and UI boundaries — SC 1.4.11, 3:1 floor

| Foreground | Background | Ratio | 1.4.11 |
|---|---|---:|---|
| `--line-dark` | `--ink` | 1.79 | **FAIL** |
| `--line-dark` | `--ink-deep` | 1.86 | **FAIL** |
| `--line-dark` | `--ink-soft` | 1.62 | **FAIL** |
| `--line-dark` | `--ink-raised` | 1.46 | **FAIL** |
| `--line-dark` | `--paper` | 8.66 | pass |
| `--line-dark` | `--paper-muted` | 5.69 | pass |

This is the most consequential finding in the table. `--line-dark` is the
single border token for the whole shell, and on every ink field it sits between
1.46:1 and 1.86:1 — well under 3:1. It draws the masthead's bottom rule, the
spine's right rule, the panel switcher's top rule, and the panel title bar's
bottom rule. Those are band separators the user does not strictly need in order
to read, and the shell's structure is carried independently by the Truth Rail,
the landmarks, and the tablist, so this is a **PARTIAL** finding against SC
1.4.11 rather than a blocker. It is not, however, something to leave
unrecorded: the rules are doing real work as band separators, and the remedy
already exists in the token layer.

### Wayfinding edges and marks — SC 1.4.11, 3:1 floor

| Foreground | Background | Ratio | 1.4.11 |
|---|---|---:|---|
| `--signal` | `--ink` | 5.07 | pass |
| `--signal` | `--ink-deep` | 5.27 | pass |
| `--signal` | `--ink-soft` | 4.59 | pass |
| `--signal` | `--ink-raised` | 4.12 | pass |
| `--signal` | `--paper` | 3.06 | pass, marginal |
| `--signal` | `--paper-muted` | 2.01 | **FAIL** |

Signal red as a 3px wayfinding edge clears the non-text floor on every ink
field, which is what the shell relies on. It does not clear 4.5:1 anywhere, so
`--signal` is a **mark and border token only**; text on any surface must use
`--signal-text`.

### Focus ring and attention marks — SC 1.4.11, 3:1 floor

| Foreground | Background | Ratio | 1.4.11 |
|---|---|---:|---|
| `--attention` | `--ink` | 12.97 | pass |
| `--attention` | `--ink-deep` | 13.48 | pass |
| `--attention` | `--ink-soft` | 11.76 | pass |
| `--attention` | `--ink-raised` | 10.55 | pass |
| `--attention` | `--paper` | 1.20 | **FAIL** |
| `--attention` | `--paper-muted` | 1.27 | **FAIL** |

Attention yellow on an ink field is the strongest contrast in the entire
palette. The same token on a paper field is effectively invisible, and the
palette ships a paper field.

### Body and label text — SC 1.4.3, 4.5:1 floor

| Foreground | Background | Ratio | 1.4.3 |
|---|---|---:|---|
| `--paper` | `--ink` | 15.52 | pass (AAA) |
| `--paper` | `--ink-deep` | 16.14 | pass (AAA) |
| `--paper` | `--ink-soft` | 14.08 | pass (AAA) |
| `--paper` | `--ink-raised` | 12.63 | pass (AAA) |
| `--paper-muted` | `--ink` | 10.19 | pass (AAA) |
| `--paper-muted` | `--ink-deep` | 10.60 | pass (AAA) |
| `--paper-muted` | `--ink-soft` | 9.24 | pass (AAA) |
| `--paper-muted` | `--ink-raised` | 8.29 | pass (AAA) |
| `--paper-dim` | `--ink` | 5.55 | pass |
| `--paper-dim` | `--ink-deep` | 5.78 | pass |
| `--paper-dim` | `--ink-soft` | 5.04 | pass |
| `--paper-dim` | `--ink-raised` | 4.52 | pass |
| `--signal-text` | `--ink` | 2.40 | **FAIL** |
| `--signal-text` | `--ink-deep` | 2.49 | **FAIL** |
| `--signal-text` | `--ink-soft` | 2.18 | **FAIL** |
| `--signal-text` | `--ink-raised` | 1.95 | **FAIL** |

### On paper surfaces — SC 1.4.3, 4.5:1 floor

| Foreground | Background | Ratio | 1.4.3 |
|---|---|---:|---|
| `--signal-text` | `--paper` | 6.47 | pass |
| `--signal-text` | `--paper-muted` | 4.25 | **FAIL** |
| `--paper-dim` | `--paper` | 3.42 | **FAIL** |
| `--paper-muted` | `--paper` | 1.52 | **FAIL** |
| `--signal` | `--paper` | 3.06 | **FAIL**, 3:1 only |
| `--attention` | `--paper` | 1.20 | **FAIL** |

### Pairings that must not be combined

1. **`--attention` with any paper field.** 1.20:1 against `--paper`. A yellow
   focus ring on a cream surface is not a focus indicator. Paper-field controls
   need a dark ring; the existing `forced-colors` block handles the
   system-forced case but nothing handles the author's own paper fields.
2. **`--paper-muted` with `--paper`.** 1.52:1. The muted paper token is an
   *ink*-field secondary tone only.
3. **`--signal-text` with `--paper-muted`.** 4.25:1. Accessible red belongs on
   `--paper`, not on a muted panel.
4. **`--signal` with `--paper-muted`.** 2.01:1 — fails even the non-text floor.
5. **`--signal-text` with any ink field.** 1.95 to 2.49:1. Accessible red is a
   paper-field token.
6. **`--paper-dim` with `--ink-soft` or `--ink-raised`.** *Resolved during this
   work.* At `#817e76` these measured 4.12:1 and 3.70:1, below the SC 1.4.3
   floor. The token is now `#908d85`, which measures 4.52:1 on the hardest
   field. The three-step text hierarchy is intact: the new value still sits well
   below `--paper-muted` (luminance 0.267 against 0.531). The remedy is
   documented at the token and pinned by a test that recomputes the ratio from
   `design-tokens.css` rather than trusting this table.
7. **`--line-dark` with any ink field**, per the structural table above.

### The raised-contrast remedy is already in the token layer

The `@media (prefers-contrast: more)` block (`design-tokens.css:1103`)
re-points the failing tokens. Computed the same way:

| Token | Default | Raised-contrast value | On `--ink-deep` | On `--ink-raised` |
|---|---|---|---:|---:|
| `--line-dark` | `#3c423f` | `--line-structural` (`#6b716e`) | 3.84 | 3.01 |
| `--paper-muted` | `#c7c0b3` | `#ded7ca` | 13.39 | not measured |
| `--paper-dim` | `#908d85` | `#b5b0a4` | 8.86 | 6.93 |

Every one of the three failing text and rule tokens clears its floor under
`prefers-contrast: more`. The defect is therefore that the *default* values do
not clear it, not that the palette lacks a compliant variant. The
`@media (forced-colors: active)` block (`design-tokens.css:1128`)
reasserts borders on the shell's structural elements with `ButtonBorder` and
swaps the focus ring to `Highlight`.

## What deliberately did not change

These were in scope to change and were left alone on purpose. Each is a
[Direction C](DIRECTION_C.md) commitment, not an accident of the redesign.

- **The palette.** Ten tokens, unchanged hex values — with one exception made
  during this work: `--paper-dim` moved from `#817e76` to `#908d85` because the
  original failed SC 1.4.3 on two of the four ink fields. The hue, the role, and
  its place in the three-step text hierarchy are unchanged; the value is a
  correction, not a new palette. The other failures above are recorded against
  the token layer and left alone deliberately, for the reason given in the
  1.4.11 entry.
- **The type pairing's role split.** Staatliches for display and compact
  uppercase labels, Barlow for body, forms, instructions, and every label a
  user has to read in order to act. `ViewHeader.vue` sets the step name in
  `--font-sans` and the step numeral in `--font-display`, which is the split
  being applied rather than a departure from it.
- **Square corners.** Base corner radius stays `0`; the only functional
  clearance is for focus.
- **Hard offset shadows.** Preserved for floating panels and overlays. Nothing
  was converted to soft elevation, blur, or glow.
- **No gradients, glass, or glow.** The redesign removed motion, not depth
  language.
- **The six-step journey order.** `DESKTOP_APPS` in
  [`useDesktop.js`](../../frontend/src/composables/useDesktop.js) is unchanged
  in content and order: state the decision, map the sources, set assumptions,
  run scenarios, decision brief, ask follow-ups. `JOURNEY_TOTAL` is derived from
  the list length, so the count and the order can never disagree.
- **The five-fact Truth Rail.** Still mounted exactly once, in the shell, and
  still unconditional. `frontend/src/__tests__/shell-ux-contract.spec.js`
  asserts both the mount and the absence of a conditional wrapper.

## Accepted, unresolved

Vocabulary is the legend defined in
[architecture/index.md](../architecture/index.md#state-legend-used-in-this-document).

### CURRENT

- The journey spine is a `<nav>` with `aria-current="step"`, open by default,
  and it is the only journey navigation in the shell.
- Panel layouts are deterministic and `focus` is the default; `split` and `free`
  are available and labelled in plain language as "One at a time", "Side by
  side", and "Floating".
- The panel switcher implements the tab pattern it declares, including
  `aria-controls`, a matching `tabpanel`, roving `tabindex`, arrow-key movement,
  `Home`, `End`, and `Delete` closing only the selected panel.
- Keyboard resize and single-pointer placement both exist, so dragging is never
  the only route to any panel operation.
- Focus is not obscured by floating panel chrome in the default layout, because
  the default layout has no floating chrome.
- One shared `ViewHeader.vue` supplies the single `h1` for all five route views;
  the second step counter, the per-view brand block, and four of the five
  footer truth-rail restatements are gone.
- The token layer defines every spacing step its components reference, a
  control-height scale anchored on `--target-min`, the four shell bands, one
  focus-ring definition, and the `prefers-contrast: more` and
  `forced-colors: active` blocks.
- Panel scroll containers transition `opacity` only.
- `Home.vue` leads with the composer, discloses source material and extra
  context behind native `<details>`, keeps both required sequence statements in
  visible text, and uses `aria-busy` for its loading regions.

### PARTIAL

- **SC 1.4.11 on structural rules.** `--line-dark` still measures 1.46 to 1.86:1
  on ink fields and still draws every band separator, panel edge, and input
  border. The redesign deliberately did not adopt `--line-structural` as the
  default: the compliant value is roughly three times the current luminance,
  and applying it everywhere would stop the ink fields reading as one dark
  mass, which is the whole character of the theme. It is shipped, it clears
  3.01:1 on the hardest field, `prefers-contrast: more` now selects it, and
  adopting it as the default is a one-token change for whoever wants it.
- **SC 1.4.3 on `--paper-dim` over raised ink.** Resolved during this work.
  `--paper-dim` was `#817e76` and failed on `--ink-soft` and `--ink-raised`; it
  is now `#908d85` and clears 4.5:1 on all four ink fields. Recorded here
  because the fix was part of this redesign and the value change is visible in
  a diff.
- **The Placement menu is not a complete menu widget.** It declares `role="menu"`
  with `role="menuitem"` children but has no roving focus, no arrow-key
  movement, and no `Escape` handler; `openPositionAndFocusFirst` currently only
  opens the menu. It is rendered only in the `free` layout.
- **A heading inside a live region.** `InteractionView.vue`'s loading-state
  section is `role="status"` with `aria-live="polite"` and carries a heading
  inside it. This was a second `<h1>` when first recorded and has since been
  demoted to `<h2>`, which resolves the duplicate-`h1` problem this entry
  originally described. Putting any heading inside a polite live region is
  still wrong: the announcement fires on content change, not on navigation, so
  the heading is read as a status message. Move the heading out of the region.
- **One view footer still restates the disclosure.** `InteractionView.vue`'s
  `app-footer-mini` repeats the zero-human and not-a-forecast statement that
  the shell's Truth Rail already carries.
- **The masthead descriptor is hidden on narrow viewports.** Under
  `max-width: 620px` `DesktopMasthead.vue` sets `.masthead-descriptor` to
  `display: none`, so the wordmark renders without its visible descriptor below
  that width. The link's `aria-label` still carries it.
- **Target size: floor met, product standard not.** `--target-min: 1.5rem`
  encodes the WCAG 2.2 AA floor of 24 by 24. [Direction C](DIRECTION_C.md) and
  [Accessibility](ACCESSIBILITY.md) both state 44 by 44 as the product's
  enhanced target; `--control-h-md` is 2.25rem and `--control-h-sm` is 1.75rem,
  both below 44px. The gap is real and is not closed by this change.
- **Focus-ring tokens are declared but not consumed.** `--focus-ring-color`,
  `--focus-ring-width`, and `--focus-ring-offset` exist
  (`design-tokens.css:98-100`) and the pre-existing global `:focus-visible` rule
  (`design-tokens.css:345-348`) still hard-codes `3px` and `3px`. There is now
  one *named* definition; there are not yet zero hard-coded copies.

### TARGET

- **A canonical semantic route list with an automated parity test.** Required by
  [ADR-0006](../architecture/adr/ADR-0006-route-map-list-parity.md) and still
  **not done**. There is no canonical list at the API or JSON-LD level that the
  visual map and the list view both consume, and there is no CI test asserting
  that every map fact has a list entry and vice versa. Nothing in this redesign
  advances that requirement, and this record must not be read as claiming it.
- **WCAG 2.2 conformance evidence.** No automated accessibility scan, no named
  screen-reader results, no focus-not-obscured capture, and no comprehension
  testing. [Accessibility](ACCESSIBILITY.md) records that requirement; this
  record does not satisfy it.
- **44 by 44 primary pointer targets** across every control family.
- **A focus ring that works on both ink and paper fields.** The palette has no
  compliant yellow-on-paper option, so a second ring token is needed.

### TRANSITION

- Decide whether `--line-structural` becomes the default. The token ships, it is
  wired into `prefers-contrast: more`, and the blocker is aesthetic rather than
  technical: every separator would lighten at once. A narrower option is to
  adopt it for the four band separators only and leave interior detail on
  `--line-dark`, which is most of the measured benefit for much less of the
  visual change.
- Complete the Placement menu as a WAI-ARIA menu button, with roving focus,
  arrow keys, and `Escape`, and give the resize grip `aria-valuenow`,
  `aria-valuemin`, and `aria-valuemax` readings of the current size.
- Rewrite `:focus-visible` to consume the focus-ring tokens, and add a paper
  field counterpart.
- Move `InteractionView.vue`'s loading heading out of its `role="status"` live
  region, and retire its remaining footer restatement.
- Keep the masthead descriptor visible at every width, or move it to a
  treatment that survives narrow viewports.
- Build the ADR-0006 semantic list and its parity test. This is the largest open
  item and it belongs to a different workstream.

## Truth-contract compliance note

The redesign removed seven naked-wordmark violations from the frontend and
retired them in the ratchet. Six violations remain, across five files, and they
are recorded in `acceptedDebt` in
`frontend/src/__tests__/product-truth-guard.spec.js`:

| File | Term | Surface |
|---|---|---|
| `frontend/index.html` | `respondents` | `content`, two occurrences |
| `frontend/src/components/Step4Report.vue` | `respondents` | `text` |
| `frontend/public/mark.svg` | `product-name` | `text` |
| `frontend/public/social-card.svg` | `product-name` | `text` |
| `frontend/src/views/NotFoundView.vue` | `product-name` | `text` |

None of the five files is one this redesign touched. The last three are the
`product-name` rule; the first two are the `respondents` term.

## References

- [Direction C — Civic Wayfinding](DIRECTION_C.md) — the design direction this
  record does not change, including its convergence ledger.
- [Accessibility](ACCESSIBILITY.md) — the WCAG 2.2 AA target, the keyboard
  contract, and the acceptance-evidence requirement.
- [ADR-0006 — Route map/list semantic parity](../architecture/adr/ADR-0006-route-map-list-parity.md)
  — the parity requirement that remains TARGET.
- [Architecture overview, Status of record](../architecture/index.md#status-of-record)
  — the single authoritative statement of gate status.
- [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/) —
  the conformance target.
- [Understanding WCAG 2.2 SC 1.4.11 Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
- [Understanding WCAG 2.2 SC 2.5.7 Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html)
- [Understanding WCAG 2.2 SC 2.5.8 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [Understanding WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)

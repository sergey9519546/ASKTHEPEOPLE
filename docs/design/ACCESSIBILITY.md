---
title: "Accessibility"
status: "Normative"
version: "1.1.0"
owner: "Accessibility Lead + Frontend Engineering"
last_reviewed: "2026-07-29"
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

### Current state — PARTIAL

- Frontend is Vue 3 + Vite + vue-router. Built into
  `frontend/dist/` and served by
  [`backend/app/__init__.py:317-325`](../../backend/app/__init__.py:317).
- The accessibility conformance target is WCAG 2.2; no
  conformance evidence is recorded.
- The semantic route list required by
  [`adr/ADR-0006-route-map-list-parity.md`](../architecture/adr/ADR-0006-route-map-list-parity.md)
  is not yet rendered.
- The Truth Rail and the per-screen contextual statements
  ([`docs/product/PRODUCT_TRUTH_CONTRACT.md`](../product/PRODUCT_TRUTH_CONTRACT.md))
  are not yet rendered in the frontend.
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

---
title: "UI/UX Design Analysis — Contemporary High-End Patterns vs. Current Implementation"
status: "Reference"
version: "1.0.0"
owner: "askthepeople-frontend-steward"
created: "2026-08-02"
last_reviewed: "2026-08-03"
research_cutoff: "2026-08-02"
applies_to: "frontend/src/*, design system, visual language"
---

# UI/UX Design Analysis: ASKTHEPEOPLE vs. 2026 High-End Patterns

## Executive Summary

**Current State:** ASKTHEPEOPLE has implemented a distinctive "Civic Wayfinding" design system with strong conceptual foundations: editorial clarity, semantic surfaces (paper/charcoal/white), hard-edged geometry, and truth-first disclosure. The implementation is **architecturally sound but visually under-realized**.

**Gap Analysis:** Comparing against 2026 high-end references (Linear, Stripe, Vercel, Bloomberg Terminal UX evolution, and civic design systems), ASKTHEPEOPLE has the right conceptual bones but needs **refinement in density, hierarchy, motion, and progressive disclosure** to match the polish of contemporary interfaces.

**Recommendation:** Tactical enhancements that preserve the civic editorial identity while elevating execution quality to match products shipping in 2026.

---

## 1. Benchmark Analysis: 2026 High-End Design Patterns

### 1.1 The Linear Standard (Dark-First Restraint)

**What Linear Does:**
- Extreme whitespace discipline: 32–64px vertical rhythm
- Typography as the primary hierarchy tool (not color)
- One interaction mode visible at a time
- Keyboard-first affordances (visible shortcuts, command palette prominence)
- Zero decorative elements in the primary workflow
- Subtle but consistent 2–4px borders for containment
- Monochrome + one accent (purple) used sparingly

**Application to ASKTHEPEOPLE:**
- ✅ **Already implemented:** Hard-edged geometry, minimal decoration, compressed display type
- ⚠️ **Needs refinement:** Vertical rhythm is inconsistent (compare `decision-composer` padding to `method-section` spacing)
- ❌ **Missing:** Keyboard shortcuts are not visually surfaced; command palette would elevate power-user workflows

---

### 1.2 The Stripe Pattern (Data Table Excellence)

**What Stripe Does:**
- Table typography: tabular numerals, monospace for IDs, 13–14px body with tight line-height
- Row zebra striping is subtle (2–3% opacity difference)
- Hover states are instant and consistent (background + border change together)
- Status pills are small (18–20px height), uppercase, 10–11px type
- Dense information presented without feeling cramped (16–20px row height for tables)
- Action buttons never inside the table; always in a dedicated column or row toolbar

**Application to ASKTHEPEOPLE:**
- ✅ **Already specified:** Tabular numerals for IDs in content system
- ⚠️ **Inconsistent:** Run list rows are 7rem tall (112px) — this is **dashboard scale**, not data-table scale
- ❌ **Missing:** Source-to-starting-condition ledger (Step 2) is not yet implemented; when it is, apply Stripe's table density

**Recommendation:** Step 2 and Step 5 list views should use **compact table treatment** (48–56px row height, not 112px). Step 1 decision composer can remain large (it's a form, not a data table).

---

### 1.3 The Vercel Aesthetic (Blueprint Grid + Technical Precision)

**What Vercel Does:**
- Subtle dot or line grid at 24–32px intervals (2–4% opacity)
- Monochrome base (black/white) with rare blue accent
- Typography contrast: compressed sans for headlines, regular for body
- "Engineering paper" metaphor: grids, coordinates, technical labels
- Animation is **subtle and purposeful** (100–200ms ease-out, no bounces)
- Zero gradients, zero glassmorphism, zero shadows (except rare 1px hard offset)

**Application to ASKTHEPEOPLE:**
- ✅ **Conceptually aligned:** Blueprint/route-map metaphor, hard geometry, no glass/blur
- ⚠️ **Under-utilized:** Grid background in `method-section` is visible but not leveraged elsewhere
- ❌ **Missing:** Coordinate labels, technical metadata (run IDs, timestamps, version hashes) could be styled as "engineering annotations"

**Recommendation:** Extend the grid treatment to the route-map canvas; add subtle coordinate labels (`SC-01`, `P-03`) styled as technical annotations (10–11px uppercase, 40% opacity).

---

### 1.4 Bloomberg Terminal UX Evolution (Concealing Complexity)

**What Bloomberg Does:**
- **Primary/secondary/tertiary information hierarchy** is ruthless
- Advanced functions are hidden in keyboard shortcuts, not visible by default
- "Launchpad" pattern: one workflow path visible, diagnostics in inspector
- High-density data for power users, but **never all at once**
- Status indicators are small, consistent, and always in the same position
- Color is reserved for **state and alert**, not decoration

**Application to ASKTHEPEOPLE:**
- ✅ **Already specified:** Inspector pattern, progressive disclosure, primary/secondary actions
- ⚠️ **Implementation gap:** Current UI shows diagnostics and primary workflow with equal visual weight
- ❌ **Missing:** Run record inspector is not yet implemented; when it is, ensure it's **tertiary** (collapsed by default, never as large as primary content)

**Recommendation:** Step 5 (Explore Paths) should show **map OR list** as primary, with inspector as slide-out drawer (320–360px, right edge, collapsed by default).

---

### 1.5 Gov.UK / Civic Design Systems (Accessibility-First Editorial)

**What Gov.UK Does:**
- Maximum 68-character line length for body text
- 48×48px minimum touch targets (not the WCAG AA minimum)
- **Check answers** pattern before every consequential action
- Error summary at page top, linked to fields
- No color-only meaning; always redundant text label
- Plain language: "What happens next" instead of "Status"

**Application to ASKTHEPEOPLE:**
- ✅ **Already specified:** Check-answers at Step 4, plain-language states, 44×44px touch targets, no color-only
- ⚠️ **Partial:** Error handling in `Home.vue` uses inline messages, but no error summary pattern
- ❌ **Missing:** "What happens next" section after Step 7 (research handoff); user is left without clear next action

**Recommendation:** Add explicit "What happens next" sections after Steps 4, 6, and 7. Use Gov.UK's three-part structure: (1) what we did, (2) what you can do now, (3) what happens next.

---

## 2. Current Implementation Strengths

### 2.1 Conceptual Clarity
The Civic Wayfinding system has **strong semantic architecture**:
- Surface semantics (paper/charcoal/white) are conceptually sound
- Route grammar is well-defined and normative
- Truth Rail is a unique, memorable disclosure pattern
- Typography choices (Archivo Narrow + Source Sans 3) support the editorial voice

### 2.2 Accessibility Foundation
The design system specifies:
- WCAG 2.2 AA target (with selected AAA enhancements)
- Keyboard-first operation
- Screen-reader labels for route semantics
- Reduced-motion support
- No color-only meaning

### 2.3 Responsive Strategy
Mobile-first patterns are specified:
- List view as default on mobile (not miniaturized map)
- Vertical stacking, no horizontal panning
- 320px minimum width
- Touch targets at 44×44px

---

## 3. Identified Gaps (Tactical Fixes)

### 3.1 **Density and Rhythm Inconsistency**

**Issue:** Visual density varies wildly between sections.

| Element | Current | Benchmark | Recommendation |
|---|---:|---:|---|
| Run list row | 112px | 48–64px (data list) | **64px** for balance |
| Decision composer | ~12rem (192px) | Variable (form) | **Keep** (form context) |
| Method section padding | 3.5–7.5rem | 4–6rem | **Tighten to 4–5rem** |
| Section heading gap | 3rem | 2–3rem | **2rem** for faster scanning |

**Fix:** Establish three density modes:
1. **Form density** (Step 1): generous padding, large type
2. **Data density** (Step 2, 5): compact rows, tabular layout
3. **Reading density** (Step 6): 680–760px column, 24–32px rhythm

---

### 3.2 **Hierarchy: Everything Looks Primary**

**Issue:** Current `Home.vue` gives equal visual weight to:
- Decision input (primary)
- Recent runs (secondary)
- Templates (tertiary)

All three sections use similar heading sizes, spacing, and contrast.

**Fix — Apply Bloomberg's Primary/Secondary/Tertiary Scale:**

| Level | Size | Weight | Spacing Above | Use |
|---|---:|---:|---:|---|
| Primary | 48–56px | 900 | 0 | Current step title |
| Secondary | 32–40px | 700–900 | 64–96px | Section heading |
| Tertiary | 20–24px | 600–700 | 32–48px | Inspector, metadata |

**Specific changes:**
- Decision section: **Primary** (hero treatment, current size OK)
- Method section: **Secondary** (reduce h2 from 5rem to 3.5–4rem)
- Recent runs: **Secondary** (current size OK)
- Templates: **Tertiary** (reduce h2 from 5rem to 2.5–3rem, move below fold)

---

### 3.3 **Motion: Stiff Transitions**

**Issue:** Current motion is minimal (good!) but some transitions feel abrupt.

**Current motion budget:**
```css
transition: transform 220ms var(--ease-out);
```

**Fix — Three-tier motion system:**

| Interaction | Duration | Easing | Use |
|---|---:|---|---|
| **Instant** | 0–60ms | Linear | Hover state, focus ring |
| **Quick** | 100–180ms | `cubic-bezier(0.2, 0, 0.2, 1)` | Button press, dropdown, tooltip |
| **Deliberate** | 220–320ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Panel slide, route draw, page transition |

**Specific changes:**
- Button hover: **100ms** (currently 220ms feels sluggish)
- Route draw animation: **280ms** (currently 820ms is too theatrical)
- Panel transitions: **240ms** (when inspector is added)

---

### 3.4 **Progressive Disclosure: Under-Utilized**

**Issue:** Step 3 (Review Assumptions) is specified as a task list but not yet implemented. When it is, it should use **stacked disclosure**, not a dashboard.

**Pattern to implement:**

```
✓ READY         Decision question
✓ READY         Source material
⚠ NEEDS REVIEW  2 assumptions             [Review →]
⚠ NEEDS REVIEW  1 generated profile        [Review →]
✓ READY         Scenario rules

Each section expands inline when clicked. Only one section open at a time.
```

**Reference:** Linear's issue detail panel — one focused task, with metadata in collapsed sections below.

---

### 3.5 **Typography Tuning**

**Issue:** Type scale is close but needs refinement for 2026 standards.

**Current:**
```css
.masthead-copy h1 {
  font-size: clamp(3rem, 4.7vw, 5.7rem); /* 48–91px */
}
```

**Benchmark (Linear, Stripe, Vercel):**
- Hero: 56–72px (not 91px)
- H1: 36–48px
- H2: 24–32px
- Body: 15–16px (not 16–17px)
- Small: 13–14px (not 12–13px)

**Fix:**
```css
/* Tighten the scale */
--font-hero: clamp(3.5rem, 4vw, 4.5rem);    /* 56–72px */
--font-h1: clamp(2.25rem, 2.5vw, 3rem);     /* 36–48px */
--font-h2: clamp(1.5rem, 1.8vw, 2rem);      /* 24–32px */
--font-body: 15px;                          /* 15px fixed */
--font-small: 13px;                         /* 13px fixed */
```

---

## 4. Advanced Enhancements (Phase 2)

### 4.1 **Command Palette**

**Why:** Power users expect keyboard-first navigation in 2026.

**Pattern:** `Cmd+K` / `Ctrl+K` opens a fuzzy-search command palette:
- Jump to decision
- Jump to run
- Create new decision
- Export current view
- Open settings

**Reference:** Linear, Raycast, GitHub

---

### 4.2 **Route Map: Technical Annotation Layer**

**Why:** The route map is conceptually strong but visually plain.

**Enhancement:** Add subtle "engineering annotations":
- Node IDs at 10px, 40% opacity, positioned as margin notes
- Timestamp overlays for run stages (ISO 8601, monospace, 11px)
- Grid coordinates (A1, A2, B1, B2) at canvas edges
- "This is a synthetic route, not observed behavior" watermark at 6% opacity

**Reference:** Vercel's blueprint aesthetic, Bloomberg's metadata layering

---

### 4.3 **Micro-Interactions**

**Why:** High-end 2026 interfaces feel responsive without being distracting.

**Add:**
- **Button press:** Subtle scale-down on click (`transform: scale(0.98)`)
- **List item selection:** 2px left border slides in (100ms)
- **Route highlight:** Path thickens from 3.5px to 5px on hover (120ms)
- **Toast enter/exit:** Slide from right + fade (180ms ease-out)

**Reference:** Stripe's button feedback, Linear's list selection

---

### 4.4 **Dark Mode Refinement**

**Current:** Charcoal (`#111313`) is the primary surface.

**Enhancement:** Offer a **pure black mode** for OLED displays:
- Background: `#000000`
- Text: `#E5E5E5` (not pure white)
- Rules: `#1A1A1A`
- Signal: Keep `#FFD51D`

**Reference:** Linear's true-black mode, Twitter's OLED theme

---

## 5. What to Preserve (Do Not Change)

### 5.1 **Semantic Surface System**
The paper/charcoal/white narrative is **unique and effective**. Do not replace it with generic light/dark modes.

### 5.2 **Truth Rail**
The five-cell desktop rail is **memorable and functional**. Do not reduce it to a footer disclaimer.

### 5.3 **Hard Geometry**
Zero border radius (except 2px for focus) is **intentional and civic**. Do not add rounded corners.

### 5.4 **Typography Pairing**
Archivo Narrow + Source Sans 3 is **appropriate**. Do not replace with Inter or Geist.

### 5.5 **Route Grammar**
Equal-weight paths, no quantitative encoding, direct labels — this is **architecturally sound**. Do not add thickness = probability.

---

## 6. Implementation Priority (High → Low)

### P0 — Foundational Fixes (Gate 5)
1. **Density normalization:** 64px run rows, 48–56px table rows
2. **Hierarchy tuning:** Reduce method/template headings by 25–30%
3. **Motion timing:** 100ms hover, 280ms route draw, 240ms panels
4. **Typography scale:** Tighten to 56–72px max hero

### P1 — Progressive Disclosure (Gate 5)
1. **Step 3 task list:** Implement stacked disclosure pattern
2. **Inspector pattern:** 320–360px right drawer, collapsed by default
3. **Error summary:** Add page-top summary linking to fields

### P2 — Power-User Tools (Post-Gate 5)
1. **Command palette:** `Cmd+K` search and navigation
2. **Keyboard shortcuts:** Surface them in UI (tooltips, help panel)
3. **Route annotations:** Technical metadata layer

### P3 — Polish (Post-Launch)
1. **Micro-interactions:** Button press, list selection, route hover
2. **True black mode:** OLED-optimized dark variant
3. **Blueprint grid:** Extend to route canvas, add coordinate labels

---

## 7. Validation Checklist

Before shipping visual refinements, validate:

- [ ] **Density:** Three distinct modes (form, data, reading) are implemented
- [ ] **Hierarchy:** Primary/secondary/tertiary scale is consistent across all views
- [ ] **Motion:** No transition exceeds 320ms; hover states are under 120ms
- [ ] **Typography:** Hero never exceeds 72px; body is 15–16px
- [ ] **Progressive disclosure:** Advanced features are collapsed by default
- [ ] **Accessibility:** All changes pass WCAG 2.2 AA (contrast, keyboard, screen reader)
- [ ] **Truth integrity:** No visual change undermines the synthetic/non-forecast boundary
- [ ] **Route grammar:** No change introduces quantitative encoding

---

## 8. References

### 8.1 High-End Benchmarks (2026)
- **Linear:** Dark-first restraint, keyboard shortcuts, whitespace discipline
- **Stripe:** Data table density, status pills, tabular numerals
- **Vercel:** Blueprint grid, technical precision, monochrome + accent
- **Bloomberg Terminal UX:** Primary/secondary/tertiary hierarchy, progressive disclosure
- **Gov.UK Design System:** Check answers, error summary, plain language

### 8.2 Design Systems Referenced
- [Linear Design](https://linear.app) — Live product
- [Stripe Dashboard](https://dashboard.stripe.com) — Live product (requires auth)
- [Vercel Aesthetic Guide](https://www.setproduct.com/blog/complete-guide-to-blueprint-grid-design) — Analysis
- [Bloomberg UX Blog](https://www.bloomberg.com/ux/) — Case studies
- [Gov.UK Design System](https://design-system.service.gov.uk/) — Public reference

### 8.3 Accessibility Standards
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) — Current conformance target
- [Accessible Charts Guide](https://www.adacompliancepros.com/blog/accessible-charts) — Data visualization
- [Tableau Accessibility Guide](https://help.tableau.com/current/pro/desktop/en-us/accessibility_overview.htm) — Dashboard patterns

### 8.4 2026 Design Trends
- [SaaS UI Design Trends 2026](https://www.saasui.design/blog/7-saas-ui-design-trends-2026) — Analysis
- [Brutalist/Editorial Trend](https://www.setproduct.com/blog/retro-brutalist-ui-design-2026) — Context
- [Progressive Disclosure UX](https://www.uxpin.com/studio/blog/what-is-progressive-disclosure/) — Pattern reference

---

## 9. Conclusion

**ASKTHEPEOPLE's Civic Wayfinding system has the right conceptual foundation.** The semantic surfaces, truth-first disclosure, and route grammar are **architecturally strong and unique**.

**The gap is execution refinement, not direction.** By adopting tactical fixes from 2026 high-end patterns—density normalization, hierarchy tuning, motion polish, progressive disclosure—the interface can match the quality bar of Linear, Stripe, and Vercel **without abandoning its civic editorial identity**.

**Next steps:**
1. Implement P0 fixes (density, hierarchy, motion, typography)
2. Build out Step 3 and Step 5 list views with progressive disclosure
3. Add inspector pattern for run records
4. Validate with accessibility and comprehension tests

The result will be a **high-end civic interface** that earns trust through precision, clarity, and restraint.

---

*This analysis was prepared by the askthepeople-frontend-steward agent on 2026-08-02, based on the normative design system in `docs/design/` and contemporary research on high-end web interfaces shipping in 2026.*

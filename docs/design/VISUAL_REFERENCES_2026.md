---
title: "Visual References — 2026 High-End Design Systems"
status: "Reference"
version: "1.0.0"
owner: "askthepeople-frontend-steward"
created: "2026-08-02"
last_reviewed: "2026-08-03"
research_cutoff: "2026-08-02"
applies_to: "frontend/src/*, design system refinement"
---

# Visual References: 2026 High-End Design Systems

This document provides extracted specifications from contemporary high-end interfaces to inform ASKTHEPEOPLE's visual refinement while preserving its unique civic identity.

---

## 1. Linear Design System

### Color Palette (Dark-First)

**Surface Hierarchy** (4-step ladder for depth without shadows):
```css
--canvas: #010102;           /* Near-black with blue tint (not pure black) */
--surface-1: #0f1011;
--surface-2: #141516;
--surface-3: #18191a;
--surface-4: #191a1b;
```

**Text Hierarchy**:
```css
--ink: #f7f8f8;              /* Primary text */
--ink-muted: #d0d6e0;        /* Secondary text */
--ink-subtle: #8a8f98;       /* Tertiary labels */
--ink-tertiary: #62666d;     /* Metadata, timestamps */
```

**Borders**:
```css
--hairline: #23252a;         /* Default dividers */
--hairline-strong: #34343a;  /* Emphasized borders */
--hairline-tertiary: #3e3e44; /* Subtle container edges */
```

**Brand Accent** (single chromatic color):
```css
--primary: #5e6ad2;          /* Lavender-blue for CTA, focus, brand */
--primary-hover: #828fff;
--primary-focus: #5e69d1;
```

**Semantic**:
```css
--success: #27a644;          /* Green for completed states */
```

### Typography

**Typefaces**:
- Linear Display (headlines)
- Linear Text (body)
- Linear Mono (code)
- **Substitute**: Inter (500/600/700) or Geist Sans

**Scale with Negative Letter-Spacing**:
| Size | Weight | Tracking | Use |
|---:|---:|---:|---|
| 80px | 600 | -3.0px | Hero display |
| 56px | 600 | -1.8px | Section headline |
| 40px | 600 | -1.0px | Page title |
| 28px | 500 | -0.6px | Subsection |
| 16px | 400 | -0.05px | Body text |
| 12px | 500 | +0.4px | Eyebrow labels (uppercase) |

**Key principle**: Aggressive negative tracking on display type (~4% of font size at top scale).

### Layout & Spacing

**Spacing Scale** (4px base, 9 steps):
```
4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px
```

**Border Radius** (8 steps):
```
4px, 8px (base), 12px, 16px, 20px, 24px, pill (100px), full (9999px)
```

### Design Principles

1. **Dark-only canvas** — Never pure black (#000000), always tinted (#010102)
2. **Single chromatic accent** — Lavender for brand/focus/CTA only
3. **Four-step surface ladder** — Hierarchy without drop shadows
4. **Generous whitespace** — 32–64px vertical rhythm
5. **Typography as hierarchy** — Not color or size alone

### Application to ASKTHEPEOPLE

**What to adopt**:
- ✅ Four-step surface ladder (charcoal already has this foundation)
- ✅ Aggressive negative tracking on display type (-2% at 48px+)
- ✅ 4px spacing base (already specified)
- ✅ Single accent discipline (yellow signal is already this)

**What NOT to adopt**:
- ❌ Lavender accent (keep yellow #FFD51D)
- ❌ Dark-only approach (paper surface is core to semantic system)
- ❌ Linear's specific typefaces (Archivo Narrow + Source Sans 3 are appropriate)

---

## 2. Vercel Design System

### Color Palette (Stark Minimalism)

**Surfaces**:
```css
--canvas: #ffffff;           /* Pure white */
--canvas-soft: #fafafa;      /* Body background */
--canvas-soft-2: #f5f5f5;    /* Nested container */
```

**Ink** (primary brand color):
```css
--primary-ink: #171717;      /* Near-black, carries ALL CTAs and headlines */
```

**200-Step Gray Scale**:
```css
--hairline: #ebebeb;         /* Lightest divider */
--hairline-strong: #a1a1a1;  /* Emphasized border */
--body-text: #4d4d4d;        /* Primary text */
--mute: #888888;             /* Secondary text */
```

**Semantic & Accent**:
```css
--link-blue: #0070f3;        /* Inline links only (not brand accent) */
--link-deep: #0761d1;
--success: #0070f3;
--error: #ee0000;
--warning: #f5a623;
```

**Mesh Gradient** (hero-scale only, never miniaturized):
- Develop: `#007cf0 → #00dfd8`
- Preview: `#7928ca → #ff0080`
- Ship: `#ff4d4d → #f9cb28`

### Typography

**Typeface**: Geist (display, body, UI) + Geist Mono (code)

**Weights**: 400 / 500 / 600 only — "display caps at weight 600"

**Tracking**: Aggressive negative letter-spacing
| Size | Tracking |
|---:|---:|
| 48px | -2.4px |
| 32px | -1.28px |

**Scale**: 12px → 48px (controlled maximum)

### Spacing

**12 values** (4px base):
```
4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 80px, 96px, 128px, 192px
```

### Border Radius

**Two distinct scales** (never mixed on one screen):
- **Marketing**: 100px pill (signature element)
- **App UI**: 6px squared buttons

**Full scale**: 0px, 6px, 8px (base), 12px, 16px, 100px, 9999px

### Elevation & Shadows

**"Stacked shadows over single drops"**:
```css
/* Subtle drop */
box-shadow:
  0 0 0 1px rgba(0,0,0,0.08) inset,
  0 2px 4px rgba(0,0,0,0.04);

/* Soft stack */
box-shadow:
  0 0 0 1px rgba(0,0,0,0.08) inset,
  0 4px 8px rgba(0,0,0,0.06),
  0 8px 16px rgba(0,0,0,0.04);

/* Float stack (modals) */
box-shadow:
  0 0 0 1px rgba(0,0,0,0.08) inset,
  0 8px 16px rgba(0,0,0,0.08),
  0 16px 32px rgba(0,0,0,0.06);
```

### Design Principles

1. **Single-color discipline** — Primary #171717 for every CTA, never softened
2. **Restraint as product** — No second accent, no weight above 600, no gradient miniaturization
3. **Polarity-flipped sections** — Dark bands use white-on-ink (no new colors)
4. **Stark minimalism** — "One of the strictest stark systems on the web"
5. **Sentence-case headlines** — No all-caps display treatments

### Application to ASKTHEPEOPLE

**What to adopt**:
- ✅ Stacked shadows (paper surface 4px hard offset could become layered)
- ✅ Controlled maximum type size (48px hero, not 91px)
- ✅ Single-color discipline (yellow signal already follows this)
- ✅ Sentence-case headlines (already specified in content system)

**What NOT to adopt**:
- ❌ Pure white canvas (paper #F2EBDD is warmer and more editorial)
- ❌ 100px pill radius (0px hard geometry is civic identity)
- ❌ Geist typeface (Archivo Narrow is more compressed/civic)

---

## 3. Blueprint Grid Pattern

### Grid Specifications

**Line Grid** (subtle, almost subliminal):
```css
.blueprint-grid {
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
  background-size: 24px 24px;
}
```

**Dot Matrix**:
```css
.dot-grid {
  background-image: radial-gradient(
    circle,
    rgba(0, 0, 0, 0.1) 1px,
    transparent 1px
  );
  background-size: 16px 16px;
}
```

**Specifications**:
- **Line weight**: 1px
- **Spacing**: 16px or 24px (based on 8px/16px unit system)
- **Opacity**: 10–20% (15% optimal — "barely visible")
- **Color**: Light gray on light backgrounds, subtle white on dark
- **Principle**: "Almost subliminal, never competes with content"

### Technical Annotation Layer

**Coordinate Labels**:
- **Size**: 10–11px
- **Opacity**: 40%
- **Font**: Monospace (Geist Mono, JetBrains Mono, or Source Code Pro)
- **Placement**: Canvas edges (A1, A2, B1, B2)

**Metadata Overlays**:
- **Timestamps**: ISO 8601, monospace, 11px
- **Node IDs**: 10px, 40% opacity, positioned as margin notes
- **Watermarks**: 6% opacity, large display type

### Application to ASKTHEPEOPLE

**What to adopt**:
- ✅ Blueprint grid on route-map canvas (24px, 15% opacity)
- ✅ Technical annotations (node IDs at 10px, 40% opacity)
- ✅ Coordinate labels at canvas edges
- ✅ Monospace for run IDs, timestamps, technical metadata

**Current implementation**:
- ✅ Already has grid in `method-section` (2.5rem = 40px spacing)
- ⚠️ Not yet applied to route-map canvas
- ❌ No coordinate labels or technical annotations

---

## 4. Gov.UK Design System (Check Answers Pattern)

### Layout Structure

**Grid**:
- **Desktop**: Two-thirds layout (`govuk-grid-column-two-thirds-from-desktop`)
- **Mobile**: Full-width, single column
- **Max line length**: 68 characters for body text

**Component Structure**:
```html
<dl class="govuk-summary-list">
  <div class="govuk-summary-list__row">
    <dt class="govuk-summary-list__key">Question</dt>
    <dd class="govuk-summary-list__value">Answer</dd>
    <dd class="govuk-summary-list__actions">
      <a href="#">Change <span class="govuk-visually-hidden">question</span></a>
    </dd>
  </div>
</dl>
```

### Spacing

**Vertical rhythm**:
- Between sections: `govuk-!-margin-bottom-9` (~40px)
- Within summary list: ~16px rows
- Action links: Right-aligned in third column

### Typography

**Scale**:
- **H1**: `govuk-heading-l` (~36px)
- **H2**: `govuk-heading-m` (~24px)
- **Body**: `govuk-body` (19px on desktop, 16px on mobile)

### Interaction Patterns

**Change Links**:
- Text: "Change" + visually hidden context
- Returns user to specific question with pre-populated answer
- After editing, "Continue" returns to check answers page

**Navigation Flow**:
- Back link at top
- Declaration text before submission
- Primary button with clear action description ("Accept and send application")

### Accessibility

**Screen Reader Support**:
- Hidden text in change links: `<span class="govuk-visually-hidden"> name</span>`
- Semantic HTML: `<dl>`, `<dt>`, `<dd>` for key-value pairs
- Proper heading hierarchy
- Main landmark with `role="main"` and `id="main-content"`

**Touch Targets**:
- **Minimum**: 44×44px (WCAG 2.2 AA enhanced target, not the 24×24px minimum)

### Application to ASKTHEPEOPLE

**What to adopt**:
- ✅ Summary list pattern for Step 4 (Check this run)
- ✅ "What happens next" sections after Steps 4, 6, 7
- ✅ Error summary at page top, linked to fields
- ✅ 44×44px touch targets (already specified)
- ✅ Visually hidden text for screen readers

**Already implemented**:
- ✅ Check-answers pattern specified in Step 4
- ✅ Plain-language states
- ⚠️ Error summary pattern not yet implemented

---

## 5. 2026 SaaS UI Trends — Core Patterns

### 1. Strategic Minimalism (Calm Design)

**Visual Characteristics**:
- **Whitespace**: 32–64px vertical rhythm (generous, functional)
- **Hierarchy**: Typography does heavy lifting, minimal icon usage
- **Density**: Low by default, progressive disclosure for complexity
- **Formula**: Confidence > Complexity

**Pattern**:
```
Primary task (large, clear)
  ↓
Secondary diagnostics (collapsed by default)
  ↓
Tertiary advanced settings (hidden until needed)
```

**Examples**: Linear's issue list, Calendly's calendar

### 2. Command Palettes (Cmd+K as Standard)

**Interaction**:
- **Trigger**: Global `Cmd+K` / `Ctrl+K`
- **Features**: Actions + navigation + fuzzy search
- **Hierarchy**: Recent items first (zero typing for common tasks)
- **Keyboard navigation**: Arrow keys, Enter to execute, Esc to close

**Visual**:
- **Overlay**: Modal dialog, centered, 600–640px wide
- **Search input**: Large (44–48px height), autofocused
- **Results**: Grouped by type (Actions, Navigation, Recent)
- **Keyboard hints**: Visible shortcuts (e.g., "⌘ + K")

**Examples**: Linear, Slack, GitHub, Raycast

### 3. Progressive Disclosure

**Three-Layer Hierarchy**:

| Layer | Visibility | Use | Example |
|---|---|---|---|
| **Primary** | Always visible | Core workflow | Decision input, current step |
| **Secondary** | Collapsed by default, one click away | Related tasks, context | Inspector, run history |
| **Tertiary** | Hidden until demonstrated need | Advanced settings, diagnostics | Model configuration, API keys |

**Pattern**:
```
Empty state → One action
Basic usage → Core features visible
Power user → Advanced features revealed
```

**Timing**: Features revealed at moment of demonstrated need, not upfront

### 4. Density Modes

**Three distinct scales** (never mixed on one screen):

| Mode | Row Height | Font Size | Use | Example |
|---|---:|---:|---|---|
| **Form** | 80–120px | 16–18px | Input, review, editorial | Step 1, Step 6 |
| **Data table** | 48–64px | 13–15px | Lists, ledgers | Step 2, Step 5 list |
| **Dashboard** | 80–96px | 14–16px | Cards, summaries | Home, run cards |

**Linear's density**:
- Issue list: 56px rows
- Sidebar: 32px rows
- Settings: 64px rows

**Stripe's density**:
- Payment list: 52px rows
- Customer table: 48px rows
- Inline forms: 40px input height

### 5. Motion Timing

**Three-tier system**:

| Tier | Duration | Easing | Use |
|---|---:|---|---|
| **Instant** | 0–60ms | Linear | Hover, focus ring |
| **Quick** | 100–180ms | `cubic-bezier(0.2, 0, 0.2, 1)` | Button, dropdown, tooltip |
| **Deliberate** | 220–320ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Panel slide, modal, page transition |

**Principle**: Motion communicates sequence, never probability or intelligence

**Reduced motion**: All animations resolve to final state immediately

### 6. Micro-Interactions

**Subtle feedback**:
- **Button press**: Scale-down (`transform: scale(0.98)`) for 100ms
- **List selection**: 2px left border slides in (100ms)
- **Hover**: Background + border change together (60–100ms)
- **Focus**: Instant 2px outline + subtle glow (0ms)

**Examples**:
- Stripe's button feedback
- Linear's list selection
- Vercel's hover states

---

## 6. Comparison Matrix: ASKTHEPEOPLE vs. Benchmarks

### Color Strategy

| System | Primary | Accent | Surfaces | Strategy |
|---|---|---|---|---|
| **Linear** | Near-black (#010102) | Lavender (#5e6ad2) | 4-step dark ladder | Dark-first, single accent |
| **Vercel** | Near-black (#171717) | None (blue for links only) | White + near-white | Stark minimalism |
| **ASKTHEPEOPLE** | Ink (#111313) | Signal (#FFD51D) | Paper (#F2EBDD) + Charcoal | **Semantic surfaces** ✨ |

**Verdict**: ASKTHEPEOPLE's semantic surface system (paper/charcoal/white) is **more distinctive** than Linear/Vercel. Preserve it.

### Typography Scale

| System | Hero Max | H1 | Body | Tracking |
|---|---:|---:|---:|---|
| **Linear** | 80px | 40px | 16px | -3.0px at 80px |
| **Vercel** | 48px | 32px | 16px | -2.4px at 48px |
| **ASKTHEPEOPLE (current)** | 91px | 48px | 16–17px | Not specified |
| **ASKTHEPEOPLE (proposed)** | **72px** | **40px** | **15px** | **-2.4px at 72px** |

**Verdict**: Current hero is too large. Tighten to 72px max.

### Spacing Scale

| System | Base | Steps | Max Section Gap |
|---|---:|---:|---:|
| **Linear** | 4px | 9 steps | 96px |
| **Vercel** | 4px | 12 steps | 192px |
| **ASKTHEPEOPLE** | 4px | 9 steps | 96px |

**Verdict**: Spacing scale is aligned. Keep it.

### Border Radius

| System | Base | Max | Philosophy |
|---|---:|---:|---|
| **Linear** | 8px | Pill (100px) | Soft, rounded |
| **Vercel** | 8px | Pill (9999px) | Mixed (6px app, 100px marketing) |
| **ASKTHEPEOPLE** | 0px | 2px (focus only) | **Hard civic geometry** ✨ |

**Verdict**: Hard geometry is a **strength**. Do not add rounded corners.

### Density (Data List Row Height)

| System | Row Height | Font Size | Use |
|---|---:|---:|---|
| **Linear** | 56px | 14px | Issue list |
| **Stripe** | 48–52px | 13–14px | Payment/customer table |
| **ASKTHEPEOPLE (current)** | 112px | 14px+ | Run list |
| **ASKTHEPEOPLE (proposed)** | **64px** | **14px** | Run list (data mode) |

**Verdict**: Current run list is **too tall** for data context. Reduce to 64px.

### Motion Timing

| System | Hover | Button | Panel | Route Draw |
|---|---:|---:|---:|---:|
| **Linear** | 100ms | 120ms | 240ms | — |
| **Vercel** | 60ms | 100ms | 220ms | — |
| **ASKTHEPEOPLE (current)** | 220ms | 220ms | — | 820ms |
| **ASKTHEPEOPLE (proposed)** | **100ms** | **120ms** | **240ms** | **280ms** |

**Verdict**: Current timing is **too slow**. Adopt 2026 standard.

---

## 7. Visual Mockup Patterns (Text-Based)

### Pattern A: Run List (Current vs. Proposed)

**Current (112px rows, heavy)**:
```
╔═══════════════════════════════════════════════════════════════════╗
║ 01  [                                                           ] ║
║     [  What could happen if we launch in Q3?                    ] ║
║     [  Aug 1, 2026                                Ready to review] ║
║                                                                [→] ║
╠═══════════════════════════════════════════════════════════════════╣
║ 02  [                                                           ] ║
║     [  Should we prioritize mobile-first design?                ] ║
║     [  Jul 29, 2026                              Ready to review] ║
║                                                                [→] ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Proposed (64px rows, data-table density)**:
```
╔═══════════════════════════════════════════════════════════════════╗
║ 01  What could happen if we launch in Q3?           Ready  [→] ║
║     Aug 1, 2026                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║ 02  Should we prioritize mobile-first design?       Ready  [→] ║
║     Jul 29, 2026                                                  ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Pattern B: Step 3 Progressive Disclosure

**Stacked disclosure (Linear pattern)**:
```
╔═══════════════════════════════════════════════════════════════════╗
║ ✓ READY         Decision question                                ║
║ ✓ READY         Source material                                  ║
║ ⚠ NEEDS REVIEW  2 assumptions                         [Review →] ║
║ ⚠ NEEDS REVIEW  1 generated profile                   [Review →] ║
║ ✓ READY         Scenario rules                                   ║
╚═══════════════════════════════════════════════════════════════════╝

Click "Review" expands inline:

╔═══════════════════════════════════════════════════════════════════╗
║ ⚠ NEEDS REVIEW  2 assumptions                         [Review →] ║
║                                                                   ║
║   ┌─────────────────────────────────────────────────────────────┐║
║   │ Assumption A-01                                             │║
║   │ Users prefer mobile-first interfaces for quick tasks       │║
║   │                                                             │║
║   │ [Edit] [Accept] [Ignore]                                   │║
║   └─────────────────────────────────────────────────────────────┘║
║                                                                   ║
║   ┌─────────────────────────────────────────────────────────────┐║
║   │ Assumption A-02                                             │║
║   │ Response time matters more than feature completeness       │║
║   │                                                             │║
║   │ [Edit] [Accept] [Ignore]                                   │║
║   └─────────────────────────────────────────────────────────────┘║
╚═══════════════════════════════════════════════════════════════════╝
```

### Pattern C: Inspector Pattern (Step 5)

**Primary + Secondary + Tertiary Hierarchy**:
```
╔═════════════════════════════════════════╦═══════════════════════╗
║                                         ║ RUN RECORD        [×] ║
║  PRIMARY: Route Map                     ║─────────────────────  ║
║  (Map view fills this space)            ║ RELATED BY KEYWORD    ║
║                                         ║ NOT A CITATION        ║
║                                         ║─────────────────────  ║
║                                         ║                       ║
║                                         ║ Record R-01           ║
║                                         ║ Similar context...    ║
║                                         ║                       ║
║                                         ║ Record R-02           ║
║                                         ║ Related theme...      ║
║                                         ║                       ║
╠═════════════════════════════════════════╩═══════════════════════╣
║ SECONDARY: Path List (toggle)                                   ║
║                                                                  ║
║ Path P-01  Early response → Second-order → Outcome      [View]  ║
║ Path P-02  Different → New pressure → Alternative       [View]  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 8. Implementation Checklist

### Phase 1: Foundational Refinement (P0)

- [ ] **Reduce run list rows** from 112px to 64px
- [ ] **Tighten hero type** from 91px to 72px max
- [ ] **Add negative tracking** (-2.4px at 72px, -1.8px at 56px)
- [ ] **Speed up motion** (100ms hover, 280ms route draw)
- [ ] **Normalize section spacing** (reduce method/template headings by 25%)

### Phase 2: Progressive Disclosure (P1)

- [ ] **Build Step 3 task list** with stacked disclosure
- [ ] **Add inspector pattern** (320–360px right drawer, collapsed by default)
- [ ] **Implement error summary** pattern (page-top, linked to fields)
- [ ] **Add "What happens next"** sections (Steps 4, 6, 7)

### Phase 3: Power-User Tools (P2)

- [ ] **Build command palette** (`Cmd+K` / `Ctrl+K`)
- [ ] **Surface keyboard shortcuts** in UI (tooltips, help panel)
- [ ] **Add blueprint grid** to route canvas (24px, 15% opacity)
- [ ] **Add technical annotations** (node IDs, coordinates, timestamps)

### Phase 4: Micro-Polish (P3)

- [ ] **Button press feedback** (`scale(0.98)`, 100ms)
- [ ] **List selection border** (2px left, slides in)
- [ ] **Route hover thicken** (3.5px → 5px, 120ms)
- [ ] **Toast animations** (slide + fade, 180ms)
- [ ] **True black mode** (OLED-optimized, optional)

---

## 9. Do Not Change

These elements are **strengths** of ASKTHEPEOPLE's identity:

- ✅ **Semantic surface system** (paper/charcoal/white narrative)
- ✅ **Truth Rail** (five-cell desktop, two-line mobile)
- ✅ **Hard geometry** (0px radius, 1–2px borders)
- ✅ **Typography pairing** (Archivo Narrow + Source Sans 3)
- ✅ **Route grammar** (equal-weight paths, no quantitative encoding)
- ✅ **Signal yellow** (#FFD51D as single accent)
- ✅ **Editorial voice** (plain language, sentence case, active voice)

---

## 10. Key Takeaways

### ASKTHEPEOPLE's Unique Position

Your system is **not a clone of Linear or Vercel**. It has a distinct civic editorial identity:

1. **Semantic surfaces** > Generic light/dark modes
2. **Truth-first disclosure** > Hidden disclaimers
3. **Hard civic geometry** > Soft rounded SaaS
4. **Editorial brief** > Dashboard KPIs
5. **Route grammar** > Generic network viz

### Where to Learn from 2026 Standards

Adopt **execution refinements** while preserving identity:

1. **Density**: 64px data rows (not 112px)
2. **Hierarchy**: Primary/secondary/tertiary scale
3. **Motion**: 100–280ms (not 820ms)
4. **Typography**: 72px max hero (not 91px)
5. **Progressive disclosure**: Bloomberg's concealing pattern

### The Formula

```
ASKTHEPEOPLE's Civic Identity
+
2026 Execution Standards
=
High-End Civic Interface
```

---

*This reference document was compiled by the askthepeople-frontend-steward agent on 2026-08-02, based on extracted specifications from Linear, Vercel, Gov.UK, and 2026 SaaS UI research.*

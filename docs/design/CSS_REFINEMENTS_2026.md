---
title: "CSS Refinements — Implementation Guide"
status: "Reference"
version: "1.0.0"
owner: "askthepeople-frontend-steward"
created: "2026-08-02"
last_reviewed: "2026-08-03"
applies_to: "frontend/src/assets/main.css, frontend/src/**/*.vue"
---

# CSS Refinements: Implementation Guide

This document provides **copy-paste CSS code** for implementing the 2026 refinements while preserving ASKTHEPEOPLE's civic identity.

---

## 1. Updated CSS Custom Properties

### Typography Scale (Tightened)

**Replace in `frontend/src/assets/main.css`:**

```css
/* BEFORE (Current - too large) */
:root {
  --font-hero: clamp(3rem, 4.7vw, 5.7rem);     /* 48–91px */
  --font-h1: clamp(2.6rem, 4vw, 5rem);         /* 42–80px */
}

/* AFTER (Proposed - 2026 standard) */
:root {
  --font-hero: clamp(3.5rem, 4vw, 4.5rem);     /* 56–72px */
  --font-h1: clamp(2.25rem, 2.5vw, 3rem);      /* 36–48px */
  --font-h2: clamp(1.5rem, 1.8vw, 2rem);       /* 24–32px */
  --font-h3: clamp(1.25rem, 1.3vw, 1.5rem);    /* 20–24px */
  --font-body: 15px;                            /* Fixed, not fluid */
  --font-small: 13px;                           /* Fixed, not fluid */
  --font-tiny: 11px;                            /* Fixed for labels */
}
```

### Letter Spacing (Negative Tracking for Display)

**Add to `frontend/src/assets/main.css`:**

```css
:root {
  --tracking-hero: -0.033em;      /* -2.4px at 72px */
  --tracking-h1: -0.030em;        /* -1.8px at 56px */
  --tracking-h2: -0.025em;        /* -1.0px at 40px */
  --tracking-body: -0.003em;      /* -0.05px at 16px */
  --tracking-label: 0.040em;      /* +0.4px at 10px (uppercase) */
}
```

### Motion Timing (Three-Tier System)

**Replace in `frontend/src/assets/main.css`:**

```css
/* BEFORE (Current - too slow) */
:root {
  --ease-out: cubic-bezier(0.33, 1, 0.68, 1);
  /* No timing constants defined */
}

/* AFTER (Proposed - 2026 standard) */
:root {
  --ease-out: cubic-bezier(0.2, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  
  --duration-instant: 60ms;      /* Hover, focus ring */
  --duration-quick: 120ms;       /* Button, dropdown, tooltip */
  --duration-deliberate: 280ms;  /* Panel slide, route draw */
}
```

### Density Modes

**Add to `frontend/src/assets/main.css`:**

```css
:root {
  /* Row heights for different contexts */
  --row-form: 80px;        /* Step 1: generous input forms */
  --row-data: 64px;        /* Step 2, 5: compact data lists */
  --row-dashboard: 88px;   /* Home: run cards */
  
  /* Vertical rhythm */
  --section-gap-tight: 2rem;    /* 32px - between related sections */
  --section-gap-normal: 3rem;   /* 48px - between unrelated sections */
  --section-gap-loose: 4rem;    /* 64px - between major page regions */
}
```

---

## 2. Component-Level Refinements

### A. Run List Density (Home.vue)

**BEFORE (Current - 112px rows):**

```css
.run-list button {
  min-height: 7rem;  /* 112px - too tall */
  padding: 1rem 0.4rem;
}

.run-main strong {
  font-size: clamp(1.4rem, 2.3vw, 2.7rem);  /* 22–43px - too large */
}
```

**AFTER (Proposed - 64px data density):**

```css
.run-list button {
  min-height: 4rem;  /* 64px - data table scale */
  padding: 0.75rem 0.5rem;
  transition: 
    background-color var(--duration-quick) var(--ease-out),
    padding var(--duration-quick) var(--ease-out);
}

.run-list button:hover {
  padding-inline: 1rem;  /* Expand on hover */
  background: var(--signal-soft);
}

.run-main strong {
  font-size: clamp(1.25rem, 1.8vw, 1.75rem);  /* 20–28px - tighter */
  letter-spacing: var(--tracking-h2);
  line-height: 1.1;
}

.run-main span {
  margin-top: 0.25rem;  /* Tighter gap */
  font-size: var(--font-small);  /* 13px */
}
```

### B. Hero Typography (Home.vue masthead)

**BEFORE (Current - 91px max):**

```css
.masthead-copy h1 {
  font-size: clamp(3rem, 4.7vw, 5.7rem);  /* 48–91px - too large */
  letter-spacing: -0.02em;  /* Not aggressive enough */
}
```

**AFTER (Proposed - 72px max with aggressive tracking):**

```css
.masthead-copy h1 {
  font-size: var(--font-hero);  /* 56–72px */
  letter-spacing: var(--tracking-hero);  /* -0.033em */
  line-height: 0.92;
  font-weight: 900;
}
```

### C. Section Headings (Reduce visual weight)

**BEFORE (Current - all sections look primary):**

```css
.section-heading h2 {
  font-size: clamp(2.6rem, 4vw, 5rem);  /* 42–80px - too uniform */
}
```

**AFTER (Proposed - primary/secondary/tertiary scale):**

```css
/* Primary: Decision section (keep large) */
.decision-section .section-heading h2 {
  font-size: var(--font-hero);  /* 56–72px */
  letter-spacing: var(--tracking-hero);
}

/* Secondary: Method, Runs sections */
.method-section .section-heading h2,
.runs-section .section-heading h2 {
  font-size: var(--font-h1);  /* 36–48px - reduced 25% */
  letter-spacing: var(--tracking-h1);
}

/* Tertiary: Templates section (move visual priority down) */
.templates-section .section-heading h2 {
  font-size: var(--font-h2);  /* 24–32px - reduced 50% */
  letter-spacing: var(--tracking-h2);
  font-weight: 700;  /* Lighter weight */
}
```

### D. Motion Timing Updates

**BEFORE (Current - 220ms and 820ms):**

```css
.source-dropzone {
  transition: transform 220ms var(--ease-out);  /* Too slow for hover */
}

.path::before {
  animation: draw-path 820ms var(--ease-out) forwards;  /* Too theatrical */
}
```

**AFTER (Proposed - 100ms and 280ms):**

```css
.source-dropzone {
  transition: 
    transform var(--duration-quick) var(--ease-out),
    background-color var(--duration-quick) var(--ease-out),
    border-color var(--duration-quick) var(--ease-out);
}

.path::before {
  animation: draw-path var(--duration-deliberate) var(--ease-spring) forwards;
}

@keyframes draw-path {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}

/* Button hover - instant feedback */
.primary-action {
  transition: 
    transform var(--duration-instant) var(--ease-out),
    background-color var(--duration-quick) var(--ease-out);
}

.primary-action:hover:not(:disabled) {
  transform: translateY(-2px);
}

.primary-action:active:not(:disabled) {
  transform: translateY(-1px) scale(0.98);  /* Press feedback */
}
```

### E. Blueprint Grid (Add to route canvas)

**Add to route-map component CSS:**

```css
.route-canvas {
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
  background-size: 24px 24px;
}

/* On dark (charcoal) surface */
.route-canvas-dark {
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
}
```

### F. Technical Annotations (Route node IDs)

**Add styling for node labels:**

```css
.route-node-id {
  font-family: var(--font-mono);
  font-size: var(--font-tiny);  /* 11px */
  font-weight: 500;
  letter-spacing: 0.02em;
  opacity: 0.4;
  color: currentColor;
  text-transform: uppercase;
}

.route-coordinate-label {
  position: absolute;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 400;
  letter-spacing: 0.05em;
  opacity: 0.3;
  color: var(--ink-muted);
  text-transform: uppercase;
}

/* Top-left: A1, A2, A3 */
.route-coordinate-label[data-axis="x"] {
  top: -1.5rem;
}

/* Left edge: 1, 2, 3 */
.route-coordinate-label[data-axis="y"] {
  left: -1.5rem;
}
```

---

## 3. Progressive Disclosure Pattern

### Step 3 Task List (Stacked Disclosure)

**HTML Structure:**

```html
<div class="task-list">
  <button class="task-item" :class="{ expanded: expandedTask === 'assumptions' }" @click="toggleTask('assumptions')">
    <span class="task-status" :class="{ ready: task.ready, needs-review: !task.ready }">
      {{ task.ready ? '✓ READY' : '⚠ NEEDS REVIEW' }}
    </span>
    <span class="task-label">2 assumptions</span>
    <span class="task-action">Review →</span>
  </button>
  
  <div v-if="expandedTask === 'assumptions'" class="task-content">
    <!-- Assumption cards inline -->
  </div>
</div>
```

**CSS:**

```css
.task-list {
  display: grid;
  gap: 1px;
  background: var(--line-light);
  border-top: 2px solid var(--ink);
}

.task-item {
  display: grid;
  grid-template-columns: 10rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 1.5rem;
  min-height: 3.5rem;  /* 56px - compact */
  padding: 0.75rem 1.25rem;
  border: 0;
  background: var(--paper);
  color: var(--ink);
  text-align: left;
  transition: background-color var(--duration-quick) var(--ease-out);
}

.task-item:hover {
  background: var(--signal-soft);
}

.task-item.expanded {
  background: var(--signal-soft);
  border-bottom: 0;
}

.task-status {
  font-family: var(--font-display);
  font-size: var(--font-small);  /* 13px */
  font-weight: 600;
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
}

.task-status.ready {
  color: var(--ink-muted);
}

.task-status.needs-review {
  color: var(--signal-text);
}

.task-label {
  font-size: 15px;
  font-weight: 600;
}

.task-action {
  font-size: var(--font-small);
  font-weight: 600;
  color: var(--ink-muted);
}

.task-content {
  padding: 1.5rem;
  background: var(--paper-strong);
  border-top: 1px solid var(--line-light);
  animation: expand-content var(--duration-deliberate) var(--ease-spring);
}

@keyframes expand-content {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## 4. Inspector Pattern (Right Drawer)

### HTML Structure:

```html
<div class="route-view-container">
  <div class="route-primary">
    <!-- Map or list view -->
  </div>
  
  <aside 
    class="route-inspector" 
    :class="{ collapsed: !inspectorOpen }"
    aria-label="Run record inspector"
  >
    <button class="inspector-toggle" @click="inspectorOpen = !inspectorOpen">
      <span v-if="inspectorOpen">Close</span>
      <span v-else>Run Record</span>
    </button>
    
    <div v-if="inspectorOpen" class="inspector-content">
      <h3>RUN RECORD</h3>
      <p class="inspector-disclaimer">
        RELATED BY KEYWORD<br>
        NOT A CITATION
      </p>
      <!-- Content -->
    </div>
  </aside>
</div>
```

### CSS:

```css
.route-view-container {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0;
  min-height: 60vh;
}

.route-primary {
  min-width: 0;
  padding: 1.5rem;
}

.route-inspector {
  width: 360px;
  border-left: 1px solid var(--line-light);
  background: var(--paper-strong);
  transition: 
    width var(--duration-deliberate) var(--ease-spring),
    opacity var(--duration-quick) var(--ease-out);
}

.route-inspector.collapsed {
  width: 48px;
}

.inspector-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 3rem;
  border: 0;
  border-bottom: 1px solid var(--line-light);
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: var(--font-small);
  font-weight: 600;
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
  transition: background-color var(--duration-quick) var(--ease-out);
}

.inspector-toggle:hover {
  background: var(--signal-soft);
}

.inspector-content {
  padding: 1.25rem;
  opacity: 1;
  transition: opacity var(--duration-quick) var(--ease-out);
}

.route-inspector.collapsed .inspector-content {
  display: none;
}

.inspector-content h3 {
  margin: 0 0 0.5rem;
  font-family: var(--font-display);
  font-size: var(--font-small);
  font-weight: 700;
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
}

.inspector-disclaimer {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--line-light);
  color: var(--ink-muted);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: 0.02em;
}

/* Mobile: full-screen overlay */
@media (max-width: 767px) {
  .route-inspector {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 20;
    width: 100%;
    border-left: 0;
  }
  
  .route-inspector.collapsed {
    transform: translateX(100%);
  }
}
```

---

## 5. Micro-Interactions

### A. Button Press Feedback

```css
.primary-action,
.run-list button,
.template-list button {
  transition: 
    transform var(--duration-instant) var(--ease-out),
    background-color var(--duration-quick) var(--ease-out);
}

.primary-action:active:not(:disabled),
.run-list button:active,
.template-list button:active {
  transform: scale(0.98);
}
```

### B. List Selection Border

```css
.run-list li,
.template-list button {
  position: relative;
}

.run-list li::before,
.template-list button::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 2px;
  background: var(--signal);
  transform: scaleY(0);
  transform-origin: top;
  transition: transform var(--duration-quick) var(--ease-out);
}

.run-list li:hover::before,
.run-list li:focus-within::before,
.template-list button:hover::before,
.template-list button:focus::before {
  transform: scaleY(1);
}
```

### C. Route Hover Thicken

```css
.route-path {
  stroke-width: 3.5px;
  transition: stroke-width var(--duration-quick) var(--ease-out);
}

.route-path:hover,
.route-path.active {
  stroke-width: 5px;
}
```

---

## 6. Error Summary Pattern (Gov.UK)

### HTML Structure:

```html
<div v-if="errors.length > 0" class="error-summary" role="alert" tabindex="-1">
  <h2 class="error-summary-title">There is a problem</h2>
  <ul class="error-summary-list">
    <li v-for="error in errors" :key="error.field">
      <a :href="`#${error.field}`">{{ error.message }}</a>
    </li>
  </ul>
</div>
```

### CSS:

```css
.error-summary {
  margin-bottom: 2rem;
  padding: 1.25rem;
  border: 3px solid var(--error);
  background: var(--paper);
}

.error-summary:focus {
  outline: 3px solid var(--signal);
  outline-offset: 0;
}

.error-summary-title {
  margin: 0 0 0.75rem;
  color: var(--error);
  font-size: var(--font-h3);
  font-weight: 700;
}

.error-summary-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.error-summary-list li {
  margin-bottom: 0.5rem;
}

.error-summary-list a {
  color: var(--error);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 0.15em;
}

.error-summary-list a:hover {
  text-decoration-thickness: 2px;
}
```

---

## 7. Mobile Refinements

### A. Run List (Mobile)

```css
@media (max-width: 767px) {
  .run-list button {
    grid-template-columns: 2rem minmax(0, 1fr) 1.5rem;
    min-height: 4rem;  /* 64px even on mobile */
    gap: 0.75rem;
    padding: 0.75rem 1rem;
  }
  
  .run-index {
    font-size: 11px;
  }
  
  .run-main strong {
    font-size: clamp(1.125rem, 5vw, 1.5rem);  /* 18–24px */
    white-space: normal;
    line-height: 1.15;
  }
  
  .run-status {
    display: none;  /* Hide on mobile */
  }
}
```

### B. Section Headings (Mobile)

```css
@media (max-width: 767px) {
  .section-heading h2 {
    font-size: clamp(2rem, 10vw, 3rem);  /* 32–48px max */
    margin-top: 0.75rem;
  }
  
  .templates-section .section-heading h2 {
    font-size: clamp(1.5rem, 8vw, 2rem);  /* 24–32px for tertiary */
  }
}
```

---

## 8. Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  .path::before {
    animation: none;
    transform: scaleX(1);  /* Final state immediately */
  }
  
  .route-inspector {
    transition: none;
  }
}
```

---

## 9. Implementation Checklist

### Phase 1: CSS Variables (15 min)

- [ ] Update typography scale custom properties
- [ ] Add letter-spacing variables
- [ ] Update motion timing variables
- [ ] Add density mode variables

### Phase 2: Component Refinements (1–2 hours)

- [ ] Reduce run list row height to 64px
- [ ] Tighten hero typography to 72px max
- [ ] Apply three-tier section heading scale
- [ ] Speed up all motion (100ms hover, 280ms animations)

### Phase 3: New Patterns (2–4 hours)

- [ ] Build task list with stacked disclosure
- [ ] Add inspector drawer pattern
- [ ] Implement error summary component
- [ ] Add blueprint grid to route canvas

### Phase 4: Micro-Interactions (1 hour)

- [ ] Button press feedback (scale 0.98)
- [ ] List selection left border
- [ ] Route hover thicken
- [ ] Focus improvements

### Phase 5: Testing (1 hour)

- [ ] Keyboard navigation
- [ ] Screen reader (NVDA/VoiceOver)
- [ ] 200% zoom
- [ ] 320px mobile width
- [ ] Reduced motion
- [ ] High contrast mode

---

## 10. Before/After Quick Reference

| Element | Before | After | Impact |
|---|---:|---:|---|
| Hero type | 91px max | 72px max | -21% size |
| Run list row | 112px | 64px | -43% height |
| Section h2 (secondary) | 80px | 48px | -40% size |
| Section h2 (tertiary) | 80px | 32px | -60% size |
| Button hover | 220ms | 100ms | -55% duration |
| Route draw | 820ms | 280ms | -66% duration |
| Panel slide | N/A | 240ms | New pattern |

**Result**: Faster, denser, more polished — while preserving civic identity.

---

*This implementation guide was prepared by the askthepeople-frontend-steward agent on 2026-08-02. All changes preserve ASKTHEPEOPLE's semantic surface system, truth-first disclosure, and civic editorial voice.*

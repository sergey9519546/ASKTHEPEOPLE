# ASKTHEPEOPLE UX/UI Redesign: Bold Amplification
## "Brutal Kinetic" — Decision Exploration Made Visceral

---

## The Insight

The **rig UI** reference demonstrates how **motion, visual feedback, and theatrical effect** can amplify a technical aesthetic without diluting it. The chamfered buttons, glitch feedback, scanlines, and RGB fringing feel retro-technical but *alive*.

ASKTHEPEOPLE needs the same energy: **keep the Brutal Editorial character, but make the simulation area sing**. Users need to *understand what's happening* when scenarios branch, nodes calculate, paths form. Right now: static panels and passive visualization. Target: **visceral feedback that shows decision flow in real time**.

---

## Design Direction: "Brutal Kinetic"

**Philosophy**: Amplify the existing Brutal Editorial theme with **intentional motion design, precise visual feedback, and technical theater**. Keep hard edges, cream/ink/red palette, sharp typography. Add **purposeful animation that communicates state**.

---

## Part 1: Keep & Preserve

### What Does NOT Change
- **Palette**: Ink (`#111513`), paper (`#f2ebdd`), signal red (`#f04b3d`), attention yellow (`#ffd51d`)
- **Typography**: Staatliches (display, nouns only, large sizes), Barlow (body/controls)
- **Aesthetics**: Zero border-radius, hard offset shadows, print-inspired
- **Truth Rail**: Permanent, non-dismissible, exactly as is
- **Layout discipline**: Asymmetric, never centered uniformly, proper spacing scale

---

## Part 2: Amplify With Motion & Feedback

### 1. Chamfered Corners (Selective, High Impact)
Adopt the rig theme's **chamfered button aesthetic** but sparingly:

```css
/* Primary CTAs only - not everything */
.btn-primary-action {
  clip-path: polygon(
    12px 0,
    100% 0,
    100% calc(100% - 12px),
    calc(100% - 12px) 100%,
    0 100%,
    0 12px
  );
  background: var(--signal);
  color: var(--ink);
}
```

**Where**: Primary action buttons (Map Decision, Continue, Execute), simulation control buttons
**Not**: Secondary buttons, form inputs, cards - keep them sharp corners

### 2. Glitch Feedback on Hover (Technical Theater)
Borrow rig's glitch effect but **constrained and meaningful**:

```css
@keyframes micro-glitch {
  0% {
    transform: translate(0);
    opacity: 1;
  }
  33% {
    transform: translate(-0.5px, 0.5px);
    opacity: 0.95;
  }
  66% {
    transform: translate(0.5px, -0.5px);
    opacity: 0.98;
  }
  100% {
    transform: translate(0);
    opacity: 1;
  }
}

.btn-primary-action:hover {
  animation: micro-glitch 0.15s ease-in-out;
  box-shadow: 
    3px 3px 0 var(--signal-deep),
    6px 6px 0 var(--ink);
}
```

**Purpose**: Visual confirmation that the click registered. Feels technical, not broken.
**Where**: Primary buttons, simulation control triggers
**Duration**: 150ms - fast enough to feel snappy

### 3. Scanlines & Film Grain (Subtle, Ambient)
Keep it as background texture:

```css
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.04) 2px,
    rgba(0, 0, 0, 0.04) 4px
  );
  pointer-events: none;
  z-index: 10000;
}
```

**Purpose**: Adds texture without reading as "wrong" - reinforces technical character
**Opacity**: 4% - present but not dominant

### 4. RGB Fringe on Edges (Strategic, Not Everywhere)
Use on simulation panel edges to create visual depth:

```css
.simulation-viewport::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    rgba(237, 70, 45, 0.08) 0%,
    transparent 5%,
    transparent 95%,
    rgba(43, 79, 255, 0.08) 100%
  );
  pointer-events: none;
  z-index: 1;
}
```

**Purpose**: Chromatic aberration effect signals "computation happening" - visual energy
**Where**: Simulation canvas edges only
**Opacity**: 8% - felt more than seen

---

## Part 3: THE BIG MOVE - Simulation Animation System

This is where the redesign earns its keep. **The simulation area needs animations that show what's actually happening**.

### Current State
- D3 graph renders static nodes
- User waits in silence
- No visual feedback until step completes
- Users don't understand: "What is it doing?"

### New: Visceral Simulation Feedback

#### A. Node Activation Pulse
When a node starts being evaluated:

```css
@keyframes node-activate {
  0% {
    r: 12;
    filter: drop-shadow(0 0 0 var(--signal));
  }
  50% {
    r: 14;
    filter: drop-shadow(0 0 8px var(--signal));
  }
  100% {
    r: 12;
    filter: drop-shadow(0 0 0 var(--signal));
  }
}

.graph-node.evaluating {
  animation: node-activate 0.6s ease-in-out infinite;
}
```

**What user sees**: Node pulses with signal red glow - "This one is working right now"
**Duration**: 600ms loop during evaluation

#### B. Path Tracing Animation
When a scenario path branches:

```css
@keyframes path-trace {
  0% {
    stroke-dashoffset: 0;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    stroke-dashoffset: -100;
    opacity: 0;
  }
}

.graph-edge.active {
  stroke: var(--signal);
  stroke-width: 3;
  stroke-dasharray: 10 5;
  animation: path-trace 1.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
```

**What user sees**: Red line traces the path being explored - "This decision leads there"
**Duration**: 1.2s smooth animation

#### C. Assumption Cascade
When assumptions are being validated:

```css
@keyframes assumption-flow {
  0% {
    transform: translateX(-100%) scaleX(0);
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    transform: translateX(0) scaleX(1);
    opacity: 1;
  }
}

.assumption-block.validating {
  animation: assumption-flow 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.assumption-block.validating:nth-child(2) {
  animation-delay: 0.1s;
}

.assumption-block.validating:nth-child(3) {
  animation-delay: 0.2s;
}

.assumption-block.validating:nth-child(n+4) {
  animation-delay: 0.3s;
}
```

**What user sees**: Assumptions slide in and validate sequentially - "The decision is being built step by step"
**Stagger**: 100ms between each, elastic timing

#### D. Step Completion Badge
When a step transitions to "completed":

```css
@keyframes step-complete {
  0% {
    scale: 0.8;
    opacity: 0;
  }
  50% {
    scale: 1.1;
  }
  100% {
    scale: 1;
    opacity: 1;
  }
}

.step-badge.completed {
  animation: step-complete 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  background: var(--signal);
  color: var(--paper);
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
}
```

**What user sees**: Badge bounces in with confidence - "This step is done"
**Feel**: Satisfying, with energy

#### E. Parallel Scenario Divergence
When multiple scenarios branch simultaneously:

```css
@keyframes diverge {
  0% {
    cx: 300;
    cy: 400;
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 1;
  }
}

.scenario-node-a {
  animation: diverge 0.8s ease-out;
  animation-name: diverge-left;
}

@keyframes diverge-left {
  0% { transform: translate(0, 0); opacity: 0; }
  100% { transform: translate(-60px, -40px); opacity: 1; }
}

.scenario-node-b {
  animation: diverge 0.8s ease-out;
  animation-name: diverge-right;
}

@keyframes diverge-right {
  0% { transform: translate(0, 0); opacity: 0; }
  100% { transform: translate(60px, -40px); opacity: 1; }
}
```

**What user sees**: Scenarios split and drift apart - "The decision creates branches"
**Feel**: Physical, natural motion

---

## Part 4: Interaction Feedback (Brutal Kinetic)

### Button Press Feedback
```css
.btn-primary:active {
  box-shadow: 
    1px 1px 0 var(--signal-deep),
    2px 2px 0 var(--ink);
  transform: translate(2px, 2px);
}
```

**Feel**: Physical press - like pressing a real button with satisfying mechanical feedback

### Error State Vibration
```css
@keyframes vibrate {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

.step-card.error {
  animation: vibrate 0.3s ease-in-out;
  border-left: 3px solid var(--error);
}
```

**Feel**: Alert you can *feel* - not just see

### Loading State: Staggered Dots
```css
@keyframes dot-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.loading-dot {
  animation: dot-pulse 1.2s ease-in-out infinite;
}

.loading-dot:nth-child(1) { animation-delay: 0s; }
.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }
```

**Feel**: Rhythm, not static spinner - communicates "something is happening"

---

## Part 5: Timing Strategy

All animations use **elastic/bounce easing** for energy, **not ease-out**:

```css
/* Spring-like, snappy */
--ease-snap: cubic-bezier(0.34, 1.56, 0.64, 1);

/* For continuous loops */
--ease-pulse: ease-in-out;

/* For tracing/flowing */
--ease-flow: cubic-bezier(0.4, 0, 0.2, 1);
```

**Duration philosophy**:
- `150ms`: Hover feedback (feels instant)
- `300-400ms`: State transitions (feels responsive)
- `600-800ms`: Long-running processes (communicates "thinking")
- `1-1.5s`: Major scene changes (gives time to perceive the shift)

---

## Part 6: Typography Amplification

### Display Font More Dynamic
Staatliches is perfect, but use it more assertively:

```css
.section-title {
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 4vw, 2.5rem);
  letter-spacing: -0.02em;
  text-transform: uppercase;
  font-weight: 400;
}

.step-label {
  font-family: var(--font-display);
  font-size: 0.95rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-weight: 400;
}
```

**Effect**: More presence, clearer hierarchy

### Mono for Status/Data
Use monospace for step numbers, node IDs, progress indicators:

```css
.node-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--paper-dim);
}
```

**Effect**: Technical precision, clear differentiation between labels and data

---

## Part 7: Where The Magic Happens - Simulation Panel

### Current Structure (Static)
```
┌─────────────────────┐
│  Step 1: Sources    │
│  [✓ Completed]      │
├─────────────────────┤
│  Graph visualizes   │
│  nodes, edges       │
│  (no motion)        │
├─────────────────────┤
│  Step 2: Validation │
│  [○ In Progress]    │
└─────────────────────┘
```

### New Structure (Kinetic)
```
┌─────────────────────────────────────┐
│  STEP 01: SOURCE READING     [✓]    │
│  Status: Complete                   │
│  ├─ Entity extraction: 12 items ✓   │
│  ├─ Relationship mapping: 8 links ✓ │
│  └─ Validation: 100% ✓              │
├─────────────────────────────────────┤
│                                     │
│   [Animated Graph Canvas]           │
│   • Nodes pulse as evaluated        │
│   • Edges trace as paths form       │
│   • Scenarios diverge with motion   │
│   • Current step highlighted        │
│                                     │
├─────────────────────────────────────┤
│  STEP 02: ASSUMPTION REVIEW  [⚬]    │
│  Status: In Progress                │
│  ├─ A₁: Assumption slides in        │
│  ├─ A₂: Validating... (pulse)       │
│  └─ A₃: Waiting...                  │
│                                     │
│  [Micro-glitch button]              │
│  ⇾ CONTINUE SCENARIO                │
└─────────────────────────────────────┘
```

**Key Changes**:
1. **Step labels use display font** - uppercase, prominent
2. **Substep details shown** - users see what's being processed
3. **Animation in canvas** - nodes pulse, paths trace, scenarios diverge
4. **Motion in assumption list** - blocks cascade and validate
5. **Chamfered primary button** - with glitch hover effect
6. **Scanline + RGB fringe** - ambient technical theater

---

## Part 8: Implementation Priority

### Phase 1: Foundation (Week 1)
1. Add chamfered button styles to primary CTAs
2. Add micro-glitch hover animation
3. Add scanline and RGB fringe overlays
4. Update Barlow/Staatliches usage in simulation panel

### Phase 2: Simulation Animation (Week 2)
5. Node activation pulse when evaluating
6. Path tracing animation when branching
7. Assumption cascade animation
8. Step completion badge bounce

### Phase 3: Polish (Week 3)
9. Error vibration feedback
10. Loading state staggered dots
11. Button press mechanical feedback
12. Timing refinement and cross-browser test

### Phase 4: Verification (Week 4)
13. Visual QA across all simulation states
14. Animation performance profiling
15. Accessibility check (motion preferences)
16. Browser compatibility

---

## Part 9: What This DOESN'T Do

- **Doesn't abandon Brutal Editorial**: Keeps ink/paper/red, hard edges, sharp typography
- **Doesn't become glassmorphic**: No blur, no floating panels, no translucency
- **Doesn't soften the brand**: Actually makes it bolder and more distinctive
- **Doesn't add frivolous motion**: Every animation communicates state or process

---

## Part 10: What This DOES Achieve

✅ **Brutal aesthetic amplified** - More distinctive, not diluted
✅ **Technical theater** - Scanlines, RGB fringe, glitch effects feel natural here
✅ **Visceral feedback** - Users SEE what's happening in simulation
✅ **Decision visualization** - Path branching and assumption validation are *felt*
✅ **Brand consistency** - Sherpa's kinetic energy meets ASKTHEPEOPLE's methodical precision
✅ **Motion that matters** - Every animation communicates, doesn't distract

---

## Part 11: Design Principles

1. **Motion communicates** - Every animation shows state change or processing
2. **Buttons have weight** - Chamfered + shadow + glitch = tactile feedback
3. **Scanlines are texture** - Not decoration, ambient technical character
4. **Timing has rhythm** - Staggered animations create visual flow
5. **Brutal stays brutal** - Hard edges, sharp corners, strong palette
6. **Theatre but truthful** - Effects are fun but never misleading about state

---

**This is a redesign that amplifies what ASKTHEPEOPLE already is, rather than replacing it.**

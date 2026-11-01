# ASKTHEPEOPLE: Radical Redesign Vision
## "Decision Cartography" - A Complete Reimagining

---

## Core Philosophy Shift

**FROM**: Brutal Editorial (print-inspired, hard edges, restrained)
**TO**: Fluid Cartography (living data, organic depth, immersive exploration)

The current design treats decisions like documents. The new design treats them like **territories to explore**.

---

## Visual Direction: "Liquid Data Architecture"

### 1. NEW TYPOGRAPHY SYSTEM

**Display**: **Space Grotesk** (geometric, technical precision, variable weight)
- Modern, technical feel without being cold
- Variable font allows for dynamic weight shifts on interaction
- Excellent at large sizes for data visualization labels

**Body**: **Inter Variable** (supreme readability, optimized for screens)
- Most readable sans-serif for sustained reading
- Tabular figures built-in
- Variable font for micro-interactions

**Data/Code**: **JetBrains Mono** (modern monospace with ligatures)
- For node IDs, technical details, system logs
- Crisp at small sizes
- Contextual ligatures for technical elegance

**Accent**: **Fraunces** (soft serif for emphasis)
- Use sparingly for hero statements and key insights
- Adds warmth to otherwise technical aesthetic
- Variable weight and optical sizing

### Typography Scale (Fluid, not fixed)
```css
--text-xs: clamp(0.7rem, 0.5vw + 0.6rem, 0.75rem);
--text-sm: clamp(0.8rem, 0.6vw + 0.7rem, 0.875rem);
--text-base: clamp(0.95rem, 0.8vw + 0.85rem, 1.05rem);
--text-lg: clamp(1.15rem, 1.2vw + 1rem, 1.35rem);
--text-xl: clamp(1.4rem, 1.8vw + 1.2rem, 1.75rem);
--text-2xl: clamp(1.75rem, 2.5vw + 1.4rem, 2.25rem);
--text-3xl: clamp(2.25rem, 3.5vw + 1.8rem, 3rem);
--text-hero: clamp(3rem, 6vw + 2rem, 5.5rem);
```

---

## 2. NEW COLOR SYSTEM: "Deep Ocean to Horizon"

**Philosophy**: Move from harsh contrast to **atmospheric depth**. Colors should feel like they exist in space, not on a flat plane.

### Base Layers (replacing ink/paper)
```css
/* Deep space backgrounds */
--void: #0a0e27;           /* Deep indigo void */
--ocean-deep: #111827;     /* Primary dark surface */
--ocean-mid: #1e293b;      /* Elevated surfaces */
--ocean-surface: #334155;  /* Interactive surfaces */

/* Light surfaces (for data panels, not full backgrounds) */
--cloud: #f8fafc;          /* Lightest data surface */
--mist: #e2e8f0;           /* Secondary light surface */
--frost: #cbd5e1;          /* Tertiary elements */
```

### Accent System (replacing signal red)
```css
/* Primary: Electric Teal (energy, flow, paths) */
--flow: #06b6d4;           /* Primary actions, paths */
--flow-bright: #22d3ee;    /* Hover states */
--flow-dim: #0891b2;       /* Pressed states */
--flow-glow: rgba(6, 182, 212, 0.15);

/* Secondary: Warm Amber (attention, warnings, insights) */
--insight: #f59e0b;
--insight-bright: #fbbf24;
--insight-soft: #fcd34d;

/* Tertiary: Deep Purple (depth, complexity, branches) */
--depth: #8b5cf6;
--depth-bright: #a78bfa;
--depth-soft: #c4b5fd;

/* Success/Error refined */
--success: #10b981;
--caution: #f59e0b;
--critical: #ef4444;
```

### Semantic Layers
```css
/* Data visualization palette */
--data-1: #06b6d4;  /* Teal */
--data-2: #8b5cf6;  /* Purple */
--data-3: #f59e0b;  /* Amber */
--data-4: #10b981;  /* Emerald */
--data-5: #f43f5e;  /* Rose */
--data-6: #6366f1;  /* Indigo */
```

---

## 3. SPATIAL SYSTEM: "Floating Architecture"

**Philosophy**: Elements exist in 3D space. Use real depth, not flat cards.

### Z-Space Layers
```css
--depth-pit: -20px;        /* Recessed elements (inputs) */
--depth-floor: 0px;        /* Base canvas */
--depth-surface: 8px;      /* Cards, panels */
--depth-raised: 16px;      /* Interactive elements */
--depth-floating: 24px;    /* Modals, dropdowns */
--depth-overlay: 32px;     /* Toasts, alerts */
```

### Shadow System (Real physics)
```css
--shadow-subtle: 
  0 1px 2px rgba(0, 0, 0, 0.15),
  0 2px 4px rgba(6, 182, 212, 0.05);

--shadow-lifted:
  0 4px 8px rgba(0, 0, 0, 0.2),
  0 8px 16px rgba(6, 182, 212, 0.08),
  0 0 32px rgba(6, 182, 212, 0.03);

--shadow-floating:
  0 12px 24px rgba(0, 0, 0, 0.25),
  0 24px 48px rgba(6, 182, 212, 0.12),
  0 0 64px rgba(6, 182, 212, 0.06);

--shadow-dramatic:
  0 24px 48px rgba(0, 0, 0, 0.3),
  0 48px 96px rgba(6, 182, 212, 0.15),
  0 0 128px rgba(6, 182, 212, 0.08);
```

### Border System (Glows, not lines)
```css
--border-subtle: 1px solid rgba(6, 182, 212, 0.1);
--border-medium: 1px solid rgba(6, 182, 212, 0.2);
--border-bright: 1px solid rgba(6, 182, 212, 0.4);
--border-glow: 0 0 12px rgba(6, 182, 212, 0.3);
```

---

## 4. MOTION LANGUAGE: "Liquid Physics"

**Philosophy**: Everything feels like it has weight and responds to physics.

### Spring Animations (Replace all easing)
```css
/* Gentle spring for hover */
--spring-gentle: cubic-bezier(0.34, 1.56, 0.64, 1);

/* Bounce for actions */
--spring-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);

/* Elastic for dramatic reveals */
--spring-elastic: cubic-bezier(0.175, 0.885, 0.32, 1.275);

/* Smooth for continuous */
--spring-smooth: cubic-bezier(0.4, 0, 0.2, 1);
```

### Duration Scale (Physical feel)
```css
--instant: 100ms;    /* Micro-interactions */
--quick: 200ms;      /* Hover, focus */
--fluid: 350ms;      /* Card reveals */
--smooth: 500ms;     /* Panel transitions */
--dramatic: 800ms;   /* Page transitions */
--cinematic: 1200ms; /* Hero animations */
```

### Transform Patterns
```css
/* Hover lift */
.interactive:hover {
  transform: translateY(-2px) scale(1.01);
  box-shadow: var(--shadow-lifted);
}

/* Press down */
.interactive:active {
  transform: translateY(1px) scale(0.99);
  box-shadow: var(--shadow-subtle);
}

/* Slide up reveal */
@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Scale fade */
@keyframes scale-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
```

---

## 5. LAYOUT PHILOSOPHY: "Asymmetric Flow"

### Home Page: "Decision Launchpad"

**Before**: Centered form in cream panel
**After**: Split-screen cinematic entry

```
┌─────────────────────────────────────────────────────┐
│  [Left 40%]                    [Right 60%]          │
│                                                      │
│  ASKTHEPEOPLE              ╔════════════════════╗  │
│  Decision Explorer         ║  Animated scenario  ║  │
│                            ║  path visualization ║  │
│  "Map scenario paths       ║  showing branching  ║  │
│   before they exist"       ║  possibilities      ║  │
│                            ║  (D3.js animated)   ║  │
│  [Large textarea]          ║                     ║  │
│  What decision do you      ╚════════════════════╝  │
│  want to explore?                                   │
│                            Recent explorations ↓    │
│  [Context expander]        ┌──────┐ ┌──────┐      │
│  [Source upload]           │ Card │ │ Card │      │
│                            └──────┘ └──────┘      │
│  [Primary CTA: Explore →]                         │
└─────────────────────────────────────────────────────┘
```

### Workspace: "3D Data Space"

**Before**: Two-panel split (graph left, workflow right)
**After**: Floating workspace with depth layers

```
┌─────────────────────────────────────────────────────┐
│ ┌──────────────────────────┐  [Floating Tools] ⚙️  │
│ │  Main Canvas             │                       │
│ │  (Graph visualization)   │  [Mini Map]           │
│ │                          │  ┌──────────┐         │
│ │  Nodes float in space    │  │ Overview │         │
│ │  with real depth         │  │ of full  │         │
│ │                          │  │ graph    │         │
│ │  [Selected node expands  │  └──────────┘         │
│ │   detail panel overlaid] │                       │
│ │                          │  [Timeline]           │
│ │                          │  Step 1 ● ─ ● ─ ○ ─ ○│
│ └──────────────────────────┘                       │
│                                                     │
│ [Bottom: Floating control bar with glassmorphism]  │
└─────────────────────────────────────────────────────┘
```

---

## 6. COMPONENT REDESIGNS

### Buttons: "Magnetic Surfaces"

**Before**: Flat rectangles with borders
**After**: Floating surfaces with magnetic hover

```css
.btn-primary {
  position: relative;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, var(--flow) 0%, var(--depth) 100%);
  border: none;
  border-radius: 12px;
  color: white;
  font-weight: 600;
  font-size: 1rem;
  box-shadow: var(--shadow-lifted);
  transition: all var(--fluid) var(--spring-gentle);
  overflow: hidden;
}

.btn-primary::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, 
    rgba(255, 255, 255, 0.2) 0%, 
    transparent 100%);
  opacity: 0;
  transition: opacity var(--quick);
}

.btn-primary:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: var(--shadow-floating);
}

.btn-primary:hover::before {
  opacity: 1;
}

.btn-primary:active {
  transform: translateY(0) scale(0.98);
}
```

### Cards: "Floating Panels"

**Before**: Flat panels with hairline borders
**After**: Elevated surfaces with depth and glow

```css
.card {
  position: relative;
  padding: 2rem;
  background: linear-gradient(135deg, 
    var(--ocean-mid) 0%, 
    var(--ocean-surface) 100%);
  border-radius: 16px;
  border: var(--border-subtle);
  box-shadow: var(--shadow-lifted);
  transition: all var(--fluid) var(--spring-gentle);
}

.card::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(135deg, 
    var(--flow-glow), 
    transparent);
  mask: linear-gradient(#fff 0 0) content-box, 
        linear-gradient(#fff 0 0);
  mask-composite: exclude;
  opacity: 0;
  transition: opacity var(--quick);
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-floating);
  border-color: var(--flow-glow);
}

.card:hover::before {
  opacity: 1;
}
```

### Inputs: "Recessed Fields"

**Before**: Flat inputs with bottom border
**After**: Inset fields with inner glow

```css
.input {
  padding: 1rem 1.25rem;
  background: var(--void);
  border: var(--border-subtle);
  border-radius: 12px;
  color: var(--cloud);
  font-size: 1rem;
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.3),
    inset 0 0 0 1px rgba(6, 182, 212, 0.05);
  transition: all var(--quick);
}

.input:focus {
  outline: none;
  border-color: var(--flow);
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.3),
    inset 0 0 0 2px rgba(6, 182, 212, 0.2),
    0 0 0 4px rgba(6, 182, 212, 0.1),
    0 0 24px rgba(6, 182, 212, 0.15);
}
```

---

## 7. MICRO-INTERACTIONS

### Cursor-Following Spotlight
```css
.spotlight-container {
  position: relative;
  overflow: hidden;
}

.spotlight-container::before {
  content: '';
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, 
    rgba(6, 182, 212, 0.15) 0%, 
    transparent 70%);
  pointer-events: none;
  transition: opacity 300ms;
  /* Position follows cursor via JS */
}
```

### Loading States: "Pulse Breath"
```css
@keyframes pulse-breath {
  0%, 100% {
    opacity: 0.4;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.02);
  }
}

.loading {
  animation: pulse-breath 2s ease-in-out infinite;
}
```

### Stagger Reveal
```css
.stagger-item {
  opacity: 0;
  transform: translateY(20px);
  animation: slide-up var(--fluid) var(--spring-gentle) forwards;
}

.stagger-item:nth-child(1) { animation-delay: 50ms; }
.stagger-item:nth-child(2) { animation-delay: 100ms; }
.stagger-item:nth-child(3) { animation-delay: 150ms; }
.stagger-item:nth-child(4) { animation-delay: 200ms; }
.stagger-item:nth-child(5) { animation-delay: 250ms; }
```

---

## 8. DATA VISUALIZATION ENHANCEMENTS

### Scenario Graph: From Static to Fluid

**Current**: D3 force graph with basic nodes
**New**: Layered, animated network with particle flows

- **Nodes**: Glassmorphic circles with inner glow
- **Edges**: Animated particle flows showing directionality
- **Hover**: Node expands with smooth spring, reveals detail overlay
- **Selection**: Ripple effect emanates from selected node
- **Minimap**: Glowing viewport indicator showing current view

```css
.graph-node {
  fill: url(#node-gradient);
  stroke: var(--flow);
  stroke-width: 2;
  filter: drop-shadow(0 4px 8px rgba(6, 182, 212, 0.3));
  transition: all var(--fluid) var(--spring-bounce);
}

.graph-node:hover {
  filter: drop-shadow(0 8px 16px rgba(6, 182, 212, 0.5));
  transform: scale(1.2);
}

.graph-edge {
  stroke: rgba(6, 182, 212, 0.3);
  stroke-width: 2;
  stroke-dasharray: 5 5;
  animation: dash-flow 2s linear infinite;
}

@keyframes dash-flow {
  to {
    stroke-dashoffset: -10;
  }
}
```

---

## 9. TRUTH RAIL REDESIGN

**Before**: Static bar at top with separated items
**After**: Persistent ambient disclosure

```css
.truth-rail {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  backdrop-filter: blur(12px) saturate(180%);
  background: rgba(10, 14, 39, 0.85);
  border-bottom: 1px solid rgba(6, 182, 212, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.truth-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  padding: 0.75rem 2rem;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.truth-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--mist);
}

.truth-item::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--insight);
  box-shadow: 0 0 8px var(--insight);
  animation: pulse-glow 2s ease-in-out infinite;
}

.truth-emphasis {
  color: var(--insight-bright);
  text-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
}

@keyframes pulse-glow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## 10. RESPONSIVE STRATEGY

**Philosophy**: Adapt meaningfully, don't just stack

### Desktop (>1200px)
- Full split layouts
- Floating panels with depth
- Cursor interactions active
- Full animation suite

### Tablet (768px - 1200px)
- Collapsible sidebars
- Simplified shadows (performance)
- Touch-optimized hit areas (min 44px)
- Reduced particle effects

### Mobile (<768px)
- Single column flow
- Bottom sheet interactions
- Swipe gestures
- Minimal shadows
- Disabled parallax/cursor effects

---

## Implementation Priority

### Phase 1: Foundation (Week 1)
1. New design tokens
2. Typography system
3. Color system
4. Base component redesigns (buttons, inputs, cards)

### Phase 2: Core Experience (Week 2)
5. Home page redesign
6. Workspace layout restructure
7. Graph visualization enhancements
8. Motion system implementation

### Phase 3: Polish (Week 3)
9. Micro-interactions
10. Loading states
11. Error states
12. Responsive refinements

### Phase 4: Advanced (Week 4)
13. Cursor following effects
14. Particle systems
15. Advanced animations
16. Performance optimization

---

## Success Metrics

**Quantitative**:
- Page load time < 2s
- Interaction response < 100ms
- Lighthouse score > 95
- 0 accessibility violations

**Qualitative**:
- Feels "alive" not static
- Invites exploration
- Reinforces "mapping" metaphor
- Premium, not generic

---

## Design Principles

1. **Depth over flatness** - Use real Z-space
2. **Flow over rigidity** - Organic curves, liquid motion
3. **Glow over lines** - Light emanates, doesn't outline
4. **Invitation over instruction** - Interface draws you in
5. **Precision over decoration** - Every effect serves purpose

---

**This is not a refresh. This is a transformation.**

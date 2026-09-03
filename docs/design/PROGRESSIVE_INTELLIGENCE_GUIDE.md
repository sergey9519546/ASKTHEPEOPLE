---
title: "Progressive Intelligence Transformation Guide"
status: "Normative"
version: "1.0.0"
owner: "Frontend Design + Product"
last_reviewed: "2026-09-01"
review_cycle: "Quarterly"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "frontend interface, progressive disclosure, contextual guidance"
---

# Progressive Intelligence Transformation Guide

## Overview

This guide documents the transformation from documentation-heavy interface patterns to intelligently guided experiences. The goal is to prevent complexity from reaching users before it becomes useful, while maintaining full capability for advanced users.

## Core Problem

The current interface shows **everything at once**:
- Explanatory text for every feature before users need it
- All controls visible regardless of user capability or current task
- Technical terminology exposed before users understand the domain
- Multiple competing status indicators and information surfaces
- Features organized by system architecture rather than user needs

## Solution: Context-Aware Progressive Intelligence

The system tracks three dimensions to determine what to show:

1. **User capability level** (inferred from behavior, not explicit setting)
   - First use: Never completed a run
   - Learning: 1-3 completed runs
   - Practiced: 4-10 completed runs
   - Expert: 10+ runs or explicit preference

2. **Workflow phase** (where user is in the process)
   - Setup → Mapping → Configuring → Reviewing → Exploring → Validating

3. **User intent** (inferred from actions)
   - Quick exploration: Minimal setup, see what happens
   - Thorough analysis: Reviewing all options carefully
   - Comparison: Multiple runs side-by-side
   - Validation prep: Preparing human research
   - Troubleshooting: Something went wrong

## Implementation Architecture

### 1. Guided Context System (`useGuidedContext.js`)

Central intelligence that tracks:
- Current workflow phase
- User capability level
- Inferred intent from behavior patterns
- Interaction history
- Time signals (pausing vs moving quickly)
- Error and attention states

**Key computed properties:**
- `explanationLevel`: How much to explain (minimal/contextual/essential/detailed)
- `prominentLayer`: What to emphasize (error/attention/action/context/balanced)
- `showAdvancedControls`: Should expert features be visible
- `currentEmphasis`: What to prioritize in current phase

### 2. Adaptive UI Layer (`useAdaptiveUI.js`)

Translates context into UI decisions:
- `adaptiveClasses`: Visibility and emphasis classes for elements
- `shouldExplain`: Whether to show detailed explanations
- `shouldAutoExpand`: Should sections start expanded
- `actionLabel`: Appropriate button text for context
- `layoutMode`: Linear/spatial/focus/split based on task
- `statusMessage`: Context-appropriate status text

### 3. UI Components

**ProgressiveGuidance.vue**: Wrapper that shows/hides content based on context
- Primary level: Always visible, most prominent
- Secondary level: Visible but less prominent
- Available level: Accessible but not prominent
- Advanced level: Hidden until revealed

**ContextualHelp.vue**: Inline help that appears when relevant
- Auto-shows for first-time users on critical concepts
- Fades as users demonstrate understanding
- Re-appears when users pause or show confusion
- Always accessible via explicit toggle

## Transformation Patterns

### Before: Show Everything

```vue
<template>
  <div class="step-card">
    <div class="card-header">
      <span class="step-num">01</span>
      <span class="step-title">Read the source material</span>
      <span class="badge">Processing</span>
    </div>
    
    <div class="card-content">
      <p class="api-note">SOURCE READING</p>
      <p class="description">
        A model proposes actor, place, concept, and relationship categories
        from the submitted material. Review them: they may be incomplete,
        ambiguous, or wrong.
      </p>
      
      <!-- Always visible: entity list, relationship list, attribute details -->
      <div class="tags-container">
        <span class="tag-label">People, places, and concepts</span>
        <div class="tags-list">
          <!-- 20+ entity tags visible immediately -->
        </div>
      </div>
      
      <div class="relationships-section">
        <!-- Complex relationship details visible immediately -->
      </div>
    </div>
  </div>
</template>
```

### After: Guide Through Context

```vue
<template>
  <div class="step-card">
    <div class="card-header">
      <span class="step-num">01</span>
      <span class="step-title">{{ adaptiveTitle }}</span>
      <span :class="['badge', statusClass]">
        {{ statusMessage('processing', { stage: 'Reading sources' }) }}
      </span>
    </div>
    
    <div class="card-content">
      <!-- Help only appears when relevant -->
      <ContextualHelp
        help-id="source-reading"
        concept="entity_extraction"
        :content="{
          first_use: 'The system identifies key people, places, and concepts from your sources. This helps structure the scenario.',
          learning: 'Extracted entities will be used to build generated profiles.',
          practiced: 'Entities from source material',
          expert: null
        }"
        :auto-show-phases="['mapping']"
      />
      
      <!-- Primary: Key entities overview (always visible at this phase) -->
      <ProgressiveGuidance
        id="key_entities"
        level="primary"
        :phases="['mapping']"
      >
        <div class="entities-summary">
          <span class="summary-count">{{ entityCount }} key entities found</span>
          <div class="entity-preview">
            <!-- Top 6 entities shown by default -->
            <button
              v-for="entity in topEntities"
              :key="entity.name"
              class="entity-chip"
              @click="selectEntity(entity)"
            >
              {{ entity.name }}
            </button>
          </div>
        </div>
      </ProgressiveGuidance>
      
      <!-- Available: Full entity list (expandable) -->
      <ProgressiveGuidance
        id="all_entities"
        level="available"
        :phases="['mapping']"
      >
        <template #preview>
          <span>{{ remainingCount }} more entities available</span>
        </template>
        
        <template #default>
          <div class="full-entity-list">
            <!-- All entities, searchable -->
          </div>
        </template>
      </ProgressiveGuidance>
      
      <!-- Advanced: Relationship details (hidden until user demonstrates need) -->
      <ProgressiveGuidance
        id="relationship_types"
        level="advanced"
        :capabilities="['practiced', 'expert']"
      >
        <template #trigger-label>relationship details</template>
        
        <template #default>
          <div class="relationship-details">
            <!-- Complex relationship visualization and editing -->
          </div>
        </template>
      </ProgressiveGuidance>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useAdaptiveUI } from '../composables/useAdaptiveUI';
import ProgressiveGuidance from './ProgressiveGuidance.vue';
import ContextualHelp from './ContextualHelp.vue';

const { 
  actionLabel, 
  statusMessage, 
  adaptiveCopy,
  guidance 
} = useAdaptiveUI();

// Title adapts to capability level
const adaptiveTitle = computed(() => adaptiveCopy('step_title', {
  first_use: 'Review what we found in your sources',
  learning: 'Review extracted entities',
  practiced: 'Source entities',
  expert: 'Entities'
}));

// ... component logic
</script>
```

## Migration Checklist

### Step 1: Wrap existing sections in ProgressiveGuidance

Identify information hierarchy:
- What's essential for the primary task? → `level="primary"`
- What's helpful context? → `level="secondary"`
- What's available for thoroughness? → `level="available"`
- What's only for advanced users? → `level="advanced"`

### Step 2: Replace static explanations with ContextualHelp

Look for patterns like:
- Long descriptions at the top of sections
- "What is this?" explanatory paragraphs
- Always-visible helper text

Replace with ContextualHelp that:
- Defines content per capability level
- Specifies when to auto-show (phases)
- Can be dismissed or expanded manually

### Step 3: Make labels contextual

Replace static labels with adaptive variants:
```js
// Before
<button>Generate possible paths</button>

// After
<button>
  {{ actionLabel('generate', {
    explicit: 'Generate possible scenario paths',
    default: 'Generate paths',
    terse: 'Generate'
  }) }}
</button>
```

### Step 4: Consolidate status indicators

Replace multiple competing status displays with single contextual message:
```js
{{ statusMessage('processing', { 
  stage: 'Building scenarios', 
  progress: '3/5' 
}) }}
```

### Step 5: Track user interactions

Add tracking to key interactions:
```js
const handleEntityClick = (entity) => {
  guidance.trackInteraction('entity_detail');
  selectEntity(entity);
};
```

## Design Principles

### 1. Structure Remains Predictable

The layout doesn't reorganize itself. Elements stay in consistent positions. What changes is:
- Visual emphasis (size, weight, color)
- Expansion state (collapsed/preview/expanded)
- Availability (hidden/available/prominent)

### 2. Progression is Discoverable

Users can always access more:
- "Show details" triggers are visible
- Collapsed sections have preview text
- Available features show brief descriptions

### 3. Nothing is Permanently Hidden

Expert features are:
- Hidden by default for new users
- Revealed automatically as users demonstrate capability
- Always accessible via "Show advanced" toggles
- Never removed entirely

### 4. Context is Inferred, Not Asked

The system determines capability and intent from:
- Completion history
- Interaction patterns
- Time spent on views
- Sections expanded
- Errors encountered

Never ask: "Are you a beginner or expert?"

### 5. Errors Always Win

When something needs attention:
- Errors are always primary
- Attention items surface when user pauses
- Recovery actions are prominent
- Explanations adapt to the error context

## Measuring Success

The transformation succeeds when:

1. **First-time users complete a run without documentation**
   - No external help needed
   - Core concepts understood from interface itself
   - Primary path is obvious

2. **Advanced users access deep functionality efficiently**
   - Expert features are 1-2 clicks away
   - No unnecessary explanations blocking workflow
   - Technical detail available when needed

3. **Interface feels connected, not disjointed**
   - Consistent terminology throughout
   - Actions named by outcome, not implementation
   - Navigation follows task structure

4. **Complexity reveals progressively**
   - Simple tasks feel simple
   - Complex tasks feel manageable
   - Depth appears when relevant

5. **Users trust the guidance**
   - Help appears at the right moment
   - Suggestions are actually helpful
   - System "understands" what they're trying to do

## Common Pitfalls to Avoid

### 1. Don't Hide Critical Information

Progressive disclosure is not about hiding things users need. The primary action and essential context must always be visible.

### 2. Don't Create Unpredictability

If a feature moves location or changes dramatically between sessions, users will be confused. Adapt emphasis and availability, not structure.

### 3. Don't Over-Infer

Intent detection should be conservative. If uncertain, default to showing more rather than less. A missed revelation is worse than a slightly verbose interface.

### 4. Don't Break Keyboard Navigation

Collapsed sections must still be keyboard-accessible. Hidden features need discovery affordances that work without hovering.

### 5. Don't Forget Mobile

Progressive disclosure is even more important on small screens, but the patterns must work with touch. No hover-only reveals.

## CSS Adaptive Classes Reference

The system applies these classes automatically based on context:

```css
/* Core visibility */
.adaptive-hidden { display: none; }

.adaptive-primary {
  /* Most prominent, always visible */
  order: -2;
  opacity: 1;
}

.adaptive-secondary {
  /* Visible but less prominent */
  order: -1;
  opacity: 0.95;
}

.adaptive-available {
  /* Accessible but not prominent */
  order: 0;
  opacity: 0.85;
}

/* Interaction state */
.adaptive-revealed {
  /* User has interacted */
  opacity: 1;
}

/* Capability mode */
.adaptive-expert-mode {
  /* More compact, less decoration */
}
```

Components can use these to adjust styling without duplicating logic.

## Next Steps for Implementation

1. **Create user capability persistence**
   - Store completion count in localStorage
   - Respect explicit "expert mode" toggle
   - Sync across sessions

2. **Build intent detection algorithms**
   - Track time between actions
   - Identify quick exploration patterns
   - Recognize comparison workflows

3. **Implement help dismissal memory**
   - Remember dismissed help per concept
   - Allow "reset all help" option
   - Respect dismissals across sessions

4. **Add analytics to validate assumptions**
   - Track which features are never revealed
   - Measure time to first completion by capability
   - Identify friction points in guidance

5. **Test with real users**
   - First-time user walkthrough (no intervention)
   - Expert user efficiency audit
   - Mixed-capability group observation

## Further Reading

- `frontend/src/composables/useGuidedContext.js` - Central intelligence
- `frontend/src/composables/useAdaptiveUI.js` - UI adaptation layer
- `frontend/src/components/ProgressiveGuidance.vue` - Progressive disclosure component
- `frontend/src/components/ContextualHelp.vue` - Contextual help component
- `docs/design/CONTENT_SYSTEM.md` - Content and terminology standards
- `docs/design/DIRECTION_C.md` - Civic Wayfinding design principles

---
title: "Intelligent Guidance System — Implementation Summary"
status: "Normative"
version: "1.0.0"
owner: "Frontend Design + Product"
last_reviewed: "2026-09-01"
review_cycle: "Quarterly"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "frontend components, adaptive UI, user capability tracking"
---

# Intelligent Guidance System — Implementation Summary

## What We Built

A complete system for transforming documentation-heavy interfaces into intelligently guided experiences. The product now understands user context and adapts what it shows, rather than presenting all features and explanations simultaneously.

## Core Components

### 1. Context Intelligence (`useGuidedContext.js`)

Tracks three dimensions to determine what to show:

**User Capability** (inferred from behavior)
- First use: Never completed a run
- Learning: 1-3 runs completed
- Practiced: 4-10 runs completed  
- Expert: 10+ runs or explicit preference

**Workflow Phase** (current task)
- Setup → Mapping → Configuring → Reviewing → Exploring → Validating

**User Intent** (inferred from actions)
- Quick exploration: See what happens fast
- Thorough analysis: Review everything carefully
- Comparison: Multiple runs side-by-side
- Validation prep: Preparing human research
- Troubleshooting: Something went wrong

### 2. Adaptive UI Layer (`useAdaptiveUI.js`)

Translates context into concrete UI decisions:
- Which elements are visible, prominent, or hidden
- How much explanation to provide
- What labels and copy to use
- What layout mode to apply
- When to auto-expand sections

### 3. UI Components

**ProgressiveGuidance.vue**
- Wraps content with context-aware visibility
- Four levels: primary, secondary, available, advanced
- Shows preview when collapsed, full detail when expanded
- Remembers user interactions

**ContextualHelp.vue**
- Inline help that appears when relevant
- Different content per capability level
- Auto-shows for first-time users, fades for experts
- Three visual variants: inline, tooltip, aside

## Key Transformations

### Before: Everything Visible

```vue
<p class="description">
  A model proposes actor, place, concept, and relationship 
  categories from the submitted material. Review them: they 
  may be incomplete, ambiguous, or wrong.
</p>

<div class="tags-container">
  <!-- 20+ entity tags always visible -->
</div>

<div class="relationships-section">
  <!-- Complex relationship details always visible -->
</div>

<div class="attributes-section">
  <!-- Attribute schema always visible -->
</div>
```

### After: Guided Through Context

```vue
<ContextualHelp
  help-id="source-reading"
  concept="entity_extraction"
  :content="{
    first_use: 'The system identifies key people, places...',
    learning: 'Extracted entities will be used...',
    practiced: 'Entities from source material',
    expert: null
  }"
/>

<ProgressiveGuidance id="key_entities" level="primary">
  <!-- Top 6 entities, always visible -->
</ProgressiveGuidance>

<ProgressiveGuidance id="remaining_entities" level="secondary">
  <template #preview>12 more entities</template>
  <template #default><!-- Full list --></template>
</ProgressiveGuidance>

<ProgressiveGuidance id="relationship_types" level="available">
  <template #trigger-label>relationship details</template>
  <template #default><!-- Complex details --></template>
</ProgressiveGuidance>
```

## Implementation Strategy

### Phase 1: Foundation (Complete)
- ✅ Create guided context system
- ✅ Build adaptive UI layer
- ✅ Implement progressive guidance component
- ✅ Implement contextual help component
- ✅ Document transformation patterns
- ✅ Create refactored example component

### Phase 2: Core Interface Migration
1. **Home/Setup View**
   - Wrap route grammar in ProgressiveGuidance (advanced level)
   - Make decision field contextual help auto-show for first-time users
   - Simplify source upload explanation based on capability
   - Consolidate quick-start presets with progressive reveal

2. **Source Mapping (Step 1)**
   - Replace with Step1GraphBuildRefactored.vue pattern
   - Hide entity attributes until user demonstrates need
   - Show key entities prominently, remaining as secondary
   - Make relationship details available but not prominent

3. **Assumptions Setup (Step 2)**
   - Contextual help for "generated profiles" concept
   - Progressive reveal of behavioral models
   - Consolidate preparation status into single adaptive message
   - Hide advanced configuration until practiced level

4. **Run Review (Step 3)**
   - Adaptive detail level for configuration summary
   - Progressive reveal of full technical parameters
   - Contextual help for scenario concepts
   - Status messages adapt to capability level

5. **Results Exploration (Step 4)**
   - Context-aware path display (overview vs detail)
   - Progressive reveal of supporting evidence
   - Adaptive comparison controls
   - Contextual explanations of synthetic nature

### Phase 3: Capability Persistence
1. **Track completion history**
   ```js
   // localStorage or backend
   {
     userId: string,
     completedRuns: number,
     lastCapabilityLevel: string,
     dismissedHelp: Set<string>,
     revealedFeatures: Set<string>,
     explicitExpertMode: boolean
   }
   ```

2. **Intent detection refinement**
   - Track time between actions
   - Identify comparison patterns (multiple tabs)
   - Recognize validation prep (export focus)
   - Detect troubleshooting (repeated attempts)

3. **Help dismissal memory**
   - Remember per concept, not globally
   - Allow "reset all help" option
   - Respect across sessions but allow re-enable

### Phase 4: Validation & Refinement
1. **User testing**
   - First-time user walkthrough (no intervention)
   - Expert user efficiency audit
   - Mixed-capability observation

2. **Analytics**
   - Track which features are never revealed
   - Measure time to first completion by capability
   - Identify friction points in guidance
   - Monitor help dismissal patterns

3. **Iteration**
   - Adjust auto-show thresholds
   - Refine intent detection algorithms
   - Tune capability level transitions
   - Improve contextual copy

## Design Principles Maintained

### 1. Structure Remains Predictable
Layout doesn't reorganize. Elements stay in consistent positions. Only emphasis, expansion state, and availability change.

### 2. Nothing Permanently Hidden
Expert features are:
- Hidden by default for new users
- Revealed as users demonstrate capability
- Always accessible via explicit toggles
- Never removed entirely

### 3. Context Inferred, Never Asked
System determines capability from:
- Completion history
- Interaction patterns
- Time on views
- Sections expanded
- Errors encountered

Never ask: "Are you a beginner or expert?"

### 4. Errors Always Win
When something needs attention:
- Errors are always primary
- Recovery actions are prominent
- Explanations adapt to error context

### 5. Coherent System
One connected experience:
- Consistent terminology
- Actions named by outcome
- Navigation follows task structure
- Progressive depth revelation

## Success Metrics

The transformation succeeds when:

1. **First-time users complete a run without documentation**
   - No external help needed
   - Core concepts understood from interface
   - Primary path is obvious

2. **Advanced users access deep functionality efficiently**
   - Expert features 1-2 clicks away
   - No unnecessary explanations
   - Technical detail available when needed

3. **Interface feels connected**
   - Consistent terminology throughout
   - Actions named clearly
   - Navigation follows mental model

4. **Complexity reveals progressively**
   - Simple tasks feel simple
   - Complex tasks feel manageable
   - Depth appears when relevant

## Quick Reference: When to Use What

### Use ProgressiveGuidance when:
- Content has clear importance hierarchy
- Features are not needed by all users
- Detail can be revealed progressively
- You want to reduce initial cognitive load

### Use ContextualHelp when:
- Explaining a concept or term
- Providing task-specific guidance
- Help relevance changes with context
- You want to fade help as users learn

### Use adaptive copy when:
- Labels should change based on capability
- Status messages need context
- Placeholders should guide differently
- Errors need appropriate detail level

## Common Patterns

### Pattern: Essential + Detail
```vue
<!-- Essential (always visible) -->
<ProgressiveGuidance id="summary" level="primary">
  <div class="summary">6 key entities found</div>
</ProgressiveGuidance>

<!-- Detail (expandable) -->
<ProgressiveGuidance id="full_list" level="secondary">
  <template #preview>Show all entities</template>
  <template #default><!-- Full entity list --></template>
</ProgressiveGuidance>
```

### Pattern: First-Time Help
```vue
<ContextualHelp
  help-id="concept"
  concept="concept_id"
  :content="{
    first_use: 'Detailed explanation with examples',
    learning: 'Shorter reminder',
    practiced: 'Brief note',
    expert: null
  }"
  :auto-show-phases="['relevant_phase']"
/>
```

### Pattern: Expert Features
```vue
<ProgressiveGuidance
  id="advanced_feature"
  level="advanced"
  :capabilities="['practiced', 'expert']"
>
  <template #trigger-label>advanced options</template>
  <template #default><!-- Complex controls --></template>
</ProgressiveGuidance>
```

## Files Created

### Core System
- `frontend/src/composables/useGuidedContext.js` — Central intelligence
- `frontend/src/composables/useAdaptiveUI.js` — UI adaptation layer

### Components
- `frontend/src/components/ProgressiveGuidance.vue` — Progressive disclosure
- `frontend/src/components/ContextualHelp.vue` — Contextual help

### Documentation
- `docs/design/PROGRESSIVE_INTELLIGENCE_GUIDE.md` — Comprehensive guide
- `docs/design/INTELLIGENT_GUIDANCE_IMPLEMENTATION.md` — This file

### Examples
- `frontend/src/components/Step1GraphBuildRefactored.vue` — Refactored example

## Next Actions

1. **Integrate with existing components**
   - Start with Step1GraphBuild.vue
   - Apply pattern to Step2EnvSetup.vue
   - Migrate other step components

2. **Add capability persistence**
   - Create localStorage wrapper
   - Track completion count
   - Remember dismissed help
   - Sync explicit preferences

3. **Test with users**
   - First-time user observation
   - Expert user feedback
   - Identify friction points

4. **Refine algorithms**
   - Adjust auto-show thresholds
   - Improve intent detection
   - Tune capability transitions

5. **Measure success**
   - Track completion rates by capability
   - Monitor help engagement
   - Identify never-revealed features

## Related Documentation

- `docs/design/CONTENT_SYSTEM.md` — Content standards and terminology
- `docs/design/DIRECTION_C.md` — Civic Wayfinding principles
- `docs/design/ACCESSIBILITY.md` — Accessibility requirements
- `AGENTS.md` — Repository governance and agent contracts

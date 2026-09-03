---
title: "Component Migration Checklist"
status: "Normative"
version: "1.0.0"
owner: "Frontend Design + Product"
last_reviewed: "2026-09-01"
review_cycle: "Per migration"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "component refactoring, progressive disclosure migration"
---

# Component Migration Checklist

Use this checklist when refactoring an existing component to use the intelligent guidance system.

## Pre-Migration Audit

- [ ] **Identify all information layers currently visible**
  - List what's shown by default
  - List what's in dropdowns/disclosures
  - List what's completely hidden
  
- [ ] **Map to user capability levels**
  - What does a first-time user need to see?
  - What does an expert need quick access to?
  - What's only relevant for thorough analysis?

- [ ] **Identify explanatory content**
  - Static descriptions
  - Always-visible helper text
  - Technical terminology
  - "What is this?" paragraphs

- [ ] **List all actions/buttons**
  - Primary action
  - Secondary actions
  - Advanced/expert actions
  - Destructive actions

## Migration Steps

### 1. Add Adaptive UI Composable

```vue
<script setup>
import { useAdaptiveUI } from '../composables/useAdaptiveUI';

const { 
  adaptiveClasses,
  actionLabel,
  statusMessage,
  adaptiveCopy,
  shouldExplain,
  guidance
} = useAdaptiveUI();
</script>
```

- [ ] Import `useAdaptiveUI`
- [ ] Destructure needed functions
- [ ] Test that composable initializes

### 2. Wrap Sections in ProgressiveGuidance

For each major section, determine its level:

```vue
<!-- PRIMARY: Essential for the task, always visible -->
<ProgressiveGuidance
  id="section_name"
  level="primary"
  :phases="['relevant_phase']"
  :expandable="false"
>
  <!-- Essential content -->
</ProgressiveGuidance>

<!-- SECONDARY: Helpful context, visible but less prominent -->
<ProgressiveGuidance
  id="section_name"
  level="secondary"
  :phases="['relevant_phase']"
>
  <template #preview>Brief summary</template>
  <template #default>Full content</template>
</ProgressiveGuidance>

<!-- AVAILABLE: For thoroughness, expandable -->
<ProgressiveGuidance
  id="section_name"
  level="available"
  :capabilities="['learning', 'practiced', 'expert']"
>
  <template #trigger-label>feature name</template>
  <template #default>Detailed content</template>
</ProgressiveGuidance>

<!-- ADVANCED: Expert-only features -->
<ProgressiveGuidance
  id="section_name"
  level="advanced"
  :capabilities="['practiced', 'expert']"
>
  <template #trigger-label>advanced options</template>
  <template #default>Complex controls</template>
</ProgressiveGuidance>
```

- [ ] Wrap primary content (level="primary")
- [ ] Wrap secondary content (level="secondary")
- [ ] Wrap available features (level="available")
- [ ] Wrap advanced features (level="advanced")
- [ ] Test expansion/collapse behavior

### 3. Replace Static Explanations with ContextualHelp

Find patterns like:
```vue
<!-- BEFORE -->
<p class="description">
  A model proposes actor, place, concept, and relationship 
  categories from the submitted material. Review them...
</p>
```

Replace with:
```vue
<!-- AFTER -->
<ContextualHelp
  help-id="unique_id"
  concept="concept_name"
  :content="{
    first_use: 'Detailed explanation for new users',
    learning: 'Shorter reminder for learning users',
    practiced: 'Brief note for practiced users',
    expert: null
  }"
  :auto-show-phases="['phase_name']"
  variant="inline"
/>
```

- [ ] Identify static explanations
- [ ] Create content variants per capability level
- [ ] Specify when to auto-show (phases)
- [ ] Test appearance for each capability level
- [ ] Verify dismissal works

### 4. Make Labels Contextual

Replace static button labels:
```vue
<!-- BEFORE -->
<button>Continue to set assumptions</button>

<!-- AFTER -->
<button>
  {{ actionLabel('continue', {
    explicit: 'Continue to set assumptions',
    default: 'Continue',
    terse: 'Next'
  }) }}
</button>
```

Replace static titles:
```vue
<!-- BEFORE -->
<span class="step-title">Read the source material</span>

<!-- AFTER -->
<span class="step-title">
  {{ adaptiveCopy('step_title', {
    first_use: 'Review what we found in your sources',
    learning: 'Review extracted entities',
    practiced: 'Source entities',
    expert: 'Entities'
  }) }}
</span>
```

- [ ] Identify all button labels
- [ ] Create variants (explicit/default/terse)
- [ ] Replace with `actionLabel()`
- [ ] Identify section titles
- [ ] Create variants per capability
- [ ] Replace with `adaptiveCopy()`

### 5. Consolidate Status Indicators

Replace multiple competing status displays:
```vue
<!-- BEFORE -->
<span v-if="phase > 0" class="badge success">Completed</span>
<span v-else-if="phase === 0" class="badge processing">Reading</span>
<span v-else class="badge pending">Waiting</span>

<!-- AFTER -->
<span :class="['badge', stepStatus]">
  {{ statusMessage(stepStatus, { 
    stage: 'Reading sources',
    itemCount: entities.length 
  }) }}
</span>
```

- [ ] Identify all status displays
- [ ] Determine status type (processing/ready/error/waiting)
- [ ] Replace with `statusMessage()`
- [ ] Pass relevant context data
- [ ] Test for each capability level

### 6. Add Interaction Tracking

Track when users interact with important elements:
```vue
const handleEntityClick = (entity) => {
  guidance.trackInteraction('entity_detail');
  selectEntity(entity);
};
```

- [ ] Identify key interaction points
- [ ] Add `guidance.trackInteraction()` calls
- [ ] Use meaningful IDs
- [ ] Test that tracking works

### 7. Apply Adaptive Classes

Add adaptive classes to elements that should respond to context:
```vue
<div :class="[
  'progress-section',
  adaptiveClasses('processing_indicator', 'primary')
]">
  <!-- Content -->
</div>
```

- [ ] Identify elements needing adaptive behavior
- [ ] Apply `adaptiveClasses()`
- [ ] Specify element ID and role
- [ ] Test visibility changes

### 8. Test Capability Levels

Manually test each capability level:

**First-time user simulation:**
- [ ] All help appears automatically
- [ ] Only primary content is prominent
- [ ] Labels are explicit and clear
- [ ] Advanced features are hidden

**Learning user simulation:**
- [ ] Some help appears when pausing
- [ ] Primary and secondary visible
- [ ] Available features are discoverable
- [ ] Advanced features remain hidden

**Practiced user simulation:**
- [ ] Minimal automatic help
- [ ] All levels except advanced visible
- [ ] Advanced features are one click away
- [ ] Labels are more concise

**Expert user simulation:**
- [ ] No automatic help
- [ ] Everything accessible
- [ ] Labels are terse
- [ ] UI is more compact

### 9. Test Workflow Phases

Test that content appears in the right phases:
- [ ] Setup phase shows correct content
- [ ] Mapping phase shows correct content
- [ ] Configuring phase shows correct content
- [ ] Reviewing phase shows correct content
- [ ] Exploring phase shows correct content
- [ ] Validating phase shows correct content

### 10. Verify Accessibility

- [ ] Keyboard navigation works
- [ ] Focus states are visible
- [ ] Screen reader announcements are appropriate
- [ ] Color is not the only indicator
- [ ] Reduced motion is respected

## Post-Migration Validation

### Functionality
- [ ] All features still accessible
- [ ] Nothing permanently hidden
- [ ] Progressive disclosure works smoothly
- [ ] Help can be dismissed
- [ ] Expansion state is remembered

### User Experience
- [ ] First-time path is clear
- [ ] Expert features are quick to access
- [ ] Interface feels connected
- [ ] Terminology is consistent
- [ ] Actions are clearly labeled

### Performance
- [ ] No unnecessary re-renders
- [ ] Smooth animations
- [ ] Fast capability detection
- [ ] Efficient context tracking

## Common Issues and Solutions

### Issue: Feature never reveals for any user
**Solution:** Check the `level` and `capabilities` props. Make sure at least one capability level can see it.

### Issue: Help appears for experts
**Solution:** Set `expert: null` in the content object, or ensure auto-show phases are appropriate.

### Issue: Labels feel inconsistent
**Solution:** Review all `actionLabel()` and `adaptiveCopy()` calls. Ensure variants follow the same pattern across components.

### Issue: Status messages are redundant
**Solution:** Consolidate multiple status indicators into a single contextual message using `statusMessage()`.

### Issue: Layout shifts when expanding
**Solution:** Use CSS transitions and maintain consistent spacing. Test with different content lengths.

### Issue: Advanced features feel too buried
**Solution:** Review the preview template. Make sure it gives enough information about what's behind the disclosure.

### Issue: First-time users feel overwhelmed
**Solution:** Move more content to secondary or available levels. Check that help is concise and actionable.

### Issue: Expert users complain about extra clicks
**Solution:** Review what's at the advanced level. Consider moving to available level with capability filter.

## Rollback Plan

If migration causes issues:

1. **Keep old component as backup**
   ```
   ComponentName.vue → ComponentName.original.vue
   ComponentNameRefactored.vue → ComponentName.vue
   ```

2. **Feature flag the new version**
   ```vue
   <ComponentOriginal v-if="!useNewGuidance" />
   <ComponentRefactored v-else />
   ```

3. **Gradual migration**
   - Start with least-critical component
   - Gather feedback
   - Refine approach
   - Migrate next component

## Success Criteria

The migration is successful when:

- [ ] First-time users complete task without asking for help
- [ ] Expert users access all features within 2 clicks
- [ ] No features are permanently hidden
- [ ] Help appears at the right moments
- [ ] Interface feels more connected, not more complex
- [ ] User testing shows improved comprehension
- [ ] Analytics show reduced friction

## Files to Update

After migrating a component:

- [ ] Update imports in parent components
- [ ] Update any tests
- [ ] Document any new IDs in guidance system
- [ ] Add to migration tracking document
- [ ] Update any Storybook stories

## Notes and Observations

Use this space to record learnings during migration:

- What worked well?
- What was challenging?
- What patterns emerged?
- What should be improved in the system?
- What documentation is missing?

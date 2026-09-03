---
title: "Step2EnvSetup Migration Strategy"
status: "Normative"
version: "1.0.0"
owner: "Frontend Design"
last_reviewed: "2026-09-03"
review_cycle: "Per migration"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "Step2EnvSetup.vue refactoring"
---

# Step2EnvSetup Migration Strategy

## Component Overview

**Current state:** 2,889 lines, shows everything at once
- Profile generation status (profiles appear incrementally)
- Simulation configuration (platforms, timing, advanced settings)
- 50+ configuration parameters visible simultaneously
- Technical terminology ("recency weight", "echo chamber strength", "viral threshold")
- All advanced settings exposed by default

## Problem Analysis

### Information Overload Patterns

1. **Technical Parameter Dump**
   - Lines 183-236: Advanced assumptions section shows all platform parameters
   - "Recency weighting", "Viral threshold", "Echo-chamber strength" exposed immediately
   - Users must understand technical model parameters to proceed

2. **Premature Complexity**
   - Configuration appears before profiles are generated
   - All timing/platform controls visible before needed
   - Advanced settings not progressive (just wrapped in `<details>`)

3. **No Capability Adaptation**
   - First-time users see same view as experts
   - No contextual help on complex concepts
   - Status messages assume understanding of "agents", "simulation config", "scripts"

## Refactoring Strategy

### Phase 1: Wrap Existing Sections (Low Risk)

Apply `ProgressiveGuidance` to existing DOM structure without rewriting logic.

**Target sections:**

1. **Profile Generation (Lines 38-115)**
   ```vue
   <ProgressiveGuidance
     id="step2-profiles"
     level="primary"
     :capabilities="['first_use', 'learning', 'practiced', 'expert']"
     :phases="['setup', 'mapping']"
   >
     <template #preview>
       {{ profiles.length }} generated perspectives ready
     </template>
     <div class="card-content">
       <!-- existing profile grid -->
     </div>
   </ProgressiveGuidance>
   ```

2. **Advanced Model Settings (Lines 173-370)**
   ```vue
   <ProgressiveGuidance
     id="step2-advanced-settings"
     level="advanced"
     :capabilities="['practiced', 'expert']"
     :expandable="true"
     :autoExpand="false"
   >
     <template #preview>
       Model parameters: 2 conversation spaces, {{ plainRunLength }}
     </template>
     <template #trigger-label>advanced model settings</template>
     <div class="advanced-assumptions-body">
       <!-- existing config blocks -->
     </div>
   </ProgressiveGuidance>
   ```

3. **Simulation Configuration (Lines 117-172)**
   ```vue
   <!-- Keep assumption brief visible for all users -->
   <section class="assumption-brief">
     <!-- Lines 146-171: always visible -->
   </section>
   
   <!-- Wrap detailed platform config -->
   <ProgressiveGuidance
     id="step2-platform-details"
     level="secondary"
     :capabilities="['learning', 'practiced', 'expert']"
   >
     <template #preview>
       Configuration applied · 2 spaces · {{ profiles.length }} profiles
     </template>
     <!-- detailed config blocks -->
   </ProgressiveGuidance>
   ```

### Phase 2: Add Contextual Help (Medium Risk)

Add `ContextualHelp` components for technical concepts.

**High-priority concepts:**

1. **"Generated perspectives" (Line 45)**
   ```vue
   <ContextualHelp
     helpId="generated-perspectives"
     concept="synthetic-agents"
     variant="tooltip"
     :content="{
       first_use: 'Fictional profiles created from your source map patterns. They act as scenario devices, not observations of real people.',
       learning: 'Generated profiles that will produce activity based on source map patterns.',
       practiced: 'Synthetic agents for the simulation.',
       expert: null
     }"
   />
   ```

2. **"Conversation spaces" (Line 148)**
   ```vue
   <ContextualHelp
     helpId="conversation-spaces"
     concept="platform-simulation"
     variant="inline"
     :content="{
       first_use: 'Two different conversation environments. One favors quick posts, the other keeps discussions grouped by topic. This lets you compare how the same starting conditions play out in different spaces.',
       learning: 'Short-post channel vs topic community: two platform types to compare generated activity.',
       practiced: 'Twitter-like and Reddit-like platform simulation.',
       expert: null
     }"
   />
   ```

3. **"Recency weighting / Echo chamber strength" (Lines 195-230)**
   ```vue
   <ContextualHelp
     helpId="model-parameters"
     concept="simulation-weights"
     variant="aside"
     :autoShowPhases="['configuring']"
     :content="{
       first_use: 'These numbers control how the model prioritizes different types of content. Higher recency weight means newer posts get more attention. Higher echo-chamber strength means similar perspectives cluster together more.',
       learning: 'Model tuning parameters: recency favors new content, echo-chamber increases clustering.',
       practiced: 'Platform behavior weights.',
       expert: null
     }"
   />
   ```

### Phase 3: Capability-Adaptive Copy (Medium Risk)

Use `adaptiveCopy` for status messages and labels.

**Target messages:**

1. **Preparation status (Lines 11-14)**
   ```vue
   <script setup>
   import { useAdaptiveUI } from '../composables/useAdaptiveUI';
   const { adaptiveCopy } = useAdaptiveUI();
   
   const preparationTitle = computed(() => {
     return adaptiveCopy('step2-prep-title', {
       first_use: 'Setting up your scenario',
       learning: 'Preparing simulation environment',
       practiced: 'Environment setup',
       expert: 'Prep'
     });
   });
   
   const preparationMessage = computed(() => {
     if (preparationStatus.value === 'processing') {
       return adaptiveCopy('step2-prep-processing', {
         first_use: 'Generating fictional profiles and conversation rules from your source map. This takes about 2 minutes.',
         learning: 'Generating profiles and config from source map.',
         practiced: 'Profile + config generation in progress.',
         expert: `Stage: ${currentStage.value}`
       });
     }
     // ... other states
   });
   </script>
   ```

2. **Step titles (Lines 45, 125)**
   ```vue
   <span class="step-title">
     {{ adaptiveCopy('step2-profiles-title', {
       first_use: 'Create generated perspectives',
       learning: 'Generate profiles',
       practiced: 'Profiles',
       expert: 'Agents'
     }) }}
   </span>
   ```

3. **Configuration labels**
   ```vue
   <span class="config-block-title">
     {{ adaptiveCopy('step2-spaces-label', {
       first_use: 'CONVERSATION SPACES',
       learning: 'PLATFORM CONFIG',
       practiced: 'PLATFORMS',
       expert: 'ENV'
     }) }}
   </span>
   ```

### Phase 4: Progressive Profile Display (Low Risk)

Adapt profile grid based on capability.

**Current:** Shows 6 profiles, then "View all" button (Line 105)

**Refactored:**
```vue
<script setup>
const { guidance } = useAdaptiveUI();

const displayProfiles = computed(() => {
  const capability = guidance.userCapability.value;
  const limit = {
    first_use: 4,      // Show fewer initially
    learning: 6,        // Current behavior
    practiced: 12,      // Show more for practiced users
    expert: profiles.value.length  // Show all for experts
  }[capability];
  
  return showProfilesDetail.value 
    ? profiles.value 
    : profiles.value.slice(0, limit);
});

const shouldShowExpandButton = computed(() => {
  const capability = guidance.userCapability.value;
  if (capability === 'expert') return false;  // Experts see all anyway
  
  const limits = { first_use: 4, learning: 6, practiced: 12 };
  return profiles.value.length > limits[capability];
});
</script>

<template>
  <div class="profiles-list">
    <button
      v-for="profile in displayProfiles"
      :key="profile.id"
      class="profile-card"
      type="button"
      @click="selectProfile(profile)"
    >
      <!-- existing profile card content -->
    </button>
  </div>
  
  <div v-if="shouldShowExpandButton" class="action-section">
    <button
      class="action-btn secondary"
      type="button"
      @click="showProfilesDetail = !showProfilesDetail"
    >
      {{ showProfilesDetail 
        ? 'Show fewer' 
        : `View all ${profiles.length} profiles` 
      }}
    </button>
  </div>
</template>
```

## Implementation Checklist

### Session 1: Low-Risk Wrapping (2 hours)
- [ ] Import `ProgressiveGuidance` and `ContextualHelp`
- [ ] Import `useAdaptiveUI` composable
- [ ] Wrap profile section (Lines 38-115)
- [ ] Wrap advanced settings (Lines 173-370)
- [ ] Test existing functionality unchanged
- [ ] Verify no regressions

### Session 2: Add Contextual Help (1.5 hours)
- [ ] Add help for "generated perspectives"
- [ ] Add help for "conversation spaces"
- [ ] Add help for model parameters
- [ ] Test help appears for first_use
- [ ] Test help fades for practiced/expert

### Session 3: Adaptive Copy (2 hours)
- [ ] Refactor preparation status messages
- [ ] Refactor step titles
- [ ] Refactor configuration labels
- [ ] Test all capability levels
- [ ] Verify terminology consistency

### Session 4: Progressive Display (1 hour)
- [ ] Implement adaptive profile limits
- [ ] Update expand button logic
- [ ] Test with 4, 10, 20+ profiles
- [ ] Verify performance unchanged

### Session 5: Integration Testing (1 hour)
- [ ] Test first-time user flow
- [ ] Test expert user flow
- [ ] Test capability progression
- [ ] Verify accessibility
- [ ] Check against migration checklist

## Success Metrics

**Before migration:**
- All 50+ parameters visible immediately
- Technical terminology unchanging
- Same experience for all users
- 2,889 lines in one component

**After migration:**
- First-time users see 15-20 key items
- Expert users see full technical detail
- Help appears contextually
- Same functionality, adaptive presentation
- No increase in component size (wrapping only)

## Risk Assessment

**Low Risk:**
- Phase 1 (wrapping) — DOM structure unchanged, logic untouched
- Phase 4 (display limits) — cosmetic change to existing pattern

**Medium Risk:**
- Phase 2 (help) — adds new elements but non-breaking
- Phase 3 (copy) — changes visible text but preserves meaning

**High Risk:**
- None (no logic refactoring proposed)

## Rollback Plan

If any phase causes issues:
1. Remove `ProgressiveGuidance` wrapper → reverts to original DOM
2. Remove `ContextualHelp` components → removes help only
3. Revert adaptive copy → restores original labels
4. Git revert specific commits → surgical rollback

## Notes

- Component remains 2,889 lines (no major refactoring)
- All existing logic preserved
- All props/events unchanged
- Parent component (MainView) unaffected
- Can be completed in 5 focused sessions
- Each session independently testable
- No external dependencies added

---

**Next Steps:**
1. Review this strategy with team
2. Create feature branch: `refactor/step2-intelligent-guidance`
3. Execute Session 1 (low-risk wrapping)
4. Test and verify before proceeding
5. Continue with remaining sessions

**References:**
- [Progressive Intelligence Guide](PROGRESSIVE_INTELLIGENCE_GUIDE.md)
- [Component Migration Checklist](COMPONENT_MIGRATION_CHECKLIST.md)
- [Step1GraphBuildRefactored.vue](../../frontend/src/components/Step1GraphBuildRefactored.vue) (working example)

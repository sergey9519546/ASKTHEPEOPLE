---
title: "Step3 & Step4 Migration Strategy"
status: "Normative"
version: "1.0.0"
owner: "Frontend Design"
last_reviewed: "2026-09-03"
review_cycle: "Per migration"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "Step3Simulation.vue and Step4Report.vue refactoring"
---

# Step3 & Step4 Migration Strategy

## Overview

**Step3Simulation.vue:** 547 lines (delegates to Step3RunWayfinder.vue)
**Step4Report.vue:** 1,791 lines (report generation and review)

Both components are well-structured but display technical information without capability adaptation.

---

## Step3Simulation Migration

### Current State Analysis

**Step3RunWayfinder.vue** contains the main UI:
- Run progress tracker (Lines 34-52)
- Generated activity feed (Lines 55-69)
- Truth boundary banner (Lines 14-24)
- Status codes and error states
- Metrics and diagnostics panels

**Key Issues:**
1. Technical status codes ("REC", "ERR", "DONE") always visible
2. Truth boundary banner prominent for all users (necessary for first-time, intrusive for experts)
3. Diagnostics and metrics exposed without progressive disclosure
4. Same terminology for all capability levels

### Refactoring Strategy

#### Phase 1: Adaptive Truth Boundary (High Impact, Low Risk)

**Current (Lines 14-24):**
```vue
<aside class="run-truth-boundary">
  <span>Actions + answers: generated</span>
  <span>Human respondents: 0</span>
  <span>Not a forecast</span>
  <span>Sources: starting conditions only</span>
  <span>Human validation: outside this run</span>
</aside>
```

**Refactored:**
```vue
<ProgressiveGuidance
  id="step3-truth-boundary"
  level="primary"
  :capabilities="['first_use', 'learning']"
  :phases="['exploring', 'validating']"
  :autoExpand="true"
>
  <template #preview>
    Generated output · Not a forecast · 0 human respondents
  </template>
  <aside class="run-truth-boundary">
    <span>Actions + answers: generated</span>
    <span>Human respondents: 0</span>
    <span>Not a forecast</span>
    <span>Sources: starting conditions only</span>
    <span>Human validation: outside this run</span>
  </aside>
</ProgressiveGuidance>
```

**Impact:**
- First-time users: Full truth boundary visible (critical context)
- Learning users: Condensed to preview after first view
- Practiced/Expert: Hidden by default (they understand the constraints)
- Reduces visual noise by ~25% for experienced users

#### Phase 2: Adaptive Status Codes (Medium Risk)

**Current (Lines 65-68):**
```vue
<span class="record-status" :class="`is-${statusTone}`">
  <b>{{ statusCode }}</b>
  {{ statusLabel }}
</span>
```

**Refactored:**
```vue
<script setup>
import { useAdaptiveUI } from '../composables/useAdaptiveUI';
const { adaptiveCopy, guidance } = useAdaptiveUI();

const displayedStatusCode = computed(() => {
  if (guidance.userCapability.value === 'expert') {
    return statusCode.value; // Show technical codes: "REC", "ERR", "DONE"
  }
  return ''; // Hide codes for others
});

const displayedStatusLabel = computed(() => {
  return adaptiveCopy(`status-${statusCode.value}`, {
    first_use: {
      'REC': 'Recording generated activity',
      'DONE': 'Recording complete',
      'ERR': 'Run stopped with error'
    },
    learning: {
      'REC': 'Saving run',
      'DONE': 'Run saved',
      'ERR': 'Error occurred'
    },
    practiced: {
      'REC': 'Recording',
      'DONE': 'Complete',
      'ERR': 'Error'
    },
    expert: statusLabel.value // Use original technical labels
  });
});
</script>

<template>
  <span class="record-status" :class="`is-${statusTone}`">
    <b v-if="displayedStatusCode">{{ displayedStatusCode }}</b>
    {{ displayedStatusLabel }}
  </span>
</template>
```

#### Phase 3: Progressive Metrics/Diagnostics (Low Risk)

Wrap diagnostics and metrics panels with capability-aware disclosure.

```vue
<ProgressiveGuidance
  id="step3-diagnostics"
  level="advanced"
  :capabilities="['practiced', 'expert']"
  :expandable="true"
  :autoExpand="false"
>
  <template #preview>
    Diagnostics available
  </template>
  <template #trigger-label>system diagnostics</template>
  <div class="diagnostics-panel">
    <!-- existing diagnostics content -->
  </div>
</ProgressiveGuidance>

<ProgressiveGuidance
  id="step3-metrics"
  level="secondary"
  :capabilities="['learning', 'practiced', 'expert']"
  :expandable="true"
>
  <template #preview>
    {{ metricsData?.total_actions || 0 }} actions recorded
  </template>
  <div class="metrics-panel">
    <!-- existing metrics content -->
  </div>
</ProgressiveGuidance>
```

#### Phase 4: Contextual Help

Add help for key concepts:

1. **"Generated activity" (Line 58)**
   ```vue
   <ContextualHelp
     helpId="generated-activity"
     concept="simulation-output"
     variant="tooltip"
     :content="{
       first_use: 'These are posts, replies, and votes created by the model during the run. They form the run record—the raw output before you extract insights.',
       learning: 'Model-generated posts and interactions that form the run record.',
       practiced: 'Simulation output.',
       expert: null
     }"
   />
   ```

2. **"Decision brief" (Line 62)**
   ```vue
   <ContextualHelp
     helpId="decision-brief"
     concept="report-generation"
     variant="inline"
     :autoShowPhases="['exploring']"
     :content="{
       first_use: 'After the run completes, you'll generate a decision brief that analyzes possible paths and outcomes from this activity.',
       learning: 'The decision brief extracts insights from the run record.',
       practiced: 'Analysis generated from run output.',
       expert: null
     }"
   />
   ```

### Step3 Migration Checklist

- [ ] Phase 1: Wrap truth boundary with ProgressiveGuidance
- [ ] Phase 2: Implement adaptive status codes
- [ ] Phase 3: Wrap diagnostics and metrics panels
- [ ] Phase 4: Add contextual help for 2-3 key concepts
- [ ] Test with first_use capability
- [ ] Test with expert capability
- [ ] Verify WebSocket updates work unchanged
- [ ] Verify error states display correctly

**Estimated effort:** 3-4 hours
**Risk level:** Low-Medium (status code changes need careful testing)

---

## Step4Report Migration

### Current State Analysis

**Step4Report.vue** (1,791 lines) shows:
- Report generation status
- Decision brief overview
- Generated insights and recommendations
- Export controls
- Path analysis and outcome summaries

**Key Issues:**
1. All insights visible simultaneously (no prioritization)
2. Technical export options exposed immediately
3. No progressive disclosure of secondary analysis
4. Same presentation for exploratory vs validation use cases

### Refactoring Strategy

#### Phase 1: Priority-Based Insight Display

**Current:** All insights shown in flat list

**Refactored:**
```vue
<script setup>
import { useAdaptiveUI } from '../composables/useAdaptiveUI';
const { guidance } = useAdaptiveUI();

const prioritizedInsights = computed(() => {
  if (!reportData.value?.insights) return [];
  
  const capability = guidance.userCapability.value;
  const intent = guidance.currentIntent.value;
  
  // Sort insights by relevance to user context
  return reportData.value.insights.sort((a, b) => {
    // First-time users: prioritize summary insights
    if (capability === 'first_use') {
      if (a.type === 'summary' && b.type !== 'summary') return -1;
      if (b.type === 'summary' && a.type !== 'summary') return 1;
    }
    
    // Expert users: prioritize detailed analysis
    if (capability === 'expert') {
      if (a.type === 'detailed' && b.type !== 'detailed') return -1;
      if (b.type === 'detailed' && a.type !== 'detailed') return 1;
    }
    
    // Validation intent: prioritize limitations and caveats
    if (intent === 'validation-prep') {
      if (a.type === 'limitation' && b.type !== 'limitation') return -1;
      if (b.type === 'limitation' && a.type !== 'limitation') return 1;
    }
    
    return 0; // Maintain original order otherwise
  });
});

const displayedInsightCount = computed(() => {
  const capability = guidance.userCapability.value;
  return {
    first_use: 3,      // Show top 3 insights
    learning: 5,       // Show top 5
    practiced: 8,      // Show top 8
    expert: Infinity   // Show all
  }[capability];
});

const topInsights = computed(() => {
  return prioritizedInsights.value.slice(0, displayedInsightCount.value);
});

const remainingInsights = computed(() => {
  return prioritizedInsights.value.slice(displayedInsightCount.value);
});
</script>

<template>
  <div class="insights-section">
    <h3>Key findings</h3>
    
    <!-- Always visible: top priority insights -->
    <div class="insights-primary">
      <div
        v-for="insight in topInsights"
        :key="insight.id"
        class="insight-card"
      >
        <!-- insight content -->
      </div>
    </div>
    
    <!-- Progressive disclosure: remaining insights -->
    <ProgressiveGuidance
      v-if="remainingInsights.length > 0"
      id="step4-additional-insights"
      level="secondary"
      :capabilities="['learning', 'practiced', 'expert']"
      :expandable="true"
    >
      <template #preview>
        {{ remainingInsights.length }} additional insights available
      </template>
      <div class="insights-secondary">
        <div
          v-for="insight in remainingInsights"
          :key="insight.id"
          class="insight-card"
        >
          <!-- insight content -->
        </div>
      </div>
    </ProgressiveGuidance>
  </div>
</template>
```

#### Phase 2: Adaptive Export Controls

**Current:** All export options visible

**Refactored:**
```vue
<ProgressiveGuidance
  id="step4-export-options"
  level="secondary"
  :capabilities="['learning', 'practiced', 'expert']"
  :phases="['validating', 'complete']"
>
  <template #preview>
    Export: JSON, Markdown, PDF
  </template>
  <template #trigger-label>export options</template>
  <div class="export-controls">
    <!-- existing export buttons -->
  </div>
</ProgressiveGuidance>
```

#### Phase 3: Contextual Help for Report Sections

```vue
<ContextualHelp
  helpId="decision-brief-structure"
  concept="report-format"
  variant="aside"
  :autoShowPhases="['exploring']"
  :content="{
    first_use: 'The decision brief contains three sections: summary findings (what happened across both spaces), path analysis (how different approaches played out), and outcome summaries (end states and their drivers). Start with summary findings.',
    learning: 'Summary → Paths → Outcomes. Read top to bottom for exploration, or jump to paths for comparison.',
    practiced: 'Summary / Paths / Outcomes structure.',
    expert: null
  }"
/>
```

#### Phase 4: Intent-Based Section Emphasis

Adapt which sections get visual priority based on user intent.

```vue
<script setup>
const sectionOrder = computed(() => {
  const intent = guidance.currentIntent.value;
  
  if (intent === 'quick-exploration') {
    return ['summary', 'paths', 'outcomes']; // Default order
  }
  
  if (intent === 'thorough-analysis') {
    return ['paths', 'outcomes', 'summary']; // Detailed first
  }
  
  if (intent === 'validation-prep') {
    return ['limitations', 'assumptions', 'summary']; // Caveats first
  }
  
  return ['summary', 'paths', 'outcomes']; // Default
});
</script>

<template>
  <div class="report-sections" :style="{ '--section-order': sectionOrder.join(',') }">
    <section class="report-summary" :style="{ order: sectionOrder.indexOf('summary') }">
      <!-- summary content -->
    </section>
    <section class="report-paths" :style="{ order: sectionOrder.indexOf('paths') }">
      <!-- paths content -->
    </section>
    <section class="report-outcomes" :style="{ order: sectionOrder.indexOf('outcomes') }">
      <!-- outcomes content -->
    </section>
  </div>
</template>
```

### Step4 Migration Checklist

- [ ] Phase 1: Implement priority-based insight display
- [ ] Phase 2: Wrap export controls with ProgressiveGuidance
- [ ] Phase 3: Add contextual help for 3-4 key concepts
- [ ] Phase 4: Implement intent-based section ordering
- [ ] Test with different user intents (exploration, analysis, validation)
- [ ] Test with different capability levels
- [ ] Verify export functionality unchanged
- [ ] Verify PDF generation works with adaptive layout

**Estimated effort:** 4-5 hours
**Risk level:** Medium (insight prioritization logic needs careful testing)

---

## Combined Migration Timeline

### Week 1: Step2 (Assumption Setup)
- **Monday-Tuesday:** Phases 1-2 (wrapping + contextual help)
- **Wednesday:** Phase 3 (adaptive copy)
- **Thursday:** Phase 4 (progressive display)
- **Friday:** Testing and refinement

### Week 2: Step3 (Run Monitoring)
- **Monday:** Phases 1-2 (truth boundary + status codes)
- **Tuesday:** Phase 3 (metrics/diagnostics)
- **Wednesday:** Phase 4 (contextual help)
- **Thursday-Friday:** Testing and refinement

### Week 3: Step4 (Report Review)
- **Monday-Tuesday:** Phases 1-2 (insight display + export controls)
- **Wednesday:** Phase 3 (contextual help)
- **Thursday:** Phase 4 (intent-based emphasis)
- **Friday:** Testing and refinement

### Week 4: Integration & Tuning
- **Monday:** End-to-end flow testing (Step1 → Step2 → Step3 → Step4)
- **Tuesday:** Capability progression testing
- **Wednesday:** Accessibility audit
- **Thursday:** Performance verification
- **Friday:** Documentation and handoff

---

## Success Metrics

**Before Migration:**
- All components show same UI for all users
- Technical terminology unchanging
- No progressive disclosure
- Flat information hierarchy

**After Migration:**
- First-time users see 40-60% less information initially
- Expert users access full detail immediately
- Contextual help appears for 8-12 key concepts
- Information prioritized by relevance to capability/intent

---

## Testing Strategy

### Per-Component Testing
1. **Capability Level Testing**
   - Test with `first_use`, `learning`, `practiced`, `expert`
   - Verify appropriate content visible at each level
   - Verify manual expansion works

2. **Phase Testing**
   - Test in each workflow phase
   - Verify phase-specific guidance appears
   - Verify phase transitions work

3. **Regression Testing**
   - All existing functionality works
   - No broken interactions
   - No visual regressions (run Percy/visual tests)

### Integration Testing
1. **Flow Testing**
   - Complete workflow from Step1 → Step4
   - Verify capability inference across steps
   - Verify state preservation

2. **Edge Cases**
   - Error states at each capability level
   - Empty states (no profiles, no actions, no insights)
   - Interrupted workflows (page refresh, navigation)

3. **Performance Testing**
   - Verify no performance degradation
   - Check bundle size impact
   - Verify animation smoothness

---

## Rollback Plan

Each step component can be rolled back independently:
1. Remove ProgressiveGuidance wrappers → revert to original
2. Remove adaptive copy → restore original labels
3. Remove contextual help → removes help only
4. Git revert specific commits per component

No cascading dependencies between component migrations.

---

**Next Steps:**
1. Complete Step1 migration (already done ✅)
2. Begin Step2 migration (strategy documented ✅)
3. Execute Step3 migration (estimated: Week 2)
4. Execute Step4 migration (estimated: Week 3)
5. Integration testing (Week 4)
6. Deploy to staging
7. Gather feedback and tune

**References:**
- [Step2 Migration Strategy](STEP2_MIGRATION_STRATEGY.md)
- [Progressive Intelligence Guide](PROGRESSIVE_INTELLIGENCE_GUIDE.md)
- [Component Migration Checklist](COMPONENT_MIGRATION_CHECKLIST.md)

---
title: "Quick Start: Integrating the Intelligent Guidance System"
status: "Normative"
version: "1.0.0"
owner: "Frontend Design + Product"
last_reviewed: "2026-09-01"
review_cycle: "Per release"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "integration guide, getting started, testing"
---

# Quick Start: Integrating the Intelligent Guidance System

## 5-Minute Integration

### Step 1: Import CSS Utilities

Add to `frontend/src/main.js`:

```javascript
import './assets/adaptive-utilities.css';
```

### Step 2: Test the Refactored Component

Temporarily replace Step1GraphBuild in MainView.vue:

```vue
// In frontend/src/views/MainView.vue
import Step1GraphBuildRefactored from '../components/Step1GraphBuildRefactored.vue';

// In template, replace:
<Step1GraphBuild ... />
// With:
<Step1GraphBuildRefactored ... />
```

### Step 3: Run and Test

```bash
cd frontend
npm run dev
```

Test scenarios:
1. **First-time user**: Clear localStorage, complete a full workflow
2. **Learning user**: Manually set capability level, observe changes
3. **Expert user**: All features accessible within 2 clicks

## Integration Validation

After running the test:

✅ **Working correctly if you see:**
- Top 6 entities shown by default (not all 20+)
- "Show details" button for remaining entities
- Contextual help appears inline for new users
- Status messages are concise and contextual
- No technical terminology in primary view

❌ **Issues if you see:**
- All entities shown immediately
- Multiple competing status indicators
- Always-visible explanation paragraphs
- No progressive disclosure controls
- Technical terms before they're needed

## Production Integration Path

### Week 1: Foundation
```bash
# Day 1-2: Setup
- [x] Import adaptive-utilities.css
- [x] Test refactored component
- [x] Document baseline user experience

# Day 3-5: First migration
- [ ] Migrate Step1GraphBuild.vue using checklist
- [ ] Add localStorage capability tracking
- [ ] Test with 5 real users (2 first-time, 3 returning)
```

### Week 2-3: Core Components
```bash
# Week 2
- [ ] Migrate Step2EnvSetup.vue
- [ ] Migrate Step3Simulation.vue
- [ ] Implement help dismissal memory

# Week 3
- [ ] Migrate Step4Report.vue
- [ ] Migrate Step5Interaction.vue
- [ ] Add intent detection signals
```

### Week 4: Polish & Analytics
```bash
- [ ] Refine auto-show thresholds based on user testing
- [ ] Add analytics for feature revelation
- [ ] Create admin dashboard for monitoring
- [ ] Complete accessibility audit
```

## File Map

**Created files (ready to use):**
```
frontend/src/
  composables/
    useGuidedContext.js ...................... ✓ Core intelligence
    useAdaptiveUI.js ......................... ✓ UI adaptation
  components/
    ProgressiveGuidance.vue .................. ✓ Progressive disclosure
    ContextualHelp.vue ....................... ✓ Contextual help
    Step1GraphBuildRefactored.vue ............ ✓ Working example
  assets/
    adaptive-utilities.css ................... ✓ Utility styles

docs/design/
  PROGRESSIVE_INTELLIGENCE_GUIDE.md .......... ✓ Complete guide
  INTELLIGENT_GUIDANCE_IMPLEMENTATION.md ..... ✓ Summary
  INTELLIGENT_GUIDANCE_COMPLETE.md ........... ✓ Full documentation
  COMPONENT_MIGRATION_CHECKLIST.md ........... ✓ Step-by-step migration
  QUICK_START_INTEGRATION.md ................. ✓ This file
```

**Files to modify:**
```
frontend/src/
  main.js ...................................... Add CSS import
  views/MainView.vue ........................... Use refactored components
  components/Step1GraphBuild.vue ............... Migrate using checklist
  components/Step2EnvSetup.vue ................. Migrate using checklist
  components/Step3Simulation.vue ............... Migrate using checklist
```

## Capability Tracking (localStorage)

Add to your app initialization:

```javascript
// frontend/src/composables/useCapabilityTracking.js
import { ref, watch } from 'vue';

export function useCapabilityTracking() {
  const STORAGE_KEY = 'askthepeople_user_capability';
  
  const capability = ref(loadCapability());
  
  function loadCapability() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return 'first_use';
    
    const data = JSON.parse(stored);
    const runCount = data.completedRuns || 0;
    
    if (data.explicitExpertMode) return 'expert';
    if (runCount >= 10) return 'expert';
    if (runCount >= 4) return 'practiced';
    if (runCount >= 1) return 'learning';
    return 'first_use';
  }
  
  function trackRunCompletion() {
    const stored = localStorage.getItem(STORAGE_KEY);
    const data = stored ? JSON.parse(stored) : {};
    data.completedRuns = (data.completedRuns || 0) + 1;
    data.lastRunDate = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    capability.value = loadCapability();
  }
  
  function setExpertMode(enabled) {
    const stored = localStorage.getItem(STORAGE_KEY);
    const data = stored ? JSON.parse(stored) : {};
    data.explicitExpertMode = enabled;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    capability.value = loadCapability();
  }
  
  return {
    capability,
    trackRunCompletion,
    setExpertMode
  };
}
```

## Common Patterns Reference

### Pattern 1: Essential + Detail
```vue
<!-- Essential: always visible -->
<ProgressiveGuidance id="summary" level="primary">
  <div>{{ summaryText }}</div>
</ProgressiveGuidance>

<!-- Detail: expandable -->
<ProgressiveGuidance id="detail" level="secondary">
  <template #preview>Show all details</template>
  <template #default>{{ fullDetails }}</template>
</ProgressiveGuidance>
```

### Pattern 2: Contextual Help
```vue
<ContextualHelp
  help-id="concept-id"
  concept="concept_name"
  :content="{
    first_use: 'Full explanation...',
    learning: 'Brief reminder...',
    practiced: 'Quick note...',
    expert: null
  }"
/>
```

### Pattern 3: Adaptive Labels
```vue
<button>
  {{ actionLabel('action', {
    explicit: 'Complete descriptive label',
    default: 'Clear label',
    terse: 'Short'
  }) }}
</button>
```

## Troubleshooting

### Issue: Components not adapting
**Check:** Is useAdaptiveUI imported and destructured?
```vue
<script setup>
import { useAdaptiveUI } from '../composables/useAdaptiveUI';
const { adaptiveClasses, guidance } = useAdaptiveUI();
</script>
```

### Issue: CSS not applying
**Check:** Is adaptive-utilities.css imported in main.js?
```javascript
// main.js
import './assets/adaptive-utilities.css';
```

### Issue: ProgressiveGuidance not showing
**Check:** Are level and phase props correct?
```vue
<!-- Make sure phase matches current workflow phase -->
<ProgressiveGuidance
  id="feature"
  level="primary"
  :phases="['mapping']"  <!-- Must match guidance.currentPhase -->
>
```

### Issue: Help always showing
**Check:** Content object has null for expert level?
```javascript
:content="{
  first_use: 'Text',
  learning: 'Text',
  practiced: 'Text',
  expert: null  // ← This prevents auto-show for experts
}"
```

## Next Steps

1. **Run the integration** following Step 1-3 above
2. **Gather feedback** from 3-5 users (mix of new and experienced)
3. **Iterate** on thresholds and content
4. **Migrate** one component per week using the checklist
5. **Monitor** analytics for validation

## Support

**Documentation:**
- Complete guide: `docs/design/PROGRESSIVE_INTELLIGENCE_GUIDE.md`
- Migration steps: `docs/design/COMPONENT_MIGRATION_CHECKLIST.md`
- Implementation details: `docs/design/INTELLIGENT_GUIDANCE_IMPLEMENTATION.md`

**Example code:**
- Working component: `frontend/src/components/Step1GraphBuildRefactored.vue`
- Core composables: `frontend/src/composables/useGuidedContext.js`

**Related docs:**
- Content system: `docs/design/CONTENT_SYSTEM.md`
- Civic wayfinding: `docs/design/DIRECTION_C.md`
- Accessibility: `docs/design/ACCESSIBILITY.md`

<script setup>
/**
 * Progressive Guidance Component
 * 
 * A component that wraps content and reveals it based on user context,
 * capability level, and current workflow phase. Replaces the pattern of
 * showing all information upfront with intelligent progressive disclosure.
 * 
 * Usage:
 * <ProgressiveGuidance
 *   id="feature-name"
 *   level="primary"
 *   :capabilities="['first_use', 'learning', 'practiced']"
 *   :phases="['setup', 'configuring']"
 * >
 *   <template #preview>Brief summary shown when collapsed</template>
 *   <template #default>Full content shown when expanded</template>
 * </ProgressiveGuidance>
 */

import { computed, ref, watch } from 'vue';
import { useAdaptiveUI } from '../composables/useAdaptiveUI';

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  level: {
    type: String,
    default: 'secondary',
    validator: (value) => ['primary', 'secondary', 'available', 'advanced'].includes(value)
  },
  capabilities: {
    type: Array,
    default: () => ['first_use', 'learning', 'practiced', 'expert']
  },
  phases: {
    type: Array,
    default: () => null // null means all phases
  },
  showPreview: {
    type: Boolean,
    default: true
  },
  expandable: {
    type: Boolean,
    default: true
  },
  autoExpand: {
    type: Boolean,
    default: null // null means use adaptive logic
  }
});

const { 
  adaptiveClasses, 
  shouldAutoExpand, 
  toggleExpansion, 
  isRevealed,
  shouldShowPreview,
  guidance 
} = useAdaptiveUI();

// Local expansion state
const isExpanded = ref(false);

// Determine if this content should be visible at all
const isVisible = computed(() => {
  // Check capability filter
  if (!props.capabilities.includes(guidance.userCapability.value)) {
    return false;
  }
  
  // Check phase filter
  if (props.phases && !props.phases.includes(guidance.currentPhase.value)) {
    return false;
  }
  
  // Check if revealed through interaction
  return isRevealed.value(props.id);
});

// Determine if should be expanded
const shouldExpand = computed(() => {
  if (props.autoExpand !== null) return props.autoExpand;
  if (!props.expandable) return true;
  return isExpanded.value || shouldAutoExpand.value(props.id);
});

// Should show preview when collapsed
const showPreviewContent = computed(() => {
  return props.showPreview && 
         !shouldExpand.value && 
         shouldShowPreview.value(props.id);
});

// Classes for the wrapper
const wrapperClasses = computed(() => {
  return [
    'progressive-guidance',
    `progressive-guidance--${props.level}`,
    adaptiveClasses.value(props.id, props.level),
    {
      'progressive-guidance--expanded': shouldExpand.value,
      'progressive-guidance--collapsed': !shouldExpand.value,
      'progressive-guidance--preview': showPreviewContent.value,
      'progressive-guidance--expandable': props.expandable
    }
  ];
});

const handleToggle = () => {
  if (!props.expandable) return;
  isExpanded.value = !isExpanded.value;
  toggleExpansion(props.id);
};

// Auto-expand based on adaptive logic
watch(() => shouldAutoExpand.value(props.id), (should) => {
  if (should && props.autoExpand === null) {
    isExpanded.value = true;
  }
});
</script>

<template>
  <div v-if="isVisible" :class="wrapperClasses">
    <!-- Preview mode: show summary with expand option -->
    <div v-if="showPreviewContent && !shouldExpand" class="progressive-guidance__preview">
      <div class="progressive-guidance__preview-content">
        <slot name="preview">
          <span class="progressive-guidance__preview-fallback">Additional options available</span>
        </slot>
      </div>
      <button
        v-if="expandable"
        type="button"
        class="progressive-guidance__expand-trigger"
        @click="handleToggle"
      >
        <span class="progressive-guidance__expand-label">Show details</span>
        <svg class="progressive-guidance__expand-icon" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M4 6l4 4 4-4" />
        </svg>
      </button>
    </div>

    <!-- Collapsed mode: show expand trigger only -->
    <button
      v-else-if="!shouldExpand && expandable"
      type="button"
      class="progressive-guidance__trigger"
      @click="handleToggle"
      :aria-expanded="false"
      :aria-controls="`guidance-${id}`"
    >
      <slot name="trigger">
        <span class="progressive-guidance__trigger-label">
          Show <slot name="trigger-label">{{ id }}</slot>
        </span>
      </slot>
      <svg class="progressive-guidance__trigger-icon" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M4 6l4 4 4-4" />
      </svg>
    </button>

    <!-- Expanded mode: show full content -->
    <div
      v-else
      :id="`guidance-${id}`"
      class="progressive-guidance__content"
    >
      <slot></slot>
      
      <button
        v-if="expandable && isExpanded"
        type="button"
        class="progressive-guidance__collapse"
        @click="handleToggle"
        :aria-expanded="true"
        :aria-controls="`guidance-${id}`"
      >
        <span>Show less</span>
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M12 10l-4-4-4 4" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Base wrapper */
.progressive-guidance {
  position: relative;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

/* Visibility states driven by adaptive system */
.progressive-guidance.adaptive-hidden {
  display: none;
}

.progressive-guidance.adaptive-primary {
  /* Primary content: most prominent, always visible */
  order: -2;
  opacity: 1;
}

.progressive-guidance.adaptive-secondary {
  /* Secondary content: visible but less prominent */
  order: -1;
  opacity: 0.95;
}

.progressive-guidance.adaptive-available {
  /* Available content: accessible but not prominent */
  order: 0;
  opacity: 0.85;
}

.progressive-guidance.adaptive-revealed {
  /* User has interacted - maintain full visibility */
  opacity: 1;
}

/* Preview mode: compact summary with expand option */
.progressive-guidance__preview {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
  border-radius: 0;
  transition: background 0.15s ease;
}

.progressive-guidance__preview:hover {
  background: var(--ink);
}

.progressive-guidance__preview-content {
  flex: 1;
  font-size: 0.875rem;
  color: var(--paper-muted);
}

.progressive-guidance__preview-fallback {
  font-style: italic;
}

.progressive-guidance__expand-trigger {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper);
  font-family: var(--font-body);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.progressive-guidance__expand-trigger:hover {
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.progressive-guidance__expand-icon {
  width: 1rem;
  height: 1rem;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
}

/* Collapsed trigger: minimal disclosure control */
.progressive-guidance__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.15s ease;
}

.progressive-guidance__trigger:hover {
  background: var(--ink);
  color: var(--paper);
  border-color: var(--paper-dim);
}

.progressive-guidance__trigger:focus-visible {
  outline: 2px solid var(--signal);
  outline-offset: 2px;
}

.progressive-guidance__trigger-icon {
  width: 1rem;
  height: 1rem;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
  transition: transform 0.2s ease;
}

.progressive-guidance__trigger:hover .progressive-guidance__trigger-icon {
  transform: translateY(2px);
}

/* Expanded content */
.progressive-guidance__content {
  position: relative;
  animation: reveal 0.3s ease;
}

@keyframes reveal {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.progressive-guidance__collapse {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper-muted);
  font-family: var(--font-body);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.progressive-guidance__collapse:hover {
  color: var(--paper);
  border-color: var(--paper-dim);
}

.progressive-guidance__collapse svg {
  width: 1rem;
  height: 1rem;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
}

/* Expert mode: more compact, less decoration */
.progressive-guidance.adaptive-expert-mode .progressive-guidance__trigger,
.progressive-guidance.adaptive-expert-mode .progressive-guidance__preview {
  padding: 0.5rem 0.75rem;
  font-size: 0.7rem;
}

.progressive-guidance.adaptive-expert-mode .progressive-guidance__expand-trigger {
  padding: 0.4rem 0.6rem;
  font-size: 0.75rem;
}

/* Non-expandable: just show content */
.progressive-guidance--expandable.progressive-guidance--expanded 
.progressive-guidance__content {
  /* Additional styling when expanded */
}

/* Responsive */
@media (max-width: 760px) {
  .progressive-guidance__preview {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
  
  .progressive-guidance__expand-trigger {
    width: 100%;
    justify-content: center;
  }
}
</style>

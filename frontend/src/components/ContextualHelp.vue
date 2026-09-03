<script setup>
/**
 * Contextual Help Component
 * 
 * Provides inline help that appears only when relevant to the user's
 * current capability level, workflow phase, and interaction pattern.
 * 
 * Unlike traditional help text that's always visible or always hidden,
 * this component:
 * - Appears automatically for first-time users on critical concepts
 * - Fades as users demonstrate understanding
 * - Re-appears when users pause or show confusion
 * - Stays accessible for all users via explicit toggle
 */
import { computed, ref } from 'vue';
import { useAdaptiveUI } from '../composables/useAdaptiveUI';

const props = defineProps({
  helpId: {
    type: String,
    required: true
  },
  concept: {
    type: String,
    required: true
  },
  // Help content keyed by capability level
  content: {
    type: Object,
    required: true,
    // Expected shape:
    // {
    //   first_use: "Detailed explanation for first-time users",
    //   learning: "Shorter explanation for learning users",
    //   practiced: "Brief reminder for practiced users",
    //   expert: null // or minimal text
    // }
  },
  // When to show automatically
  autoShowPhases: {
    type: Array,
    default: () => null // null means all phases
  },
  // Visual style
  variant: {
    type: String,
    default: 'inline',
    validator: (value) => ['inline', 'tooltip', 'aside'].includes(value)
  },
  // Icon to show with help
  icon: {
    type: String,
    default: 'info'
  }
});

const emit = defineEmits(['dismissed', 'expanded']);

const { guidance, shouldExplain, adaptiveCopy } = useAdaptiveUI({
  helpContent: { [props.helpId]: props.content }
});

const isManuallyExpanded = ref(false);
const isDismissed = ref(false);

// Should this help be visible?
const shouldShow = computed(() => {
  if (isDismissed.value) return false;
  
  // Manual expansion always shows
  if (isManuallyExpanded.value) return true;
  
  // Check phase filter
  if (props.autoShowPhases && 
      !props.autoShowPhases.includes(guidance.currentPhase.value)) {
    return false;
  }
  
  // Use adaptive logic
  return shouldExplain.value(props.concept);
});

// Get appropriate content for current capability level
const helpContent = computed(() => {
  const capability = guidance.userCapability.value;
  return props.content[capability] || 
         props.content.default || 
         props.content.detailed ||
         '';
});

// Is this help expanded or collapsed?
const isExpanded = computed(() => {
  return isManuallyExpanded.value || 
         (shouldShow.value && props.variant !== 'tooltip');
});

const toggleHelp = () => {
  isManuallyExpanded.value = !isManuallyExpanded.value;
  if (isManuallyExpanded.value) {
    emit('expanded', props.helpId);
    guidance.trackInteraction(`help_${props.helpId}`);
  }
};

const dismissHelp = () => {
  isDismissed.value = true;
  isManuallyExpanded.value = false;
  emit('dismissed', props.helpId);
};

const iconPath = computed(() => {
  const icons = {
    info: 'M12 11v5M12 8h.01M22 12c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2s10 4.477 10 10z',
    question: 'M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01M22 12c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2s10 4.477 10 10z',
    lightbulb: 'M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41M9 16a5 5 0 006 0M12 3a5 5 0 00-5 5v3h10V8a5 5 0 00-5-5z'
  };
  return icons[props.icon] || icons.info;
});
</script>

<template>
  <div
    v-if="shouldShow"
    :class="[
      'contextual-help',
      `contextual-help--${variant}`,
      { 'contextual-help--expanded': isExpanded }
    ]"
  >
    <!-- Inline variant: block element with icon and content -->
    <div v-if="variant === 'inline'" class="contextual-help__inline">
      <div class="contextual-help__header">
        <svg class="contextual-help__icon" viewBox="0 0 24 24" aria-hidden="true">
          <path :d="iconPath" />
        </svg>
        <button
          v-if="guidance.userCapability.value !== guidance.CAPABILITY_LEVELS.FIRST_USE"
          type="button"
          class="contextual-help__dismiss"
          aria-label="Dismiss this help"
          @click="dismissHelp"
        >
          ×
        </button>
      </div>
      <div class="contextual-help__body">
        {{ helpContent }}
      </div>
    </div>

    <!-- Tooltip variant: appears on hover/focus of trigger -->
    <div v-else-if="variant === 'tooltip'" class="contextual-help__tooltip-wrapper">
      <button
        type="button"
        class="contextual-help__trigger"
        aria-label="Show help"
        @click="toggleHelp"
        @mouseenter="isManuallyExpanded = true"
        @mouseleave="isManuallyExpanded = false"
        @focus="isManuallyExpanded = true"
        @blur="isManuallyExpanded = false"
      >
        <svg class="contextual-help__icon" viewBox="0 0 24 24" aria-hidden="true">
          <path :d="iconPath" />
        </svg>
      </button>
      <div
        v-if="isExpanded"
        class="contextual-help__tooltip"
        role="tooltip"
      >
        {{ helpContent }}
      </div>
    </div>

    <!-- Aside variant: sidebar or pull-out panel -->
    <aside v-else-if="variant === 'aside'" class="contextual-help__aside">
      <div class="contextual-help__aside-header">
        <svg class="contextual-help__icon" viewBox="0 0 24 24" aria-hidden="true">
          <path :d="iconPath" />
        </svg>
        <span class="contextual-help__aside-label">Help</span>
        <button
          type="button"
          class="contextual-help__dismiss"
          aria-label="Dismiss this help"
          @click="dismissHelp"
        >
          ×
        </button>
      </div>
      <div class="contextual-help__aside-body">
        {{ helpContent }}
      </div>
    </aside>
  </div>
</template>

<style scoped>
/* Base styles */
.contextual-help {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Inline variant */
.contextual-help__inline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  border-left: 3px solid var(--attention);
  background: rgba(255, 213, 29, 0.08);
  color: var(--paper);
  font-size: 0.875rem;
  line-height: 1.5;
}

.contextual-help__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.contextual-help__icon {
  width: 1.25rem;
  height: 1.25rem;
  stroke: var(--attention);
  stroke-width: 2;
  fill: none;
  flex-shrink: 0;
}

.contextual-help__dismiss {
  margin-left: auto;
  padding: 0.25rem 0.5rem;
  border: 0;
  background: transparent;
  color: var(--paper-muted);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.15s ease;
}

.contextual-help__dismiss:hover {
  color: var(--paper);
}

.contextual-help__body {
  color: var(--paper-muted);
}

/* Tooltip variant */
.contextual-help__tooltip-wrapper {
  position: relative;
  display: inline-block;
}

.contextual-help__trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  border: 1px solid var(--line-dark);
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.contextual-help__trigger:hover {
  border-color: var(--attention);
  background: rgba(255, 213, 29, 0.1);
}

.contextual-help__trigger .contextual-help__icon {
  width: 1rem;
  height: 1rem;
  stroke: var(--paper-muted);
}

.contextual-help__trigger:hover .contextual-help__icon {
  stroke: var(--attention);
}

.contextual-help__tooltip {
  position: absolute;
  bottom: calc(100% + 0.5rem);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  min-width: 200px;
  max-width: 320px;
  padding: 0.75rem 1rem;
  border: 1px solid var(--line-dark);
  background: var(--ink);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  color: var(--paper);
  font-size: 0.8125rem;
  line-height: 1.5;
  white-space: normal;
  animation: tooltipAppear 0.2s ease;
}

@keyframes tooltipAppear {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.contextual-help__tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--ink);
}

/* Aside variant */
.contextual-help__aside {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
  color: var(--paper);
}

.contextual-help__aside-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.contextual-help__aside-label {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--attention);
}

.contextual-help__aside-body {
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--paper-muted);
}

/* Responsive */
@media (max-width: 760px) {
  .contextual-help__inline {
    padding: 0.75rem 0.875rem;
    font-size: 0.8125rem;
  }
  
  .contextual-help__tooltip {
    min-width: 180px;
    max-width: 280px;
    font-size: 0.75rem;
  }
}
</style>

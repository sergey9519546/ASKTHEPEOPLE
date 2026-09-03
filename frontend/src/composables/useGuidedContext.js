/**
 * Guided Context System
 *
 * Tracks user progress, intent, and capability to determine what information
 * and controls should be emphasized, available, or hidden at each moment.
 *
 * This replaces the pattern of showing all features/options/explanations
 * simultaneously with context-aware progressive revelation.
 *
 * State is module-level (a singleton), matching `useWorkspaceState.js`, so a
 * parent view and its child step components read and mutate one shared context.
 * Creating the refs inside the composable would give every caller its own
 * disconnected copy and the guidance would never actually coordinate.
 */

import { computed, readonly, ref } from "vue";

// User capability levels (inferred from behavior, not explicit)
export const CAPABILITY_LEVELS = {
  FIRST_USE: "first_use", // Never completed a run
  LEARNING: "learning", // 1-3 completed runs
  PRACTICED: "practiced", // 4-10 completed runs
  EXPERT: "expert", // 10+ completed runs or explicit preference
};

// Context phases within a workflow
export const WORKFLOW_PHASES = {
  SETUP: "setup", // Defining the decision
  MAPPING: "mapping", // Understanding sources
  CONFIGURING: "configuring", // Setting assumptions
  REVIEWING: "reviewing", // Pre-run validation
  EXPLORING: "exploring", // Examining results
  VALIDATING: "validating", // Planning human research
};

// What the user is trying to accomplish (inferred from actions)
export const USER_INTENTS = {
  QUICK_EXPLORATION: "quick_exploration", // Minimal setup, see what happens
  THOROUGH_ANALYSIS: "thorough_analysis", // Reviewing all options
  COMPARISON: "comparison", // Multiple runs side-by-side
  VALIDATION_PREP: "validation_prep", // Preparing human research
  TROUBLESHOOTING: "troubleshooting", // Something went wrong
};

// === MODULE-LEVEL STATE (shared across all consumers) ===
const currentPhase = ref(WORKFLOW_PHASES.SETUP);
const userCapability = ref(CAPABILITY_LEVELS.FIRST_USE);
const inferredIntent = ref(USER_INTENTS.QUICK_EXPLORATION);

// Track what user has interacted with in this session
const interactedElements = ref(new Set());
const expandedSections = ref(new Set());
const completedCheckpoints = ref(new Set());

// Error and attention state
const activeErrors = ref([]);
const needsAttention = ref([]);

// Timing signals (user is deliberating vs moving quickly)
const timeOnCurrentView = ref(0);
const actionsSinceLastPause = ref(0);

// A single interval owns the time-on-view counter regardless of how many
// components mount the composable.
let viewTimer = null;

const startViewTimer = () => {
  if (viewTimer || typeof window === "undefined") return;
  viewTimer = window.setInterval(() => {
    timeOnCurrentView.value += 1000;
  }, 1000);
};

const stopViewTimer = () => {
  if (!viewTimer) return;
  window.clearInterval(viewTimer);
  viewTimer = null;
};

// === COMPUTED GUIDANCE (module-level so they are computed once) ===

/** How much to explain: minimal | contextual | essential | detailed. */
const explanationLevel = computed(() => {
  if (userCapability.value === CAPABILITY_LEVELS.EXPERT) return "minimal";
  if (userCapability.value === CAPABILITY_LEVELS.PRACTICED) return "contextual";
  if (inferredIntent.value === USER_INTENTS.QUICK_EXPLORATION) return "essential";
  return "detailed";
});

/** What information layer should be prominent. */
const prominentLayer = computed(() => {
  if (activeErrors.value.length > 0) return "error";
  if (needsAttention.value.length > 0 && timeOnCurrentView.value > 30000) {
    return "attention";
  }
  if (inferredIntent.value === USER_INTENTS.QUICK_EXPLORATION) return "action";
  if (inferredIntent.value === USER_INTENTS.THOROUGH_ANALYSIS) return "context";
  return "balanced";
});

/** Should advanced controls be visible. */
const showAdvancedControls = computed(
  () =>
    userCapability.value === CAPABILITY_LEVELS.EXPERT ||
    userCapability.value === CAPABILITY_LEVELS.PRACTICED ||
    inferredIntent.value === USER_INTENTS.THOROUGH_ANALYSIS ||
    expandedSections.value.has("advanced"),
);

/** Which navigation mode to use. */
const navigationMode = computed(() => {
  if (inferredIntent.value === USER_INTENTS.COMPARISON) return "tabs";
  if (currentPhase.value === WORKFLOW_PHASES.EXPLORING) return "spatial";
  return "linear";
});

/** What to emphasize in the current phase. */
const currentEmphasis = computed(() => {
  const phase = currentPhase.value;
  const capability = userCapability.value;
  const intent = inferredIntent.value;

  switch (phase) {
    case WORKFLOW_PHASES.SETUP:
      if (capability === CAPABILITY_LEVELS.FIRST_USE) {
        return {
          primary: "decision_field",
          secondary: "examples",
          available: [],
          hidden: ["route_grammar", "advanced_options", "model_settings"],
        };
      }
      return {
        primary: "decision_field",
        secondary: "source_upload",
        available: ["advanced_options"],
        hidden: ["route_grammar"],
      };

    case WORKFLOW_PHASES.MAPPING:
      if (intent === USER_INTENTS.QUICK_EXPLORATION) {
        return {
          primary: "key_entities",
          secondary: "continue_action",
          available: [],
          hidden: ["full_ontology", "attribute_details", "relationship_types"],
        };
      }
      return {
        primary: "entity_review",
        secondary: "source_map",
        available: ["attribute_details", "relationship_types"],
        hidden: [],
      };

    case WORKFLOW_PHASES.CONFIGURING:
      if (capability === CAPABILITY_LEVELS.FIRST_USE) {
        return {
          primary: "generated_profiles",
          secondary: "scenario_length",
          available: [],
          hidden: ["behavioral_models", "calibration_options", "sampling_strategy"],
        };
      }
      return {
        primary: "assumptions_checklist",
        secondary: "configuration_preview",
        available: ["behavioral_models", "advanced_config"],
        hidden: [],
      };

    case WORKFLOW_PHASES.REVIEWING:
      return {
        primary: "run_summary",
        secondary: "cost_estimate",
        available: ["full_configuration"],
        hidden: [],
      };

    case WORKFLOW_PHASES.EXPLORING:
      if (intent === USER_INTENTS.COMPARISON) {
        return {
          primary: "path_comparison",
          secondary: "key_differences",
          available: ["full_details"],
          hidden: [],
        };
      }
      return {
        primary: "path_overview",
        secondary: "key_insights",
        available: ["supporting_detail", "run_record"],
        hidden: [],
      };

    case WORKFLOW_PHASES.VALIDATING:
      return {
        primary: "validation_questions",
        secondary: "research_handoff",
        available: ["methodology_notes"],
        hidden: [],
      };

    default:
      return { primary: null, secondary: null, available: [], hidden: [] };
  }
});

// === DECISION FUNCTIONS ===

/** Determine if a feature should be visible. */
const shouldShow = (featureId) => {
  const emphasis = currentEmphasis.value;
  if (emphasis.hidden?.includes(featureId)) return false;
  if (featureId === emphasis.primary || featureId === emphasis.secondary) {
    return true;
  }
  if (emphasis.available?.includes(featureId)) {
    return showAdvancedControls.value || interactedElements.value.has(featureId);
  }
  return false;
};

/** Get appropriate label/copy for current context. */
const getContextualCopy = (copyKey, variants) => {
  const level = explanationLevel.value;
  if (variants[level]) return variants[level];
  if (variants.default) return variants.default;
  return variants.detailed || "";
};

/** Should show inline help for this element. */
const shouldShowHelp = (elementId) => {
  if (userCapability.value === CAPABILITY_LEVELS.EXPERT) return false;
  if (expandedSections.value.has(`help_${elementId}`)) return true;
  if (userCapability.value === CAPABILITY_LEVELS.FIRST_USE) {
    const criticalElements = ["decision_field", "source_upload", "primary_action"];
    return criticalElements.includes(elementId);
  }
  return false;
};

// === ACTIONS ===

const setPhase = (phase) => {
  if (phase === currentPhase.value) return;
  currentPhase.value = phase;
  actionsSinceLastPause.value = 0;
  timeOnCurrentView.value = 0;
  startViewTimer();
};

const updateCapability = (level) => {
  if (Object.values(CAPABILITY_LEVELS).includes(level)) {
    userCapability.value = level;
  }
};

const inferIntent = (signals = {}) => {
  if (signals.quickActions && signals.minimalReview) {
    inferredIntent.value = USER_INTENTS.QUICK_EXPLORATION;
  } else if (signals.thoroughReview && signals.expandedSections) {
    inferredIntent.value = USER_INTENTS.THOROUGH_ANALYSIS;
  } else if (signals.multipleRuns) {
    inferredIntent.value = USER_INTENTS.COMPARISON;
  } else if (signals.exportFocus) {
    inferredIntent.value = USER_INTENTS.VALIDATION_PREP;
  } else if (signals.repeatedAttempts) {
    inferredIntent.value = USER_INTENTS.TROUBLESHOOTING;
  }
};

const trackInteraction = (elementId) => {
  // Replace the Set so computed properties depending on it re-evaluate.
  interactedElements.value = new Set(interactedElements.value).add(elementId);
  actionsSinceLastPause.value += 1;
};

const toggleSection = (sectionId) => {
  const next = new Set(expandedSections.value);
  if (next.has(sectionId)) {
    next.delete(sectionId);
  } else {
    next.add(sectionId);
  }
  expandedSections.value = next;
};

const completeCheckpoint = (checkpointId) => {
  completedCheckpoints.value = new Set(completedCheckpoints.value).add(
    checkpointId,
  );
};

const addError = (error) => {
  activeErrors.value = [...activeErrors.value, error];
};

const clearError = (errorId) => {
  activeErrors.value = activeErrors.value.filter((e) => e.id !== errorId);
};

const addAttention = (item) => {
  if (!needsAttention.value.find((a) => a.id === item.id)) {
    needsAttention.value = [...needsAttention.value, item];
  }
};

const clearAttention = (itemId) => {
  needsAttention.value = needsAttention.value.filter((a) => a.id !== itemId);
};

/** Test-only: reset the singleton to defaults. */
const resetGuidedContext = () => {
  currentPhase.value = WORKFLOW_PHASES.SETUP;
  userCapability.value = CAPABILITY_LEVELS.FIRST_USE;
  inferredIntent.value = USER_INTENTS.QUICK_EXPLORATION;
  interactedElements.value = new Set();
  expandedSections.value = new Set();
  completedCheckpoints.value = new Set();
  activeErrors.value = [];
  needsAttention.value = [];
  timeOnCurrentView.value = 0;
  actionsSinceLastPause.value = 0;
  stopViewTimer();
};

export function useGuidedContext() {
  return {
    // State (read-only refs; mutate through the actions below)
    currentPhase: readonly(currentPhase),
    userCapability: readonly(userCapability),
    inferredIntent: readonly(inferredIntent),
    interactedElements: readonly(interactedElements),
    expandedSections: readonly(expandedSections),
    completedCheckpoints: readonly(completedCheckpoints),
    activeErrors: readonly(activeErrors),
    needsAttention: readonly(needsAttention),
    timeOnCurrentView: readonly(timeOnCurrentView),
    actionsSinceLastPause: readonly(actionsSinceLastPause),

    // Computed guidance
    explanationLevel,
    prominentLayer,
    showAdvancedControls,
    navigationMode,
    currentEmphasis,

    // Decision functions
    shouldShow,
    getContextualCopy,
    shouldShowHelp,

    // Actions
    setPhase,
    updateCapability,
    inferIntent,
    trackInteraction,
    toggleSection,
    completeCheckpoint,
    addError,
    clearError,
    addAttention,
    clearAttention,
    resetGuidedContext,

    // Constants for consumers
    CAPABILITY_LEVELS,
    WORKFLOW_PHASES,
    USER_INTENTS,
  };
}

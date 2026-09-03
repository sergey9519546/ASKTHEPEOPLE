/**
 * Adaptive UI Composable
 *
 * Handles progressive disclosure, contextual emphasis, and intelligent defaults
 * based on user context. Surfaces are organized hierarchically: primary action,
 * contextual information, available depth, hidden complexity.
 *
 * The interface adapts without becoming unpredictable. Structure stays stable;
 * emphasis and availability shift.
 */

import { computed, ref } from "vue";
import { useGuidedContext } from "./useGuidedContext";

export function useAdaptiveUI(componentContext = {}) {
  const guidance = useGuidedContext();

  // Component-specific state
  const localExpandedItems = ref(new Set());

  const hasInteracted = (elementId) =>
    guidance.interactedElements.value.has(elementId);

  /**
   * Adaptive visibility classes for an element. Returns a function so callers
   * can pass the element id at the point of use.
   */
  const adaptiveClasses = computed(() => (elementId, role = "secondary") => {
    const classes = [];
    const emphasis = guidance.currentEmphasis.value;

    if (!guidance.shouldShow(elementId)) {
      classes.push("adaptive-hidden");
    } else if (elementId === emphasis.primary) {
      classes.push("adaptive-primary");
    } else if (elementId === emphasis.secondary) {
      classes.push("adaptive-secondary");
    } else if (emphasis.available?.includes(elementId)) {
      classes.push("adaptive-available");
    }

    if (hasInteracted(elementId)) {
      classes.push("adaptive-revealed");
    }

    if (guidance.userCapability.value === guidance.CAPABILITY_LEVELS.EXPERT) {
      classes.push("adaptive-expert-mode");
    }

    // `role` is accepted for call-site clarity and future weighting.
    void role;
    return classes.join(" ");
  });

  /** Get contextual copy with appropriate detail level. */
  const adaptiveCopy = (copyKey, variants) =>
    guidance.getContextualCopy(copyKey, variants);

  /** Should show detailed explanation for this concept. */
  const shouldExplain = computed(() => (conceptId) => {
    if (guidance.userCapability.value === guidance.CAPABILITY_LEVELS.EXPERT) {
      return localExpandedItems.value.has(`explain_${conceptId}`);
    }

    if (guidance.userCapability.value === guidance.CAPABILITY_LEVELS.FIRST_USE) {
      const coreConceptsPerPhase = {
        [guidance.WORKFLOW_PHASES.SETUP]: ["decision_field", "source_material"],
        [guidance.WORKFLOW_PHASES.MAPPING]: ["entities", "relationships", "entity_extraction"],
        [guidance.WORKFLOW_PHASES.CONFIGURING]: ["generated_profiles", "assumptions"],
        [guidance.WORKFLOW_PHASES.EXPLORING]: ["possible_paths", "synthetic_nature"],
      };
      return coreConceptsPerPhase[guidance.currentPhase.value]?.includes(conceptId) || false;
    }

    if (guidance.userCapability.value === guidance.CAPABILITY_LEVELS.LEARNING) {
      return (
        guidance.timeOnCurrentView.value > 15000 && !hasInteracted(conceptId)
      );
    }

    return false;
  });

  /** Determine if a section should be expanded by default. */
  const shouldAutoExpand = computed(() => (sectionId) => {
    const emphasis = guidance.currentEmphasis.value;

    if (sectionId === emphasis.primary) return true;
    if (
      sectionId === emphasis.secondary &&
      guidance.actionsSinceLastPause.value < 3
    ) {
      return true;
    }
    if (localExpandedItems.value.has(sectionId)) return true;
    if (
      guidance.inferredIntent.value === guidance.USER_INTENTS.QUICK_EXPLORATION
    ) {
      return sectionId === emphasis.primary;
    }
    return false;
  });

  /** Get appropriate button label based on context. */
  const actionLabel = computed(() => (action, variants) => {
    const capability = guidance.userCapability.value;
    if (capability === guidance.CAPABILITY_LEVELS.EXPERT && variants.terse) {
      return variants.terse;
    }
    if (
      capability === guidance.CAPABILITY_LEVELS.FIRST_USE &&
      variants.explicit
    ) {
      return variants.explicit;
    }
    return variants.default || variants.explicit || action;
  });

  /** Determine layout mode based on context. */
  const layoutMode = computed(() => {
    const phase = guidance.currentPhase.value;
    const intent = guidance.inferredIntent.value;

    if (intent === guidance.USER_INTENTS.COMPARISON) return "split";
    if (phase === guidance.WORKFLOW_PHASES.EXPLORING) return "spatial";
    if (
      phase === guidance.WORKFLOW_PHASES.SETUP ||
      phase === guidance.WORKFLOW_PHASES.CONFIGURING
    ) {
      return "linear";
    }
    return "focus";
  });

  /** Should show preview/summary of hidden content. */
  const shouldShowPreview = computed(() => (contentId) => {
    const emphasis = guidance.currentEmphasis.value;
    if (
      emphasis.available?.includes(contentId) &&
      !guidance.showAdvancedControls.value
    ) {
      return true;
    }
    if (
      guidance.inferredIntent.value === guidance.USER_INTENTS.THOROUGH_ANALYSIS
    ) {
      return true;
    }
    return false;
  });

  /** Get contextual placeholder text. */
  const placeholderText = computed(() => (fieldId) => {
    const capability = guidance.userCapability.value;
    const placeholders = {
      decision_field: {
        first_use:
          'What decision are you exploring? (e.g., "Should we expand our service to a new city?")',
        learning: "Describe the decision you want to explore",
        practiced: "Your decision",
        expert: "Decision",
      },
      source_upload: {
        first_use: "Add documents to inform the scenario (optional)",
        learning: "Add source material",
        practiced: "Sources",
        expert: "Sources",
      },
    };
    const fieldPlaceholders = placeholders[fieldId];
    if (!fieldPlaceholders) return "";
    return fieldPlaceholders[capability] || fieldPlaceholders.default || "";
  });

  /** Determine if inline help should be visible, returning its content. */
  const inlineHelp = computed(() => (helpId) => {
    if (!guidance.shouldShowHelp(helpId)) return null;
    const helpContent = componentContext.helpContent?.[helpId];
    if (!helpContent) return null;
    const capability = guidance.userCapability.value;
    if (helpContent.levels) {
      return helpContent.levels[capability] || helpContent.levels.default;
    }
    return helpContent;
  });

  /** Get contextual status message. */
  const statusMessage = computed(() => (statusType, data = {}) => {
    const messages = {
      processing: {
        quick: "Preparing…",
        detailed: `${data.stage || "Processing"}… ${data.progress || ""}`.trim(),
        expert: data.stage || "Processing",
      },
      ready: {
        quick: "Ready",
        detailed: `${data.itemCount || "Everything"} ready to review`,
        expert: "Ready",
      },
      error: {
        quick: "Needs attention",
        detailed: data.message || "Something needs your attention",
        expert: data.code || "Error",
      },
      waiting: {
        quick: "Waiting",
        detailed: `Waiting for ${data.dependency || "previous step"}`,
        expert: "Blocked",
      },
    };
    const statusMessages = messages[statusType];
    if (!statusMessages) return "";
    const level = guidance.explanationLevel.value;
    const mapping = {
      minimal: "expert",
      contextual: "detailed",
      essential: "quick",
      detailed: "detailed",
    };
    return statusMessages[mapping[level]] || statusMessages.detailed;
  });

  /** Toggle expansion of a collapsible section. */
  const toggleExpansion = (itemId) => {
    const next = new Set(localExpandedItems.value);
    if (next.has(itemId)) {
      next.delete(itemId);
    } else {
      next.add(itemId);
      guidance.trackInteraction(itemId);
    }
    localExpandedItems.value = next;
  };

  /** Reveal a hidden feature (make it available). */
  const revealFeature = (featureId) => {
    guidance.trackInteraction(featureId);
    localExpandedItems.value = new Set(localExpandedItems.value).add(featureId);
  };

  /** Check if a feature is currently revealed. */
  const isRevealed = computed(() => (featureId) => {
    return (
      localExpandedItems.value.has(featureId) ||
      hasInteracted(featureId) ||
      guidance.shouldShow(featureId)
    );
  });

  return {
    // Computed properties
    adaptiveClasses,
    shouldExplain,
    shouldAutoExpand,
    actionLabel,
    layoutMode,
    shouldShowPreview,
    placeholderText,
    inlineHelp,
    statusMessage,
    isRevealed,

    // Methods
    adaptiveCopy,
    toggleExpansion,
    revealFeature,

    // Expose guidance for advanced use
    guidance,
  };
}

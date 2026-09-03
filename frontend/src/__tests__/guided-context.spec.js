// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from "vitest";
import {
  CAPABILITY_LEVELS,
  USER_INTENTS,
  WORKFLOW_PHASES,
  useGuidedContext,
} from "../composables/useGuidedContext.js";
import { useAdaptiveUI } from "../composables/useAdaptiveUI.js";
import { deriveCapability } from "../composables/useCapabilityTracking.js";

describe("useGuidedContext singleton", () => {
  beforeEach(() => {
    useGuidedContext().resetGuidedContext();
  });

  it("shares one state across separate calls", () => {
    const a = useGuidedContext();
    const b = useGuidedContext();
    a.setPhase(WORKFLOW_PHASES.CONFIGURING);
    // b is a distinct closure but must observe a's mutation.
    expect(b.currentPhase.value).toBe(WORKFLOW_PHASES.CONFIGURING);
  });

  it("exposes timing and interaction state as reactive refs", () => {
    const ctx = useGuidedContext();
    expect(ctx.interactedElements.value instanceof Set).toBe(true);
    expect(typeof ctx.timeOnCurrentView.value).toBe("number");
    expect(typeof ctx.actionsSinceLastPause.value).toBe("number");
  });

  it("records interactions and increments action count", () => {
    const ctx = useGuidedContext();
    ctx.trackInteraction("entity_detail");
    expect(ctx.interactedElements.value.has("entity_detail")).toBe(true);
    expect(ctx.actionsSinceLastPause.value).toBe(1);
  });

  it("resets action count and view time on phase change", () => {
    const ctx = useGuidedContext();
    ctx.trackInteraction("x");
    expect(ctx.actionsSinceLastPause.value).toBe(1);
    ctx.setPhase(WORKFLOW_PHASES.MAPPING);
    expect(ctx.actionsSinceLastPause.value).toBe(0);
  });

  it("prioritizes the error layer whenever an error is active", () => {
    const ctx = useGuidedContext();
    ctx.addError({ id: "e1", message: "boom" });
    expect(ctx.prominentLayer.value).toBe("error");
    ctx.clearError("e1");
    expect(ctx.prominentLayer.value).not.toBe("error");
  });

  it("hides route_grammar for a first-use setup emphasis", () => {
    const ctx = useGuidedContext();
    ctx.updateCapability(CAPABILITY_LEVELS.FIRST_USE);
    ctx.setPhase(WORKFLOW_PHASES.SETUP);
    expect(ctx.currentEmphasis.value.hidden).toContain("route_grammar");
    expect(ctx.shouldShow("route_grammar")).toBe(false);
    expect(ctx.shouldShow("decision_field")).toBe(true);
  });

  it("reveals an available feature once interacted with", () => {
    const ctx = useGuidedContext();
    ctx.updateCapability(CAPABILITY_LEVELS.FIRST_USE);
    ctx.setPhase(WORKFLOW_PHASES.EXPLORING);
    // supporting_detail is available in exploring; first-use hides advanced by default.
    expect(ctx.shouldShow("supporting_detail")).toBe(false);
    ctx.trackInteraction("supporting_detail");
    expect(ctx.shouldShow("supporting_detail")).toBe(true);
  });

  it("maps capability to explanation level", () => {
    const ctx = useGuidedContext();
    ctx.updateCapability(CAPABILITY_LEVELS.EXPERT);
    expect(ctx.explanationLevel.value).toBe("minimal");
    ctx.updateCapability(CAPABILITY_LEVELS.PRACTICED);
    expect(ctx.explanationLevel.value).toBe("contextual");
  });

  it("suppresses inline help for experts", () => {
    const ctx = useGuidedContext();
    ctx.updateCapability(CAPABILITY_LEVELS.EXPERT);
    expect(ctx.shouldShowHelp("decision_field")).toBe(false);
    ctx.updateCapability(CAPABILITY_LEVELS.FIRST_USE);
    expect(ctx.shouldShowHelp("decision_field")).toBe(true);
  });
});

describe("useAdaptiveUI", () => {
  beforeEach(() => {
    useGuidedContext().resetGuidedContext();
  });

  it("returns explicit labels for first-use and terse for expert", () => {
    const ctx = useGuidedContext();
    const { actionLabel } = useAdaptiveUI();
    const variants = { explicit: "Continue to set assumptions", default: "Continue", terse: "Next" };

    ctx.updateCapability(CAPABILITY_LEVELS.FIRST_USE);
    expect(actionLabel.value("continue", variants)).toBe("Continue to set assumptions");

    ctx.updateCapability(CAPABILITY_LEVELS.EXPERT);
    expect(actionLabel.value("continue", variants)).toBe("Next");
  });

  it("produces adaptive classes reflecting emphasis", () => {
    const ctx = useGuidedContext();
    ctx.updateCapability(CAPABILITY_LEVELS.FIRST_USE);
    ctx.setPhase(WORKFLOW_PHASES.SETUP);
    const { adaptiveClasses } = useAdaptiveUI();
    expect(adaptiveClasses.value("decision_field")).toContain("adaptive-primary");
    expect(adaptiveClasses.value("route_grammar")).toContain("adaptive-hidden");
  });

  it("adapts status messages to explanation level", () => {
    const ctx = useGuidedContext();
    const { statusMessage } = useAdaptiveUI();

    ctx.updateCapability(CAPABILITY_LEVELS.EXPERT);
    expect(statusMessage.value("ready", { itemCount: 6 })).toBe("Ready");

    ctx.updateCapability(CAPABILITY_LEVELS.PRACTICED);
    expect(statusMessage.value("ready", { itemCount: 6 })).toBe("6 ready to review");
  });

  it("auto-expands the primary section only in quick exploration", () => {
    const ctx = useGuidedContext();
    ctx.setPhase(WORKFLOW_PHASES.MAPPING); // quick-exploration default => primary key_entities
    const { shouldAutoExpand } = useAdaptiveUI();
    expect(shouldAutoExpand.value("key_entities")).toBe(true);
    expect(shouldAutoExpand.value("relationship_types")).toBe(false);
  });
});

describe("deriveCapability", () => {
  it("maps run counts to levels", () => {
    expect(deriveCapability({ completedRuns: 0 })).toBe(CAPABILITY_LEVELS.FIRST_USE);
    expect(deriveCapability({ completedRuns: 1 })).toBe(CAPABILITY_LEVELS.LEARNING);
    expect(deriveCapability({ completedRuns: 4 })).toBe(CAPABILITY_LEVELS.PRACTICED);
    expect(deriveCapability({ completedRuns: 10 })).toBe(CAPABILITY_LEVELS.EXPERT);
  });

  it("honors explicit expert mode regardless of run count", () => {
    expect(deriveCapability({ completedRuns: 0, explicitExpertMode: true })).toBe(
      CAPABILITY_LEVELS.EXPERT,
    );
  });
});

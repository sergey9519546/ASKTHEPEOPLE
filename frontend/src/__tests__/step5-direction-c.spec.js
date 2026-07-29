import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const step5 = readFileSync(
  resolve("src/components/Step5Interaction.vue"),
  "utf8",
);
const interactionView = readFileSync(
  resolve("src/views/InteractionView.vue"),
  "utf8",
);
const opinionMap = readFileSync(
  resolve("src/components/OpinionMap.vue"),
  "utf8",
);

describe("Step 5 Direction C interaction contracts", () => {
  it("leads with a plain-language follow-up flow and persistent truth boundary", () => {
    expect(step5).toContain("Ask what the report means. Test what it missed.");
    expect(step5).toContain("Explain the report");
    expect(step5).toContain("Ask a fictional profile");
    expect(step5).toContain("Ask a fictional group");
    expect(step5).toContain("0 human respondents");
    expect(step5).toContain("Not a forecast");
    expect(step5).toContain("Fictional response generated on request");
    expect(step5).not.toContain("v-html");
  });

  it("keeps diagnostics and generated traces in one secondary disclosure", () => {
    expect(step5).toContain('class="secondary-record"');
    expect(step5).toContain(
      "Report context, generated traces, and diagnostics",
    );
    expect(step5).toContain("Secondary record · closed by default");
    expect(step5).toContain("Recent generated activity");
    expect(step5).toContain("Workspace messages");
    expect(step5).not.toContain("Evidence summary");
    expect(step5).not.toContain("sim-dashboard");
    expect(step5).not.toContain("activity-container");
  });

  it("preserves report chat, fictional response, export, stop, and map actions", () => {
    expect(step5).toContain("chatWithReport({");
    expect(step5).toContain("askSyntheticProfiles({");
    expect(step5).toContain("exportGeneratedResponsesCSV(");
    expect(step5).toContain("stopSimulation({");
    expect(step5).toContain("<OpinionMap");
    expect(step5).toContain('const activeTab = ref("chat")');
    expect(step5).toContain('const chatTarget = ref("report_agent")');
    expect(step5).toContain('maxlength="4000"');
    expect(step5).toContain('maxlength="2000"');
  });

  it("puts the primary question before the transcript and exposes a compact mode chooser", () => {
    expect(step5).toContain("Choose a follow-up mode");
    expect(step5).toContain("Start here · ask one clear question");
    expect(step5.indexOf('class="question-composer"')).toBeLessThan(
      step5.indexOf('class="messages-list"'),
    );
    expect(step5).toContain(
      ".followup-modes button:nth-of-type(odd)",
    );
    expect(step5).toContain(
      "grid-template-columns: repeat(2, minmax(0, 1fr));",
    );
  });

  it("distinguishes loading, partial failure, disconnection, and true empty states", () => {
    expect(step5).toContain('data-testid="workspace-loading"');
    expect(step5).toContain('data-testid="workspace-load-error"');
    expect(step5).toContain('data-testid="workspace-load-warning"');
    expect(step5).toContain('data-testid="run-status-disconnected"');
    expect(step5).toContain("Nothing is being treated as empty while these records load.");
    expect(step5).toContain("This is a connection problem, not an empty profile set.");
    expect(step5).toContain("Reconnect live updates");
    expect(step5).toContain('emit("update-status", "error")');
  });

  it("uses ordinary labeled profile-choice buttons instead of an incomplete listbox", () => {
    expect(step5).toContain('role="group"');
    expect(step5).toContain('aria-label="Fictional profile choices"');
    expect(step5).toContain(
      ':aria-pressed="selectedAgentIndex === profileIndex"',
    );
    expect(step5).not.toContain('role="listbox"');
    expect(step5).not.toContain('role="option"');
    expect(step5).not.toContain('aria-haspopup="listbox"');
  });

  it("renders the generated-interaction map as flat civic wayfinding", () => {
    expect(opinionMap).toContain("Generated interaction route");
    expect(opinionMap).toContain("What happened inside this run");
    expect(opinionMap).toContain("0 human respondents");
    expect(opinionMap).toContain("Not public opinion · not a forecast");
    expect(opinionMap).toContain('class="route-board"');
    expect(opinionMap).toContain('class="technical-record"');
    expect(opinionMap).toContain("closed by default");
    expect(opinionMap).not.toMatch(/\b3D\b/i);
    expect(opinionMap).not.toMatch(/\bcube\b/i);
    expect(opinionMap).not.toMatch(/\bSTANCE\b/);
    expect(opinionMap).not.toMatch(/\bINTENSITY\b/);
    expect(opinionMap).not.toMatch(/\bNUANCE\b/);
    expect(opinionMap).not.toContain("translate3d");
    expect(opinionMap).not.toContain("rotateX");
    expect(opinionMap).not.toContain("rotateY");
    expect(opinionMap).not.toContain(".toFixed(");
  });

  it("uses Conversation as the default shell and keeps mobile modes exclusive", () => {
    expect(interactionView).toContain('const viewMode = ref("workbench")');
    expect(interactionView).toContain('const currentStatus = ref("processing")');
    expect(interactionView).toContain('error: "NEEDS ATTENTION"');
    expect(interactionView).toContain('aria-live="polite"');
    expect(interactionView).toContain(':aria-pressed="viewMode === m"');
    expect(interactionView).toContain('split: "Compare"');
    expect(interactionView).toContain('workbench: "Conversation"');
    expect(interactionView).toContain(':class="`mode-${viewMode}`"');
    expect(interactionView).toContain(
      ".workbench-viewport.mode-workbench .panel-container.left",
    );
    expect(interactionView).toContain("display: none !important;");
    expect(interactionView).toContain(
      "height: calc(100dvh - 11rem) !important;",
    );
    expect(interactionView).toContain(
      "0 human respondents · not a forecast",
    );
  });
});

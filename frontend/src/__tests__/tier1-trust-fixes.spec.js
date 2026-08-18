// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ProjectLinks from "../components/ProjectLinks.vue";
import TruthRail from "../components/TruthRail.vue";

describe("T1 — permanent disclosure is a static region, not a live alert", () => {
  it("renders the truth rail as role=note with its label intact and no aria-live", () => {
    const wrapper = mount(TruthRail);
    const rail = wrapper.get(".truth-rail");

    expect(rail.attributes("role")).toBe("note");
    expect(rail.attributes("aria-live")).toBeUndefined();
    expect(rail.attributes("aria-label")).toContain("HUMAN RESPONDENTS: 0");
    expect(rail.attributes("aria-label")).toContain("NOT A FORECAST");
  });
});

describe("X1 — transparency links are served and legible", () => {
  it("points Provenance at the real repo document instead of a 404 path", () => {
    const wrapper = mount(ProjectLinks);
    const provenance = wrapper
      .findAll("a")
      .find((a) => a.text() === "Provenance");

    expect(provenance.attributes("href")).toBe(
      "https://github.com/sergey9519546/ASKTHEPEOPLE/blob/main/PROVENANCE.md",
    );
  });

  it("uses a legible link font size, not 0.58rem", () => {
    const source = readFileSync(resolve("src/components/ProjectLinks.vue"), "utf8");
    expect(source).toContain("font-size: 0.72rem");
    expect(source).not.toContain("font-size: 0.58rem");
  });
});

describe("H3 — readiness badge is a neutral prompt-detail signal", () => {
  it("claims no precision and shows no percentage", () => {
    const home = readFileSync(resolve("src/views/Home.vue"), "utf8");

    expect(home).not.toContain("High-Precision");
    expect(home).not.toContain("Grounded Scenario");
    expect(home).not.toContain("Initial Prompt");
    expect(home).not.toMatch(/sourceReadiness\.score/);
    expect(home).toContain('label: "Decision only"');
    expect(home).toContain('label: "Decision + sources"');
    expect(home).toContain('label: "Decision + context + sources"');
  });
});

describe("H4 — consent is an explicit act", () => {
  it("quick-start presets never pre-check the use-policy acknowledgment", () => {
    const home = readFileSync(resolve("src/views/Home.vue"), "utf8");

    // applyPreset fills the form but must not set the acknowledgment.
    const applyPresetBlock = home.slice(
      home.indexOf("const applyPreset"),
      home.indexOf("const sourceReadiness"),
    );
    expect(applyPresetBlock).not.toContain("usePolicyAcknowledged.value = true");

    // The checkbox stays user-bound and required.
    expect(home).toContain('v-model="usePolicyAcknowledged"');
    expect(home).toContain('type="checkbox" required');
  });
});

describe("M1 — prompt-only workspaces are not a dead-end", () => {
  it("handleNewProject no longer rejects zero files with a misleading error", () => {
    const main = readFileSync(resolve("src/views/MainView.vue"), "utf8");

    expect(main).not.toContain("No source files were carried into this workspace");
    expect(main).not.toContain("pending.files.length === 0");
    expect(main).toContain(
      "No decision was carried into this workspace. Return to the decision and start again.",
    );
  });
});

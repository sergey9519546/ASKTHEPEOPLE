// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

const simulationApi = vi.hoisted(() => ({
  createSimulation: vi.fn(),
  getPrepareStatus: vi.fn(),
  getSimulationConfigRealtime: vi.fn(),
  getSimulationProfilesRealtime: vi.fn(),
  prepareSimulation: vi.fn(),
}));

vi.mock("../api/simulation", () => simulationApi);
vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

import AccessKeyGate from "../components/AccessKeyGate.vue";
import Step1GraphBuild from "../components/Step1GraphBuild.vue";
import Step2EnvSetup from "../components/Step2EnvSetup.vue";

const preparedConfig = {
  time_config: {
    total_simulation_hours: 24,
    minutes_per_round: 15,
  },
  event_config: {
    narrative_direction: "Explore multiple possible reactions.",
    hot_topics: ["service"],
    initial_posts: [],
  },
  twitter_config: {
    recency_weight: 0.4,
    viral_threshold: 10,
  },
  reddit_config: {
    relevance_weight: 0.3,
    echo_chamber_strength: 0.5,
  },
};

const generatedProfile = {
  id: 0,
  name: "Avery Chen",
  username: "avery_chen",
  profession: "Transit rider",
  bio: "A fictional profile created for this scenario.",
  interested_topics: ["service"],
};

async function settlePreparation() {
  await flushPromises();
  await nextTick();
  await flushPromises();
}

describe("early journey accessibility and readiness contracts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    simulationApi.prepareSimulation.mockResolvedValue({
      success: true,
      data: { already_prepared: true },
    });
    simulationApi.getSimulationProfilesRealtime.mockResolvedValue({
      success: true,
      data: { profiles: [generatedProfile], total_expected: 1 },
    });
    simulationApi.getSimulationConfigRealtime.mockResolvedValue({
      success: true,
      data: {
        config_generated: true,
        is_generating: false,
        generation_stage: "completed",
        config: preparedConfig,
      },
    });
  });

  it("traps access-gate focus, locks page scroll, and restores focus", async () => {
    const returnTarget = document.createElement("button");
    returnTarget.textContent = "Underlying action";
    document.body.appendChild(returnTarget);
    returnTarget.focus();

    const wrapper = mount(AccessKeyGate, { attachTo: document.body });
    await nextTick();
    await nextTick();

    const keyInput = wrapper.get("#access-key").element;
    expect(document.activeElement).toBe(keyInput);
    expect(document.body.style.overflow).toBe("hidden");

    document.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "Tab",
        shiftKey: true,
        bubbles: true,
        cancelable: true,
      }),
    );
    expect(document.activeElement).toBe(wrapper.get(".reveal-key").element);

    wrapper.unmount();
    expect(document.body.style.overflow).toBe("");
    expect(document.activeElement).toBe(returnTarget);
    returnTarget.remove();
  });

  it("keeps source-map items keyboard operable and restores modal focus", async () => {
    const wrapper = mount(Step1GraphBuild, {
      attachTo: document.body,
      props: {
        currentPhase: 2,
        projectData: {
          project_id: "project-1",
          graph_id: "graph-1",
          ontology: {
            entity_types: [
              {
                name: "Weekend rider",
                description: "A source-map concept.",
              },
            ],
            edge_types: [],
          },
        },
        graphData: { nodes: [{ id: "node-1" }], edges: [] },
        systemLogs: [],
      },
    });

    const sourceMapButton = wrapper.get(".entity-tag");
    expect(sourceMapButton.element.tagName).toBe("BUTTON");
    sourceMapButton.element.focus();
    await sourceMapButton.trigger("click");
    await nextTick();

    expect(wrapper.get('[role="dialog"]').attributes("aria-modal")).toBe("true");
    expect(document.activeElement).toBe(wrapper.get(".close-btn").element);
    await wrapper.get('[role="dialog"]').trigger("keydown", { key: "Escape" });
    await nextTick();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(document.activeElement).toBe(sourceMapButton.element);
    wrapper.unmount();
  });

  it("blocks an empty or unreferenced source map before setup", () => {
    const wrapper = mount(Step1GraphBuild, {
      props: {
        currentPhase: 2,
        projectData: { project_id: "project-1", ontology: {} },
        graphData: { nodes: [], edges: [] },
      },
    });

    expect(wrapper.get(".action-btn").attributes()).toHaveProperty("disabled");
    expect(wrapper.get(".readiness-note").text()).toContain("source map is empty");
  });

  it("presents progress as plain-language notes instead of a system terminal", () => {
    const wrapper = mount(Step1GraphBuild, {
      props: {
        currentPhase: 1,
        projectData: { project_id: "project-1", ontology: {} },
        graphData: { nodes: [], edges: [] },
        systemLogs: [
          { time: "09:41", msg: "Source reading started." },
          { time: "09:42", msg: "Source categories are ready to review." },
        ],
      },
    });

    expect(wrapper.get(".activity-status").text()).toContain("Source-map progress");
    expect(wrapper.get(".activity-history summary").text()).toContain(
      "Review progress notes",
    );
    expect(wrapper.text()).not.toContain("System Terminal");
    expect(wrapper.text()).not.toContain("$>");
  });

  it("emits one resolved suggested round count after complete preparation", async () => {
    const wrapper = mount(Step2EnvSetup, {
      props: {
        simulationId: "simulation-1",
        systemLogs: [],
      },
    });
    await settlePreparation();

    expect(wrapper.get(".preparation-banner").classes()).toContain("is-completed");
    expect(wrapper.get(".profile-card").element.tagName).toBe("BUTTON");
    expect(wrapper.get(".assumption-brief").text()).toContain(
      "Two generated conversation spaces",
    );
    expect(wrapper.get(".assumption-brief").text()).toContain(
      "fictional perspectives",
    );
    expect(wrapper.get(".advanced-assumptions").attributes("open")).toBeUndefined();
    expect(wrapper.text()).not.toContain("PROFILE_");
    expect(wrapper.text()).not.toContain("Generated participant");
    expect(wrapper.get(".action-btn:not(.secondary)").attributes("disabled")).toBeUndefined();

    await wrapper.get(".action-btn:not(.secondary)").trigger("click");
    expect(wrapper.emitted("next-step")?.at(-1)?.[0]).toEqual({
      maxRounds: 96,
    });
    wrapper.unmount();
  });

  it("shows a retry state and keeps run disabled when profiles are empty", async () => {
    simulationApi.getSimulationProfilesRealtime.mockResolvedValue({
      success: true,
      data: { profiles: [], total_expected: 0 },
    });

    const wrapper = mount(Step2EnvSetup, {
      props: {
        simulationId: "simulation-empty",
        systemLogs: [],
      },
    });
    await settlePreparation();

    expect(wrapper.get(".preparation-banner").classes()).toContain("is-error");
    expect(wrapper.get(".preparation-banner").text()).toContain(
      "without any generated profiles",
    );
    expect(wrapper.get(".retry-button").text()).toContain("Try preparation again");
    expect(wrapper.get(".action-btn:not(.secondary)").attributes()).toHaveProperty(
      "disabled",
    );
    wrapper.unmount();
  });
});

describe("early journey source contracts", () => {
  it("separates uploaded source material from evidence and nested controls", () => {
    const home = readFileSync(resolve("src/views/Home.vue"), "utf8");

    expect(home).toContain("Source material (optional)");
    expect(home).not.toContain("<strong>Evidence in</strong>");
    expect(home).toContain('class="source-material"');
    expect(home).toContain('class="source-dropzone"');
    expect(home).toContain('class="submission-requirements"');
    expect(home).toContain('prefers-reduced-motion: reduce');
  });

  it("makes the access-gated background inert and mobile panels exclusive", () => {
    const app = readFileSync(resolve("src/App.vue"), "utf8");
    const main = readFileSync(resolve("src/views/MainView.vue"), "utf8");
    const simulation = readFileSync(resolve("src/views/SimulationView.vue"), "utf8");

    expect(app).toContain(':inert="accessRequired || hasCrashed ? \'\' : undefined"');
    expect(app).toContain(':aria-hidden="accessRequired || hasCrashed');
    expect(main).toContain('@update-status="updateStepStatus"');
    expect(main).toContain(".content-area.view-graph .panel-wrapper.right");
    expect(main).toContain("display: none !important");
    expect(main).toContain('class="mobile-workflow-picker"');
    expect(main).toContain('aria-label="Choose an available workflow step"');
    expect(main).not.toContain("animation: smooth-pulse");
    expect(simulation).toContain("statusLabel");
    expect(simulation).toContain("The assumptions could not be opened");
  });

  it("keeps source-map provenance conservative and shell labels activity-first", () => {
    const step1 = readFileSync(
      resolve("src/components/Step1GraphBuild.vue"),
      "utf8",
    );
    const graphPanel = readFileSync(
      resolve("src/components/GraphPanel.vue"),
      "utf8",
    );
    const main = readFileSync(resolve("src/views/MainView.vue"), "utf8");
    const run = readFileSync(
      resolve("src/views/SimulationRunView.vue"),
      "utf8",
    );

    expect(step1).toContain("they may be incomplete");
    expect(step1).toContain("independently verified facts");
    expect(step1).toContain(
      "Relationship categories proposed from the sources",
    );
    expect(graphPanel).toContain("Graph record · provenance unverified");
    expect(main).toContain('workbench: "Decision steps"');
    expect(run).toContain('workbench: "Run record"');
    expect(run).toContain(':aria-pressed="viewMode === m"');
    expect(run).not.toContain("Routes unfolding");
    expect(run).not.toContain("animation: flash");
    expect(run).not.toContain('workbench: "Scenario paths"');
  });
});

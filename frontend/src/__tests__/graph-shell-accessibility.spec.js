// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { flushPromises, mount, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

const mocks = vi.hoisted(() => ({
  route: { params: { reportId: "report-accessibility" } },
  routerPush: vi.fn(),
  getGraphData: vi.fn(),
  getProject: vi.fn(),
  getReport: vi.fn(),
  getSimulation: vi.fn(),
}));

vi.mock("vue-router", () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.routerPush }),
}));

vi.mock("../api/graph", () => ({
  getGraphData: mocks.getGraphData,
  getProject: mocks.getProject,
}));

vi.mock("../api/report", () => ({
  getReport: mocks.getReport,
}));

vi.mock("../api/simulation", () => ({
  getSimulation: mocks.getSimulation,
}));

import App from "../App.vue";
import GraphPanel from "../components/GraphPanel.vue";
import { accessRequired } from "../composables/useAccessKey.js";
import { hasCrashed } from "../composables/useCrashState.js";
import InteractionView from "../views/InteractionView.vue";
import ReportView from "../views/ReportView.vue";

let widthSpy;
let heightSpy;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.route.params.reportId = "report-accessibility";
  mocks.getReport.mockResolvedValue({
    success: true,
    data: {
      report_id: "report-accessibility",
      simulation_id: "simulation-accessibility",
      status: "completed",
    },
  });
  mocks.getSimulation.mockResolvedValue({
    success: true,
    data: { project_id: null },
  });
  mocks.getProject.mockResolvedValue({ success: true, data: {} });
  mocks.getGraphData.mockResolvedValue({
    success: true,
    data: { nodes: [], edges: [] },
  });
  accessRequired.value = false;
  hasCrashed.value = false;
  document.body.style.overflow = "";
  widthSpy = vi
    .spyOn(HTMLElement.prototype, "clientWidth", "get")
    .mockReturnValue(640);
  heightSpy = vi
    .spyOn(HTMLElement.prototype, "clientHeight", "get")
    .mockReturnValue(480);
});

afterEach(() => {
  widthSpy?.mockRestore();
  heightSpy?.mockRestore();
  hasCrashed.value = false;
  accessRequired.value = false;
  document.body.style.overflow = "";
  document.body.replaceChildren();
});

describe("source-map keyboard and state contracts", () => {
  it("uses source-material language and renders an explicit empty state", async () => {
    const wrapper = mount(GraphPanel, {
      props: {
        graphData: { nodes: [], edges: [] },
        loading: false,
        currentPhase: 1,
        isSimulating: false,
      },
    });
    await nextTick();

    expect(wrapper.get(".panel-label").text()).toBe(
      "Connecting the source material",
    );
    expect(wrapper.text()).not.toContain("Connecting the evidence");
    expect(wrapper.find(".graph-svg-element").exists()).toBe(false);
    expect(wrapper.get(".state-placeholder").text()).toContain(
      "No source-map items were found.",
    );
    expect(wrapper.get(".empty-refresh").text()).toContain(
      "Refresh source map",
    );
    wrapper.unmount();
  });

  it("names graph nodes and supports Enter, trapped focus, Escape, and focus return", async () => {
    const wrapper = mount(GraphPanel, {
      attachTo: document.body,
      props: {
        graphData: {
          nodes: [
            {
              uuid: "node-weekend-rider",
              name: "Weekend rider",
              labels: ["Entity", "Person"],
              attributes: {},
            },
          ],
          edges: [],
        },
        loading: false,
        currentPhase: 2,
        isSimulating: false,
      },
    });
    await nextTick();
    await flushPromises();

    const node = wrapper.get("circle.graph-node");
    expect(node.attributes("role")).toBe("button");
    expect(node.attributes("tabindex")).toBe("0");
    expect(node.attributes("aria-label")).toContain(
      "Weekend rider, Person. Open details.",
    );

    node.element.focus();
    await node.trigger("keydown", { key: "Enter" });
    await nextTick();

    const dialog = wrapper.get('[role="dialog"]');
    const closeButton = wrapper.get(".close-detail-btn");
    expect(dialog.attributes("aria-labelledby")).toBe("graph-detail-title");
    expect(dialog.text()).toContain("Map item: Weekend rider");
    expect(document.activeElement).toBe(closeButton.element);

    await dialog.trigger("keydown", { key: "Tab" });
    expect(document.activeElement).toBe(closeButton.element);

    await dialog.trigger("keydown", { key: "Escape" });
    await nextTick();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(document.activeElement).toBe(node.element);
    wrapper.unmount();
  });
});

describe("report and follow-up shell accessibility contracts", () => {
  it("loads the follow-up shell once and exposes a safe retryable error", async () => {
    mocks.getReport.mockRejectedValueOnce(
      new Error("SECRET internal gateway at 10.0.0.4"),
    );

    const wrapper = shallowMount(InteractionView, {
      global: {
        stubs: {
          GraphPanel: true,
          Step5Interaction: true,
        },
      },
    });
    await flushPromises();

    expect(mocks.getReport).toHaveBeenCalledTimes(1);
    expect(wrapper.get(".interaction-shell-state").attributes("role")).toBe(
      "alert",
    );
    expect(wrapper.text()).toContain(
      "The follow-up workspace could not be opened.",
    );
    expect(wrapper.text()).not.toContain("SECRET");
    expect(wrapper.text()).not.toContain("10.0.0.4");

    mocks.getReport.mockResolvedValueOnce({
      success: true,
      data: {
        report_id: "report-accessibility",
        simulation_id: "simulation-accessibility",
      },
    });
    await wrapper.get(".shell-retry").trigger("click");
    await flushPromises();

    expect(mocks.getReport).toHaveBeenCalledTimes(2);
    expect(wrapper.find(".interaction-shell-state.is-error").exists()).toBe(
      false,
    );
    expect(wrapper.findComponent({ name: "Step5Interaction" }).exists()).toBe(
      true,
    );
    wrapper.unmount();
  });

  it("keeps inactive panels inert and labels shell controls", async () => {
    const interaction = shallowMount(InteractionView, {
      global: {
        stubs: {
          GraphPanel: true,
          Step5Interaction: true,
        },
      },
    });
    await flushPromises();

    expect(interaction.get(".header-left").element.tagName).toBe("BUTTON");
    expect(
      interaction.get(".view-mode-selector").attributes("aria-label"),
    ).toContain("conversation view");
    expect(
      interaction.get(".panel-container.left").attributes("aria-hidden"),
    ).toBe("true");
    expect(
      interaction.get(".panel-container.left").attributes(),
    ).toHaveProperty("inert");

    const interactionGraphButton = interaction
      .findAll(".mode-btn")
      .find((button) => button.text() === "Source map");
    await interactionGraphButton.trigger("click");
    expect(
      interaction.get(".panel-container.left").attributes(),
    ).not.toHaveProperty("inert");
    expect(
      interaction.get(".panel-container.right").attributes("aria-hidden"),
    ).toBe("true");
    expect(
      interaction.get(".panel-container.right").attributes(),
    ).toHaveProperty("inert");
    interaction.unmount();

    const report = shallowMount(ReportView, {
      global: {
        stubs: {
          GraphPanel: true,
          Step4Report: true,
        },
      },
    });
    await flushPromises();

    expect(report.get(".header-left").element.tagName).toBe("BUTTON");
    expect(report.get(".view-mode-selector").attributes("aria-label")).toContain(
      "decision-brief view",
    );
    expect(report.get(".panel-container.left").attributes()).toHaveProperty(
      "inert",
    );

    const reportGraphButton = report
      .findAll(".mode-btn")
      .find((button) => button.text() === "Source map");
    await reportGraphButton.trigger("click");
    expect(report.get(".panel-container.left").attributes()).not.toHaveProperty(
      "inert",
    );
    expect(report.get(".panel-container.right").attributes()).toHaveProperty(
      "inert",
    );
    report.unmount();
  });
});

describe("global recovery and focus contracts", () => {
  it("names the crash alertdialog, traps focus, and restores the trigger", async () => {
    const returnTarget = document.createElement("button");
    returnTarget.textContent = "Return target";
    document.body.appendChild(returnTarget);
    returnTarget.focus();

    const wrapper = mount(App, {
      attachTo: document.body,
      global: {
        stubs: {
          AccessKeyGate: true,
          ProjectLinks: true,
          RouterView: true,
          ToastContainer: true,
        },
      },
    });

    hasCrashed.value = true;
    await nextTick();
    await nextTick();

    const dialog = wrapper.get('[role="alertdialog"]');
    const reload = wrapper.get(".crash-reload");
    expect(dialog.attributes("aria-labelledby")).toBe("crash-title");
    expect(dialog.attributes("aria-describedby")).toBe("crash-description");
    expect(document.activeElement).toBe(reload.element);
    expect(document.body.style.overflow).toBe("hidden");

    document.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "Tab",
        bubbles: true,
        cancelable: true,
      }),
    );
    expect(document.activeElement).toBe(reload.element);

    hasCrashed.value = false;
    await nextTick();
    expect(document.activeElement).toBe(returnTarget);
    expect(document.body.style.overflow).toBe("");
    wrapper.unmount();
    returnTarget.remove();
  });

  it("keeps a geometric focus outline on text controls", () => {
    const tokens = readFileSync(
      resolve("src/assets/design-tokens.css"),
      "utf8",
    );
    expect(tokens).toContain("input:focus-visible");
    expect(tokens).toContain("textarea:focus-visible");
    expect(tokens).toContain("select:focus-visible");
    expect(tokens).toContain("outline: 3px solid var(--signal)");
    expect(tokens).not.toMatch(
      /input:focus,[\s\S]*?select:focus\s*\{[\s\S]*?outline:\s*none/,
    );
  });

  it("keeps the report shells viewport-bound and rerenders a revealed map", () => {
    const tokens = readFileSync(
      resolve("src/assets/design-tokens.css"),
      "utf8",
    );
    const graphPanel = readFileSync(
      resolve("src/components/GraphPanel.vue"),
      "utf8",
    );
    const reportView = readFileSync(
      resolve("src/views/ReportView.vue"),
      "utf8",
    );

    expect(tokens).toMatch(
      /\.bauhaus-view-root,\s*\.app-view-root\s*\{[\s\S]*?height:\s*100dvh\s*!important/,
    );
    expect(graphPanel).toContain("new ResizeObserver");
    expect(graphPanel).toContain("graphResizeObserver.observe(graphContainer.value)");
    expect(reportView).toMatch(
      /\.mode-btn\.is-active\s*\{\s*background:\s*var\(--signal\)\s*!important/,
    );
    expect(reportView).not.toContain("border-radius: 6px !important");
  });
});

// @vitest-environment jsdom

import { flushPromises, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  route: {
    params: { reportId: "report-old", simulationId: "simulation-old" },
    query: {},
  },
  routerPush: vi.fn(),
  getGraphData: vi.fn(),
  getProject: vi.fn(),
  getReport: vi.fn(),
  getSimulation: vi.fn(),
  closeSimulationEnv: vi.fn(),
  getEnvStatus: vi.fn(),
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
  closeSimulationEnv: mocks.closeSimulationEnv,
  getEnvStatus: mocks.getEnvStatus,
  getSimulation: mocks.getSimulation,
}));

import InteractionView from "../views/InteractionView.vue";
import ReportView from "../views/ReportView.vue";
import SimulationRunView from "../views/SimulationRunView.vue";
import SimulationView from "../views/SimulationView.vue";

const wrappers = [];
const mountView = (component) => {
  const wrapper = shallowMount(component, {
    global: {
      stubs: {
        ForkRunControl: true,
        GraphPanel: true,
        Step2EnvSetup: true,
        Step3Simulation: true,
        Step4Report: true,
        Step5Interaction: true,
        TruthRail: true,
      },
    },
  });
  wrappers.push(wrapper);
  return wrapper;
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.route.params.reportId = "report-old";
  mocks.route.params.simulationId = "simulation-old";
  mocks.route.query = {};
  mocks.getSimulation.mockResolvedValue({
    success: true,
    data: {
      simulation_id: "simulation-old",
      project_id: "project-1",
      graph_id: "graph-recorded",
    },
  });
  mocks.getReport.mockResolvedValue({
    success: true,
    data: {
      report_id: "report-old",
      simulation_id: "simulation-old",
      graph_id: "graph-recorded",
      status: "completed",
    },
  });
  mocks.getProject.mockResolvedValue({
    success: true,
    data: {
      project_id: "project-1",
      graph_id: "graph-current",
    },
  });
  mocks.getGraphData.mockResolvedValue({ success: true, data: {} });
  mocks.getEnvStatus.mockResolvedValue({
    success: true,
    data: { env_alive: false },
  });
});

afterEach(() => {
  while (wrappers.length) wrappers.pop().unmount();
});

describe("historical source-map identity", () => {
  it.each([
    ["prepared scenario", SimulationView],
    ["scenario run", SimulationRunView],
    ["decision brief", ReportView],
    ["follow-up workspace", InteractionView],
  ])(
    "fails visibly for a %s when its recorded graph is no longer current",
    async (_label, component) => {
      const wrapper = mountView(component);
      await flushPromises();

      expect(wrapper.text()).toContain(
        "The source map recorded for this run is no longer the project's current source map.",
      );
      expect(mocks.getGraphData).not.toHaveBeenCalled();
    },
  );

  it.each([
    ["prepared scenario", SimulationView, false],
    ["scenario run", SimulationRunView, false],
    ["decision brief", ReportView, true],
    ["follow-up workspace", InteractionView, true],
  ])(
    "loads the %s with the recorded identity, never a later project graph",
    async (_label, component, usesReport) => {
      mocks.getProject.mockResolvedValue({
        success: true,
        data: { project_id: "project-1", graph_id: "graph-recorded" },
      });
      if (!usesReport) {
        mocks.getReport.mockRejectedValue(
          new Error("report lookup must not be needed for a simulation view"),
        );
      }

      mountView(component);
      await flushPromises();

      expect(mocks.getGraphData).toHaveBeenCalledWith(
        "project-1",
        "graph-recorded",
      );
      expect(mocks.getGraphData).not.toHaveBeenCalledWith(
        "project-1",
        "graph-current",
      );
    },
  );

  it.each([
    ["decision brief", ReportView],
    ["follow-up workspace", InteractionView],
  ])(
    "fails the %s visibly when report and simulation graph identities disagree",
    async (_label, component) => {
      mocks.getProject.mockResolvedValue({
        success: true,
        data: { project_id: "project-1", graph_id: "graph-recorded" },
      });
      mocks.getReport.mockResolvedValue({
        success: true,
        data: {
          report_id: "report-old",
          simulation_id: "simulation-old",
          graph_id: "graph-report-other",
          status: "completed",
        },
      });

      const wrapper = mountView(component);
      await flushPromises();

      expect(wrapper.text()).toContain(
        "The saved report and run do not reference the same source map.",
      );
      expect(mocks.getGraphData).not.toHaveBeenCalled();
    },
  );

  it.each([
    ["decision brief", ReportView],
    ["follow-up workspace", InteractionView],
  ])(
    "fails the %s instead of inferring a missing report graph identity",
    async (_label, component) => {
      mocks.getProject.mockResolvedValue({
        success: true,
        data: { project_id: "project-1", graph_id: "graph-recorded" },
      });
      mocks.getReport.mockResolvedValue({
        success: true,
        data: {
          report_id: "report-old",
          simulation_id: "simulation-old",
          status: "completed",
        },
      });

      const wrapper = mountView(component);
      await flushPromises();

      expect(wrapper.text()).toContain(
        "The saved report is missing its recorded source-map identity.",
      );
      expect(mocks.getGraphData).not.toHaveBeenCalled();
    },
  );

  it.each([
    ["prepared scenario", SimulationView],
    ["scenario run", SimulationRunView],
    ["decision brief", ReportView],
    ["follow-up workspace", InteractionView],
  ])(
    "surfaces a %s refresh race when the recorded graph stops being current",
    async (_label, component) => {
      mocks.getProject.mockResolvedValue({
        success: true,
        data: { project_id: "project-1", graph_id: "graph-recorded" },
      });
      const wrapper = mountView(component);
      await flushPromises();
      mocks.getGraphData.mockResolvedValueOnce({
        success: false,
        error: "graph_not_available_for_project",
      });

      if (!wrapper.findComponent({ name: "GraphPanel" }).exists()) {
        const sourceMapButton = wrapper
          .findAll("button")
          .find((button) => button.text() === "Source map");
        await sourceMapButton.trigger("click");
      }
      wrapper.findComponent({ name: "GraphPanel" }).vm.$emit("refresh");
      await flushPromises();

      expect(wrapper.text()).toContain(
        "The source map recorded for this run is no longer the project's current source map.",
      );
    },
  );
});

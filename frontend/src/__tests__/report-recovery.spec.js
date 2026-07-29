import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { flushPromises, mount, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  route: { params: { reportId: "report-test" } },
  exportReportPDF: vi.fn(),
  getAgentLog: vi.fn(),
  getReport: vi.fn(),
  getReportEvidence: vi.fn(),
  getReportStatus: vi.fn(),
  getSimulation: vi.fn(),
  getGraphData: vi.fn(),
  getProject: vi.fn(),
}));

vi.mock("vue-router", () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.routerPush }),
}));

vi.mock("../api/report", () => ({
  exportReportPDF: mocks.exportReportPDF,
  getAgentLog: mocks.getAgentLog,
  getReport: mocks.getReport,
  getReportEvidence: mocks.getReportEvidence,
  getReportStatus: mocks.getReportStatus,
  normalizeAgentLogEntry: (entry) => entry,
  normalizeLogPage: (response) => ({
    logs: response?.data?.logs || [],
    nextFromLine: response?.data?.logs?.length || 0,
  }),
  normalizeReportEvidence: () => [],
  outlineSectionTitles: (outline) =>
    (outline?.sections || [])
      .map((section) =>
        typeof section === "string" ? section : section?.title,
      )
      .filter(Boolean),
}));

vi.mock("../api/simulation", () => ({
  getSimulation: mocks.getSimulation,
}));

vi.mock("../api/graph", () => ({
  getGraphData: mocks.getGraphData,
  getProject: mocks.getProject,
}));

import Step4Report from "../components/Step4Report.vue";
import ReportView from "../views/ReportView.vue";

const completedReport = {
  success: true,
  data: {
    report_id: "report-test",
    simulation_id: "sim-test",
    status: "completed",
    simulation_requirement: "Should weekend service change?",
    outline: {
      title: "Scenario findings",
      summary: "A bounded synthetic summary.",
      sections: [
        {
          title: "Possible path",
          content: "One generated path may change travel behavior.",
        },
      ],
    },
    markdown_content:
      "# Scenario findings\n\nOne generated path may change travel behavior.",
  },
};

let anchorClick;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.route.params.reportId = "report-test";
  mocks.getReport.mockResolvedValue(completedReport);
  mocks.getAgentLog.mockResolvedValue({ success: true, data: { logs: [] } });
  mocks.getReportEvidence.mockResolvedValue({
    success: true,
    data: { evidence: [] },
  });
  mocks.getReportStatus.mockResolvedValue({
    success: true,
    data: { status: "completed", progress: 100 },
  });
  mocks.getSimulation.mockResolvedValue({
    success: true,
    data: { project_id: null },
  });
  mocks.getGraphData.mockResolvedValue({ success: true, data: {} });
  mocks.getProject.mockResolvedValue({ success: true, data: {} });
  mocks.exportReportPDF.mockResolvedValue(new Blob(["pdf"]));

  Object.defineProperty(window.URL, "createObjectURL", {
    configurable: true,
    value: vi.fn(() => "blob:report-export"),
  });
  Object.defineProperty(window.URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
  anchorClick = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => {});
});

afterEach(() => {
  anchorClick?.mockRestore();
});

describe("Step 4 terminal recovery", () => {
  it("renders a saved failed report as a terminal alert and never polls", async () => {
    mocks.getReport.mockResolvedValue({
      success: true,
      data: {
        report_id: "report-failed",
        simulation_id: "sim-failed",
        status: "failed",
        error: "SECRET traceback /srv/private/report.py",
      },
    });

    const wrapper = mount(Step4Report, {
      props: { reportId: "report-failed", simulationId: "sim-failed" },
    });
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain(
      "This report was not completed.",
    );
    expect(wrapper.text()).toContain("Retry loading report");
    expect(wrapper.text()).toContain("Return home");
    expect(wrapper.text()).not.toContain("SECRET");
    expect(wrapper.find(".generation-strip").exists()).toBe(false);
    expect(mocks.getReportStatus).not.toHaveBeenCalled();

    await wrapper
      .get("button.action-button.is-primary")
      .trigger("click");
    await flushPromises();
    expect(mocks.getReport).toHaveBeenCalledTimes(2);

    const homeButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Return home"));
    await homeButton.trigger("click");
    expect(mocks.routerPush).toHaveBeenCalledWith({ name: "Home" });
    wrapper.unmount();
  });

  it("sanitizes report-load failures and stops before status polling", async () => {
    mocks.getReport.mockRejectedValue(
      new Error("postgres://admin:secret@private-host/report"),
    );

    const wrapper = mount(Step4Report, {
      props: { reportId: "missing-report", simulationId: "sim-test" },
    });
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain(
      "This report could not be opened.",
    );
    expect(wrapper.text()).not.toContain("postgres");
    expect(wrapper.text()).not.toContain("private-host");
    expect(mocks.getReportStatus).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});

describe("Step 4 visible export feedback", () => {
  it("shows separate safe errors for PDF, Markdown, and plain text", async () => {
    const wrapper = mount(Step4Report, {
      props: { reportId: "report-test", simulationId: "sim-test" },
    });
    await flushPromises();

    mocks.exportReportPDF.mockRejectedValueOnce(
      new Error("SECRET upstream renderer stack"),
    );
    const pdfButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Download report PDF"));
    await pdfButton.trigger("click");
    await flushPromises();
    expect(wrapper.get("#pdf-export-error").text()).toContain(
      "The PDF could not be downloaded.",
    );

    window.URL.createObjectURL.mockImplementationOnce(() => {
      throw new Error("SECRET markdown filesystem path");
    });
    const markdownButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Download Markdown"));
    await markdownButton.trigger("click");
    await flushPromises();
    expect(wrapper.get("#markdown-export-error").text()).toContain(
      "The Markdown file could not be created.",
    );

    window.URL.createObjectURL.mockImplementationOnce(() => {
      throw new Error("SECRET text filesystem path");
    });
    const txtButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Download plain text"));
    await txtButton.trigger("click");
    await flushPromises();
    expect(wrapper.get("#txt-export-error").text()).toContain(
      "The plain-text file could not be created.",
    );

    expect(wrapper.text()).not.toContain("SECRET");
    wrapper.unmount();
  });

  it("does not render raw diagnostic payloads in the secondary record", async () => {
    mocks.getAgentLog.mockResolvedValue({
      success: true,
      data: {
        logs: [
          {
            action: "tool_result",
            timestamp: "2026-07-29T00:00:00Z",
            tool_name: "private_search_backend",
            content: "SECRET raw model output",
            params: { token: "SECRET_TOKEN" },
          },
        ],
      },
    });

    const wrapper = mount(Step4Report, {
      props: { reportId: "report-test", simulationId: "sim-test" },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("A configured source tool returned a result.");
    expect(wrapper.text()).toContain(
      "Raw runtime diagnostics are intentionally omitted",
    );
    expect(wrapper.text()).not.toContain("SECRET");
    expect(wrapper.text()).not.toContain("private_search_backend");
    wrapper.unmount();
  });
});

describe("Report shell and route recovery contracts", () => {
  it("renders a visible sanitized shell error with retry and home actions", async () => {
    mocks.getReport.mockRejectedValue(
      new Error("SECRET gateway diagnostic from 10.0.0.7"),
    );

    const wrapper = shallowMount(ReportView, {
      global: {
        stubs: {
          GraphPanel: true,
          Step4Report: true,
        },
      },
    });
    await flushPromises();

    expect(wrapper.get(".report-shell-error").attributes("role")).toBe("alert");
    expect(wrapper.text()).toContain("This report could not be opened.");
    expect(wrapper.text()).toContain("NEEDS ATTENTION");
    expect(wrapper.text()).not.toContain("SECRET");
    expect(wrapper.text()).not.toContain("10.0.0.7");
    expect(wrapper.findComponent(Step4Report).exists()).toBe(false);
    wrapper.unmount();
  });

  it("maps a saved failed report to Needs attention", async () => {
    mocks.getReport.mockResolvedValue({
      success: true,
      data: {
        report_id: "report-failed",
        simulation_id: "sim-failed",
        status: "failed",
        error: "SECRET",
      },
    });

    const wrapper = shallowMount(ReportView, {
      global: {
        stubs: {
          GraphPanel: true,
          Step4Report: true,
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("NEEDS ATTENTION");
    expect(wrapper.text()).not.toContain("SECRET");
    wrapper.unmount();
  });

  it("keeps the parameter guard and adds a final catch-all recovery route", () => {
    const routerSource = readFileSync(resolve("src/router/index.js"), "utf8");
    const notFound = readFileSync(
      resolve("src/views/NotFoundView.vue"),
      "utf8",
    );

    expect(routerSource).toContain("const requiredParamsByRoute");
    expect(routerSource).toContain("value === 'undefined'");
    expect(routerSource).toContain("path: '/:pathMatch(.*)*'");
    expect(routerSource.indexOf("path: '/:pathMatch(.*)*'")).toBeGreaterThan(
      routerSource.indexOf("path: '/interaction/:reportId'"),
    );
    expect(notFound).toContain('aria-labelledby="not-found-heading"');
    expect(notFound).toContain("This path does not exist.");
    expect(notFound).toContain("Return to the start");
    expect(notFound).not.toContain("route.fullPath");
  });
});

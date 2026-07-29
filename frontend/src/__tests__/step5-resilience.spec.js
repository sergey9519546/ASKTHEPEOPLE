import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  chatWithReport: vi.fn(),
  getAgentLog: vi.fn(),
  getReport: vi.fn(),
  askSyntheticProfiles: vi.fn(),
  exportGeneratedResponsesCSV: vi.fn(),
  getRunStatusDetail: vi.fn(),
  getSimulationOpinions: vi.fn(),
  getSimulationProfilesRealtime: vi.fn(),
  stopSimulation: vi.fn(),
}));

vi.mock("../api/report", () => ({
  chatWithReport: mocks.chatWithReport,
  getAgentLog: mocks.getAgentLog,
  getReport: mocks.getReport,
  normalizeAgentLogEntry: (entry) => entry,
  normalizeLogPage: (response) => ({
    logs: response?.data?.logs || [],
  }),
}));

vi.mock("../api/simulation", () => ({
  askSyntheticProfiles: mocks.askSyntheticProfiles,
  exportGeneratedResponsesCSV: mocks.exportGeneratedResponsesCSV,
  getRunStatusDetail: mocks.getRunStatusDetail,
  getSimulationOpinions: mocks.getSimulationOpinions,
  getSimulationProfilesRealtime: mocks.getSimulationProfilesRealtime,
  stopSimulation: mocks.stopSimulation,
}));

import OpinionMap from "../components/OpinionMap.vue";
import Step5Interaction from "../components/Step5Interaction.vue";

const mountedWrappers = [];

const track = (wrapper) => {
  mountedWrappers.push(wrapper);
  return wrapper;
};

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
};

const successfulReport = {
  success: true,
  data: {
    outline: {
      title: "Weekend transit decision brief",
      summary: "A bounded synthetic report.",
      sections: [],
    },
  },
};

const successfulLogs = {
  success: true,
  data: { logs: [] },
};

const successfulProfiles = {
  success: true,
  data: {
    profiles: [
      {
        id: "profile-1",
        username: "Night-shift parent",
        profession: "Hospital technician",
      },
    ],
  },
};

const successfulRunStatus = {
  success: true,
  data: {
    runner_status: "completed",
    current_round: 8,
    total_rounds: 8,
    total_actions_count: 17,
    recent_actions: [],
  },
};

const mountStep5 = () =>
  track(
    mount(Step5Interaction, {
      props: {
        reportId: "report-test",
        simulationId: "simulation-test",
        systemLogs: [],
      },
      global: {
        stubs: {
          OpinionMap: true,
        },
      },
    }),
  );

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getReport.mockResolvedValue(successfulReport);
  mocks.getAgentLog.mockResolvedValue(successfulLogs);
  mocks.getSimulationProfilesRealtime.mockResolvedValue(successfulProfiles);
  mocks.getRunStatusDetail.mockResolvedValue(successfulRunStatus);
  mocks.getSimulationOpinions.mockResolvedValue({
    success: true,
    data: { opinions: [] },
  });
});

afterEach(() => {
  while (mountedWrappers.length > 0) {
    mountedWrappers.pop().unmount();
  }
});

describe("Step 5 workspace resilience", () => {
  it("keeps unresolved records in an explicit loading state instead of showing empty content", async () => {
    const reportRequest = deferred();
    const logRequest = deferred();
    const profileRequest = deferred();
    mocks.getReport.mockReturnValue(reportRequest.promise);
    mocks.getAgentLog.mockReturnValue(logRequest.promise);
    mocks.getSimulationProfilesRealtime.mockReturnValue(profileRequest.promise);

    const wrapper = mountStep5();

    expect(wrapper.get('[data-testid="workspace-loading"]').text()).toContain(
      "Connecting the report, profile briefs, and run status.",
    );
    expect(wrapper.find("main#followup-main").exists()).toBe(false);
    expect(wrapper.text()).not.toContain(
      "No generated profiles are available for this run.",
    );

    reportRequest.resolve(successfulReport);
    logRequest.resolve(successfulLogs);
    profileRequest.resolve(successfulProfiles);
    await flushPromises();

    expect(wrapper.find('[data-testid="workspace-loading"]').exists()).toBe(
      false,
    );
    expect(wrapper.get("main#followup-main").exists()).toBe(true);
  });

  it("marks a rejected profile request as disconnected rather than as an empty set", async () => {
    mocks.getSimulationProfilesRealtime.mockRejectedValue(
      new Error("private upstream detail"),
    );
    const wrapper = mountStep5();
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-load-warning"]').text()).toContain(
      "Fictional profile briefs are disconnected.",
    );

    const profileMode = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Ask a fictional profile"));
    await profileMode.trigger("click");

    expect(wrapper.get('[data-testid="profile-load-error"]').text()).toContain(
      "This is a connection problem, not an empty profile set.",
    );
    expect(wrapper.text()).not.toContain(
      "No generated profiles are available for this run.",
    );
    expect(wrapper.text()).not.toContain("private upstream detail");
  });

  it("surfaces a live-status failure and reconnects without hiding available tools", async () => {
    mocks.getRunStatusDetail.mockRejectedValueOnce(
      new Error("temporary connection failure"),
    );
    const wrapper = mountStep5();
    await flushPromises();

    expect(wrapper.get("main#followup-main").exists()).toBe(true);
    expect(wrapper.get('[data-testid="run-status-disconnected"]').text()).toContain(
      "Live run updates disconnected",
    );

    mocks.getRunStatusDetail.mockResolvedValueOnce(successfulRunStatus);
    await wrapper
      .get('[data-testid="run-status-disconnected"] button')
      .trigger("click");
    await flushPromises();

    expect(
      wrapper.find('[data-testid="run-status-disconnected"]').exists(),
    ).toBe(false);
    expect(mocks.getRunStatusDetail).toHaveBeenCalledTimes(2);
  });

  it("offers a full retry when every initial context request fails", async () => {
    mocks.getReport.mockRejectedValueOnce(new Error("report unavailable"));
    mocks.getAgentLog.mockRejectedValueOnce(new Error("logs unavailable"));
    mocks.getSimulationProfilesRealtime.mockRejectedValueOnce(
      new Error("profiles unavailable"),
    );
    mocks.getRunStatusDetail.mockRejectedValueOnce(
      new Error("status unavailable"),
    );

    const wrapper = mountStep5();
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-load-error"]').text()).toContain(
      "The run context could not be opened.",
    );
    expect(wrapper.find("main#followup-main").exists()).toBe(false);

    mocks.getReport.mockResolvedValueOnce(successfulReport);
    mocks.getAgentLog.mockResolvedValueOnce(successfulLogs);
    mocks.getSimulationProfilesRealtime.mockResolvedValueOnce(
      successfulProfiles,
    );
    mocks.getRunStatusDetail.mockResolvedValueOnce(successfulRunStatus);

    await wrapper
      .get('[data-testid="workspace-load-error"] button')
      .trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-testid="workspace-load-error"]').exists()).toBe(
      false,
    );
    expect(wrapper.get("main#followup-main").exists()).toBe(true);
  });
});

describe("flat generated-interaction route", () => {
  it("renders plain-language channel routes with the truth boundary and closed technical details", async () => {
    mocks.getSimulationOpinions.mockResolvedValueOnce({
      success: true,
      data: {
        opinions: [
          {
            agent_id: 4,
            agent_name: "Night-shift parent",
            platform: "reddit",
            timestamp: "2026-07-28T18:20:00Z",
            text_snippet: "A missed transfer would make the new schedule difficult.",
          },
          {
            agent_id: 8,
            agent_name: "Market district owner",
            platform: "twitter",
            timestamp: "2026-07-28T18:22:00Z",
            text_snippet: "Later service could change closing-time foot traffic.",
          },
        ],
      },
    });

    const wrapper = track(
      mount(OpinionMap, {
        props: { simulationId: "simulation-test" },
      }),
    );
    await flushPromises();

    expect(wrapper.text()).toContain("What happened inside this run");
    expect(wrapper.text()).toContain("0 human respondents");
    expect(wrapper.text()).toContain("Not public opinion · not a forecast");
    expect(wrapper.text()).toContain("Topic community");
    expect(wrapper.text()).toContain("Short-post channel");
    expect(wrapper.text()).toContain("Night-shift parent");
    expect(wrapper.find(".route-board").exists()).toBe(true);
    expect(wrapper.get(".technical-record").attributes("open")).toBeUndefined();
  });

  it("keeps the last loaded route visible when refresh polling disconnects", async () => {
    mocks.getSimulationOpinions.mockResolvedValueOnce({
      success: true,
      data: {
        opinions: [
          {
            agent_id: 4,
            agent_name: "Night-shift parent",
            platform: "reddit",
            timestamp: "2026-07-28T18:20:00Z",
            text_snippet: "A generated route record.",
          },
        ],
      },
    });
    const wrapper = track(
      mount(OpinionMap, {
        props: { simulationId: "simulation-test" },
      }),
    );
    await flushPromises();

    mocks.getSimulationOpinions.mockRejectedValueOnce(
      new Error("private connection detail"),
    );
    const refreshButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Refresh generated records"));
    await refreshButton.trigger("click");
    await flushPromises();

    expect(
      wrapper.get('[data-testid="interaction-map-disconnected"]').text(),
    ).toContain("The last loaded route remains below.");
    expect(wrapper.text()).toContain("Night-shift parent");
    expect(wrapper.text()).not.toContain("private connection detail");
  });
});

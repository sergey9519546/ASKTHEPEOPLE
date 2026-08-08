import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getSimulationOpinions: vi.fn(),
}));

vi.mock("../api/simulation", () => ({
  getSimulationOpinions: mocks.getSimulationOpinions,
}));

import OpinionMap from "../components/OpinionMap.vue";

const wrappers = [];

const deferred = () => {
  let resolvePromise;
  let rejectPromise;
  const promise = new Promise((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return { promise, reject: rejectPromise, resolve: resolvePromise };
};

const mountMap = () => {
  const wrapper = mount(OpinionMap, {
    props: { simulationId: "simulation-test" },
  });
  wrappers.push(wrapper);
  return wrapper;
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
});

describe("OpinionMap chronological run record", () => {
  it("keeps loading distinct from a true empty record", () => {
    mocks.getSimulationOpinions.mockReturnValue(deferred().promise);
    const wrapper = mountMap();

    expect(wrapper.get('[data-testid="interaction-run-record-loading"]')).toBeTruthy();
    expect(wrapper.find('[data-testid="interaction-run-record-empty"]').exists()).toBe(false);
  });

  it("shows a bounded error without exposing private upstream detail", async () => {
    mocks.getSimulationOpinions.mockRejectedValueOnce(
      new Error("private provider trace"),
    );
    const wrapper = mountMap();
    await flushPromises();

    const error = wrapper.get('[data-testid="interaction-run-record-error"]');
    expect(error.text()).toContain("The saved run record could not be opened.");
    expect(error.text()).not.toContain("private provider trace");
  });

  it("renders a true empty state only after a successful request", async () => {
    mocks.getSimulationOpinions.mockResolvedValueOnce({
      success: true,
      data: { opinions: [] },
    });
    const wrapper = mountMap();
    await flushPromises();

    expect(wrapper.get('[data-testid="interaction-run-record-empty"]').text()).toContain(
      "No generated activity records were saved.",
    );
    expect(wrapper.find('[data-testid="interaction-run-record-error"]').exists()).toBe(false);
  });

  it("keeps every record in chronological order and inspects the latest record", async () => {
    mocks.getSimulationOpinions.mockResolvedValueOnce({
      success: true,
      data: {
        opinions: [
          {
            agent_id: 4,
            agent_name: "Night-shift parent",
            platform: "reddit",
            timestamp: "2026-07-28T18:22:00Z",
            text_snippet: "The later saved response.",
          },
          {
            agent_id: 4,
            agent_name: "Night-shift parent",
            platform: "reddit",
            timestamp: "2026-07-28T18:20:00Z",
            text_snippet: "The first saved response.",
          },
          {
            agent_id: 8,
            agent_name: "Market district owner",
            platform: "twitter",
            timestamp: "2026-07-28T18:21:00Z",
            text_snippet: "The middle saved response.",
          },
        ],
      },
    });
    const wrapper = mountMap();
    await flushPromises();

    const truthBoundary = wrapper.get(
      '[data-testid="interaction-truth-boundary"]',
    );
    expect(truthBoundary.text()).toContain("Actions + answers: synthetic");
    expect(truthBoundary.text()).toContain("Human respondents: 0");
    expect(truthBoundary.text()).toContain("Not a forecast");
    expect(truthBoundary.text()).toContain("Human validation: outside this run");

    const list = wrapper.get('[data-testid="interaction-run-record-list"]');
    expect(list.element.tagName).toBe("OL");
    expect(list.findAll('li[data-origin="synthetic-generated"]')).toHaveLength(3);
    expect(list.text().indexOf("The first saved response.")).toBeLessThan(
      list.text().indexOf("The middle saved response."),
    );
    expect(list.text().indexOf("The middle saved response.")).toBeLessThan(
      list.text().indexOf("The later saved response."),
    );

    const inspector = wrapper.get('[data-testid="latest-record-inspector"]');
    expect(inspector.text()).toContain("Latest saved record");
    expect(inspector.text()).toContain("The later saved response.");
    expect(inspector.text()).toContain(
      "This is generated activity, not a human statement.",
    );
  });

  it("contains no fake consensus, automatic polling, or perpetual animation", () => {
    const source = readFileSync(
      resolve("src/components/OpinionMap.vue"),
      "utf8",
    );

    expect(source).not.toMatch(/consensus|perspective alignment|popularity/i);
    expect(source).not.toContain("setInterval");
    expect(source).not.toMatch(/@keyframes\s+route-pulse/i);
    expect(source).not.toMatch(/animation:\s*[^;]*infinite/i);
  });
});

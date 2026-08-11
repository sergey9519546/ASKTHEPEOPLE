import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
}));

vi.mock("../api/index.js", () => ({
  default: mocks.request,
}));

import * as graphApi from "../api/graph.js";

const graphConsumerFiles = [
  "src/views/MainView.vue",
  "src/views/InteractionView.vue",
  "src/views/ReportView.vue",
  "src/views/SimulationView.vue",
  "src/views/SimulationRunView.vue",
];

beforeEach(() => {
  vi.clearAllMocks();
  mocks.request.mockResolvedValue({ success: true, data: {} });
});

describe("server-owned graph API identity", () => {
  it("reads a graph only with its canonical project identifier", async () => {
    await graphApi.getGraphData("project-1", "graph-1");

    expect(mocks.request).toHaveBeenCalledWith({
      url: "/api/graph/data/graph-1",
      method: "get",
      params: { project_id: "project-1" },
    });
  });

  it("preserves the stable association code from a real Axios 404", async () => {
    mocks.request.mockRejectedValueOnce({
      response: {
        status: 404,
        data: { success: false, error: "graph_not_available_for_project" },
      },
    });

    await expect(graphApi.getGraphData("project-1", "graph-1")).resolves.toEqual({
      success: false,
      error: "graph_not_available_for_project",
    });
  });

  it("refuses provider-graph-only reads at the client boundary", () => {
    expect(() => graphApi.getGraphData("graph-1")).toThrow(
      "projectId and graphId are required",
    );
    expect(mocks.request).not.toHaveBeenCalled();
  });

  it("keeps the delete helper ownership-bound for any future consumer", async () => {
    expect(typeof graphApi.deleteGraph).toBe("function");

    await graphApi.deleteGraph("project-1", "graph-1");

    expect(mocks.request).toHaveBeenCalledWith({
      url: "/api/graph/delete/graph-1",
      method: "delete",
      params: { project_id: "project-1" },
    });
  });

  it("passes both project and graph identity from every graph-data consumer", () => {
    for (const file of graphConsumerFiles) {
      const source = readFileSync(resolve(file), "utf8");
      const callLines = source
        .split(/\r?\n/)
        .filter((line) => line.includes("getGraphData("));

      expect(
        callLines.length,
        `${file} should read graph data`,
      ).toBeGreaterThan(0);
      for (const line of callLines) {
        expect(line, `${file} must not call by provider graph ID alone`).toMatch(
          /getGraphData\(\s*[^,]*project[^,]*,\s*[^)]+\)/i,
        );
      }
    }
  });
});

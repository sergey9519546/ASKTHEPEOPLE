import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
}));

vi.mock("../api/index.js", () => ({
  default: mocks.request,
}));

import { fetchSourceUrls } from "../api/sources.js";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.request.mockResolvedValue({ success: true, files: [] });
});

describe("authenticated source ingestion", () => {
  it("uses the shared authenticated API client", async () => {
    await fetchSourceUrls(["https://example.invalid/fixture"]);

    expect(mocks.request).toHaveBeenCalledWith({
      url: "/api/sources/fetch",
      method: "post",
      data: { urls: ["https://example.invalid/fixture"] },
    });
  });

  it("keeps Home away from unauthenticated raw fetch", () => {
    const source = readFileSync(resolve("src/views/Home.vue"), "utf8");

    expect(source).toContain("fetchSourceUrls");
    expect(source).not.toMatch(/fetch\(["']\/api\/sources\/fetch/);
  });
});

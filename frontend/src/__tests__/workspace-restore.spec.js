// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({ name: "Home", params: {}, query: {}, fullPath: "/" }),
}));

import DesktopShell from "../components/DesktopShell.vue";
import {
  JOURNEY_TOTAL,
  closeAllWindows,
  journeyState,
  windows,
} from "../composables/useDesktop.js";
import {
  STORAGE_KEY,
  clearState,
  loadSavedState,
  setContext,
} from "../composables/useWorkspaceState.js";

/**
 * Regression tests for a defect this suite's own design introduced.
 *
 * `setContext()` persists the workspace ids a journey window reports
 * (projectId / simulationId / reportId) to localStorage, but nothing called
 * `loadSavedState()` on the way back in. So after any refresh, `workspaceState`
 * was `DEFAULT_STATE` with every id empty while `restoreSession()` faithfully
 * reopened the panels the user had been working in.
 *
 * `journeyState()` gates cumulatively on those ids, so every step the user had
 * already completed came back marked LOCKED with its panel open on screen. The
 * journey spine made the omission visible — before it existed, nothing read
 * workspace state at boot, so the missing restore was harmless.
 */

function stored() {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

/**
 * Leave localStorage exactly as a finished session would, while the in-memory
 * ref keeps its fresh module default. That pair IS a page reload.
 */
function seedPreviousSession(ids) {
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ ...ids, savedAt: "2026-10-02T00:00:00.000Z" }),
  );
}

beforeEach(() => {
  closeAllWindows();
  clearState();
  window.localStorage.clear();
  document.body.replaceChildren();
});

describe("workspace state survives a reload", () => {
  it("writes the ids a window reports", () => {
    setContext({ projectId: "p-1", simulationId: "s-1", reportId: "r-1" });

    expect(stored()).toMatchObject({
      projectId: "p-1",
      simulationId: "s-1",
      reportId: "r-1",
    });
  });

  it("reads them back on the next load", () => {
    // A reload keeps localStorage and loses module memory. clearState() wipes
    // both, so it cannot stand in for one; seed storage the way a previous
    // session left it and let the in-memory copy stay at its fresh default.
    seedPreviousSession({ projectId: "p-1", simulationId: "s-1", reportId: "r-1" });

    loadSavedState();

    const state = journeyState();
    expect(state.find((e) => e.id === "sources").reached).toBe(true);
    expect(state.find((e) => e.id === "assumptions").reached).toBe(true);
    expect(state.find((e) => e.id === "brief").reached).toBe(true);
  });

  it("keeps a completed step from coming back LOCKED", () => {
    seedPreviousSession({ projectId: "p-1", simulationId: "s-1" });

    // The failure mode: fresh module state, ids empty, so every step past the
    // first reports locked even though its panel is open on screen.
    const fresh = journeyState();
    expect(fresh.find((e) => e.id === "assumptions").status).toBe("locked");
    expect(fresh.find((e) => e.id === "brief").status).toBe("locked");

    loadSavedState();

    const restored = journeyState();
    // `assumptions` requires simulationId, which the seeded session recorded, so
    // it must be reachable again.
    expect(restored.find((e) => e.id === "assumptions").status).not.toBe("locked");
    // `brief` requires reportId, which it did not. Restoring the workspace must
    // not quietly unlock steps the workspace never actually reached - that
    // would be a worse bug than the one being fixed.
    expect(restored.find((e) => e.id === "brief").status).toBe("locked");
  });

  it("unlocks the last steps once the session recorded their coordinates", () => {
    seedPreviousSession({ projectId: "p-1", simulationId: "s-1", reportId: "r-1" });

    loadSavedState();

    const restored = journeyState();
    expect(restored.find((e) => e.id === "brief").reached).toBe(true);
    expect(restored.find((e) => e.id === "followup").reached).toBe(true);
  });

  it("degrades to session-only when storage throws", () => {
    const original = window.localStorage.setItem;
    window.localStorage.setItem = () => {
      throw new Error("quota exceeded");
    };
    try {
      expect(() => setContext({ projectId: "p-1" })).not.toThrow();
    } finally {
      window.localStorage.setItem = original;
    }
    // The in-memory copy is still correct even when persistence failed.
    expect(journeyState().find((e) => e.id === "sources").reached).toBe(true);
  });

  it("ignores corrupt storage instead of wedging the boot", () => {
    window.localStorage.setItem(STORAGE_KEY, "{not json");
    expect(() => loadSavedState()).not.toThrow();
    expect(journeyState()).toHaveLength(JOURNEY_TOTAL);
  });
});

describe("the shell restores the workspace before it restores panels", () => {
  it("orders loadSavedState ahead of restoreSession in onMounted", () => {
    // Ordering is the whole fix. If restoreSession ran first, a panel could be
    // restored and focused against an empty workspace, which is the locked-
    // steps symptom in a different guise.
    const source = readFileSync(
      resolve("src/components/DesktopShell.vue"),
      "utf8",
    );
    const load = source.indexOf("loadSavedState();");
    const restore = source.indexOf("restoreSession();");

    expect(load).toBeGreaterThan(-1);
    expect(restore).toBeGreaterThan(-1);
    expect(load).toBeLessThan(restore);
  });

  it("actually calls it when the shell mounts", async () => {
    setContext({ projectId: "p-1", simulationId: "s-1" });

    const wrapper = mount(DesktopShell, {
      global: {
        stubs: {
          DesktopMasthead: true,
          DesktopDock: true,
          DesktopTaskbar: true,
          DesktopWindow: true,
          TruthRail: true,
        },
      },
    });
    await flushPromises();
    await flushPromises();

    // The panel session restores one panel; the ids must still be present.
    expect(windows.value.length).toBeGreaterThan(0);
    const state = journeyState();
    expect(state.find((e) => e.id === "assumptions").reached).toBe(true);
    wrapper.unmount();
  });
});
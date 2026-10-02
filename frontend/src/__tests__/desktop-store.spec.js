// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_LAYOUT_MODE,
  JOURNEY_TOTAL,
  activeKey,
  activeWindow,
  closeAllWindows,
  closeWindow,
  cycleLayoutMode,
  currentJourneyStep,
  focusWindow,
  journeyState,
  launchRouteFor,
  layoutMode,
  minimizeWindow,
  openApp,
  openRoute,
  persistSession,
  restoreSession,
  tileWindows,
  windows,
} from "../composables/useDesktop.js";
import { clearState, setContext } from "../composables/useWorkspaceState.js";

const DESKTOP_KEY = "atp_desktop_session_v1";

function memoryStorage() {
  const store = new Map();
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
    key: (index) => [...store.keys()][index] ?? null,
    get length() {
      return store.size;
    },
  };
}

let storage;

function installStorage() {
  storage = memoryStorage();
  vi.stubGlobal("localStorage", storage);
  Object.defineProperty(window, "localStorage", {
    value: storage,
    configurable: true,
    writable: true,
  });
}

function resetDesktop() {
  closeAllWindows();
  layoutMode.value = DEFAULT_LAYOUT_MODE;
  clearState();
  storage.clear();
}

beforeEach(() => {
  installStorage();
  resetDesktop();
});

describe("desktop window lifecycle", () => {
  it("opens a window for an app and marks it active", () => {
    const win = openApp("decision", { name: "Home" });

    expect(win).not.toBeNull();
    expect(windows.value).toHaveLength(1);
    expect(activeKey.value).toBe(win.key);
    expect(activeWindow.value.key).toBe(win.key);
  });

  it("deduplicates an open app instead of opening a second window", () => {
    openApp("decision", { name: "Home" });
    openApp("decision", { name: "Home" });

    expect(windows.value).toHaveLength(1);
  });

  it("distinguishes the same app by its route parameter", () => {
    const a = openApp("brief", { name: "Report", params: { reportId: "r-1" } });
    const b = openApp("brief", { name: "Report", params: { reportId: "r-2" } });

    expect(a.key).not.toBe(b.key);
    expect(windows.value).toHaveLength(2);
  });

  it("closes a window and activates the next visible window", () => {
    const a = openApp("decision", { name: "Home" });
    const b = openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    closeWindow(b.key);

    expect(windows.value).toHaveLength(1);
    expect(activeKey.value).toBe(a.key);
  });

  it("minimizes a window and moves focus to the next visible one", () => {
    const a = openApp("decision", { name: "Home" });
    openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    minimizeWindow(activeKey.value);

    expect(activeKey.value).toBe(a.key);
    expect(windows.value.find((w) => w.minimized)?.key).toBe("brief:r-1");
  });

  it("defaults to one panel at a time, because the journey is sequential", () => {
    expect(DEFAULT_LAYOUT_MODE).toBe("focus");
  });

  it("toggles between a side-by-side pair and floating panels", () => {
    openApp("decision", { name: "Home" });
    openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    tileWindows();
    expect(layoutMode.value).toBe("split");

    tileWindows();
    expect(layoutMode.value).toBe("free");
  });

  it("cycles through every layout mode and returns to where it started", () => {
    const start = layoutMode.value;
    const seen = new Set([start]);
    for (let i = 0; i < 3; i += 1) seen.add(cycleLayoutMode());
    expect(seen.size).toBe(3);
    expect(layoutMode.value).toBe(start);
  });

  it("restores a pre-redesign tiled session as a side-by-side pair", () => {
    storage.setItem(
      DESKTOP_KEY,
      JSON.stringify({
        activeKey: "decision",
        layoutMode: "tiled",
        windows: [
          {
            key: "decision",
            appId: "decision",
            minimized: false,
            maximized: false,
            params: {},
            query: {},
          },
        ],
      }),
    );

    restoreSession(true);

    expect(layoutMode.value).toBe("split");
  });

  it("opens a route by its route name", () => {
    const win = openRoute({ name: "Simulation", params: { simulationId: "s-1" } });

    expect(win).not.toBeNull();
    expect(win.routeName).toBe("Simulation");
    expect(win.params.simulationId).toBe("s-1");
  });

  it("focuses an already-open window instead of creating a duplicate", () => {
    const first = openApp("brief", { name: "Report", params: { reportId: "r-1" } });
    openApp("decision", { name: "Home" });

    const refocused = openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    expect(windows.value).toHaveLength(2);
    expect(activeKey.value).toBe(first.key);
    expect(refocused.key).toBe(first.key);
  });
});

describe("dock launch gating", () => {
  it("always launches the decision step", () => {
    expect(launchRouteFor("decision")).toEqual({ name: "Home" });
  });

  it("gates parameterized steps on their workspace coordinate", () => {
    expect(launchRouteFor("brief")).toBeNull();

    setContext({ reportId: "r-9" });
    expect(launchRouteFor("brief")).toEqual({
      name: "Report",
      params: { reportId: "r-9" },
    });
  });

  it("carries the saved round count into a run launch", () => {
    setContext({ simulationId: "s-4", maxRounds: 12 });

    expect(launchRouteFor("run")).toEqual({
      name: "SimulationRun",
      params: { simulationId: "s-4" },
      query: { maxRounds: "12" },
    });
  });
});

describe("journey spine state", () => {
  it("locks every step after the decision until its coordinate exists", () => {
    openApp("decision", { name: "Home" });

    const state = journeyState();
    expect(state).toHaveLength(JOURNEY_TOTAL);
    expect(state[0].status).toBe("current");
    expect(state.slice(1).every((entry) => entry.status === "locked")).toBe(true);
  });

  it("does not offer a step whose predecessor has not been reached", () => {
    openApp("decision", { name: "Home" });
    // simulationId alone would make both "Set assumptions" and "Run scenarios"
    // reachable if availability were read per-step instead of cumulatively.
    setContext({ simulationId: "s-1" });

    const state = journeyState();
    expect(state.find((e) => e.id === "assumptions").status).toBe("locked");
    expect(state.find((e) => e.id === "run").status).toBe("locked");
  });

  it("offers the next step once the workspace can reach it", () => {
    openApp("decision", { name: "Home" });
    setContext({ projectId: "p-1", simulationId: "s-1" });

    openApp("assumptions", { name: "Simulation", params: { simulationId: "s-1" } });

    const state = journeyState();
    expect(state.find((e) => e.id === "assumptions").status).toBe("current");
    expect(state.find((e) => e.id === "run").status).toBe("next");
    expect(currentJourneyStep()).toBe(3);
  });

  it("keeps the step the user is looking at, not the furthest one reached", () => {
    openApp("decision", { name: "Home" });
    setContext({ projectId: "p-1", simulationId: "s-1" });
    openApp("run", {
      name: "SimulationRun",
      params: { simulationId: "s-1" },
    });

    expect(currentJourneyStep()).toBe(4);
  });
});

describe("session persistence", () => {
  it("round-trips the window set and active window", () => {
    const first = openApp("decision", { name: "Home" });
    const second = openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    persistSession();
    expect(storage.getItem(DESKTOP_KEY)).not.toBeNull();

    closeAllWindows();

    restoreSession(true);

    expect(windows.value.map((w) => w.key).sort()).toEqual(
      [first.key, second.key].sort(),
    );
    expect(activeKey.value).toBe(second.key);
  });

  it("drops unknown apps when restoring", () => {
    storage.setItem(
      DESKTOP_KEY,
      JSON.stringify({
        activeKey: "ghost:1",
        layoutMode: "free",
        windows: [
          { key: "ghost:1", appId: "ghost", minimized: false, maximized: false },
          {
            key: "decision",
            appId: "decision",
            minimized: false,
            maximized: false,
            params: {},
            query: {},
          },
        ],
      }),
    );

    restoreSession(true);

    expect(windows.value.map((w) => w.key)).toEqual(["decision"]);
  });
});

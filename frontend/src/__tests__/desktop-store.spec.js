// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  activeKey,
  activeWindow,
  closeAllWindows,
  closeWindow,
  focusWindow,
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
  layoutMode.value = "free";
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

  it("toggles tiling across all windows", () => {
    openApp("decision", { name: "Home" });
    openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    tileWindows();
    expect(layoutMode.value).toBe("tiled");

    tileWindows();
    expect(layoutMode.value).toBe("free");
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

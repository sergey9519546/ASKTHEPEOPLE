import { computed, ref } from "vue";
import { workspaceState } from "./useWorkspaceState.js";
import Home from "../views/Home.vue";
import MainView from "../views/MainView.vue";
import SimulationView from "../views/SimulationView.vue";
import SimulationRunView from "../views/SimulationRunView.vue";
import ReportView from "../views/ReportView.vue";
import InteractionView from "../views/InteractionView.vue";

/**
 * The journey is a launchable application suite, not a linear page stack.
 * Each "app" maps one step of the route grammar onto a window that hosts the
 * existing route view. The store owns window lifecycle (open / focus /
 * minimize / maximize / close / tile) and persists the desktop across
 * refreshes; the shell is responsible for syncing windows with the URL.
 */

const STORAGE_KEY = "atp_desktop_session_v1";
const MAX_WINDOWS = 8;
const CASCADE_STEP = 36;
const CASCADE_ORIGIN = 56;

export const DESKTOP_APPS = [
  {
    id: "decision",
    title: "State the decision",
    code: "D-01",
    group: "Journey",
    routeName: "Home",
    component: Home,
  },
  {
    id: "sources",
    title: "Map the sources",
    code: "SM-01",
    group: "Journey",
    routeName: "Process",
    param: "projectId",
    component: MainView,
  },
  {
    id: "assumptions",
    title: "Set assumptions",
    code: "A-01",
    group: "Journey",
    routeName: "Simulation",
    param: "simulationId",
    component: SimulationView,
  },
  {
    id: "run",
    title: "Run scenarios",
    code: "P-01",
    group: "Journey",
    routeName: "SimulationRun",
    param: "simulationId",
    component: SimulationRunView,
  },
  {
    id: "brief",
    title: "Decision brief",
    code: "DC-01",
    group: "Journey",
    routeName: "Report",
    param: "reportId",
    component: ReportView,
  },
  {
    id: "followup",
    title: "Ask follow-ups",
    code: "VQ-01",
    group: "Journey",
    routeName: "Interaction",
    param: "reportId",
    component: InteractionView,
  },
];

export const appById = (id) => DESKTOP_APPS.find((app) => app.id === id);
export const appByRouteName = (name) =>
  DESKTOP_APPS.find((app) => app.routeName === name);

export const windows = ref([]);
export const activeKey = ref(null);
export const layoutMode = ref("free");
let zCounter = 10;
let cascadeIndex = 0;
let persisted = false;
let persistTimer = null;

export const activeWindow = computed(
  () => windows.value.find((window) => window.key === activeKey.value) || null,
);

export const activeRoute = computed(() => {
  const win = activeWindow.value;
  if (!win) return null;
  if (win.routeName === "Home") return { name: "Home" };
  return { name: win.routeName, params: win.params || {}, query: win.query || {} };
});

function keyFor(app, route) {
  const paramValue = app.param ? route.params?.[app.param] : null;
  return paramValue ? `${app.id}:${paramValue}` : app.id;
}

function nextCascade() {
  const index = cascadeIndex % 8;
  cascadeIndex += 1;
  return {
    x: CASCADE_ORIGIN + index * CASCADE_STEP,
    y: CASCADE_ORIGIN + index * CASCADE_STEP,
  };
}

function schedulePersist() {
  if (persistTimer) clearTimeout(persistTimer);
  persistTimer = setTimeout(persistSession, 250);
}

export function persistSession() {
  try {
    const payload = {
      activeKey: activeKey.value,
      layoutMode: layoutMode.value,
      windows: windows.value.map((window) => ({
        key: window.key,
        appId: window.appId,
        minimized: window.minimized,
        maximized: window.maximized,
        x: window.x,
        y: window.y,
        w: window.w,
        h: window.h,
        params: window.params,
        query: window.query,
      })),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // A blocked storage API degrades to a session-only desktop.
  }
}

export function restoreSession(force = false) {
  if (persisted && !force) return;
  persisted = true;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.windows)) return;

    const restored = [];
    for (const entry of parsed.windows) {
      const app = appById(entry.appId);
      if (!app) continue;
      const routeName = app.routeName;
      const params = entry.params || {};
      const query = entry.query || {};
      restored.push({
        key: entry.key || keyFor(app, { params }),
        appId: app.id,
        routeName,
        params,
        query,
        minimized: Boolean(entry.minimized),
        maximized: Boolean(entry.maximized),
        x: Number.isFinite(entry.x) ? entry.x : null,
        y: Number.isFinite(entry.y) ? entry.y : null,
        w: Number.isFinite(entry.w) ? entry.w : null,
        h: Number.isFinite(entry.h) ? entry.h : null,
        z: ++zCounter,
      });
    }
    windows.value = restored.slice(0, MAX_WINDOWS);
    layoutMode.value = parsed.layoutMode === "tiled" ? "tiled" : "free";
    const active = restored.find((window) => window.key === parsed.activeKey);
    activeKey.value = active ? active.key : restored[0]?.key || null;
    if (activeKey.value) {
      const focused = windows.value.find((w) => w.key === activeKey.value);
      if (focused) focused.z = ++zCounter;
    }
  } catch {
    windows.value = [];
    activeKey.value = null;
  }
}

export function openApp(appId, route = {}) {
  const app = appById(appId);
  if (!app) return null;
  if (windows.value.length >= MAX_WINDOWS) {
    return focusWindow(windows.value[windows.value.length - 1].key);
  }

  const key = keyFor(app, route);
  const existing = windows.value.find((window) => window.key === key);
  if (existing) {
    return focusWindow(existing.key);
  }

  const { x, y } = nextCascade();
  const win = {
    key,
    appId: app.id,
    routeName: route.name || app.routeName,
    params: { ...(route.params || {}) },
    query: { ...(route.query || {}) },
    minimized: false,
    maximized: false,
    x,
    y,
    w: null,
    h: null,
    z: ++zCounter,
  };
  windows.value.push(win);
  focusWindow(win.key);
  return win;
}

export function openRoute(route = {}) {
  const app = appByRouteName(route.name);
  if (!app) return null;
  return openApp(app.id, route);
}

export function focusWindow(key) {
  const win = windows.value.find((window) => window.key === key);
  if (!win) return win;
  win.minimized = false;
  win.z = ++zCounter;
  activeKey.value = win.key;
  schedulePersist();
  return win;
}

function topmostVisible() {
  return windows.value
    .filter((window) => !window.minimized)
    .sort((a, b) => b.z - a.z)[0];
}

export function closeWindow(key) {
  const index = windows.value.findIndex((window) => window.key === key);
  if (index === -1) return;
  windows.value.splice(index, 1);
  if (activeKey.value === key) {
    const next = topmostVisible();
    activeKey.value = next ? next.key : windows.value[0]?.key || null;
  }
  schedulePersist();
}

export function minimizeWindow(key) {
  const win = windows.value.find((window) => window.key === key);
  if (!win) return;
  win.minimized = true;
  if (activeKey.value === key) {
    const next = windows.value
      .filter((window) => window.key !== key && !window.minimized)
      .sort((a, b) => b.z - a.z)[0];
    if (next) activeKey.value = next.key;
  }
  schedulePersist();
}

export function toggleMaximize(key) {
  const win = windows.value.find((window) => window.key === key);
  if (!win) return;
  win.maximized = !win.maximized;
  focusWindow(key);
}

export function tileWindows() {
  const visible = windows.value.filter((window) => !window.minimized);
  for (const win of visible) win.minimized = false;
  layoutMode.value = layoutMode.value === "tiled" ? "free" : "tiled";
  schedulePersist();
}

export function untileWindows() {
  layoutMode.value = "free";
  schedulePersist();
}

export function closeAllWindows() {
  windows.value = [];
  activeKey.value = null;
  schedulePersist();
}

export function cycleWindow(direction = 1) {
  const visible = windows.value
    .filter((window) => !window.minimized)
    .sort((a, b) => a.z - b.z);
  if (visible.length < 2) return;
  const index = visible.findIndex((window) => window.key === activeKey.value);
  const nextIndex =
    index === -1
      ? 0
      : (index + direction + visible.length) % visible.length;
  focusWindow(visible[nextIndex].key);
}

export function updateGeometry(key, patch) {
  const win = windows.value.find((window) => window.key === key);
  if (!win) return;
  Object.assign(win, patch);
  schedulePersist();
}

/**
 * Build the route the dock should navigate to for an app, using the
 * workspace's current coordinates. Returns null when a prerequisite step has
 * not produced the required id yet (the dock renders the app unavailable).
 */
export function launchRouteFor(appId) {
  const app = appById(appId);
  if (!app) return null;
  if (!app.param) return { name: app.routeName };

  const context = workspaceState.value;
  const value = context[app.param];
  if (!value) return null;

  const route = { name: app.routeName, params: { [app.param]: value } };
  if (app.id === "run" && context.maxRounds) {
    route.query = { maxRounds: String(context.maxRounds) };
  }
  return route;
}

export function windowForApp(appId) {
  return windows.value.find((window) => window.appId === appId) || null;
}

export function useDesktop() {
  return {
    DESKTOP_APPS,
    windows,
    activeKey,
    activeWindow,
    activeRoute,
    layoutMode,
    openApp,
    openRoute,
    focusWindow,
    closeWindow,
    minimizeWindow,
    toggleMaximize,
    tileWindows,
    untileWindows,
    closeAllWindows,
    cycleWindow,
    updateGeometry,
    launchRouteFor,
    windowForApp,
    restoreSession,
    persistSession,
  };
}

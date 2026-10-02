import { computed, ref } from "vue";
import { workspaceState } from "./useWorkspaceState.js";
import Home from "../views/Home.vue";
import MainView from "../views/MainView.vue";
import SimulationView from "../views/SimulationView.vue";
import SimulationRunView from "../views/SimulationRunView.vue";
import ReportView from "../views/ReportView.vue";
import InteractionView from "../views/InteractionView.vue";

/**
 * The journey is a launchable suite of panels, not a page stack and not a
 * window manager. Each entry maps one destination onto the route view that
 * renders it; the store owns panel lifecycle (open / focus / minimize /
 * maximize / close / layout) and persists the workspace across refreshes; the
 * shell syncs panels with the URL.
 *
 * `step` is the journey position and `requires` is the workspace coordinate a
 * step needs before it can be launched. Both live here, next to the title,
 * because the journey spine and the availability messaging are two renderings
 * of one list and must never disagree about what comes next.
 */

const STORAGE_KEY = "atp_desktop_session_v1";
const MAX_WINDOWS = 8;
const CASCADE_STEP = 36;
const CASCADE_ORIGIN = 56;

export const DESKTOP_APPS = [
  {
    id: "decision",
    step: 1,
    title: "State the decision",
    code: "D-01",
    group: "Journey",
    routeName: "Home",
    component: Home,
    outcome: "One written decision to examine",
  },
  {
    id: "sources",
    step: 2,
    title: "Map the sources",
    code: "SM-01",
    group: "Journey",
    routeName: "Process",
    param: "projectId",
    component: MainView,
    requires: "projectId",
    outcome: "Reviewed starting material",
  },
  {
    id: "assumptions",
    step: 3,
    title: "Set assumptions",
    code: "A-01",
    group: "Journey",
    routeName: "Simulation",
    param: "simulationId",
    component: SimulationView,
    requires: "simulationId",
    outcome: "Named uncertainties and assumptions",
  },
  {
    id: "run",
    step: 4,
    title: "Run scenarios",
    code: "P-01",
    group: "Journey",
    routeName: "SimulationRun",
    param: "simulationId",
    component: SimulationRunView,
    requires: "simulationId",
    outcome: "Equal-weight generated paths",
  },
  {
    id: "brief",
    step: 5,
    title: "Decision brief",
    code: "DC-01",
    group: "Journey",
    routeName: "Report",
    param: "reportId",
    component: ReportView,
    requires: "reportId",
    outcome: "Findings, limits, and next steps",
  },
  {
    id: "followup",
    step: 6,
    title: "Ask follow-ups",
    code: "VQ-01",
    group: "Journey",
    routeName: "Interaction",
    param: "reportId",
    component: InteractionView,
    requires: "reportId",
    outcome: "Questions to take to real people",
  },
];

/**
 * Layout modes, in the order the switcher offers them.
 *
 * `focus` is the default because this is a sequential journey: one panel at a
 * time, full height and width, with the switcher flipping between open
 * panels. `split` puts the active panel beside the most recently used other
 * panel, which is the comparison case the source map exists for. `free` keeps
 * the original draggable cascade for people who want two surfaces floating.
 *
 * `tiled` is retained as a persisted value so a session saved before this
 * change still restores to something sensible; it now means `split`.
 */
const LAYOUT_MODES = ["focus", "split", "free"];
export const DEFAULT_LAYOUT_MODE = "focus";

export const appById = (id) => DESKTOP_APPS.find((app) => app.id === id);
export const appByRouteName = (name) =>
  DESKTOP_APPS.find((app) => app.routeName === name);

export const windows = ref([]);
export const activeKey = ref(null);
export const layoutMode = ref(DEFAULT_LAYOUT_MODE);
let zCounter = 10;
let cascadeIndex = 0;
let persisted = false;
let persistTimer = null;

export const activeWindow = computed(
  () => windows.value.find((window) => window.key === activeKey.value) || null,
);


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
    // "tiled" is the pre-redesign name for a side-by-side layout.
    const savedLayout = parsed.layoutMode === "tiled" ? "split" : parsed.layoutMode;
    layoutMode.value = LAYOUT_MODES.includes(savedLayout) ? savedLayout : DEFAULT_LAYOUT_MODE;
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

/**
 * Every panel switch animates, not just the keyboard one.
 *
 * The transition lives here rather than in the shell because the shell is only
 * one of the callers: the switcher, the journey spine, and the URL watcher all
 * change the active panel, and routing the transition through a single function
 * is the only way to guarantee they agree. Leaving it in the shell meant tab
 * clicks cut instantly while the Alt+` shortcut cross-faded.
 *
 * The cross-fade is scoped by `view-transition-name` on the workspace canvas in
 * DesktopShell.vue. Without that name the browser transitions the whole
 * document root, which would cross-fade the truth rail, masthead, spine, and
 * switcher on every switch - re-animating the orientation surfaces at the exact
 * moment the user is trying to read a different one.
 *
 * Feature-detected and no-op when the API is absent or the user has asked for
 * reduced motion. Same-document view transitions are Baseline since October
 * 2025; Vue has no first-party support, so this is the hand-rolled glue.
 */
function runPanelTransition(update) {
  const canTransition =
    typeof document !== "undefined" &&
    typeof document.startViewTransition === "function" &&
    !(typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
  if (!canTransition) {
    update();
    return;
  }
  document.startViewTransition(update);
}

export function focusWindow(key) {
  const win = windows.value.find((window) => window.key === key);
  if (!win) return win;
  runPanelTransition(() => {
    win.minimized = false;
    win.z = ++zCounter;
    activeKey.value = win.key;
    schedulePersist();
  });
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

/**
 * Step through the layout modes. `tileWindows` is kept as the historical name
 * because the command palette and the panel switcher both refer to a two-panel
 * arrangement as "tiling"; internally that arrangement is `split`.
 */
export function tileWindows() {
  const visible = windows.value.filter((window) => !window.minimized);
  for (const win of visible) win.minimized = false;
  layoutMode.value = layoutMode.value === "split" ? "free" : "split";
  schedulePersist();
}

export function cycleLayoutMode() {
  const index = LAYOUT_MODES.indexOf(layoutMode.value);
  layoutMode.value = LAYOUT_MODES[(index + 1) % LAYOUT_MODES.length];
  schedulePersist();
  return layoutMode.value;
}

export function setLayoutMode(mode) {
  if (!LAYOUT_MODES.includes(mode)) return layoutMode.value;
  layoutMode.value = mode;
  schedulePersist();
  return layoutMode.value;
}


/**
 * The panels a two-panel layout should show: the active one first, then the
 * most recently focused other panel. Returning them in order lets the shell
 * render a stable left/right pair instead of z-order accident.
 */
export function visiblePair() {
  const open = windows.value.filter((window) => !window.minimized);
  if (open.length <= 1) return open;
  const active = open.find((window) => window.key === activeKey.value) || open[0];
  const other = [...open]
    .filter((window) => window.key !== active.key)
    .sort((a, b) => b.z - a.z)[0];
  return [active, other];
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

/**
 * One derivation of journey state, consumed by the spine, the masthead, and
 * the switcher. Every surface that says "where am I" reads this, so the three
 * can never tell three different stories about the same workspace.
 *
 * A step is `reached` once every step before it is reached, which is what the
 * `requires` coordinate encodes. States:
 *   - `done`     reached, and the workspace has moved past it
 *   - `current`  the furthest step reached, or the open panel
 *   - `next`     reached but not yet the furthest
 *   - `locked`   a prerequisite coordinate is missing
 */
export function journeyState() {
  const context = workspaceState.value;
  const openSteps = DESKTOP_APPS.filter((app) => windowForApp(app.id)).map(
    (app) => app.step,
  );
  const activeStep = activeWindow.value
    ? (appById(activeWindow.value.appId)?.step ?? 0)
    : 0;

  // Reachability is cumulative: a step is launchable only if every step before
  // it is launchable. Deriving each step's availability from its own
  // coordinate alone would let "Run scenarios" appear while "Set assumptions"
  // is still locked, because both read simulationId.
  let reachable = true;
  const entries = DESKTOP_APPS.map((app) => {
    const hasCoordinate = !app.requires || Boolean(context[app.requires]);
    const reached = reachable && hasCoordinate;
    reachable = reached;
    return { ...app, reached, open: openSteps.includes(app.step) };
  });

  const furthest = entries.reduce(
    (acc, entry) => (entry.reached ? Math.max(acc, entry.step) : acc),
    0,
  );
  const position = activeStep || (openSteps.length ? Math.min(...openSteps) : furthest) || 1;

  return entries.map((entry) => {
    let status = "locked";
    if (entry.reached) {
      if (entry.step === position) status = "current";
      else if (entry.step < position) status = "done";
      else status = "next";
    }
    return { ...entry, status, position };
  });
}

export const JOURNEY_TOTAL = DESKTOP_APPS.length;

/** "Step 3 of 6" for the surface the user is actually looking at. */
export function currentJourneyStep() {
  const state = journeyState();
  const active = state.find((entry) => entry.status === "current");
  if (active) return active.step;
  return state.filter((entry) => entry.reached).length || 1;
}


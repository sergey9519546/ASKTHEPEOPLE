<template>
  <div class="desktop-shell" :class="{ 'is-narrow': isNarrow }">
    <TruthRail />

    <DesktopMasthead />

    <div class="desktop-main">
      <DesktopDock :collapsed="dockCollapsed" @toggle="dockCollapsed = !dockCollapsed" />

      <section
        class="desktop-surface"
        aria-label="Workspace panels"
        :class="[`layout-${isNarrow ? 'focus' : layoutMode}`]"
      >
        <DesktopWindow
          v-for="win in renderedPanels"
          :key="win.key"
          :win="win"
          :mode="layoutMode"
        />
      </section>
    </div>

    <DesktopTaskbar :panels="switcherPanels" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import TruthRail from "./TruthRail.vue";
import DesktopMasthead from "./DesktopMasthead.vue";
import DesktopDock from "./DesktopDock.vue";
import DesktopTaskbar from "./DesktopTaskbar.vue";
import DesktopWindow from "./DesktopWindow.vue";
import {
  activeKey,
  activeWindow,
  appByRouteName,
  closeWindow,
  cycleWindow,
  focusWindow,
  layoutMode,
  openApp,
  openRoute,
  restoreSession,
  visiblePair,
  windows,
} from "../composables/useDesktop.js";
import { loadSavedState } from "../composables/useWorkspaceState.js";

/**
 * The shell owns four bands - truth rail, masthead, journey spine, panel
 * switcher - and exactly one canvas.
 *
 * The default layout is one panel at a time. The journey is sequential: each
 * step consumes what the previous one produced, so a cascading pile of floating
 * windows was asking the user to manage windows while they were trying to think
 * about a decision. Side-by-side remains available when comparison is the actual
 * task, and floating remains available for people who want two surfaces at
 * once, but neither is the default.
 *
 * Panel switching goes through the View Transitions API, and `focusWindow` in
 * the desktop store owns it so the switcher, the spine, and the URL watcher all
 * animate identically. This component's contribution is the canvas's
 * `view-transition-name`: naming only the canvas is what keeps the truth rail,
 * masthead, spine, and switcher still while the panel beneath them cross-fades.
 * There is deliberately no hand-written overlap animation - keeping both panels
 * in the DOM at once is exactly what causes reading-position loss and the
 * confusing live-region announcements MDN warns about.
 */
const route = useRoute();
const router = useRouter();

const isNarrow = ref(false);
const dockCollapsed = ref(false);
let syncing = false;
let narrowQuery = null;
let dockQuery = null;



/**
 * Panels the canvas renders for the current layout mode.
 *
 * A narrow viewport overrides the chosen mode. Splitting a 700px viewport gives
 * each panel less width than a decision brief can be read at, and a floating
 * cascade has nowhere to cascade to, so both degrade to one panel. The user's
 * chosen mode is not overwritten - it is honoured again on the way back up.
 */
const renderedPanels = computed(() => {
  const active = activeWindow.value;
  const single = active && !active.minimized
    ? [active]
    : windows.value.filter((win) => !win.minimized);

  if (isNarrow.value || layoutMode.value === "focus") return single;
  if (layoutMode.value === "split") {
    return visiblePair().filter((win) => !win.minimized);
  }
  return windows.value;
});

/** Panels the switcher offers, which is every panel the user has open. */
const switcherPanels = computed(() => windows.value);

function sameRoute(a, b) {
  if (!a || !b) return false;
  if (a.name !== b.name) return false;
  const aParams = a.params || {};
  const bParams = b.params || {};
  const aQuery = a.query || {};
  const bQuery = b.query || {};
  for (const key of new Set([...Object.keys(aParams), ...Object.keys(bParams)])) {
    if (String(aParams[key] ?? "") !== String(bParams[key] ?? "")) return false;
  }
  for (const key of new Set([...Object.keys(aQuery), ...Object.keys(bQuery)])) {
    if (String(aQuery[key] ?? "") !== String(bQuery[key] ?? "")) return false;
  }
  return true;
}

// URL -> panels. Deep links, browser back/forward, and view-initiated pushes all
// land here: the matching panel is opened (if needed) and focused.
watch(
  () => route.fullPath,
  () => {
    if (syncing) return;
    syncing = true;
    const app = appByRouteName(route.name);
    if (app) {
      openRoute({ name: route.name, params: route.params, query: route.query });
    } else {
      openApp("decision", { name: "Home" });
    }
    nextTick(() => {
      syncing = false;
    });
  },
);

// Panels -> URL. User panel focus and switcher actions change the active panel;
// the URL follows so refreshes and shares keep working. Switches use replace so
// they never spam history.
watch(activeWindow, (win) => {
  if (syncing || !win) return;
  const target = win.routeName === "Home" ? { name: "Home" } : {
    name: win.routeName,
    params: win.params || {},
    query: win.query && Object.keys(win.query).length ? win.query : undefined,
  };
  if (sameRoute(target, route)) return;
  syncing = true;
  const navigate = router.replace || router.push;
  navigate.call(router, target);
  nextTick(() => {
    syncing = false;
  });
});

// The workspace never stays empty: closing the last panel returns to the
// decision, which is always available.
watch(
  () => windows.value.length,
  (count) => {
    if (count === 0) {
      openApp("decision", { name: "Home" });
    }
  },
);

function onKeydown(event) {
  if (event.defaultPrevented) return;
  const target = event.target;
  const typing =
    target &&
    (target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.tagName === "SELECT" ||
      target.isContentEditable);
  if (typing) return;

  const mod = event.ctrlKey || event.metaKey;
  // Ctrl/Cmd+W closes the focused panel. This deliberately does NOT also bind
  // Ctrl+Tab: that chord belongs to the browser, and a workspace must never
  // stand between a person and the tab they meant to switch to.
  if (mod && !event.altKey && !event.shiftKey && (event.key === "w" || event.key === "W")) {
    if (activeWindow.value) {
      event.preventDefault();
      closeWindow(activeWindow.value.key);
    }
    return;
  }
  if (event.altKey && event.code === "Backquote") {
    event.preventDefault();
    // cycleWindow routes through focusWindow, which owns the cross-fade.
    cycleWindow(event.shiftKey ? -1 : 1);
  }
}

function updateNarrow(event) {
  isNarrow.value = Boolean(event.matches);
}

// Orientation is not a preference. The spine opens expanded and stays expanded
// until the viewport is too narrow to carry the labels, or the user collapses
// it themselves.
function updateDockRoom(event) {
  dockCollapsed.value = !event.matches;
}

onMounted(async () => {
  if (window.matchMedia) {
    narrowQuery = window.matchMedia("(max-width: 860px)");
    isNarrow.value = narrowQuery.matches;
    narrowQuery.addEventListener?.("change", updateNarrow);

    dockQuery = window.matchMedia("(min-width: 1080px)");
    dockCollapsed.value = !dockQuery.matches;
    dockQuery.addEventListener?.("change", updateDockRoom);
  }
  document.addEventListener("keydown", onKeydown);

  // Workspace state MUST be restored before the panel session, and both must be
  // restored before any journey state is read.
  //
  // `setContext()` persists every id a window reports to localStorage, but
  // nothing was calling `loadSavedState()`, so on a refresh `workspaceState`
  // came back as DEFAULT_STATE with empty ids. `journeyState()` gates
  // cumulatively on those ids, so every completed step reappeared as LOCKED
  // even though its panel was still open and its work was still on screen. The
  // spine made this visible: before it existed, nothing read workspace state at
  // boot, so the omission was harmless.
  loadSavedState();
  restoreSession();

  // vue-router resolves the initial navigation asynchronously, so a direct
  // deep-link load would otherwise boot against the START_LOCATION ("/", no
  // route name) and bounce to Home. Wait for the route to resolve first.
  if (typeof router.isReady === "function") {
    await router.isReady();
  }

  const app = appByRouteName(route.name);
  if (app) {
    openRoute({ name: route.name, params: route.params, query: route.query });
  } else if (windows.value.length === 0) {
    openApp("decision", { name: "Home" });
  } else {
    focusWindow(activeKey.value || windows.value[0].key);
  }
});

onBeforeUnmount(() => {
  narrowQuery?.removeEventListener?.("change", updateNarrow);
  dockQuery?.removeEventListener?.("change", updateDockRoom);
  document.removeEventListener("keydown", onKeydown);
});

</script>

<style scoped>
.desktop-shell {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--ink);
  color: var(--paper);
}

.desktop-main {
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
}

.desktop-surface {
  /* Names the canvas for the View Transitions API. Without a name the browser
     transitions the document root, which would cross-fade all four orientation
     bands on every switch. */
  view-transition-name: workspace-canvas;
  position: relative;
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--ink);
}

.layout-focus {
  display: block;
}

.layout-free {
  display: block;
  overflow: auto;
}

.layout-split {
  gap: 0;
}

@media (max-width: 860px) {
  .desktop-main {
    flex-direction: column;
  }
}
</style>

<style>
/* Route views were written as full-viewport pages. Inside a panel they fill the
   panel body instead. These selectors intentionally outrank the global 100dvh
   rules in design-tokens.css. */
.desktop-window-body .main-view,
.desktop-window-body .bauhaus-view-root,
.desktop-window-body .app-view-root {
  height: 100% !important;
  min-height: 0 !important;
}

.desktop-window-body .public-signal-home,
.desktop-window-body .not-found-view {
  min-height: 0 !important;
}

/* Panel switching is a cross-fade scoped to the canvas, not an overlap, and not
   a whole-document cross-fade. Naming only the canvas keeps the orientation
   surfaces still while the content beneath them changes; letting the browser
   interpolate keeps reading position and focus stable, which a hand-managed
   overlap does not. */
@media (prefers-reduced-motion: no-preference) {
  ::view-transition-old(workspace-canvas),
  ::view-transition-new(workspace-canvas) {
    animation-duration: 160ms;
    animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
  }
}
</style>
<template>
  <div class="desktop-shell" :class="{ 'is-narrow': isNarrow }">
    <TruthRail />
    <DesktopMasthead />

    <div class="desktop-main">
      <DesktopDock :collapsed="dockCollapsed" @toggle="dockCollapsed = !dockCollapsed" />

      <main
        class="desktop-surface"
        :class="{ 'is-tiled': layoutMode === 'tiled' }"
        aria-label="Decision workspace"
      >
        <DesktopWindow
          v-for="win in windows"
          :key="win.key"
          :win="win"
          :tiled="layoutMode === 'tiled'"
          :locked="isNarrow"
        />
      </main>
    </div>

    <DesktopTaskbar />
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
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
  windows,
} from "../composables/useDesktop.js";

const route = useRoute();
const router = useRouter();

const isNarrow = ref(false);
  const dockCollapsed = ref(true);
let syncing = false;
let narrowQuery = null;

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

// URL -> windows. Deep links, browser back/forward, and view-initiated pushes
// all land here: the matching window is opened (if needed) and focused.
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

// Windows -> URL. User window focus/dock/taskbar actions change the active
// window; the URL follows the active window so refreshes and shares keep
// working. Window switches use replace so they never spam history.
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

// The desktop never stays empty: closing the last window returns to the
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
  if (mod && !event.altKey && !event.shiftKey && (event.key === "w" || event.key === "W")) {
    if (activeWindow.value) {
      event.preventDefault();
      closeWindow(activeWindow.value.key);
    }
    return;
  }
  if (event.altKey && event.code === "Backquote") {
    event.preventDefault();
    cycleWindow(1);
    return;
  }
  if (event.ctrlKey && event.key === "Tab") {
    event.preventDefault();
    cycleWindow(event.shiftKey ? -1 : 1);
  }
}

function updateNarrow(event) {
  isNarrow.value = Boolean(event.matches);
}

onMounted(async () => {
  if (window.matchMedia) {
    narrowQuery = window.matchMedia("(max-width: 860px)");
    isNarrow.value = narrowQuery.matches;
    narrowQuery.addEventListener?.("change", updateNarrow);
  }
  document.addEventListener("keydown", onKeydown);

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

.desktop-main { gap: var(--space-2);
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
}

.desktop-surface {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background: var(--ink);
}

.desktop-surface.is-tiled {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr));
  gap: 0.6rem;
  padding: 0.6rem;
  overflow: auto;
}

@media (max-width: 860px) {
  .desktop-main { gap: var(--space-2);
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
}
}
</style>

<style>
/* Route views were written as full-viewport pages. Inside a window they fill
   the window body instead. These selectors intentionally outrank the global
   100dvh rules in design-tokens.css. */
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

/* On narrow screens the desktop collapses to one full-screen window at a
   time; the taskbar switches between them. */
.desktop-shell.is-narrow .desktop-window {
  position: absolute !important;
  inset: 0 !important;
  left: 0 !important;
  top: 0 !important;
  width: auto !important;
  height: auto !important;
  display: none;
}

.desktop-shell.is-narrow .desktop-window.is-active {
  display: flex !important;
}

.desktop-shell.is-narrow .window-resize {
  display: none !important;
}
</style>



<template>
  <section
    v-if="visible"
    class="desktop-window"
    :class="[
      `layout-${mode}`,
      { 'is-active': isActive, 'is-maximized': win.maximized },
    ]"
    :style="windowStyle"
    :id="panelId"
    role="tabpanel"
    :aria-labelledby="tabId"
    tabindex="0"
    @pointerdown="raise"
  >
    <header class="window-titlebar">
      <div class="window-identity">
        <span class="window-code" aria-hidden="true">{{ app.code }}</span>
        <span :id="tabId" class="window-title">{{ app.title }}</span>
      </div>

      <div class="window-position" v-if="mode === 'free'">
        <button
          class="window-control window-control-text"
          type="button"
          :aria-expanded="positionOpen"
          aria-haspopup="menu"
          :aria-label="`Placement options for ${app.title}`"
          @click.stop="positionOpen = !positionOpen"
          @keydown.down.prevent.stop="openPositionAndFocusFirst"
        >
          Placement
        </button>
        <div v-if="positionOpen" class="position-menu" role="menu">
          <button
            v-for="option in POSITION_OPTIONS"
            :key="option.id"
            class="position-option"
            type="button"
            role="menuitem"
            @click.stop="applyPosition(option.id)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="window-controls">
        <button
          class="window-control u-target"
          type="button"
          data-window-control
          :aria-label="`Close ${app.title}`"
          title="Close panel"
          @click.stop="closeWindow(win.key)"
        >
          <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M1 1l10 10M11 1L1 11" /></svg>
        </button>
      </div>
    </header>

    <div class="desktop-window-body">
      <component :is="app.component" />
    </div>

    <div
      v-if="mode === 'free' && !win.maximized"
      class="window-resize u-target"
      role="separator"
      :aria-label="`Resize ${app.title}. Use the arrow keys to change the size.`"
      aria-orientation="horizontal"
      tabindex="0"
      @pointerdown.prevent="startResize"
      @keydown="onResizeKeydown"
    ></div>
  </section>
</template>

<script setup>
import { computed, provide, ref } from "vue";
import {
  appById,
  activeKey,
  closeWindow,
  focusWindow,
  updateGeometry,
} from "../composables/useDesktop.js";
import { windowContextKey } from "../composables/useWindowContext.js";

const props = defineProps({
  win: { type: Object, required: true },
  mode: { type: String, default: "focus" },
  position: { type: Number, default: 0 },
});

/**
 * One open panel.
 *
 * Two things changed and both were defects rather than preferences.
 *
 * Geometry. The panel used to be an absolutely positioned floating window at a
 * fixed size inside a viewport-height shell, which meant a long decision brief
 * lived in a 48rem box with its own nested scrollbar, and the free layout's
 * default was a cascading pile. Panels now participate in a deterministic
 * layout: one at a time, or two side by side, or free-floating only when the
 * user asks for it. Because most panels are no longer positioned by pointer at
 * all, the dragging accessibility problem largely disappears rather than being
 * patched.
 *
 * Roles. Panels are `tabpanel` and are labelled by the switcher tab that opens
 * them. They were `region` with an `h2` that sat *before* the view's own `h1`,
 * which inverted heading order in every window; the title is no longer a
 * heading, so each view is the single owner of its heading structure.
 */
const app = computed(() => appById(props.win.appId) || { title: "Panel", code: "" });
const isActive = computed(() => activeKey.value === props.win.key);
const visible = computed(() => !props.win.minimized);

const panelId = computed(() => `panel-body-${props.win.key}`);
const tabId = computed(() => `panel-tab-${props.win.key}`);

const positionOpen = ref(false);

const POSITION_OPTIONS = [
  { id: "fill", label: "Fill the workspace" },
  { id: "centre", label: "Centre in the workspace" },
  { id: "left", label: "Left half" },
  { id: "right", label: "Right half" },
];

// Each window renders its view with an isolated route context so views that
// read `useWindowRoute()` get their own decision/run params, never another
// window's.
provide(windowContextKey, {
  name: props.win.routeName,
  params: props.win.params,
  query: props.win.query,
});

const windowStyle = computed(() => {
  const win = props.win;
  if (props.mode !== "free") return {};
  if (win.maximized) return {};
  const width = Number.isFinite(win.w) && win.w ? `${win.w}px` : "min(72rem, calc(100% - 3rem))";
  const height = Number.isFinite(win.h) && win.h ? `${win.h}px` : "min(48rem, calc(100% - 3rem))";
  const left = Number.isFinite(win.x) ? `${win.x}px` : "1.5rem";
  const top = Number.isFinite(win.y) ? `${win.y}px` : "1.5rem";
  return { left, top, width, height, zIndex: win.z };
});

function raise() {
  if (!isActive.value) focusWindow(props.win.key);
}

function applyPosition(id) {
  positionOpen.value = false;
  if (id === "fill") {
    updateGeometry(props.win.key, { x: 0, y: 0, w: null, h: null, maximized: true });
    return;
  }
  if (id === "centre") {
    updateGeometry(props.win.key, { x: 96, y: 64, w: null, h: null, maximized: false });
    return;
  }
  updateGeometry(props.win.key, {
    x: id === "left" ? 24 : 380,
    y: 48,
    w: 360,
    h: null,
    maximized: false,
  });
}

function openPositionAndFocusFirst() {
  positionOpen.value = true;
}

/**
 * Dragging Movements (WCAG 2.2 SC 2.5.7) requires a single-pointer, non-drag
 * alternative - a modifier held while arrowing does not count, which is why the
 * grip is a real focusable separator with its own arrow-key behaviour rather
 * than a passive corner graphic.
 */
function onResizeKeydown(event) {
  const step = event.shiftKey ? 48 : 16;
  const win = props.win;
  const currentW = Number.isFinite(win.w) && win.w ? win.w : 560;
  const currentH = Number.isFinite(win.h) && win.h ? win.h : 360;
  const next = {};
  if (event.key === "ArrowRight") next.w = currentW + step;
  else if (event.key === "ArrowLeft") next.w = Math.max(320, currentW - step);
  else if (event.key === "ArrowDown") next.h = currentH + step;
  else if (event.key === "ArrowUp") next.h = Math.max(240, currentH - step);
  else return;
  event.preventDefault();
  updateGeometry(props.win.key, next);
}

function startResize(event) {
  if (event.button !== 0) return;
  const originW = props.win.w;
  const originH = props.win.h;
  const startX = event.clientX;
  const startY = event.clientY;

  const onMove = (moveEvent) => {
    updateGeometry(props.win.key, {
      w: Math.max(320, (originW || 560) + moveEvent.clientX - startX),
      h: Math.max(240, (originH || 360) + moveEvent.clientY - startY),
    });
  };
  const onUp = () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}
</script>

<style scoped>
.desktop-window {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: var(--ink);
  overflow: hidden;
}

/* Focus layout: the panel is the whole workspace. No positioning, no nested
   scroller fighting the shell's, and no floating chrome to occlude a focused
   control (WCAG 2.2 SC 2.4.11 Focus Not Obscured, AA). */
.layout-focus {
  width: 100%;
  height: 100%;
  border: 0;
}

/* Split layout: two panels share the width, both full height. */
.layout-split {
  width: 100%;
  height: 100%;
  min-width: 0;
  border: 0;
  border-right: 1px solid var(--line-dark);
  overflow: hidden;
}

.layout-free {
  position: absolute;
  border: 1px solid var(--line-dark);
  box-shadow: var(--shadow-md);
}

.layout-free.is-active {
  border-color: var(--signal);
  box-shadow: 0.7rem 0.7rem 0 rgba(0, 0, 0, 0.62);
}

.layout-free.is-maximized {
  inset: 0;
  width: auto;
  height: auto;
  border: 0;
  box-shadow: none;
}

.window-titlebar {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: var(--control-h-lg);
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-raised);
}

.layout-focus .window-titlebar,
.layout-split .window-titlebar {
  border-left: var(--edge-wayfinding) solid transparent;
}

.desktop-window.is-active .window-titlebar {
  border-bottom-color: var(--signal);
}

.layout-focus.is-active .window-titlebar,
.layout-split.is-active .window-titlebar {
  border-left-color: var(--signal);
}

.window-identity {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  padding: 0 var(--space-3);
}

.window-code {
  color: var(--attention);
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.06em;
}

.window-title {
  overflow: hidden;
  color: var(--paper);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.window-position {
  position: relative;
  display: flex;
  align-items: stretch;
  margin-left: auto;
}

.position-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 2px);
  z-index: 4;
  display: flex;
  flex-direction: column;
  min-width: 13rem;
  border: 1px solid var(--line-strong);
  background: var(--ink-deep);
  box-shadow: var(--shadow-sm);
}

.position-option {
  min-height: var(--control-h-md);
  justify-content: flex-start;
  padding: 0 var(--space-3);
  border: 0;
  border-bottom: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper);
  font-size: 0.76rem;
  font-weight: 600;
  text-align: left;
}

.position-option:last-child {
  border-bottom: 0;
}

.position-option:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

.window-controls {
  display: flex;
  align-items: stretch;
}

.window-control {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--control-h-lg);
  min-height: var(--control-h-lg);
  padding: 0 var(--space-2);
  border: 0;
  border-left: 1px solid var(--line-dark);
  border-radius: 0;
  background: transparent;
  color: var(--paper-muted);
}

.window-control-text {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.window-control svg {
  width: 0.85rem;
  height: 0.85rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.4;
}

.window-control:hover {
  background: var(--ink-deep);
  color: var(--paper);
}

.desktop-window-body {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: var(--ink);
}

.window-resize {
  position: absolute;
  right: 0;
  bottom: 0;
  z-index: 3;
  width: 1.25rem;
  height: 1.25rem;
  cursor: nwse-resize;
  touch-action: none;
}

.window-resize::after {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 0.9rem;
  height: 0.9rem;
  border-right: 1px solid var(--line-strong);
  border-bottom: 1px solid var(--line-strong);
}

@media (prefers-reduced-motion: reduce) {
  .desktop-window {
    transition: none;
  }
}
</style>
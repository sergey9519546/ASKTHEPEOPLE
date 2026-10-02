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

      <div v-if="mode === 'free'" ref="positionWrap" class="window-position">
        <button
          ref="positionTrigger"
          class="window-control window-control-text"
          type="button"
          :aria-expanded="positionOpen"
          aria-haspopup="menu"
          :aria-controls="positionMenuId"
          :aria-label="`Placement options for ${app.title}`"
          @click.stop="togglePosition"
          @keydown="onPositionTriggerKeydown"
        >
          Placement
        </button>
        <div
          v-if="positionOpen"
          :id="positionMenuId"
          class="position-menu"
          role="menu"
          aria-orientation="vertical"
          @keydown="onPositionMenuKeydown"
        >
          <button
            v-for="(option, index) in POSITION_OPTIONS"
            :id="`${positionMenuId}-${option.id}`"
            :key="option.id"
            :ref="(el) => setPositionRef(el, index)"
            class="position-option"
            type="button"
            role="menuitem"
            :tabindex="index === positionIndex ? 0 : -1"
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
      :aria-valuemin="MIN_PANEL_W"
      :aria-valuemax="MAX_PANEL_W"
      :aria-valuenow="panelWidth"
      :aria-valuetext="panelSizeText"
      tabindex="0"
      @pointerdown.prevent="startResize"
      @keydown="onResizeKeydown"
    ></div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, provide, ref, watch } from "vue";
import {
  appById,
  activeKey,
  closeWindow,
  focusWindow,
  updateGeometry,
  windows,
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

/**
 * Placement menu.
 *
 * `role="menu"` is a promise. The previous markup declared a menu and shipped
 * none of the menu behaviour: no roving tabindex, no arrow movement, no Home or
 * End, no Escape, and no return of focus to the trigger. A keyboard user
 * arriving at that control landed inside a menu with no way to move through it
 * and no way out of it. Everything below exists to make the declared role true.
 */
const positionOpen = ref(false);
const positionIndex = ref(0);
const positionTrigger = ref(null);
const positionWrap = ref(null);

const positionMenuId = computed(() => `placement-menu-${props.win.key}`);

const POSITION_OPTIONS = [
  { id: "fill", label: "Fill the workspace" },
  { id: "centre", label: "Centre in the workspace" },
  { id: "left", label: "Left half" },
  { id: "right", label: "Right half" },
];

// Collected through a callback ref rather than a v-for string ref so each item
// is addressable by index the moment the menu opens, without waiting on the
// array to settle.
let positionEls = [];
function setPositionRef(el, index) {
  if (el) positionEls[index] = el;
  else delete positionEls[index];
}

/**
 * Free-panel geometry bounds, declared once.
 *
 * The floors are the numbers the keyboard and pointer paths already clamped to.
 * The ceilings are the free-panel maximums the stylesheet already implies -
 * `min(72rem, ...)` across, `min(48rem, ...)` down - so a floating panel can
 * never be larger than the workspace the "Fill" option would give it.
 *
 * The split publishes these same constants as `aria-valuemin` / `aria-valuemax`.
 * A second hard-coded set beside them would be free to drift from the
 * arithmetic it describes, which is the whole defect being closed here.
 */
const MIN_PANEL_W = 320;
const MIN_PANEL_H = 240;
const MAX_PANEL_W = 72 * 16;
const MAX_PANEL_H = 48 * 16;
const DEFAULT_PANEL_W = 560;
const DEFAULT_PANEL_H = 360;
const RESIZE_STEP = 16;
const RESIZE_STEP_LARGE = 48;

/**
 * Geometry is read back through the store rather than off the prop.
 *
 * `updateGeometry` writes to the reactive record inside `windows`, so a size
 * read off a plain prop object can describe geometry the panel no longer has -
 * which for a splitter means `aria-valuenow` quietly lying about its own size.
 */
const liveWin = computed(
  () => windows.value.find((entry) => entry.key === props.win.key) || props.win,
);

const panelWidth = computed(() =>
  panelSize(liveWin.value.w, DEFAULT_PANEL_W, MIN_PANEL_W, MAX_PANEL_W),
);
const panelHeight = computed(() =>
  panelSize(liveWin.value.h, DEFAULT_PANEL_H, MIN_PANEL_H, MAX_PANEL_H),
);

// An unset dimension means the stylesheet default applies, so the reported size
// is the default rather than zero. Values are rounded and bounded so
// `aria-valuenow` can never fall outside the min and max it declares.
function panelSize(value, fallback, floor, ceiling) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return Math.min(ceiling, Math.max(floor, Math.round(parsed)));
}

// A splitter's value is one number, but this control moves both axes, so the
// readable form names the driven axis first and the other one alongside it.
const panelSizeText = computed(
  () => `${panelWidth.value} by ${panelHeight.value} pixels`,
);

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

/**
 * Choosing a placement closes the menu and hands focus back to the trigger. A
 * menu that closes without restoring focus drops a keyboard user at the top of
 * the document, which is a worse outcome than the placement they chose not
 * having taken effect.
 */
function applyPosition(id) {
  closePosition(true);
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

function focusPositionItem(index) {
  const total = POSITION_OPTIONS.length;
  if (total === 0) return;
  // Menus wrap. Stopping at the ends would make the last item a dead end.
  const bounded = (index + total) % total;
  positionIndex.value = bounded;
  nextTick(() => {
    const el = positionEls[bounded];
    if (el && typeof el.focus === "function") el.focus();
  });
}

function openPosition(index = 0) {
  positionOpen.value = true;
  focusPositionItem(index);
}

function closePosition(returnFocus) {
  positionOpen.value = false;
  if (!returnFocus) return;
  nextTick(() => {
    const el = positionTrigger.value;
    if (el && typeof el.focus === "function") el.focus();
  });
}

function togglePosition() {
  if (positionOpen.value) closePosition(false);
  else openPosition(0);
}

/**
 * The menu button half of the WAI-ARIA menu-button pattern.
 *
 * Enter and Space are handled here and default-prevented rather than left to the
 * button's own activation, because native activation also fires `click`; the
 * trigger's click handler toggles, so letting both run would open the menu and
 * immediately close it again.
 */
function onPositionTriggerKeydown(event) {
  switch (event.key) {
    case "ArrowDown":
    case "Enter":
    case " ":
    case "Spacebar":
      event.preventDefault();
      event.stopPropagation();
      openPosition(0);
      break;
    case "ArrowUp":
      event.preventDefault();
      event.stopPropagation();
      openPosition(POSITION_OPTIONS.length - 1);
      break;
    case "Escape":
      if (!positionOpen.value) return;
      event.preventDefault();
      event.stopPropagation();
      closePosition(false);
      break;
    default:
      break;
  }
}

/**
 * The menu half of the pattern. `Tab` closes instead of moving focus itself: a
 * menu is not a tab container, so it must not intercept traversal - it only
 * gets to stop being open while focus continues on its way.
 */
function onPositionMenuKeydown(event) {
  switch (event.key) {
    case "ArrowDown":
      event.preventDefault();
      focusPositionItem(positionIndex.value + 1);
      break;
    case "ArrowUp":
      event.preventDefault();
      focusPositionItem(positionIndex.value - 1);
      break;
    case "Home":
      event.preventDefault();
      focusPositionItem(0);
      break;
    case "End":
      event.preventDefault();
      focusPositionItem(POSITION_OPTIONS.length - 1);
      break;
    case "Escape":
      event.preventDefault();
      event.stopPropagation();
      closePosition(true);
      break;
    case "Tab":
      closePosition(false);
      break;
    default:
      break;
  }
}

/**
 * Clicking away dismisses the menu.
 *
 * The listener exists only while the menu is open, so a closed placement
 * control costs nothing, and it is removed on unmount so a torn-down panel
 * cannot leave a handler bound to the document. Capture is used so the check
 * runs before anything the click would otherwise activate.
 */
function onDocumentPointerDown(event) {
  const wrap = positionWrap.value;
  if (wrap && event.target instanceof Node && wrap.contains(event.target)) return;
  closePosition(false);
}

watch(positionOpen, (open) => {
  if (typeof document === "undefined") return;
  if (open) document.addEventListener("pointerdown", onDocumentPointerDown, true);
  else document.removeEventListener("pointerdown", onDocumentPointerDown, true);
});

onBeforeUnmount(() => {
  if (typeof document === "undefined") return;
  document.removeEventListener("pointerdown", onDocumentPointerDown, true);
});

/**
 * Dragging Movements (WCAG 2.2 SC 2.5.7) requires a single-pointer, non-drag
 * alternative - a modifier held while arrowing does not count, which is why the
 * grip is a real focusable separator with its own arrow-key behaviour rather
 * than a passive corner graphic.
 *
 * A focusable separator is a window splitter, so it must also state its size.
 * Both paths bound the same way the published `aria-valuemin` / `aria-valuemax`
 * do, which is what stops `aria-valuenow` from ever describing a size outside
 * the range the control claims.
 */
function onResizeKeydown(event) {
  const step = event.shiftKey ? RESIZE_STEP_LARGE : RESIZE_STEP;
  const next = {};
  if (event.key === "ArrowRight") {
    next.w = Math.min(MAX_PANEL_W, panelWidth.value + step);
  } else if (event.key === "ArrowLeft") {
    next.w = Math.max(MIN_PANEL_W, panelWidth.value - step);
  } else if (event.key === "ArrowDown") {
    next.h = Math.min(MAX_PANEL_H, panelHeight.value + step);
  } else if (event.key === "ArrowUp") {
    next.h = Math.max(MIN_PANEL_H, panelHeight.value - step);
  } else return;
  event.preventDefault();
  updateGeometry(props.win.key, next);
}

// Set for the duration of a pointer drag so `onBeforeUnmount` can release the
// listeners even when the panel is torn down mid-gesture.
let activeDragCleanup = null;

onBeforeUnmount(() => {
  if (activeDragCleanup) activeDragCleanup();
});

function startResize(event) {
  if (event.button !== 0) return;
  const originW = panelWidth.value;
  const originH = panelHeight.value;
  const startX = event.clientX;
  const startY = event.clientY;

  const onMove = (moveEvent) => {
    updateGeometry(props.win.key, {
      w: Math.min(
        MAX_PANEL_W,
        Math.max(MIN_PANEL_W, originW + moveEvent.clientX - startX),
      ),
      h: Math.min(
        MAX_PANEL_H,
        Math.max(MIN_PANEL_H, originH + moveEvent.clientY - startY),
      ),
    });
  };
  // Teardown has to be reachable from more than the happy path. Unmounting
  // mid-drag, or releasing the pointer outside the window, both skipped the
  // removal and left two window-level listeners alive for the life of the tab.
  const detach = () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
    window.removeEventListener("pointercancel", detach);
    activeDragCleanup = null;
  };
  const onUp = detach;
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
  window.addEventListener("pointercancel", detach);
  activeDragCleanup = detach;
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
  border-right: 1px solid var(--line-structural);
  overflow: hidden;
}

.layout-free {
  position: absolute;
  border: 1px solid var(--line-structural);
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
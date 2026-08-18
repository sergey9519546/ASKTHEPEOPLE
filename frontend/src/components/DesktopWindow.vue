<template>
  <section
    v-show="!win.minimized"
    class="desktop-window"
    :class="{
      'is-active': isActive,
      'is-maximized': win.maximized,
      'is-tiled': tiled,
    }"
    :style="windowStyle"
    :aria-label="`${app.title} window`"
    role="region"
    @pointerdown="raise"
  >
    <header class="window-titlebar" @pointerdown="startDrag">
      <div class="window-identity">
        <span class="window-code" aria-hidden="true">{{ app.code }}</span>
        <h2 class="window-title">{{ app.title }}</h2>
      </div>
      <div class="window-controls">
        <button
          type="button"
          class="window-control"
          data-window-control
          :aria-label="`Minimize ${app.title}`"
          title="Minimize"
          @click.stop="minimizeWindow(win.key)"
        >
          <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M1 11h10" /></svg>
        </button>
        <button
          type="button"
          class="window-control"
          data-window-control
          :aria-label="win.maximized ? `Restore ${app.title}` : `Maximize ${app.title}`"
          :title="win.maximized ? 'Restore' : 'Maximize'"
          @click.stop="toggleMaximize(win.key)"
        >
          <svg v-if="win.maximized" viewBox="0 0 12 12" aria-hidden="true">
            <path d="M3 3h6v6H3zM4 1h7v7" />
          </svg>
          <svg v-else viewBox="0 0 12 12" aria-hidden="true">
            <path d="M1 1h10v10H1z" />
          </svg>
        </button>
        <button
          type="button"
          class="window-control window-control-close"
          data-window-control
          :aria-label="`Close ${app.title}`"
          title="Close"
          @click.stop="closeWindow(win.key)"
        >
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M1 1l10 10M11 1L1 11" />
          </svg>
        </button>
      </div>
    </header>

    <div class="desktop-window-body">
      <component :is="app.component" />
    </div>

    <div
      v-if="!tiled && !locked && !win.maximized"
      class="window-resize"
      aria-hidden="true"
      @pointerdown.prevent="startResize"
    ></div>
  </section>
</template>

<script setup>
import { computed, provide } from "vue";
import { appById, activeKey, closeWindow, focusWindow, minimizeWindow, toggleMaximize, updateGeometry } from "../composables/useDesktop.js";
import { windowContextKey } from "../composables/useWindowContext.js";

const props = defineProps({
  win: { type: Object, required: true },
  tiled: { type: Boolean, default: false },
  locked: { type: Boolean, default: false },
});

const app = computed(() => appById(props.win.appId) || { title: "Workspace", code: "" });
const isActive = computed(() => activeKey.value === props.win.key);

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
  if (props.tiled || win.maximized) return {};
  const width = Number.isFinite(win.w) && win.w ? `${win.w}px` : "min(72rem, calc(100% - 5rem))";
  const height = Number.isFinite(win.h) && win.h ? `${win.h}px` : "min(48rem, calc(100% - 5rem))";
  const left = Number.isFinite(win.x) ? `${win.x}px` : "3.5rem";
  const top = Number.isFinite(win.y) ? `${win.y}px` : "3.5rem";
  return { left, top, width, height, zIndex: win.z };
});

function raise() {
  if (!isActive.value) focusWindow(props.win.key);
}

function startDrag(event) {
  if (event.button !== 0) return;
  if (event.target.closest("[data-window-control]")) return;
  if (props.tiled || props.locked || props.win.maximized) return;

  const originX = props.win.x ?? 56;
  const originY = props.win.y ?? 56;
  const startX = event.clientX;
  const startY = event.clientY;

  const onMove = (moveEvent) => {
    updateGeometry(props.win.key, {
      x: Math.max(0, originX + moveEvent.clientX - startX),
      y: Math.max(0, originY + moveEvent.clientY - startY),
    });
  };
  const onUp = () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}

function startResize(event) {
  if (event.button !== 0 || props.locked) return;
  const originW = props.win.w;
  const originH = props.win.h;
  const startX = event.clientX;
  const startY = event.clientY;

  const onMove = (moveEvent) => {
    updateGeometry(props.win.key, {
      w: Math.max(20, (originW || 560) + moveEvent.clientX - startX),
      h: Math.max(12, (originH || 360) + moveEvent.clientY - startY),
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
  position: absolute;
  display: flex;
  flex-direction: column;
  min-width: 20rem;
  border: 1px solid var(--line-dark);
  background: var(--ink);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: box-shadow var(--duration-quick) var(--ease-out);
}

.desktop-window.is-active {
  border-color: var(--signal);
  box-shadow: 0.7rem 0.7rem 0 rgba(0, 0, 0, 0.62);
}

.desktop-window.is-maximized {
  inset: 0;
  width: auto !important;
  height: auto !important;
}

.desktop-window.is-tiled {
  position: relative;
  inset: auto;
  left: auto !important;
  top: auto !important;
  width: auto !important;
  height: auto !important;
}

.window-titlebar {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  min-height: 2.5rem;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-deep);
  cursor: default;
  user-select: none;
  touch-action: none;
}

.desktop-window.is-active .window-titlebar {
  background: var(--ink-raised);
  border-bottom-color: var(--signal);
}

.window-identity {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-width: 0;
  padding: 0.4rem 0.85rem;
}

.window-code {
  color: var(--attention);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.window-title {
  margin: 0;
  overflow: hidden;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-transform: uppercase;
}

.window-controls {
  display: flex;
  align-items: stretch;
}

.window-control {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.9rem;
  padding: 0;
  border: 0;
  border-left: 1px solid var(--line-dark);
  border-radius: 0;
  background: transparent;
  color: var(--paper-muted);
}

.window-control svg {
  width: 0.9rem;
  height: 0.9rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.4;
}

.window-control:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

.window-control-close:hover {
  background: var(--signal);
  color: var(--ink);
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
  border-right: 1px solid var(--line-dark);
  border-bottom: 1px solid var(--line-dark);
}

@media (prefers-reduced-motion: reduce) {
  .desktop-window {
    transition: none;
  }
}
</style>

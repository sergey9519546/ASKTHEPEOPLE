<template>
  <footer class="desktop-taskbar">
    <div class="taskbar-windows" role="tablist" aria-label="Open windows">
      <button
        v-for="win in windows"
        :key="win.key"
        type="button"
        role="tab"
        class="taskbar-window"
        :class="{ 'is-active': win.key === activeKey, 'is-minimized': win.minimized }"
        :aria-selected="win.key === activeKey"
        @click="focusWindow(win.key)"
      >
        <span class="taskbar-code" aria-hidden="true">{{ codeFor(win) }}</span>
        <span class="taskbar-title">{{ titleFor(win) }}</span>
      </button>

      <p v-if="windows.length === 0" class="taskbar-empty">
        No windows open
      </p>
    </div>

    <div class="taskbar-actions">
      <button
        type="button"
        class="taskbar-action"
        :aria-pressed="layoutMode === 'tiled'"
        @click="tileWindows"
      >
        {{ layoutMode === "tiled" ? "Free layout" : "Tile windows" }}
      </button>
      <button
        type="button"
        class="taskbar-action"
        :disabled="windows.length === 0"
        @click="closeAllWindows"
      >
        Close all
      </button>
    </div>
  </footer>
</template>

<script setup>
import {
  activeKey,
  appById,
  closeAllWindows,
  focusWindow,
  layoutMode,
  tileWindows,
  windows,
} from "../composables/useDesktop.js";

const titleFor = (win) => appById(win.appId)?.title || "Workspace";
const codeFor = (win) => appById(win.appId)?.code || "";
</script>

<style scoped>
.desktop-taskbar {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 2.35rem;
  padding: 0.3rem 0.5rem;
  border-top: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.taskbar-windows {
  display: flex;
  align-items: stretch;
  gap: 0.3rem;
  min-width: 0;
  overflow-x: auto;
}

.taskbar-window {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  max-width: 16rem;
  padding: 0.25rem 0.65rem;
  border: 1px solid var(--line-dark);
  border-radius: 0;
  background: var(--ink-soft);
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
}

.taskbar-window.is-active {
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.taskbar-window.is-minimized {
  opacity: 0.55;
}

.taskbar-code {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  font-weight: 700;
}

.taskbar-title {
  overflow: hidden;
  text-overflow: ellipsis;
}

.taskbar-empty {
  margin: 0;
  padding: 0.3rem 0.5rem;
  color: var(--paper-dim);
  font-size: 0.7rem;
}

.taskbar-actions {
  display: flex;
  align-items: stretch;
  gap: 0.3rem;
  flex-shrink: 0;
}

.taskbar-action {
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--line-dark);
  border-radius: 0;
  background: transparent;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.68rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.taskbar-action:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

@media (max-width: 620px) {
  .taskbar-title {
    display: none;
  }

  .taskbar-actions {
    display: none;
  }
}
</style>

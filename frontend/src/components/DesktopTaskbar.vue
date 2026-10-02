<template>
  <footer class="panel-switcher desktop-taskbar">
    <div
      v-if="panels.length"
      class="switcher-tabs"
      role="tablist"
      aria-label="Open panels"
      @keydown="onTablistKeydown"
    >
      <button
        v-for="(panel, index) in panels"
        :id="`panel-tab-${panel.key}`"
        :key="panel.key"
        :ref="(el) => setTabRef(el, index)"
        type="button"
        role="tab"
        class="switcher-tab"
        :class="{ 'is-active': isSelected(panel) }"
        :aria-selected="isSelected(panel)"
        :aria-controls="`panel-body-${panel.key}`"
        :tabindex="isSelected(panel) ? 0 : -1"
        @click="focusPanel(panel.key)"
      >
        <span class="tab-index" aria-hidden="true">{{ index + 1 }}</span>
        <span class="tab-title">{{ titleFor(panel) }}</span>
        <span class="tab-code" aria-hidden="true">{{ codeFor(panel) }}</span>
      </button>
    </div>

    <p v-else class="switcher-empty">
      No panel open. The decision surface always stays available.
    </p>

    <div class="switcher-actions">
      <p class="switcher-layout" aria-live="polite">
        <span class="switcher-layout-label">Layout</span>
        <span class="switcher-layout-value">{{ LAYOUT_LABEL[layoutMode] }}</span>
      </p>
      <button class="switcher-action u-target" type="button" @click="cycleLayoutMode">
        Change layout
      </button>
      <button
        class="switcher-action u-target"
        type="button"
        :disabled="!panels.length"
        @click="closeAllWindows"
      >
        Close all panels
      </button>
    </div>
  </footer>
</template>

<script setup>
import { nextTick } from "vue";
import {
  LAYOUT_MODES,
  activeKey,
  appById,
  closeAllWindows,
  closeWindow,
  cycleLayoutMode,
  focusWindow,
  layoutMode,
  windows,
} from "../composables/useDesktop.js";

/**
 * The switcher is a tablist because in the default layout it really is one:
 * several open panels over a single canvas, one visible at a time, sharing one
 * workspace context. That relationship is exactly what the tab role describes.
 *
 * The previous implementation used `role="tablist"` but implemented none of the
 * pattern - no `aria-controls`, no matching tabpanel, no roving tabindex, and no
 * arrow-key movement - which left assistive technology with the semantics of a
 * tab interface and none of the behaviour. It is now a real tablist.
 *
 * Activation is manual rather than automatic: a panel can be running a polling
 * loop or a heavy render, and auto-switching on focus would make arrowing past
 * it expensive. Arrow keys move focus; Enter or Space activates.
 */
const props = defineProps({
  panels: { type: Array, default: () => [] },
});

const LAYOUT_LABEL = {
  focus: "One at a time",
  split: "Side by side",
  free: "Floating",
};

void LAYOUT_MODES;

// A tablist with no tab in the tab order is a keyboard dead end. The selected
// tab owns the tab stop, and when nothing is selected the first panel does.
const isSelected = (panel) =>
  props.panels.some((entry) => entry.key === activeKey.value)
    ? panel.key === activeKey.value
    : props.panels[0]?.key === panel.key;

// Collected through a callback ref rather than the v-for string ref so the
// elements are addressable by index without waiting for array reactivity.
let tabEls = [];
function setTabRef(el, index) {
  if (el) tabEls[index] = el;
  else delete tabEls[index];
}

const titleFor = (panel) => appById(panel.appId)?.title || "Panel";
const codeFor = (panel) => appById(panel.appId)?.code || "";

function focusPanel(key) {
  focusWindow(key);
}

function focusTab(index) {
  const bounded = (index + props.panels.length) % props.panels.length;
  if (!props.panels[bounded]) return;
  nextTick(() => {
    const el = tabEls[bounded];
    if (el && typeof el.focus === "function") el.focus();
  });
}

function onTablistKeydown(event) {
  const total = props.panels.length;
  if (total === 0) return;
  const index = props.panels.findIndex((panel) => panel.key === activeKey.value);
  const current = index === -1 ? 0 : index;

  switch (event.key) {
    case "ArrowRight":
      event.preventDefault();
      focusTab(current + 1);
      break;
    case "ArrowLeft":
      event.preventDefault();
      focusTab(current - 1);
      break;
    case "Home":
      event.preventDefault();
      focusTab(0);
      break;
    case "End":
      event.preventDefault();
      focusTab(total - 1);
      break;
    case "Delete":
    case "Backspace": {
      const panel = props.panels[current];
      if (!panel) return;
      event.preventDefault();
      closePanel(panel.key);
      break;
    }
    default:
      break;
  }
}

// Deleting a tab removes exactly that panel and moves focus to its neighbour,
// which is the behaviour the tab pattern specifies. It deliberately does not
// close every panel: the tab pattern's Delete key means "close this", and
// destroying unrelated open work would be an unrecoverable surprise.
function closePanel(key) {
  const index = props.panels.findIndex((panel) => panel.key === key);
  closeWindow(key);
  const remaining = props.panels.length - 1;
  if (remaining > 0) focusTab(Math.min(index > 0 ? index - 1 : 0, remaining - 1));
}

void windows;
</script>

<style scoped>
.panel-switcher {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: var(--band-switcher);
  padding: 0 var(--space-3);
  border-top: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.switcher-tabs {
  display: flex;
  align-items: stretch;
  gap: var(--space-1);
  min-width: 0;
  overflow-x: auto;
}

.switcher-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  max-width: 15rem;
  min-height: var(--control-h-sm);
  padding: 0 var(--space-3);
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--paper-muted);
  white-space: nowrap;
}

.switcher-tab:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

.switcher-tab.is-active {
  border-bottom-color: var(--signal);
  background: var(--ink-raised);
  color: var(--paper);
}

.tab-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.15rem;
  height: 1.15rem;
  background: var(--ink-deep);
  color: var(--paper-muted);
  font-size: 0.6rem;
  font-weight: 700;
}

.switcher-tab.is-active .tab-index {
  background: var(--signal);
  color: var(--ink);
}

.tab-title {
  overflow: hidden;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-overflow: ellipsis;
  text-transform: uppercase;
}

.tab-code {
  color: var(--paper-dim);
  font-size: 0.58rem;
  letter-spacing: 0.06em;
}

.switcher-empty {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  color: var(--paper-dim);
  font-size: 0.72rem;
  align-self: center;
}

.switcher-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.switcher-layout {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-2);
  margin: 0;
  padding-right: var(--space-2);
}

.switcher-layout-label {
  color: var(--paper-muted);
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.switcher-layout-value {
  color: var(--paper);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.switcher-action {
  min-height: var(--control-h-sm);
  padding: 0 var(--space-3);
  border: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper-muted);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
}

.switcher-action:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

@media (max-width: 720px) {
  .switcher-layout,
  .tab-code {
    display: none;
  }
}
</style>
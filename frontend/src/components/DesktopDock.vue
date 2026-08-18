<template>
  <nav class="desktop-dock" :class="{ "is-collapsed": props.collapsed }" aria-label="Workspace launcher" @click.self="emit("toggle")">
    <div class="dock-heading">
      <h3 class="dock-heading-text">Journey</h3>
      <span class="dock-heading-note">Sequence only</span>
    </div>

    <ul class="dock-apps" role="list">
      <li v-for="app in DESKTOP_APPS" :key="app.id">
        <button
          type="button"
          class="dock-app"
          :class="{
            'is-active': isActive(app),
            'is-open': isOpen(app),
            'is-unavailable': !isAvailable(app),
          }"
          :aria-current="isActive(app) ? 'step' : undefined"
          :aria-disabled="!isAvailable(app) && !isOpen(app)"
          :aria-expanded="isOpen(app)"
          :title="availabilityHint(app)"
          @click="launch(app)"
        >
          <span class="dock-code" aria-hidden="true">{{ app.code }}</span>
          <span class="dock-title">{{ app.title }}</span>
          <span v-if="isOpen(app)" class="dock-state" aria-hidden="true">
            {{ isActive(app) ? "ACTIVE" : "OPEN" }}
          </span>
          <span v-else-if="isAvailable(app)" class="dock-state dock-state-ready" aria-hidden="true">
            OPEN
          </span>
        </button>
      </li>
    </ul>

    <div class="dock-heading dock-heading-system">
      <h3 class="dock-heading-text">System</h3>
    </div>

    <ul class="dock-apps dock-apps-system" role="list">
      <li>
        <button type="button" class="dock-app" @click="openSettings">
          <span class="dock-code" aria-hidden="true">CFG</span>
          <span class="dock-title">Model settings</span>
        </button>
      </li>
      <li>
        <button type="button" class="dock-app" @click="startOver">
          <span class="dock-code" aria-hidden="true">RST</span>
          <span class="dock-title">Start over</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { useRouter } from "vue-router";
import {
  activeKey,
  DESKTOP_APPS,
  focusWindow,
  launchRouteFor,
  openApp,
  windowForApp,
} from "../composables/useDesktop.js";
import { openSettings } from "../composables/useCommandPalette.js";
import { clearState } from "../composables/useWorkspaceState.js";
import { toast } from "../utils/toast.js";

const router = useRouter();
const props = defineProps({ collapsed: Boolean });
const emit = defineEmits(["toggle"]);

const isOpen = (app) => Boolean(windowForApp(app.id));
const isActive = (app) => {
  const win = windowForApp(app.id);
  return Boolean(win && activeKey.value === win.key);
};
const isAvailable = (app) => Boolean(launchRouteFor(app.id));

function availabilityHint(app) {
  if (isOpen(app)) return `Open ${app.title}`;
  if (isAvailable(app)) return `Open ${app.title}`;
  return `${app.title} is available after the earlier steps`;
}

function launch(app) {
  const win = windowForApp(app.id);
  if (win) {
    focusWindow(win.key);
    return;
  }
  const route = launchRouteFor(app.id);
  if (!route) {
    toast.warning(
      "Complete the earlier journey steps first.",
      `${app.title} is not ready`,
    );
    return;
  }
  openApp(app.id, route);
}

function startOver() {
  clearState();
  windowForApp("decision") || openApp("decision", { name: "Home" });
  router.replace({ name: "Home" });
  toast.info("Workspace reset. State a new decision.", "Start over");
}
</script>

<style scoped>
.desktop-dock.is-collapsed {
  width: var(--dock-collapsed-width, 3rem);
  min-width: 3rem;
  overflow: hidden;
}
.desktop-dock.is-collapsed .dock-heading,
.desktop-dock.is-collapsed .dock-heading-system,
.desktop-dock.is-collapsed .dock-title,
.desktop-dock.is-collapsed .dock-state,
.desktop-dock.is-collapsed .dock-heading-note {
  display: none;
}
.desktop-dock.is-collapsed .dock-app {
  grid-template-columns: 2.6rem;
  justify-content: center;
  border-left: 0;
  padding: var(--space-1);
}
.desktop-dock.is-collapsed .dock-code {
  font-size: 0.55rem;
  opacity: 1;
  color: var(--attention) !important;
}
.desktop-dock {
  display: flex;
  flex-direction: column;
  width: var(--dock-width);
  min-width: var(--dock-width);
  overflow-y: auto;
  border-right: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.dock-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4) var(--space-1);
  border-bottom: 1px solid var(--line-dark);
}

.dock-heading-system {
  border-top: 1px solid var(--line-dark);
}

.dock-heading-text {
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.dock-heading-note {
  color: var(--paper-dim);
  font-family: var(--font-mono);
  font-size: 0.58rem;
  letter-spacing: 0.04em;
}

.dock-apps {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: var(--space-1) 0;
  list-style: none;
}

.dock-apps-system {
  border-bottom: 1px solid var(--line-dark);
}

.dock-app {
  display: grid;
  grid-template-columns: 2.6rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-height: var(--space-7);
  padding: var(--space-1) var(--space-4);
  border: 0;
  border-left: 3px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--paper-muted);
  text-align: left;
}

.dock-app:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

.dock-app.is-active {
  border-left-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.dock-app.is-open:not(.is-active) {
  border-left-color: var(--attention);
  background: var(--ink-soft);
  color: var(--paper);
}

.dock-app:disabled,
.dock-app.is-unavailable:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.dock-app:disabled:hover {
  background: transparent;
  color: var(--paper-muted);
}

.dock-code {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: inherit;
  opacity: 0.85;
}

.dock-app.is-active .dock-code {
  color: var(--ink);
}

.dock-title {
  overflow: hidden;
  font-family: var(--font-display);
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-transform: uppercase;
}

.dock-state {
  font-family: var(--font-mono);
  font-size: 0.56rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  opacity: 0.85;
}

.dock-state-ready {
  color: var(--paper-dim);
}

@media (max-width: 860px) {
  .desktop-dock.is-collapsed {
  width: var(--dock-collapsed-width, 3rem);
  min-width: 3rem;
  overflow: hidden;
}
.desktop-dock.is-collapsed .dock-heading,
.desktop-dock.is-collapsed .dock-heading-system,
.desktop-dock.is-collapsed .dock-title,
.desktop-dock.is-collapsed .dock-state,
.desktop-dock.is-collapsed .dock-heading-note {
  display: none;
}
.desktop-dock.is-collapsed .dock-app {
  grid-template-columns: 2.6rem;
  justify-content: center;
  border-left: 0;
  padding: var(--space-1);
}
.desktop-dock.is-collapsed .dock-code {
  font-size: 0.55rem;
  opacity: 1;
  color: var(--attention) !important;
}
.desktop-dock {
    flex-direction: row;
    width: 100%;
    min-width: 0;
    overflow-x: auto;
    overflow-y: hidden;
    border-right: 0;
    border-bottom: 1px solid var(--line-dark);
  }

  .dock-heading,
  .dock-state {
    display: none;
  }

  .dock-apps,
  .dock-apps-system {
    flex-direction: row;
    padding: var(--space-1) var(--space-1);
    border: 0;
  }

  .dock-app {
    grid-template-columns: auto;
    width: auto;
    min-height: var(--space-6);
    padding: var(--space-1) var(--space-2);
    border-left: 0;
    border-bottom: 2px solid transparent;
  }

  .dock-app.is-active {
    border-bottom-color: var(--signal);
    background: var(--signal);
  }

  .dock-title {
    font-size: var(--text-sm);
  }
}
</style>


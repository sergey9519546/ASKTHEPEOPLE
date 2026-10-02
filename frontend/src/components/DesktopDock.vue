<template>
  <nav
    class="journey-spine desktop-dock"
    :class="{ 'is-collapsed': collapsed }"
    aria-label="Journey"
  >
    <div class="spine-heading">
      <h2 class="spine-heading-text">Journey</h2>
      <button
        class="spine-toggle u-target"
        type="button"
        :aria-expanded="!collapsed"
        aria-controls="journey-spine-list"
        :aria-label="collapsed ? 'Expand the journey spine' : 'Collapse the journey spine'"
        @click="emit('toggle')"
      >
        <span aria-hidden="true">{{ collapsed ? ">" : "<" }}</span>
      </button>
    </div>
    <p v-if="!collapsed" class="spine-note">
      Six steps in sequence. Spacing shows order only, not time or likelihood.
    </p>

    <ol id="journey-spine-list" class="spine-steps" :class="{ 'is-compact': collapsed }">
      <li v-for="entry in journey" :key="entry.id" class="spine-step">
        <button
          type="button"
          class="spine-entry"
          :class="[
            `is-${entry.status}`,
            { 'is-open': entry.open },
          ]"
          :aria-current="entry.status === 'current' ? 'step' : undefined"
          :aria-disabled="entry.status === 'locked'"
          :title="hint(entry)"
          @click="launch(entry)"
        >
          <span class="spine-index" aria-hidden="true">
            {{ String(entry.step).padStart(2, "0") }}
          </span>
          <span class="spine-text">
            <span class="spine-title">{{ entry.title }}</span>
            <span v-if="!collapsed" class="spine-outcome">{{ entry.outcome }}</span>
          </span>
          <span v-if="!collapsed" class="spine-state" aria-hidden="true">
            {{ STATE_LABEL[entry.status] }}
          </span>
        </button>
      </li>
    </ol>

    <div class="spine-system">
      <h2 class="spine-heading-text">System</h2>
      <button class="spine-entry is-quiet" type="button" @click="openSettings">
        <span class="spine-index" aria-hidden="true">CFG</span>
        <span class="spine-text">
          <span class="spine-title">Model settings</span>
        </span>
      </button>
      <button class="spine-entry is-quiet is-danger" type="button" @click="startOver">
        <span class="spine-index" aria-hidden="true">RST</span>
        <span class="spine-text">
          <span class="spine-title">Start over</span>
        </span>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import {
  DESKTOP_APPS,
  JOURNEY_TOTAL,
  focusWindow,
  journeyState,
  launchRouteFor,
  openApp,
  windowForApp,
} from "../composables/useDesktop.js";
import { openSettings } from "../composables/useCommandPalette.js";
import { clearState } from "../composables/useWorkspaceState.js";
import { toast } from "../utils/toast.js";

/**
 * The journey spine is the shell's only journey navigation.
 *
 * It replaces a dock that shipped collapsed by default, which meant a first-time
 * user saw a 3rem column of two-letter codes - "D-01 SM-01 A-01" - with no
 * labels and no explanation. Orientation is not a user preference; it is a
 * precondition, so the spine opens expanded and the collapsed state is now the
 * exception the user opts into.
 *
 * Semantics are `nav` + `aria-current="step"`, not a tablist. These are journey
 * positions, not tabs over one canvas, and `aria-current="step"` is the pattern
 * intended for exactly this case; a tablist here would misdescribe the
 * relationship and drag in a keyboard contract that does not apply.
 */
const props = defineProps({ collapsed: Boolean });
const emit = defineEmits(["toggle"]);

const router = useRouter();

const STATE_LABEL = {
  done: "DONE",
  current: "NOW",
  next: "NEXT",
  locked: "LOCKED",
};

const journey = computed(() => journeyState());

/** Why a step cannot be opened, named in terms of the step that unlocks it. */
function hint(entry) {
  if (entry.status === "current") return `Open ${entry.title}`;
  if (entry.open) return `Return to ${entry.title}`;
  if (entry.status === "locked") {
    const gate = DESKTOP_APPS[entry.step - 2];
    return `${entry.title} opens after "${gate ? gate.title : "the earlier step"}"`;
  }
  return `Continue to ${entry.title}`;
}

function launch(entry) {
  const win = windowForApp(entry.id);
  if (win) {
    focusWindow(win.key);
    return;
  }
  const route = launchRouteFor(entry.id);
  if (!route) {
    toast.warning(hint(entry), "That step is not ready");
    return;
  }
  openApp(entry.id, route);
}

function startOver() {
  clearState();
  windowForApp("decision") || openApp("decision", { name: "Home" });
  router.replace({ name: "Home" });
  toast.info("Workspace reset. State a new decision.", "Start over");
}

void JOURNEY_TOTAL;
</script>

<style scoped>
.journey-spine {
  display: flex;
  flex-direction: column;
  width: var(--band-spine);
  min-width: var(--band-spine);
  overflow-y: auto;
  border-right: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.journey-spine.is-collapsed {
  width: var(--band-spine-collapsed);
  min-width: var(--band-spine-collapsed);
}

.spine-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: var(--band-masthead);
  padding: 0 var(--space-2) 0 var(--space-4);
  border-bottom: 1px solid var(--line-dark);
}

.spine-heading-text {
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.journey-spine.is-collapsed .spine-heading {
  justify-content: center;
  padding: 0;
}

.journey-spine.is-collapsed .spine-heading-text {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.spine-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--control-h-md);
  min-height: var(--control-h-md);
  padding: 0;
  border: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper-muted);
  font-family: var(--font-sans);
  font-size: 0.7rem;
}

.spine-toggle:hover {
  border-color: var(--line-strong);
  background: var(--ink-raised);
  color: var(--paper);
}

.spine-note {
  margin: 0;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--line-dark);
  color: var(--paper-dim);
  font-size: 0.64rem;
  line-height: var(--leading-snug);
}

.spine-steps {
  margin: 0;
  padding: var(--space-2) 0;
  list-style: none;
}

.spine-entry {
  display: grid;
  grid-template-columns: 1.9rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-height: var(--control-h-lg);
  padding: var(--space-2) var(--space-4);
  border: 0;
  border-left: var(--edge-wayfinding) solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--paper-muted);
  text-align: left;
}

.journey-spine.is-collapsed .spine-entry {
  grid-template-columns: 1fr;
  justify-items: center;
  padding: var(--space-2) 0;
  border-left: 0;
}

.spine-entry:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

/* Step position is the job of signal red: the current step carries it as a
   left wayfinding edge, and "NOW" as text. Filling the whole row in red would
   make the spine read as a stack of equal alarms. */
.spine-entry.is-current {
  border-left-color: var(--signal);
  background: var(--signal-haze);
  color: var(--paper);
}

.spine-entry.is-done {
  color: var(--paper);
}

.spine-entry.is-locked {
  color: var(--paper-dim);
}

.spine-entry.is-locked:hover {
  background: transparent;
  color: var(--paper-dim);
}

.spine-index {
  color: var(--attention);
  font-family: var(--font-display);
  font-size: 0.78rem;
  line-height: var(--leading-display);
}

.journey-spine.is-collapsed .spine-index {
  font-size: 0.6rem;
}

.spine-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.05rem;
}

.spine-title {
  overflow: hidden;
  color: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: var(--leading-snug);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spine-outcome {
  overflow: hidden;
  color: var(--paper-dim);
  font-size: 0.62rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  line-height: var(--leading-snug);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spine-state {
  color: var(--paper-dim);
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.09em;
}

.spine-entry.is-current .spine-state {
  color: var(--signal);
}

.spine-system {
  margin-top: auto;
  padding-top: var(--space-2);
  border-top: 1px solid var(--line-dark);
}

.spine-system .spine-heading-text {
  display: block;
  padding: var(--space-3) var(--space-4) var(--space-1);
}

.spine-entry.is-quiet .spine-index {
  color: var(--paper-dim);
}

.spine-entry.is-danger:hover {
  border-left-color: var(--error);
  color: var(--error);
}

@media (max-width: 860px) {
  .journey-spine,
  .journey-spine.is-collapsed {
    width: 100%;
    min-width: 0;
    overflow-x: auto;
    overflow-y: hidden;
    border-right: 0;
    border-bottom: 1px solid var(--line-dark);
  }

  .spine-heading,
  .spine-note,
  .spine-state {
    display: none;
  }

  .spine-steps {
    display: flex;
    flex-direction: row;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-2);
  }

  .journey-spine.is-collapsed .spine-entry {
    grid-template-columns: auto;
    padding: var(--space-2) var(--space-3);
  }

  .spine-entry,
  .journey-spine.is-collapsed .spine-entry {
    width: auto;
    grid-template-columns: auto auto;
    border-left: 0;
    border-bottom: 2px solid transparent;
  }

  .spine-entry.is-current {
    border-bottom-color: var(--signal);
  }

  .spine-outcome {
    display: none;
  }

  .spine-system {
    display: none;
  }
}
</style>
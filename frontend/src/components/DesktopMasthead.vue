<template>
  <header class="desktop-masthead">
    <a
      class="masthead-lockup"
      href="/"
      :aria-label="`ASKTHEPEOPLE, synthetic decision explorer. Go to the start.`"
      @click.prevent="goHome"
    >
      <span class="masthead-wordmark">ASKTHEPEOPLE</span>
      <span class="masthead-descriptor">Synthetic Decision Explorer</span>
    </a>

    <div class="masthead-context">
      <span class="context-label">Workspace</span>
      <span class="context-value">{{ contextLabel || "No decision open" }}</span>
    </div>

    <p class="masthead-position">
      <span class="position-eyebrow">Step</span>
      <span class="position-value">{{ position.step }}<span class="position-of">/{{ position.total }}</span></span>
      <span class="position-name">{{ position.title }}</span>
    </p>

    <div class="masthead-actions">
      <span class="masthead-truth">
        <span class="truth-mark" aria-hidden="true"></span>
        Generated output, not a forecast
      </span>

      <button
        v-if="nextStep"
        class="masthead-next"
        type="button"
        :aria-label="`Continue to ${nextStep.title}, step ${nextStep.step} of ${JOURNEY_TOTAL}`"
        @click="launchNext"
      >
        <span class="next-label">Next</span>
        <span class="next-target">{{ nextStep.title }}</span>
      </button>

      <button class="masthead-palette" type="button" @click="openPalette">
        <span>Commands</span>
        <kbd aria-hidden="true">Ctrl K</kbd>
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { openPalette } from "../composables/useCommandPalette.js";
import { workspaceState } from "../composables/useWorkspaceState.js";
import {
  JOURNEY_TOTAL,
  journeyState,
  launchRouteFor,
  openApp,
} from "../composables/useDesktop.js";

/**
 * The masthead is the workspace's orientation band: what this workspace is,
 * how far along the journey it is, and the single most likely next action.
 *
 * It previously carried a wall clock that re-rendered every 15 seconds. A clock
 * has no bearing on any decision this product supports, and updating visible
 * text on a timer is a live-region hazard for no benefit, so it is gone. That
 * space now carries the step position and a resume affordance instead - the two
 * things a person returning to a half-finished exploration actually needs.
 */
const router = useRouter();

const contextLabel = computed(() => {
  const state = workspaceState.value;
  const label = state.projectName || state.simulationRequirement || "";
  if (!label) return "";
  return label.length > 56 ? `${label.slice(0, 53)}…` : label;
});

const journey = computed(() => journeyState());

const position = computed(() => {
  const current = journey.value.find((entry) => entry.status === "current");
  const fallback = current || journey.value[0];
  return {
    step: fallback.step,
    total: JOURNEY_TOTAL,
    title: fallback.title,
  };
});

// The first step ahead of the user that is actually launchable. Absent when the
// journey is locked at the current position - an offer to go somewhere you
// cannot is worse than no offer.
const nextStep = computed(
  () => journey.value.find((entry) => entry.status === "next") || null,
);

function launchNext() {
  const entry = nextStep.value;
  if (!entry) return;
  const route = launchRouteFor(entry.id);
  if (!route) return;
  openApp(entry.id, route);
}

function goHome() {
  router.push({ name: "Home" });
}

</script>

<style scoped>
.desktop-masthead {
  display: grid;
  grid-template-columns: auto minmax(10rem, 1fr) auto auto;
  align-items: stretch;
  min-height: var(--band-masthead);
  border-bottom: 1px solid var(--line-structural);
  background: var(--ink-deep);
}

/* The lockup is ink with a red wayfinding edge, not a red field: red is
   reserved for action and position, so a brand block wearing it would compete
   with both. The descriptor is part of the lockup, not optional decoration -
   the product contract prohibits a naked wordmark. */
.masthead-lockup {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.1rem;
  padding: var(--space-2) var(--space-4);
  border: 0;
  border-right: 1px solid var(--line-dark);
  border-left: var(--edge-wayfinding) solid var(--signal);
  border-radius: 0;
  background: transparent;
  color: var(--paper);
  text-align: left;
  text-decoration: none;
}

.masthead-lockup:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

.masthead-wordmark {
  font-family: var(--font-display);
  font-size: 1.05rem;
  letter-spacing: 0.05em;
  line-height: var(--leading-display);
}

.masthead-descriptor {
  color: var(--paper-muted);
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  line-height: var(--leading-tight);
  text-transform: uppercase;
}

.masthead-context {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: var(--space-2) var(--space-4);
}

.context-label {
  color: var(--paper-muted);
  font-size: 0.62rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.context-value {
  overflow: hidden;
  color: var(--paper);
  font-size: 0.82rem;
  font-weight: 600;
  line-height: var(--leading-snug);
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Position is a numeral, so it keeps the display face and the attention
   colour - the same signal the spine uses for the current step. */
.masthead-position {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin: 0;
  padding: var(--space-2) var(--space-4);
  border-left: 1px solid var(--line-dark);
}

.position-eyebrow {
  color: var(--paper-muted);
  font-size: 0.62rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.position-value {
  color: var(--attention);
  font-family: var(--font-display);
  font-size: 1.15rem;
  line-height: var(--leading-display);
}

.position-of {
  color: var(--paper-muted);
  font-size: 0.7rem;
}

.position-name {
  max-width: 12rem;
  overflow: hidden;
  color: var(--paper);
  font-size: 0.78rem;
  font-weight: 600;
  line-height: var(--leading-snug);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.masthead-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  border-left: 1px solid var(--line-dark);
}

/* The permanent five-fact disclosure lives in the Truth Rail directly above
   this band. This is a short standing mark on the workspace band, not a
   second copy of the disclosure. */
.masthead-truth {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--paper-muted);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  white-space: nowrap;
}

.truth-mark {
  width: 0.45rem;
  height: 0.45rem;
  background: var(--attention);
}

/* The single most likely next action, in signal red, at the right edge of the
   workspace band. Red is spent here deliberately: it is the only persistent red
   fill in the shell, which is why it reads as an instruction. */
.masthead-next {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--control-h-md);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--signal);
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
}

.masthead-next:hover {
  border-color: var(--signal-strong);
  background: var(--signal-strong);
  color: var(--ink);
}

.next-label {
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  opacity: 0.8;
}

.next-target {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.masthead-palette {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--control-h-md);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--line-dark);
  border-radius: 0;
  background: var(--ink-soft);
  color: var(--paper);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  white-space: nowrap;
}

.masthead-palette kbd {
  padding: 0.1rem var(--space-1);
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
  color: var(--paper-muted);
  font-family: var(--font-sans);
  font-size: 0.62rem;
  letter-spacing: 0.04em;
}

@media (max-width: 1080px) {
  .masthead-truth {
    display: none;
  }
}

@media (max-width: 900px) {
  .desktop-masthead {
    grid-template-columns: auto minmax(0, 1fr) auto;
    flex-wrap: wrap;
  }

  .masthead-context {
    display: none;
  }

  .masthead-position {
    justify-content: flex-end;
    border-left: 0;
  }

  .position-name {
    display: none;
  }

  .next-target {
    display: none;
  }
}

@media (max-width: 620px) {
  .masthead-descriptor {
    display: none;
  }

  .masthead-palette span {
    display: none;
  }
}
</style>
<template>
  <header class="view-header app-header">
    <a
      class="header-left"
      href="/"
      :aria-label="`ASKTHEPEOPLE, synthetic decision explorer. Return to the decision. ${step.title}, step ${step.step} of ${JOURNEY_TOTAL}.`"
    >
      <span class="header-step-code" aria-hidden="true">
        {{ String(step.step).padStart(2, "0") }}
      </span>
      <span class="header-step-body">
        <h1 class="header-step-name">{{ step.title }}</h1>
        <span class="header-step-of">Step {{ step.step }} of {{ JOURNEY_TOTAL }}</span>
      </span>
    </a>

    <div class="header-center">
      <div
        class="view-mode-selector"
        role="group"
        :aria-label="modeSelectorLabel"
      >
        <button
          v-for="mode in modes"
          :key="mode"
          :class="['mode-btn', { 'is-active': activeMode === mode }]"
          type="button"
          :aria-pressed="activeMode === mode"
          @click="emit('update:activeMode', mode)"
        >
          {{ modeLabels[mode] }}
        </button>
      </div>
    </div>

    <div class="header-right">
      <p class="header-outcome">
        <span class="header-outcome-label">Produces</span>
        <span class="header-outcome-value">{{ step.outcome }}</span>
      </p>
      <p class="status-box" :class="status" role="status">
        <span class="status-dot" aria-hidden="true"></span>
        <span class="status-msg">{{ statusLabel }}</span>
      </p>
    </div>
  </header>
</template>

<script setup>
/**
 * One header for every route view.
 *
 * Previously each of the five route views hand-wrote this row, and the five
 * copies had drifted: three different status vocabularies, a naked product
 * wordmark on every one (seven truth-contract violations in total), a second
 * "STEP 0X/05" counter that disagreed with the shell's own numbering, and a
 * truth-rail restatement repeated in each view footer. The route views are
 * still the place where step content lives; they are no longer the place where
 * journey identity, brand, or the permanent disclosure are restated.
 *
 * `step` is a DESKTOP_APPS entry, not a locally typed-in number, so the header,
 * the journey spine, and the panel switcher read the same source and cannot
 * disagree about which step is which.
 */
import { JOURNEY_TOTAL } from "../composables/useDesktop.js";

defineProps({
  step: { type: Object, required: true },
  status: { type: String, default: "" },
  statusLabel: { type: String, default: "" },
  modes: { type: Array, required: true },
  activeMode: { type: String, required: true },
  modeLabels: { type: Object, required: true },
  modeSelectorLabel: { type: String, required: true },
});

const emit = defineEmits(["update:activeMode"]);
</script>

<style scoped>
.view-header {
  display: grid;
  grid-template-columns: minmax(11rem, 0.75fr) minmax(0, 1fr) minmax(13rem, 0.9fr);
  align-items: stretch;
  min-height: var(--band-masthead);
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-2) var(--space-4);
  border: 0;
  border-right: 1px solid var(--line-dark);
  /* Signal red as a wayfinding edge, never a full brand field. */
  border-left: var(--edge-wayfinding) solid var(--signal);
  border-radius: 0;
  background: transparent;
  color: var(--paper);
  text-align: left;
  text-decoration: none;
}

.header-left:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

/* The step numeral is a noun, so it keeps the display face. */
.header-step-code {
  flex: none;
  color: var(--attention);
  font-family: var(--font-display);
  font-size: 1.5rem;
  line-height: var(--leading-display);
}

.header-step-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.1rem;
}

/* Navigation and body-adjacent labels use the text face. The display face is a
   single-weight condensed all-caps poster face; below roughly 20px it loses the
   stroke contrast that makes small caps legible, so every label a user has to
   read to act is set in Barlow with the tracking carrying the label quality. */
.header-step-name {
  margin: 0;
  overflow: hidden;
  color: var(--paper);
  font-family: var(--font-sans);
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: var(--leading-tight);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-step-of {
  color: var(--paper-muted);
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.header-center {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: var(--space-2) var(--space-3);
}

.view-mode-selector {
  display: flex;
  border: 1px solid var(--line-dark);
  background: transparent;
}

.mode-btn {
  min-height: var(--control-h-md);
  padding: 0.4rem var(--space-4);
  border: 0;
  border-right: 1px solid var(--line-dark);
  border-radius: 0;
  background: transparent;
  color: var(--paper-muted);
  font-family: var(--font-sans);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.mode-btn:last-child {
  border-right: 0;
}

.mode-btn:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

.mode-btn.is-active {
  background: var(--signal);
  color: var(--ink);
}

.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-2) var(--space-4);
  border-left: 1px solid var(--line-dark);
}

/* "Produces" answers the question a person actually has when they open a step:
   what am I going to walk away with. It replaced a second step counter. */
.header-outcome {
  display: flex;
  flex-direction: column;
  min-width: 0;
  margin: 0;
  text-align: right;
}

.header-outcome-label {
  color: var(--paper-muted);
  font-size: 0.62rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.header-outcome-value {
  overflow: hidden;
  color: var(--paper);
  font-size: 0.76rem;
  font-weight: 600;
  line-height: var(--leading-snug);
  text-overflow: ellipsis;
}

.status-box {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.status-dot {
  flex: none;
  width: 0.5rem;
  height: 0.5rem;
  background: var(--attention);
}

.status-box.completed .status-dot {
  background: var(--success);
}

.status-box.processing .status-dot,
.status-box.running .status-dot {
  background: var(--signal);
}

.status-box.error .status-dot,
.status-box.failed .status-dot {
  background: var(--error);
}

@media (max-width: 900px) {
  .view-header {
    grid-template-columns: minmax(0, 1fr);
  }

  .header-left {
    border-right: 0;
    border-bottom: 1px solid var(--line-dark);
  }

  .header-center {
    justify-content: flex-start;
    overflow-x: auto;
  }

  .header-right {
    justify-content: space-between;
    border-left: 0;
    border-top: 1px solid var(--line-dark);
  }

  .header-outcome {
    text-align: left;
  }
}

@media (max-width: 560px) {
  .header-outcome {
    display: none;
  }
}
</style>
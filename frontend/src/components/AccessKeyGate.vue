<template>
  <div
    ref="gateDialog"
    class="access-gate"
    role="dialog"
    aria-modal="true"
    aria-labelledby="access-gate-title"
    aria-describedby="access-gate-description"
  >
    <form class="access-gate-card" @submit.prevent="submitKey">
      <span class="access-index">Private deployment</span>
      <h2 id="access-gate-title">Access key required</h2>
      <p id="access-gate-description">
        This workspace is protected by a key set by its owner. The key stays in
        this browser tab and is never bundled into the public app.
      </p>

      <label for="access-key">Access key</label>
      <div class="access-input-row">
        <input
          id="access-key"
          ref="keyInput"
          v-model="key"
          :type="showKey ? 'text' : 'password'"
          autocomplete="current-password"
          required
          aria-describedby="access-help access-error"
        />
        <button
          type="button"
          class="reveal-key"
          :aria-label="showKey ? 'Hide access key' : 'Show access key'"
          @click="showKey = !showKey"
        >
          {{ showKey ? "Hide" : "Show" }}
        </button>
      </div>
      <span id="access-help" class="access-help">
        Closing this tab clears the saved key.
      </span>
      <span v-if="error || accessMessage" id="access-error" class="access-error" role="alert">
        {{ error || accessMessage }}
      </span>

      <button class="access-submit" type="submit" :disabled="!key.trim()">
        Open the workspace
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 12h13M14 7l5 5-5 5"></path>
        </svg>
      </button>
    </form>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import {
  accessMessage,
  saveAccessKey,
} from "../composables/useAccessKey.js";

const key = ref("");
const showKey = ref(false);
const error = ref("");
const keyInput = ref(null);
const gateDialog = ref(null);
let previouslyFocused = null;
let previousBodyOverflow = "";

const getFocusableElements = () =>
  Array.from(
    gateDialog.value?.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
    ) || [],
  ).filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");

const trapFocus = (event) => {
  if (event.key !== "Tab") return;

  const focusable = getFocusableElements();
  if (focusable.length === 0) {
    event.preventDefault();
    gateDialog.value?.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (event.shiftKey && (active === first || !gateDialog.value?.contains(active))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (active === last || !gateDialog.value?.contains(active))) {
    event.preventDefault();
    first.focus();
  }
};

const submitKey = () => {
  error.value = "";
  if (!saveAccessKey(key.value)) {
    error.value = "The key could not be saved in this browser tab.";
    return;
  }
  window.location.reload();
};

onMounted(() => {
  previouslyFocused = document.activeElement;
  previousBodyOverflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  document.addEventListener("keydown", trapFocus);
  nextTick(() => keyInput.value?.focus());
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", trapFocus);
  document.body.style.overflow = previousBodyOverflow;
  if (previouslyFocused?.isConnected) {
    previouslyFocused.focus();
  }
});
</script>

<style scoped>
.access-gate {
  position: fixed;
  inset: 0;
  z-index: 25;
  display: grid;
  place-items: center;
  padding: 1rem;
}

.access-gate-card {
  width: min(100%, 31rem);
  padding: clamp(1.5rem, 4vw, 2.5rem);
}

.access-index {
  color: var(--signal-text);
  font-family: var(--font-display);
  font-size: 0.9rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

h2 {
  margin: 0.45rem 0 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: clamp(2.6rem, 7vw, 4.2rem);
  font-weight: 500;
  line-height: 0.9;
  letter-spacing: -0.01em;
}

p {
  max-width: 43ch;
  margin: 1rem 0 1.6rem;
  color: var(--ink-muted);
  font-size: 0.9rem;
  line-height: 1.55;
}

label {
  display: block;
  margin-bottom: 0.45rem;
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 700;
}

.access-input-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
}

input {
  min-width: 0;
  min-height: 3.2rem;
  padding: 0.7rem 0.8rem;
  border-color: var(--ink) !important;
  background: var(--paper-strong) !important;
  color: var(--ink) !important;
}

.reveal-key {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
}

.access-help,
.access-error {
  display: block;
  margin-top: 0.45rem;
  font-size: 0.72rem;
  line-height: 1.4;
}

.access-help {
  color: var(--ink-muted);
}

.access-error {
  color: var(--error-text);
  font-weight: 650;
}

.access-submit {
  width: 100%;
  min-height: 3.5rem;
  margin-top: 1.4rem;
  border-color: var(--signal-deep);
  background: var(--signal);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.05rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.access-gate:focus {
  outline: none;
}

.access-submit svg {
  width: 1.2rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
}
</style>

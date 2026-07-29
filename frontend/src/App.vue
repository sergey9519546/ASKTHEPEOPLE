<template>
  <div
    class="app-surface"
    :aria-hidden="accessRequired || hasCrashed ? 'true' : undefined"
    :inert="accessRequired || hasCrashed ? '' : undefined"
  >
    <router-view />
    <ToastContainer />
    <ProjectLinks />
  </div>
  <AccessKeyGate v-if="accessRequired && !hasCrashed" />

  <div
    v-if="hasCrashed"
    ref="crashDialog"
    class="crash-overlay"
    role="alertdialog"
    aria-modal="true"
    aria-labelledby="crash-title"
    aria-describedby="crash-description"
    tabindex="-1"
  >
    <div class="crash-banner">
      <span class="crash-index" aria-hidden="true">Recovery</span>
      <div class="crash-message">
        <h1 id="crash-title">Something went wrong</h1>
        <p id="crash-description">
          The workspace hit an unexpected error. Reload to continue.
        </p>
      </div>
      <button
        ref="crashReload"
        class="crash-reload"
        type="button"
        @click="reloadPage"
      >
        Reload workspace
      </button>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import AccessKeyGate from "./components/AccessKeyGate.vue";
import ProjectLinks from "./components/ProjectLinks.vue";
import ToastContainer from "./components/ToastContainer.vue";
import { accessRequired } from "./composables/useAccessKey.js";
import { hasCrashed } from "./composables/useCrashState.js";

const crashDialog = ref(null);
const crashReload = ref(null);
let previouslyFocused = null;
let previousBodyOverflow = "";

const getCrashFocusableElements = () =>
  Array.from(
    crashDialog.value?.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) || [],
  ).filter(
    (element) =>
      !element.hidden && element.getAttribute("aria-hidden") !== "true",
  );

const trapCrashFocus = (event) => {
  if (!hasCrashed.value || event.key !== "Tab") return;
  const focusable = getCrashFocusableElements();
  if (focusable.length === 0) {
    event.preventDefault();
    crashDialog.value?.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (event.shiftKey && (active === first || !crashDialog.value?.contains(active))) {
    event.preventDefault();
    last.focus();
  } else if (
    !event.shiftKey &&
    (active === last || !crashDialog.value?.contains(active))
  ) {
    event.preventDefault();
    first.focus();
  }
};

const activateCrashDialog = () => {
  previouslyFocused = document.activeElement;
  previousBodyOverflow = document.body.style.overflow;
  document.addEventListener("keydown", trapCrashFocus);
  nextTick(() => {
    document.body.style.overflow = "hidden";
    (crashReload.value || crashDialog.value)?.focus();
  });
};

const deactivateCrashDialog = () => {
  document.removeEventListener("keydown", trapCrashFocus);
  document.body.style.overflow = previousBodyOverflow;
  if (previouslyFocused?.isConnected) {
    previouslyFocused.focus();
  }
  previouslyFocused = null;
};

watch(hasCrashed, (crashed) => {
  if (crashed) {
    activateCrashDialog();
  } else {
    deactivateCrashDialog();
  }
}, { immediate: true });

function reloadPage() {
  window.location.reload();
}

onBeforeUnmount(() => {
  deactivateCrashDialog();
});
</script>

<style>
.app-surface {
  min-height: 100dvh;
}

.crash-overlay {
  position: fixed;
  inset: 0;
  z-index: 26;
  display: grid;
  place-items: center;
  padding: 1rem;
}

.crash-banner {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 1.2rem;
  width: min(100%, 45rem);
  padding: 1.4rem;
}

.crash-index {
  color: var(--signal-text);
  font-family: var(--font-display);
  font-size: 0.9rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.crash-message {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.crash-message h1 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 500;
  line-height: 1;
}

.crash-message p {
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.82rem;
  line-height: 1.45;
}

.crash-reload {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
}

@media (max-width: 620px) {
  .crash-banner {
    grid-template-columns: 1fr;
  }
}
</style>

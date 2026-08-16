<template>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  <div
    id="main-content"
    class="app-surface"
    :aria-hidden="accessRequired || hasCrashed ? 'true' : undefined"
    :inert="accessRequired || hasCrashed ? '' : undefined"
  >
    <router-view />
    <ToastContainer />
    <ProjectLinks />
    <CommandPalette v-if="!accessRequired && !hasCrashed" />
    <KeyboardShortcutsModal :is-open="shortcutsOpen" @close="shortcutsOpen = false" />
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
        <h1 id="crash-title">The workspace hit an error</h1>
        <p id="crash-description">
          No final brief was created from this session. Reload to review partial artifacts, or start a new run.
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
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AccessKeyGate from "./components/AccessKeyGate.vue";
import CommandPalette from "./components/CommandPalette.vue";
import KeyboardShortcutsModal from "./components/KeyboardShortcutsModal.vue";
import ProjectLinks from "./components/ProjectLinks.vue";
import ToastContainer from "./components/ToastContainer.vue";
import { accessRequired } from "./composables/useAccessKey.js";
import { hasCrashed } from "./composables/useCrashState.js";

const crashDialog = ref(null);
const crashReload = ref(null);
const shortcutsOpen = ref(false);
let previouslyFocused = null;
let previousBodyOverflow = "";

const handleGlobalShortcuts = (event) => {
  if (
    event.target.tagName === "INPUT" ||
    event.target.tagName === "TEXTAREA" ||
    event.target.isContentEditable
  ) {
    return;
  }

  if (event.key === "?") {
    event.preventDefault();
    shortcutsOpen.value = !shortcutsOpen.value;
  } else if (event.key === "Escape" && shortcutsOpen.value) {
    shortcutsOpen.value = false;
  }
};

onMounted(() => {
  window.addEventListener("keydown", handleGlobalShortcuts);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleGlobalShortcuts);
});

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
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  z-index: 100;
  padding: 0.8rem 1.2rem;
  border: 2px solid var(--signal);
  background: var(--signal);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-decoration: none;
  text-transform: uppercase;
  transition: top 0.2s;
}

.skip-link:focus {
  top: 0;
}

.app-surface {
  min-height: 100dvh;
  background: linear-gradient(135deg, var(--signal-aura) 0%, var(--signal-haze) 50%, transparent 100%);
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
  box-shadow: var(--shadow-lg);
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



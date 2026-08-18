<template>
  <header class="desktop-masthead">
    <a class="masthead-lockup" href="/" @click.prevent="goHome">
      <span class="masthead-wordmark">ASKTHEPEOPLE</span>
    </a>

    <a
      class="masthead-context"
      href="/"
      :title="contextLabel || 'State a decision to begin'"
      @click.prevent="goHome"
    >
      <span class="context-label">Workspace</span>
      <span class="context-value">
        {{ contextLabel || "No decision open" }}
      </span>
    </a>

    <div class="masthead-right">
      <span class="masthead-status">
        <span class="status-mark" aria-hidden="true"></span>
        GENERATED · NOT A FORECAST
      </span>
      <time class="masthead-clock" :datetime="clockIso" aria-label="Local time">
        {{ clockText }}
      </time>
      <button class="masthead-palette" type="button" @click="openPalette">
        <span>Commands</span>
        <kbd>Ctrl K</kbd>
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { openPalette } from "../composables/useCommandPalette.js";
import { workspaceState } from "../composables/useWorkspaceState.js";

const router = useRouter();

const now = ref(new Date());
let clockTimer = null;

const clockText = computed(() =>
  now.value.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }),
);

const clockIso = computed(() => now.value.toISOString());

const contextLabel = computed(() => {
  const state = workspaceState.value;
  const label = state.projectName || state.simulationRequirement || "";
  if (!label) return "";
  return label.length > 64 ? `${label.slice(0, 61)}…` : label;
});

function goHome() {
  router.push({ name: "Home" });
}

onMounted(() => {
  now.value = new Date();
  clockTimer = window.setInterval(() => {
    now.value = new Date();
  }, 15000);
});

onBeforeUnmount(() => {
  if (clockTimer) window.clearInterval(clockTimer);
});
</script>

<style scoped>
.desktop-masthead {
  display: flex;
  align-items: stretch;
  gap: 0;
  min-height: 3.4rem;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.masthead-lockup {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.15rem;
  min-width: 16rem;
  padding: 0.5rem 1.1rem;
  border: 0;
  border-right: 1px solid var(--line-dark);
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
  text-align: left;
}

.masthead-lockup:hover {
  background: var(--signal-strong);
  color: var(--ink);
}

.masthead-wordmark {
  font-family: var(--font-display);
  font-size: 1.15rem;
  letter-spacing: 0.04em;
  line-height: 1;
}

.masthead-descriptor {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.masthead-context {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.1rem;
  max-width: 26rem;
  min-width: 12rem;
  padding: 0.45rem 1.1rem;
  border: 0;
  border-right: 1px solid var(--line-dark);
  border-radius: 0;
  background: transparent;
  color: var(--paper);
  text-align: left;
}

.masthead-context:hover {
  background: var(--ink-raised);
  color: var(--paper);
}

.context-label {
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.66rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.context-value {
  overflow: hidden;
  max-width: 100%;
  font-size: 0.85rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.masthead-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-left: auto;
  padding: 0.4rem 0.9rem;
}

.masthead-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--paper-muted);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.status-mark {
  width: 0.5rem;
  height: 0.5rem;
  border: 1px solid var(--attention);
  background: var(--attention);
}

.masthead-clock {
  color: var(--paper);
  font-family: var(--font-mono);
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
}

.masthead-palette {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--line-dark);
  border-radius: 0;
  background: var(--ink-soft);
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 0.74rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.masthead-palette kbd {
  padding: 0.1rem 0.35rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
  color: var(--paper-muted);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.04em;
}

@media (max-width: 820px) {
  .masthead-descriptor,
  .masthead-context,
  .masthead-status {
    display: none;
  }

  .masthead-lockup {
    min-width: 0;
  }
}
</style>

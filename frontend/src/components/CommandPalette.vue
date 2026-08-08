<template>
  <div
    v-if="paletteOpen"
    ref="overlay"
    class="palette-overlay"
    @click.self="close"
  >
    <div
      class="palette-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="palette-title"
    >
      <h2 id="palette-title" class="palette-sr-only">Command palette</h2>

      <div class="palette-input-row">
        <span class="palette-prompt" aria-hidden="true">&gt;</span>
        <input
          ref="input"
          v-model="query"
          class="palette-input"
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-results"
          :aria-activedescendant="activeId"
          aria-describedby="palette-hint"
          autocomplete="off"
          spellcheck="false"
          placeholder="Search commands"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="runActive"
          @keydown.esc.prevent="close"
          @keydown.tab.prevent
        />
        <kbd class="palette-esc">Esc</kbd>
      </div>

      <ul
        v-if="results.length"
        id="palette-results"
        class="palette-results"
        role="listbox"
        aria-label="Commands"
      >
        <li
          v-for="(command, index) in results"
          :id="`palette-option-${command.id}`"
          :key="command.id"
          class="palette-option"
          :class="{ 'is-active': index === activeIndex }"
          role="option"
          :aria-selected="index === activeIndex"
          @click="run(command)"
          @mousemove="activeIndex = index"
        >
          <span class="palette-option-label">{{ command.label }}</span>
          <span class="palette-option-group">{{ command.group }}</span>
          <span v-if="index === activeIndex" class="palette-option-mark">
            Enter
          </span>
        </li>
      </ul>

      <p v-else class="palette-empty">
        No command matches &ldquo;{{ query }}&rdquo;.
      </p>

      <p id="palette-hint" class="palette-hint">
        Arrow keys to move. Enter to run. Esc to dismiss.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  closePalette,
  isPaletteChord,
  openSettings,
  paletteOpen,
  togglePalette,
} from "../composables/useCommandPalette.js";

const router = useRouter();
const route = useRoute();

const overlay = ref(null);
const input = ref(null);
const query = ref("");
const activeIndex = ref(0);

let previouslyFocused = null;
let previousBodyOverflow = "";

/**
 * Only commands that actually resolve are listed. A palette entry that
 * leads nowhere is worse than an absent one, so route-dependent commands
 * declare an `available` predicate instead of failing at run time.
 */
const commands = computed(() => [
  {
    id: "home",
    label: "Go to start",
    group: "Navigate",
    run: () => router.push({ name: "Home" }),
  },
  {
    id: "new-decision",
    label: "State a new decision",
    group: "Navigate",
    run: async () => {
      await router.push({ name: "Home" });
      await nextTick();
      document.querySelector("textarea, input[type='text']")?.focus();
    },
  },
  {
    id: "settings",
    label: "Open model settings",
    group: "Configure",
    run: () => openSettings(),
  },
  {
    id: "back-to-run",
    label: "Back to the run",
    group: "Navigate",
    available: () => route.name === "Report" || route.name === "Interaction",
    run: () => router.back(),
  },
]);

const availableCommands = computed(() =>
  commands.value.filter((command) =>
    command.available ? command.available() : true,
  ),
);

/**
 * Subsequence match rather than substring, so "nsd" reaches
 * "State a new decision" the way an editor palette would.
 */
function matches(haystack, needle) {
  if (!needle) return true;
  const text = haystack.toLowerCase();
  const term = needle.toLowerCase().trim();
  let cursor = 0;
  for (const char of term) {
    if (char === " ") continue;
    cursor = text.indexOf(char, cursor);
    if (cursor === -1) return false;
    cursor += 1;
  }
  return true;
}

const results = computed(() =>
  availableCommands.value.filter((command) =>
    matches(`${command.label} ${command.group}`, query.value),
  ),
);

const activeId = computed(() => {
  const command = results.value[activeIndex.value];
  return command ? `palette-option-${command.id}` : undefined;
});

function move(delta) {
  const total = results.value.length;
  if (total === 0) return;
  activeIndex.value = (activeIndex.value + delta + total) % total;
}

function close() {
  closePalette();
}

async function run(command) {
  close();
  await command.run();
}

function runActive() {
  const command = results.value[activeIndex.value];
  if (command) run(command);
}

watch(query, () => {
  activeIndex.value = 0;
});

watch(paletteOpen, (open) => {
  if (open) {
    previouslyFocused = document.activeElement;
    previousBodyOverflow = document.body.style.overflow;
    query.value = "";
    activeIndex.value = 0;
    nextTick(() => {
      document.body.style.overflow = "hidden";
      input.value?.focus();
    });
  } else {
    document.body.style.overflow = previousBodyOverflow;
    if (previouslyFocused?.isConnected) previouslyFocused.focus();
    previouslyFocused = null;
  }
});

function onGlobalKeydown(event) {
  if (isPaletteChord(event)) {
    event.preventDefault();
    togglePalette();
  }
}

onMounted(() => {
  document.addEventListener("keydown", onGlobalKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onGlobalKeydown);
  document.body.style.overflow = previousBodyOverflow;
});
</script>

<style scoped>
.palette-overlay {
  position: fixed;
  inset: 0;
  z-index: 25;
  display: flex;
  justify-content: center;
  padding: var(--space-10) var(--space-4) var(--space-4);
  background: rgba(12, 16, 15, 0.92);
}

.palette-panel {
  display: flex;
  flex-direction: column;
  width: min(100%, 34rem);
  max-height: 60vh;
  border: 1px solid var(--signal-rule);
  background: var(--ink-soft); backdrop-filter: none;
  color: var(--paper);
  box-shadow: 0.9rem 0.9rem 0 var(--signal-deep);
}

.palette-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.palette-input-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--line-light);
}

.palette-prompt {
  color: var(--signal-text);
  font-family: var(--font-display);
  font-size: var(--text-md);
}

.palette-input {
  flex: 1;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--paper);
  font-size: var(--text-md);
}

.palette-input:focus,
.palette-input:focus-visible {
  border: 0;
  outline: none;
}

.palette-input::placeholder {
  color: var(--paper-muted);
}

.palette-esc {
  padding: 0.1rem var(--space-2);
  border: 1px solid var(--line-light);
  color: var(--paper-muted);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
}

.palette-results {
  flex: 1;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.palette-option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--space-3);
  min-height: 3rem;
  padding: var(--space-2) var(--space-4);
  border-left: 3px solid transparent;
  cursor: pointer;
  transition:
    background-color var(--duration-quick) var(--ease-out),
    border-color var(--duration-quick) var(--ease-out);
}

.palette-option.is-active {
  border-left-color: var(--signal-deep);
  background: var(--signal-soft);
}

.palette-option-label {
  overflow: hidden;
  font-size: var(--text-sm);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.palette-option-group {
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.palette-option-mark {
  color: var(--signal-text);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
}

.palette-empty,
.palette-hint {
  margin: 0;
  padding: var(--space-3) var(--space-4);
  color: var(--paper-muted);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.palette-hint {
  border-top: 1px solid var(--line-light);
}

@media (max-width: 560px) {
  .palette-overlay {
    padding-top: var(--space-6);
  }

  .palette-option-group {
    display: none;
  }
}
</style>

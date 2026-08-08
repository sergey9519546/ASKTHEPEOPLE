<template>
  <div
    v-if="isOpen"
    class="shortcuts-overlay"
    role="dialog"
    aria-modal="true"
    aria-labelledby="shortcuts-modal-title"
    @click.self="$emit('close')"
  >
    <div class="shortcuts-card">
      <header class="shortcuts-header">
        <div>
          <span class="shortcuts-kicker">Keyboard Shortcuts</span>
          <h2 id="shortcuts-modal-title">Hotkeys & Workspace Controls</h2>
        </div>
        <button
          type="button"
          class="close-btn"
          aria-label="Close keyboard shortcuts modal"
          @click="$emit('close')"
        >
          ×
        </button>
      </header>

      <div class="shortcuts-grid">
        <section v-for="category in categories" :key="category.name" class="shortcut-category">
          <h3>{{ category.name }}</h3>
          <ul>
            <li v-for="shortcut in category.items" :key="shortcut.label">
              <span class="shortcut-label">{{ shortcut.label }}</span>
              <kbd class="shortcut-keys">{{ shortcut.keys }}</kbd>
            </li>
          </ul>
        </section>
      </div>

      <footer class="shortcuts-footer">
        <p>Press <kbd>Esc</kbd> anytime to dismiss overlays.</p>
      </footer>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isOpen: Boolean,
});

defineEmits(["close"]);

const categories = [
  {
    name: "Workflow Navigation",
    items: [
      { label: "Step 01: Map the sources", keys: "Ctrl + 1" },
      { label: "Step 02: Set assumptions", keys: "Ctrl + 2" },
      { label: "Step 03: Run scenarios", keys: "Ctrl + 3" },
      { label: "Step 04: Review brief", keys: "Ctrl + 4" },
      { label: "Step 05: Ask follow-ups", keys: "Ctrl + 5" },
    ],
  },
  {
    name: "Command & Tools",
    items: [
      { label: "Open Command Palette", keys: "Ctrl + K / ⌘K" },
      { label: "Toggle Shortcuts Help", keys: "?" },
      { label: "Dismiss Overlays", keys: "Esc" },
    ],
  },
];
</script>

<style scoped>
.shortcuts-overlay {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(12, 16, 15, 0.9);
  backdrop-filter: none;
}

.shortcuts-card {
  width: min(100%, 38rem);
  padding: 1.5rem;
  border: 1px solid var(--signal);
  background: var(--ink-soft);
  color: var(--paper);
  box-shadow: 0.55rem 0.55rem 0 var(--signal-deep);
}

.shortcuts-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--line-dark);
}

.shortcuts-kicker {
  color: var(--attention);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.shortcuts-header h2 {
  margin: 0.2rem 0 0;
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 500;
}

.close-btn {
  padding: 0.2rem 0.6rem;
  border: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper-muted);
  font-size: 1.3rem;
  cursor: pointer;
}

.close-btn:hover {
  border-color: var(--signal);
  color: var(--signal);
}

.shortcuts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1.5rem;
  padding: 1.2rem 0;
}

.shortcut-category h3 {
  margin: 0 0 0.8rem;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.shortcut-category ul {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.shortcut-category li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.shortcut-label {
  font-size: 0.82rem;
}

.shortcut-keys {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-raised);
  color: var(--signal);
  font-family: var(--font-mono);
  font-size: 0.74rem;
}

.shortcuts-footer {
  padding-top: 0.8rem;
  border-top: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.78rem;
  text-align: right;
}
</style>

<template>
  <div class="toast-container" aria-live="polite">
    <transition-group name="toast">
      <div
        v-for="item in toasts"
        :key="item.id"
        class="toast-item"
        :class="item.type"
        role="status"
      >
        <span class="toast-kind">{{ kindLabel(item.type) }}</span>
        <div class="toast-body">
          <strong v-if="item.title" class="toast-title">{{ item.title }}</strong>
          <span class="toast-message">{{ item.message }}</span>
        </div>
        <button
          class="toast-close"
          type="button"
          :aria-label="`Dismiss ${item.title || 'notification'}`"
          @click="removeToast(item.id)"
        >
          Close
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { removeToast, toasts } from "../utils/toast.js";

const kindLabel = (type) =>
  ({
    success: "Saved",
    error: "Error",
    warning: "Notice",
    info: "Info",
  })[type] || "Info";
</script>

<style scoped>
.toast-container {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: 24;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  width: min(calc(100vw - 2rem), 28rem);
  pointer-events: none;
}

.toast-item {
  display: grid;
  grid-template-columns: 3.5rem minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.8rem;
  padding: 0.9rem;
  border: 1px solid var(--line-dark);
  border-left: 0.35rem solid var(--signal);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0.45rem 0.45rem 0 var(--signal-deep);
  pointer-events: auto;
  transition:
    opacity 260ms var(--ease-out),
    transform 260ms var(--ease-out);
}

.toast-item.error {
  border-left-color: var(--error);
}

.toast-kind {
  color: var(--signal-deep);
  font-family: var(--font-display);
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.toast-item.error .toast-kind {
  color: var(--error);
}

.toast-body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
}

.toast-title {
  color: var(--ink);
  font-size: 0.82rem;
}

.toast-message {
  color: var(--ink-muted);
  font-size: 0.76rem;
  line-height: 1.4;
}

.toast-close {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-muted);
  font-size: 0.7rem;
  text-decoration: underline;
}

.toast-close:hover {
  background: transparent;
  color: var(--ink);
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(1rem);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(2rem);
}
</style>

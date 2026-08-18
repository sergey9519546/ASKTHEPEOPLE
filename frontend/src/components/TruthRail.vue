<template>
  <div
    class="truth-rail"
    role="note"
    aria-label="ACTIONS + ANSWERS: GENERATED. HUMAN RESPONDENTS: 0. NOT A FORECAST. SOURCES: STARTING CONDITIONS ONLY. HUMAN VALIDATION: OUTSIDE THIS RUN"
  >
    <div class="truth-rail-content">
      <span class="truth-rail-text">
        <strong class="truth-rail-item">ACTIONS + ANSWERS: GENERATED</strong>
        <span class="truth-rail-item">HUMAN RESPONDENTS: 0</span>
        <span class="truth-rail-item">NOT A FORECAST</span>
        <span class="truth-rail-item">SOURCES: STARTING CONDITIONS ONLY</span>
        <span class="truth-rail-item">HUMAN VALIDATION: OUTSIDE THIS RUN</span>
      </span>
    </div>
  </div>
</template>

<script setup>
// Shared permanent disclosure; the product-truth guard audits route coverage.
</script>

<style scoped>
.truth-rail {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: rgba(12, 16, 15, 0.98);
  color: var(--paper-muted);
  border-bottom: 1px solid var(--line-dark);
}

.truth-rail-content {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 2rem;
  padding: 0.5rem 1rem;
}

.truth-rail-text {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  column-gap: 0;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  font-size: 0.875rem;
  font-weight: 600;
  text-align: center;
  letter-spacing: 0.025em;
}

.truth-rail-item {
  padding: 0 0.75rem;
}

.truth-rail-item + .truth-rail-item {
  border-left: 1px solid currentColor;
}

.truth-rail-text strong {
  color: var(--attention);
  font-weight: 800;
  letter-spacing: 0.05em;
}

@media (max-width: 767px) {
  .truth-rail-text {
    font-size: 0.75rem;
    row-gap: 0.25rem;
  }

  .truth-rail-item {
    padding: 0 0.4rem;
  }

  .truth-rail-content {
    min-height: 2rem;
    padding: 0.4rem 0.75rem;
  }
}
</style>


<template>
  <div class="truth-rail" role="alert" aria-live="polite">
    <div class="truth-rail-content">
      <span class="truth-rail-text">
        <strong>SYNTHETIC EXPLORATION</strong> • 0 human respondents • Non-representative sample
      </span>
    </div>
  </div>
</template>

<script setup>
// Truth Rail Component
// Enforces Gate 1 requirement: visible disclosure on all workflow screens
</script>

<style scoped>
.truth-rail {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  background: #ffd700;
  color: #000;
  border-bottom: 2px solid #000;
}

.truth-rail-content {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 2.5rem;
  padding: 0.5rem 1rem;
}

.truth-rail-text {
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  font-size: 0.875rem;
  font-weight: 600;
  text-align: center;
  letter-spacing: 0.025em;
}

.truth-rail-text strong {
  font-weight: 800;
  letter-spacing: 0.05em;
}

@media (max-width: 767px) {
  .truth-rail-text {
    font-size: 0.75rem;
  }
  
  .truth-rail-content {
    min-height: 2rem;
    padding: 0.4rem 0.75rem;
  }
}
</style>

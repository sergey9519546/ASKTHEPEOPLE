<template>
  <div 
    class="evidence-badge" 
    :class="`evidence-${evidenceLevel.toLowerCase()}`"
    role="status"
    :aria-label="ariaLabel"
  >
    <div class="badge-header">
      <span class="badge-icon" aria-hidden="true">{{ icon }}</span>
      <span class="badge-level">{{ evidenceLevel }}</span>
      <span class="badge-label">{{ levelLabel }}</span>
    </div>
    
    <div v-if="claimText" class="badge-claim">
      {{ claimText }}
    </div>
    
    <div v-if="scope" class="badge-scope">
      <strong>Scope:</strong> {{ scope }}
    </div>
    
    <details v-if="restrictions && restrictions.length > 0" class="badge-restrictions">
      <summary>What this does NOT claim</summary>
      <ul>
        <li v-for="(restriction, index) in restrictions" :key="index">
          {{ restriction }}
        </li>
      </ul>
    </details>
    
    <div v-if="performanceMetrics" class="badge-metrics">
      <details>
        <summary>Performance metrics</summary>
        <dl>
          <div v-for="(value, key) in performanceMetrics" :key="key">
            <dt>{{ formatMetricName(key) }}</dt>
            <dd>{{ formatMetricValue(value) }}</dd>
          </div>
        </dl>
      </details>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  evidenceLevel: {
    type: String,
    required: true,
    validator: (value) => ["E0", "E1", "E2", "E3", "E4", "E5", "E6"].includes(value),
  },
  claimText: {
    type: String,
    default: null,
  },
  scope: {
    type: String,
    default: null,
  },
  restrictions: {
    type: Array,
    default: () => [],
  },
  performanceMetrics: {
    type: Object,
    default: null,
  },
  isForecast: {
    type: Boolean,
    default: false,
  },
  driftStatus: {
    type: String,
    default: "unknown",
  },
});

const levelLabel = computed(() => {
  const labels = {
    E0: "Untested",
    E1: "Engineering Validated",
    E2: "Retrospectively Benchmarked",
    E3: "Temporally Validated",
    E4: "Prospectively Validated",
    E5: "Externally Replicated",
    E6: "Production Monitored",
  };
  return labels[props.evidenceLevel] || "Unknown";
});

const icon = computed(() => {
  // E0-E2: not forecast (⚙️)
  // E3: experimental forecast (🔬)
  // E4+: validated forecast (✓)
  if (props.evidenceLevel === "E0" || props.evidenceLevel === "E1") return "⚙";
  if (props.evidenceLevel === "E2") return "📊";
  if (props.evidenceLevel === "E3") return "🔬";
  return "✓";
});

const ariaLabel = computed(() => {
  let label = `Evidence level ${props.evidenceLevel}: ${levelLabel.value}. `;
  if (props.isForecast) {
    label += "Forecast claim permitted within registered scope. ";
  } else {
    label += "Not a forecast. ";
  }
  if (props.driftStatus === "out_of_limits") {
    label += "Capability suspended due to performance drift.";
  }
  return label;
});

function formatMetricName(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMetricValue(value) {
  if (typeof value === "number") {
    return value.toFixed(3);
  }
  return value;
}
</script>

<style scoped>
.evidence-badge {
  margin: 1.5rem 0;
  padding: 1rem 1.25rem;
  border-left: 4px solid var(--signal);
  background: var(--paper-transfer);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  line-height: 1.5;
}

/* Evidence level color coding */
.evidence-e0,
.evidence-e1 {
  border-left-color: var(--paper-dim);
  background: var(--ink-soft);
  color: var(--paper);
}

.evidence-e2 {
  border-left-color: var(--attention);
  background: var(--paper-transfer);
}

.evidence-e3 {
  border-left-color: var(--signal);
  background: var(--paper-transfer);
}

.evidence-e4,
.evidence-e5,
.evidence-e6 {
  border-left-color: var(--success);
  background: var(--paper);
}

/* Suspended state */
.evidence-badge[data-drift="out_of_limits"] {
  border-left-color: var(--error);
  background: var(--error-tint);
}

.badge-header {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.badge-icon {
  font-size: 1.2rem;
}

.badge-level {
  padding: 0.15rem 0.4rem;
  background: var(--ink);
  color: var(--paper);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.badge-label {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.badge-claim {
  margin: 0.5rem 0;
  font-weight: 600;
  line-height: 1.4;
}

.badge-scope {
  margin: 0.5rem 0;
  font-size: 0.8rem;
  line-height: 1.4;
}

.badge-scope strong {
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.badge-restrictions summary,
.badge-metrics summary {
  margin-top: 0.75rem;
  padding: 0.35rem 0;
  border-top: 1px solid var(--line-light);
  color: var(--ink-muted);
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  cursor: pointer;
}

.badge-restrictions summary:hover,
.badge-metrics summary:hover {
  color: var(--ink);
}

.badge-restrictions ul {
  margin: 0.5rem 0 0 1.2rem;
  padding: 0;
  list-style: disc;
}

.badge-restrictions li {
  margin: 0.35rem 0;
  color: var(--ink-muted);
  font-size: 0.8rem;
  line-height: 1.4;
}

.badge-metrics dl {
  margin: 0.5rem 0 0;
  padding: 0;
}

.badge-metrics dl > div {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem 1rem;
  margin: 0.3rem 0;
  padding: 0.3rem 0;
  border-bottom: 1px solid var(--line-faint);
}

.badge-metrics dt {
  color: var(--ink-muted);
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-metrics dd {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

/* Mobile adjustments */
@media (max-width: 640px) {
  .evidence-badge {
    padding: 0.85rem 1rem;
    font-size: 0.8rem;
  }

  .badge-header {
    flex-wrap: wrap;
  }
}
</style>

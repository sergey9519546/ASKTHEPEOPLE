<template>
  <section class="fork-control" aria-labelledby="fork-heading">
    <header>
      <h3 id="fork-heading">Branch this exploration</h3>
      <p>
        Copy this run up to a chosen turn and continue it separately. Both stay
        available, so you can compare two synthetic explorations of the same
        decision. Branching changes nothing about the run it came from.
      </p>
    </header>

    <div class="fork-row">
      <label class="fork-field" for="fork-turn">
        <span>Branch from turn</span>
        <input
          id="fork-turn"
          v-model.number="targetTurn"
          type="number"
          min="0"
          :max="maxTurn"
          :disabled="busy"
          inputmode="numeric"
          :aria-describedby="error ? 'fork-error' : 'fork-turn-hint'"
        />
      </label>
      <span id="fork-turn-hint" class="fork-hint">
        0 to {{ maxTurn }} — the branch starts with everything up to that turn.
      </span>

      <button type="button" :disabled="busy || !isTurnValid" @click="submit">
        {{ busy ? "Creating branch…" : "Create branch" }}
      </button>
    </div>

    <p v-if="error" id="fork-error" class="fork-error" role="alert">{{ error }}</p>

    <p v-if="created" class="fork-created" role="status">
      Branch created from turn {{ created.forked_at_turn }}.
      <button type="button" class="link-button" @click="openBranch">
        Open the new branch
      </button>
    </p>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { forkSimulation } from "../api/simulation";

const props = defineProps({
  simulationId: { type: String, required: true },
  maxTurn: { type: Number, default: 0 },
});

const emit = defineEmits(["branched"]);

const router = useRouter();
const targetTurn = ref(props.maxTurn);
const busy = ref(false);
const error = ref("");
const created = ref(null);

// Turn 0 is a legitimate branch point — the whole run re-explored from the
// start — so this checks the range rather than truthiness.
const isTurnValid = computed(() => {
  const turn = targetTurn.value;
  return Number.isInteger(turn) && turn >= 0 && turn <= props.maxTurn;
});

const submit = async () => {
  if (!isTurnValid.value || busy.value) return;
  busy.value = true;
  error.value = "";
  created.value = null;
  try {
    const res = await forkSimulation(props.simulationId, targetTurn.value);
    if (res?.success && res.data?.new_simulation_id) {
      created.value = res.data;
      emit("branched", res.data);
    } else {
      error.value = res?.error || "The workspace did not create a branch.";
    }
  } catch (err) {
    error.value = err?.message || "Check the connection and try again.";
  } finally {
    busy.value = false;
  }
};

const openBranch = () => {
  if (!created.value?.new_simulation_id) return;
  router.push({
    name: "SimulationRun",
    params: { simulationId: created.value.new_simulation_id },
  });
};
</script>

<style scoped>
.fork-control {
  padding: 1rem 1.1rem;
  border: 1px solid var(--border-color, #222);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
}

.fork-control h3 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.fork-control p {
  margin: 0.4rem 0 0;
  color: var(--text-secondary, #8a8a8a);
  font-size: 0.78rem;
  line-height: 1.5;
}

.fork-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 0.9rem;
  align-items: center;
  margin-top: 0.9rem;
}

.fork-field {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.78rem;
}

.fork-field input {
  width: 5.5rem;
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--border-color, #222);
  border-radius: 3px;
  background: transparent;
  color: inherit;
  font-family: var(--font-mono, monospace);
}

.fork-hint {
  color: var(--text-secondary, #8a8a8a);
  font-size: 0.72rem;
}

.fork-row button {
  padding: 0.4rem 0.9rem;
  border: 1px solid var(--border-color, #222);
  border-radius: 3px;
  background: transparent;
  color: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.fork-row button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fork-error {
  color: #ff8a8a;
}

.link-button {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
}
</style>

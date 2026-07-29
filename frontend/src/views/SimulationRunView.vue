<template>
  <div class="bauhaus-view-root">
    <!-- HEADER -->
    <header class="bauhaus-header">
      <button
        class="header-left run-brand"
        type="button"
        aria-label="Ask The People — home"
        @click="router.push('/')"
      >
        <span class="brand-monogram">ASK</span>
        <span class="brand-full">THE PEOPLE</span>
      </button>

      <div class="header-center">
        <div
          class="view-mode-selector"
          role="group"
          aria-label="View generated run activity or inspect supporting source material"
        >
          <button
            v-for="m in ['workbench', 'graph', 'split']"
            :key="m"
            class="mode-btn"
            :class="{ 'is-active': viewMode === m }"
            @click="viewMode = m"
          >
            {{ { graph: "Source map", split: "Compare", workbench: "Run activity" }[m] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="step-indicator">
          <span class="step-val">STEP 03/05</span>
          <span class="step-label">Run scenarios</span>
        </div>
        <div class="status-box" :class="currentStatus">
          <span class="status-dot"></span>
          <span class="status-msg">{{ statusText }}</span>
        </div>
      </div>
    </header>

    <div v-if="contextError" class="context-alert" role="alert">
      <div>
        <strong>The saved run context needs attention.</strong>
        <span>{{ contextError }}</span>
      </div>
      <button type="button" :disabled="contextLoading" @click="loadSimulationData">
        {{ contextLoading ? "Trying again…" : "Try again" }}
      </button>
    </div>

    <!-- CONTENT -->
    <main class="workbench-viewport" :class="`view-${viewMode}`">
      <!-- LEFT: GRAPH -->
      <div
        v-if="viewMode !== 'workbench'"
        class="panel-container left"
        :style="leftPanelStyle"
        aria-label="Supporting source map"
      >
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="3"
          :isSimulating="isSimulating"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- RIGHT: WORKBENCH -->
      <div
        class="panel-container right"
        :style="rightPanelStyle"
        :aria-hidden="viewMode === 'graph'"
        :inert="viewMode === 'graph'"
        aria-label="Generated run activity"
      >
        <div class="workbench-frame">
          <div class="wb-content">
            <Step3Simulation
              :simulationId="currentSimulationId"
              :maxRounds="maxRounds"
              :minutesPerRound="minutesPerRound"
              :projectData="projectData"
              :graphData="graphData"
              :systemLogs="systemLogs"
              @go-back="handleGoBack"
              @next-step="handleNextStep"
              @add-log="addLog"
              @update-status="updateStatus"
            />
          </div>
        </div>
      </div>
    </main>

  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getGraphData, getProject } from "../api/graph";
import {
  closeSimulationEnv,
  getEnvStatus,
  getSimulation,
} from "../api/simulation";
import GraphPanel from "../components/GraphPanel.vue";
import Step3Simulation from "../components/Step3Simulation.vue";

const route = useRoute();
const router = useRouter();

const viewMode = ref("workbench");
const currentSimulationId = ref(route.params.simulationId);
const maxRounds = ref(
  route.query.maxRounds ? parseInt(route.query.maxRounds) : null,
);
const minutesPerRound = ref(30);
const projectData = ref(null);
const graphData = ref(null);
const graphLoading = ref(false);
const contextLoading = ref(false);
const contextError = ref(null);
const systemLogs = ref([]);
const currentStatus = ref("processing");

// Layout Styles
const leftPanelStyle = computed(() => {
  if (viewMode.value === "graph")
    return { width: "100%", opacity: 1, transform: "translateX(0)" };
  if (viewMode.value === "workbench")
    return {
      width: "0%",
      opacity: 0,
      transform: "translateX(-20px)",
      pointerEvents: "none",
    };
  return { width: "50%", opacity: 1, transform: "translateX(0)" };
});

const rightPanelStyle = computed(() => {
  if (viewMode.value === "workbench")
    return { width: "100%", opacity: 1, transform: "translateX(0)" };
  if (viewMode.value === "graph")
    return {
      width: "0%",
      opacity: 0,
      transform: "translateX(20px)",
      pointerEvents: "none",
    };
  return { width: "50%", opacity: 1, transform: "translateX(0)" };
});

const statusText = computed(() => {
  if (currentStatus.value === "error") return "Needs attention";
  if (currentStatus.value === "completed") return "Run complete";
  return "Routes unfolding";
});

const isSimulating = computed(() => currentStatus.value === "processing");

const addLog = (msg) => {
  const time = new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  systemLogs.value.push({ time, msg });
  if (systemLogs.value.length > 200) systemLogs.value.shift();
};

const updateStatus = (status) => (currentStatus.value = status);

const toggleMaximize = (target) =>
  (viewMode.value = viewMode.value === target ? "workbench" : target);

const handleGoBack = async () => {
  addLog("Closing the current scenario run…");
  stopGraphRefresh();
  try {
    const envStatusRes = await getEnvStatus({
      simulation_id: currentSimulationId.value,
    });
    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      await closeSimulationEnv({
        simulation_id: currentSimulationId.value,
        timeout: 5,
      });
    }
  } catch (err) {
    addLog(`The run could not be closed cleanly: ${err.message}`);
  }
  router.push({
    name: "Simulation",
    params: { simulationId: currentSimulationId.value },
  });
};

const handleNextStep = () =>
  addLog("Scenario run complete. The decision brief can now be opened.");

const loadSimulationData = async () => {
  if (contextLoading.value) return;
  contextLoading.value = true;
  contextError.value = null;
  try {
    addLog("Loading the saved scenario run…");
    const simRes = await getSimulation(currentSimulationId.value);
    if (!simRes.success || !simRes.data) {
      throw new Error("simulation");
    }

    const simData = simRes.data;
    if (!simData.project_id) {
      contextError.value =
        "The run is available, but its decision context is not linked.";
      return;
    }

    const projRes = await getProject(simData.project_id);
    if (!projRes.success || !projRes.data) {
      throw new Error("project");
    }

    projectData.value = projRes.data;
    if (projRes.data.graph_id) {
      await loadGraph(projRes.data.graph_id, true);
    }
  } catch (err) {
    contextError.value =
      "Its decision and source material could not be loaded. The run itself may still be available below.";
    addLog("The saved run context could not be loaded.");
  } finally {
    contextLoading.value = false;
  }
};

const loadGraph = async (id, surfaceError = false) => {
  if (!isSimulating.value) graphLoading.value = true;
  try {
    const res = await getGraphData(id);
    if (!res.success || !res.data) {
      if (surfaceError) {
        contextError.value =
          "The decision loaded, but its supporting source map is temporarily unavailable.";
      }
      return;
    }
    graphData.value = res.data;
  } catch {
    if (surfaceError) {
      contextError.value =
        "The decision loaded, but its supporting source map is temporarily unavailable.";
    }
  } finally {
    graphLoading.value = false;
  }
};

const refreshGraph = () =>
  projectData.value?.graph_id && loadGraph(projectData.value.graph_id);

let graphRefreshTimer = null;
const startGraphRefresh = () => {
  if (graphRefreshTimer) return;
  graphRefreshTimer = setInterval(refreshGraph, 30000);
};
const stopGraphRefresh = () => {
  if (graphRefreshTimer) {
    clearInterval(graphRefreshTimer);
    graphRefreshTimer = null;
  }
};

watch(isSimulating, (val) => (val ? startGraphRefresh() : stopGraphRefresh()), {
  immediate: true,
});

onMounted(() => {
  addLog("Scenario run view opened.");
  loadSimulationData();
});
onUnmounted(stopGraphRefresh);
</script>

<style scoped>
.bauhaus-view-root {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  background: var(--ink-deep);
  color: var(--paper);
  overflow: hidden;
}

.bauhaus-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.context-alert {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem clamp(1rem, 3vw, 2.5rem);
  border-bottom: 1px solid var(--error);
  background: #ead5cf;
  color: #612b26;
  font-size: 0.8rem;
}

.context-alert strong,
.context-alert span {
  display: block;
}

.context-alert span {
  margin-top: 0.18rem;
}

.context-alert button {
  flex: 0 0 auto;
  min-height: 2.4rem;
  border: 1px solid currentColor;
  border-radius: 0;
  background: transparent;
  color: inherit;
  font-weight: 700;
}

.context-alert button:hover:not(:disabled) {
  background: #612b26;
  color: var(--paper);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.42rem;
  cursor: pointer;
}

.run-brand {
  border: 0;
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
  text-align: left;
}

.run-brand:hover {
  background: var(--signal-strong) !important;
  color: var(--ink) !important;
}

.brand-full {
  font-family: var(--font-display);
  font-size: 1.55rem;
  font-weight: 400;
  letter-spacing: 0.035em;
}

.view-mode-selector {
  display: flex;
  border: 1px solid var(--line-dark);
  background: transparent;
}

.mode-btn {
  min-height: 2.6rem;
  border: 0 !important;
  border-right: 1px solid var(--line-dark) !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: var(--paper-muted) !important;
  font-family: var(--font-display);
  font-size: 0.88rem;
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
  box-shadow: none !important;
  transform: none !important;
}

.mode-btn:last-child {
  border-right: 0 !important;
}

.mode-btn.is-active {
  background: var(--signal) !important;
  color: var(--ink) !important;
}

.mode-btn:hover:not(.is-active) {
  background: var(--ink-raised) !important;
  color: var(--paper) !important;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 25px;
}
.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
}

.step-val {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
}

.step-label {
  color: var(--paper);
  font-size: 0.74rem;
}

.status-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--paper-muted);
  font-family: var(--font-sans);
  font-size: 0.72rem;
}

.status-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
}

.status-box.processing .status-dot {
  background: var(--signal);
  animation: flash 1.5s var(--ease-out) infinite alternate;
}

.status-box.completed .status-dot {
  background: var(--paper);
}

.status-box.error .status-dot {
  background: var(--error);
}

@keyframes flash {
  from { opacity: 0.3; }
  to { opacity: 1; }
}

.workbench-viewport {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.workbench-viewport.view-workbench {
  gap: 0 !important;
  padding: 0 !important;
  background: var(--ink-deep) !important;
}

.panel-container {
  height: 100%;
  border: 1px solid var(--line-dark);
  border-radius: 0;
  background: var(--ink-soft);
  box-shadow: none;
  overflow: hidden;
}

.view-workbench .panel-container.right {
  border: 0 !important;
}

.workbench-frame {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.wb-content {
  flex: 1;
  height: 100% !important;
  min-height: 0;
  overflow-y: auto;
}

@media (max-width: 1100px) {
  .workbench-viewport.view-split {
    flex-direction: column;
  }

  .workbench-viewport.view-split .panel-container {
    width: 100% !important;
    height: 50% !important;
  }
}

@media (max-width: 760px) {
  .bauhaus-header {
    grid-template-columns: minmax(8rem, 0.8fr) minmax(0, 1.5fr) !important;
  }

  .bauhaus-header .header-right {
    display: none;
  }

  .mode-btn {
    min-height: 2.35rem;
    padding: 0.45rem 0.55rem !important;
    font-size: 0.72rem !important;
  }

  .context-alert {
    align-items: stretch;
    flex-direction: column;
  }

  .context-alert button {
    width: 100%;
  }
}
</style>

<template>
  <div class="bauhaus-view-root">
    <!-- HEADER -->
    <header class="bauhaus-header">
      <a class="header-left" href="/" aria-label="Ask The People / generated Decision Explorer — home">
        <span class="brand-full">ASK THE PEOPLE</span>
      </a>

      <div class="header-center">
        <div
          class="view-mode-selector"
          aria-label="View assumptions or inspect supporting material"
        >
          <button
            v-for="m in ['workbench', 'graph', 'split']"
            :key="m"
            class="mode-btn"
            :class="{ 'is-active': viewMode === m }"
            type="button"
            :aria-pressed="viewMode === m"
            @click="viewMode = m"
          >
            {{ { graph: "Source map", split: "Compare", workbench: "Assumptions" }[m] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="step-indicator">
          <span class="step-val">STEP 02/05</span>
          <span class="step-label">Set assumptions</span>
        </div>
        <div class="status-box" :class="currentStatus">
          <span class="status-dot"></span>
          <span class="status-msg">{{ statusLabel }}</span>
        </div>
      </div>
    </header>

    <div v-if="error" class="workspace-error" role="alert">
      <div>
        <strong>The assumptions could not be opened</strong>
        <span>{{ error }}</span>
      </div>
      <button type="button" @click="loadSimulationData">Try again</button>
    </div>

    <!-- CONTENT -->
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <h1 class="view-title">Set assumptions</h1>
    <main id="main-content" class="workbench-viewport" :class="`mode-${viewMode}`">
      <!-- LEFT: GRAPH -->
      <div
        class="panel-container left"
        :style="leftPanelStyle"
        :aria-hidden="viewMode === 'workbench'"
        :inert="viewMode === 'workbench'"
      >
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="hasGraphContent ? 2 : 0"
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
      >
        <div class="workbench-frame">
          <header class="workbench-header">
            <span class="wb-label">Set the scenario assumptions</span>
          </header>
          <div class="wb-content">
            <Step2EnvSetup
              :simulationId="currentSimulationId"
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

    <!-- FOOTER -->
    <footer class="bauhaus-footer-mini">
      <div class="f-block">generated scenarios · 0 human respondents</div>
      <div class="f-block">Use outputs as hypotheses, not forecasts</div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useWindowRoute } from "../composables/useWindowContext.js";
import { useWorkspaceState } from "../composables/useWorkspaceState.js";
import { getGraphData, getProject } from "../api/graph";
import { getSimulation } from "../api/simulation";
import GraphPanel from "../components/GraphPanel.vue";
import Step2EnvSetup from "../components/Step2EnvSetup.vue";
import {
  RecordedGraphIdentityError,
  recordedGraphReadError,
  resolveRecordedGraphIdentity,
} from "../utils/recordedGraphIdentity";

const router = useRouter();
const windowRoute = useWindowRoute();
const { setContext } = useWorkspaceState();

const viewMode = ref("workbench");
const currentSimulationId = ref(windowRoute.value.params.simulationId);
if (currentSimulationId.value) setContext({ simulationId: currentSimulationId.value });
const projectData = ref(null);
const graphIdentity = ref(null);
const graphData = ref(null);
const graphLoading = ref(false);
const systemLogs = ref([]);
const currentStatus = ref("processing");
const error = ref("");
const statusLabel = computed(
  () =>
    ({
      completed: "Ready",
      error: "Needs attention",
      failed: "Needs attention",
      processing: "Preparing",
    })[currentStatus.value] || "Preparing",
);
const hasGraphContent = computed(
  () =>
    Number(graphData.value?.node_count || 0) > 0 ||
    (Array.isArray(graphData.value?.nodes) && graphData.value.nodes.length > 0),
);

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

const addLog = (msg) => {
  const time = new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  systemLogs.value.push({ time, msg });
  if (systemLogs.value.length > 100) systemLogs.value.shift();
};

const updateStatus = (status) => {
  currentStatus.value = status === "failed" ? "error" : status;
};

const toggleMaximize = (target) =>
  (viewMode.value = viewMode.value === target ? "split" : target);

const handleGoBack = () => {
  if (projectData.value?.project_id) {
    router.push({
      name: "Process",
      params: { projectId: projectData.value.project_id },
    });
  } else {
    router.push("/");
  }
};

const handleNextStep = (params = {}) => {
  const maxRounds = Number(params.maxRounds);
  if (!Number.isInteger(maxRounds) || maxRounds < 10 || maxRounds > 200) {
    error.value =
      "Choose a valid scenario length between 10 and 200 rounds before continuing.";
    currentStatus.value = "error";
    return;
  }
  error.value = "";
  addLog("Opening the scenario run.");
  const routeParams = {
    name: "SimulationRun",
    params: { simulationId: currentSimulationId.value },
    query: { maxRounds },
  };
  router.push(routeParams);
};

const loadSimulationData = async () => {
  error.value = "";
  graphIdentity.value = null;
  graphData.value = null;
  currentStatus.value = "processing";
  try {
    addLog("Loading the prepared scenario…");
    const simRes = await getSimulation(currentSimulationId.value);
    if (!simRes.success || !simRes.data) {
      throw new Error(simRes.error || "The scenario was not found.");
    }
    const simData = simRes.data;
    if (!simData.project_id) {
      throw new Error("The scenario is missing its project reference.");
    }
    const projRes = await getProject(simData.project_id);
    if (!projRes.success || !projRes.data) {
      throw new Error(projRes.error || "The source project could not be loaded.");
    }
    projectData.value = projRes.data;
    graphIdentity.value = resolveRecordedGraphIdentity({
      project: projRes.data,
      simulation: simData,
    });
    await loadGraph(
      graphIdentity.value.projectId,
      graphIdentity.value.graphId,
    );
  } catch (err) {
    error.value =
      err instanceof RecordedGraphIdentityError
        ? err.message
        : "The prepared scenario could not be loaded.";
    currentStatus.value = "error";
    addLog(`The prepared scenario could not be loaded: ${error.value}`);
  }
};

const loadGraph = async (projectId, graphId) => {
  graphLoading.value = true;
  try {
    const res = await getGraphData(projectId, graphId);
    if (res.success) {
      graphData.value = res.data;
    } else {
      throw recordedGraphReadError(res);
    }
  } catch (err) {
    error.value =
      err instanceof RecordedGraphIdentityError
        ? err.message
        : "The recorded source map is temporarily unavailable.";
    currentStatus.value = "error";
    throw err;
  } finally {
    graphLoading.value = false;
  }
};

const refreshGraph = async () => {
  if (!graphIdentity.value) return;
  try {
    await loadGraph(
      graphIdentity.value.projectId,
      graphIdentity.value.graphId,
    );
  } catch {
    // loadGraph owns the sanitized visible failure state.
  }
};

onMounted(async () => {
  addLog("Scenario workspace opened.");
  await loadSimulationData();
});
</script>

<style scoped>
.bauhaus-view-root {
  height: 100vh;
  background: var(--bg-void);
  color: var(--text-void);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--font-sans);
}

.bauhaus-header {
  height: 54px;
  background: var(--bg-base);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 100;
  box-shadow: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 0;
  background: transparent;
  color: inherit;
  padding: 0 !important;
  border-radius: 0;
  box-shadow: none;
  transform: none;
  cursor: pointer;
}
.brand-full {
  font-weight: 400;
  font-size: 1.2rem;
  font-family: var(--font-display);
  letter-spacing: 0.05em;
  color: var(--text-primary);
}

.view-mode-selector {
  display: flex;
  border: 1px solid var(--line);
  background: var(--bg-void);
  padding: 3px;
  border-radius: 0;
  gap: 2px;
}
.mode-btn {
  border: 1px solid transparent !important;
  background: transparent !important;
  padding: 5px 14px !important;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 11px;
  cursor: pointer;
  color: var(--text-secondary);
  border-radius: 0 !important;
  box-shadow: none !important;
  transform: none !important;
}
.mode-btn.is-active {
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border-color: var(--accent) !important;
}
.mode-btn:hover:not(.is-active) {
  background: var(--bg-hover) !important;
  color: var(--text-void) !important;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.step-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 11px;
  font-family: var(--font-mono);
}
.step-val {
  color: var(--accent);
}
.status-box {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 10px;
  color: var(--text-secondary);
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}
.status-box.processing .status-dot {
  background: var(--accent);
  animation: flash 1s infinite alternate;
}
.status-box.completed .status-dot {
  background: var(--status-live);
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
  padding: 12px;
  gap: 12px;
  overflow: hidden;
  position: relative;
  background: var(--bg-void);
}
.panel-container {
  height: 100%;
  transition: all 0.2s ease;
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 0;
  box-shadow: none;
  overflow: hidden;
}

.workbench-frame {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.workbench-header {
  height: 44px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: var(--bg-base);
}
.wb-label {
  font-weight: 600;
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 0.1em;
  color: var(--text-muted);
  text-transform: uppercase;
}
.wb-content {
  flex: 1;
  overflow-y: auto;
  padding: 0px;
}

.bauhaus-footer-mini {
  height: 36px;
  padding: 0 24px;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 9px;
  color: var(--text-muted);
  background: var(--bg-base);
}

@media (max-width: 1100px) {
  .workbench-viewport {
    flex-direction: column;
  }

  .workbench-viewport.mode-workbench .panel-container.left,
  .workbench-viewport.mode-graph .panel-container.right {
    display: none;
  }

  .workbench-viewport.mode-workbench .panel-container.right,
  .workbench-viewport.mode-graph .panel-container.left {
    width: 100% !important;
    height: 100% !important;
  }

  .workbench-viewport.mode-split .panel-container {
    width: 100% !important;
    height: 50% !important;
  }
}

.workspace-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--error);
  background: #291817;
  color: var(--paper);
}

.workspace-error div {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.workspace-error strong {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 500;
}

.workspace-error span {
  color: var(--paper-muted);
  font-size: 0.72rem;
}

.workspace-error button {
  flex: 0 0 auto;
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

@media (max-width: 760px) {
  .bauhaus-header {
    height: 58px;
    padding: 0 0.75rem;
    gap: 0.6rem;
  }

  .header-right {
    display: none;
  }

  .brand-full {
    display: inline-block !important;
    font-size: 1rem;
    white-space: nowrap;
  }

  .view-mode-selector {
    padding: 0;
    gap: 0;
  }

  .mode-btn {
    padding: 0.45rem 0.5rem !important;
    font-size: 0.65rem;
  }

  .workbench-viewport {
    padding: 0;
    gap: 0;
  }

  .workspace-error {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

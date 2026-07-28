<template>
  <div class="bauhaus-view-root">
    <!-- HEADER -->
    <header class="bauhaus-header">
      <div class="header-left" @click="router.push('/')">
        <span class="brand-monogram">ATP</span>
        <span class="brand-full">ASK THE PEOPLE</span>
      </div>

      <div class="header-center">
        <div class="view-mode-selector">
          <button
            v-for="m in ['graph', 'split', 'workbench']"
            :key="m"
            class="mode-btn"
            :class="{ 'is-active': viewMode === m }"
            @click="viewMode = m"
          >
            {{ m.toUpperCase() }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="step-indicator">
          <span class="step-val">STEP 02/05</span>
          <span class="step-label">ENV_SETUP</span>
        </div>
        <div class="status-box" :class="currentStatus">
          <span class="status-dot"></span>
          <span class="status-msg">{{ currentStatus.toUpperCase() }}</span>
        </div>
      </div>
    </header>

    <!-- CONTENT -->
    <main class="workbench-viewport">
      <!-- LEFT: GRAPH -->
      <div class="panel-container left" :style="leftPanelStyle">
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="2"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- RIGHT: WORKBENCH -->
      <div class="panel-container right" :style="rightPanelStyle">
        <div class="workbench-frame">
          <header class="workbench-header">
            <span class="wb-label">WORKBENCH_ENV</span>
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
      <div class="f-block">SYS_STATUS: NOMINAL</div>
      <div class="f-block">LOC: WORKSPACE_ENV_SETUP</div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getGraphData, getProject } from "../api/graph";
import { getSimulation } from "../api/simulation";
import GraphPanel from "../components/GraphPanel.vue";
import Step2EnvSetup from "../components/Step2EnvSetup.vue";

const route = useRoute();
const router = useRouter();

const viewMode = ref("split");
const currentSimulationId = ref(route.params.simulationId);
const projectData = ref(null);
const graphData = ref(null);
const graphLoading = ref(false);
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

const updateStatus = (status) => (currentStatus.value = status);

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
  addLog("Entering Stage 03: Engine Runtime");
  const routeParams = {
    name: "SimulationRun",
    params: { simulationId: currentSimulationId.value },
  };
  if (params.maxRounds) routeParams.query = { maxRounds: params.maxRounds };
  router.push(routeParams);
};

const loadSimulationData = async () => {
  try {
    addLog(`Accessing database: ${currentSimulationId.value}`);
    const simRes = await getSimulation(currentSimulationId.value);
    if (simRes.success && simRes.data) {
      const simData = simRes.data;
      if (simData.project_id) {
        const projRes = await getProject(simData.project_id);
        if (projRes.success && projRes.data) {
          projectData.value = projRes.data;
          if (projRes.data.graph_id) await loadGraph(projRes.data.graph_id);
        }
      }
    }
  } catch (err) {
    addLog(`DB Error: ${err.message}`);
  }
};

const loadGraph = async (id) => {
  graphLoading.value = true;
  try {
    const res = await getGraphData(id);
    if (res.success) graphData.value = res.data;
  } finally {
    graphLoading.value = false;
  }
};

const refreshGraph = () =>
  projectData.value?.graph_id && loadGraph(projectData.value.graph_id);

onMounted(async () => {
  addLog("Runtime View Initialized");
  loadSimulationData();
});
</script>

<style scoped>
.bauhaus-view-root {
  height: 100vh;
  background: var(--bg-color);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.bauhaus-header {
  height: 70px;
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  z-index: 100;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}
.brand-monogram {
  background: var(--accent-color);
  color: white;
  padding: 4px 8px;
  font-weight: 700;
  font-size: 1rem;
  border-radius: 4px;
}
.brand-full {
  font-weight: 600;
  font-size: 1rem;
  letter-spacing: -0.5px;
}

.view-mode-selector {
  display: flex;
  border: 1px solid var(--border-color);
  background: var(--atp-light-gray);
  padding: 4px;
  border-radius: var(--radius-sm);
  gap: 4px;
}
.mode-btn {
  border: none !important;
  background: transparent !important;
  padding: 6px 16px !important;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 10px;
  cursor: pointer;
  border-radius: 6px !important;
  box-shadow: none !important;
  transform: none !important;
}
.mode-btn.is-active {
  background: var(--surface-color) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-color) !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}
.mode-btn:hover:not(.is-active) {
  background: rgba(15, 23, 42, 0.03) !important;
  color: var(--text-primary) !important;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 25px;
}
.step-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 11px;
}
.step-val {
  color: var(--accent-secondary);
  font-family: var(--font-mono);
}
.status-box {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 10px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-box.processing .status-dot {
  background: var(--accent-color);
  animation: flash 1s infinite alternate;
}
.status-box.completed .status-dot {
  background: var(--accent-tertiary);
}
@keyframes flash {
  from { opacity: 0.3; }
  to { opacity: 1; }
}

.workbench-viewport {
  flex: 1;
  display: flex;
  padding: 24px;
  gap: 24px;
  overflow: hidden;
  position: relative;
}
.panel-container {
  height: 100%;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.04), 0 1px 3px -1px rgba(15, 23, 42, 0.02);
  overflow: hidden;
}

.workbench-frame {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.workbench-header {
  height: 50px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  padding: 0 20px;
  background: var(--atp-light-gray);
}
.wb-label {
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  text-transform: uppercase;
}
.wb-content {
  flex: 1;
  overflow-y: auto;
  padding: 0px;
}

.bauhaus-footer-mini {
  height: 40px;
  padding: 0 40px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 9px;
  color: var(--text-secondary);
  background: var(--surface-color);
}

@media (max-width: 1100px) {
  .workbench-viewport {
    flex-direction: column;
  }
  .panel-container {
    width: 100% !important;
    height: 50% !important;
  }
}
</style>

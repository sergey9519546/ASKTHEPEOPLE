<template>
  <div class="main-view">
    <TruthRail />
    <header class="app-header">
      <button class="header-left brand-home" type="button" @click="router.push('/')">
        <span class="brand">ASK THE PEOPLE</span>
      </button>

      <div class="header-center">
        <div
          class="view-switcher"
          role="group"
          aria-label="View decision steps or inspect supporting source material"
        >
          <button
            v-for="mode in ['workbench', 'graph', 'split']"
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            type="button"
            :aria-pressed="viewMode === mode"
            @click="viewMode = mode"
          >
            {{ { graph: "Source map", split: "Compare", workbench: "Decision steps" }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num">Step {{ currentStep }}/5</span>
          <span class="step-name">{{ stepNames[currentStep - 1] }}</span>
        </div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <nav ref="workflowPath" class="workflow-path" aria-label="Scenario workflow">
      <div
        v-for="(step, index) in stepNames"
        :key="step"
        :ref="(element) => setWorkflowStepRef(element, index)"
        class="workflow-path-step"
        :class="{ current: currentStep === index + 1, complete: currentStep > index + 1, clickable: index + 1 <= maxCompletedStep }"
        :aria-current="currentStep === index + 1 ? 'step' : undefined"
        :tabindex="index + 1 <= maxCompletedStep ? 0 : -1"
        role="button"
        :aria-label="`Step ${index + 1}: ${step}`"
        @click="jumpToStep(index + 1)"
        @keydown.enter.space.prevent="jumpToStep(index + 1)"
      >
        <span>{{ String(index + 1).padStart(2, "0") }}</span>
        <strong>{{ step }}</strong>
      </div>
      <p><strong>0 human respondents</strong> · Synthetic scenarios, not a forecast</p>
    </nav>
    <label class="mobile-workflow-picker">
      <span>Workflow step</span>
      <select
        :value="currentStep"
        aria-label="Choose an available workflow step"
        @change="jumpToStep(Number($event.target.value))"
      >
        <option
          v-for="(step, index) in stepNames"
          :key="step"
          :value="index + 1"
          :disabled="index + 1 > maxCompletedStep"
        >
          {{ String(index + 1).padStart(2, "0") }} — {{ step }}
        </option>
      </select>
    </label>

    <div v-if="error" class="workspace-error" role="alert">
      <div>
        <strong>This step needs attention</strong>
        <span>{{ error }}</span>
      </div>
      <div class="workspace-error-actions">
        <button type="button" @click="recoverWorkspace">Try again</button>
        <button type="button" @click="router.push('/')">Return to the decision</button>
      </div>
    </div>

    <main class="content-area" :class="`view-${viewMode}`">
      <section
        v-if="viewMode !== 'workbench'"
        class="panel-wrapper left"
        :style="leftPanelStyle"
        :aria-hidden="viewMode === 'workbench'"
        :inert="viewMode === 'workbench'"
        aria-label="Supporting source map"
      >
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="currentPhase"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </section>

      <section
        class="panel-wrapper right"
        :style="rightPanelStyle"
        :aria-hidden="viewMode === 'graph'"
        :inert="viewMode === 'graph'"
        aria-label="Decision workflow"
      >
        <Step1GraphBuild
          v-if="currentStep === 1"
          :currentPhase="currentPhase"
          :projectData="projectData"
          :ontologyProgress="ontologyProgress"
          :buildProgress="buildProgress"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @next-step="handleNextStep"
        />
        <Step2EnvSetup
          v-else-if="currentStep === 2"
          :simulationId="processState.simulationId"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStepStatus"
        />
        <Step3Simulation
          v-else-if="currentStep === 3"
          :simulationId="processState.simulationId"
          :maxRounds="processState.maxRounds"
          :minutesPerRound="30"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStepStatus"
        />
        <Step4Report
          v-else-if="currentStep === 4"
          :simulationId="processState.simulationId"
          :reportId="processState.reportId"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStepStatus"
        />
        <Step5Interaction
          v-else-if="currentStep === 5"
          :simulationId="processState.simulationId"
          :reportId="processState.reportId"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @update-status="updateStepStatus"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  buildGraph,
  generateOntology,
  getGraphData,
  getProject,
  getTaskStatus,
} from "../api/graph";
import GraphPanel from "../components/GraphPanel.vue";
import Step1GraphBuild from "../components/Step1GraphBuild.vue";
import Step2EnvSetup from "../components/Step2EnvSetup.vue";
import Step3Simulation from "../components/Step3Simulation.vue";
import Step4Report from "../components/Step4Report.vue";
import Step5Interaction from "../components/Step5Interaction.vue";
import TruthRail from "../components/TruthRail.vue";
import { clearPendingUpload, getPendingUpload } from "../store/pendingUpload";
import { listSimulations } from "../api/simulation";
import { deriveWorkflowStep } from "../utils/workflow.js";

const route = useRoute();
const router = useRouter();

const viewMode = ref("workbench");
const currentStep = ref(1);
const maxCompletedStep = ref(1);
const stepNames = [
  "Map the sources",
  "Set assumptions",
  "Run scenarios",
  "Review the brief",
  "Ask follow-ups",
];

watch(currentStep, (newStep) => {
  if (newStep > maxCompletedStep.value) {
    maxCompletedStep.value = newStep;
  }
}, { immediate: true });

const jumpToStep = (targetStep) => {
  if (targetStep <= maxCompletedStep.value && targetStep !== currentStep.value) {
    currentStep.value = targetStep;
  }
};

const currentProjectId = ref(route.params.projectId);
const loading = ref(false);
const graphLoading = ref(false);
const error = ref("");
const projectData = ref(null);
const graphData = ref(null);
const currentPhase = ref(-1);
const ontologyProgress = ref(null);
const buildProgress = ref(null);
const systemLogs = ref([]);
const stepRuntimeStatus = ref("processing");
const workflowPath = ref(null);
const workflowStepElements = [];
const processState = ref({
  simulationId: null,
  maxRounds: null,
  reportId: null,
});

const hasGraphContent = computed(
  () =>
    Number(graphData.value?.node_count || 0) > 0 ||
    (Array.isArray(graphData.value?.nodes) && graphData.value.nodes.length > 0),
);

let pollTimer = null;
let graphPollTimer = null;
let ontologyPollTimer = null;
let recoveryAction = null;

const showRecoverableError = (message, action = null) => {
  error.value = message;
  recoveryAction = action;
  stepRuntimeStatus.value = "error";
};

const recoverWorkspace = async () => {
  const action = recoveryAction;
  recoveryAction = null;
  error.value = "";
  stepRuntimeStatus.value = "processing";
  if (action) {
    await action();
    return;
  }
  await loadProject();
};

const leftPanelStyle = computed(() => {
  if (viewMode.value === "graph") {
    return { width: "100%", opacity: 1, transform: "translateX(0)" };
  }
  if (viewMode.value === "workbench") {
    return {
      width: "0%",
      opacity: 0,
      transform: "translateX(-20px)",
      pointerEvents: "none",
    };
  }
  return { width: "50%", opacity: 1, transform: "translateX(0)" };
});

const rightPanelStyle = computed(() => {
  if (viewMode.value === "workbench") {
    return { width: "100%", opacity: 1, transform: "translateX(0)" };
  }
  if (viewMode.value === "graph") {
    return {
      width: "0%",
      opacity: 0,
      transform: "translateX(20px)",
      pointerEvents: "none",
    };
  }
  return { width: "50%", opacity: 1, transform: "translateX(0)" };
});

const statusClass = computed(() => {
  if (error.value) return "error";
  if (currentStep.value === 1 && currentPhase.value >= 2) {
    return hasGraphContent.value ? "completed" : "error";
  }
  if (currentStep.value > 1) return stepRuntimeStatus.value;
  return "processing";
});

const statusText = computed(() => {
  if (error.value) return "Needs attention";
  if (currentStep.value > 1) {
    return {
      completed: "Ready",
      error: "Needs attention",
      failed: "Needs attention",
      processing: "Preparing",
    }[stepRuntimeStatus.value] || "Preparing";
  }
  if (currentPhase.value >= 2) {
    return hasGraphContent.value ? "Ready" : "Needs attention";
  }
  if (currentPhase.value === 1) return "Mapping sources";
  if (currentPhase.value === 0) return "Reading sources";
  return "Preparing";
});

const updateStepStatus = (status) => {
  stepRuntimeStatus.value = status === "failed" ? "error" : status;
};

const setWorkflowStepRef = (element, index) => {
  if (element) workflowStepElements[index] = element;
};

const keepCurrentStepVisible = () => {
  if (window.innerWidth > 700) return;
  const element = workflowStepElements[currentStep.value - 1];
  if (!element || !workflowPath.value) return;
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  element.scrollIntoView({
    behavior: reduceMotion ? "auto" : "smooth",
    block: "nearest",
    inline: "center",
  });
};

const normalizeRounds = (value) => {
  const rounds = Number(value);
  return Number.isInteger(rounds) && rounds >= 10 && rounds <= 200
    ? rounds
    : null;
};

const addLog = (msg) => {
  const time =
    new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }) +
    "." +
    new Date().getMilliseconds().toString().padStart(3, "0");
  systemLogs.value.push({ time, msg });
  if (systemLogs.value.length > 100) systemLogs.value.shift();
};

const toggleMaximize = (target) => {
  viewMode.value = viewMode.value === target ? "workbench" : target;
};

const handleNextStep = (params = {}) => {
  if (currentStep.value >= 5) return;
  if (currentStep.value === 2) {
    const resolvedRounds = normalizeRounds(params.maxRounds);
    if (!resolvedRounds) {
      error.value =
        "Choose a valid scenario length between 10 and 200 rounds before continuing.";
      stepRuntimeStatus.value = "error";
      return;
    }
    processState.value.maxRounds = resolvedRounds;
  }
  error.value = "";
  currentStep.value += 1;
  stepRuntimeStatus.value = "processing";
  addLog(`Opened step ${currentStep.value}: ${stepNames[currentStep.value - 1]}`);
  if (params.simulationId) processState.value.simulationId = params.simulationId;
  if (params.reportId) processState.value.reportId = params.reportId;
};

const handleGoBack = () => {
  if (currentStep.value <= 1) return;
  currentStep.value -= 1;
  stepRuntimeStatus.value = "processing";
  addLog(`Returned to step ${currentStep.value}: ${stepNames[currentStep.value - 1]}`);
};

const initProject = async () => {
  addLog("Workspace opened.");
  if (currentProjectId.value === "new") {
    await handleNewProject();
  } else {
    await loadProject();
  }
};

const handleNewProject = async () => {
  const pending = getPendingUpload();
  if (!pending.isPending || pending.files.length === 0) {
    error.value = "No source files were carried into this workspace.";
    return;
  }

  try {
    loading.value = true;
    currentPhase.value = 0;
    ontologyProgress.value = { message: "Uploading source material…" };

    const formData = new FormData();
    pending.files.forEach((file) => formData.append("files", file));
    formData.append("simulation_requirement", pending.simulationRequirement);
    if (pending.projectName) formData.append("project_name", pending.projectName);
    if (pending.additionalContext) {
      formData.append("additional_context", pending.additionalContext);
    }
    formData.append(
      "use_policy_acknowledged",
      pending.usePolicyAcknowledged ? "true" : "false",
    );
    formData.append("intended_use", "scenario_planning");

    const response = await generateOntology(formData);
    if (!response.success) {
      error.value = response.error || "The source material could not be read.";
      return;
    }

    clearPendingUpload();
    currentProjectId.value = response.data.project_id;
    await router.replace({
      name: "Process",
      params: { projectId: response.data.project_id },
    });
    ontologyProgress.value = { message: "Reading sources and identifying key entities…" };
    startPollingOntologyTask(response.data.task_id);
  } catch (caughtError) {
    error.value = caughtError.message || "The source material could not be uploaded.";
  } finally {
    loading.value = false;
  }
};

const startPollingOntologyTask = (taskId) => {
  stopOntologyPolling();
  pollOntologyTask(taskId);
  ontologyPollTimer = setInterval(() => pollOntologyTask(taskId), 3000);
};

const stopOntologyPolling = () => {
  if (!ontologyPollTimer) return;
  clearInterval(ontologyPollTimer);
  ontologyPollTimer = null;
};

const pollOntologyTask = async (taskId) => {
  try {
    const response = await getTaskStatus(taskId);
    if (!response.success) {
      stopOntologyPolling();
      showRecoverableError(
        "Source-reading progress could not be checked. Your uploaded material is still saved.",
        () => startPollingOntologyTask(taskId),
      );
      return;
    }

    const task = response.data;
    if (task.message && task.message !== ontologyProgress.value?.message) {
      addLog(task.message);
    }
    ontologyProgress.value = {
      progress: task.progress || 0,
      message: task.message,
    };

    if (task.status === "completed") {
      stopOntologyPolling();
      ontologyProgress.value = null;
      projectData.value = task.result;
      await startBuildGraph();
    } else if (task.status === "failed") {
      stopOntologyPolling();
      error.value = task.error || task.message || "The sources could not be mapped.";
    }
  } catch (caughtError) {
    stopOntologyPolling();
    showRecoverableError(
      "Source-reading updates stopped. Try reconnecting to the saved task.",
      () => startPollingOntologyTask(taskId),
    );
    if (import.meta.env.DEV) console.error("Source progress error", caughtError);
  }
};

const loadProject = async () => {
  try {
    loading.value = true;
    const response = await getProject(currentProjectId.value);
    if (!response.success) {
      error.value = response.error || "This workspace could not be loaded.";
      return;
    }

    projectData.value = response.data;
    updatePhaseByStatus(response.data.status);
    await hydrateSavedWorkflow();

    if (response.data.status === "ontology_generated" && !response.data.graph_id) {
      await startBuildGraph();
    } else if (
      response.data.status === "graph_building" &&
      response.data.graph_build_task_id
    ) {
      currentPhase.value = 1;
      startPollingTask(response.data.graph_build_task_id);
      startGraphPolling();
    } else if (
      response.data.status === "graph_completed" &&
      response.data.graph_id
    ) {
      currentPhase.value = 2;
      await loadGraph(response.data.project_id, response.data.graph_id);
    }
  } catch (caughtError) {
    error.value = caughtError.message || "This workspace could not be loaded.";
  } finally {
    loading.value = false;
  }
};

const hydrateSavedWorkflow = async () => {
  const response = await listSimulations(currentProjectId.value);
  if (!response.success || !Array.isArray(response.data) || response.data.length === 0) {
    return;
  }

  const savedRun = response.data[0];
  processState.value.simulationId = savedRun.simulation_id || null;
  processState.value.reportId = savedRun.report_id || null;
  if (Number(savedRun.total_rounds) > 0) {
    processState.value.maxRounds = normalizeRounds(savedRun.total_rounds);
  }
  currentStep.value = deriveWorkflowStep(savedRun);
  addLog(
    `Resumed saved work at step ${currentStep.value}: ${
      stepNames[currentStep.value - 1]
    }.`,
  );
};

const updatePhaseByStatus = (status) => {
  switch (status) {
    case "created":
    case "ontology_generated":
      currentPhase.value = 0;
      break;
    case "graph_building":
      currentPhase.value = 1;
      break;
    case "graph_completed":
      currentPhase.value = 2;
      break;
    case "failed":
      error.value = "The source map could not be completed.";
      break;
  }
};

const startBuildGraph = async () => {
  try {
    currentPhase.value = 1;
    buildProgress.value = { progress: 0, message: "Starting the source map…" };
    const response = await buildGraph({ project_id: currentProjectId.value });
    if (!response.success) {
      error.value = response.error || "The source map could not be started.";
      return;
    }
    startGraphPolling();
    startPollingTask(response.data.task_id);
  } catch (caughtError) {
    error.value = caughtError.message || "The source map could not be started.";
  }
};

const startGraphPolling = () => {
  stopGraphPolling();
  fetchGraphData();
  graphPollTimer = setInterval(fetchGraphData, 10000);
};

const fetchGraphData = async () => {
  try {
    const projectResponse = await getProject(currentProjectId.value);
    if (!projectResponse.success || !projectResponse.data?.graph_id) {
      return;
    }
    const graphResponse = await getGraphData(projectResponse.data.project_id, projectResponse.data.graph_id);
    if (graphResponse.success) {
      graphData.value = graphResponse.data;
    } else {
      stopGraphPolling();
      showRecoverableError(
        "Source-map updates paused. The saved workspace is still available.",
        startGraphPolling,
      );
    }
  } catch (caughtError) {
    stopGraphPolling();
    showRecoverableError(
      "Source-map updates paused. Try reconnecting to the saved workspace.",
      startGraphPolling,
    );
    if (import.meta.env.DEV) console.warn("Source map refresh error", caughtError);
  }
};

const startPollingTask = (taskId) => {
  stopPolling();
  pollTaskStatus(taskId);
  pollTimer = setInterval(() => pollTaskStatus(taskId), 2000);
};

const pollTaskStatus = async (taskId) => {
  try {
    const response = await getTaskStatus(taskId);
    if (!response.success) {
      stopPolling();
      showRecoverableError(
        "Source-map progress could not be checked. The saved task can be retried.",
        () => startPollingTask(taskId),
      );
      return;
    }
    const task = response.data;
    if (task.message && task.message !== buildProgress.value?.message) {
      addLog(task.message);
    }
    buildProgress.value = {
      progress: task.progress || 0,
      message: task.message,
    };

    if (task.status === "completed") {
      stopPolling();
      stopGraphPolling();
      currentPhase.value = 2;
      const projectResponse = await getProject(currentProjectId.value);
      if (projectResponse.success && projectResponse.data?.graph_id) {
        projectData.value = projectResponse.data;
        await loadGraph(projectResponse.data.project_id, projectResponse.data.graph_id);
      }
    } else if (task.status === "failed") {
      stopPolling();
      error.value = task.error || "The source map could not be completed.";
    }
  } catch (caughtError) {
    stopPolling();
    showRecoverableError(
      "Source-map progress updates stopped. Try reconnecting to the saved task.",
      () => startPollingTask(taskId),
    );
    if (import.meta.env.DEV) console.error("Source map progress error", caughtError);
  }
};

const loadGraph = async (projectId, graphId) => {
  graphLoading.value = true;
  try {
    const response = await getGraphData(projectId, graphId);
    if (response.success) {
      graphData.value = response.data;
    } else {
      error.value = response.error || "The source map could not be loaded.";
    }
  } catch (caughtError) {
    error.value = caughtError.message || "The source map could not be loaded.";
  } finally {
    graphLoading.value = false;
  }
};

const refreshGraph = () => {
  if (projectData.value?.project_id && projectData.value?.graph_id) {
    loadGraph(projectData.value.project_id, projectData.value.graph_id);
  }
};

const stopPolling = () => {
  if (!pollTimer) return;
  clearInterval(pollTimer);
  pollTimer = null;
};

const stopGraphPolling = () => {
  if (!graphPollTimer) return;
  clearInterval(graphPollTimer);
  graphPollTimer = null;
};

watch(currentStep, () => nextTick(keepCurrentStepVisible));

onMounted(async () => {
  await initProject();
  await nextTick();
  keepCurrentStepVisible();
});

onUnmounted(() => {
  stopPolling();
  stopGraphPolling();
  stopOntologyPolling();
});
</script>

<style scoped>
.main-view {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  overflow: hidden;
}

.brand-home {
  border: 0;
  border-radius: 0;
  text-align: left;
}

.brand-home:hover {
  background: var(--signal-strong) !important;
  color: var(--ink) !important;
}

.status-indicator.processing .dot {
  background: var(--attention);
}

.status-indicator.error .dot {
  background: var(--error) !important;
}

.workflow-path {
  display: grid;
  grid-template-columns: repeat(5, minmax(7rem, 1fr)) minmax(16rem, 1.25fr);
  align-items: stretch;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink);
}

.workflow-path-step {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
  min-height: 3.4rem;
  padding: 0.7rem 0.8rem;
  border-right: 1px solid var(--line-dark);
  color: var(--paper-dim);
}

.workflow-path-step::after {
  content: "";
  position: absolute;
  right: 0;
  bottom: -1px;
  left: 0;
  height: 0.22rem;
  background: transparent;
}

.workflow-path-step.current {
  color: var(--paper);
}

.workflow-path-step.current::after,
.workflow-path-step.complete::after {
  background: var(--signal);
}

.workflow-path-step span {
  font-family: var(--font-mono);
  font-size: 0.62rem;
}

.workflow-path-step strong {
  overflow: hidden;
  font-family: var(--font-display);
  font-size: 0.82rem;
  font-weight: 500;
  letter-spacing: 0.035em;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.workflow-path > p {
  align-self: center;
  margin: 0;
  padding: 0.7rem 1rem;
  color: var(--paper-dim);
  font-size: 0.66rem;
  text-align: right;
}

.workflow-path > p strong {
  color: var(--paper-muted);
}

.mobile-workflow-picker {
  display: none;
}

.workspace-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--error);
  background: #291817;
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

.workspace-error .workspace-error-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: row;
  gap: 0.55rem;
}

.workspace-error-actions button:first-child {
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.content-area {
  position: relative;
}

.content-area.view-workbench {
  gap: 0 !important;
  padding: 0 !important;
  background: var(--ink-deep) !important;
}

.content-area.view-workbench .panel-wrapper.right {
  border: 0 !important;
}

.panel-wrapper {
  height: 100%;
}

@keyframes smooth-pulse {
  0%,
  100% {
    opacity: 0.5;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 1080px) {
  .workflow-path {
    grid-template-columns: repeat(5, minmax(6rem, 1fr));
  }

  .workflow-path > p {
    grid-column: 1 / -1;
    border-top: 1px solid var(--line-dark);
    text-align: left;
  }
}

@media (max-width: 900px) {
  .content-area.view-graph .panel-wrapper.right,
  .content-area.view-workbench .panel-wrapper.left {
    display: none !important;
  }

  .content-area.view-graph .panel-wrapper.left,
  .content-area.view-workbench .panel-wrapper.right {
    display: block !important;
    width: 100% !important;
    opacity: 1 !important;
    transform: none !important;
  }
}

@media (max-width: 620px) {
  .workspace-error {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace-error .workspace-error-actions {
    display: grid;
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .workflow-path {
    display: none;
  }

  .mobile-workflow-picker {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 0.75rem;
    padding: 0.65rem 1rem;
    border-bottom: 1px solid var(--line-dark);
    background: var(--ink);
    color: var(--paper-muted);
  }

  .mobile-workflow-picker > span {
    font-family: var(--font-display);
    font-size: 0.72rem;
    letter-spacing: 0.045em;
    text-transform: uppercase;
  }

  .mobile-workflow-picker select {
    width: 100%;
    min-height: 2.75rem;
    padding: 0.45rem 2rem 0.45rem 0.65rem;
    border: 1px solid var(--line-dark);
    border-radius: 0;
    background: var(--ink-deep);
    color: var(--paper);
    font-family: var(--font-body);
    font-size: 0.85rem;
  }

  .workspace-error {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

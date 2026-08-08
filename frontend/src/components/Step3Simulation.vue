<template>
  <div class="simulation-panel">
    <Step3RunWayfinder
      :run-status="runStatus"
      :actions="chronologicalActions"
      :phase="phase"
      :is-starting="isStarting"
      :start-error="startError"
      :live-update-error="liveUpdateError"
      :report-error="reportError"
      :can-review="canGenerateReport"
      :is-reviewing="isGeneratingReport"
      :project-data="projectData"
      :max-rounds="maxRounds"
      :preflight="preflight"
      :diagnostics="diagnostics"
      :diagnostics-error="diagnosticsError"
      :metrics="metricsData"
      :metrics-loading="loadingMetrics"
      :metrics-error="metricsError"
      :system-logs="systemLogs"
      @review="handleNextStep"
      @load-metrics="fetchMetrics"
      @retry-run="retryRun"
      @start-over="$emit('go-back')"
      @reconnect="reconnectRun"
    />
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { generateReport } from "../api/report";
import {
  getRunStatus,
  getSimulationActions,
  getSimulationDiagnostics,
  getSimulationMetrics,
  getSimulationPreflight,
  startSimulation,
} from "../api/simulation";
import { connectSimulationWs } from "../api/ws";
import Step3RunWayfinder from "./Step3RunWayfinder.vue";

const props = defineProps({
  simulationId: String,
  maxRounds: Number,
  minutesPerRound: {
    type: Number,
    default: 15,
  },
  projectData: {
    type: Object,
    default: () => ({}),
  },
  graphData: {
    type: Object,
    default: () => ({}),
  },
  systemLogs: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["go-back", "next-step", "add-log", "update-status"]);
const router = useRouter();

const phase = ref(0);
const isStarting = ref(false);
const isGeneratingReport = ref(false);
const startError = ref(null);
const liveUpdateError = ref(null);
const reportError = ref(null);
const runStatus = ref({});
const allActions = ref([]);
const actionIds = ref(new Set());
const preflight = ref(null);
const diagnostics = ref(null);
const diagnosticsError = ref(null);
const metricsData = ref(null);
const loadingMetrics = ref(false);
const metricsError = ref(null);
const previousShortPostRound = ref(0);
const previousCommunityRound = ref(0);

let simulationWs = null;

const chronologicalActions = computed(() =>
  [...allActions.value].sort((left, right) => {
    const roundDifference =
      Number(left.round_num || 0) - Number(right.round_num || 0);
    if (roundDifference) return roundDifference;

    const timeDifference = String(left.timestamp || "").localeCompare(
      String(right.timestamp || ""),
    );
    return timeDifference || Number(left._sequence || 0) - Number(right._sequence || 0);
  }),
);

const canGenerateReport = computed(
  () =>
    phase.value === 2 &&
    !["failed", "interrupted"].includes(runStatus.value.runner_status),
);

const addLog = (message) => emit("add-log", message);

const readableError = (error, fallback) =>
  error?.message || String(error || "").trim() || fallback;

const fetchMetrics = async (force = false) => {
  if (!props.simulationId || loadingMetrics.value) return;

  loadingMetrics.value = true;
  metricsError.value = null;
  try {
    const response = await getSimulationMetrics(props.simulationId, force);
    if (response.success && response.data) {
      metricsData.value = response.data;
    } else {
      metricsError.value =
        response.error || "The interaction summary is not available.";
    }
  } catch (error) {
    metricsError.value = readableError(
      error,
      "The interaction summary is not available.",
    );
  } finally {
    loadingMetrics.value = false;
  }
};

const fetchExecutionContracts = async () => {
  const simulationId = props.simulationId;
  if (!simulationId) return;

  diagnosticsError.value = null;
  const [preflightResult, diagnosticsResult] = await Promise.allSettled([
    getSimulationPreflight(simulationId),
    getSimulationDiagnostics(simulationId),
  ]);

  if (simulationId !== props.simulationId) return;

  if (
    preflightResult.status === "fulfilled" &&
    preflightResult.value.success
  ) {
    preflight.value = preflightResult.value.data;
  }

  if (
    diagnosticsResult.status === "fulfilled" &&
    diagnosticsResult.value.success
  ) {
    diagnostics.value = diagnosticsResult.value.data;
    return;
  }

  diagnosticsError.value =
    diagnosticsResult.status === "fulfilled"
      ? diagnosticsResult.value.error || "Run details are not available."
      : readableError(
          diagnosticsResult.reason,
          "Run details are not available.",
        );
};

const stopWs = () => {
  const connection = simulationWs;
  simulationWs = null;
  connection?.close();
};

const resetRuntime = () => {
  stopWs();
  phase.value = 0;
  isStarting.value = false;
  isGeneratingReport.value = false;
  startError.value = null;
  liveUpdateError.value = null;
  reportError.value = null;
  runStatus.value = {};
  allActions.value = [];
  actionIds.value = new Set();
  previousShortPostRound.value = 0;
  previousCommunityRound.value = 0;
  metricsData.value = null;
  metricsError.value = null;
};

const actionIdentity = (action, index) =>
  String(
    action?.id ||
      [
        action?.timestamp,
        action?.platform,
        action?.round_num,
        action?.agent_id,
        action?.action_type,
        JSON.stringify(action?.action_args || {}),
        index,
      ].join("|"),
  );

const mergeActions = (incoming) => {
  if (!Array.isArray(incoming)) return;

  incoming.forEach((action, index) => {
    const identity = actionIdentity(action, index);
    if (actionIds.value.has(identity)) return;

    actionIds.value.add(identity);
    allActions.value.push({
      ...action,
      _uniqueId: identity,
      _sequence: allActions.value.length,
    });
  });
};

const loadSavedActions = async () => {
  if (!props.simulationId) return;

  try {
    const response = await getSimulationActions(props.simulationId);
    if (response.success && response.data) {
      mergeActions(response.data.actions || response.data);
    }
  } catch {
    // The primary run state remains usable when its optional activity feed is
    // temporarily unavailable.
  }
};

const platformsAreComplete = (state) => {
  if (!state) return false;

  const shortPostComplete = state.twitter_completed === true;
  const communityComplete = state.reddit_completed === true;
  const shortPostEnabled =
    Number(state.twitter_actions_count || 0) > 0 ||
    state.twitter_running ||
    shortPostComplete;
  const communityEnabled =
    Number(state.reddit_actions_count || 0) > 0 ||
    state.reddit_running ||
    communityComplete;

  if (!shortPostEnabled && !communityEnabled) return false;
  if (shortPostEnabled && !shortPostComplete) return false;
  if (communityEnabled && !communityComplete) return false;
  return true;
};

const finishRun = async (state) => {
  runStatus.value = {
    ...runStatus.value,
    ...(state || {}),
    runner_status:
      state?.runner_status === "stopped" ? "stopped" : "completed",
  };
  phase.value = 2;
  stopWs();
  addLog("Scenario run complete.");
  emit("update-status", "completed");

  await Promise.all([fetchMetrics(), loadSavedActions()]);
};

const handleWsFrame = async (frame) => {
  if (frame.type === "state") {
    const state = frame;
    runStatus.value = state;

    if (["failed", "interrupted"].includes(state.runner_status)) {
      phase.value = 2;
      stopWs();
      addLog(
        `The scenario run stopped unexpectedly: ${
          state.error || "no reason was provided"
        }`,
      );
      emit("update-status", "error");
      return;
    }

    if (
      Number(state.twitter_current_round || 0) >
      previousShortPostRound.value
    ) {
      addLog(
        `Short-post route: round ${state.twitter_current_round}/${state.total_rounds}, ${
          state.twitter_actions_count || 0
        } generated actions.`,
      );
      previousShortPostRound.value = Number(state.twitter_current_round);
    }

    if (
      Number(state.reddit_current_round || 0) >
      previousCommunityRound.value
    ) {
      addLog(
        `Topic-community route: round ${state.reddit_current_round}/${state.total_rounds}, ${
          state.reddit_actions_count || 0
        } generated actions.`,
      );
      previousCommunityRound.value = Number(state.reddit_current_round);
    }

    mergeActions(state.recent_actions);

    if (
      ["completed", "stopped"].includes(state.runner_status) ||
      platformsAreComplete(state)
    ) {
      await finishRun(state);
    }
    return;
  }

  if (frame.type === "done") {
    await finishRun(frame);
    return;
  }

  if (frame.type === "error") {
    liveUpdateError.value =
      "Live updates stopped. Reconnect to check the saved run.";
    addLog(`Live updates were interrupted: ${frame.message || "unknown error"}`);
  }
};

const startWs = () => {
  if (!props.simulationId) return;

  stopWs();
  liveUpdateError.value = null;
  let connection = null;
  connection = connectSimulationWs(props.simulationId, {
    onMessage: handleWsFrame,
    onClose: () => {
      if (simulationWs !== connection) return;
      simulationWs = null;
      if (phase.value === 1) {
        liveUpdateError.value =
          "Live updates stopped. Reconnect to check the saved run.";
      }
    },
    onError: (error) => {
      liveUpdateError.value =
        "Live updates stopped. Reconnect to check the saved run.";
      if (import.meta.env.DEV) {
        console.warn("Scenario live-update connection error", error);
      }
    },
  });
  simulationWs = connection;
};

const doStartSimulation = async () => {
  if (!props.simulationId) {
    addLog("The scenario workspace reference is missing.");
    return;
  }

  resetRuntime();
  isStarting.value = true;
  addLog("Starting both synthetic conversation spaces…");
  emit("update-status", "processing");

  try {
    const params = {
      simulation_id: props.simulationId,
      platform: "parallel",
      force: false,
      // Generated observations remain separate from the source-backed graph.
      enable_graph_memory_update: false,
    };

    if (props.maxRounds) {
      params.max_rounds = props.maxRounds;
      addLog(`Scenario length: ${props.maxRounds} rounds.`);
    }

    const response = await startSimulation(params);
    if (!response.success || !response.data) {
      throw new Error(response.error || "The scenario run could not start.");
    }

    runStatus.value = response.data;
    phase.value = 1;
    addLog("Scenario run started.");
    startWs();
  } catch (error) {
    startError.value = readableError(
      error,
      "The scenario run could not start.",
    );
    addLog(`Scenario run could not start: ${startError.value}`);
    emit("update-status", "error");
  } finally {
    isStarting.value = false;
  }
};

const hydrateOrStartSimulation = async () => {
  if (!props.simulationId) return;

  startError.value = null;
  try {
    const response = await getRunStatus(props.simulationId);
    if (!response.success || !response.data) {
      throw new Error(
        response.error || "The saved run status is not available.",
      );
    }

    const savedState = response.data;
    const runnerStatus = savedState.runner_status || "idle";

    if (["starting", "running", "stopping"].includes(runnerStatus)) {
      runStatus.value = savedState;
      phase.value = 1;
      previousShortPostRound.value = Number(
        savedState.twitter_current_round || 0,
      );
      previousCommunityRound.value = Number(
        savedState.reddit_current_round || 0,
      );
      addLog("Reconnected to the saved scenario run.");
      emit("update-status", "processing");
      await loadSavedActions();
      startWs();
      return;
    }

    if (
      ["completed", "stopped", "failed", "interrupted"].includes(runnerStatus)
    ) {
      runStatus.value = savedState;
      phase.value = 2;
      const completed = ["completed", "stopped"].includes(runnerStatus);
      addLog(
        completed
          ? "Opened the completed scenario run."
          : "Opened a scenario run that needs attention.",
      );
      emit("update-status", completed ? "completed" : "error");
      await loadSavedActions();
      if (completed) await fetchMetrics();
      return;
    }

    if (runnerStatus === "idle") {
      await doStartSimulation();
      return;
    }

    throw new Error(`Saved run has an unsupported status: ${runnerStatus}`);
  } catch (error) {
    startError.value = `Saved run status could not be read: ${readableError(
      error,
      "unknown error",
    )}`;
    addLog(startError.value);
    emit("update-status", "error");
  }
};

const retryRun = async () => {
  if (isStarting.value) return;
  await hydrateOrStartSimulation();
};

const reconnectRun = async () => {
  if (!props.simulationId) return;
  liveUpdateError.value = null;
  await hydrateOrStartSimulation();
};

const handleNextStep = async () => {
  if (!props.simulationId || isGeneratingReport.value) return;

  isGeneratingReport.value = true;
  reportError.value = null;
  addLog("Preparing the decision brief…");

  try {
    const response = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true,
    });
    const reportId = response.success ? response.data?.report_id : null;
    if (!reportId) {
      throw new Error(response.error || "The decision brief could not be prepared.");
    }

    addLog("Decision brief preparation started.");
    await router.push({ name: "Report", params: { reportId } });
  } catch (error) {
    reportError.value = readableError(
      error,
      "The decision brief could not be prepared. Try again.",
    );
    addLog(
      `Decision brief preparation failed: ${reportError.value}`,
    );
    isGeneratingReport.value = false;
  }
};

watch(
  () => props.simulationId,
  (simulationId, previousSimulationId) => {
    if (simulationId === previousSimulationId && previousSimulationId) return;

    resetRuntime();
    preflight.value = null;
    diagnostics.value = null;
    diagnosticsError.value = null;
    if (!simulationId) return;

    addLog("Scenario run opened.");
    void fetchExecutionContracts();
    void hydrateOrStartSimulation();
  },
  { immediate: true },
);

onUnmounted(stopWs);
</script>

<style scoped>
.simulation-panel {
  width: 100%;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--ink-deep); backdrop-filter: none;
}
</style>

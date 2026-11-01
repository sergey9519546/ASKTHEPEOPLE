<template>
  <div class="simulation-panel">
    <Step3RunWayfinder
      :key="runSessionKey"
      :run-status="runStatus"
      :actions="displayedRecords"
      :activity-held="held"
      :pending-count="pendingCount"
      :pending-overflow="pendingOverflow"
      :activity-evicted="hasEvicted"
      :activity-limit="RUN_ACTIVITY_LIMIT"
      :selected-record="selectedRecord"
      :history-error="historyError"
      :phase="phase"
      :is-starting="isStarting"
      :start-error="startError"
      :live-update-error="liveUpdateError"
      :connection-status="connectionStatus"
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
      @hold-view="holdView"
      @show-latest="showLatest"
      @inspect-record="selectRecord"
      @close-inspector="clearSelection"
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
import { RUN_ACTIVITY_LIMIT, useRunActivity } from "../composables/useRunActivity";
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
const connectionStatus = ref("disconnected");
const reportError = ref(null);
const runStatus = ref({});
const historyError = ref(null);
const runSessionKey = ref(0);
const {
  displayedRecords,
  held,
  pendingCount,
  pendingOverflow,
  hasEvicted,
  selectedRecord,
  mergeActions,
  holdView,
  showLatest,
  selectRecord,
  clearSelection,
  reset: resetActivity,
} = useRunActivity();
const preflight = ref(null);
const diagnostics = ref(null);
const diagnosticsError = ref(null);
const metricsData = ref(null);
const loadingMetrics = ref(false);
const metricsError = ref(null);
const previousShortPostRound = ref(0);
const previousCommunityRound = ref(0);

let simulationWs = null;
let sessionGeneration = 0;
let socketGeneration = 0;
let historyRequest = 0;
let disposed = false;

// An ID check alone cannot distinguish a retry or an A -> B -> A switch.
const captureSession = () => ({
  simulationId: props.simulationId,
  generation: sessionGeneration,
});
const isCurrentSession = (session) =>
  !disposed &&
  session.generation === sessionGeneration &&
  session.simulationId === props.simulationId;

const canGenerateReport = computed(
  () =>
    phase.value === 2 &&
    !["failed", "interrupted"].includes(runStatus.value.runner_status),
);

const addLog = (message) => emit("add-log", message);

const readableError = (error, fallback) =>
  error?.message || String(error || "").trim() || fallback;

const fetchMetrics = async (force = false, session = captureSession()) => {
  if (!isCurrentSession(session) || !session.simulationId || loadingMetrics.value) return;

  loadingMetrics.value = true;
  metricsError.value = null;
  try {
    const response = await getSimulationMetrics(session.simulationId, force);
    if (!isCurrentSession(session)) return;
    if (response.success && response.data) {
      metricsData.value = response.data;
    } else {
      metricsError.value =
        response.error || "The interaction summary is not available.";
    }
  } catch (error) {
    if (!isCurrentSession(session)) return;
    metricsError.value = readableError(
      error,
      "The interaction summary is not available.",
    );
  } finally {
    if (isCurrentSession(session)) loadingMetrics.value = false;
  }
};

const fetchExecutionContracts = async (session = captureSession()) => {
  if (!isCurrentSession(session) || !session.simulationId) return;

  diagnosticsError.value = null;
  const [preflightResult, diagnosticsResult] = await Promise.allSettled([
    getSimulationPreflight(session.simulationId),
    getSimulationDiagnostics(session.simulationId),
  ]);

  if (!isCurrentSession(session)) return;

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
  // Invalidate callbacks before close(), which can synchronously call onClose.
  socketGeneration += 1;
  const connection = simulationWs;
  simulationWs = null;
  connection?.close();
  connectionStatus.value = "disconnected";
};

const invalidateSession = () => {
  sessionGeneration += 1;
  stopWs();
  loadingMetrics.value = false;
  isStarting.value = false;
  isGeneratingReport.value = false;
};

const resetRuntime = () => {
  invalidateSession();
  runSessionKey.value += 1;
  resetActivity();
  phase.value = 0;
  startError.value = null;
  liveUpdateError.value = null;
  reportError.value = null;
  historyError.value = null;
  runStatus.value = {};
  preflight.value = null;
  diagnostics.value = null;
  diagnosticsError.value = null;
  previousShortPostRound.value = 0;
  previousCommunityRound.value = 0;
  metricsData.value = null;
  metricsError.value = null;
};

const loadSavedActions = async (session = captureSession()) => {
  if (!isCurrentSession(session) || !session.simulationId) return;

  const request = ++historyRequest;
  const isCurrentRequest = () =>
    isCurrentSession(session) && request === historyRequest;
  try {
    const response = await getSimulationActions(session.simulationId, {
      limit: RUN_ACTIVITY_LIMIT,
      offset: 0,
    });
    if (!isCurrentRequest()) return;
    const actions = response.data?.actions ?? response.data;
    if (!response.success || !Array.isArray(actions)) throw new Error();
    mergeActions(actions);
    historyError.value = null;
  } catch {
    if (!isCurrentRequest()) return;
    // Do not expose server/provider text or describe an unavailable read as empty.
    historyError.value =
      "Recent activity history is unavailable. Displayed records may be incomplete.";
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

const finishRun = async (state, session) => {
  if (!isCurrentSession(session)) return;
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

  await Promise.all([fetchMetrics(false, session), loadSavedActions(session)]);
};

const handleWsFrame = async (frame, session) => {
  if (!isCurrentSession(session)) return;
  if (frame.type === "state") {
    const state = frame;
    runStatus.value = state;
    // Terminal frames can carry the last saved records too. Holding affects
    // presentation only, never ingestion or the server's run state.
    mergeActions(state.recent_actions);

    if (["failed", "interrupted"].includes(state.runner_status)) {
      phase.value = 2;
      stopWs();
      addLog(
        `The scenario run stopped unexpectedly: ${
          state.error || "no reason was provided"
        }`,
      );
      emit("update-status", "error");
      await loadSavedActions(session);
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

    if (
      ["completed", "stopped"].includes(state.runner_status) ||
      platformsAreComplete(state)
    ) {
      await finishRun(state, session);
    }
    return;
  }

  if (frame.type === "done") {
    mergeActions(frame.recent_actions);
    await finishRun(frame, session);
    return;
  }

  if (frame.type === "error") {
    liveUpdateError.value =
      "The live connection reported an update error. Reconnect to check the saved run.";
    addLog(`Live updates were interrupted: ${frame.message || "unknown error"}`);
  }
};

const startWs = (session) => {
  if (!isCurrentSession(session) || !session.simulationId) return;

  stopWs();
  const generation = socketGeneration;
  const isCurrentSocket = () =>
    isCurrentSession(session) && generation === socketGeneration;
  liveUpdateError.value = null;
  connectionStatus.value = "connecting";
  const connection = connectSimulationWs(session.simulationId, {
    onMessage: (frame) => {
      if (!isCurrentSocket()) return;
      return handleWsFrame(frame, session);
    },
    onStatus: (status) => {
      if (!isCurrentSocket()) return;
      connectionStatus.value = status;
      if (status === "connected" || status === "reconnecting") {
        liveUpdateError.value = null;
      } else if (status === "disconnected" && phase.value === 1) {
        liveUpdateError.value =
          "Live updates stopped. Reconnect to check the saved run.";
      }
    },
    onClose: () => {
      if (!isCurrentSocket()) return;
      socketGeneration += 1;
      simulationWs = null;
      connectionStatus.value = "disconnected";
      if (phase.value === 1) {
        liveUpdateError.value =
          "Live updates stopped. Reconnect to check the saved run.";
      }
    },
    onError: (error) => {
      if (!isCurrentSocket()) return;
      if (import.meta.env.DEV) {
        console.warn("Scenario live-update connection error", error);
      }
    },
  });
  if (isCurrentSocket()) simulationWs = connection;
  else connection?.close();
};

const doStartSimulation = async (session) => {
  if (!isCurrentSession(session)) return;
  if (!session.simulationId) {
    addLog("The scenario workspace reference is missing.");
    return;
  }

  // The caller resets once for a new attempt, before status hydration.
  isStarting.value = true;
  addLog("Starting both generated conversation spaces…");
  emit("update-status", "processing");

  try {
    const params = {
      simulation_id: session.simulationId,
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
    if (!isCurrentSession(session)) return;
    if (!response.success || !response.data) {
      throw new Error(response.error || "The scenario run could not start.");
    }

    runStatus.value = response.data;
    mergeActions(response.data.recent_actions);
    phase.value = 1;
    addLog("Scenario run started.");
    startWs(session);
  } catch (error) {
    if (!isCurrentSession(session)) return;
    startError.value = readableError(
      error,
      "The scenario run could not start.",
    );
    addLog(`Scenario run could not start: ${startError.value}`);
    emit("update-status", "error");
  } finally {
    if (isCurrentSession(session)) isStarting.value = false;
  }
};

const hydrateOrStartSimulation = async (session, resetOnStart = false) => {
  if (!isCurrentSession(session) || !session.simulationId) return;

  startError.value = null;
  try {
    const response = await getRunStatus(session.simulationId);
    if (!isCurrentSession(session)) return;
    if (!response.success || !response.data) {
      throw new Error(
        response.error || "The saved run status is not available.",
      );
    }

    const savedState = response.data;
    const runnerStatus = savedState.runner_status || "idle";

    if (["starting", "running", "stopping"].includes(runnerStatus)) {
      runStatus.value = savedState;
      mergeActions(savedState.recent_actions);
      phase.value = 1;
      previousShortPostRound.value = Number(
        savedState.twitter_current_round || 0,
      );
      previousCommunityRound.value = Number(
        savedState.reddit_current_round || 0,
      );
      addLog("Reconnected to the saved scenario run.");
      emit("update-status", "processing");
      // A slow history read must not prevent incoming state/actions.
      startWs(session);
      await loadSavedActions(session);
      return;
    }

    if (
      ["completed", "stopped", "failed", "interrupted"].includes(runnerStatus)
    ) {
      runStatus.value = savedState;
      mergeActions(savedState.recent_actions);
      phase.value = 2;
      const completed = ["completed", "stopped"].includes(runnerStatus);
      addLog(
        completed
          ? "Opened the completed scenario run."
          : "Opened a scenario run that needs attention.",
      );
      emit("update-status", completed ? "completed" : "error");
      await Promise.all([
        loadSavedActions(session),
        completed ? fetchMetrics(false, session) : Promise.resolve(),
      ]);
      return;
    }

    if (runnerStatus === "idle") {
      // Reconnecting an existing reader preserves it unless the saved state
      // actually requires a new run; then its held view/inspection is obsolete.
      if (resetOnStart) {
        resetRuntime();
        session = captureSession();
        void fetchExecutionContracts(session);
      }
      await doStartSimulation(session);
      return;
    }

    throw new Error(`Saved run has an unsupported status: ${runnerStatus}`);
  } catch (error) {
    if (!isCurrentSession(session)) return;
    startError.value = `Saved run status could not be read: ${readableError(
      error,
      "unknown error",
    )}`;
    addLog(startError.value);
    emit("update-status", "error");
  }
};

const retryRun = async () => {
  if (isStarting.value || !props.simulationId) return;
  resetRuntime();
  const session = captureSession();
  void fetchExecutionContracts(session);
  await hydrateOrStartSimulation(session);
};

const reconnectRun = async () => {
  if (!props.simulationId || isStarting.value) return;
  // Invalidate requests/connections, not the reader snapshot or its child key.
  invalidateSession();
  const session = captureSession();
  liveUpdateError.value = null;
  void fetchExecutionContracts(session);
  await hydrateOrStartSimulation(session, true);
};

const handleNextStep = async () => {
  const session = captureSession();
  if (!isCurrentSession(session) || !session.simulationId || isGeneratingReport.value) return;

  isGeneratingReport.value = true;
  reportError.value = null;
  addLog("Preparing the decision brief…");

  try {
    const response = await generateReport({
      simulation_id: session.simulationId,
      force_regenerate: true,
    });
    if (!isCurrentSession(session)) return;
    const reportId = response.success ? response.data?.report_id : null;
    if (!reportId) {
      throw new Error(response.error || "The decision brief could not be prepared.");
    }

    addLog("Decision brief preparation started.");
    await router.push({ name: "Report", params: { reportId } });
  } catch (error) {
    if (!isCurrentSession(session)) return;
    reportError.value = readableError(
      error,
      "The decision brief could not be prepared. Try again.",
    );
    addLog(`Decision brief preparation failed: ${reportError.value}`);
    isGeneratingReport.value = false;
  }
};

watch(
  () => props.simulationId,
  (simulationId, previousSimulationId) => {
    if (simulationId === previousSimulationId && previousSimulationId) return;

    resetRuntime();
    if (!simulationId) return;

    const session = captureSession();
    addLog("Scenario run opened.");
    void fetchExecutionContracts(session);
    void hydrateOrStartSimulation(session);
  },
  { immediate: true, flush: "sync" },
);

onUnmounted(() => {
  disposed = true;
  invalidateSession();
});
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

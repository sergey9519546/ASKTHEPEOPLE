<template>
  <div class="app-view-root">
    <!-- HEADER -->
    <header class="app-header">
      <a
        class="header-left"
        href="/"
        aria-label="Ask The People / generated Decision Explorer — home"
      >
        <span class="brand-monogram">ATP</span>
        <span class="brand-full">ASK THE PEOPLE</span>
      </a>

      <div class="header-center">
        <div
          class="view-mode-selector"
          role="group"
          aria-label="Choose source map, comparison, or conversation view"
        >
          <button
            v-for="m in ['graph', 'split', 'workbench']"
            :key="m"
            class="mode-btn"
            type="button"
            :class="{ 'is-active': viewMode === m }"
            :aria-pressed="viewMode === m"
            @click="viewMode = m"
          >
            {{ { graph: "Source map", split: "Compare", workbench: "Conversation" }[m] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="step-indicator">
          <span class="step-val">STEP 05/05</span>
          <span class="step-label">Ask follow-up questions</span>
        </div>
        <div class="status-box" :class="currentStatus" aria-live="polite">
          <span class="status-dot"></span>
          <span class="status-msg">{{ statusLabel }}</span>
        </div>
      </div>
    </header>

    <!-- CONTENT -->
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <h1 class="view-title">Explore the findings</h1>
    <main id="main-content" class="workbench-viewport" :class="`mode-${viewMode}`">
      <!-- LEFT: GRAPH -->
      <div
        class="panel-container left"
        :style="leftPanelStyle"
        :aria-hidden="viewMode === 'workbench' ? 'true' : undefined"
        :inert="viewMode === 'workbench' ? '' : undefined"
        aria-label="Supporting source map"
      >
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="5"
          :isSimulating="false"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- RIGHT: WORKBENCH -->
      <div
        class="panel-container right"
        :style="rightPanelStyle"
        :aria-hidden="viewMode === 'graph' ? 'true' : undefined"
        :inert="viewMode === 'graph' ? '' : undefined"
        aria-label="Follow-up conversation"
      >
        <div class="workbench-frame">
          <header class="workbench-header">
            <span class="wb-label">Ask the report or explore fictional responses</span>
          </header>
          <div class="wb-content">
            <section
              v-if="error"
              ref="shellError"
              class="interaction-shell-state is-error"
              role="alert"
              aria-labelledby="interaction-shell-error-heading"
              tabindex="-1"
            >
              <span class="shell-state-index" aria-hidden="true">!</span>
              <div>
                <p>Follow-up workspace needs attention</p>
                <h1 id="interaction-shell-error-heading">
                  The follow-up workspace could not be opened.
                </h1>
                <p>{{ error }}</p>
                <div class="shell-state-actions">
                  <button
                    class="shell-retry"
                    type="button"
                    :disabled="currentStatus === 'processing'"
                    @click="loadReportData"
                  >
                    {{
                      currentStatus === "processing"
                        ? "Trying again…"
                        : "Retry opening follow-up questions"
                    }}
                  </button>
                  <button
                    class="shell-home"
                    type="button"
                    @click="router.push({ name: 'Home' })"
                  >
                    Return home
                  </button>
                </div>
              </div>
            </section>
            <section
              v-else-if="currentStatus === 'processing' || !simulationId"
              class="interaction-shell-state is-loading"
              role="status"
              aria-live="polite"
            >
              <span class="shell-state-index" aria-hidden="true">05</span>
              <div>
                <p>Opening follow-up questions</p>
                <h1>Loading the report and its saved run.</h1>
                <div class="shell-loading-route" aria-hidden="true">
                  <span></span>
                </div>
              </div>
            </section>
            <Step5Interaction
              v-else
              :reportId="currentReportId"
              :simulationId="simulationId"
              :systemLogs="systemLogs"
              @add-log="addLog"
              @update-status="updateStatus"
            />
          </div>
        </div>
      </div>
    </main>

    <!-- FOOTER -->
    <footer class="app-footer-mini">
      <div class="f-block">0 human respondents · not a forecast</div>
      <div class="f-block">Fictional generated responses are not interviews</div>
    </footer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useWindowRoute } from "../composables/useWindowContext.js";
import { useWorkspaceState } from "../composables/useWorkspaceState.js";
import { getGraphData, getProject } from "../api/graph";
import { getReport } from "../api/report";
import { getSimulation } from "../api/simulation";
import {
  normalizeStatus,
  useStatusPresentation,
} from "../composables/useStatusPresentation.js";
import GraphPanel from "../components/GraphPanel.vue";
import Step5Interaction from "../components/Step5Interaction.vue";
import {
  RecordedGraphIdentityError,
  recordedGraphReadError,
  resolveRecordedGraphIdentity,
} from "../utils/recordedGraphIdentity";

const router = useRouter();
const windowRoute = useWindowRoute();
const { setContext } = useWorkspaceState();

const viewMode = ref("workbench");
const currentReportId = ref(windowRoute.value.params.reportId);
if (currentReportId.value) setContext({ reportId: currentReportId.value });
const simulationId = ref(null);
const projectData = ref(null);
const graphIdentity = ref(null);
const graphData = ref(null);
const graphLoading = ref(false);
const systemLogs = ref([]);
const error = ref("");
const shellError = ref(null);
const currentStatus = ref("processing");
let loadSequence = 0;
const statusLabel = useStatusPresentation(currentStatus, {
  labels: {
    processing: "OPENING",
    ready: "READY",
    error: "NEEDS ATTENTION",
  },
  fallback: (status) => status.toUpperCase(),
}).label;

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
  if (systemLogs.value.length > 200) systemLogs.value.shift();
};

const updateStatus = (status) => {
  currentStatus.value = normalizeStatus(status, {
    allowed: ["processing", "ready", "error"],
    fallback: "error",
  });
};

const toggleMaximize = (target) =>
  (viewMode.value = viewMode.value === target ? "split" : target);

const loadReportData = async () => {
  const sequence = ++loadSequence;
  currentStatus.value = "processing";
  error.value = "";
  simulationId.value = null;
  projectData.value = null;
  graphIdentity.value = null;
  graphData.value = null;

  try {
    addLog("Opening follow-up questions…");
    const reportRes = await getReport(currentReportId.value);
    if (sequence !== loadSequence) return;
    if (!reportRes?.success || !reportRes?.data) {
      throw new Error("report_unavailable");
    }

    const reportData = reportRes.data;
    simulationId.value = reportData.simulation_id;
    if (!simulationId.value) {
      error.value =
        "The saved report is missing its linked scenario run. Return home and reopen the project.";
      currentStatus.value = "error";
      addLog("This report is missing its linked scenario run.");
      await nextTick();
      shellError.value?.focus();
      return;
    }

    const simRes = await getSimulation(simulationId.value);
    if (sequence !== loadSequence) return;
    if (!simRes?.success || !simRes?.data) {
      throw new Error("simulation_unavailable");
    }

    const simData = simRes.data;
    if (simData.project_id) {
      try {
        const projRes = await getProject(simData.project_id);
        if (sequence !== loadSequence) return;
        if (projRes?.success && projRes.data) {
          projectData.value = projRes.data;
          graphIdentity.value = resolveRecordedGraphIdentity({
            project: projRes.data,
            report: reportData,
            simulation: simData,
          });
          await loadGraph(
            graphIdentity.value.projectId,
            graphIdentity.value.graphId,
          );
        }
      } catch (err) {
        if (err instanceof RecordedGraphIdentityError) throw err;
        addLog("The supporting source map could not be loaded.");
      }
    }

    if (sequence !== loadSequence) return;
    currentStatus.value = "ready";
  } catch (err) {
    if (sequence !== loadSequence) return;
    error.value =
      err instanceof RecordedGraphIdentityError
        ? err.message
        : "The saved report or its linked run is unavailable right now. Check the link and try again, or return home.";
    currentStatus.value = "error";
    addLog("The follow-up workspace could not be opened.");
    await nextTick();
    shellError.value?.focus();
  }
};

const loadGraph = async (projectId, graphId) => {
  graphLoading.value = true;
  try {
    const res = await getGraphData(projectId, graphId);
    if (!res.success || !res.data) throw recordedGraphReadError(res);
    graphData.value = res.data;
  } catch (err) {
    addLog("The supporting source map could not be refreshed.");
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
  } catch (err) {
    error.value =
      err instanceof RecordedGraphIdentityError
        ? err.message
        : "The recorded source map is temporarily unavailable.";
    currentStatus.value = "error";
    addLog("The recorded source map could not be refreshed.");
  }
};

watch(
  () => windowRoute.value.params.reportId,
  (newId) => {
    if (!newId) return;
    currentReportId.value = newId;
    loadReportData();
  },
  { immediate: true },
);

onMounted(() => {
  addLog("Follow-up workspace opened.");
});
</script>

<style scoped>
.app-view-root {
  height: 100vh;
  background: var(--ink);
  color: var(--paper);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  height: 70px;
  flex: 0 0 70px;
  background: var(--ink-deep);
  border-bottom: 3px solid var(--signal);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 2.75rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  text-transform: none;
  transform: none;
}

.header-left:hover {
  border: 0;
  background: transparent;
  color: inherit;
  transform: none;
}
.brand-monogram {
  border: 1px solid var(--signal);
  background: var(--ink-deep);
  color: var(--signal);
  padding: 5px 9px 4px;
  font-family: var(--font-display);
  font-size: 1.18rem;
  line-height: 1;
  letter-spacing: 0.04em;
}
.brand-full {
  font-family: var(--font-display);
  font-size: 1.28rem;
  letter-spacing: 0.045em;
}

.view-mode-selector {
  display: flex;
  border: 1px solid var(--line-dark);
  background: var(--ink);
  padding: 0;
  gap: 0;
}
.mode-btn {
  border: none !important;
  background: transparent !important;
  border-right: 1px solid var(--line-dark) !important;
  padding: 8px 16px 7px !important;
  color: var(--paper-muted) !important;
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 0.68rem;
  letter-spacing: 0.075em;
  text-transform: uppercase;
  cursor: pointer;
  border-radius: 0 !important;
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
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 0.7rem;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}
.step-val {
  color: var(--signal);
  font-family: var(--font-sans);
}
.status-box {
  display: flex;
  align-items: center;
  gap: 8px;
  border-left: 1px solid var(--line-dark);
  padding-left: 1rem;
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 0.65rem;
  letter-spacing: 0.08em;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-box.processing .status-dot {
  background: var(--signal) !important;
  animation: flash 1s infinite alternate;
}
.status-box.ready .status-dot {
  background: var(--success) !important;
}
.status-box.error .status-dot {
  background: var(--error) !important;
}
@keyframes flash {
  from { opacity: 0.3; }
  to { opacity: 1; }
}

.workbench-viewport {
  flex: 1;
  display: flex;
  padding: 18px;
  gap: 18px;
  overflow: hidden;
  position: relative;
}
.panel-container {
  height: 100%;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  background: var(--paper);
  border: 2px solid var(--line-dark);
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
  height: 50px;
  flex: 0 0 50px;
  border-bottom: 3px solid var(--ink);
  display: flex;
  align-items: center;
  padding: 0 20px;
  background: var(--ink-raised);
}
.wb-label {
  font-weight: 700;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  color: var(--paper);
  text-transform: uppercase;
}
.wb-content {
  flex: 1;
  overflow-y: auto;
  padding: 0px;
}

.interaction-shell-state {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  gap: 1.5rem;
  align-content: center;
  min-height: 100%;
  padding: clamp(1.5rem, 6vw, 6rem);
  background: var(--paper);
  color: var(--ink);
}

.shell-state-index {
  display: grid;
  width: 4.25rem;
  height: 4.25rem;
  place-items: center;
  border: 2px solid var(--signal);
  background: var(--ink-deep);
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1.65rem;
}

.interaction-shell-state.is-error .shell-state-index {
  background: var(--error);
  color: var(--paper-strong);
}

.interaction-shell-state > div {
  max-width: 48rem;
  padding-top: 0.4rem;
  border-top: 0.65rem solid var(--signal);
}

.interaction-shell-state.is-error > div {
  border-top-color: var(--error);
}

.interaction-shell-state > div > p:first-child {
  margin: 0.8rem 0 0.4rem;
  color: var(--signal-text);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.interaction-shell-state.is-error > div > p:first-child {
  color: var(--error-text);
}

.interaction-shell-state h1 {
  max-width: 15ch;
  margin: 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: clamp(3rem, 7vw, 6.2rem);
  font-weight: 400;
  line-height: 0.9;
}

.interaction-shell-state h1 + p {
  max-width: 54ch;
  margin: 1.2rem 0 0;
  color: var(--ink-muted);
  font-size: 1rem;
  line-height: 1.55;
}

.shell-state-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.5rem;
}

.shell-retry,
.shell-home {
  min-height: 3.25rem;
  padding: 0.75rem 1.1rem;
  border: 2px solid var(--ink);
  border-radius: 0;
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.shell-retry {
  background: var(--signal);
  color: var(--ink);
}

.shell-home {
  background: var(--ink);
  color: var(--paper);
}

.shell-loading-route {
  width: min(100%, 32rem);
  height: 0.6rem;
  margin-top: 1.5rem;
  overflow: hidden;
  border: 1px solid var(--ink);
  background: var(--line-light);
}

.shell-loading-route span {
  display: block;
  width: 100%;
  height: 100%;
  background: var(--signal);
  transform: scaleX(0.35);
  transform-origin: left;
  animation: open-followup 1.2s var(--ease-out) infinite alternate;
}

@keyframes open-followup {
  to {
    transform: scaleX(1);
  }
}

.app-footer-mini {
  height: 40px;
  flex: 0 0 40px;
  padding: 0 40px;
  border-top: 1px solid var(--line-dark);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 0.65rem;
  letter-spacing: 0.055em;
  color: var(--paper-muted);
  background: var(--ink-deep);
  text-transform: uppercase;
}

@media (max-width: 1100px) {
  .workbench-viewport {
    flex-direction: column;
    padding: 0.75rem;
    gap: 0.75rem;
  }

  .workbench-viewport.mode-workbench .panel-container.left,
  .workbench-viewport.mode-graph .panel-container.right {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    border: 0;
    opacity: 0 !important;
  }

  .workbench-viewport.mode-workbench .panel-container.right,
  .workbench-viewport.mode-graph .panel-container.left {
    display: block !important;
    width: 100% !important;
    height: calc(100dvh - 11rem) !important;
    min-height: 32rem !important;
    margin: 0 !important;
  }

  .workbench-viewport.mode-split .panel-container {
    display: block !important;
    width: 100% !important;
    height: calc(50dvh - 2rem) !important;
    min-height: 28rem !important;
    margin-bottom: 0.75rem;
  }
}

@media (max-width: 760px) {
  .app-header {
    height: auto;
    min-height: 0;
    flex: 0 0 auto;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 0.65rem;
    padding: 0.8rem 0.9rem;
  }

  .brand-full,
  .step-label,
  .status-msg {
    display: none;
  }

  .header-center {
    order: 3;
    flex: 0 0 100% !important;
    width: 100% !important;
    min-width: 100% !important;
    padding: 0 0 0.55rem !important;
  }

  .view-mode-selector {
    width: 100%;
  }

  .mode-btn {
    flex: 1;
    padding-inline: 0.45rem !important;
  }

  .header-right {
    width: auto !important;
    margin-left: auto;
    padding: 0.8rem 0.9rem !important;
    border-top: 0 !important;
    border-left: 1px solid var(--line-dark) !important;
    gap: 0.7rem;
  }

  .workbench-viewport.mode-workbench .panel-container.right,
  .workbench-viewport.mode-graph .panel-container.left {
    height: calc(100dvh - 10.75rem) !important;
    min-height: 28rem !important;
  }

  .workbench-header {
    min-height: 3rem;
    height: auto;
    padding: 0.65rem 0.8rem;
  }

  .app-footer-mini {
    height: auto;
    min-height: 2.5rem;
    flex: 0 0 auto;
    padding: 0.5rem 0.8rem;
  }

  .app-footer-mini .f-block:last-child {
    display: none;
  }

  .interaction-shell-state {
    grid-template-columns: 1fr;
    align-content: start;
    padding: 1.5rem 1rem;
  }

  .interaction-shell-state h1 {
    font-size: clamp(3rem, 15vw, 4.5rem);
  }

  .shell-state-actions {
    display: grid;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-box.processing .status-dot,
  .shell-loading-route span {
    animation: none;
    transform: none;
  }
}
</style>

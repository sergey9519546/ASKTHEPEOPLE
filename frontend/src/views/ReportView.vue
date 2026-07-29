<template>
  <div class="bauhaus-view-root">
    <!-- HEADER -->
    <header class="bauhaus-header">
      <button
        class="header-left"
        type="button"
        aria-label="Ask The People — home"
        @click="router.push('/')"
      >
        <span class="brand-monogram">ATP</span>
        <span class="brand-full">ASK THE PEOPLE</span>
      </button>

      <div class="header-center">
        <div
          class="view-mode-selector"
          role="group"
          aria-label="Choose source map, comparison, or decision-brief view"
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
            {{ { graph: "Source map", split: "Compare", workbench: "Decision steps" }[m] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="step-indicator">
          <span class="step-val">STEP 04/05</span>
          <span class="step-label">Review the run</span>
        </div>
        <div class="status-box" :class="currentStatus" aria-live="polite">
          <span class="status-dot"></span>
          <span class="status-msg">{{ statusLabel }}</span>
        </div>
      </div>
    </header>

    <!-- CONTENT -->
    <main class="workbench-viewport" :class="`mode-${viewMode}`">
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
          :currentPhase="4"
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
        aria-label="Decision brief"
      >
        <div class="workbench-frame">
          <header class="workbench-header">
            <span class="wb-label">Review findings, related records, and limits</span>
          </header>
          <div class="wb-content">
            <section
              v-if="error"
              ref="shellError"
              class="report-shell-error"
              role="alert"
              aria-labelledby="report-shell-error-heading"
              tabindex="-1"
            >
              <span aria-hidden="true">!</span>
              <div>
                <p>Report needs attention</p>
                <h1 id="report-shell-error-heading">
                  This report could not be opened.
                </h1>
                <p>{{ error }}</p>
                <div>
                  <button
                    type="button"
                    class="shell-retry"
                    :disabled="currentStatus === 'processing'"
                    @click="loadReportData"
                  >
                    {{
                      currentStatus === "processing"
                        ? "Trying again…"
                        : "Retry loading report"
                    }}
                  </button>
                  <button
                    type="button"
                    class="shell-home"
                    @click="router.push({ name: 'Home' })"
                  >
                    Return home
                  </button>
                </div>
              </div>
            </section>
            <Step4Report
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
    <footer class="bauhaus-footer-mini">
      <div class="f-block">Synthetic report · 0 human respondents</div>
      <div class="f-block">Validate material decisions with people</div>
    </footer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getGraphData, getProject } from "../api/graph";
import { getReport } from "../api/report";
import { getSimulation } from "../api/simulation";
import GraphPanel from "../components/GraphPanel.vue";
import Step4Report from "../components/Step4Report.vue";

const route = useRoute();
const router = useRouter();

const viewMode = ref("workbench");
const currentReportId = ref(route.params.reportId);
const simulationId = ref(null);
const projectData = ref(null);
const graphData = ref(null);
const graphLoading = ref(false);
const systemLogs = ref([]);
const error = ref("");
const shellError = ref(null);
const currentStatus = ref("processing");
let loadSequence = 0;

const statusLabel = computed(
  () =>
    ({
      processing: "BUILDING",
      completed: "READY",
      failed: "NEEDS ATTENTION",
    })[currentStatus.value] || "NEEDS ATTENTION",
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
  if (systemLogs.value.length > 200) systemLogs.value.shift();
};

const updateStatus = (status) => {
  currentStatus.value = ["processing", "completed", "failed"].includes(status)
    ? status
    : "failed";
};

const toggleMaximize = (target) =>
  (viewMode.value = viewMode.value === target ? "split" : target);

const loadReportData = async () => {
  const sequence = ++loadSequence;
  error.value = "";
  simulationId.value = null;
  currentStatus.value = "processing";
  addLog("Opening the scenario report…");

  try {
    const reportRes = await getReport(currentReportId.value);
    if (sequence !== loadSequence) return;
    if (!reportRes?.success || !reportRes?.data) {
      throw new Error("report_unavailable");
    }

    const reportData = reportRes.data;
    simulationId.value = reportData.simulation_id;
    currentStatus.value =
      reportData.status === "failed"
        ? "failed"
        : reportData.status === "completed"
          ? "completed"
          : "processing";

    if (!simulationId.value) {
      error.value =
        "The saved report is missing its linked scenario run. Return home and reopen the project.";
      currentStatus.value = "failed";
      addLog("The report is missing its linked scenario run.");
      await nextTick();
      shellError.value?.focus();
      return;
    }

    try {
      const simRes = await getSimulation(simulationId.value);
      if (sequence !== loadSequence) return;
      if (simRes?.success && simRes.data?.project_id) {
        const projRes = await getProject(simRes.data.project_id);
        if (projRes?.success && projRes.data) {
          projectData.value = projRes.data;
          if (projRes.data.graph_id) {
            await loadGraph(projRes.data.graph_id);
          }
        }
      }
    } catch (_) {
      addLog("The source map context could not be loaded.");
    }
  } catch (_) {
    if (sequence !== loadSequence) return;
    error.value =
      "The saved report is unavailable right now. Check the link and try again, or return home.";
    currentStatus.value = "failed";
    addLog("The saved report could not be opened.");
    await nextTick();
    shellError.value?.focus();
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

watch(
  () => route.params.reportId,
  (newId) => {
    if (!newId) return;
    currentReportId.value = newId;
    loadReportData();
  },
  { immediate: true },
);

onMounted(() => {
  addLog("Report workspace opened.");
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
  gap: 0;
  padding: 0;
  border: 1px solid var(--line-dark);
  background: var(--ink);
}
.mode-btn {
  padding: 8px 16px 7px !important;
  border: 0 !important;
  border-right: 1px solid var(--line-dark) !important;
  background: transparent !important;
  color: var(--paper-muted) !important;
  font-family: var(--font-sans);
  font-size: 0.68rem;
  font-weight: 700;
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
  background: var(--success) !important;
}
.status-box.failed .status-dot {
  background: var(--error) !important;
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

.report-shell-error {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  gap: 1.5rem;
  align-content: center;
  min-height: 100%;
  padding: clamp(1.5rem, 6vw, 6rem);
  background: var(--paper);
  color: var(--ink);
}

.report-shell-error > span {
  display: grid;
  width: 4.25rem;
  height: 4.25rem;
  place-items: center;
  background: var(--error);
  color: var(--paper-strong);
  font-family: var(--font-display);
  font-size: 2.5rem;
}

.report-shell-error > div {
  max-width: 48rem;
  padding-top: 0.4rem;
  border-top: 0.65rem solid var(--error);
}

.report-shell-error > div > p:first-child {
  margin: 0.8rem 0 0.4rem;
  color: var(--error);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.report-shell-error h1 {
  max-width: 13ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(3.2rem, 7vw, 6.5rem);
  font-weight: 400;
  line-height: 0.9;
}

.report-shell-error h1 + p {
  max-width: 52ch;
  margin: 1.2rem 0 0;
  color: var(--ink-muted);
  font-size: 1rem;
  line-height: 1.55;
}

.report-shell-error > div > div {
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
  font-weight: 400;
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

.shell-retry:hover:not(:disabled),
.shell-home:hover:not(:disabled) {
  transform: translateX(0.2rem);
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
  .bauhaus-header {
    min-height: 0;
    flex-wrap: wrap;
  }

  .header-center {
    order: 3;
    flex: 0 0 100% !important;
    width: 100% !important;
    min-width: 100% !important;
    padding: 0 0 0.55rem !important;
  }

  .header-right {
    width: auto !important;
    margin-left: auto;
    padding: 0.8rem 0.9rem !important;
    border-top: 0 !important;
    border-left: 1px solid var(--line-dark) !important;
  }

  .view-mode-selector {
    width: 100%;
  }

  .mode-btn {
    flex: 1;
    padding-inline: 0.45rem !important;
  }

  .brand-full,
  .step-label,
  .status-msg {
    display: none;
  }

  .report-shell-error {
    grid-template-columns: 1fr;
    align-content: start;
    padding: 1.5rem 1rem;
  }

  .report-shell-error h1 {
    font-size: clamp(3rem, 15vw, 4.5rem);
  }

  .report-shell-error > div > div {
    display: grid;
  }
}
</style>

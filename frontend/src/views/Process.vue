<template>
  <div class="app-process-root">
    <!-- TOP BAR -->
    <nav class="app-header">
      <div class="header-left" @click="goHome">
        <span class="brand-monogram">ATP</span>
        <span class="brand-full">ASK THE PEOPLE</span>
      </div>

      <div class="header-center">
        <div class="phase-indicator">
          <span class="phase-label">Phase 1</span>
          <span class="phase-name">Map the source material</span>
        </div>
      </div>

      <div class="header-right">
        <div class="system-status" :class="statusClass">
          <span class="status-dot"></span>
          <span class="status-msg">{{ statusText }}</span>
        </div>
      </div>
    </nav>

    <!-- WORKSPACE -->
    <main class="workbench-layout">
      <!-- LEFT: ONTOLOGY VISUALIZATION -->
      <section
        class="workbench-panel graph-panel-v2"
        :class="{ 'is-maximized': isFullScreen }"
      >
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="1"
          @refresh="loadGraphData"
          @toggle-maximize="toggleFullScreen"
        />
      </section>

      <!-- RIGHT: EXECUTION PIPELINE -->
      <section class="workbench-panel pipeline-panel" v-if="!isFullScreen">
        <header class="panel-label-bar">
          <span class="label">Source-mapping progress</span>
        </header>

        <div class="pipeline-scroll">
          <div
            v-for="phase in phases"
            :key="phase.id"
            class="pipeline-step"
            :class="{
              'is-active': currentPhase === phase.id,
              'is-done': currentPhase > phase.id,
            }"
          >
            <div class="step-meta">
              <span class="step-id">0{{ phase.id }}</span>
              <div class="step-info">
                <h4 class="step-title">{{ phase.title }}</h4>
                <div class="step-status-tag">
                  {{
                    currentPhase === phase.id
                      ? "IN PROGRESS"
                      : currentPhase > phase.id
                        ? "READY"
                        : "WAITING"
                  }}
                </div>
              </div>
            </div>

            <Transition name="fade">
              <div v-if="currentPhase === phase.id" class="step-runtime-view">
                <!-- Build Progress for Phase 1 -->
                <div v-if="phase.id === 1" class="progress-container">
                  <div class="progress-track">
                    <div
                      class="progress-thumb"
                      :style="{ width: (buildProgress?.progress || 0) + '%' }"
                    ></div>
                  </div>
                  <div class="progress-stats">
                    <span class="stat-msg">{{
                      buildProgress?.message || "Waiting for source material…"
                    }}</span>
                    <span class="stat-pct"
                      >{{ buildProgress?.progress || 0 }}%</span
                    >
                  </div>
                </div>
                <!-- Info for Phase 2/3 -->
                <div v-else class="ontology-status-box">
                  The source map is ready. Continue to set the scenario assumptions.
                </div>
              </div>
            </Transition>
          </div>

          <!-- LAUNCH CTA -->
          <div class="launch-sequence-box" v-if="currentPhase >= 2">
            <button class="app-cta-btn" @click="goToNextStep">
              SET THE ASSUMPTIONS <span class="arrow">→</span>
            </button>
          </div>
        </div>
      </section>
    </main>

    <!-- FOOTER STATUS -->
    <footer class="app-footer-bar">
      <div class="f-left">Synthetic scenarios · 0 human respondents</div>
      <div class="f-right">Not a forecast</div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  buildGraph,
  getGraphData,
  getProject,
  getTaskStatus,
} from "../api/graph";
import GraphPanel from "../components/GraphPanel.vue";

const route = useRoute();
const router = useRouter();

const currentStep = ref(1);
const phases = [
  { id: 1, title: "Knowledge Construction" },
  { id: 2, title: "Reality Seed Extraction" },
  { id: 3, title: "Entity Relational Map" },
];

const currentPhase = ref(1);
const projectData = ref(null);
const graphData = ref(null);
const buildProgress = ref(null);
const graphLoading = ref(false);
const error = ref("");
const isFullScreen = ref(false);

const currentProjectId = computed(() => route.params.projectId);

const statusClass = computed(() => {
  if (error.value) return "error";
  return currentPhase.value < 3 ? "processing" : "ready";
});

const statusText = computed(() => {
  if (error.value) return "SYS ERROR";
  return currentPhase.value < 3 ? "EXECUTING" : "SEQUENCE READY";
});

const goHome = () => router.push("/");
const goToNextStep = () => {
  router.push({
    name: "Process",
    params: { projectId: currentProjectId.value },
    query: { step: 2 },
  });
};

let pollTimer = null;
const initProject = async () => {
  const result = await getProject(currentProjectId.value);
  if (result.success) {
    projectData.value = result.data;
    startGraphBuild();
  }
};

const startGraphBuild = async () => {
  const result = await buildGraph(currentProjectId.value);
  if (result.success) {
    pollTaskStatus(result.data.task_id);
  }
};

const pollTaskStatus = (taskId) => {
  pollTimer = setInterval(async () => {
    const result = await getTaskStatus(taskId);
    if (result.success) {
      const task = result.data;
      buildProgress.value = {
        progress: task.progress ?? 0,
        message: task.message ?? "",
      };
      if (task.status === "completed") {
        clearInterval(pollTimer);
        currentPhase.value = 2;
        loadGraphData();
      } else if (task.status === "failed") {
        clearInterval(pollTimer);
        error.value = task.error;
      }
    }
  }, 2000);
};

const loadGraphData = async () => {
  const result = await getProject(currentProjectId.value);
  if (result.success && result.data.graph_id) {
    graphLoading.value = true;
    const gRes = await getGraphData(result.data.graph_id);
    if (gRes.success) {
      graphData.value = gRes.data;
    }
    graphLoading.value = false;
  }
};

const toggleFullScreen = () => (isFullScreen.value = !isFullScreen.value);

onMounted(initProject);
onUnmounted(() => pollTimer && clearInterval(pollTimer));
</script>

<style scoped>
.app-process-root {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-void);
  color: var(--text-void);
  overflow: hidden;
  font-family: var(--font-sans);
  position: relative;
}

.app-header {
  height: 60px;
  background: var(--bg-base);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
}
.brand-monogram {
  background: var(--accent);
  color: var(--accent-ink);
  padding: 6px 10px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
}
.brand-full {
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.phase-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  padding: 6px 14px;
}
.phase-label {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 10px;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.phase-name {
  font-family: var(--font-serif);
  font-weight: 500;
  font-size: 13px;
  color: var(--text-void);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.system-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  padding: 6px 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.system-status.processing .status-dot {
  background: var(--accent);
  animation: pulseDot 1.5s ease-in-out infinite;
}
.system-status.ready .status-dot {
  background: var(--accent);
}
.system-status.error .status-dot {
  background: var(--status-error);
}

@keyframes pulseDot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}
.workbench-panel {
  background: var(--bg-base);
  border: 1px solid var(--line);
  border-radius: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  transition: border-color 0.1s ease;
}
.graph-panel-v2 {
  flex: 1.6;
}
.pipeline-panel {
  flex: 1;
  padding: 16px;
}

.graph-panel-v2.is-maximized {
  position: absolute;
  top: 76px;
  left: 16px;
  right: 16px;
  bottom: 56px;
  z-index: 50;
}

.panel-label-bar {
  border-bottom: 1px solid var(--line);
  padding-bottom: 12px;
  margin-bottom: 16px;
}
.panel-label-bar .label {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.pipeline-scroll {
  flex: 1;
  overflow-y: auto;
}
.pipeline-step {
  border: 1px solid var(--line);
  margin-bottom: 12px;
  padding: 16px;
  background: var(--bg-base);
  transition: border-color 0.1s ease, background 0.1s ease;
}
.pipeline-step:hover {
  border-color: var(--line-active);
  background: var(--bg-elevated);
}
.pipeline-step.is-active {
  border-color: var(--accent);
  background: var(--bg-elevated);
}
.pipeline-step.is-done {
  opacity: 0.5;
}

.step-meta {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.step-id {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--accent);
  letter-spacing: -0.02em;
}
.step-title {
  font-family: var(--font-serif);
  font-weight: 500;
  font-size: 1rem;
  margin-bottom: 6px;
  color: var(--text-void);
}
.step-status-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 9px;
  padding: 2px 8px;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--line);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.step-runtime-view {
  margin-top: 12px;
}

.progress-container {
  margin-top: 10px;
}
.progress-track {
  height: 2px;
  background: var(--line);
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-thumb {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}
.progress-stats {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 10px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.ontology-status-box {
  background: var(--bg-elevated);
  padding: 12px 16px;
  border-left: 2px solid var(--accent);
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 11px;
  color: var(--accent-bright);
  letter-spacing: 0.02em;
}

.app-cta-btn {
  width: 100%;
  height: 48px;
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border: 1px solid var(--accent) !important;
  font-family: var(--font-mono) !important;
  font-weight: 700 !important;
  font-size: 0.85rem !important;
  cursor: pointer;
  transition: background 0.1s ease !important;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
}
.app-cta-btn:hover {
  background: var(--accent-bright) !important;
  border-color: var(--accent-bright) !important;
}

.app-footer-bar {
  height: 40px;
  padding: 0 32px;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 9px;
  color: var(--text-muted);
  background: var(--bg-base);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

@media (max-width: 1100px) {
  .workbench-layout {
    flex-direction: column;
  }
  .graph-panel-v2 {
    height: 400px;
    flex: none;
  }
}
</style>

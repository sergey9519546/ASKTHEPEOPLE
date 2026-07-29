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
          <span class="phase-name">Knowledge Construction</span>
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
          <span class="label">Execution Pipeline</span>
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
                      ? "PROCESSING"
                      : currentPhase > phase.id
                        ? "TERMINATED"
                        : "STAGED"
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
                      buildProgress?.message || "AWAITING INPUT..."
                    }}</span>
                    <span class="stat-pct"
                      >{{ buildProgress?.progress || 0 }}%</span
                    >
                  </div>
                </div>
                <!-- Info for Phase 2/3 -->
                <div v-else class="ontology-status-box">
                  CORE ONTOLOGY SYNTHESIZED. READY FOR INJECTION PROXY.
                </div>
              </div>
            </Transition>
          </div>

          <!-- LAUNCH CTA -->
          <div class="launch-sequence-box" v-if="currentPhase >= 2">
            <button class="app-cta-btn" @click="goToNextStep">
              INITIALIZE ENVIRONMENT <span class="arrow">→</span>
            </button>
          </div>
        </div>
      </section>
    </main>

    <!-- FOOTER STATUS -->
    <footer class="app-footer-bar">
      <div class="f-left">LOC: Workspace Phase 01</div>
      <div class="f-right">
        System Time: {{ new Date().toLocaleTimeString() }}
      </div>
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
  background: var(--bg-color);
  color: var(--text-primary);
  overflow: hidden;
  font-family: var(--font-sans);
}

.app-header {
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

.phase-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--atp-light-gray);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 6px 18px;
}
.phase-label {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 10px;
  color: var(--accent-color);
}
.phase-name {
  font-weight: 600;
  font-size: 11px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.system-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 10px;
  font-family: var(--font-mono);
}
.system-status.processing .status-dot {
  background: var(--accent-color);
  animation: flash 1s infinite alternate;
}
.system-status.ready .status-dot {
  background: var(--accent-tertiary);
}
.system-status.error .status-dot {
  background: var(--accent-secondary);
}

@keyframes flash {
  from { opacity: 0.3; }
  to { opacity: 1; }
}

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 24px;
  gap: 24px;
}
.workbench-panel {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.04), 0 1px 3px -1px rgba(15, 23, 42, 0.02);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.graph-panel-v2 {
  flex: 1.6;
}
.pipeline-panel {
  flex: 1;
  padding: 24px;
}

.graph-panel-v2.is-maximized {
  position: absolute;
  top: 94px;
  left: 24px;
  right: 24px;
  bottom: 64px;
  z-index: 50;
}

.panel-label-bar {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  margin-bottom: 24px;
}
.panel-label-bar .label {
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.pipeline-scroll {
  flex: 1;
  overflow-y: auto;
}
.pipeline-step {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  margin-bottom: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 20px;
  background: var(--surface-color);
}
.pipeline-step.is-active {
  border-color: var(--accent-secondary);
  box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.08), 0 8px 10px -6px rgba(59, 130, 246, 0.03);
}
.pipeline-step.is-done {
  opacity: 0.6;
  background: var(--atp-light-gray);
}

.step-meta {
  display: flex;
  gap: 15px;
  align-items: flex-start;
}
.step-id {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 1.25rem;
  color: var(--text-secondary);
}
.step-title {
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 5px;
  color: var(--text-primary);
}
.step-status-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 8px;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--atp-light-gray);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.step-runtime-view {
  margin-top: 16px;
}

.progress-container {
  margin-top: 12px;
}
.progress-track {
  height: 6px;
  background: var(--atp-light-gray);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-thumb {
  height: 100%;
  background: var(--accent-color);
  border-radius: 3px;
  transition: width 0.3s ease;
}
.progress-stats {
  display: flex;
  justify-content: space-between;
  font-weight: 500;
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.ontology-status-box {
  background: rgba(16, 185, 129, 0.05);
  padding: 12px 16px;
  border-left: 3px solid var(--accent-tertiary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-weight: 500;
  font-size: 11px;
  color: #065f46;
}

.app-cta-btn {
  width: 100%;
  height: 52px;
  background: var(--accent-secondary);
  color: white;
  border: none !important;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  border-radius: var(--radius-sm) !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15) !important;
}
.app-cta-btn:hover {
  background: #2563eb !important;
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.25) !important;
  transform: translateY(-1px) !important;
}

.app-footer-bar {
  height: 40px;
  padding: 0 30px;
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
  .workbench-layout {
    flex-direction: column;
  }
  .graph-panel-v2 {
    height: 400px;
    flex: none;
  }
}
</style>

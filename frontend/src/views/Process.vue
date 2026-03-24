<template>
  <div class="bauhaus-process-root">
    <!-- TOP BAR -->
    <nav class="bauhaus-header">
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
                <div v-if="phase.id === 1" class="progress-container-bauhaus">
                  <div class="progress-track">
                    <div
                      class="progress-thumb"
                      :style="{ width: (buildProgress?.progress || 0) + '%' }"
                    ></div>
                  </div>
                  <div class="progress-stats">
                    <span class="stat-msg">{{
                      buildProgress?.message || "AWAITING_INPUT..."
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
            <button class="bauhaus-cta-btn" @click="goToNextStep">
              INITIALIZE ENVIRONMENT <span class="arrow">→</span>
            </button>
          </div>
        </div>
      </section>
    </main>

    <!-- FOOTER STATUS -->
    <footer class="bauhaus-footer-bar">
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
  if (error.value) return "SYS_ERROR";
  return currentPhase.value < 3 ? "EXECUTING" : "SEQUENCE_READY";
});

const goHome = () => router.push("/");
const goToNextStep = () => {
  router.push({
    name: "Main",
    query: { step: 2, projectId: currentProjectId.value },
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
      buildProgress.value = { progress: task.progress, message: task.message };
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
.bauhaus-process-root {
  height: 100vh;
  background: var(--atp-white);
  display: flex;
  flex-direction: column;
  color: var(--atp-black);
  overflow: hidden;
}

.bauhaus-header {
  height: 70px;
  background: var(--atp-white);
  border-bottom: 4px solid var(--atp-black);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
  cursor: pointer;
}
.brand-monogram {
  background: var(--atp-black);
  color: var(--atp-white);
  padding: 4px 8px;
  font-weight: 950;
  font-size: 1.2rem;
}
.brand-full {
  font-weight: 950;
  font-size: 1rem;
  letter-spacing: -0.5px;
}

.phase-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f0f0f0;
  border: 3px solid var(--atp-black);
  padding: 6px 20px;
}
.phase-label {
  font-family: var(--font-mono);
  font-weight: 950;
  font-size: 11px;
  color: var(--bauhaus-red);
}
.phase-name {
  font-weight: 950;
  font-size: 12px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border: 2.5px solid var(--atp-black);
}
.system-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 950;
  font-size: 10px;
  font-family: var(--font-mono);
}
.system-status.processing .status-dot {
  background: var(--bauhaus-red);
  animation: flash 0.8s infinite;
}
.system-status.ready .status-dot {
  background: var(--bauhaus-yellow);
}
.system-status.error .status-dot {
  background: var(--bauhaus-blue);
}

@keyframes flash {
  50% {
    opacity: 0;
  }
}

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 25px;
  gap: 25px;
}
.workbench-panel {
  background: var(--atp-white);
  border: 4px solid var(--atp-black);
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
  padding: 30px;
}

.graph-panel-v2.is-maximized {
  position: absolute;
  top: 95px;
  left: 25px;
  right: 25px;
  bottom: 85px;
  z-index: 50;
}

.panel-label-bar {
  border-bottom: 4px solid var(--atp-black);
  padding-bottom: 15px;
  margin-bottom: 30px;
}
.panel-label-bar .label {
  font-weight: 950;
  font-size: 13px;
  letter-spacing: 1px;
  color: var(--atp-black);
}

.pipeline-scroll {
  flex: 1;
  overflow-y: auto;
}
.pipeline-step {
  border: 3px solid var(--atp-black);
  margin-bottom: 25px;
  transition: 0.3s;
  padding: 20px;
}
.pipeline-step.is-active {
  background: var(--bauhaus-blue);
  color: var(--atp-white);
  box-shadow: 8px 8px 0 var(--atp-black);
  transform: translate(-4px, -4px);
}
.pipeline-step.is-done {
  opacity: 0.6;
  filter: grayscale(1);
}

.step-meta {
  display: flex;
  gap: 15px;
  align-items: flex-start;
}
.step-id {
  font-family: var(--font-mono);
  font-weight: 950;
  font-size: 1.5rem;
  color: inherit;
}
.step-title {
  font-weight: 950;
  font-size: 0.95rem;
  margin-bottom: 5px;
}
.step-status-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-weight: 900;
  font-size: 9px;
  padding: 2px 6px;
  border: 1.5px solid var(--atp-black);
}

.step-runtime-view {
  margin-top: 20px;
}

.progress-container-bauhaus {
  margin-top: 15px;
}
.progress-track {
  height: 12px;
  background: var(--atp-white);
  border: 3px solid var(--atp-black);
  margin-bottom: 8px;
}
.progress-thumb {
  height: 100%;
  background: var(--bauhaus-red);
}
.progress-stats {
  display: flex;
  justify-content: space-between;
  font-weight: 950;
  font-size: 10px;
  font-family: var(--font-mono);
}

.ontology-status-box {
  background: rgba(0, 0, 0, 0.05);
  padding: 15px;
  border-left: 6px solid var(--bauhaus-yellow);
  font-weight: 900;
  font-size: 11px;
}

.bauhaus-cta-btn {
  width: 100%;
  height: 60px;
  background: var(--atp-black);
  color: var(--atp-white);
  border: none;
  font-weight: 950;
  font-size: 1.1rem;
  cursor: pointer;
  transition: 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
}
.bauhaus-cta-btn:hover {
  background: var(--bauhaus-red);
  color: var(--atp-black);
  transform: translate(-5px, -5px);
  box-shadow: 8px 8px 0 var(--atp-black);
}

.bauhaus-footer-bar {
  height: 40px;
  padding: 0 30px;
  border-top: 4px solid var(--atp-black);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-weight: 950;
  font-size: 10px;
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

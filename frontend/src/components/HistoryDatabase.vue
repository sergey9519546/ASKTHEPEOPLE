<template>
  <div
    class="simulation-history-workbench"
    :class="{ 'empty-state': projects.length === 0 && !loading }"
    ref="historyContainer"
  >
    <!-- Section Header -->
    <header class="section-title-area" aria-label="Simulation Archive section">
      <h2 class="section-label">Simulation Archive</h2>
      <p class="section-subtitle">Browse and replay synthetic scenario runs</p>
    </header>

    <!-- Project Cards Grid -->
    <div
      v-if="projects.length > 0"
      class="workbench-cards-grid"
      :class="{ 'is-expanded': isExpanded }"
      :style="gridContainerStyle"
    >
      <div
        v-for="(project, index) in projects"
        :key="project.simulation_id"
        class="simulation-card"
        :class="{
          'is-expanded': isExpanded,
          'is-hovered': hoveringCard === index,
        }"
        :style="getCardStyle(index)"
        @mouseenter="hoveringCard = index"
        @mouseleave="hoveringCard = null"
        @click="openProjectDetails(project)"
        role="button"
        tabindex="0"
        :aria-label="`Simulation ${formatSimId(project.simulation_id)}: ${getShortRequirement(project.simulation_requirement)}`"
        @keydown.enter="openProjectDetails(project)"
        @keydown.space.prevent="openProjectDetails(project)"
      >
        <!-- Card Header: ID & Capabilities -->
        <header class="card-header-row">
          <span class="simulation-id">{{
            formatSimId(project.simulation_id)
          }}</span>
          <div class="capability-flags" aria-label="Capabilities">
            <span
              class="flag"
              :class="{ active: project.project_id }"
              title="Graph Building"
              :aria-label="`Graph Building: ${project.project_id ? 'Available' : 'Not available'}`"
            >
              GRAPH BUILD
            </span>
            <span class="flag-pill is-active" aria-label="Environment Setup: Available">
              ENV SETUP
            </span>
            <span
              class="flag-pill"
              :class="{ 'is-active': project.report_id }"
              :aria-label="`Analysis Report: ${project.report_id ? 'Available' : 'Not available'}`"
              >AR</span
            >
          </div>
        </header>

        <!-- Preview Area: Files -->
        <div class="card-preview-area">
          <div
            v-if="project.files && project.files.length > 0"
            class="file-previews"
          >
            <div
              v-for="(file, fIdx) in project.files.slice(0, 2)"
              :key="fIdx"
              class="file-strip"
            >
              <span class="type-tag" :class="getFileExtension(file.filename)">{{
                getShortExt(file.filename)
              }}</span>
              <span class="filename-text">{{
                truncate(file.filename, 22)
              }}</span>
            </div>
            <div v-if="project.files.length > 2" class="more-files-indicator">
              +{{ project.files.length - 2 }} Assets
            </div>
          </div>
          <div
            v-else
            class="empty-files-placeholder"
            aria-label="No source data available"
          >
            <span class="empty-text">No Source Data</span>
          </div>
        </div>

        <!-- Content Area -->
        <div class="card-content-block">
          <h3 class="requirement-title text-rose-500">
            {{ getShortRequirement(project.simulation_requirement) }}
          </h3>
          <p class="requirement-preview text-slate-500">
            {{ truncate(project.simulation_requirement, 70) }}
          </p>
        </div>

        <!-- Footer -->
        <footer class="card-footer-row">
          <div class="timestamp-group text-slate-400">
            <span class="date-text">{{ formatDate(project.created_at) }}</span>
            <span class="time-text">{{ formatTime(project.created_at) }}</span>
          </div>
          <div class="execution-progress" :class="getProgressState(project)">
            <span class="status-indicator"></span>
            <span class="progress-text">{{ formatIteration(project) }}</span>
          </div>
        </footer>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="workbench-loading"
      role="status"
      aria-live="polite"
    >
      <div class="spinner" aria-hidden="true"></div>
      <span class="loading-label text-slate-400">Retrieving simulation runs...</span>
    </div>

    <!-- Modal: Project Details & Playback -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div
          v-if="selectedProject"
          class="workbench-modal-overlay"
          @click.self="closeModal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div class="modal-card">
            <!-- Modal Header -->
            <header class="modal-header-block">
              <div class="id-meta">
                <span class="modal-sim-id" id="modal-title">{{
                  formatSimId(selectedProject.simulation_id)
                }}</span>
                <div class="modal-badges">
                  <div
                    class="modal-status-badge"
                    :class="getProgressState(selectedProject)"
                  >
                    <span class="status-dot" aria-hidden="true"></span>
                    {{ formatIteration(selectedProject) }}
                  </div>
                  <span class="creation-stamp text-slate-400"
                    >{{ formatDate(selectedProject.created_at) }} @
                    {{ formatTime(selectedProject.created_at) }}</span
                  >
                </div>
              </div>
              <button
                class="close-modal-btn"
                @click="closeModal"
                aria-label="Close modal"
              >
                ×
              </button>
            </header>

            <!-- Modal Body -->
            <div
              class="modal-scroll-area scrollbar-thin"
              role="region"
              aria-label="Modal content"
            >
              <section
                class="modal-section"
                aria-labelledby="simulation-objective-heading"
              >
                <h4 class="section-heading" id="simulation-objective-heading">
                  Simulation Objective
                </h4>
                <div class="requirement-box text-slate-700">
                  {{
                    selectedProject.simulation_requirement ||
                    "No objective defined"
                  }}
                </div>
              </section>

              <section
                class="modal-section"
                aria-labelledby="linked-assets-heading"
              >
                <h4 class="section-heading" id="linked-assets-heading">
                  Linked Assets
                </h4>
                <div
                  v-if="
                    selectedProject.files && selectedProject.files.length > 0
                  "
                  class="modal-file-list"
                  role="list"
                  aria-label="Linked files"
                >
                  <div
                    v-for="(file, idx) in selectedProject.files"
                    :key="idx"
                    class="modal-file-row"
                    role="listitem"
                    :aria-label="`File: ${file.filename}, Type: ${getShortExt(file.filename)}`"
                  >
                    <span
                      class="file-extension-pill"
                      :class="getFileExtension(file.filename)"
                      aria-hidden="true"
                      >{{ getShortExt(file.filename) }}</span
                    >
                    <span class="modal-filename text-slate-700" aria-hidden="true">{{
                      file.filename
                    }}</span>
                  </div>
                </div>
                <div
                  v-else
                  class="modal-no-assets text-slate-400"
                  aria-label="No assets detected"
                >
                  No assets detected
                </div>
              </section>
            </div>

            <!-- Interactivity Area -->
            <div
              class="modal-playback-divider"
              aria-label="Synthetic playback section"
            >
              <span class="playback-label text-slate-400">Replay Pipeline</span>
            </div>

            <nav class="modal-navigation-grid" aria-label="Phase navigation">
              <button
                class="nav-btn btn-graph"
                @click="jumpToGraph"
                :disabled="!selectedProject.project_id"
                aria-label="Navigate to Phase 01: Graph Archive"
              >
                <span class="step-num text-rose-500">PHASE 01</span>
                <span class="action-label">Graph Archive</span>
              </button>
              <button
                class="nav-btn btn-setup"
                @click="jumpToSetup"
                aria-label="Navigate to Phase 02: Environment Configuration"
              >
                <span class="step-num text-blue-500">PHASE 02</span>
                <span class="action-label">Environment Config</span>
              </button>
              <button
                class="nav-btn btn-report"
                @click="jumpToReport"
                :disabled="!selectedProject.report_id"
                aria-label="Navigate to Phase 04: Report Synthesis"
              >
                <span class="step-num text-emerald-500">PHASE 04</span>
                <span class="action-label">Report Synthesis</span>
              </button>
            </nav>

            <footer class="modal-notice" aria-label="Important notice">
              <p>
                Note: Interactive Simulation is run-time only and not saved in replay format.
              </p>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onActivated,
  onMounted,
  onUnmounted,
  ref,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { getSimulationHistory } from "../api/simulation";

const router = useRouter();
const route = useRoute();

// State
const projects = ref([]);
const loading = ref(true);
const isExpanded = ref(false);
const hoveringCard = ref(null);
const historyContainer = ref(null);
const selectedProject = ref(null);
let observer = null;
let isAnimating = false;
let expandDebounceTimer = null;
let pendingState = null;

// Configuration
const CARDS_PER_ROW = 4;
const CARD_WIDTH = 280;
const CARD_HEIGHT = 280;
const CARD_GAP = 24;
const HISTORY_FETCH_LIMIT = 24;

const gridContainerStyle = computed(() => {
  if (!isExpanded.value) return { minHeight: "360px" };
  const total = projects.value.length;
  if (total === 0) return { minHeight: "260px" };
  const rows = Math.ceil(total / CARDS_PER_ROW);
  return { minHeight: `${rows * CARD_HEIGHT + (rows - 1) * CARD_GAP + 60}px` };
});

const getCardStyle = (index) => {
  const total = projects.value.length;
  const transition =
    "transform 800ms cubic-bezier(0.16, 1, 0.3, 1), opacity 800ms, box-shadow 0.3s ease, border-color 0.2s ease";

  if (isExpanded.value) {
    const col = index % CARDS_PER_ROW;
    const row = Math.floor(index / CARDS_PER_ROW);
    const currentRowStart = row * CARDS_PER_ROW;
    const currentRowCards = Math.min(CARDS_PER_ROW, total - currentRowStart);
    const rowWidth =
      currentRowCards * CARD_WIDTH + (currentRowCards - 1) * CARD_GAP;
    const startX = -(rowWidth / 2) + CARD_WIDTH / 2;
    const x = startX + (index % CARDS_PER_ROW) * (CARD_WIDTH + CARD_GAP);
    const y = 20 + row * (CARD_HEIGHT + CARD_GAP);

    return {
      transform: `translate(${x}px, ${y}px) scale(1)`,
      zIndex: 100 + index,
      opacity: 1,
      transition,
    };
  } else {
    const centerIdx = (total - 1) / 2;
    const offset = index - centerIdx;
    const x = offset * 24;
    const y = 20 + Math.abs(offset) * 8;
    const r = offset * 2.5;
    const s = 1 - Math.abs(offset) * 0.04;

    return {
      transform: `translate(${x}px, ${y}px) rotate(${r}deg) scale(${s})`,
      zIndex: 10 + index,
      opacity: 1,
      transition,
    };
  }
};

// Formatters
const formatSimId = (id) =>
  id
    ? `SIM-${id.replace("sim_", "").slice(0, 6).toUpperCase()}`
    : "SIM-UNKNOWN";
const truncate = (text, len) =>
  text && text.length > len ? text.slice(0, len) + "..." : text || "";
const getShortRequirement = (req) => (req ? truncate(req, 20) : "Untitled Simulation");
const formatDate = (ds) => (ds ? new Date(ds).toISOString().slice(0, 10) : "");
const formatTime = (ds) =>
  ds
    ? new Date(ds).toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";
const formatIteration = (sim) => {
  const c = sim.current_round || 0;
  const t = sim.total_rounds || 0;
  return t === 0 ? "Pending" : `${c}/${t} Cycles`;
};

const getProgressState = (sim) => {
  const c = sim.current_round || 0;
  const t = sim.total_rounds || 0;
  if (t === 0 || c === 0) return "state-pending";
  if (c >= t) return "state-complete";
  return "state-active";
};

const getShortExt = (fn) =>
  fn ? fn.split(".").pop()?.toUpperCase().slice(0, 4) : "FILE";
const getFileExtension = (fn) => {
  const ext = fn?.split(".").pop()?.toLowerCase();
  const map = {
    pdf: "pdf",
    doc: "doc",
    docx: "doc",
    xls: "xls",
    xlsx: "xls",
    csv: "xls",
    ppt: "ppt",
    pptx: "ppt",
    txt: "txt",
    md: "txt",
    json: "code",
  };
  return map[ext] || "bin";
};

// Navigation & Actions
const openProjectDetails = (sim) => (selectedProject.value = sim);
const closeModal = () => (selectedProject.value = null);

const jumpToGraph = () => {
  if (selectedProject.value?.project_id) {
    router.push({
      name: "Process",
      params: { projectId: selectedProject.value.project_id },
    });
    closeModal();
  }
};

const jumpToSetup = () => {
  if (selectedProject.value?.simulation_id) {
    router.push({
      name: "Simulation",
      params: { simulationId: selectedProject.value.simulation_id },
    });
    closeModal();
  }
};

const jumpToReport = () => {
  if (selectedProject.value?.report_id) {
    router.push({
      name: "Report",
      params: { reportId: selectedProject.value.report_id },
    });
    closeModal();
  }
};

const fetchHistory = async () => {
  try {
    loading.value = true;
    const res = await getSimulationHistory(HISTORY_FETCH_LIMIT);
    if (res.success) projects.value = res.data || [];
  } finally {
    loading.value = false;
  }
};

const setupObserver = () => {
  if (observer) observer.disconnect();
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        pendingState = e.isIntersecting;
        if (isAnimating) return;
        if (pendingState === isExpanded.value) return;

        const delay = pendingState ? 80 : 250;
        if (expandDebounceTimer) clearTimeout(expandDebounceTimer);
        expandDebounceTimer = setTimeout(() => {
          if (
            isAnimating ||
            pendingState === null ||
            pendingState === isExpanded.value
          )
            return;
          isAnimating = true;
          isExpanded.value = pendingState;
          pendingState = null;
          setTimeout(() => (isAnimating = false), 800);
        }, delay);
      });
    },
    { threshold: [0.3, 0.7], rootMargin: "0px 0px -100px 0px" },
  );

  if (historyContainer.value) observer.observe(historyContainer.value);
};

onMounted(async () => {
  await nextTick();
  await fetchHistory();
  setTimeout(setupObserver, 200);
});

onActivated(fetchHistory);
onUnmounted(() => {
  if (observer) observer.disconnect();
  if (expandDebounceTimer) clearTimeout(expandDebounceTimer);
});
</script>


<style scoped>
.simulation-history-workbench {
  position: relative;
  width: 100%;
  min-height: 380px;
  margin-top: 60px;
  padding: 40px 0;
  background: transparent;
  border-top: 1px solid var(--border-color);
}

.section-title-area {
  text-align: center;
  margin-bottom: 32px;
}

.section-label {
  font-weight: 700;
  font-size: 1.5rem;
  letter-spacing: -0.5px;
  color: var(--text-primary);
}

.section-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.workbench-cards-grid {
  position: relative;
  display: flex;
  justify-content: center;
  padding: 0 40px;
  transition: min-height 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.simulation-card {
  position: absolute;
  width: 280px;
  height: 280px;
  border: 1px solid var(--line);
  background: var(--bg-base);
  border-radius: 0;
  padding: 16px;
  cursor: pointer;
  box-shadow: none;
  display: flex;
  flex-direction: column;
}

.simulation-card:hover {
  border-color: var(--accent);
  background: var(--bg-panel);
  transform: translate3d(0, -4px, 0) !important;
  z-index: 2000 !important;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.simulation-id {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 11px;
  color: var(--text-primary);
}

.capability-flags {
  display: flex;
  gap: 4px;
}
.flag {
  width: 20px;
  height: 20px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  font-weight: 700;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
}
.flag.active {
  background: var(--accent-color);
  color: #fff;
  border-color: var(--accent-color);
  box-shadow: 0 0 8px var(--accent-glow);
}

.card-preview-area {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  height: 68px;
  margin-bottom: 12px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.file-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  margin-bottom: 4px;
  padding: 2px 6px;
}

.type-tag {
  font-family: var(--font-mono);
  font-size: 7px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  padding: 1px 3px;
  border-radius: 2px;
}
.type-tag.pdf { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.type-tag.xls { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.type-tag.doc { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.type-tag.ppt { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

.filename-text {
  font-size: 9px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
}

.more-files-indicator {
  font-size: 8px;
  font-weight: 600;
  color: var(--text-secondary);
  text-align: right;
  margin-top: 2px;
}

.empty-files-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.empty-text {
  font-size: 9px;
  font-weight: 500;
  color: var(--text-secondary);
}

.card-content-block {
  flex-grow: 1;
}
.requirement-title {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 4px;
  color: var(--text-primary);
}
.requirement-preview {
  font-size: 10px;
  line-height: 1.5;
  height: 30px;
  overflow: hidden;
  color: var(--text-secondary);
}

.card-footer-row {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timestamp-group {
  display: flex;
  flex-direction: column;
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 500;
  color: var(--text-secondary);
}
.execution-progress {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 700;
  font-size: 9px;
}
.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.state-complete {
  color: #34d399;
}
.state-complete .status-indicator {
  background: #34d399;
  box-shadow: 0 0 6px rgba(52, 211, 153, 0.5);
}
.state-active {
  color: var(--accent-color);
}
.state-active .status-indicator {
  background: var(--accent-color);
  animation: pulse 1s infinite;
  box-shadow: 0 0 6px var(--accent-glow);
}
.state-pending {
  color: var(--text-secondary);
}
.state-pending .status-indicator {
  background: var(--text-secondary);
}

.workbench-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-secondary);
}
.spinner {
  width: 24px;
  height: 24px;
  border: 2.5px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-label {
  font-weight: 600;
  font-size: 11px;
}

/* Modal Styles */
.workbench-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-card {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  width: 580px;
  max-width: 90vw;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  color: var(--text-primary);
}

.modal-header-block {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.id-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.modal-sim-id {
  font-weight: 700;
  font-size: 20px;
  color: var(--text-primary);
}
.modal-badges {
  display: flex;
  align-items: center;
  gap: 10px;
}
.modal-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 20px;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.05);
}
.creation-stamp {
  font-size: 10px;
  color: var(--text-secondary);
}

.close-modal-btn {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.close-modal-btn:hover {
  background: rgba(255, 69, 0, 0.2);
  color: var(--accent-color);
}

.modal-scroll-area {
  padding: 24px;
  overflow-y: auto;
  flex-grow: 1;
}
.modal-section {
  margin-bottom: 24px;
}
.section-heading {
  font-weight: 700;
  font-size: 10px;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
}
.requirement-box {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  font-size: 13px;
  line-height: 1.6;
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary);
}

.modal-file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.modal-file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-primary);
}
.file-extension-pill {
  font-weight: 700;
  font-size: 8px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
}
.file-extension-pill.pdf { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.file-extension-pill.xls { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.file-extension-pill.doc { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.file-extension-pill.ppt { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

.modal-playback-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  position: relative;
}
.modal-playback-divider::before {
  content: "";
  position: absolute;
  left: 24px;
  right: 24px;
  height: 1px;
  background: var(--border-color);
  top: 50%;
  z-index: 1;
}
.playback-label {
  font-weight: 700;
  font-size: 9px;
  letter-spacing: 1px;
  text-transform: uppercase;
  background: var(--bg-color);
  color: var(--text-secondary);
  padding: 0 10px;
  position: relative;
  z-index: 2;
}

.modal-navigation-grid {
  display: flex;
  gap: 12px;
  padding: 24px;
}
.nav-btn {
  flex: 1;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-primary);
}
.nav-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(255, 69, 0, 0.2);
  border-color: var(--accent-color);
  background: rgba(255, 69, 0, 0.1);
}
.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
  background: rgba(0, 0, 0, 0.2);
}

.step-num {
  font-size: 8px;
  font-weight: 700;
  color: var(--text-secondary);
}
.action-label {
  font-weight: 700;
  font-size: 11px;
  color: var(--text-primary);
}

.modal-notice {
  padding: 0 24px 24px;
  text-align: center;
}
.modal-notice p {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-active .modal-card,
.modal-fade-leave-active .modal-card {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .modal-card,
.modal-fade-leave-to .modal-card {
  opacity: 0;
  transform: scale(0.95);
}

.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 2px;
}
</style>

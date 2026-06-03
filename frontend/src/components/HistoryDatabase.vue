<template>
  <div
    class="simulation-history-workbench"
    :class="{ 'empty-state': projects.length === 0 && !loading }"
    ref="historyContainer"
  >
    <!-- Bauhaus Backdrop -->
    <div
      v-if="projects.length > 0 || loading"
      class="bauhaus-backdrop"
      aria-hidden="true"
    >
      <div class="geometric-pattern"></div>
    </div>

    <!-- Section Header -->
    <header class="section-title-area" aria-label="Simulation Archive section">
      <div class="bauhaus-accent-shape triangle" aria-hidden="true"></div>
      <h2 class="section-label">Simulation Archive</h2>
      <div class="bauhaus-accent-shape square" aria-hidden="true"></div>
    </header>

    <!-- Project Cards Grid -->
    <div
      v-if="projects.length > 0"
      class="workbench-cards-grid"
      :class="{ 'is-expanded': isExpanded }"
      :style="gridContainerStyle"
    >
      <!-- v-memo optimization: avoids re-rendering unaffected simulation cards -->
      <div
        v-for="(project, index) in projects"
        :key="project.simulation_id"
        v-memo="[project.simulation_id, project.project_id, project.report_id, project.current_round, project.total_rounds, isExpanded, hoveringCard === index]"
        class="simulation-card bauhaus-card"
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
              aria-label="Graph Building: {{ project.project_id ? 'Available' : 'Not available' }}"
              >GB</span
            >
            <span
              class="flag active"
              title="Environment Setup"
              aria-label="Environment Setup: Available"
              >ES</span
            >
            <span
              class="flag"
              :class="{ active: project.report_id }"
              title="Analysis Report"
              aria-label="Analysis Report: {{ project.report_id ? 'Available' : 'Not available' }}"
              >AR</span
            >
          </div>
        </header>

        <!-- Preview Area: Files -->
        <div class="card-preview-area">
          <div class="viewport-mark top-left" aria-hidden="true"></div>
          <div
            v-if="project.files && project.files.length > 0"
            class="file-previews"
          >
            <div
              v-for="(file, fIdx) in project.files.slice(0, 3)"
              :key="fIdx"
              class="file-strip"
            >
              <span class="type-tag" :class="getFileExtension(file.filename)">{{
                getShortExt(file.filename)
              }}</span>
              <span class="filename-text">{{
                truncate(file.filename, 18)
              }}</span>
            </div>
            <div v-if="project.files.length > 3" class="more-files-indicator">
              +{{ project.files.length - 3 }} Assets Remaining
            </div>
          </div>
          <div
            v-else
            class="empty-files-placeholder"
            aria-label="No source data available"
          >
            <span class="empty-icon" aria-hidden="true">×</span>
            <span class="empty-text">NO SOURCE DATA</span>
          </div>
        </div>

        <!-- Content Area -->
        <div class="card-content-block">
          <h3 class="requirement-title">
            {{ getShortRequirement(project.simulation_requirement) }}
          </h3>
          <p class="requirement-preview">
            {{ truncate(project.simulation_requirement, 60) }}
          </p>
        </div>

        <!-- Footer -->
        <footer class="card-footer-row">
          <div class="timestamp-group">
            <span class="date-text">{{ formatDate(project.created_at) }}</span>
            <span class="time-text">{{ formatTime(project.created_at) }}</span>
          </div>
          <div class="execution-progress" :class="getProgressState(project)">
            <span class="status-indicator"></span>
            <span class="progress-text">{{ formatIteration(project) }}</span>
          </div>
        </footer>

        <div class="hover-accent-line" aria-hidden="true"></div>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="workbench-loading"
      role="status"
      aria-live="polite"
    >
      <div class="bauhaus-spinner" aria-hidden="true"></div>
      <span class="loading-label">RETRIEVING ARCHIVES...</span>
    </div>

    <!-- Modal: Project Details & Playback -->
    <Teleport to="body">
      <Transition name="bauhaus-modal">
        <div
          v-if="selectedProject"
          class="workbench-modal-overlay"
          @click.self="closeModal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div class="bauhaus-modal-content">
            <!-- Modal Header -->
            <header class="modal-header-block">
              <div class="id-meta">
                <span class="modal-sim-id" id="modal-title">{{
                  formatSimId(selectedProject.simulation_id)
                }}</span>
                <div
                  class="modal-status-badge"
                  :class="getProgressState(selectedProject)"
                >
                  <span class="status-dot" aria-hidden="true"></span>
                  {{ formatIteration(selectedProject) }}
                </div>
                <span class="creation-stamp"
                  >{{ formatDate(selectedProject.created_at) }} @
                  {{ formatTime(selectedProject.created_at) }}</span
                >
              </div>
              <button
                class="close-modal-btn"
                @click="closeModal"
                aria-label="Close modal"
              >
                CLOSE [X]
              </button>
            </header>

            <!-- Modal Body -->
            <div
              class="modal-scroll-area"
              role="region"
              aria-label="Modal content"
            >
              <section
                class="modal-section"
                aria-labelledby="simulation-objective-heading"
              >
                <h4 class="section-heading" id="simulation-objective-heading">
                  SIMULATION OBJECTIVE
                </h4>
                <div class="requirement-box">
                  {{
                    selectedProject.simulation_requirement ||
                    "NO OBJECTIVE DEFINED"
                  }}
                </div>
              </section>

              <section
                class="modal-section"
                aria-labelledby="linked-assets-heading"
              >
                <h4 class="section-heading" id="linked-assets-heading">
                  LINKED ASSETS
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
                    <span class="modal-filename" aria-hidden="true">{{
                      file.filename
                    }}</span>
                  </div>
                </div>
                <div
                  v-else
                  class="modal-no-assets"
                  aria-label="No assets detected"
                >
                  NO ASSETS DETECTED
                </div>
              </section>
            </div>

            <!-- Interactivity Area -->
            <div
              class="modal-playback-divider"
              aria-label="Synthetic playback section"
            >
              <div class="hr-line" aria-hidden="true"></div>
              <span class="playback-label">SYNTHETIC PLAYBACK</span>
              <div class="hr-line" aria-hidden="true"></div>
            </div>

            <nav class="modal-navigation-grid" aria-label="Phase navigation">
              <button
                class="nav-btn btn-graph"
                @click="jumpToGraph"
                :disabled="!selectedProject.project_id"
                aria-label="Navigate to Phase 01: Graph Archive"
              >
                <span class="step-num">PHASE 01</span>
                <span class="action-icon" aria-hidden="true">◆</span>
                <span class="action-label">GRAPH ARCHIVE</span>
              </button>
              <button
                class="nav-btn btn-setup"
                @click="jumpToSetup"
                aria-label="Navigate to Phase 02: Environment Configuration"
              >
                <span class="step-num">PHASE 02</span>
                <span class="action-icon" aria-hidden="true">▲</span>
                <span class="action-label">ENV CONFIG</span>
              </button>
              <button
                class="nav-btn btn-report"
                @click="jumpToReport"
                :disabled="!selectedProject.report_id"
                aria-label="Navigate to Phase 04: Report Synthesis"
              >
                <span class="step-num">PHASE 04</span>
                <span class="action-icon" aria-hidden="true">■</span>
                <span class="action-label">REPORT SYNTHESIS</span>
              </button>
            </nav>

            <footer class="modal-notice" aria-label="Important notice">
              <p>
                Phases 03 [Simulation] and 05 [Interaction] are runtime-only and
                do not support archive playback.
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
const CARD_WIDTH = 300;
const CARD_HEIGHT = 300;
const CARD_GAP = 30;

const gridContainerStyle = computed(() => {
  if (!isExpanded.value) return { minHeight: "450px" };
  const total = projects.value.length;
  if (total === 0) return { minHeight: "300px" };
  const rows = Math.ceil(total / CARDS_PER_ROW);
  return { minHeight: `${rows * CARD_HEIGHT + (rows - 1) * CARD_GAP + 50}px` };
});

const getCardStyle = (index) => {
  const total = projects.value.length;
  const transition =
    "transform 800ms cubic-bezier(0.19, 1, 0.22, 1), opacity 800ms, box-shadow 0.3s";

  if (isExpanded.value) {
    const col = index % CARDS_PER_ROW;
    const row = Math.floor(index / CARDS_PER_ROW);
    const currentRowStart = row * CARDS_PER_ROW;
    const currentRowCards = Math.min(CARDS_PER_ROW, total - currentRowStart);
    const rowWidth =
      currentRowCards * CARD_WIDTH + (currentRowCards - 1) * CARD_GAP;
    const startX = -(rowWidth / 2) + CARD_WIDTH / 2;
    const x = startX + (index % CARDS_PER_ROW) * (CARD_WIDTH + CARD_GAP);
    const y = 30 + row * (CARD_HEIGHT + CARD_GAP);

    return {
      transform: `translate(${x}px, ${y}px) scale(1)`,
      zIndex: 100 + index,
      opacity: 1,
      transition,
    };
  } else {
    const centerIdx = (total - 1) / 2;
    const offset = index - centerIdx;
    const x = offset * 40;
    const y = 30 + Math.abs(offset) * 10;
    const r = offset * 4;
    const s = 1 - Math.abs(offset) * 0.05;

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
    ? `SIM_${id.replace("sim_", "").slice(0, 6).toUpperCase()}`
    : "SIM_UNKNOWN";
const truncate = (text, len) =>
  text && text.length > len ? text.slice(0, len) + "..." : text || "";
const getShortRequirement = (req) => (req ? truncate(req, 22) : "UNTITLED_SIM");
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
  return t === 0 ? "PENDING" : `${c}/${t} CYCLES`;
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
    const res = await getSimulationHistory(24);
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
  min-height: 400px;
  margin-top: 80px;
  padding: 60px 0;
  background: var(--atp-white);
  border-top: 8px solid var(--atp-black);
}

.bauhaus-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
}

.geometric-pattern {
  width: 100%;
  height: 100%;
  background-image:
    linear-gradient(to right, var(--atp-black) 2px, transparent 2px),
    linear-gradient(to bottom, var(--atp-black) 2px, transparent 2px);
  background-size: 80px 80px;
  opacity: 0.05;
}

.section-title-area {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 30px;
  margin-bottom: 40px;
  padding: 0 60px;
}

.bauhaus-accent-shape {
  width: 40px;
  height: 40px;
  border: 4px solid var(--atp-black);
}
.bauhaus-accent-shape.triangle {
  border-bottom-color: var(--bauhaus-red);
  border-right-color: transparent;
  border-left-color: transparent;
  border-top-color: transparent;
  height: 0;
  width: 0;
  border-width: 0 20px 35px 20px;
  border-style: solid;
  box-sizing: border-box;
}
.bauhaus-accent-shape.square {
  background: var(--bauhaus-blue);
}
.section-label {
  font-weight: 950;
  font-size: 1.5rem;
  letter-spacing: -1px;
  color: var(--atp-black);
  text-transform: uppercase;
}

.workbench-cards-grid {
  position: relative;
  display: flex;
  justify-content: center;
  padding: 0 60px;
  transition: min-height 0.8s cubic-bezier(0.19, 1, 0.22, 1);
}

.bauhaus-card {
  border: 4px solid var(--atp-black);
  background: var(--atp-white);
  border-radius: 0;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s;
}

.simulation-card {
  position: absolute;
  width: 300px;
}

.simulation-card:hover {
  box-shadow: 15px 15px 0 var(--atp-black);
  transform: translate(-6px, -6px) !important;
  z-index: 2000 !important;
  border-color: var(--bauhaus-red);
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 3px solid var(--atp-black);
}

.simulation-id {
  font-family: var(--font-mono);
  font-weight: 900;
  font-size: 13px;
}

.capability-flags {
  display: flex;
  gap: 5px;
}
.flag {
  width: 24px;
  height: 24px;
  border: 2px solid var(--atp-black);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 900;
  opacity: 0.2;
}
.flag.active {
  opacity: 1;
  background: var(--bauhaus-blue);
  color: var(--atp-white);
}

.card-preview-area {
  position: relative;
  background: var(--atp-black);
  height: 80px;
  margin-bottom: 15px;
  padding: 10px;
}

.viewport-mark {
  position: absolute;
  width: 10px;
  height: 10px;
  border-top: 2px solid var(--atp-white);
  border-left: 2px solid var(--atp-white);
}
.top-left {
  top: 5px;
  left: 5px;
}

.file-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--atp-white);
  border: 2px solid var(--atp-black);
  margin-bottom: 4px;
  padding: 2px 6px;
}

.type-tag {
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 900;
  background: var(--bauhaus-blue);
  color: var(--atp-white);
  padding: 1px 4px;
}
.filename-text {
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--atp-black);
}

.more-files-indicator {
  font-size: 9px;
  font-weight: 900;
  color: var(--atp-white);
  text-align: center;
}

.empty-files-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--atp-white);
}
.empty-icon {
  font-size: 20px;
  font-weight: 900;
  color: var(--bauhaus-blue);
}
.empty-text {
  font-size: 9px;
  font-weight: 800;
}

.requirement-title {
  font-weight: 900;
  font-size: 16px;
  margin-bottom: 5px;
  color: var(--bauhaus-red);
  text-transform: uppercase;
}
.requirement-preview {
  font-size: 11px;
  line-height: 1.4;
  color: #333;
  height: 32px;
  overflow: hidden;
}

.card-footer-row {
  margin-top: 15px;
  padding-top: 12px;
  border-top: 2px solid var(--atp-black);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timestamp-group {
  display: flex;
  flex-direction: column;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 800;
}
.execution-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 900;
  font-size: 10px;
}
.status-indicator {
  width: 8px;
  height: 8px;
  border: 1px solid var(--atp-black);
}

.state-complete {
  color: var(--bauhaus-yellow);
}
.state-complete .status-indicator {
  background: var(--bauhaus-yellow);
}
.state-active {
  color: var(--bauhaus-red);
}
.state-active .status-indicator {
  background: var(--bauhaus-red);
}
.state-pending {
  color: #666;
}

.workbench-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  padding: 50px;
}
.bauhaus-spinner {
  width: 40px;
  height: 40px;
  border: 6px solid var(--atp-black);
  border-top-color: var(--bauhaus-red);
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.loading-label {
  font-weight: 900;
  font-size: 12px;
  letter-spacing: 2px;
}

/* Modal Styles */
.workbench-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--atp-white);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.bauhaus-modal-content {
  background: var(--atp-white);
  border: 8px solid var(--atp-black);
  width: 650px;
  max-width: 95vw;
  box-shadow: 20px 20px 0 var(--atp-black);
}

.modal-header-block {
  padding: 30px;
  border-bottom: 6px solid var(--atp-black);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.id-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.modal-sim-id {
  font-weight: 900;
  font-size: 28px;
}
.modal-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 900;
  font-size: 12px;
  padding: 5px 12px;
  border: 3px solid var(--atp-black);
}

.close-modal-btn {
  background: var(--bauhaus-blue);
  color: var(--atp-white);
  border: 4px solid var(--atp-black);
  padding: 10px 20px;
  font-weight: 900;
  cursor: pointer;
}
.close-modal-btn:hover {
  background: var(--atp-black);
}

.modal-scroll-area {
  padding: 30px;
  max-height: 400px;
  overflow-y: auto;
}
.modal-section {
  margin-bottom: 30px;
}
.section-heading {
  font-weight: 900;
  font-size: 12px;
  letter-spacing: 2px;
  color: var(--bauhaus-blue);
  margin-bottom: 12px;
}
.requirement-box {
  border: 4px solid var(--atp-black);
  padding: 20px;
  font-size: 16px;
  line-height: 1.6;
  background: #f5f5f5;
}

.modal-file-row {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 12px;
  border: 2px solid var(--atp-black);
  margin-bottom: 8px;
}
.file-extension-pill {
  font-weight: 900;
  font-size: 10px;
  padding: 4px 8px;
  border: 2px solid var(--atp-black);
  background: var(--bauhaus-blue);
  color: var(--atp-white);
}

.modal-playback-divider {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 30px;
}
.hr-line {
  flex: 1;
  height: 3px;
  background: var(--atp-black);
}
.playback-label {
  font-weight: 900;
  font-size: 10px;
  letter-spacing: 3px;
}

.modal-navigation-grid {
  display: flex;
  gap: 15px;
  padding: 30px;
}
.nav-btn {
  flex: 1;
  border: 4px solid var(--atp-black);
  background: var(--atp-white);
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: 0.2s;
}
.nav-btn:hover:not(:disabled) {
  transform: translateY(-5px);
  box-shadow: 8px 8px 0 var(--atp-black);
  border-color: var(--bauhaus-red);
}
.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.step-num {
  font-size: 10px;
  font-weight: 900;
  color: #666;
}
.action-icon {
  font-size: 24px;
}
.action-label {
  font-weight: 900;
  font-size: 11px;
}

.modal-notice {
  padding: 0 30px 30px;
  text-align: center;
}
.modal-notice p {
  font-size: 11px;
  font-weight: 700;
  color: var(--bauhaus-blue);
}

/* Transition */
.bauhaus-modal-enter-active,
.bauhaus-modal-leave-active {
  transition: opacity 0.4s;
}
.bauhaus-modal-enter-from,
.bauhaus-modal-leave-to {
  opacity: 0;
}
</style>

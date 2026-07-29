<template>
  <div class="workbench-panel">
    <div class="scroll-container scrollbar-thin">
      <!-- Step 01: Ontology -->
      <div
        class="step-card"
        :class="{ active: currentPhase === 0, completed: currentPhase > 0 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">Ontology Generation</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 0" class="badge success">Completed</span>
            <span v-else-if="currentPhase === 0" class="badge processing"
              >Generating</span
            >
            <span v-else class="badge pending">Waiting</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/graph/ontology/generate</p>
          <p class="description">
            LLM analyzes document content and requirements to extract reality
            seeds and automatically generate an optimal ontology structure.
          </p>

          <!-- Loading / Progress -->
          <div
            v-if="currentPhase === 0 && ontologyProgress"
            class="progress-section"
          >
            <div class="spinner-sm"></div>
            <span>{{
              ontologyProgress.message || "Analyzing documents..."
            }}</span>
          </div>

          <!-- Detail Overlay -->
          <div v-if="selectedOntologyItem" class="ontology-detail-overlay">
            <div class="detail-header">
              <div class="detail-title-group">
                <span class="detail-type-badge">{{
                  selectedOntologyItem.itemType === "entity"
                    ? "Entity"
                    : "Relation"
                }}</span>
                <span class="detail-name">{{ selectedOntologyItem.name }}</span>
              </div>
              <button class="close-btn" @click="selectedOntologyItem = null">
                ×
              </button>
            </div>
            <div class="detail-body scrollbar-thin">
              <div class="detail-desc text-slate-600">
                {{ selectedOntologyItem.description }}
              </div>

              <!-- Attributes -->
              <div
                class="detail-section"
                v-if="selectedOntologyItem.attributes?.length"
              >
                <span class="section-label">Attributes</span>
                <div class="attr-list">
                  <div
                    v-for="attr in selectedOntologyItem.attributes"
                    :key="attr.name"
                    class="attr-item"
                  >
                    <div class="attr-header">
                      <span class="attr-name">{{ attr.name }}</span>
                      <span class="attr-type">({{ attr.type }})</span>
                    </div>
                    <span class="attr-desc text-slate-500">{{ attr.description }}</span>
                  </div>
                </div>
              </div>

              <!-- Examples (Entity) -->
              <div
                class="detail-section"
                v-if="selectedOntologyItem.examples?.length"
              >
                <span class="section-label">Examples</span>
                <div class="example-list">
                  <span
                    v-for="ex in selectedOntologyItem.examples"
                    :key="ex"
                    class="example-tag"
                    >{{ ex }}</span
                  >
                </div>
              </div>

              <!-- Source/Target (Relation) -->
              <div
                class="detail-section"
                v-if="selectedOntologyItem.source_targets?.length"
              >
                <span class="section-label">Connections</span>
                <div class="conn-list">
                  <div
                    v-for="(conn, idx) in selectedOntologyItem.source_targets"
                    :key="idx"
                    class="conn-item text-slate-600"
                  >
                    <span class="conn-node">{{ conn.source }}</span>
                    <span class="conn-arrow">→</span>
                    <span class="conn-node">{{ conn.target }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Generated Entity Tags -->
          <div
            v-if="projectData?.ontology?.entity_types"
            class="tags-container"
            :class="{ dimmed: selectedOntologyItem }"
          >
            <span class="tag-label">Generated Entity Types</span>
            <div class="tags-list">
              <span
                v-for="entity in projectData.ontology.entity_types"
                :key="entity.name"
                class="entity-tag clickable"
                @click="selectOntologyItem(entity, 'entity')"
              >
                {{ entity.name }}
              </span>
            </div>
          </div>

          <!-- Generated Relation Tags -->
          <div
            v-if="projectData?.ontology?.edge_types"
            class="tags-container"
            :class="{ dimmed: selectedOntologyItem }"
          >
            <span class="tag-label">Generated Relation Types</span>
            <div class="tags-list">
              <span
                v-for="rel in projectData.ontology.edge_types"
                :key="rel.name"
                class="entity-tag clickable"
                @click="selectOntologyItem(rel, 'relation')"
              >
                {{ rel.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Graph Build -->
      <div
        class="step-card"
        :class="{ active: currentPhase === 1, completed: currentPhase > 1 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">GraphRAG Build</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 1" class="badge success">Completed</span>
            <span v-else-if="currentPhase === 1" class="badge processing"
              >{{ buildProgress?.progress || 0 }}%</span
            >
            <span v-else class="badge pending">Waiting</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/graph/build</p>
          <p class="description">
            Based on the generated ontology, documents are chunked and processed
            using GraphRAG to extract entities, relationships, temporal
            memories, and community summaries.
          </p>

          <!-- Stats Cards -->
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value text-rose-500">{{ graphStats.nodes }}</span>
              <span class="stat-label">Entities</span>
            </div>
            <div class="stat-card">
              <span class="stat-value text-blue-500">{{ graphStats.edges }}</span>
              <span class="stat-label">Relations</span>
            </div>
            <div class="stat-card">
              <span class="stat-value text-emerald-500">{{ graphStats.types }}</span>
              <span class="stat-label">Schema Types</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: Build Complete -->
      <div
        class="step-card"
        :class="{ active: currentPhase === 2, completed: currentPhase >= 2 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">Build Complete</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase >= 2" class="badge accent"
              >In Progress</span
            >
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description text-slate-500">
            Graph construction complete. Please proceed to the next step for
            environment setup.
          </p>
          <button
            class="action-btn"
            :disabled="currentPhase < 2 || creatingSimulation"
            @click="handleEnterEnvSetup"
          >
            <span v-if="creatingSimulation" class="spinner-sm"></span>
            {{ creatingSimulation ? "Creating..." : "Configure Environment ➝" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">System Dashboard</span>
        <span class="log-id">{{
          projectData?.project_id || "NO PROJECT"
        }}</span>
      </div>
      <div class="log-content scrollbar-thin" ref="logContent">
        <div class="log-line text-slate-300" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time text-slate-500">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { createSimulation } from "../api/simulation";

const router = useRouter();

const props = defineProps({
  currentPhase: { type: Number, default: 0 },
  projectData: Object,
  ontologyProgress: Object,
  buildProgress: Object,
  graphData: Object,
  systemLogs: { type: Array, default: () => [] },
});

const emit = defineEmits(["next-step"]);

const selectedOntologyItem = ref(null);
const logContent = ref(null);
const creatingSimulation = ref(false);

const handleEnterEnvSetup = async () => {
  if (!props.projectData?.project_id || !props.projectData?.graph_id) {
    if (import.meta.env.DEV) console.error("Missing project or graph info");
    return;
  }

  creatingSimulation.value = true;

  try {
    const res = await createSimulation({
      project_id: props.projectData.project_id,
      graph_id: props.projectData.graph_id,
      enable_twitter: true,
      enable_reddit: true,
    });

    if (res.success && res.data?.simulation_id) {
      emit("next-step", {
        simulationId: res.data.simulation_id
      });
    } else {
      if (import.meta.env.DEV) console.error("Failed to create simulation:", res.error);
      alert("Failed to create simulation: " + (res.error || "Unknown error"));
    }
  } catch (err) {
    if (import.meta.env.DEV) console.error("Simulation creation exception:", err);
    alert("Simulation creation exception: " + err.message);
  } finally {
    creatingSimulation.value = false;
  }
};

const selectOntologyItem = (item, type) => {
  selectedOntologyItem.value = { ...item, itemType: type };
};

const graphStats = computed(() => {
  const nodes =
    props.graphData?.node_count || props.graphData?.nodes?.length || 0;
  const edges =
    props.graphData?.edge_count || props.graphData?.edges?.length || 0;
  const types = props.projectData?.ontology?.entity_types?.length || 0;
  return { nodes, edges, types };
});

watch(
  () => props.systemLogs.length,
  () => {
    nextTick(() => {
      if (logContent.value) {
        logContent.value.scrollTop = logContent.value.scrollHeight;
      }
    });
  },
);
</script>

<style scoped>
.workbench-panel {
  height: 100%;
  background-color: var(--bg-color);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.step-card {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  transition: all 0.25s ease;
  position: relative;
}

.step-card.active {
  box-shadow: 0 10px 20px -8px rgba(0, 0, 0, 0.04);
  border-color: var(--border-color);
}

.step-card.completed {
  opacity: 0.65;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-secondary);
}

.step-title {
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
}

.badge {
  font-size: 9px;
  padding: 3px 10px;
  border-radius: 20px;
  font-weight: 700;
  text-transform: uppercase;
}

.badge.success {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
}
.badge.processing {
  background: #fee2e2;
  color: var(--accent-color);
}
.badge.accent {
  background: #ecfdf5;
  color: var(--accent-tertiary);
}
.badge.pending {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
}

.api-note {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-secondary);
  margin-bottom: 10px;
  font-weight: 600;
}

.description {
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 20px;
  color: var(--text-secondary);
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: var(--accent-color);
  margin-bottom: 16px;
  font-weight: 600;
}

/* Tags */
.tags-container {
  margin-top: 20px;
}

.tag-label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  font-size: 11px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 600;
  color: var(--text-secondary);
}

.entity-tag:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--border-color);
  color: var(--text-primary);
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-card {
  padding: 16px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-mono);
  line-height: 1;
}

.stat-label {
  font-size: 9px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-top: 6px;
}

/* Overlay */
.ontology-detail-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(8px);
  z-index: 50;
  display: flex;
  flex-direction: column;
  padding: 24px;
}

.detail-header {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 16px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-type-badge {
  font-size: 9px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  padding: 3px 8px;
  border-radius: 4px;
  margin-right: 12px;
  text-transform: uppercase;
}

.detail-name {
  font-weight: 700;
  font-size: 15px;
}

.detail-body {
  overflow-y: auto;
  flex-grow: 1;
}

.detail-desc {
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-weight: 700;
  font-size: 10px;
  margin-bottom: 10px;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.attr-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.attr-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
}
.attr-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.attr-name {
  font-weight: 700;
  font-size: 11px;
}
.attr-type {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-secondary);
}
.attr-desc {
  font-size: 10px;
  line-height: 1.4;
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.example-tag {
  background: rgba(255, 255, 255, 0.05);
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 500;
}

.conn-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.conn-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}
.conn-node {
  font-weight: 600;
}
.conn-arrow {
  color: var(--border-color);
}

.close-btn {
  background: rgba(255, 255, 255, 0.05);
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.action-btn {
  width: 100%;
  padding: 14px;
  background: var(--surface-color);
  color: var(--bg-color);
  border: none;
  font-weight: 600;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.action-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Logs */
.system-logs {
  background: var(--surface-color);
  padding: 20px;
  color: var(--bg-color);
  display: flex;
  flex-direction: column;
  min-height: 180px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.log-title {
  font-weight: 700;
  font-size: 11px;
  color: var(--accent-color);
}
.log-id {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-secondary);
}

.log-content {
  margin-top: 10px;
  height: 100px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 10px;
}
.log-line {
  margin-bottom: 4px;
}
.log-time {
  margin-right: 8px;
}

.spinner-sm {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top-color: var(--bg-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
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
.system-logs .scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
}
</style>

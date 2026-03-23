<template>
  <div class="workbench-panel">
    <div class="scroll-container">
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
            <span v-if="currentPhase > 0" class="badge success">COMPLETED</span>
            <span v-else-if="currentPhase === 0" class="badge processing"
              >GENERATING</span
            >
            <span v-else class="badge pending">WAITING</span>
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
                    ? "ENTITY"
                    : "RELATION"
                }}</span>
                <span class="detail-name">{{ selectedOntologyItem.name }}</span>
              </div>
              <button class="close-btn" @click="selectedOntologyItem = null">
                ×
              </button>
            </div>
            <div class="detail-body">
              <div class="detail-desc">
                {{ selectedOntologyItem.description }}
              </div>

              <!-- Attributes -->
              <div
                class="detail-section"
                v-if="selectedOntologyItem.attributes?.length"
              >
                <span class="section-label">ATTRIBUTES</span>
                <div class="attr-list">
                  <div
                    v-for="attr in selectedOntologyItem.attributes"
                    :key="attr.name"
                    class="attr-item"
                  >
                    <span class="attr-name">{{ attr.name }}</span>
                    <span class="attr-type">({{ attr.type }})</span>
                    <span class="attr-desc">{{ attr.description }}</span>
                  </div>
                </div>
              </div>

              <!-- Examples (Entity) -->
              <div
                class="detail-section"
                v-if="selectedOntologyItem.examples?.length"
              >
                <span class="section-label">EXAMPLES</span>
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
                <span class="section-label">CONNECTIONS</span>
                <div class="conn-list">
                  <div
                    v-for="(conn, idx) in selectedOntologyItem.source_targets"
                    :key="idx"
                    class="conn-item"
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
            <span class="tag-label">GENERATED ENTITY TYPES</span>
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
            <span class="tag-label">GENERATED RELATION TYPES</span>
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
            <span v-if="currentPhase > 1" class="badge success">COMPLETED</span>
            <span v-else-if="currentPhase === 1" class="badge processing"
              >{{ buildProgress?.progress || 0 }}%</span
            >
            <span v-else class="badge pending">WAITING</span>
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
              <span class="stat-value">{{ graphStats.nodes }}</span>
              <span class="stat-label">ENTITIES</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.edges }}</span>
              <span class="stat-label">RELATIONS</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.types }}</span>
              <span class="stat-label">SCHEMA TYPES</span>
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
              >IN PROGRESS</span
            >
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">
            Graph construction complete. Please proceed to the next step for
            environment setup.
          </p>
          <button
            class="action-btn"
            :disabled="currentPhase < 2 || creatingSimulation"
            @click="handleEnterEnvSetup"
          >
            <span v-if="creatingSimulation" class="spinner-sm"></span>
            {{ creatingSimulation ? "Creating..." : "ENTER ENV SETUP ➝" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <span class="log-id">{{
          projectData?.project_id || "NO_PROJECT"
        }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from "vue";
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

defineEmits(["next-step"]);

const selectedOntologyItem = ref(null);
const logContent = ref(null);
const creatingSimulation = ref(false);

const handleEnterEnvSetup = async () => {
  if (!props.projectData?.project_id || !props.projectData?.graph_id) {
    console.error("Missing project or graph info");
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
      router.push({
        name: "Simulation",
        params: { simulationId: res.data.simulation_id },
      });
    } else {
      console.error("Failed to create simulation:", res.error);
      alert("Failed to create simulation: " + (res.error || "Unknown error"));
    }
  } catch (err) {
    console.error("Simulation creation exception:", err);
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
  background-color: var(--atp-white);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: var(--font-sans);
  color: var(--atp-black);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.step-card {
  background: var(--atp-white);
  border: var(--border-width) solid var(--atp-black);
  border-radius: 0;
  padding: 40px;
  transition: all 0.2s;
  position: relative;
}

.step-card.active {
  box-shadow: 12px 12px 0px var(--atp-blue);
  transform: translate(-4px, -4px);
}

.step-card.completed {
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  border-bottom: var(--border-width) solid var(--atp-black);
  padding-bottom: 20px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 32px;
  font-weight: 900;
  color: var(--atp-black);
}

.step-title {
  font-weight: 900;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.badge {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 6px 16px;
  border-radius: 0;
  font-weight: 900;
  text-transform: uppercase;
  border: 2px solid var(--atp-black);
}

.badge.success {
  background: var(--atp-white);
  color: var(--atp-black);
}
.badge.processing {
  background: var(--atp-blue);
  color: var(--atp-white);
}
.badge.accent {
  background: var(--atp-yellow);
  color: var(--atp-black);
}
.badge.pending {
  background: #eee;
  color: #888;
  border-color: #ccc;
}

.api-note {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--atp-black);
  opacity: 0.5;
  margin-bottom: 16px;
  font-weight: 800;
}

.description {
  font-size: 0.95rem;
  line-height: 1.7;
  margin-bottom: 32px;
  font-weight: 500;
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 16px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--atp-blue);
  margin-bottom: 24px;
  font-weight: 900;
  text-transform: uppercase;
}

/* Tags */
.tags-container {
  margin-top: 32px;
}

.tag-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 900;
  color: var(--atp-black);
  margin-bottom: 16px;
  letter-spacing: 1px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.entity-tag {
  background: var(--atp-white);
  border: 2px solid var(--atp-black);
  padding: 8px 18px;
  font-size: 0.85rem;
  border-radius: 0;
  cursor: pointer;
  transition: all 0.1s;
  font-weight: 800;
  text-transform: uppercase;
}

.entity-tag:hover {
  background: var(--atp-yellow);
  transform: translate(-4px, -4px);
  box-shadow: 4px 4px 0px var(--atp-black);
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.stat-card {
  padding: 32px 20px;
  background: var(--atp-white);
  border: var(--border-width) solid var(--atp-black);
  border-radius: 0;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 2.5rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--atp-blue);
  line-height: 1;
}

.stat-label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 900;
  color: var(--atp-black);
  margin-top: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

/* Overlay */
.ontology-detail-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--atp-white);
  z-index: 50;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  padding: 40px;
  border: var(--border-width) solid var(--atp-black);
}

.detail-header {
  border-bottom: var(--border-width) solid var(--atp-black);
  padding-bottom: 24px;
  margin-bottom: 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-type-badge {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 900;
  background: var(--atp-black);
  color: var(--atp-white);
  padding: 6px 16px;
  border-radius: 0;
  margin-right: 20px;
}

.detail-name {
  font-weight: 900;
  font-size: 1.5rem;
  text-transform: uppercase;
}

.detail-body {
  overflow-y: auto;
}

.detail-desc {
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 32px;
}

.section-label {
  display: block;
  font-family: var(--font-mono);
  font-weight: 900;
  font-size: 0.8rem;
  margin-bottom: 16px;
  text-transform: uppercase;
  color: var(--atp-blue);
}

.attr-item {
  background: #f9f9f9;
  border: 2px solid var(--atp-black);
  padding: 16px;
  margin-bottom: 12px;
}

.attr-name {
  font-weight: 900;
  font-family: var(--font-mono);
  margin-right: 8px;
}

.action-btn {
  width: 100%;
  padding: 32px;
  background: var(--atp-black);
  color: var(--atp-white);
  border: var(--border-width) solid var(--atp-black);
  font-weight: 900;
  border-radius: 0;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 3px;
  font-family: var(--font-mono);
  font-size: 1rem;
  transition: all 0.1s;
}

.action-btn:hover:not(:disabled) {
  background: var(--atp-blue);
  transform: translate(-8px, -8px);
  box-shadow: 10px 10px 0px var(--atp-yellow);
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Logs */
.system-logs {
  background: #000;
  padding: 40px;
  border-top: var(--border-width) solid var(--atp-black);
  color: #fff;
}

.log-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 900;
  color: var(--atp-blue);
  letter-spacing: 4px;
}

.log-content {
  margin-top: 20px;
  height: 120px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 12px;
}

.spinner-sm {
  width: 20px;
  height: 20px;
  border: 4px solid rgba(0, 38, 254, 0.2);
  border-top-color: var(--atp-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}
</style>

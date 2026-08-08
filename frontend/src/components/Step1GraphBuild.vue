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
            <span class="step-title">Read the source material</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 0" class="badge success">Completed</span>
            <span v-else-if="currentPhase === 0" class="badge processing"
              >Reading</span
            >
            <span v-else class="badge pending">Waiting</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">SOURCE READING</p>
          <p class="description">
            A model proposes actor, place, concept, and relationship categories
            from the submitted material. Review them: they may be incomplete,
            ambiguous, or wrong.
          </p>

          <!-- Loading / Progress -->
          <div
            v-if="currentPhase === 0 && ontologyProgress"
            class="progress-section"
          >
            <div class="spinner-sm"></div>
            <span>{{
              ontologyProgress.message || "Reading source material…"
            }}</span>
          </div>

          <!-- Detail Overlay -->
          <div
            v-if="selectedOntologyItem"
            ref="detailDialog"
            class="ontology-detail-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ontology-detail-title"
            tabindex="-1"
            @keydown="handleDetailKeydown"
          >
            <div class="detail-header">
              <div class="detail-title-group">
                <span class="detail-type-badge">{{
                  selectedOntologyItem.itemType === "entity"
                    ? "Entity"
                    : "Relation"
                }}</span>
                <span id="ontology-detail-title" class="detail-name">{{
                  selectedOntologyItem.name
                }}</span>
              </div>
              <button
                ref="detailCloseButton"
                class="close-btn"
                type="button"
                aria-label="Close source-map detail"
                @click="closeOntologyDetail"
              >
                ×
              </button>
            </div>
            <div class="detail-body scrollbar-thin">
              <div class="detail-desc">
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
                    <span class="attr-desc">{{ attr.description }}</span>
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
            <span class="tag-label">People, places, and concepts</span>
            <div class="tags-list">
              <button
                v-for="entity in projectData.ontology.entity_types"
                :key="entity.name"
                class="entity-tag clickable"
                type="button"
                @click="openOntologyItem(entity, 'entity')"
              >
                {{ entity.name }}
              </button>
            </div>
          </div>

          <!-- Generated Relation Tags -->
          <div
            v-if="projectData?.ontology?.edge_types"
            class="tags-container"
            :class="{ dimmed: selectedOntologyItem }"
          >
            <span class="tag-label">Relationship categories proposed from the sources</span>
            <div class="tags-list">
              <button
                v-for="rel in projectData.ontology.edge_types"
                :key="rel.name"
                class="entity-tag clickable"
                type="button"
                @click="openOntologyItem(rel, 'relation')"
              >
                {{ rel.name }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Build Source Map -->
      <div
        class="step-card"
        :class="{ active: currentPhase === 1, completed: currentPhase > 1 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">Source map connections</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 1" class="badge success"
              >COMPLETED</span
            >
            <span v-else-if="currentPhase === 1" class="badge processing"
              >MAPPING</span
            >
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">GRAPH NETWORK · GROUNDING MATERIAL</p>
          <p class="description">
            A model connects submitted material into an inspectable map. Open
            any item to inspect the generated record. Map entries are not
            independently verified facts or evidence of causality.
          </p>

          <!-- Stats Cards -->
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.nodes }}</span>
              <span class="stat-label">Entities</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.edges }}</span>
              <span class="stat-label">Relations</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.types }}</span>
              <span class="stat-label">Types</span>
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
            <span class="step-title">Source map ready</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase >= 2" class="badge accent"
              >Ready</span
            >
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">NEXT: SET ASSUMPTIONS</p>
          <p class="description">
            Review the map, then define how the synthetic scenario should run.
          </p>
          <button
            class="action-btn"
            type="button"
            :disabled="!canContinue || creatingSimulation"
            :aria-describedby="!canContinue ? 'source-map-requirements' : undefined"
            @click="handleEnterEnvSetup"
          >
            <span v-if="creatingSimulation" class="spinner-sm"></span>
            {{ creatingSimulation ? "Opening…" : "Set the assumptions →" }}
          </button>
          <p
            v-if="!canContinue"
            id="source-map-requirements"
            class="readiness-note"
            aria-live="polite"
          >
            {{ sourceMapRequirement }}
          </p>
          <p v-if="creationError" class="inline-error" role="alert">{{ creationError }}</p>
        </div>
      </div>
    </div>

    <section class="activity-record" aria-labelledby="source-progress-heading">
      <div class="activity-status" role="status" aria-live="polite">
        <span id="source-progress-heading">Source-map progress</span>
        <strong>{{ latestActivityMessage }}</strong>
      </div>
      <details v-if="systemLogs.length" class="activity-history">
        <summary>
          <span>Review progress notes</span>
          <span class="activity-count">
            {{ systemLogs.length }} {{ systemLogs.length === 1 ? "note" : "notes" }}
          </span>
        </summary>
        <ol class="activity-list">
          <li class="activity-line" v-for="(log, idx) in systemLogs" :key="idx">
            <time class="activity-time">{{ log.time }}</time>
            <span class="activity-msg">{{ log.msg }}</span>
          </li>
        </ol>
      </details>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
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
const detailDialog = ref(null);
const detailCloseButton = ref(null);
const creatingSimulation = ref(false);
const creationError = ref("");
let detailReturnTarget = null;

const graphStats = computed(() => {
  const nodes =
    props.graphData?.node_count || props.graphData?.nodes?.length || 0;
  const edges =
    props.graphData?.edge_count || props.graphData?.edges?.length || 0;
  const types = props.projectData?.ontology?.entity_types?.length || 0;
  return { nodes, edges, types };
});

const hasProjectReferences = computed(
  () => Boolean(props.projectData?.project_id && props.projectData?.graph_id),
);
const hasGraphContent = computed(() => graphStats.value.nodes > 0);
const canContinue = computed(
  () => props.currentPhase >= 2 && hasGraphContent.value && hasProjectReferences.value,
);
const sourceMapRequirement = computed(() => {
  if (props.currentPhase < 2) return "Wait until the source map is finished.";
  if (!hasGraphContent.value) {
    return "The source map is empty. Rebuild it before setting assumptions.";
  }
  if (!hasProjectReferences.value) {
    return "The workspace is missing its project or source-map reference. Reopen the run or rebuild the map.";
  }
  return "";
});
const latestActivityMessage = computed(
  () =>
    props.systemLogs.at(-1)?.msg ||
    (props.currentPhase >= 2
      ? "Source map ready for review."
      : props.buildProgress?.message || props.ontologyProgress?.message || "Reading the source material."),
);

const handleEnterEnvSetup = async () => {
  creationError.value = "";
  if (!hasGraphContent.value) {
    creationError.value =
      "The source map contains no entities. Rebuild it before continuing.";
    return;
  }
  if (!props.projectData?.project_id || !props.projectData?.graph_id) {
    creationError.value =
      "The workspace is missing its project or source-map reference. Reopen the run or rebuild the map.";
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
      creationError.value =
        res.error || "The scenario workspace could not be created. Try again.";
    }
  } catch (err) {
    if (import.meta.env.DEV) console.error("Simulation creation exception:", err);
    creationError.value =
      err?.message || "The scenario workspace could not be created. Try again.";
  } finally {
    creatingSimulation.value = false;
  }
};

const openOntologyItem = (item, type) => {
  detailReturnTarget = document.activeElement;
  selectedOntologyItem.value = { ...item, itemType: type };
  nextTick(() => detailCloseButton.value?.focus());
};

const closeOntologyDetail = () => {
  selectedOntologyItem.value = null;
  nextTick(() => {
    if (detailReturnTarget?.isConnected) detailReturnTarget.focus();
  });
};

const handleDetailKeydown = (event) => {
  if (event.key === "Escape") {
    event.preventDefault();
    closeOntologyDetail();
    return;
  }
  if (event.key !== "Tab") return;

  const focusable = Array.from(
    detailDialog.value?.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) || [],
  );
  if (!focusable.length) {
    event.preventDefault();
    detailDialog.value?.focus();
    return;
  }
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
};
</script>

<style scoped>
.workbench-panel {
  height: 100%;
  background-color: transparent;
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
  background: var(--ink-soft);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  padding: 24px;
  transition: all 0.25s ease;
  position: relative;
}

.step-card:hover {
  border-color: rgba(242, 235, 221, 0.15);
  transform: translateY(-1px);
}

.step-card.active {
  border-color: var(--primary);
  box-shadow: none;
  background: var(--signal-faint);
}

.step-card.completed {
  opacity: 0.5;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(242, 235, 221, 0.08);
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
  background: linear-gradient(135deg, var(--primary), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.step-title {
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
}

.badge {
  font-size: 9px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge.success {
  background: var(--attention-tint);
  color: var(--attention);
  border: 1px solid var(--attention-rule);
}
.badge.processing {
  background: var(--signal-tint);
  color: var(--signal-soft);
  border: 1px solid var(--signal-rule);
}
.badge.accent {
  background: rgba(139, 92, 246, 0.15);
  color: var(--signal-soft);
  border: 1px solid rgba(139, 92, 246, 0.3);
}
.badge.pending {
  background: var(--ink-raised);
  color: var(--text-muted);
  border: 1px solid rgba(242, 235, 221, 0.05);
}

.api-note {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-muted);
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
  color: var(--primary);
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
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag {
  background: var(--signal-tint);
  border: 1px solid var(--signal-rule);
  padding: 6px 12px;
  font-size: 11px;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 600;
  color: var(--signal-soft);
  font-family: var(--font-sans);
  line-height: 1.2;
  text-transform: none;
  box-shadow: none;
  animation: pop-in 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards;
}

.entity-tag:nth-child(1) { animation-delay: 0.05s; }
.entity-tag:nth-child(2) { animation-delay: 0.1s; }
.entity-tag:nth-child(3) { animation-delay: 0.15s; }
.entity-tag:nth-child(4) { animation-delay: 0.2s; }
.entity-tag:nth-child(5) { animation-delay: 0.25s; }
.entity-tag:nth-child(6) { animation-delay: 0.3s; }
.entity-tag:nth-child(n+7) { animation-delay: 0.35s; }

@keyframes pop-in {
  0% { opacity: 0; transform: scale(0.8) translateY(10px); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}

.entity-tag:hover {
  background: var(--signal-wash);
  border-color: var(--primary);
  color: var(--signal-soft);
  box-shadow: none;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-card {
  padding: 16px 12px;
  background: var(--ink-raised);
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-sm);
  text-align: center;
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: rgba(242, 235, 221, 0.15);
  background: var(--ink-raised);
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
  right: 0;
  bottom: 0;
  width: 420px;
  max-width: 100%;
  left: auto;
  background: var(--ink-deep);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  z-index: 50;
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-left: 1px solid rgba(242, 235, 221, 0.1);
  box-shadow: -15px 0 40px rgba(0,0,0,0.6);
  transform: translateX(100%);
  animation: slide-drawer-in 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slide-drawer-in {
  to { transform: translateX(0); }
}

.detail-header {
  border-bottom: 1px solid rgba(242, 235, 221, 0.08);
  padding-bottom: 16px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-type-badge {
  font-size: 9px;
  font-weight: 700;
  background: var(--signal-tint);
  color: var(--signal-soft);
  border: 1px solid var(--signal-rule);
  padding: 3px 10px;
  border-radius: var(--radius-full);
  margin-right: 12px;
  text-transform: uppercase;
}

.detail-name {
  font-weight: 700;
  font-size: 15px;
  color: var(--text-primary);
}

.detail-body {
  overflow-y: auto;
  flex-grow: 1;
}

.detail-desc {
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 20px;
  color: var(--text-secondary);
}

.section-label {
  display: block;
  font-weight: 700;
  font-size: 10px;
  margin-bottom: 10px;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
}

.attr-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.attr-item {
  background: var(--ink-raised);
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: 6px;
  padding: 12px;
  color: var(--text-primary);
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
  background: rgba(139, 92, 246, 0.15);
  color: var(--signal-soft);
  border: 1px solid rgba(139, 92, 246, 0.3);
  padding: 4px 10px;
  border-radius: var(--radius-full);
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
  background: var(--ink-raised);
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: 6px;
  color: var(--text-primary);
}
.conn-node {
  font-weight: 600;
}
.conn-arrow {
  color: var(--primary);
}

.close-btn {
  background: var(--ink-raised);
  border: 1px solid rgba(242, 235, 221, 0.08);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}
.close-btn:hover {
  background: var(--signal-tint);
  border-color: var(--signal-rule);
  color: var(--signal-soft);
}

.action-btn {
  width: 100%;
  padding: 14px;
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border: 1px solid var(--accent) !important;
  font-weight: 700;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-radius: 0;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.15s ease, border-color 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: none;
}

.action-btn:hover:not(:disabled) {
  background: var(--accent-bright) !important;
  border-color: var(--accent-bright) !important;
  transform: none;
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Logs */
.system-logs {
  background: var(--bg-base);
  padding: 16px 20px;
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  min-height: 180px;
  border-top: 1px solid var(--line);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.log-title {
  font-weight: 700;
  font-size: 10px;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
}
.log-id {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-dim);
}

.log-content {
  margin-top: 10px;
  height: 100px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-secondary);
}
.log-line {
  margin-bottom: 4px;
  padding: 2px 4px;
  border-radius: 0;
  transition: background 0.15s ease;
}
.log-line:hover {
  background: var(--bg-hover);
  color: var(--text-void);
}
.log-time {
  margin-right: 8px;
  color: var(--text-muted);
}

.spinner-sm {
  width: 12px;
  height: 12px;
  border: 2px solid var(--line-strong);
  border-top-color: var(--accent);
  border-radius: 0;
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
  background: var(--line-strong);
  border-radius: 0;
}
.system-logs .scrollbar-thin::-webkit-scrollbar-thumb {
  background: var(--line-strong);
}

/* Public Signal: readable editorial work surface */
.workbench-panel {
  border: 0 !important;
  background: var(--paper) !important;
  color: var(--ink);
}

.scroll-container {
  gap: 1rem;
  padding: clamp(0.85rem, 2vw, 1.5rem);
  background:
    linear-gradient(rgba(17, 21, 19, 0.045) 1px, transparent 1px),
    var(--paper);
  background-size: 100% 2.4rem;
}

.step-card,
.step-card.active,
.step-card.completed {
  padding: clamp(1rem, 2vw, 1.45rem);
  border: 1px solid var(--line-light) !important;
  border-radius: 0;
  background: var(--paper-strong) !important;
  color: var(--ink);
  opacity: 1;
  box-shadow: 0.4rem 0.4rem 0 var(--line-light) !important;
  backdrop-filter: none;
}

.step-card.active,
.step-card:hover {
  border-color: var(--ink) !important;
  box-shadow: 0.4rem 0.4rem 0 var(--signal) !important;
  transform: none;
}

.step-card.active {
  box-shadow: 0.4rem 0.4rem 0 var(--signal) !important;
}

.card-header {
  margin: calc(clamp(1rem, 2vw, 1.45rem) * -1)
    calc(clamp(1rem, 2vw, 1.45rem) * -1) 1.25rem;
  padding: 0.75rem clamp(1rem, 2vw, 1.45rem);
  border-color: var(--ink);
  background: var(--ink-deep) !important;
}

.step-num {
  background: none;
  color: var(--signal) !important;
  -webkit-text-fill-color: currentColor;
}

.step-title {
  color: var(--paper) !important;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.badge,
.badge.success,
.badge.processing,
.badge.accent {
  border: 1px solid var(--signal);
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
}

.badge.pending {
  border-color: var(--line-dark);
  border-radius: 0;
  background: var(--ink-raised);
  color: var(--paper-muted);
}

.api-note {
  color: var(--signal-text) !important;
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
}

.description,
.tag-label,
.stat-label {
  color: var(--ink-muted) !important;
}

.description {
  font-size: 0.88rem;
}

.entity-tag,
.example-tag,
.detail-type-badge {
  border: 1px solid var(--line-light);
  border-radius: 0;
  background: var(--signal-soft);
  color: var(--ink);
}

.entity-tag:hover {
  border-color: var(--ink);
  background: var(--signal);
  color: var(--ink);
  box-shadow: none;
}

.stat-card,
.attr-item,
.conn-item {
  border: 1px solid var(--line-light);
  border-radius: 0;
  background: var(--paper);
  color: var(--ink);
}

.stat-value {
  display: inline-block;
  color: var(--signal-text) !important;
  animation: stat-flash 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes stat-flash {
  0% { color: var(--paper); transform: scale(1.2); text-shadow: none; }
  100% { color: var(--signal-text); transform: scale(1); text-shadow: none; }
}

.ontology-detail-overlay {
  border-radius: 0;
  background: var(--paper-strong);
  color: var(--ink);
  backdrop-filter: none;
}

.ontology-detail-overlay :is(.detail-name, .attr-item, .conn-item) {
  color: var(--ink);
}

.ontology-detail-overlay :is(.detail-desc, .section-label, .attr-desc, .attr-type) {
  color: var(--ink-muted) !important;
}

.inline-error {
  margin: 0.75rem 0 0;
  color: var(--error-text);
  font-size: 0.78rem;
  font-weight: 650;
}

.readiness-note {
  margin: 0.75rem 0 0;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.45;
}

.activity-record {
  margin: 1.5rem clamp(0.85rem, 2vw, 1.5rem);
  border-top: 3px solid var(--signal);
  border-bottom: 1px solid var(--line-light);
  background: var(--paper);
}

.activity-status {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.8rem;
  align-items: baseline;
  padding: 1rem 0;
  color: var(--ink);
}

.activity-status > span,
.activity-history summary {
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.activity-status strong {
  overflow: hidden;
  color: var(--ink-muted);
  font-size: 0.84rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-history {
  border-top: 1px solid var(--line-light);
}

.activity-history summary {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 0;
  color: var(--ink);
  cursor: pointer;
  list-style: none;
}

.activity-history summary::-webkit-details-marker {
  display: none;
}

.activity-history summary::before {
  content: "+";
  color: var(--signal);
  font-family: var(--font-body);
  font-weight: 800;
}

.activity-history[open] summary::before {
  content: "−";
}

.activity-count {
  margin-left: auto;
  color: var(--ink-muted);
}

.activity-list {
  margin: 0;
  max-height: 180px;
  overflow-y: auto;
  padding: 0 0 0.65rem;
  list-style: none;
}

.activity-line {
  display: grid;
  grid-template-columns: 5.25rem minmax(0, 1fr);
  gap: 0.8rem;
  padding: 0.65rem 0;
  border-top: 1px solid color-mix(in srgb, var(--line-light) 72%, transparent);
  color: var(--ink);
  font-size: 0.8rem;
  line-height: 1.45;
}

.activity-time {
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.activity-msg {
  color: var(--ink);
}

.ontology-detail-overlay:focus {
  outline: none;
}

@media (max-width: 620px) {
  .stats-grid {
    gap: 0.4rem;
  }

  .stat-card {
    padding: 0.8rem 0.3rem;
  }

  .activity-status {
    grid-template-columns: 1fr;
    gap: 0.2rem;
  }

  .activity-line {
    grid-template-columns: 1fr;
    gap: 0.15rem;
  }
}
</style>

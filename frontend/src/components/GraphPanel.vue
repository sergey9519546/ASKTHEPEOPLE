<template>
  <div class="graph-panel-workbench">
    <!-- Header -->
    <header class="panel-header-block">
      <div class="header-left">
        <h2 class="panel-label" aria-live="polite">{{ phaseLabels }}</h2>
      </div>
      <div class="header-right">
        <button
          class="btn-action small"
          @click="$emit('refresh')"
          :disabled="loading"
          title="Refresh Graph"
          aria-label="Refresh graph data"
        >
          <span
            class="btn-icon"
            :class="{ 'is-spinning': loading }"
            aria-hidden="true"
            >↻</span
          >
          <span class="btn-text">Refresh</span>
        </button>
        <button
          class="btn-action small square"
          @click="$emit('toggle-maximize')"
          title="Maximize View"
          aria-label="Toggle maximize view"
        >
          <span class="btn-icon" aria-hidden="true">⛶</span>
        </button>
      </div>
    </header>

    <div class="viewport-container" ref="graphContainer">
      <!-- D3 SVG Layer -->
      <div v-if="graphData" class="graph-canvas-wrapper">
        <svg ref="graphSvg" class="graph-svg-element"></svg>

        <!-- Live Status Hint -->
        <div
          v-if="currentPhase === 1 || isSimulating"
          class="status-overlay-hint"
        >
          <div class="status-icon-box">
            <div class="pulse-dot"></div>
          </div>
          <span class="status-msg">{{
            isSimulating ? "GRAPHRAG LTM BROADCASTING..." : "LIVE STREAM ACTIVE"
          }}</span>
        </div>

        <!-- Completion Hint -->
        <div
          v-if="showSimulationFinishedHint"
          class="status-overlay-hint completion-hint"
        >
          <div class="status-icon-box">✓</div>
          <span class="status-msg">SEQUENCE TERMINATED. REFRESH ARCHIVE.</span>
          <button class="hint-close" @click="dismissFinishedHint">×</button>
        </div>

        <!-- Entity Detail Panel (Sidebar within Graph) -->
        <Transition name="panel-slide">
          <div
            v-if="selectedItem"
            class="entity-detail-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="detail-header"
          >
            <header class="detail-header" id="detail-header">
              <span class="detail-category">{{
                selectedItem.type === "node" ? "NODE DATA" : "RELATION LINK"
              }}</span>
              <span
                v-if="selectedItem.type === 'node'"
                class="type-badge"
                :style="{ background: selectedItem.color }"
              >
                {{ selectedItem.entityType }}
              </span>
              <button
                class="close-detail-btn"
                @click="closeDetailPanel"
                aria-label="Close detail panel"
              >
                ×
              </button>
            </header>

            <div class="detail-scroll-area scrollbar-thin">
              <!-- Node Specific -->
              <div v-if="selectedItem.type === 'node'" class="node-attributes">
                <div class="attr-row">
                  <label>Identifier</label>
                  <div class="attr-value title text-rose-500">
                    {{ selectedItem.data.name }}
                  </div>
                </div>
                <div class="attr-row">
                  <label>UUID Hex</label>
                  <div class="attr-value mono text-slate-500">
                    {{ selectedItem.data.uuid }}
                  </div>
                </div>

                <div
                  class="attr-section"
                  v-if="
                    selectedItem.data.attributes &&
                    Object.keys(selectedItem.data.attributes).length > 0
                  "
                >
                  <h4 class="section-label">Properties</h4>
                  <div class="properties-grid">
                    <div
                      v-for="(v, k) in selectedItem.data.attributes"
                      :key="k"
                      class="prop-item"
                    >
                      <span class="p-key">{{ k }}</span>
                      <span class="p-val">{{ v || "N/A" }}</span>
                    </div>
                  </div>
                </div>

                <div class="attr-section" v-if="selectedItem.data.summary">
                  <h4 class="section-label">Synthesis</h4>
                  <div class="summary-box">{{ selectedItem.data.summary }}</div>
                </div>
              </div>

              <!-- Edge Specific -->
              <div v-else class="edge-attributes">
                <div
                  v-if="selectedItem.data.isSelfLoopGroup"
                  class="self-loop-header"
                >
                  Loop: {{ selectedItem.data.source_name }} —
                  {{ selectedItem.data.selfLoopCount }} REF
                </div>
                <div v-else class="edge-path-header text-slate-800">
                  {{ selectedItem.data.source_name }} →
                  {{ selectedItem.data.name || "LINKED" }} →
                  {{ selectedItem.data.target_name }}
                </div>

                <div class="attr-row">
                  <label>Relationship Type</label>
                  <div class="attr-value highlight text-rose-500">
                    {{
                      selectedItem.data.fact_type ||
                      selectedItem.data.name ||
                      "General"
                    }}
                  </div>
                </div>

                <div v-if="selectedItem.data.fact" class="attr-section">
                  <h4 class="section-label">Observed Fact</h4>
                  <div class="fact-box">{{ selectedItem.data.fact }}</div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <!-- State Placeholders -->
      <div v-else-if="loading" class="state-placeholder">
        <div class="spinner-large"></div>
        <p class="text-xs text-slate-400 font-medium">Initializing Graph Engine...</p>
      </div>

      <div v-else class="state-placeholder">
        <div class="geometric-shape"></div>
        <p class="text-xs text-slate-400 font-medium">Awaiting Ontology Deployment</p>
      </div>
    </div>

    <!-- UI Overlays -->
    <footer class="graph-ui-overlays">
      <!-- Legend -->
      <div
        v-if="graphData && entityTypes.length"
        class="type-legend"
      >
        <h5 class="legend-header">Entity Map</h5>
        <div class="legend-list scrollbar-thin">
          <div v-for="type in entityTypes" :key="type.name" class="legend-item">
            <span
              class="color-swatch"
              :style="{ background: type.color }"
            ></span>
            <span class="type-name">{{ type.name }}</span>
          </div>
        </div>
      </div>

      <!-- Toggle -->
      <div v-if="graphData" class="view-controls">
        <div class="control-row">
          <span class="control-label">Edge Labels</span>
          <label class="switch-control">
            <input
              type="checkbox"
              v-model="showEdgeLabels"
              aria-label="Toggle edge labels"
            />
            <span class="switch-slider" aria-hidden="true"></span>
          </label>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import * as d3 from "d3";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

const props = defineProps({
  graphData: Object,
  loading: Boolean,
  currentPhase: Number,
  isSimulating: Boolean,
});

const phaseLabels = computed(() => {
  const labels = {
    1: "Phase 01: Ontology Visualization",
    2: "Phase 02: Simulation Preparation",
    3: "Phase 03: Simulation Execution",
    4: "Phase 04: Report Generation",
    5: "Phase 05: Deep Interaction",
  };
  return labels[props.currentPhase] || "Ontology Visualization";
});

const emit = defineEmits(["refresh", "toggle-maximize"]);

// Refs & State
const graphContainer = ref(null);
const graphSvg = ref(null);
const selectedItem = ref(null);
const showEdgeLabels = ref(true);
const showSimulationFinishedHint = ref(false);
const wasSimulating = ref(false);
let currentSimulation = null;
let gSelection = null;

// Watchers
watch(
  () => props.isSimulating,
  (newV) => {
    if (wasSimulating.value && !newV) showSimulationFinishedHint.value = true;
    wasSimulating.value = newV;
  },
  { immediate: true },
);

const dismissFinishedHint = () => (showSimulationFinishedHint.value = false);

const entityTypes = computed(() => {
  if (!props.graphData?.nodes) return [];
  // Elegant Slate/Rose Palette
  const palette = [
    "#ef4444", // Rose/Red 500
    "#3b82f6", // Blue 500
    "#10b981", // Emerald 500
    "#6366f1", // Indigo 500
    "#f59e0b", // Amber 500
    "#8b5cf6", // Purple 500
    "#ec4899", // Pink 500
  ];
  const map = {};
  props.graphData.nodes.forEach((n) => {
    const t = n.labels?.find((l) => l !== "Entity") || "ENTITY";
    if (!map[t])
      map[t] = {
        name: t,
        color: palette[Object.keys(map).length % palette.length],
      };
  });
  return Object.values(map);
});

const closeDetailPanel = () => (selectedItem.value = null);

// D3 Rendering Logic
const render = () => {
  if (!graphSvg.value || !props.graphData) return;
  if (currentSimulation) currentSimulation.stop();

  const width = graphContainer.value.clientWidth;
  const height = graphContainer.value.clientHeight;
  if (!width || !height) return;

  const svg = d3
    .select(graphSvg.value)
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", `0 0 ${width} ${height}`);
  
  svg.on(".zoom", null);
  svg.selectAll("*").remove();

  const nodes = (props.graphData.nodes || []).map((n) => ({
    id: n.uuid,
    name: n.name,
    type: n.labels?.find((l) => l !== "Entity") || "ENTITY",
    raw: n,
  }));
  const edges = (props.graphData.edges || []).map((e) => ({
    source: e.source_node_uuid,
    target: e.target_node_uuid,
    label: e.fact_type || e.name || "LINKED",
    raw: e,
  }));

  if (nodes.length === 0) return;

  const simulation = d3
    .forceSimulation(nodes)
    .force(
      "link",
      d3
        .forceLink(edges)
        .id((d) => d.id)
        .distance(150),
    )
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide(50));

  currentSimulation = simulation;
  const g = svg.append("g");
  const zoomBehavior = d3
    .zoom()
    .scaleExtent([0.1, 8])
    .on("zoom", (event) => g.attr("transform", event.transform));
  svg.call(zoomBehavior);

  const links = g
    .append("g")
    .selectAll("line")
    .data(edges)
    .enter()
    .append("line")
    .attr("stroke", "rgba(148, 163, 184, 0.5)")
    .attr("stroke-width", 1.5);

  const nodeDots = g
    .append("g")
    .selectAll("circle")
    .data(nodes)
    .enter()
    .append("circle")
    .attr("r", 12)
    .attr(
      "fill",
      (d) => entityTypes.value.find((t) => t.name === d.type)?.color || "#94a3b8",
    )
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 2)
    .style("cursor", "pointer")
    .on("click", (event, d) => {
      event.stopPropagation();
      selectedItem.value = {
        type: "node",
        data: d.raw,
        entityType: d.type,
        color: entityTypes.value.find((t) => t.name === d.type)?.color,
      };
    })
    .call(
      d3
        .drag()
        .on("start", dragStarted)
        .on("drag", dragged)
        .on("end", dragEnded),
    );

  const labels = g
    .append("g")
    .selectAll("text")
    .data(nodes)
    .enter()
    .append("text")
    .text((d) => d.name)
    .attr("font-size", "10px")
    .attr("font-weight", "700")
    .attr("fill", "#1e293b")
    .attr("dx", 16)
    .attr("dy", 4);

  simulation.on("tick", () => {
    links
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);
    nodeDots.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
    labels.attr("x", (d) => d.x).attr("y", (d) => d.y);
  });

  function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
};

watch(
  () => props.graphData,
  () => nextTick(render),
  { deep: true },
);
onMounted(() => {
  nextTick(render);
  window.addEventListener("resize", render);
});
onUnmounted(() => {
  window.removeEventListener("resize", render);
  if (currentSimulation) currentSimulation.stop();
});
</script>


<style scoped>
.graph-panel-workbench {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  position: relative;
  overflow: hidden;
}

.panel-header-block {
  height: 50px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--surface-color);
  backdrop-filter: blur(16px);
}

.panel-label {
  font-weight: 700;
  font-size: 13px;
  letter-spacing: -0.2px;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  gap: 8px;
}

.viewport-container {
  flex-grow: 1;
  position: relative;
  overflow: hidden;
  background: var(--bg-color);
}

.graph-canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.graph-svg-element {
  width: 100%;
  height: 100%;
  display: block;
}

.status-overlay-hint {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 69, 0, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid var(--accent-color);
  padding: 6px 12px;
  border-radius: 20px;
  z-index: 10;
  box-shadow: 0 0 15px rgba(255, 69, 0, 0.2);
}
.completion-hint {
  background: rgba(16, 185, 129, 0.1);
  border-color: #10b981;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
}
.status-msg {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 9px;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}
.status-icon-box {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #10b981;
  font-weight: 700;
  font-size: 10px;
}
.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-color);
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 69, 0, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 69, 0, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 69, 0, 0); }
}
.hint-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  margin-left: 4px;
}
.hint-close:hover {
  color: var(--text-primary);
}

.entity-detail-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 280px;
  max-height: calc(100% - 32px);
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  z-index: 100;
  color: var(--text-primary);
}

.detail-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-category {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
}
.type-badge {
  font-size: 8px;
  font-weight: 700;
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}
.close-detail-btn {
  background: none;
  border: none;
  font-size: 16px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.15s ease;
  margin-left: auto;
}
.close-detail-btn:hover {
  color: var(--accent-color);
}

.detail-scroll-area {
  padding: 16px;
  overflow-y: auto;
  flex-grow: 1;
}
.attr-row {
  margin-bottom: 12px;
}
.attr-row label {
  display: block;
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
  margin-bottom: 2px;
  text-transform: uppercase;
}
.attr-value {
  font-weight: 600;
  font-size: 12px;
  color: var(--text-primary);
}
.attr-value.title {
  font-size: 14px;
  font-weight: 700;
}
.attr-value.mono {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-secondary);
  word-break: break-all;
}

.attr-section {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}
.section-label {
  font-weight: 700;
  font-size: 9px;
  margin-bottom: 8px;
  color: var(--text-secondary);
  text-transform: uppercase;
}
.summary-box {
  font-size: 11px;
  line-height: 1.6;
  background: rgba(0, 0, 0, 0.3);
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
}

.graph-ui-overlays {
  position: absolute;
  bottom: 16px;
  left: 0;
  right: 0;
  padding: 0 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  pointer-events: none;
}

.type-legend {
  padding: 10px 12px;
  max-width: 240px;
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  pointer-events: auto;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}
.legend-header {
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.legend-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 100px;
  overflow-y: auto;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.color-swatch {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.type-name {
  font-weight: 600;
  font-size: 9px;
  color: var(--text-primary);
}

.view-controls {
  padding: 8px 12px;
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  pointer-events: auto;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}
.control-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.control-label {
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
}

.btn-action {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  font-weight: 600;
  font-size: 11px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-primary);
}
.btn-action:hover {
  background: rgba(255, 69, 0, 0.1);
  border-color: var(--accent-color);
  color: var(--accent-color);
}
.btn-action.square {
  padding: 6px;
  width: 28px;
  height: 28px;
  justify-content: center;
}
.is-spinning {
  animation: spin 0.8s infinite linear;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Switch styling */
.switch-control {
  position: relative;
  width: 28px;
  height: 16px;
  display: inline-block;
}
.switch-control input {
  opacity: 0;
  width: 0;
  height: 0;
}
.switch-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 34px;
  transition: .2s;
}
.switch-slider:before {
  position: absolute;
  content: "";
  height: 10px;
  width: 10px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: .2s;
}
input:checked + .switch-slider {
  background-color: var(--accent-color);
}
input:checked + .switch-slider:before {
  transform: translateX(12px);
}

.state-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-secondary);
}
.spinner-large {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}
.geometric-shape {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  transform: rotate(45deg);
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


<template>
  <div class="graph-panel-workbench">
    <!-- Header -->
    <header class="panel-header-block">
      <div class="header-left">
        <h2 class="panel-label">PHASE 01: ONTOLOGY VISUALIZATION</h2>
      </div>
      <div class="header-right">
        <button
          class="bauhaus-btn small"
          @click="$emit('refresh')"
          :disabled="loading"
          title="Refresh Graph"
        >
          <span class="btn-icon" :class="{ 'is-spinning': loading }">↻</span>
          <span class="btn-text">REFRESH</span>
        </button>
        <button
          class="bauhaus-btn small square"
          @click="$emit('toggle-maximize')"
          title="Maximize View"
        >
          <span class="btn-icon">⛶</span>
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
          <div v-if="selectedItem" class="entity-detail-panel bauhaus-card">
            <header class="detail-header">
              <span class="detail-category">{{
                selectedItem.type === "node" ? "NODE_DATA" : "RELATION_LINK"
              }}</span>
              <span
                v-if="selectedItem.type === 'node'"
                class="type-badge"
                :style="{ background: selectedItem.color }"
              >
                {{ selectedItem.entityType.toUpperCase() }}
              </span>
              <button class="close-detail-btn" @click="closeDetailPanel">
                ×
              </button>
            </header>

            <div class="detail-scroll-area">
              <!-- Node Specific -->
              <div v-if="selectedItem.type === 'node'" class="node-attributes">
                <div class="attr-row">
                  <label>IDENTIFIER</label>
                  <div class="attr-value title">
                    {{ selectedItem.data.name }}
                  </div>
                </div>
                <div class="attr-row">
                  <label>UUID_HEX</label>
                  <div class="attr-value mono">
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
                  <h4 class="section-label">PROPERTIES</h4>
                  <div class="properties-grid">
                    <div
                      v-for="(v, k) in selectedItem.data.attributes"
                      :key="k"
                      class="prop-item"
                    >
                      <span class="p-key">{{ k.toUpperCase() }}</span>
                      <span class="p-val">{{ v || "N/A" }}</span>
                    </div>
                  </div>
                </div>

                <div class="attr-section" v-if="selectedItem.data.summary">
                  <h4 class="section-label">SYNTHESIS</h4>
                  <div class="summary-box">{{ selectedItem.data.summary }}</div>
                </div>
              </div>

              <!-- Edge Specific -->
              <div v-else class="edge-attributes">
                <div
                  v-if="selectedItem.data.isSelfLoopGroup"
                  class="self-loop-header"
                >
                  LOOP: {{ selectedItem.data.source_name }} —
                  {{ selectedItem.data.selfLoopCount }} REF
                </div>
                <div v-else class="edge-path-header">
                  {{ selectedItem.data.source_name }} →
                  {{ (selectedItem.data.name || "LINKED").toUpperCase() }} →
                  {{ selectedItem.data.target_name }}
                </div>

                <div class="attr-row">
                  <label>LAB_TYPE</label>
                  <div class="attr-value highlight">
                    {{
                      (
                        selectedItem.data.fact_type ||
                        selectedItem.data.name ||
                        "GENERAL"
                      ).toUpperCase()
                    }}
                  </div>
                </div>

                <div v-if="selectedItem.data.fact" class="attr-section">
                  <h4 class="section-label">OBSERVED_FACT</h4>
                  <div class="fact-box">{{ selectedItem.data.fact }}</div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <!-- State Placeholders -->
      <div v-else-if="loading" class="state-placeholder">
        <div class="bauhaus-spinner-large"></div>
        <p>INITIALIZING GRAPH ENGINE...</p>
      </div>

      <div v-else class="state-placeholder">
        <div class="geometric-shape"></div>
        <p>AWAITING ONTOLOGY DEPLOYMENT</p>
      </div>
    </div>

    <!-- UI Overlays -->
    <footer class="graph-ui-overlays">
      <!-- Legend -->
      <div
        v-if="graphData && entityTypes.length"
        class="type-legend bauhaus-card"
      >
        <h5 class="legend-header">ENTITY_MAP</h5>
        <div class="legend-list">
          <div v-for="type in entityTypes" :key="type.name" class="legend-item">
            <span
              class="color-swatch"
              :style="{ background: type.color }"
            ></span>
            <span class="type-name">{{ type.name.toUpperCase() }}</span>
          </div>
        </div>
      </div>

      <!-- Toggle -->
      <div v-if="graphData" class="view-controls bauhaus-card">
        <div class="control-row">
          <span class="control-label">EDGE_LABELS</span>
          <label class="bauhaus-switch">
            <input type="checkbox" v-model="showEdgeLabels" />
            <span class="switch-slider"></span>
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
  // Modernist Brutal Palette with new Accents
  const palette = [
    "#22d3ee",
    "#a855f7",
    "#4ade80",
    "#000000",
    "#AAAAAA",
    "#555555",
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
  const svg = d3
    .select(graphSvg.value)
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", `0 0 ${width} ${height}`);
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
    .force("charge", d3.forceManyBody().strength(-500))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide(60));

  currentSimulation = simulation;
  const g = svg.append("g");
  svg.call(
    d3
      .zoom()
      .scaleExtent([0.1, 8])
      .on("zoom", (event) => g.attr("transform", event.transform)),
  );

  const links = g
    .append("g")
    .selectAll("line")
    .data(edges)
    .enter()
    .append("line")
    .attr("stroke", "#000")
    .attr("stroke-width", 2);
  const nodeDots = g
    .append("g")
    .selectAll("circle")
    .data(nodes)
    .enter()
    .append("circle")
    .attr("r", 14)
    .attr(
      "fill",
      (d) => entityTypes.value.find((t) => t.name === d.type)?.color || "#999",
    )
    .attr("stroke", "#000")
    .attr("stroke-width", 3)
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
    .attr("font-weight", "900")
    .attr("dx", 18)
    .attr("dy", 5);

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
  background: var(--atp-white);
  border: var(--border-width) solid var(--atp-black);
  position: relative;
  overflow: hidden;
}

.panel-header-block {
  height: 60px;
  padding: 0 20px;
  border-bottom: var(--border-width) solid var(--atp-black);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--atp-white);
  z-index: 10;
}

.panel-label {
  font-weight: 900;
  font-size: 13px;
  letter-spacing: 2px;
}

.header-right {
  display: flex;
  gap: 10px;
}

.viewport-container {
  flex: 1;
  position: relative;
  background: var(--atp-white);
}

.graph-canvas-wrapper {
  width: 100%;
  height: 100%;
}

.status-overlay-hint {
  position: absolute;
  top: 20px;
  left: 20px;
  background: var(--atp-cyan);
  padding: 8px 15px;
  border: var(--border-width) solid var(--atp-black);
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 900;
  font-size: 11px;
  z-index: 5;
  color: var(--atp-black);
}

.pulse-dot {
  width: 10px;
  height: 10px;
  background: var(--atp-white);
  border-radius: 50%;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
  100% {
    opacity: 1;
  }
}

.entity-detail-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 320px;
  max-height: calc(100% - 40px);
  background: var(--atp-white);
  border: var(--border-width) solid var(--atp-black);
  box-shadow: 10px 10px 0 var(--atp-black);
  display: flex;
  flex-direction: column;
  z-index: 20;
}

.detail-header {
  padding: 15px 20px;
  border-bottom: var(--border-width) solid var(--atp-black);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.detail-category {
  font-weight: 900;
  font-size: 10px;
  letter-spacing: 1px;
  color: #666;
}
.type-badge {
  font-weight: 900;
  font-size: 10px;
  color: var(--atp-white);
  padding: 2px 8px;
  border: 1.5px solid var(--atp-black);
}
.close-detail-btn {
  background: none;
  border: none;
  font-size: 20px;
  font-weight: 900;
  cursor: pointer;
}

.detail-scroll-area {
  padding: 20px;
  overflow-y: auto;
}
.attr-row {
  margin-bottom: 15px;
}
.attr-row label {
  display: block;
  font-weight: 900;
  font-size: 9px;
  color: #888;
  margin-bottom: 4px;
}
.attr-value {
  font-weight: 800;
  font-size: 14px;
}
.attr-value.title {
  font-size: 18px;
  color: var(--atp-cyan);
  text-transform: uppercase;
}
.attr-value.mono {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #555;
}

.attr-section {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 2px solid #eee;
}
.section-label {
  font-weight: 900;
  font-size: 10px;
  margin-bottom: 10px;
  color: var(--atp-black);
}
.summary-box {
  font-size: 13px;
  line-height: 1.5;
  background: #f9f9f9;
  padding: 12px;
  border: 2px solid var(--atp-black);
  border-radius: 0;
}

.graph-ui-overlays {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  pointer-events: none;
}

.bauhaus-card {
  background: var(--atp-white);
  border: 2.5px solid var(--atp-black);
  pointer-events: auto;
}

.type-legend {
  padding: 12px 15px;
  max-width: 250px;
}
.legend-header {
  font-weight: 900;
  font-size: 9px;
  margin-bottom: 8px;
}
.legend-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.color-swatch {
  width: 12px;
  height: 12px;
  border: 1px solid var(--atp-black);
  flex-shrink: 0;
}
.type-name {
  font-weight: 800;
  font-size: 9px;
}

.view-controls {
  padding: 10px 15px;
}
.control-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.control-label {
  font-weight: 900;
  font-size: 9px;
}

.bauhaus-btn {
  background: var(--atp-white);
  border: 2.5px solid var(--atp-black);
  padding: 6px 15px;
  font-weight: 900;
  font-size: 11px;
  cursor: pointer;
  transition: 0.2s;
  font-family: var(--font-mono);
}
.bauhaus-btn:hover {
  background: var(--atp-cyan);
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0 var(--atp-black);
}
.is-spinning {
  animation: spin 0.8s infinite linear;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.bauhaus-switch {
  position: relative;
  width: 34px;
  height: 18px;
}
.bauhaus-switch input {
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
  background-color: var(--atp-white);
  border: 2px solid var(--atp-black);
  transition: 0.2s;
}
.switch-slider:before {
  position: absolute;
  content: "";
  height: 10px;
  width: 10px;
  left: 2px;
  bottom: 1.5px;
  background-color: var(--atp-black);
  transition: 0.2s;
}
input:checked + .switch-slider {
  background-color: var(--atp-cyan);
}
input:checked + .switch-slider:before {
  transform: translateX(15px);
  background-color: var(--atp-white);
}

.state-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  font-weight: 900;
  font-size: 14px;
  color: #ccc;
}
.bauhaus-spinner-large {
  width: 60px;
  height: 60px;
  border: 8px solid var(--atp-black);
  border-top-color: var(--atp-cyan);
  animation: spin 1s infinite linear;
}
.geometric-shape {
  width: 60px;
  height: 60px;
  background: var(--atp-cyan);
  border: 4px solid var(--atp-black);
  transform: rotate(45deg);
}
</style>

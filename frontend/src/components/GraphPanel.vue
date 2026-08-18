<template>
  <div class="graph-panel-workbench">
    <!-- Header -->
    <header
      class="panel-header-block"
      :aria-hidden="selectedItem ? 'true' : undefined"
      :inert="selectedItem ? '' : undefined"
    >
      <div class="header-left">
        <h2 class="panel-label" aria-live="polite">{{ phaseLabels }}</h2>
      </div>
      <div class="header-right">
        <input
          v-model="searchQuery"
          type="text"
          class="graph-search-input"
          placeholder="Filter nodes…"
          aria-label="Filter map nodes"
          autocomplete="off"
          name="graph-search"
          spellcheck="false"
        />
        <button
          class="btn-action small"
          @click="$emit('refresh')"
          :disabled="loading"
          title="Refresh the source map"
          aria-label="Refresh the source map"
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
          title="Change map size"
          aria-label="Change source map size"
        >
          <svg class="btn-icon maximize-icon" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M3 8V3h5M12 3h5v5M17 12v5h-5M8 17H3v-5"></path>
          </svg>
        </button>
      </div>
    </header>

    <div class="viewport-container" ref="graphContainer">
      <!-- D3 SVG Layer -->
      <div v-if="loading" class="state-placeholder" role="status">
        <div class="map-loading-lines" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <strong>Loading the source map…</strong>
        <p>Keeping source material separate from generated scenario paths.</p>
      </div>

      <div v-else-if="hasGraphNodes" class="graph-canvas-wrapper">
        <div
          class="graph-background-layer"
          :aria-hidden="selectedItem ? 'true' : undefined"
          :inert="selectedItem ? '' : undefined"
        >
          <svg
            ref="graphSvg"
            class="graph-svg-element"
            role="group"
            aria-label="Source-map items. Tab to an item and press Enter for details."
          ></svg>

          <!-- Live Status Hint -->
          <div
            v-if="currentPhase === 1 || isSimulating"
            class="status-overlay-hint"
          >
            <div class="status-icon-box">
              <div class="pulse-dot"></div>
            </div>
            <span class="status-msg">{{
              isSimulating ? "Scenario run active" : "Mapping the sources"
            }}</span>
          </div>

          <!-- Completion Hint -->
          <div
            v-if="showSimulationFinishedHint"
            class="status-overlay-hint completion-hint"
          >
            <div class="status-icon-box">Done</div>
            <span class="status-msg"
              >Scenario run finished. Refresh to see the latest map.</span
            >
            <button
              class="hint-close"
              type="button"
              aria-label="Dismiss scenario-finished message"
              @click="dismissFinishedHint"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Entity Detail Panel (Sidebar within Graph) -->
        <Transition name="panel-slide">
          <div
            v-if="selectedItem"
            ref="detailPanel"
            class="entity-detail-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="graph-detail-title"
            tabindex="-1"
            @keydown="handleDetailKeydown"
          >
            <header class="detail-header">
              <span id="graph-detail-title" class="detail-category">
                {{
                  selectedItem.type === "node"
                    ? `Map item: ${selectedItem.data.name || "Unnamed item"}`
                    : "Source connection"
                }}
              </span>
              <span
                v-if="selectedItem.type === 'node'"
                class="type-badge"
                :style="{ background: selectedItem.color }"
              >
                {{ selectedItem.entityType }}
              </span>
              <button
                ref="detailCloseButton"
                class="close-detail-btn"
                type="button"
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
                  <div class="attr-value title">
                    {{ selectedItem.data.name }}
                  </div>
                </div>
                <div class="attr-row">
                  <label>Item reference</label>
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
                  <h4 class="section-label">Summary</h4>
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
                  {{ selectedItem.data.selfLoopCount }} references
                </div>
                <div v-else class="edge-path-header">
                  {{ selectedItem.data.source_name }} →
                  {{ selectedItem.data.name || "LINKED" }} →
                  {{ selectedItem.data.target_name }}
                </div>

                <div class="attr-row">
                  <label>Relationship Type</label>
                  <div class="attr-value highlight">
                    {{
                      selectedItem.data.fact_type ||
                      selectedItem.data.name ||
                      "General"
                    }}
                  </div>
                </div>

                <div v-if="selectedItem.data.fact" class="attr-section">
                  <h4 class="section-label">
                    Graph record · provenance unverified
                  </h4>
                  <div class="fact-box">{{ selectedItem.data.fact }}</div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <div v-else class="state-placeholder">
        <div class="geometric-shape"></div>
        <strong>{{ emptyStateTitle }}</strong>
        <p>{{ emptyStateMessage }}</p>
        <button class="empty-refresh" type="button" @click="$emit('refresh')">
          Refresh source map
        </button>
      </div>
    </div>

    <!-- UI Overlays -->
    <footer
      class="graph-ui-overlays"
      :aria-hidden="selectedItem ? 'true' : undefined"
      :inert="selectedItem ? '' : undefined"
    >
      <!-- Legend -->
      <div
        v-if="hasGraphNodes && entityTypes.length"
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
      <div v-if="hasGraphNodes" class="view-controls">
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
    0: "Reading the sources",
    1: "Connecting the source material",
    2: "Source map ready",
  };
  return labels[props.currentPhase] || "Source map";
});

const emit = defineEmits(["refresh", "toggle-maximize"]);

// Refs & State
const graphContainer = ref(null);
const graphSvg = ref(null);
const detailPanel = ref(null);
const detailCloseButton = ref(null);
const selectedItem = ref(null);
const showEdgeLabels = ref(true);
const showSimulationFinishedHint = ref(false);
const wasSimulating = ref(false);
const searchQuery = ref("");
let currentSimulation = null;
let gSelection = null;
let lastGraphTrigger = null;
let lastGraphTriggerId = null;
let graphResizeObserver = null;
let graphResizeTimer = null;

const hasGraphNodes = computed(
  () =>
    Array.isArray(props.graphData?.nodes) && props.graphData.nodes.length > 0,
);

const emptyStateTitle = computed(() =>
  props.graphData
    ? "No source-map items were found."
    : "The source map is not available yet.",
);

const emptyStateMessage = computed(() =>
  props.graphData
    ? "Review the source material, then rebuild or refresh the map."
    : "Open source material first, then refresh when mapping is complete.",
);

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
  // Keep generated entity groups inside the approved editorial palette.
  const palette = [
    "#f04b3d",
    "#f2ebdd",
    "#ffd51d",
    "#f7b6ab",
    "#c7c0b3",
    "#646761",
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

const getDetailFocusableElements = () =>
  Array.from(
    detailPanel.value?.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) || [],
  ).filter(
    (element) =>
      !element.hidden && element.getAttribute("aria-hidden") !== "true",
  );

const openNodeDetail = (event, node) => {
  event?.stopPropagation();
  lastGraphTrigger = event?.currentTarget || null;
  lastGraphTriggerId = node.id;
  selectedItem.value = {
    type: "node",
    data: node.raw,
    entityType: node.type,
    color: entityTypes.value.find((type) => type.name === node.type)?.color,
  };
  nextTick(() => {
    (detailCloseButton.value || detailPanel.value)?.focus();
  });
};

const closeDetailPanel = () => {
  const trigger = lastGraphTrigger;
  const triggerId = lastGraphTriggerId;
  selectedItem.value = null;
  nextTick(() => {
    const replacementTrigger = Array.from(
      graphSvg.value?.querySelectorAll(".graph-node") || [],
    ).find((element) => element.getAttribute("data-node-id") === triggerId);
    const focusTarget = trigger?.isConnected ? trigger : replacementTrigger;
    focusTarget?.focus();
    lastGraphTrigger = null;
    lastGraphTriggerId = null;
  });
};

const handleDetailKeydown = (event) => {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    closeDetailPanel();
    return;
  }

  if (event.key !== "Tab") return;
  const focusable = getDetailFocusableElements();
  if (focusable.length === 0) {
    event.preventDefault();
    detailPanel.value?.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (event.shiftKey && (active === first || !detailPanel.value?.contains(active))) {
    event.preventDefault();
    last.focus();
  } else if (
    !event.shiftKey &&
    (active === last || !detailPanel.value?.contains(active))
  ) {
    event.preventDefault();
    first.focus();
  }
};

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
    .attr("stroke", "rgba(188, 184, 173, 0.58)")
    .attr("stroke-width", 1.5);

  const nodeDots = g
    .append("g")
    .selectAll("circle")
    .data(nodes)
    .enter()
    .append("circle")
    .attr("class", "graph-node")
    .attr("data-node-id", (d) => d.id)
    .attr("role", "button")
    .attr("tabindex", 0)
    .attr("focusable", "true")
    .attr(
      "aria-label",
      (d) =>
        `${d.name || "Unnamed source-map item"}, ${d.type}. Open details.`,
    )
    .attr("r", 12)
    .attr(
      "fill",
      (d) => entityTypes.value.find((t) => t.name === d.type)?.color || "#bcb8ad",
    )
    .attr("stroke", "#111513")
    .attr("stroke-width", 2)
    .style("cursor", "pointer")
    .on("click", openNodeDetail)
    .on("keydown", (event, d) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      openNodeDetail(event, d);
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
    .attr("font-size", width < 520 ? "12px" : "13px")
    .attr("font-weight", "700")
    .attr("fill", "#f1eee6")
    .attr("dy", 4)
    .attr("aria-hidden", "true")
    .style("pointer-events", "none");

  simulation.on("tick", () => {
    links
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);
    nodeDots.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
    labels
      .attr("x", (d) => d.x)
      .attr("y", (d) => d.y)
      .attr("dx", (d) => (d.x > width * 0.62 ? -16 : 16))
      .attr("text-anchor", (d) => (d.x > width * 0.62 ? "end" : "start"));
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
  [() => props.graphData, () => props.loading],
  () => nextTick(render),
  { deep: true },
);
onMounted(() => {
  nextTick(render);
  window.addEventListener("resize", render);
  if (typeof ResizeObserver !== "undefined" && graphContainer.value) {
    graphResizeObserver = new ResizeObserver(() => {
      if (!hasGraphNodes.value || props.loading) return;
      window.clearTimeout(graphResizeTimer);
      graphResizeTimer = window.setTimeout(render, 80);
    });
    graphResizeObserver.observe(graphContainer.value);
  }
});
onUnmounted(() => {
  window.removeEventListener("resize", render);
  graphResizeObserver?.disconnect();
  graphResizeObserver = null;
  window.clearTimeout(graphResizeTimer);
  graphResizeTimer = null;
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
  backdrop-filter: none;
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

.graph-background-layer {
  width: 100%;
  height: 100%;
}

.graph-svg-element {
  width: 100%;
  height: 100%;
  display: block;
}

:deep(.graph-node:focus-visible) {
  outline: 3px solid var(--attention);
  outline-offset: 4px;
  stroke: var(--attention) !important;
  stroke-width: 6px;
  stroke-dasharray: 2 2;
}

.status-overlay-hint {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--signal-tint);
  backdrop-filter: none;
  border: 1px solid var(--accent-color);
  padding: 6px 12px;
  border-radius: 20px;
  z-index: 10;
  box-shadow: none;
}
.completion-hint {
  background: var(--attention-tint);
  border-color: var(--attention);
  box-shadow: none;
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
  color: var(--attention);
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
  0%, 100% { transform: scale(0.95); }
  50% { transform: scale(1); }
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
  backdrop-filter: none;
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
  color: var(--paper);
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
  backdrop-filter: none;
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
  backdrop-filter: none;
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
  background: rgba(242, 235, 221, 0.05);
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
  background: var(--signal-tint);
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
  background-color: rgba(242, 235, 221, 0.2);
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
  gap: 0.75rem;
  padding: 1.5rem;
  color: var(--text-secondary);
  text-align: center;
}

.state-placeholder strong {
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.state-placeholder p {
  max-width: 34rem;
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.8rem;
  line-height: 1.5;
}

.map-loading-lines {
  display: grid;
  gap: 0.45rem;
  width: min(100%, 18rem);
}

.map-loading-lines span {
  height: 0.38rem;
  border: 1px solid var(--line-dark);
  background: var(--signal);
  transform: scaleX(0.35);
  transform-origin: left;
  animation: map-line-read 1.2s var(--ease-out) infinite alternate;
}

.map-loading-lines span:nth-child(2) {
  animation-delay: 140ms;
}

.map-loading-lines span:nth-child(3) {
  animation-delay: 280ms;
}

.empty-refresh {
  min-height: 2.75rem;
  margin-top: 0.35rem;
  border-color: var(--signal);
  border-radius: var(--radius-md);
  background: var(--signal);
  color: var(--paper);
  font-family: var(--font-display);
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.geometric-shape {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  transform: rotate(45deg);
}

@keyframes map-line-read {
  to {
    transform: scaleX(1);
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

.maximize-icon {
  width: 1rem;
  height: 1rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
}

/* Public Signal map geometry */
.graph-panel-workbench {
  border: 0;
  border-radius: var(--radius-md);
  background: var(--ink-deep);
}

.panel-header-block {
  min-height: 3.1rem;
  border-color: var(--line-dark);
  background: var(--ink-deep);
  backdrop-filter: none;
}

.panel-label {
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.btn-action {
  border-radius: var(--radius-md);
  background: var(--ink-raised);
  box-shadow: none;
}

.btn-action:hover {
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.status-overlay-hint,
.completion-hint {
  border: 2px solid var(--signal);
  border-radius: var(--radius-md);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0.35rem 0.35rem 0 rgba(12, 16, 15, 0.55);
  backdrop-filter: none;
}

.status-overlay-hint :is(.status-msg, .status-icon-box) {
  color: var(--ink) !important;
}

.type-legend,
.view-controls,
.entity-detail-panel {
  border-color: var(--line-light);
  border-radius: var(--radius-md);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0.35rem 0.35rem 0 rgba(12, 16, 15, 0.55);
  backdrop-filter: none;
}

.legend-header,
.type-name,
.control-label,
.entity-detail-panel :is(.detail-category, .attr-row label, .attr-value, .section-label) {
  color: var(--ink) !important;
}

.color-swatch {
  border-radius: var(--radius-md);
}

.summary-box {
  border-color: var(--line-light);
  border-radius: var(--radius-md);
  background: var(--paper-transfer);
  color: var(--ink);
}

.type-badge {
  border-radius: var(--radius-md);
  color: var(--paper);
}

@media (max-width: 900px) {
  .graph-panel-workbench {
    min-height: 28rem;
  }
}

@media (max-width: 560px) {
  .panel-header-block {
    padding: 0 0.7rem;
  }

  .graph-ui-overlays {
    right: 0.55rem;
    bottom: 0.55rem;
    left: 0.55rem;
    padding: 0;
  }

  .type-legend {
    max-width: 9rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .map-loading-lines span,
  .pulse-dot,
  .is-spinning {
    animation: none;
    transform: none;
  }
}
</style>

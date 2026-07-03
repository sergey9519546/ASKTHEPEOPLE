<template>
  <div class="opinion-map-container bauhaus-card">
    <div class="map-header">
      <div class="title-group">
        <h3 class="map-title">3D_OPINION_SPACE</h3>
        <span class="map-subtitle"
          >Polarity (X) | Intensity (Y) | Nuance (Z)</span
        >
      </div>
      <div class="map-controls">
        <button class="control-btn" @click="toggleRotation">
          {{ isRotating ? "PAUSE_ROTATION" : "RESUME_ROTATION" }}
        </button>
        <div class="legend">
          <span class="legend-item"><i class="dot reddit"></i> REDDIT</span>
          <span class="legend-item"><i class="dot twitter"></i> TWITTER</span>
        </div>
      </div>
    </div>

    <!-- 3D Viewport -->
    <div
      class="map-viewport"
      @mousedown="startDrag"
      @mousemove="onDrag"
      @mouseup="stopDrag"
    >
      <div class="scene" :style="sceneStyle">
        <!-- 3D Cage -->
        <div class="cube-cage">
          <!-- Back Face -->
          <div class="face back"></div>
          <!-- Bottom Face -->
          <div class="face bottom"></div>
          <!-- Left Face -->
          <div class="face left"></div>

          <!-- Axis Indicators -->
          <div class="axis x-line"><span class="label">STANCE</span></div>
          <div class="axis y-line"><span class="label">INTENSITY</span></div>
          <div class="axis z-line"><span class="label">NUANCE</span></div>

          <!-- Agent Points -->
          <div
            v-for="agent in latestOpinions"
            :key="agent.agent_id"
            class="agent-point"
            :class="[
              agent.platform,
              { 'is-active': activeAgentId === agent.agent_id },
            ]"
            :style="getPointStyle(agent)"
            @mouseenter="activeAgentId = agent.agent_id"
            @mouseleave="activeAgentId = null"
          >
            <!-- 3D Sphere/Cube for Agent -->
            <div class="point-body">
              <div class="depth-shadow"></div>
            </div>

            <!-- Tooltip (Billboarded) -->
            <transition name="fade">
              <div
                v-if="activeAgentId === agent.agent_id"
                class="agent-tooltip"
                :style="tooltipStyle"
              >
                <div class="tooltip-header">
                  <span class="name">@{{ agent.agent_name }}</span>
                  <span class="plat" :class="agent.platform">{{
                    agent.platform.toUpperCase()
                  }}</span>
                </div>
                <div class="coords">
                  X: {{ agent.x.toFixed(2) }} | Y: {{ agent.y.toFixed(2) }} | Z:
                  {{ agent.z.toFixed(2) }}
                </div>
                <p class="reason">{{ agent.reason }}</p>
                <p class="snippet">"{{ agent.text_snippet }}..."</p>
              </div>
            </transition>
          </div>
        </div>
      </div>

      <!-- Interaction Overlay -->
      <div class="interaction-hint">DRAG TO ROTATE SPACE</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { getSimulationOpinions } from "../api/simulation";

const props = defineProps({
  simulationId: String,
});

const opinions = ref([]);
const activeAgentId = ref(null);
const isRotating = ref(true);
const rotation = reactive({ x: -20, y: 45 });
let pollTimer = null;
let animationFrame = null;

// Drag state
const isDragging = ref(false);
const lastMousePos = reactive({ x: 0, y: 0 });

const sceneStyle = computed(() => ({
  transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
}));

// We want the tooltip to always face the user (billboarding)
// We negate the scene rotation
const tooltipStyle = computed(() => ({
  transform: `rotateY(${-rotation.y}deg) rotateX(${-rotation.x}deg)`,
}));

const latestOpinions = computed(() => {
  const map = new Map();
  const sorted = [...opinions.value].sort(
    // Optimization: Compare ISO 8601 strings directly instead of parsing Date objects
    (a, b) => (a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0),
  );
  sorted.forEach((op) => {
    map.set(op.agent_id, op);
  });
  return Array.from(map.values());
});

const getPointStyle = (agent) => {
  // Normalize coordinates to cube pixels (assume 300px cube)
  const size = 300;
  const x = agent.x * (size / 2); // -150 to 150
  const y = (1 - agent.y) * size - size / 2; // inverted Y
  const z = (agent.z - 0.5) * size; // -150 to 150

  return {
    transform: `translate3d(${x}px, ${y}px, ${z}px)`,
  };
};

const fetchOpinions = async () => {
  if (!props.simulationId) return;
  try {
    const res = await getSimulationOpinions(props.simulationId);
    if (res.success && res.data) {
      opinions.value = res.data.opinions || [];
    }
  } catch (e) {
    console.error("3D Space fetch failed", e);
  }
};

const animate = () => {
  if (isRotating.value && !isDragging.value) {
    rotation.y += 0.2;
  }
  animationFrame = requestAnimationFrame(animate);
};

const toggleRotation = () => {
  isRotating.value = !isRotating.value;
};

// Drag handlers
const startDrag = (e) => {
  isDragging.value = true;
  lastMousePos.x = e.clientX;
  lastMousePos.y = e.clientY;
};

const onDrag = (e) => {
  if (!isDragging.value) return;
  const dx = e.clientX - lastMousePos.x;
  const dy = e.clientY - lastMousePos.y;

  rotation.y += dx * 0.5;
  rotation.x -= dy * 0.5;

  lastMousePos.x = e.clientX;
  lastMousePos.y = e.clientY;
};

const stopDrag = () => {
  isDragging.value = false;
};

onMounted(() => {
  fetchOpinions();
  pollTimer = setInterval(fetchOpinions, 5000);
  animate();
  window.addEventListener("mouseup", stopDrag);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  if (animationFrame) cancelAnimationFrame(animationFrame);
  window.removeEventListener("mouseup", stopDrag);
});
</script>

<style scoped>
.opinion-map-container {
  height: 600px;
  display: flex;
  flex-direction: column;
  background: var(--atp-white);
  border: 4px solid var(--atp-black);
  overflow: hidden;
}

.map-header {
  padding: 15px 25px;
  background: #f0f0f0;
  border-bottom: 4px solid var(--atp-black);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.map-title {
  font-weight: 900;
  font-size: 16px;
  margin: 0;
}
.map-subtitle {
  font-size: 10px;
  font-weight: 700;
  opacity: 0.6;
}

.map-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.control-btn {
  background: var(--atp-black);
  color: var(--atp-white);
  border: none;
  padding: 5px 12px;
  font-size: 10px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.1s;
}
.control-btn:active {
  transform: scale(0.95);
}

.legend-item {
  font-size: 10px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  margin-left: 10px;
}
.dot {
  width: 10px;
  height: 10px;
  border: 2px solid var(--atp-black);
  margin-right: 5px;
}
.dot.reddit {
  background: #ff4500;
}
.dot.twitter {
  background: #1da1f2;
}

/* 3D Viewport */
.map-viewport {
  flex: 1;
  perspective: 1000px;
  background: #fafafa;
  position: relative;
  overflow: hidden;
  cursor: grab;
}
.map-viewport:active {
  cursor: grabbing;
}

.scene {
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.1s ease-out;
}

.cube-cage {
  width: 300px;
  height: 300px;
  position: relative;
  transform-style: preserve-3d;
}

.face {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 1px dashed rgba(0, 0, 0, 0.1);
  pointer-events: none;
}

.face.back {
  transform: translateZ(-150px);
  background: rgba(0, 0, 0, 0.02);
}
.face.bottom {
  transform: rotateX(90deg) translateZ(150px);
  background: rgba(0, 0, 0, 0.05);
}
.face.left {
  transform: rotateY(-90deg) translateZ(150px);
  border-right: 2px solid var(--atp-black);
}

/* Axes */
.axis {
  position: absolute;
  background: var(--atp-black);
  pointer-events: none;
  opacity: 0.6;
}
.axis .label {
  position: absolute;
  font-size: 9px;
  font-weight: 900;
  background: var(--atp-white);
  border: 1px solid var(--atp-black);
  padding: 1px 4px;
}

.x-line {
  width: 100%;
  height: 2px;
  top: 100%;
  left: 0;
  transform: translateZ(150px);
}
.x-line .label {
  right: -40px;
}

.y-line {
  width: 2px;
  height: 100%;
  left: 0;
  top: 0;
  transform: translateZ(150px);
}
.y-line .label {
  top: -20px;
  left: -10px;
}

.z-line {
  width: 300px;
  height: 2px;
  left: 0;
  top: 100%;
  transform: rotateY(-90deg) translateZ(0);
}
.z-line .label {
  right: -40px;
}

/* Agent Points */
.agent-point {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 40px;
  height: 40px;
  margin: -20px;
  transform-style: preserve-3d;
  z-index: 10;
}

.point-body {
  width: 12px;
  height: 12px;
  position: absolute;
  top: 14px;
  left: 14px;
  border: 2px solid var(--atp-black);
  box-shadow: 4px 4px 0 var(--atp-black);
  transition: transform 0.3s;
}

.reddit .point-body {
  background: #ff4500;
}
.twitter .point-body {
  background: #1da1f2;
}

.agent-point.is-active .point-body {
  transform: scale(1.5);
  box-shadow: 6px 6px 0 var(--atp-black);
}

.depth-shadow {
  position: absolute;
  bottom: -300px; /* Projection to floor */
  left: 50%;
  width: 8px;
  height: 8px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  transform: rotateX(90deg) translateZ(0);
}

/* Tooltip */
.agent-tooltip {
  position: absolute;
  bottom: 40px;
  left: 50%;
  width: 240px;
  margin-left: -120px;
  background: var(--atp-white);
  border: 3px solid var(--atp-black);
  padding: 12px;
  box-shadow: 8px 8px 0 var(--atp-black);
  pointer-events: none;
  z-index: 200;
  backface-visibility: hidden;
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid var(--atp-black);
  padding-bottom: 5px;
  margin-bottom: 8px;
}
.name {
  font-weight: 900;
  font-size: 13px;
}
.plat {
  font-size: 9px;
  font-weight: 800;
  padding: 1px 4px;
  border: 1px solid var(--atp-black);
}
.coords {
  font-size: 10px;
  font-weight: 800;
  color: var(--atp-accent-cyan);
  margin-bottom: 6px;
}
.reason {
  font-size: 11px;
  font-weight: 700;
  margin: 0 0 8px 0;
}
.snippet {
  font-size: 10px;
  font-style: italic;
  opacity: 0.7;
  border-left: 3px solid #eee;
  padding-left: 8px;
  margin: 0;
}

.interaction-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 900;
  background: var(--atp-black);
  color: var(--atp-white);
  padding: 4px 12px;
  letter-spacing: 2px;
  pointer-events: none;
}

/* Animations */
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.2s,
    transform 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.9);
}
</style>

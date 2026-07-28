<template>
  <div class="opinion-map-container">
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
  const sorted = [...opinions.value].sort((a, b) =>
    String(a.timestamp || '').localeCompare(String(b.timestamp || '')),
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
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.04), 0 1px 3px -1px rgba(15, 23, 42, 0.02);
  overflow: hidden;
}

.map-header {
  padding: 18px 24px;
  background: var(--atp-light-gray);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.map-title {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: 0.5px;
}

.map-subtitle {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  opacity: 0.8;
  margin-top: 2px;
}

.map-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.control-btn {
  background: var(--surface-color);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 6px 14px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
  transition: all 0.2s ease;
}

.control-btn:hover {
  background: var(--atp-light-gray);
  border-color: #cbd5e1;
}

.control-btn:active {
  transform: translateY(0);
}

.legend-item {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  margin-left: 12px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
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
  background: var(--background);
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
  border: 1px dashed rgba(148, 163, 184, 0.15);
  pointer-events: none;
}

.face.back {
  transform: translateZ(-150px);
  background: rgba(148, 163, 184, 0.02);
}

.face.bottom {
  transform: rotateX(90deg) translateZ(150px);
  background: rgba(148, 163, 184, 0.04);
}

.face.left {
  transform: rotateY(-90deg) translateZ(150px);
  border-right: 1px solid var(--border-color);
}

/* Axes */
.axis {
  position: absolute;
  background: #cbd5e1;
  pointer-events: none;
}

.axis .label {
  position: absolute;
  font-size: 8px;
  font-weight: 600;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 2px 6px;
  color: var(--text-secondary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.x-line {
  width: 100%;
  height: 1px;
  top: 100%;
  left: 0;
  transform: translateZ(150px);
}

.x-line .label {
  right: -45px;
  top: -8px;
}

.y-line {
  width: 1px;
  height: 100%;
  left: 0;
  top: 0;
  transform: translateZ(150px);
}

.y-line .label {
  top: -24px;
  left: -20px;
}

.z-line {
  width: 300px;
  height: 1px;
  left: 0;
  top: 100%;
  transform: rotateY(-90deg) translateZ(0);
}

.z-line .label {
  right: -45px;
  top: -8px;
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
  width: 10px;
  height: 10px;
  position: absolute;
  top: 15px;
  left: 15px;
  border-radius: 50%;
  border: 1px solid var(--surface-color);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.reddit .point-body {
  background: #ff4500;
}

.twitter .point-body {
  background: #1da1f2;
}

.agent-point.is-active .point-body {
  transform: scale(1.6);
  border-color: var(--surface-color);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.15), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.depth-shadow {
  position: absolute;
  bottom: -300px; /* Projection to floor */
  left: 50%;
  width: 6px;
  height: 6px;
  background: rgba(0, 0, 0, 0.05);
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
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
  pointer-events: none;
  z-index: 200;
  backface-visibility: hidden;
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 6px;
  margin-bottom: 10px;
}

.name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
}

.plat {
  font-size: 9px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 12px;
}

.plat.reddit {
  background: rgba(255, 69, 0, 0.1);
  color: #ff4500;
}

.plat.twitter {
  background: rgba(29, 161, 242, 0.1);
  color: #1da1f2;
}

.coords {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-secondary);
  opacity: 0.8;
  margin-bottom: 8px;
}

.reason {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.snippet {
  font-size: 10px;
  font-style: italic;
  color: var(--text-secondary);
  border-left: 2px solid var(--border-color);
  padding-left: 8px;
  margin: 0;
  line-height: 1.4;
}

.interaction-hint {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 9px;
  font-weight: 500;
  background: var(--text-primary);
  color: var(--surface-color);
  border-radius: 20px;
  padding: 4px 12px;
  letter-spacing: 1px;
  pointer-events: none;
  opacity: 0.8;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
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
  transform: translateY(10px) scale(0.95);
}
</style>

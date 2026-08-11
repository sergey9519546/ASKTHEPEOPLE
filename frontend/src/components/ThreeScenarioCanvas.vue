<template>
  <div class="three-scenario-wrapper" aria-hidden="true">
    <canvas ref="canvasRef" class="three-scenario-canvas"></canvas>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import * as THREE from "three";

const canvasRef = ref(null);

let scene, camera, renderer, animationFrameId;
let particlesMesh, linesMesh;
let mouseX = 0;
let mouseY = 0;
let targetMouseX = 0;
let targetMouseY = 0;
let isDisposed = false;

const NODE_COUNT = 65;

const onMouseMove = (event) => {
  targetMouseX = (event.clientX / window.innerWidth - 0.5) * 2;
  targetMouseY = (event.clientY / window.innerHeight - 0.5) * 2;
};

const initThree = () => {
  if (!canvasRef.value) return;

  const width = window.innerWidth;
  const height = window.innerHeight;

  // 1. Scene
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x060b14, 0.035);

  // 2. Camera
  camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
  camera.position.set(0, 0, 15);

  // 3. Renderer
  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    alpha: true,
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  // 4. Create Node Points Geometry
  const positions = new Float32Array(NODE_COUNT * 3);
  const colors = new Float32Array(NODE_COUNT * 3);

  const baseColor = new THREE.Color(0x38bdf8); // Signal cyan
  const altColor = new THREE.Color(0x818cf8);  // Indigo accent

  for (let i = 0; i < NODE_COUNT; i++) {
    const i3 = i * 3;
    positions[i3] = (Math.random() - 0.5) * 22;
    positions[i3 + 1] = (Math.random() - 0.5) * 14;
    positions[i3 + 2] = (Math.random() - 0.5) * 10;

    const mixedColor = baseColor.clone().lerp(altColor, Math.random());
    colors[i3] = mixedColor.r;
    colors[i3 + 1] = mixedColor.g;
    colors[i3 + 2] = mixedColor.b;
  }

  const particleGeo = new THREE.BufferGeometry();
  particleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  particleGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  // Particle Material
  const particleMat = new THREE.PointsMaterial({
    size: 0.28,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
  });

  particlesMesh = new THREE.Points(particleGeo, particleMat);
  scene.add(particlesMesh);

  // 5. Create Connecting Network Lines
  const linePositions = [];
  const lineColors = [];

  for (let i = 0; i < NODE_COUNT; i++) {
    for (let j = i + 1; j < NODE_COUNT; j++) {
      const dx = positions[i * 3] - positions[j * 3];
      const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
      const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

      if (dist < 5.5) {
        linePositions.push(
          positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
          positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
        );
        const alpha = 1 - dist / 5.5;
        lineColors.push(
          0.2, 0.4, 0.7,
          0.2, 0.4, 0.7
        );
      }
    }
  }

  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3));
  
  const lineMat = new THREE.LineBasicMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.22,
    blending: THREE.AdditiveBlending,
  });

  linesMesh = new THREE.LineSegments(lineGeo, lineMat);
  scene.add(linesMesh);

  // Check reduced motion
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 6. Animation Loop
  const clock = new THREE.Clock();
  const animate = () => {
    if (isDisposed) return;

    animationFrameId = requestAnimationFrame(animate);

    const elapsedTime = clock.getElapsedTime();

    if (!prefersReducedMotion) {
      // Smooth mouse parallax interpolation
      mouseX += (targetMouseX - mouseX) * 0.05;
      mouseY += (targetMouseY - mouseY) * 0.05;

      camera.position.x = mouseX * 1.5;
      camera.position.y = -mouseY * 1.5;
      camera.lookAt(0, 0, 0);

      // Slow organic rotation of nodes & lines
      if (particlesMesh) {
        particlesMesh.rotation.y = elapsedTime * 0.04;
        particlesMesh.rotation.x = Math.sin(elapsedTime * 0.02) * 0.1;
      }
      if (linesMesh) {
        linesMesh.rotation.y = elapsedTime * 0.04;
        linesMesh.rotation.x = Math.sin(elapsedTime * 0.02) * 0.1;
      }
    }

    renderer.render(scene, camera);
  };

  animate();
};

const onResize = () => {
  if (!renderer || !camera || isDisposed) return;
  const width = window.innerWidth;
  const height = window.innerHeight;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
};

onMounted(() => {
  initThree();
  window.addEventListener("resize", onResize);
  window.addEventListener("mousemove", onMouseMove, { passive: true });
});

onBeforeUnmount(() => {
  isDisposed = true;
  if (animationFrameId) cancelAnimationFrame(animationFrameId);

  window.removeEventListener("resize", onResize);
  window.removeEventListener("mousemove", onMouseMove);

  // GPU disposal per threejs-scene-setup skill
  if (scene) {
    scene.traverse((object) => {
      if (object.geometry) object.geometry.dispose();
      if (object.material) {
        if (Array.isArray(object.material)) {
          object.material.forEach((m) => m.dispose());
        } else {
          object.material.dispose();
        }
      }
    });
  }
  if (renderer) renderer.dispose();
});
</script>

<style scoped>
.three-scenario-wrapper {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.three-scenario-canvas {
  width: 100%;
  height: 100%;
  display: block;
}
</style>

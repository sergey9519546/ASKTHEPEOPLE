<template>
  <div class="home-container">
    <!-- Bauhaus Grid Background -->
    <div class="bau-grid"></div>
    
    <!-- Navbar -->
    <nav class="navbar">
      <div class="nav-brand">Miro<span>Fish</span></div>
      <div class="nav-links">
        <a href="https://github.com/sergey9519546/ASKTHEPEOPLE" target="_blank" class="github-link">
          GITHUB <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- Hero Section: Bauhaus Geometry -->
      <section class="hero-section">
        <div class="hero-left bau-block">
          <div class="tag-row">
            <span class="bau-tag red">CROWD INTELLIGENCE</span>
            <span class="version-text">V0.1-PREVIEW</span>
          </div>
          
          <h1 class="main-title">
            REALIZE THE<br>
            <span class="highlight-blue">FUTURE</span>
          </h1>
          
          <div class="hero-desc">
            <p>
              MiroFish extracts reality seeds from your data and simulates millions of agents in a parallel world.
            </p>
            <div class="slogan-block yellow">
              FUNCTION FOLLOWS SIMULATION
            </div>
          </div>
        </div>
        
        <div class="hero-right">
          <!-- MF Geometric Logo -->
          <div class="bau-logo-mark">
            <div class="shape-m">
              <div class="bar red"></div>
              <div class="bar blue"></div>
              <div class="bar yellow"></div>
            </div>
            <div class="mf-text">MF</div>
          </div>
        </div>
      </section>

      <!-- Dashboard Grid -->
      <section class="dashboard-grid">
        <!-- Status Panel -->
        <div class="status-panel bau-block">
          <div class="panel-header">
            <span class="status-indicator">■</span> SYSTEM STATUS
          </div>
          <h2 class="section-title">ENGINE STANDBY</h2>
          <div class="metrics-grid">
            <div class="metric-box">
              <div class="label">COST</div>
              <div class="value">~$5</div>
            </div>
            <div class="metric-box">
              <div class="label">SCALE</div>
              <div class="value">1M+</div>
            </div>
          </div>
          
          <div class="workflow-grid">
            <div v-for="(step, i) in steps" :key="i" class="workflow-step">
              <span class="step-idx">{{ (i+1).toString().padStart(2, '0') }}</span>
              <div class="step-body">
                <div class="step-name">{{ step.item }}</div>
                <div class="step-desc">{{ step.desc }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Console -->
        <div class="console-panel bau-block">
          <!-- Step 1: Upload -->
          <div class="console-step">
            <div class="console-label">01 / UPLOAD DATA</div>
            <div 
              class="upload-area"
              :class="{ 'drag-over': isDragOver }"
              @dragover.prevent="handleDragOver"
              @dragleave.prevent="handleDragLeave"
              @drop.prevent="handleDrop"
              @click="triggerFileInput"
            >
              <input
                ref="fileInput"
                type="file"
                multiple
                accept=".pdf,.md,.txt"
                @change="handleFileSelect"
                style="display: none"
              />
              
              <div v-if="files.length === 0" class="placeholder">
                <span class="plus">+</span>
                <div>DROP REALITY SEEDS</div>
              </div>
              
              <div v-else class="file-list">
                <div v-for="(file, index) in files" :key="index" class="file-card">
                  <span class="name">{{ file.name }}</span>
                  <button @click.stop="removeFile(index)" class="delete">×</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 2: Prompt -->
          <div class="console-step">
            <div class="console-label">02 / INSTRUCTION</div>
            <textarea
              v-model="formData.simulationRequirement"
              class="bau-textarea"
              placeholder="DEFINE THE FUTURE..."
              rows="5"
            ></textarea>
            <div class="engine-id">ENGINE: MIROFISH-V1.0</div>
          </div>

          <!-- Action -->
          <div class="action-footer">
            <button 
              class="bau-btn-large"
              @click="startSimulation"
              :disabled="!canSubmit || loading"
            >
              INITIALIZE <span class="arrow">→</span>
            </button>
          </div>
        </div>
      </section>

      <!-- History -->
      <HistoryDatabase class="history-section" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const router = useRouter()
const formData = ref({ simulationRequirement: '' })
const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

const steps = [
  { item: 'GRAPH BUILD', desc: 'Extract reality seeds & GraphRAG' },
  { item: 'ENV SETUP', desc: 'Entity relation & Agent injection' },
  { item: 'RUNTIME', desc: 'Parallel simulation & memory' },
  { item: 'REPORTING', desc: 'Recursive agent interaction' },
  { item: 'INTERACTION', desc: 'Direct dialogue with agents' }
]

const canSubmit = computed(() => formData.value.simulationRequirement.trim() !== '' && files.value.length > 0)

const triggerFileInput = () => fileInput.value?.click()
const handleFileSelect = (e) => addFiles(Array.from(e.target.files))
const handleDragOver = () => isDragOver.value = true
const handleDragLeave = () => isDragOver.value = false
const handleDrop = (e) => {
  isDragOver.value = false
  addFiles(Array.from(e.dataTransfer.files))
}

const addFiles = (newFiles) => {
  const valid = newFiles.filter(f => ['pdf', 'md', 'txt'].includes(f.name.split('.').pop().toLowerCase()))
  files.value.push(...valid)
}

const removeFile = (i) => files.value.splice(i, 1)

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement)
    router.push({ name: 'Process', params: { projectId: 'new' } })
  })
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background-color: var(--bau-bg);
  color: var(--bau-black);
  font-family: var(--font-sans);
  position: relative;
  overflow-x: hidden;
}

/* Bauhaus Grid */
.bau-grid {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.05) 1px, transparent 1px);
  background-size: 100px 100px;
  pointer-events: none;
  z-index: 0;
}

.main-content {
  position: relative;
  z-index: 10;
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Navbar */
.navbar {
  height: 80px;
  border-bottom: 2px solid var(--bau-black);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  background: #FFF;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-family: var(--font-mono);
  font-weight: 900;
  font-size: 1.5rem;
  letter-spacing: -1px;
  text-transform: uppercase;
}

.nav-brand span {
  color: var(--bau-red);
}

.github-link {
  font-family: var(--font-mono);
  font-weight: 700;
  text-decoration: none;
  color: var(--bau-black);
  border: 2px solid var(--bau-black);
  padding: 8px 16px;
  transition: all 0.2s;
}

.github-link:hover {
  background: var(--bau-black);
  color: #FFF;
}

/* Hero */
.hero-section {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 40px;
  margin-bottom: 80px;
  align-items: center;
}

.bau-block {
  background: #FFF;
  border: 2px solid var(--bau-black);
  padding: 40px;
  position: relative;
}

.tag-row {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  align-items: center;
}

.bau-tag {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 0.75rem;
  padding: 4px 12px;
  color: #FFF;
}

.bau-tag.red { background: var(--bau-red); }

.version-text {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.75rem;
  opacity: 0.5;
}

.main-title {
  font-size: 6rem;
  line-height: 0.9;
  font-weight: 900;
  margin-bottom: 32px;
  letter-spacing: -4px;
}

.highlight-blue {
  color: var(--bau-blue);
  background: var(--bau-yellow);
  padding: 0 10px;
}

.hero-desc {
  font-size: 1.25rem;
  line-height: 1.5;
  max-width: 500px;
}

.slogan-block {
  margin-top: 32px;
  padding: 16px;
  border: 2px solid var(--bau-black);
  font-weight: 900;
  font-family: var(--font-mono);
  transform: rotate(-2deg);
  display: inline-block;
}

.slogan-block.yellow { background: var(--bau-yellow); }

/* MF Geometric Logo */
.hero-right {
  display: flex;
  justify-content: center;
}

.bau-logo-mark {
  position: relative;
  width: 300px;
  height: 300px;
}

.shape-m {
  display: flex;
  gap: 20px;
  height: 200px;
}

.bar {
  width: 40px;
  height: 100%;
}

.bar.red { background: var(--bau-red); }
.bar.blue { background: var(--bau-blue); transform: translateY(20px); }
.bar.yellow { background: var(--bau-yellow); transform: translateY(-10px); }

.mf-text {
  position: absolute;
  bottom: 0;
  right: 20px;
  font-size: 8rem;
  font-weight: 950;
  line-height: 1;
  letter-spacing: -10px;
  color: var(--bau-black);
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  margin-bottom: 60px;
}

.panel-header {
  font-family: var(--font-mono);
  font-weight: 800;
  margin-bottom: 24px;
}

.status-indicator {
  color: var(--bau-red);
}

.section-title {
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: 32px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 40px;
}

.metric-box {
  border: 2px solid var(--bau-black);
  padding: 16px;
}

.metric-box .label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  opacity: 0.5;
}

.metric-box .value {
  font-size: 1.5rem;
  font-weight: 900;
}

.workflow-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-step {
  display: flex;
  gap: 20px;
}

.step-idx {
  font-family: var(--font-mono);
  font-weight: 800;
  color: var(--bau-red);
}

.step-name {
  font-weight: 800;
  font-size: 1rem;
}

.step-desc {
  font-size: 0.85rem;
  opacity: 0.6;
}

/* Console */
.console-panel {
  display: flex;
  flex-direction: column;
}

.console-step {
  margin-bottom: 32px;
}

.console-label {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 0.85rem;
  margin-bottom: 12px;
}

.upload-area {
  height: 200px;
  border: 2px dashed var(--bau-black);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--bau-bg);
}

.upload-area.drag-over {
  background: var(--bau-yellow);
}

.upload-area .placeholder {
  text-align: center;
  font-weight: 900;
  font-family: var(--font-mono);
}

.file-list {
  padding: 16px;
  width: 100%;
}

.file-card {
  background: #FFF;
  border: 2px solid var(--bau-black);
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.file-card .name { font-family: var(--font-mono); font-size: 0.85rem; }

.bau-textarea {
  width: 100%;
  border: 2px solid var(--bau-black);
  padding: 16px;
  font-family: var(--font-mono);
  background: #FFF;
  outline: none;
}

.engine-id {
  margin-top: 8px;
  text-align: right;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
}

.action-footer {
  margin-top: auto;
}

.bau-btn-large {
  width: 100%;
  height: 60px;
  background: var(--bau-black);
  color: #FFF;
  font-size: 1.25rem;
}

.bau-btn-large:hover {
  background: var(--bau-red);
  box-shadow: 6px 6px 0 var(--bau-black);
}

.history-section {
  margin-top: 40px;
  border: 2px solid var(--bau-black);
  background: #FFF;
  padding: 40px;
}
</style>

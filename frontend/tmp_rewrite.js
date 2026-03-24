const fs = require("fs");
const path = require("path");

const targetFile = path.resolve("frontend/src/views/Home.vue");
let content = fs.readFileSync(targetFile, "utf-8");

// The new premium glassmorphism template and styles
const newContent = `<template>
  <div class="home-container">
    <!-- Glowing background orbs -->
    <div class="ambient-glow glow-1"></div>
    <div class="ambient-glow glow-2"></div>
    
    <!-- Navbar -->
    <nav class="navbar glass-panel">
      <div class="nav-brand">ASK<span class="highlight-orange">THE</span>PEOPLE</div>
      <div class="nav-links">
        <a href="https://github.com/sergey9519546/ASKTHEPEOPLE" target="_blank" class="github-link">
          Visit our GitHub <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- Hero Section -->
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="orange-tag glass-badge">Crowd Intelligence Engine</span>
            <span class="version-text">/ v0.1-preview</span>
          </div>
          
          <h1 class="main-title">
            Upload Any Report<br>
            <span class="gradient-text">Predict What Happens Next</span>
          </h1>
          
          <div class="hero-desc">
            <p>
              Even from a single document, <span class="highlight-bold">ASKTHEPEOPLE</span> extracts reality seeds and auto-generates up to <span class="highlight-orange">millions of Agents</span> in a parallel world. Inject variables from a god's-eye view and find the <span class="highlight-code">"local optimum"</span> within complex crowd dynamics.
            </p>
            <p class="slogan-text">
              Let the future rehearse among Agents, let decisions win after a hundred battles<span class="blinking-cursor">_</span>
            </p>
          </div>
           
          <div class="decoration-square"></div>
        </div>
        
        <div class="hero-right">
          <!-- Logo Area -->
          <div class="logo-container">
            <div class="atp-logo-mark glow-text">ATP</div>
          </div>
          
          <button class="scroll-down-btn" @click="scrollToBottom">
            ↓
          </button>
        </div>
      </section>

      <!-- Dashboard Layout -->
      <section class="dashboard-section">
        <!-- Left Panel: Status & Steps -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot pulsing">■</span> SYSTEM STATUS
          </div>
          
          <h2 class="section-title">Ready for Simulation</h2>
          <p class="section-desc">
            Simulation engine standing by — upload unstructured documents to initialize a sequence
          </p>
          
          <!-- Metric Cards -->
          <div class="metrics-row">
            <div class="metric-card glass-panel">
              <div class="metric-value gradient-text">Low Cost</div>
              <div class="metric-label">~ $5 / simulation</div>
            </div>
            <div class="metric-card glass-panel">
              <div class="metric-value gradient-text">High Scale</div>
              <div class="metric-label">Up to millions of Agents</div>
            </div>
          </div>

          <!-- Workflow Steps -->
          <div class="steps-container glass-panel">
            <div class="steps-header">
               <span class="diamond-icon text-accent">◇</span> Workflow Sequence
            </div>
            <div class="workflow-list">
              <div class="workflow-item">
                <span class="step-num text-accent">01</span>
                <div class="step-info">
                  <div class="step-title">Graph Build</div>
                  <div class="step-desc">Extract reality seeds & GraphRAG construction</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num text-accent">02</span>
                <div class="step-info">
                  <div class="step-title">Environment Setup</div>
                  <div class="step-desc">Entity relation extraction & Agent parameter injection</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num text-accent">03</span>
                <div class="step-info">
                  <div class="step-title">Simulation Runtime</div>
                  <div class="step-desc">Parallel simulation & dynamic temporal memory updates</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num text-accent">04</span>
                <div class="step-info">
                  <div class="step-title">Report Generation</div>
                  <div class="step-desc">ReportAgent interacts recursively with the simulation</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num text-accent">05</span>
                <div class="step-info">
                  <div class="step-title">Deep Interaction</div>
                  <div class="step-desc">Chat with any Agent in the simulated world</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Panel: Interactive Console -->
        <div class="right-panel">
          <div class="console-box glass-panel">
            <!-- Upload Zone -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label text-accent">01 / Reality Seeds</span>
                <span class="console-meta">Supported: PDF, MD, TXT</span>
              </div>
              
              <div 
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
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
                  :disabled="loading"
                />
                
                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon-wrapper">
                    <span class="upload-icon bounce">↑</span>
                  </div>
                  <div class="upload-title">Drag & Drop Files Here</div>
                  <div class="upload-hint">or click to browse local files</div>
                </div>
                
                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item glass-panel">
                    <span class="file-icon">📄</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Divider -->
            <div class="console-divider">
              <div class="divider-line"></div>
              <span>PARAMETERS</span>
              <div class="divider-line"></div>
            </div>

            <!-- Prompt Input -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label text-accent">>_ 02 / Simulation Prompt</span>
              </div>
              <div class="input-wrapper focus-glow">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  placeholder="// Enter prediction requirements in natural language..."
                  rows="6"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">Engine: ASKTHEPEOPLE-V1.0</div>
              </div>
            </div>

            <!-- Start Button -->
            <div class="console-section btn-section">
              <button 
                class="start-engine-btn action-glow"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <span class="btn-text" v-if="!loading">INITIALIZE ENGINE</span>
                <span class="btn-text" v-else>INITIALIZING...</span>
                <span class="btn-arrow">→</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- History Database Component -->
      <HistoryDatabase class="mt-xl" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const router = useRouter()

const formData = ref({
  simulationRequirement: ''
})

const files = ref([])
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

const handleDragOver = (e) => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (e) => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  })
}

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement)
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
/* Glassmorphism & Dark Theme Overrides */

.home-container {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

/* Ambient Glowing Orbs */
.ambient-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  z-index: 0;
  opacity: 0.6;
  pointer-events: none;
}
.glow-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(255, 69, 0, 0.15) 0%, rgba(0,0,0,0) 70%);
  top: -200px;
  left: -200px;
}
.glow-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(255, 69, 0, 0.1) 0%, rgba(0,0,0,0) 70%);
  bottom: 0;
  right: -100px;
}

/* Glass Panels */
.glass-panel {
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
}

.text-accent {
  color: var(--accent-color);
}

/* Navbar */
.navbar {
  height: 70px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  position: sticky;
  top: 0;
  z-index: 100;
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
}

.nav-brand {
  font-family: var(--font-mono);
  font-weight: 800;
  letter-spacing: 2px;
  font-size: 1.3rem;
  color: var(--text-primary);
}

.highlight-orange {
  color: var(--accent-color);
}

.github-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.github-link:hover {
  color: var(--text-primary);
  text-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
}

/* Main Layout */
.main-content {
  position: relative;
  z-index: 10;
  max-width: 1400px;
  margin: 0 auto;
  padding: 80px 40px;
}

/* Hero Section */
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 100px;
  align-items: center;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 30px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.orange-tag {
  color: var(--accent-color);
  padding: 6px 14px;
  font-weight: 700;
  letter-spacing: 1px;
  border: 1px solid var(--accent-glow);
  border-radius: 20px;
  box-shadow: 0 0 15px var(--accent-glow);
}

.version-text {
  color: var(--text-secondary);
  font-weight: 500;
}

.main-title {
  font-size: 5rem;
  line-height: 1.1;
  font-weight: 700;
  margin: 0 0 35px 0;
  letter-spacing: -2px;
  color: var(--text-primary);
}

.gradient-text {
  background: linear-gradient(90deg, #FFFFFF 0%, #A0A0A0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
  text-shadow: 0 0 40px rgba(255, 255, 255, 0.1);
}

.hero-desc {
  font-size: 1.1rem;
  line-height: 1.8;
  color: var(--text-secondary);
  max-width: 680px;
  margin-bottom: 50px;
  font-weight: 400;
}

.hero-desc p {
  margin-bottom: 1.5rem;
}

.highlight-bold {
  color: var(--text-primary);
  font-weight: 700;
}

.highlight-code {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--text-primary);
}

.slogan-text {
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--text-primary);
  letter-spacing: 1px;
  border-left: 3px solid var(--accent-color);
  padding-left: 20px;
  box-shadow: -2px 0 10px rgba(255, 69, 0, 0.2);
}

.blinking-cursor {
  color: var(--accent-color);
  animation: blink 1s step-end infinite;
  font-weight: 800;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.decoration-square {
  width: 24px;
  height: 24px;
  background: var(--accent-color);
  box-shadow: 0 0 20px var(--accent-glow);
  transform: rotate(45deg);
  margin-top: 40px;
}

/* Hero Right Logo */
.hero-right {
  flex: 0.6;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-end;
  height: 400px;
}

.atp-logo-mark {
  font-family: var(--font-mono);
  font-size: 10rem;
  font-weight: 900;
  color: transparent;
  -webkit-text-stroke: 2px rgba(255, 255, 255, 0.1);
  letter-spacing: -5px;
  position: relative;
}

.atp-logo-mark::after {
  content: 'ATP';
  position: absolute;
  top: 0; left: 0;
  color: transparent;
  -webkit-text-stroke: 2px var(--accent-color);
  filter: blur(15px);
  opacity: 0.5;
  z-index: -1;
}

.scroll-down-btn {
  width: 50px;
  height: 50px;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  backdrop-filter: blur(4px);
  border-radius: 50%;
  border-color: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
  font-size: 1.5rem;
  transition: all 0.3s;
  margin-top: 40px;
}

.scroll-down-btn:hover {
  border-color: var(--accent-color);
  color: var(--accent-color);
  box-shadow: 0 0 15px var(--accent-glow);
  transform: translateY(5px);
}

/* Dashboard Section */
.dashboard-section {
  display: flex;
  gap: 60px;
  margin-top: 40px;
  align-items: stretch;
}

.left-panel, .right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* Left Panel */
.panel-header {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 25px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.status-dot {
  color: var(--accent-color);
  font-size: 1rem;
}

.pulsing {
  animation: pulse-glow 2s infinite;
}

@keyframes pulse-glow {
  0% { text-shadow: 0 0 5px var(--accent-glow); transform: scale(1); }
  50% { text-shadow: 0 0 20px var(--accent-color); transform: scale(1.2); }
  100% { text-shadow: 0 0 5px var(--accent-glow); transform: scale(1); }
}

.section-title {
  font-size: 2.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 15px;
  letter-spacing: -1px;
}

.section-desc {
  color: var(--text-secondary);
  font-size: 1.05rem;
  margin-bottom: 40px;
  line-height: 1.6;
}

.metrics-row {
  display: flex;
  gap: 20px;
  margin-bottom: 40px;
}

.metric-card {
  padding: 25px;
  flex: 1;
  text-align: center;
  transition: transform 0.3s;
}

.metric-card:hover {
  transform: translateY(-5px);
  border-color: var(--border-hover);
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 8px;
}

.metric-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.steps-container {
  padding: 35px;
}

.steps-header {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-primary);
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 12px;
  letter-spacing: 1px;
}

.diamond-icon {
  font-size: 1.2rem;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 25px;
  transition: all 0.3s;
}

.workflow-item:hover {
  transform: translateX(5px);
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 1.2rem;
}

.step-title {
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.step-desc {
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* Right Panel Console */
.console-box {
  padding: 10px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.console-section {
  padding: 25px;
}

.console-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* Upload Zone */
.upload-zone {
  border: 2px dashed rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-md);
  height: 250px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  background: rgba(0, 0, 0, 0.2);
}

.upload-zone:hover, .upload-zone.drag-over {
  border-color: var(--accent-color);
  background: rgba(255, 69, 0, 0.05);
  box-shadow: inset 0 0 20px rgba(255, 69, 0, 0.1);
}

.upload-placeholder {
  text-align: center;
}

.upload-icon-wrapper {
  width: 60px;
  height: 60px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 1.5rem;
  color: var(--text-primary);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.bounce {
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-10px); }
  60% { transform: translateY(-5px); }
}

.upload-title {
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.upload-hint {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.file-list {
  width: 100%;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  font-family: var(--font-mono);
  font-size: 0.95rem;
}

.file-name {
  flex: 1;
  margin: 0 15px;
  color: var(--text-primary);
}

.remove-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-secondary);
  transition: color 0.2s;
}

.remove-btn:hover {
  color: #ff3333;
}

/* Divider */
.console-divider {
  display: flex;
  align-items: center;
  padding: 0 25px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

.console-divider span {
  padding: 0 20px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 2px;
}

/* Text Input */
.focus-glow {
  border-radius: var(--radius-sm);
  transition: box-shadow 0.3s, border-color 0.3s;
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--border-color);
}

.focus-glow:focus-within {
  border-color: var(--accent-color);
  box-shadow: 0 0 15px rgba(255,69,0,0.2);
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  line-height: 1.6;
  resize: vertical;
  color: var(--text-primary);
  outline: none;
}

.code-input::placeholder {
  color: var(--text-secondary);
  opacity: 0.5;
}

.model-badge {
  position: absolute;
  bottom: 15px;
  right: 15px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--accent-color);
  background: rgba(255, 69, 0, 0.1);
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid rgba(255, 69, 0, 0.2);
}

/* Start Button */
.btn-section {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
  margin-top: auto;
}

.start-engine-btn {
  background: var(--text-primary);
  color: var(--bg-color);
  border: none;
  padding: 18px 40px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 800;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.start-engine-btn:disabled {
  background: var(--border-color);
  color: var(--text-secondary);
  cursor: not-allowed;
  box-shadow: none !important;
}

.action-glow {
  position: relative;
  overflow: hidden;
  z-index: 1;
}

.action-glow:not(:disabled):hover {
  background: var(--accent-color);
  color: var(--text-primary);
  box-shadow: 0 8px 30px rgba(255, 69, 0, 0.4);
  transform: translateY(-2px);
}

.btn-arrow {
  font-family: sans-serif;
  font-size: 1.3rem;
  transition: transform 0.3s;
}

.start-engine-btn:not(:disabled):hover .btn-arrow {
  transform: translateX(5px);
}

.mt-xl {
  margin-top: 80px;
}
</style>
`;

fs.writeFileSync(targetFile, newContent);
console.log("Successfully re-written Home.vue");

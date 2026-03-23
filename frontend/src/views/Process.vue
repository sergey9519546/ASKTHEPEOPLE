<template>
  <div class="process-page">
    <!-- Navbar -->
    <nav class="navbar">
      <div class="nav-brand" @click="goHome">Miro<span>Fish</span></div>
      
      <div class="nav-center">
        <div class="step-badge">STEP {{ currentStep.toString().padStart(2, '0') }}</div>
        <div class="step-name">{{ stepNames[currentStep - 1] }}</div>
      </div>

      <div class="nav-status">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </nav>

    <!-- Main Content Area -->
    <div class="main-content">
      <!-- Left Panel: Graph -->
      <div class="left-panel" :class="{ 'full-screen': isFullScreen }">
        <div class="panel-header">
          <div class="header-left">
            <span class="header-title">REAL-TIME KNOWLEDGE GRAPH</span>
          </div>
          <div class="header-right">
            <template v-if="graphData">
              <span class="stat-item">{{ nodes.length }} NODES</span>
              <span class="stat-divider">|</span>
              <span class="stat-item">{{ edges.length }} RELS</span>
              <span class="stat-divider">|</span>
            </template>
            <div class="action-buttons">
                <button class="action-btn" @click="refreshGraph" :disabled="graphLoading">↻</button>
                <button class="action-btn" @click="toggleFullScreen">{{ isFullScreen ? '↙' : '↗' }}</button>
            </div>
          </div>
        </div>
        
        <div class="graph-container" ref="graphContainer">
          <div v-if="graphData" class="graph-view">
            <svg ref="graphSvg" class="graph-svg"></svg>
            <div v-if="currentPhase === 1" class="graph-building-hint">
              <span class="building-dot"></span> BUILDING...
            </div>
            
            <!-- Detail Panel -->
            <div v-if="selectedItem" class="detail-panel">
              <div class="detail-panel-header">
                <span class="detail-title">{{ selectedItem.type === 'node' ? 'NODE' : 'RELATION' }}</span>
                <button class="detail-close" @click="closeDetailPanel">×</button>
              </div>
              
              <div class="detail-content">
                <div v-if="selectedItem.type === 'node'">
                  <div class="detail-row">
                    <span class="detail-label">NAME</span>
                    <span class="detail-value highlight">{{ selectedItem.data.name }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">TYPE</span>
                    <span class="detail-value">{{ selectedItem.entityType }}</span>
                  </div>
                  <div v-if="selectedItem.data.summary" class="detail-summary">
                    {{ selectedItem.data.summary }}
                  </div>
                </div>
                <div v-else>
                  <div class="edge-relation">
                    <span class="edge-source">{{ selectedItem.source_name }}</span>
                    <span class="edge-arrow">→</span>
                    <span class="edge-type">{{ selectedItem.fact_type }}</span>
                    <span class="edge-arrow">→</span>
                    <span class="edge-target">{{ selectedItem.target_name }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="graphLoading" class="graph-loading">LOADING GRAPH...</div>
          <div v-else class="graph-waiting">STAGING REALITY...</div>
        </div>
      </div>

      <!-- Right Panel: Steps -->
      <div class="right-panel" :class="{ 'hidden': isFullScreen }">
        <div class="panel-header">
          <span class="header-title">EXECUTION PIPELINE</span>
        </div>
        
        <div class="process-content">
          <div 
            v-for="phase in phases" 
            :key="phase.id" 
            class="process-phase"
            :class="{ active: currentPhase === phase.id, completed: currentPhase > phase.id }"
          >
            <div class="phase-header">
              <span class="phase-num">{{ phase.id.toString().padStart(2, '0') }}</span>
              <div class="phase-info">
                <div class="phase-title">{{ phase.title }}</div>
                <div class="phase-status" :class="{ active: currentPhase === phase.id, completed: currentPhase > phase.id }">
                  {{ currentPhase === phase.id ? 'PROCESSING' : (currentPhase > phase.id ? 'COMPLETED' : 'PENDING') }}
                </div>
              </div>
            </div>
            
            <div v-if="currentPhase === phase.id" class="phase-detail">
               <div v-if="phase.id === 1">
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: (buildProgress?.progress || 0) + '%' }"></div>
                  </div>
                  <div class="progress-info">
                    <span>{{ buildProgress?.message || 'Extracting seeds...' }}</span>
                    <span>{{ buildProgress?.progress || 0 }}%</span>
                  </div>
               </div>
               <div v-else-if="phase.id === 2">
                  <div class="ontology-hint">GRAPH DATA INTEGRATED. READY FOR ENVIRONMENT INJECTION.</div>
               </div>
            </div>
          </div>

          <div class="next-step-section" v-if="currentPhase >= 2">
            <button class="next-step-btn" @click="goToNextStep">
              INITIALIZE ENVIRONMENT <span>→</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as d3 from 'd3'
import { getProject, buildGraph, getTaskStatus, getGraphData } from '../api/graph'

const route = useRoute()
const router = useRouter()

const currentStep = ref(1)
const stepNames = ['GRAPH BUILD', 'ENV SETUP', 'RUNTIME', 'REPORTING', 'INTERACTION']
const phases = [
  { id: 1, title: 'GRAPHRAG CONSTRUCTION' },
  { id: 2, title: 'REALITY SEED EXTRACTION' },
  { id: 3, title: 'ENTITY RELATION MAPPING' }
]

const currentPhase = ref(1)
const projectData = ref(null)
const graphData = ref(null)
const buildProgress = ref(null)
const graphLoading = ref(false)
const error = ref('')
const isFullScreen = ref(false)
const selectedItem = ref(null)
const graphSvg = ref(null)
const graphContainer = ref(null)

const currentProjectId = computed(() => route.params.projectId)

const statusClass = computed(() => {
  if (error.value) return 'error'
  if (currentPhase.value < 3) return 'processing'
  return 'completed'
})

const statusText = computed(() => {
  if (error.value) return 'ERROR'
  if (currentPhase.value < 3) return 'PROCESSING'
  return 'READY'
})

// Navigation
const goHome = () => router.push('/')
const goToNextStep = () => {
  router.push({ name: 'Main', query: { step: 2, projectId: currentProjectId.value }})
}

// Logic
let pollTimer = null
const initProject = async () => {
  const result = await getProject(currentProjectId.value)
  if (result.success) {
    projectData.value = result.data
    if (route.params.projectId === 'new') {
       // Should have been handled by redirect or state, but let's assume we have files
    }
    startGraphBuild()
  }
}

const startGraphBuild = async () => {
  const result = await buildGraph(currentProjectId.value)
  if (result.success) {
    pollTaskStatus(result.data.task_id)
  }
}

const pollTaskStatus = (taskId) => {
  pollTimer = setInterval(async () => {
    const result = await getTaskStatus(taskId)
    if (result.success) {
      const task = result.data
      buildProgress.value = { progress: task.progress, message: task.message }
      if (task.status === 'completed') {
        clearInterval(pollTimer)
        currentPhase.value = 2
        loadGraphData()
      } else if (task.status === 'failed') {
        clearInterval(pollTimer)
        error.value = task.error
      }
    }
  }, 2000)
}

const loadGraphData = async () => {
  const result = await getProject(currentProjectId.value)
  if (result.success && result.data.graph_id) {
    graphLoading.value = true
    const gRes = await getGraphData(result.data.graph_id)
    if (gRes.success) {
      graphData.value = gRes.data
      nextTick(renderGraph)
    }
    graphLoading.value = false
  }
}

const nodes = computed(() => graphData.value?.nodes || [])
const edges = computed(() => graphData.value?.edges || [])

const renderGraph = () => {
  if (!graphSvg.value || !graphData.value) return
  const container = graphContainer.value
  const rect = container.getBoundingClientRect()
  const width = rect.width
  const height = rect.height
  
  const svg = d3.select(graphSvg.value)
    .attr('width', width)
    .attr('height', height)
  svg.selectAll('*').remove()

  const simulation = d3.forceSimulation(nodes.value)
    .force('link', d3.forceLink(edges.value).id(d => d.uuid).distance(100))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))

  const g = svg.append('g')
  svg.call(d3.zoom().on('zoom', (event) => g.attr('transform', event.transform)))

  const link = g.append('g')
    .selectAll('line')
    .data(edges.value)
    .enter().append('line')
    .attr('stroke', '#000')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', 0.2)

  const node = g.append('g')
    .selectAll('circle')
    .data(nodes.value)
    .enter().append('circle')
    .attr('r', 8)
    .attr('fill', d => d.color || '#E14B3B')
    .attr('stroke', '#000')
    .attr('stroke-width', 2)
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
    .on('click', (event, d) => {
      event.stopPropagation()
      selectedItem.value = { type: 'node', data: d, entityType: d.labels?.[0] }
    })

  simulation.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    node.attr('cx', d => d.x).attr('cy', d => d.y)
  })

  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    event.subject.fx = event.subject.x
    event.subject.fy = event.subject.y
  }
  function dragged(event) {
    event.subject.fx = event.x
    event.subject.fy = event.y
  }
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0)
    event.subject.fx = null
    event.subject.fy = null
  }
}

const toggleFullScreen = () => isFullScreen.value = !isFullScreen.value
const closeDetailPanel = () => selectedItem.value = null
const refreshGraph = () => loadGraphData()

onMounted(initProject)
onUnmounted(() => pollTimer && clearInterval(pollTimer))
</script>

<style scoped>
.process-page {
  min-height: 100vh;
  background-color: var(--bau-bg);
  color: var(--bau-black);
  font-family: var(--font-sans);
}

.navbar {
  height: 60px;
  background: #FFF;
  border-bottom: 2px solid var(--bau-black);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
}

.nav-brand { font-family: var(--font-mono); font-weight: 900; text-transform: uppercase; cursor: pointer; }
.nav-brand span { color: var(--bau-red); }

.nav-center {
  background: var(--bau-bg);
  border: 2px solid var(--bau-black);
  padding: 4px 16px;
  display: flex;
  gap: 12px;
}

.step-badge { font-family: var(--font-mono); font-weight: 900; color: var(--bau-red); font-size: 0.8rem; }
.step-name { font-weight: 800; text-transform: uppercase; font-size: 0.9rem; }

.nav-status { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-weight: 800; font-size: 0.75rem; }
.status-dot { width: 10px; height: 10px; border: 1px solid var(--bau-black); }
.status-dot.processing { background: var(--bau-red); animation: pulse 1s infinite step-end; }
.status-dot.completed { background: var(--bau-blue); }
.status-dot.error { background: var(--bau-black); }

@keyframes pulse { 50% { opacity: 0; } }

.main-content {
  display: flex;
  height: calc(100vh - 60px);
  padding: 20px;
  gap: 20px;
}

.left-panel {
  flex: 1;
  background: #FFF;
  border: 2px solid var(--bau-black);
  display: flex;
  flex-direction: column;
}

.panel-header {
  height: 50px;
  background: var(--bau-bg);
  border-bottom: 2px solid var(--bau-black);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-title { font-weight: 800; font-size: 0.8rem; text-transform: uppercase; }

.action-btn { width: 32px; height: 32px; border: 2px solid var(--bau-black); background: #FFF; cursor: pointer; font-weight: 900; }
.action-btn:hover { background: var(--bau-yellow); }

.graph-container { flex: 1; position: relative; }
.graph-svg { width: 100%; height: 100%; }

.detail-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 300px;
  background: #FFF;
  border: 2px solid var(--bau-black);
  padding: 20px;
}

.detail-panel-header { display: flex; justify-content: space-between; border-bottom: 2px solid var(--bau-black); margin-bottom: 15px; padding-bottom: 10px; font-weight: 900; }
.detail-close { cursor: pointer; border: none; background: none; font-size: 1.2rem; font-weight: 900; }

.detail-row { margin-bottom: 10px; font-size: 0.8rem; }
.detail-label { font-family: var(--font-mono); opacity: 0.5; margin-right: 8px; font-weight: 700; }
.detail-value { font-weight: 800; }
.detail-summary { background: var(--bau-bg); padding: 12px; border: 1px solid var(--bau-black); font-size: 0.85rem; line-height: 1.4; }

.right-panel {
  width: 450px;
  background: #FFF;
  border: 2px solid var(--bau-black);
  padding: 30px;
  overflow-y: auto;
}

.process-phase { border: 2px solid var(--bau-black); margin-bottom: 20px; }
.phase-header { padding: 16px; border-bottom: 2px solid var(--bau-black); display: flex; gap: 15px; }
.phase-num { font-family: var(--font-mono); font-weight: 900; font-size: 1.4rem; color: var(--bau-red); }
.phase-title { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; }
.phase-status { margin-left: auto; font-family: var(--font-mono); font-size: 0.7rem; padding: 2px 8px; border: 1px solid var(--bau-black); font-weight: 800; }
.phase-status.active { background: var(--bau-yellow); }
.phase-status.completed { background: var(--bau-blue); color: #FFF; }

.phase-detail { padding: 20px; font-size: 0.85rem; }

.progress-bar { height: 10px; background: var(--bau-bg); border: 2px solid var(--bau-black); margin-bottom: 8px; }
.progress-fill { height: 100%; background: var(--bau-red); }
.progress-info { display: flex; justify-content: space-between; font-family: var(--font-mono); font-weight: 700; font-size: 0.75rem; }

.next-step-btn {
  width: 100%;
  height: 60px;
  background: var(--bau-black);
  color: #FFF;
  font-weight: 900;
  font-family: var(--font-mono);
  font-size: 1.1rem;
  cursor: pointer;
}

.next-step-btn:hover { background: var(--bau-red); box-shadow: 4px 4px 0 var(--bau-black); }

@media (max-width: 1024px) {
  .main-content { flex-direction: column; height: auto; }
  .left-panel, .right-panel { width: 100%; height: 500px; }
}
</style>

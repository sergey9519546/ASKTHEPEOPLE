<template>
  <div class="main-view">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">MiroFish</div>
      </div>
      
      <div class="header-center">
        <div class="view-switcher">
          <button 
            v-for="mode in ['graph', 'split', 'workbench']" 
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: '图谱', split: '双栏', workbench: '工作台' }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num">Step 5/5</span>
          <span class="step-name">深度互动</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel 
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="5"
          :isSimulating="false"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step5 深度互动 -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step5Interaction
          :reportId="currentReportId"
          :simulationId="simulationId"
          :systemLogs="systemLogs"
          @add-log="addLog"
          @update-status="updateStatus"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import Step5Interaction from '../components/Step5Interaction.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation } from '../api/simulation'
import { getReport } from '../api/report'

const route = useRoute()
const router = useRouter()

// Props
const props = defineProps({
  reportId: String
})

// Layout State - 默认切换到工作台视角
const viewMode = ref('workbench')

// Data State
const currentReportId = ref(route.params.reportId)
const simulationId = ref(null)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('ready') // ready | processing | completed | error

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  return currentStatus.value
})

const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Error'
  if (currentStatus.value === 'completed') return 'Completed'
  if (currentStatus.value === 'processing') return 'Processing'
  return 'Ready'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

// --- Data Logic ---
const loadReportData = async () => {
  try {
    addLog(`加载报告数据: ${currentReportId.value}`)
    
    // 获取 report 信息以获取 simulation_id
    const reportRes = await getReport(currentReportId.value)
    if (reportRes.success && reportRes.data) {
      const reportData = reportRes.data
      simulationId.value = reportData.simulation_id
      
      if (simulationId.value) {
        // 获取 simulation 信息
        const simRes = await getSimulation(simulationId.value)
        if (simRes.success && simRes.data) {
          const simData = simRes.data
          
          // 获取 project 信息
          if (simData.project_id) {
            const projRes = await getProject(simData.project_id)
            if (projRes.success && projRes.data) {
              projectData.value = projRes.data
              addLog(`项目加载成功: ${projRes.data.project_id}`)
              
              // 获取 graph 数据
              if (projRes.data.graph_id) {
                await loadGraph(projRes.data.graph_id)
              }
            }
          }
        }
      }
    } else {
      addLog(`获取报告信息失败: ${reportRes.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`加载异常: ${err.message}`)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('图谱数据加载成功')
    }
  } catch (err) {
    addLog(`图谱加载失败: ${err.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) {
    loadGraph(projectData.value.graph_id)
  }
}

// Watch route params
watch(() => route.params.reportId, (newId) => {
  if (newId && newId !== currentReportId.value) {
    currentReportId.value = newId
    loadReportData()
  }
}, { immediate: true })

onMounted(() => {
  addLog('InteractionView 初始化')
  loadReportData()
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bau-bg);
  overflow: hidden;
  font-family: var(--font-sans);
  color: var(--bau-black);
}

/* Header */
.app-header {
  height: 60px;
  border-bottom: 2px solid var(--bau-black);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  background: #FFF;
  z-index: 100;
  position: relative;
}

.brand {
  font-family: var(--font-mono);
  font-weight: 900;
  font-size: 1.2rem;
  text-transform: uppercase;
  cursor: pointer;
  color: var(--bau-black);
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.view-switcher {
  display: flex;
  background: var(--bau-bg);
  padding: 4px;
  border: 2px solid var(--bau-black);
  gap: 4px;
}

.switch-btn {
  border: none;
  background: transparent;
  padding: 6px 16px;
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--bau-black);
  cursor: pointer;
  text-transform: uppercase;
  font-family: var(--font-mono);
}

.switch-btn.active {
  background: var(--bau-black);
  color: #FFF;
}

.switch-btn:hover:not(.active) {
  background: var(--bau-yellow);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.85rem;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 900;
  color: var(--bau-red);
}

.step-name {
  font-weight: 800;
  text-transform: uppercase;
}

.step-divider {
  width: 2px;
  height: 20px;
  background-color: var(--bau-black);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  font-weight: 800;
  font-family: var(--font-mono);
  text-transform: uppercase;
}

.dot {
  width: 10px;
  height: 10px;
  border: 1px solid var(--bau-black);
  background: #DDD;
}

.status-indicator.processing .dot {
  background: var(--bau-red);
  animation: pulse 1s infinite step-end;
}
.status-indicator.completed .dot {
  background: var(--bau-blue);
}
.status-indicator.error .dot {
  background: var(--bau-black);
}

@keyframes pulse { 50% { opacity: 0; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  padding: 20px;
  gap: 20px;
}

.panel-wrapper {
  height: 100%;
  border-right: 1px solid var(--border-color);
}
</style>

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
          <span class="step-num">Step 2/5</span>
          <span class="step-name">环境搭建</span>
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
          :currentPhase="2"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step2 环境搭建 -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step2EnvSetup
          :simulationId="currentSimulationId"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStatus"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, stopSimulation, getEnvStatus, closeSimulationEnv } from '../api/simulation'

const route = useRoute()
const router = useRouter()

// Props
const props = defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')

// Data State
const currentSimulationId = ref(route.params.simulationId)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('processing') // processing | completed | error

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
  if (currentStatus.value === 'completed') return 'Ready'
  return 'Preparing'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 100) {
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

const handleGoBack = () => {
  // 返回到 process 页面
  if (projectData.value?.project_id) {
    router.push({ name: 'Process', params: { projectId: projectData.value.project_id } })
  } else {
    router.push('/')
  }
}

const handleNextStep = (params = {}) => {
  addLog('进入 Step 3: 开始模拟')
  
  // 记录模拟轮数配置
  if (params.maxRounds) {
    addLog(`自定义模拟轮数: ${params.maxRounds} 轮`)
  } else {
    addLog('使用自动配置的模拟轮数')
  }
  
  // 构建路由参数
  const routeParams = {
    name: 'SimulationRun',
    params: { simulationId: currentSimulationId.value }
  }
  
  // 如果有自定义轮数，通过 query 参数传递
  if (params.maxRounds) {
    routeParams.query = { maxRounds: params.maxRounds }
  }
  
  // 跳转到 Step 3 页面
  router.push(routeParams)
}

// --- Data Logic ---

/**
 * 检查并关闭正在运行的模拟
 * 当用户从 Step 3 返回到 Step 2 时，默认用户要退出模拟
 */
const checkAndStopRunningSimulation = async () => {
  if (!currentSimulationId.value) return
  
  try {
    // 先检查模拟环境是否存活
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })
    
    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      addLog('检测到模拟环境正在运行，正在关闭...')
      
      // 尝试优雅关闭模拟环境
      try {
        const closeRes = await closeSimulationEnv({ 
          simulation_id: currentSimulationId.value,
          timeout: 10  // 10秒超时
        })
        
        if (closeRes.success) {
          addLog('✓ 模拟环境已关闭')
        } else {
          addLog(`关闭模拟环境失败: ${closeRes.error || '未知错误'}`)
          // 如果优雅关闭失败，尝试强制停止
          await forceStopSimulation()
        }
      } catch (closeErr) {
        addLog(`关闭模拟环境异常: ${closeErr.message}`)
        // 如果优雅关闭异常，尝试强制停止
        await forceStopSimulation()
      }
    } else {
      // 环境未运行，但可能进程还在，检查模拟状态
      const simRes = await getSimulation(currentSimulationId.value)
      if (simRes.success && simRes.data?.status === 'running') {
        addLog('检测到模拟状态为运行中，正在停止...')
        await forceStopSimulation()
      }
    }
  } catch (err) {
    // 检查环境状态失败不影响后续流程
    console.warn('检查模拟状态失败:', err)
  }
}

/**
 * 强制停止模拟
 */
const forceStopSimulation = async () => {
  try {
    const stopRes = await stopSimulation({ simulation_id: currentSimulationId.value })
    if (stopRes.success) {
      addLog('✓ 模拟已强制停止')
    } else {
      addLog(`强制停止模拟失败: ${stopRes.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`强制停止模拟异常: ${err.message}`)
  }
}

const loadSimulationData = async () => {
  try {
    addLog(`加载模拟数据: ${currentSimulationId.value}`)
    
    // 获取 simulation 信息
    const simRes = await getSimulation(currentSimulationId.value)
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
    } else {
      addLog(`加载模拟数据失败: ${simRes.error || '未知错误'}`)
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

onMounted(async () => {
  addLog('SimulationView 初始化')
  
  // 检查并关闭正在运行的模拟（用户从 Step 3 返回时）
  await checkAndStopRunningSimulation()
  
  // 加载模拟数据
  loadSimulationData()
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
  background: #FFF;
  border: 2px solid var(--bau-black);
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.panel-wrapper.left { border-right: 2px solid var(--bau-black); }

@media (max-width: 1024px) {
  .content-area { flex-direction: column; }
  .panel-wrapper { width: 100% !important; height: 50% !important; }
}
</style>


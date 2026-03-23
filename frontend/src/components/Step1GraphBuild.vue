<template>
  <div class="workbench-panel">
    <div class="scroll-container">
      <!-- Step 01: Ontology -->
      <div class="step-card" :class="{ 'active': currentPhase === 0, 'completed': currentPhase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">本体生成</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 0" class="badge success">已完成</span>
            <span v-else-if="currentPhase === 0" class="badge processing">生成中</span>
            <span v-else class="badge pending">等待</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/graph/ontology/generate</p>
          <p class="description">
            LLM分析文档内容与模拟需求，提取出现实种子，自动生成合适的本体结构
          </p>

          <!-- Loading / Progress -->
          <div v-if="currentPhase === 0 && ontologyProgress" class="progress-section">
            <div class="spinner-sm"></div>
            <span>{{ ontologyProgress.message || '正在分析文档...' }}</span>
          </div>

          <!-- Detail Overlay -->
          <div v-if="selectedOntologyItem" class="ontology-detail-overlay">
            <div class="detail-header">
               <div class="detail-title-group">
                  <span class="detail-type-badge">{{ selectedOntologyItem.itemType === 'entity' ? 'ENTITY' : 'RELATION' }}</span>
                  <span class="detail-name">{{ selectedOntologyItem.name }}</span>
               </div>
               <button class="close-btn" @click="selectedOntologyItem = null">×</button>
            </div>
            <div class="detail-body">
               <div class="detail-desc">{{ selectedOntologyItem.description }}</div>
               
               <!-- Attributes -->
               <div class="detail-section" v-if="selectedOntologyItem.attributes?.length">
                  <span class="section-label">ATTRIBUTES</span>
                  <div class="attr-list">
                     <div v-for="attr in selectedOntologyItem.attributes" :key="attr.name" class="attr-item">
                        <span class="attr-name">{{ attr.name }}</span>
                        <span class="attr-type">({{ attr.type }})</span>
                        <span class="attr-desc">{{ attr.description }}</span>
                     </div>
                  </div>
               </div>

               <!-- Examples (Entity) -->
               <div class="detail-section" v-if="selectedOntologyItem.examples?.length">
                  <span class="section-label">EXAMPLES</span>
                  <div class="example-list">
                     <span v-for="ex in selectedOntologyItem.examples" :key="ex" class="example-tag">{{ ex }}</span>
                  </div>
               </div>

               <!-- Source/Target (Relation) -->
               <div class="detail-section" v-if="selectedOntologyItem.source_targets?.length">
                  <span class="section-label">CONNECTIONS</span>
                  <div class="conn-list">
                     <div v-for="(conn, idx) in selectedOntologyItem.source_targets" :key="idx" class="conn-item">
                        <span class="conn-node">{{ conn.source }}</span>
                        <span class="conn-arrow">→</span>
                        <span class="conn-node">{{ conn.target }}</span>
                     </div>
                  </div>
               </div>
            </div>
          </div>

          <!-- Generated Entity Tags -->
          <div v-if="projectData?.ontology?.entity_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">GENERATED ENTITY TYPES</span>
            <div class="tags-list">
              <span 
                v-for="entity in projectData.ontology.entity_types" 
                :key="entity.name" 
                class="entity-tag clickable"
                @click="selectOntologyItem(entity, 'entity')"
              >
                {{ entity.name }}
              </span>
            </div>
          </div>

          <!-- Generated Relation Tags -->
          <div v-if="projectData?.ontology?.edge_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">GENERATED RELATION TYPES</span>
            <div class="tags-list">
              <span 
                v-for="rel in projectData.ontology.edge_types" 
                :key="rel.name" 
                class="entity-tag clickable"
                @click="selectOntologyItem(rel, 'relation')"
              >
                {{ rel.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Graph Build -->
      <div class="step-card" :class="{ 'active': currentPhase === 1, 'completed': currentPhase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">GraphRAG构建</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 1" class="badge success">已完成</span>
            <span v-else-if="currentPhase === 1" class="badge processing">{{ buildProgress?.progress || 0 }}%</span>
            <span v-else class="badge pending">等待</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/graph/build</p>
          <p class="description">
            基于生成的本体，将文档自动分块后调用 Zep 构建知识图谱，提取实体和关系，并形成时序记忆与社区摘要
          </p>
          
          <!-- Stats Cards -->
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.nodes }}</span>
              <span class="stat-label">实体节点</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.edges }}</span>
              <span class="stat-label">关系边</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.types }}</span>
              <span class="stat-label">SCHEMA类型</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: Complete -->
      <div class="step-card" :class="{ 'active': currentPhase === 2, 'completed': currentPhase >= 2 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">构建完成</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase >= 2" class="badge accent">进行中</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">图谱构建已完成，请进入下一步进行模拟环境搭建</p>
          <button 
            class="action-btn" 
            :disabled="currentPhase < 2 || creatingSimulation"
            @click="handleEnterEnvSetup"
          >
            <span v-if="creatingSimulation" class="spinner-sm"></span>
            {{ creatingSimulation ? '创建中...' : '进入环境搭建 ➝' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <span class="log-id">{{ projectData?.project_id || 'NO_PROJECT' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createSimulation } from '../api/simulation'

const router = useRouter()

const props = defineProps({
  currentPhase: { type: Number, default: 0 },
  projectData: Object,
  ontologyProgress: Object,
  buildProgress: Object,
  graphData: Object,
  systemLogs: { type: Array, default: () => [] }
})

defineEmits(['next-step'])

const selectedOntologyItem = ref(null)
const logContent = ref(null)
const creatingSimulation = ref(false)

// 进入环境搭建 - 创建 simulation 并跳转
const handleEnterEnvSetup = async () => {
  if (!props.projectData?.project_id || !props.projectData?.graph_id) {
    console.error('缺少项目或图谱信息')
    return
  }
  
  creatingSimulation.value = true
  
  try {
    const res = await createSimulation({
      project_id: props.projectData.project_id,
      graph_id: props.projectData.graph_id,
      enable_twitter: true,
      enable_reddit: true
    })
    
    if (res.success && res.data?.simulation_id) {
      // 跳转到 simulation 页面
      router.push({
        name: 'Simulation',
        params: { simulationId: res.data.simulation_id }
      })
    } else {
      console.error('创建模拟失败:', res.error)
      alert('创建模拟失败: ' + (res.error || '未知错误'))
    }
  } catch (err) {
    console.error('创建模拟异常:', err)
    alert('创建模拟异常: ' + err.message)
  } finally {
    creatingSimulation.value = false
  }
}

const selectOntologyItem = (item, type) => {
  selectedOntologyItem.value = { ...item, itemType: type }
}

const graphStats = computed(() => {
  const nodes = props.graphData?.node_count || props.graphData?.nodes?.length || 0
  const edges = props.graphData?.edge_count || props.graphData?.edges?.length || 0
  const types = props.projectData?.ontology?.entity_types?.length || 0
  return { nodes, edges, types }
})

const formatDate = (dateStr) => {
  if (!dateStr) return '--:--:--'
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-US', { hour12: false }) + '.' + d.getMilliseconds()
}

// Auto-scroll logs
watch(() => props.systemLogs.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.workbench-panel {
  height: 100%;
  background-color: var(--bau-bg);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: var(--font-sans);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.step-card {
  background: #FFF;
  border: 4px solid var(--bau-black);
  padding: 24px;
  transition: all 0.2s;
  position: relative;
}

.step-card.active {
  border-color: var(--bau-red);
  box-shadow: 8px 8px 0 rgba(0,0,0,0.1);
}

.step-card.completed {
  border-color: var(--bau-black);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--bau-black);
  padding-bottom: 12px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 24px;
  font-weight: 900;
  color: var(--bau-red);
}

.step-title {
  font-weight: 900;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.badge {
  font-size: 10px;
  padding: 4px 10px;
  font-weight: 900;
  text-transform: uppercase;
  border: 1px solid var(--bau-black);
}

.badge.success { background: var(--bau-green); color: #FFF; }
.badge.processing { background: var(--bau-yellow); color: var(--bau-black); }
.badge.accent { background: var(--bau-red); color: #FFF; }
.badge.pending { background: #EEE; color: #999; }

.api-note {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--bau-black);
  opacity: 0.5;
  margin-bottom: 12px;
  font-weight: 700;
}

.description {
  font-size: 0.85rem;
  color: var(--bau-black);
  line-height: 1.6;
  margin-bottom: 20px;
  font-weight: 500;
}

/* Tags */
.tags-container {
  margin-top: 16px;
}

.tag-label {
  display: block;
  font-size: 10px;
  font-weight: 900;
  color: var(--bau-red);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag {
  background: var(--bau-bg);
  border: 2px solid var(--bau-black);
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 800;
  color: var(--bau-black);
  font-family: var(--font-mono);
  cursor: pointer;
}

.entity-tag:hover {
  background: var(--bau-yellow);
  transform: translate(-2px, -2px);
  box-shadow: 2px 2px 0 var(--bau-black);
}

/* Overlay */
.ontology-detail-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(255,255,255,0.95);
  z-index: 50;
  display: flex;
  flex-direction: column;
}

.detail-header {
  padding: 16px 24px;
  background: var(--bau-black);
  color: #FFF;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-type-badge {
  font-size: 10px;
  font-weight: 900;
  background: var(--bau-red);
  padding: 2px 8px;
  margin-right: 12px;
}

.detail-name {
  font-weight: 900;
  font-family: var(--font-mono);
}

.close-btn {
  background: none;
  border: none;
  color: #FFF;
  font-size: 1.5rem;
  font-weight: 900;
  cursor: pointer;
}

.detail-body {
  padding: 24px;
  overflow-y: auto;
}

.detail-desc {
  font-size: 0.9rem;
  line-height: 1.6;
  padding-bottom: 20px;
  border-bottom: 2px solid var(--bau-black);
  margin-bottom: 24px;
  font-weight: 600;
}

.section-label {
  display: block;
  font-size: 10px;
  font-weight: 900;
  color: var(--bau-red);
  margin-bottom: 16px;
  text-transform: uppercase;
}

.attr-item {
  padding: 12px;
  background: var(--bau-bg);
  border: 1px solid var(--bau-black);
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.attr-name {
  font-weight: 900;
  font-family: var(--font-mono);
}

.example-tag {
  background: var(--bau-yellow);
  border: 1px solid var(--bau-black);
  padding: 4px 12px;
  font-weight: 800;
  font-size: 0.75rem;
  margin-right: 8px;
  margin-bottom: 8px;
}

.conn-item {
  padding: 12px;
  background: var(--bau-blue);
  color: #FFF;
  border: 1px solid var(--bau-black);
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-weight: 800;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 20px;
}

.stat-card {
  padding: 16px;
  background: var(--bau-bg);
  border: 2px solid var(--bau-black);
  text-align: center;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--bau-red);
}

.stat-label {
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  margin-top: 8px;
  color: var(--bau-black);
}

/* Action Btn */
.action-btn {
  width: 100%;
  padding: 16px;
  background: var(--bau-red);
  color: #FFF;
  border: 2px solid var(--bau-black);
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 var(--bau-black);
  transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 var(--bau-black);
}

.action-btn:active:not(:disabled) {
  transform: translate(0, 0);
  box-shadow: 0 0 0 var(--bau-black);
}

.action-btn:disabled {
  background: #CCC;
  box-shadow: none;
  cursor: not-allowed;
}

/* Logs */
.system-logs {
  background: var(--bau-black);
  color: #FFF;
  padding: 24px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid #444;
  padding-bottom: 12px;
  margin-bottom: 12px;
}

.log-title {
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--bau-yellow);
}

.log-content {
  height: 120px;
  overflow-y: auto;
  font-size: 0.75rem;
}

.log-time {
  color: #666;
  margin-right: 16px;
}

.log-msg {
  color: #AAA;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 3px solid rgba(255,255,255,0.2);
  border-top-color: #FFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }
</style>


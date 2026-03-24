<template>
  <div class="step5-interaction-workbench">
    <!-- Header -->
    <header class="workbench-header">
      <div class="header-left">
        <h1 class="workbench-title">STEP 5: DEEP INTERACTION</h1>
        <p class="workbench-subtitle">Engage with simulation agents and report synthesis</p>
      </div>
      <div class="header-right">
        <div class="simulation-badge">
          <span class="badge-label">SIM_ID:</span>
          <span class="badge-value">{{ simulationId || 'N/A' }}</span>
        </div>
      </div>
    </header>

    <div class="workbench-layout">
      <!-- Left Panel: Report Context -->
      <aside class="context-panel" ref="leftPanel">
        <div class="panel-header">
          <h2 class="panel-title">REPORT CONTEXT</h2>
        </div>

        <div class="report-container">
          <div v-if="!reportOutline" class="empty-context">
            <div class="bauhaus-loader"></div>
            <p>Awaiting report synthesis...</p>
          </div>

          <div v-else class="report-content">
            <div class="report-intro bauhaus-card">
              <h1 class="report-title">{{ reportOutline.title }}</h1>
              <p class="report-summary">{{ reportOutline.summary }}</p>
            </div>

            <div class="sections-list">
              <div 
                v-for="(section, idx) in reportOutline.sections" 
                :key="idx"
                class="report-section bauhaus-card"
                :class="{ 
                  'is-active': currentSectionIndex === idx + 1,
                  'is-complete': isSectionCompleted(idx + 1),
                  'is-collapsed': collapsedSections.has(idx)
                }"
              >
                <div class="section-header" @click="toggleSectionCollapse(idx)">
                  <span class="section-number">{{ String(idx + 1).padStart(2, '0') }}</span>
                  <h3 class="section-title">{{ section.title }}</h3>
                  <div class="section-indicator">
                    <span v-if="isSectionCompleted(idx + 1)" class="indicator-done">DONE</span>
                    <span v-else-if="currentSectionIndex === idx + 1" class="indicator-writing">WRITING</span>
                    <span v-else class="indicator-pending">PENDING</span>
                  </div>
                </div>

                <div v-show="!collapsedSections.has(idx)" class="section-body">
                  <div v-if="generatedSections[idx + 1]" class="body-content markdown-body" v-html="renderMarkdown(generatedSections[idx + 1])"></div>
                  <div v-else-if="currentSectionIndex === idx + 1" class="body-loading">
                    <div class="text-cursor"></div>
                    <p>Synthesizing evidence...</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- Right Panel: Interaction Hub -->
      <main class="interaction-hub">
        <div class="interface-tabs">
          <button 
            class="tab-btn" 
            :class="{ active: chatTarget === 'report_agent' }"
            @click="selectReportAgentChat"
          >
            REPORT AGENT
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: chatTarget === 'agent' }"
            @click="toggleAgentDropdown"
          >
            {{ selectedAgent ? selectedAgent.username.toUpperCase() : 'INDIVIDUAL AGENTS' }}
            <span class="dropdown-arrow">▼</span>
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'survey' }"
            @click="selectSurveyTab"
          >
            SURVEY SYSTEM
          </button>

          <!-- Agent Dropdown -->
          <div v-if="showAgentDropdown" class="agent-dropdown bauhaus-card">
            <div class="dropdown-header">SELECT INTERVIEWEE</div>
            <div class="agent-list">
              <div 
                v-for="(agent, idx) in profiles" 
                :key="idx"
                class="agent-item"
                @click="selectAgent(agent, idx)"
              >
                <div class="agent-avatar">{{ agent.username[0] }}</div>
                <div class="agent-info">
                  <span class="agent-name">{{ agent.username }}</span>
                  <span class="agent-role">{{ agent.profession || 'SIM_CITIZEN' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Chat Interface -->
        <div v-if="activeTab === 'chat'" class="chat-viewport">
          <div class="messages-list" ref="chatMessages">
            <div v-if="chatHistory.length === 0" class="chat-empty">
              <div class="empty-graphic"></div>
              <p>{{ chatTarget === 'report_agent' ? 'Ask the Report Agent for granular insights.' : 'Directly interview simulation entities.' }}</p>
            </div>

            <div 
              v-for="(msg, idx) in chatHistory" 
              :key="idx" 
              class="message-item bauhaus-card"
              :class="msg.role"
            >
              <div class="message-meta">
                <span class="sender-tag">{{ msg.role === 'user' ? 'USER' : (chatTarget === 'report_agent' ? 'REPORT_AGENT' : selectedAgent?.username.toUpperCase()) }}</span>
                <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="message-content markdown-body" v-html="renderMarkdown(msg.content)"></div>
            </div>

            <div v-if="isSending" class="message-item assistant is-loading">
              <div class="loading-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>

          <div class="chat-input-area">
            <textarea 
              v-model="chatInput" 
              class="chat-input" 
              placeholder="Enter your query..."
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="isSending || (!selectedAgent && chatTarget === 'agent')"
            ></textarea>
            <button class="send-btn" @click="sendMessage" :disabled="!chatInput.trim() || isSending">
              SEND
            </button>
          </div>
        </div>

        <!-- Survey Interface -->
        <div v-if="activeTab === 'survey'" class="survey-viewport">
          <div class="survey-setup bauhaus-card">
            <div class="setup-header">
              <h3 class="setup-title">BATCH SURVEY SYSTEM</h3>
              <span class="selected-count">SELECTED: {{ selectedAgents.size }}</span>
            </div>
            
            <div class="agent-selection-grid">
              <label 
                v-for="(agent, idx) in profiles" 
                :key="idx" 
                class="agent-label"
                :class="{ checked: selectedAgents.has(idx) }"
              >
                <input type="checkbox" :checked="selectedAgents.has(idx)" @change="toggleAgentSelection(idx)">
                {{ agent.username }}
              </label>
            </div>

            <div class="selection-controls">
              <button class="small-btn" @click="selectAllAgents">ALL</button>
              <button class="small-btn" @click="clearAgentSelection">NONE</button>
            </div>

            <div class="question-area">
              <textarea v-model="surveyQuestion" class="survey-input" placeholder="Enter universal inquiry for selected agents..."></textarea>
              <button class="submit-survey-btn" @click="submitSurvey" :disabled="selectedAgents.size === 0 || !surveyQuestion.trim() || isSurveying">
                DISPATCH SURVEY
              </button>
            </div>
          </div>

          <div v-if="surveyResults.length > 0" class="survey-results">
            <div 
              v-for="(res, idx) in surveyResults" 
              :key="idx" 
              class="result-card bauhaus-card"
            >
              <div class="result-header">
                <span class="agent-name">{{ res.agent_name }}</span>
                <span class="agent-role">{{ res.profession }}</span>
              </div>
              <div class="result-body markdown-body" v-html="renderMarkdown(res.answer)"></div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick, reactive } from 'vue'
import { chatWithReport, getReport, getAgentLog } from '../api/report'
import { interviewAgents, getSimulationProfilesRealtime } from '../api/simulation'

const props = defineProps({
  reportId: String,
  simulationId: String,
});

const emit = defineEmits(['add-log', 'update-status']);

// State
const activeTab = ref('chat');
const chatTarget = ref('report_agent');
const showAgentDropdown = ref(false);
const selectedAgent = ref(null);
const selectedAgentIndex = ref(null);
const isSending = ref(false);
const chatInput = ref('');
const chatHistory = ref([]);
const chatHistoryCache = reactive({});
const profiles = ref([]);

// Report Data
const reportOutline = ref(null);
const generatedSections = ref({});
const collapsedSections = ref(new Set());
const currentSectionIndex = ref(null);

// Survey State
const selectedAgents = ref(new Set());
const surveyQuestion = ref('');
const surveyResults = ref([]);
const isSurveying = ref(false);

const chatMessages = ref(null);

// Methods
const addLog = (m) => emit('add-log', m);

const formatTime = (ts) => {
  if (!ts) return '';
  return new Date(ts).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
};

const renderMarkdown = (c) => {
  if (!c) return '';
  let html = c.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');
  return `<p>${html}</p>`;
};

const isSectionCompleted = (idx) => !!generatedSections.value[idx];

const toggleSectionCollapse = (idx) => {
  const s = new Set(collapsedSections.value);
  if (s.has(idx)) s.delete(idx);
  else s.add(idx);
  collapsedSections.value = s;
};

const saveChatToCache = () => {
  const key = chatTarget.value === 'report_agent' ? 'report' : `agent_${selectedAgentIndex.value}`;
  chatHistoryCache[key] = [...chatHistory.value];
};

const selectReportAgentChat = () => {
  saveChatToCache();
  chatTarget.value = 'report_agent';
  activeTab.value = 'chat';
  chatHistory.value = chatHistoryCache['report'] || [];
  showAgentDropdown.value = false;
};

const toggleAgentDropdown = () => {
  showAgentDropdown.value = !showAgentDropdown.value;
};

const selectAgent = (agent, idx) => {
  saveChatToCache();
  selectedAgent.value = agent;
  selectedAgentIndex.value = idx;
  chatTarget.value = 'agent';
  chatHistory.value = chatHistoryCache[`agent_${idx}`] || [];
  showAgentDropdown.value = false;
  activeTab.value = 'chat';
};

const selectSurveyTab = () => {
  activeTab.value = 'survey';
  showAgentDropdown.value = false;
};

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessages.value) chatMessages.value.scrollTop = chatMessages.value.scrollHeight;
  });
};

const sendMessage = async () => {
  if (!chatInput.value.trim() || isSending.value) return;
  const msg = chatInput.value.trim();
  chatInput.value = '';
  chatHistory.value.push({ role: 'user', content: msg, timestamp: new Date().toISOString() });
  scrollToBottom();
  isSending.value = true;

  try {
    if (chatTarget.value === 'report_agent') {
      const res = await chatWithReport({
        simulation_id: props.simulationId,
        message: msg,
        chat_history: chatHistory.value.slice(-6).map(m => ({ role: m.role, content: m.content }))
      });
      if (res.success) {
        chatHistory.value.push({ role: 'assistant', content: res.data.response || res.data.answer, timestamp: new Date().toISOString() });
      }
    } else {
      const res = await interviewAgents({
        simulation_id: props.simulationId,
        interviews: [{ agent_id: selectedAgentIndex.value, prompt: msg }]
      });
      if (res.success) {
        const results = res.data.result.results;
        const resp = results[`reddit_${selectedAgentIndex.value}`]?.response || results[`twitter_${selectedAgentIndex.value}`]?.response;
        chatHistory.value.push({ role: 'assistant', content: resp || 'No response', timestamp: new Date().toISOString() });
      }
    }
  } catch (e) {
    addLog(`Error: ${e.message}`);
  } finally {
    isSending.value = false;
    scrollToBottom();
    saveChatToCache();
  }
};

// Survey Methods
const toggleAgentSelection = (idx) => {
  const s = new Set(selectedAgents.value);
  if (s.has(idx)) s.delete(idx);
  else s.add(idx);
  selectedAgents.value = s;
};

const selectAllAgents = () => {
  selectedAgents.value = new Set(profiles.value.map((_, i) => i));
};

const clearAgentSelection = () => {
  selectedAgents.value = new Set();
};

const submitSurvey = async () => {
  if (selectedAgents.value.size === 0 || !surveyQuestion.value.trim()) return;
  isSurveying.value = true;
  addLog(`Dispatching survey to ${selectedAgents.value.size} agents...`);
  try {
    const res = await interviewAgents({
      simulation_id: props.simulationId,
      interviews: Array.from(selectedAgents.value).map(idx => ({ agent_id: idx, prompt: surveyQuestion.value.trim() }))
    });
    if (res.success) {
      const results = res.data.result.results;
      surveyResults.value = Array.from(selectedAgents.value).map(idx => {
        const agent = profiles.value[idx];
        const ans = results[`reddit_${idx}`]?.response || results[`twitter_${idx}`]?.response || 'N/A';
        return { agent_name: agent.username, profession: agent.profession, answer: ans };
      });
    }
  } finally {
    isSurveying.value = false;
  }
};

const loadData = async () => {
  if (!props.reportId || !props.simulationId) return;
  try {
    const logRes = await getAgentLog(props.reportId, 0);
    if (logRes.success && logRes.data) {
      const logs = logRes.data.logs || [];
      logs.forEach(l => {
        if (l.action === 'planning_complete') reportOutline.value = l.details.outline;
        if (l.action === 'section_complete') generatedSections.value[l.section_index] = l.details.content;
      });
    }
    const profRes = await getSimulationProfilesRealtime(props.simulationId, 'reddit');
    if (profRes.success) profiles.value = profRes.data.profiles || [];
  } catch (e) { addLog(`Load error: ${e.message}`); }
};

onMounted(() => {
  loadData();
  const onClick = (e) => {
    if (!e.target.closest('.agent-dropdown') && !e.target.closest('.tab-btn')) showAgentDropdown.value = false;
  };
  document.addEventListener('click', onClick);
  onUnmounted(() => document.removeEventListener('click', onClick));
});

watch(() => props.reportId, loadData);
</script>

<style scoped>
:root {
  --atp-black: #000000;
  --atp-white: #FFFFFF;
  --atp-blue: #0026FE;
  --atp-red: #FF331F;
  --atp-yellow: #E5FF00;
}

.step5-interaction-workbench {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--atp-white);
  color: var(--atp-black);
  font-family: 'Inter', sans-serif;
  overflow: hidden;
}

.workbench-header {
  height: 80px;
  border-bottom: 4px solid var(--atp-black);
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.workbench-title { font-weight: 900; font-size: 24px; letter-spacing: -1px; }
.workbench-subtitle { font-size: 14px; font-weight: 600; opacity: 0.8; }

.simulation-badge {
  padding: 8px 16px;
  border: 3px solid var(--atp-black);
  font-weight: 800;
  font-size: 12px;
}

.badge-label { opacity: 0.6; margin-right: 5px; }

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.context-panel {
  width: 450px;
  border-right: 4px solid var(--atp-black);
  display: flex;
  flex-direction: column;
}

.interaction-hub {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.panel-header {
  height: 60px;
  border-bottom: 3px solid var(--atp-black);
  padding: 0 20px;
  display: flex;
  align-items: center;
}

.panel-title { font-weight: 800; font-size: 14px; }

.report-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.bauhaus-card {
  border: 4px solid var(--atp-black);
  padding: 20px;
  margin-bottom: 20px;
  background: var(--atp-white);
}

.report-title { font-weight: 900; font-size: 24px; margin-bottom: 10px; }
.report-summary { font-size: 14px; line-height: 1.5; opacity: 0.8; }

.report-section {
  padding: 0;
  cursor: pointer;
}

.section-header {
  padding: 15px 20px;
  display: flex;
  align-items: center;
  background: var(--atp-black);
  color: var(--atp-white);
}

.section-number { font-weight: 900; font-size: 20px; margin-right: 15px; }
.section-title { font-weight: 700; font-size: 14px; flex: 1; }

.section-body { padding: 20px; }

.interface-tabs {
  height: 60px;
  border-bottom: 4px solid var(--atp-black);
  display: flex;
  position: relative;
}

.tab-btn {
  height: 100%;
  padding: 0 30px;
  border: none;
  background: transparent;
  font-weight: 800;
  font-size: 12px;
  border-right: 3px solid var(--atp-black);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
}

.tab-btn.active {
  background: var(--atp-yellow);
}

.agent-dropdown {
  position: absolute;
  top: 64px;
  left: 150px;
  width: 300px;
  z-index: 100;
  padding: 0;
  max-height: 400px;
  overflow-y: auto;
}

.dropdown-header {
  padding: 10px 15px;
  background: var(--atp-black);
  color: var(--atp-white);
  font-weight: 800;
  font-size: 10px;
}

.agent-item {
  padding: 12px 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 2px solid var(--atp-black);
  cursor: pointer;
}

.agent-item:hover { background: var(--atp-blue); color: var(--atp-white); }

.agent-avatar {
  width: 30px;
  height: 30px;
  background: var(--atp-black);
  color: var(--atp-white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  border-radius: 50%;
}

.agent-info { display: flex; flex-direction: column; }
.agent-name { font-weight: 800; font-size: 12px; }
.agent-role { font-size: 10px; opacity: 0.6; }

.chat-viewport {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 30px;
  background: #EEE;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  max-width: 80%;
}

.message-item.user { align-self: flex-end; border-color: var(--atp-blue); }
.message-item.assistant { align-self: flex-start; }

.message-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 800;
}

.sender-tag { color: var(--atp-red); }

.chat-input-area {
  margin-top: 20px;
  background: var(--atp-black);
  padding: 15px;
  display: flex;
  gap: 15px;
}

.chat-input {
  flex: 1;
  background: var(--atp-white);
  border: 4px solid var(--atp-white);
  padding: 12px;
  font-family: inherit;
  font-weight: 600;
  resize: none;
}

.send-btn {
  background: var(--atp-blue);
  color: var(--atp-white);
  border: none;
  padding: 0 30px;
  font-weight: 800;
  cursor: pointer;
}

.survey-viewport {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}

.agent-selection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
  margin: 20px 0;
}

.agent-label {
  border: 2px solid var(--atp-black);
  padding: 8px;
  font-weight: 700;
  font-size: 12px;
  cursor: pointer;
}

.agent-label.checked { background: var(--atp-yellow); }

.submit-survey-btn {
  width: 100%;
  background: var(--atp-red);
  color: var(--atp-white);
  border: none;
  padding: 15px;
  font-weight: 800;
  font-size: 18px;
  cursor: pointer;
  margin-top: 20px;
}

.bauhaus-loader {
  width: 40px;
  height: 40px;
  border: 4px solid var(--atp-black);
  border-top-color: var(--atp-blue);
  animation: spin 1s infinite linear;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-dots span {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: var(--atp-black);
  border-radius: 50%;
  margin-right: 5px;
  animation: bounce 0.6s infinite alternate;
}
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce { to { transform: translateY(-10px); } }
</style>

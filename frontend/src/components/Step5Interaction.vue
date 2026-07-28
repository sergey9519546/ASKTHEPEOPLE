<template>
  <div class="step5-interaction-workbench">
    <!-- Header -->
    <header class="workbench-header">
      <div class="header-left">
        <h1 class="workbench-title">STEP 5: DEEP INTERACTION</h1>
        <p class="workbench-subtitle">
          Engage with simulation agents and report synthesis
        </p>
      </div>
      <div class="header-right">
        <!-- Simulation Dashboard -->
        <div class="sim-dashboard bauhaus-card-mini">
          <div class="dash-item">
            <span class="dash-label">STATUS</span>
            <span class="dash-value" :class="runStatus?.runner_status">{{
              runStatus?.runner_status?.toUpperCase() || "IDLE"
            }}</span>
          </div>
          <div class="dash-item">
            <span class="dash-label">ROUND</span>
            <span class="dash-value"
              >{{ runStatus?.current_round || 0 }}/{{
                runStatus?.total_rounds || "?"
              }}</span
            >
          </div>
          <div class="dash-item">
            <span class="dash-label">ACTIONS</span>
            <span class="dash-value">{{
              runStatus?.total_actions_count || 0
            }}</span>
          </div>
          <button
            v-if="isSimRunning"
            class="abort-btn"
            @click="handleStopSimulation"
            :disabled="isStopping"
          >
            {{ isStopping ? "STOPPING..." : "ABORT_SIM" }}
          </button>
        </div>

        <div class="simulation-badge">
          <span class="badge-label">SIM_ID:</span>
          <span class="badge-value">{{ simulationId || "N/A" }}</span>
        </div>
      </div>
    </header>

    <div class="workbench-layout">
      <!-- Left Panel: Report Context -->
      <aside class="context-panel" ref="leftPanel">
        <div class="panel-header">
          <h2 class="panel-title">REPORT CONTEXT</h2>
          <div class="panel-actions">
            <button
              class="panel-toggle-btn"
              @click="activePanel = 'report'"
              :class="{ active: activePanel === 'report' }"
            >
              REPORT
            </button>
            <button
              class="panel-toggle-btn"
              @click="activePanel = 'activity'"
              :class="{ active: activePanel === 'activity' }"
            >
              ACTIVITY
            </button>
          </div>
        </div>

        <div class="panel-scroll-area">
          <!-- Report Section -->
          <div v-if="activePanel === 'report'" class="report-container">
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
                    'is-collapsed': collapsedSections.has(idx),
                  }"
                >
                  <div
                    class="section-header"
                    @click="toggleSectionCollapse(idx)"
                  >
                    <span class="section-number">{{
                      String(idx + 1).padStart(2, "0")
                    }}</span>
                    <h3 class="section-title">{{ section.title }}</h3>
                    <div class="section-indicator">
                      <span
                        v-if="isSectionCompleted(idx + 1)"
                        class="indicator-done"
                        >DONE</span
                      >
                      <span
                        v-else-if="currentSectionIndex === idx + 1"
                        class="indicator-writing"
                        >WRITING</span
                      >
                      <span v-else class="indicator-pending">PENDING</span>
                    </div>
                  </div>

                  <div
                    v-show="!collapsedSections.has(idx)"
                    class="section-body"
                  >
                    <div
                      v-if="generatedSections[idx + 1]"
                      class="body-content markdown-body"
                      v-html="renderMarkdown(generatedSections[idx + 1])"
                    ></div>
                    <div
                      v-else-if="currentSectionIndex === idx + 1"
                      class="body-loading"
                    >
                      <div class="text-cursor"></div>
                      <p>Synthesizing evidence...</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Activity Section -->
          <div v-if="activePanel === 'activity'" class="activity-container">
            <div class="activity-header">
              <h3 class="panel-subtitle">LIVE_SIM_STREAM</h3>
              <span class="live-dot" :class="{ pulse: isSimRunning }"></span>
            </div>

            <div class="activity-list">
              <div v-if="recentActions.length === 0" class="empty-activity">
                <p>No activity recorded yet...</p>
              </div>
              <div
                v-for="(action, idx) in recentActions"
                :key="idx"
                class="activity-item bauhaus-card-mini"
              >
                <div class="activity-meta">
                  <span class="action-platform" :class="action.platform">{{
                    action.platform.toUpperCase()
                  }}</span>
                  <span class="action-time">{{
                    formatTime(action.timestamp)
                  }}</span>
                </div>
                <div class="action-content">
                  <strong class="agent-name">@{{ action.agent_name }}</strong
                  >:
                  <span class="action-type">{{
                    action.action_type.replace(/_/g, " ")
                  }}</span>
                  <p v-if="action.action_args.text" class="action-text">
                    "{{ truncate(action.action_args.text, 80) }}"
                  </p>
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
            {{
              selectedAgent
                ? selectedAgent.username.toUpperCase()
                : "INDIVIDUAL AGENTS"
            }}
            <span class="dropdown-arrow">▼</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'survey' }"
            @click="selectSurveyTab"
          >
            SURVEY SYSTEM
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'opinion_map' }"
            @click="selectOpinionMapTab"
          >
            OPINION MAP
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
                  <span class="agent-role">{{
                    agent.profession || "SIM_CITIZEN"
                  }}</span>
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
              <p>
                {{
                  chatTarget === "report_agent"
                    ? "Ask the Report Agent for granular insights."
                    : "Directly interview simulation entities."
                }}
              </p>
            </div>

            <div
              v-for="(msg, idx) in chatHistory"
              :key="idx"
              class="message-item bauhaus-card"
              :class="msg.role"
            >
              <div class="message-meta">
                <span class="sender-tag">{{
                  msg.role === "user"
                    ? "USER"
                    : chatTarget === "report_agent"
                      ? "REPORT_AGENT"
                      : selectedAgent?.username.toUpperCase()
                }}</span>
                <span class="message-time">{{
                  formatTime(msg.timestamp)
                }}</span>
              </div>
              <div
                class="message-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>
            </div>

            <div v-if="isSending" class="message-item assistant is-loading">
              <div class="loading-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>

          <div class="chat-input-area">
            <div class="chat-input-row">
              <textarea
                v-model="chatInput"
                class="chat-input"
                placeholder="Enter your query..."
                @keydown.enter.exact.prevent="sendMessage"
                :disabled="
                  isSending || (!selectedAgent && chatTarget === 'agent')
                "
              ></textarea>
              <button
                class="send-btn"
                @click="sendMessage"
                :disabled="!chatInput.trim() || isSending"
              >
                SEND
              </button>
            </div>
            <div v-if="chatTarget === 'agent'" class="chat-controls">
              <label class="bypass-opt-checkbox">
                <input type="checkbox" v-model="bypassPromptOpt" />
                <span>BYPASS PROMPT OPTIMIZATION (RAW MODE)</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Survey Interface -->
        <div v-if="activeTab === 'survey'" class="survey-viewport">
          <div class="survey-setup bauhaus-card">
            <div class="setup-header">
              <h3 class="setup-title">BATCH SURVEY SYSTEM</h3>
              <div class="setup-controls">
                <span class="selected-count"
                  >SELECTED: {{ selectedAgents.size }}</span
                >
                <button
                  v-if="surveyResults.length > 0"
                  class="export-csv-btn"
                  @click="handleExportSurvey"
                  :disabled="isExporting"
                >
                  {{ isExporting ? "EXPORTING..." : "DOWNLOAD_CSV" }}
                </button>
              </div>
            </div>

            <div class="agent-selection-grid">
              <label
                v-for="(agent, idx) in profiles"
                :key="idx"
                class="agent-label"
                :class="{ checked: selectedAgents.has(idx) }"
              >
                <input
                  type="checkbox"
                  :checked="selectedAgents.has(idx)"
                  @change="toggleAgentSelection(idx)"
                />
                {{ agent.username }}
              </label>
            </div>

            <div class="selection-controls">
              <button class="small-btn" @click="selectAllAgents">ALL</button>
              <button class="small-btn" @click="clearAgentSelection">
                NONE
              </button>
            </div>

            <div class="question-area">
              <textarea
                v-model="surveyQuestion"
                class="survey-input"
                placeholder="Enter universal inquiry for selected agents..."
              ></textarea>
              <div class="survey-controls-row">
                <label class="bypass-opt-checkbox dark">
                  <input type="checkbox" v-model="bypassPromptOpt" />
                  <span>BYPASS PROMPT OPTIMIZATION (RAW MODE)</span>
                </label>
                <button
                  class="submit-survey-btn"
                  @click="submitSurvey"
                  :disabled="
                    selectedAgents.size === 0 ||
                    !surveyQuestion.trim() ||
                    isSurveying
                  "
                >
                  DISPATCH SURVEY
                </button>
              </div>
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
              <div
                class="result-body markdown-body"
                v-html="renderMarkdown(res.answer)"
              ></div>
            </div>
          </div>
        </div>

        <!-- Opinion Map Interface -->
        <div v-if="activeTab === 'opinion_map'" class="opinion-map-viewport">
          <OpinionMap :simulationId="simulationId" />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  ref,
  watch,
} from "vue";
import { chatWithReport, getAgentLog } from "../api/report";
import {
  exportSurveyCSV,
  getRunStatusDetail,
  getSimulationProfilesRealtime,
  interviewAgents,
  stopSimulation,
} from "../api/simulation";
import OpinionMap from "./OpinionMap.vue";

const props = defineProps({
  reportId: String,
  simulationId: String,
});

const emit = defineEmits(["add-log", "update-status"]);

// UI State
const activeTab = ref("chat");
const activePanel = ref("report");
const chatTarget = ref("report_agent");
const showAgentDropdown = ref(false);
const selectedAgent = ref(null);
const selectedAgentIndex = ref(null);
const isSending = ref(false);
const isStopping = ref(false);
const isExporting = ref(false);
const chatInput = ref("");
const chatHistory = ref([]);
const chatHistoryCache = reactive({});
const profiles = ref([]);

// Simulation Status
const runStatus = ref(null);
const recentActions = ref([]);
let statusTimer = null;

// Report Data
const reportOutline = ref(null);
const generatedSections = ref({});
const collapsedSections = ref(new Set());
const currentSectionIndex = ref(null);

// Survey State
const selectedAgents = ref(new Set());
const surveyQuestion = ref("");
const surveyResults = ref([]);
const isSurveying = ref(false);
const bypassPromptOpt = ref(false);

const chatMessages = ref(null);

// Computed
const isSimRunning = computed(() => {
  return (
    runStatus.value &&
    ["running", "starting"].includes(runStatus.value.runner_status)
  );
});

// Methods
const addLog = (m) => emit("add-log", m);

const formatTime = (ts) => {
  if (!ts) return "";
  return new Date(ts).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
  });
};

const truncate = (str, len) => {
  if (!str) return "";
  return str.length > len ? str.substring(0, len) + "..." : str;
};

const renderMarkdown = (c) => {
  if (!c) return "";

  // 1. Escaping
  let html = c
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 2. Bold/Italic
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>");
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

  // 3. Lists
  html = html.replace(/^\s*-\s+(.*)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gms, "<ul>$1</ul>");

  // 4. Tables (primitive)
  if (html.includes("|")) {
    const lines = html.split("\n");
    let inTable = false;
    let tableHtml = '<div class="table-wrapper"><table>';

    lines.forEach((line) => {
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        inTable = true;
        const cells = line
          .trim()
          .split("|")
          .filter((c) => c.trim() !== "");
        tableHtml +=
          "<tr>" + cells.map((c) => `<td>${c.trim()}</td>`).join("") + "</tr>";
      } else if (inTable) {
        inTable = false;
        tableHtml += "</table></div>";
      }
    });
    // This is a simple replacement, won't handle multiple tables well but works for reports
    html = html.replace(/(\|.*\|(\n|.)*\|.*\|)/gm, tableHtml);
  }

  // 5. Paragraphs
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");

  return `<div class="md-content"><p>${html}</p></div>`;
};

const isSectionCompleted = (idx) => !!generatedSections.value[idx];

const toggleSectionCollapse = (idx) => {
  const s = new Set(collapsedSections.value);
  if (s.has(idx)) s.delete(idx);
  else s.add(idx);
  collapsedSections.value = s;
};

const pollStatus = async () => {
  if (!props.simulationId) return;
  try {
    const res = await getRunStatusDetail(props.simulationId);
    if (res.success && res.data) {
      runStatus.value = res.data;
      recentActions.value = res.data.recent_actions || [];
    }
  } catch (e) {
    console.error("Status poll error", e);
  }
};

const handleStopSimulation = async () => {
  if (
    !confirm(
      "Are you sure you want to ABORT the current simulation? Data already generated will be saved.",
    )
  )
    return;
  isStopping.value = true;
  try {
    const res = await stopSimulation({ simulation_id: props.simulationId });
    if (res.success) {
      addLog("Simulation stopped by user.");
      await pollStatus();
    }
  } catch (e) {
    addLog(`Error stopping sim: ${e.message}`);
  } finally {
    isStopping.value = false;
  }
};

const handleExportSurvey = async () => {
  if (surveyResults.value.length === 0) return;
  isExporting.value = true;
  try {
    const res = await exportSurveyCSV(props.simulationId, surveyResults.value);
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `ATP_SURVEY_${props.simulationId}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    addLog("Survey results exported to CSV.");
  } catch (e) {
    addLog(`Export error: ${e.message}`);
  } finally {
    isExporting.value = false;
  }
};

const saveChatToCache = () => {
  const key =
    chatTarget.value === "report_agent"
      ? "report"
      : `agent_${selectedAgentIndex.value}`;
  chatHistoryCache[key] = [...chatHistory.value];
};

const selectReportAgentChat = () => {
  saveChatToCache();
  chatTarget.value = "report_agent";
  activeTab.value = "chat";
  chatHistory.value = chatHistoryCache["report"] || [];
  showAgentDropdown.value = false;
};

const toggleAgentDropdown = () => {
  showAgentDropdown.value = !showAgentDropdown.value;
};

const selectAgent = (agent, idx) => {
  saveChatToCache();
  selectedAgent.value = agent;
  selectedAgentIndex.value = idx;
  chatTarget.value = "agent";
  chatHistory.value = chatHistoryCache[`agent_${idx}`] || [];
  showAgentDropdown.value = false;
  activeTab.value = "chat";
};

const selectSurveyTab = () => {
  activeTab.value = "survey";
  showAgentDropdown.value = false;
};

const selectOpinionMapTab = () => {
  activeTab.value = "opinion_map";
  showAgentDropdown.value = false;
};

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessages.value)
      chatMessages.value.scrollTop = chatMessages.value.scrollHeight;
  });
};

const sendMessage = async () => {
  if (!chatInput.value.trim() || isSending.value) return;
  const msg = chatInput.value.trim();
  chatInput.value = "";
  chatHistory.value.push({
    role: "user",
    content: msg,
    timestamp: new Date().toISOString(),
  });
  scrollToBottom();
  isSending.value = true;

  try {
    if (chatTarget.value === "report_agent") {
      const res = await chatWithReport({
        simulation_id: props.simulationId,
        message: msg,
        chat_history: chatHistory.value
          .slice(-6)
          .map((m) => ({ role: m.role, content: m.content })),
      });
      if (res.success) {
        chatHistory.value.push({
          role: "assistant",
          content: res.data.response || res.data.answer,
          timestamp: new Date().toISOString(),
        });
      }
    } else {
      const res = await interviewAgents({
        simulation_id: props.simulationId,
        interviews: [{ agent_id: selectedAgentIndex.value, prompt: msg }],
        bypass_prompt_optimization: bypassPromptOpt.value,
      });
      if (res.success) {
        const results = res.data.result.results;
        const resp =
          results[`reddit_${selectedAgentIndex.value}`]?.response ||
          results[`twitter_${selectedAgentIndex.value}`]?.response;
        chatHistory.value.push({
          role: "assistant",
          content: resp || "No response",
          timestamp: new Date().toISOString(),
        });
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
      interviews: Array.from(selectedAgents.value).map((idx) => ({
        agent_id: idx,
        prompt: surveyQuestion.value.trim(),
      })),
      bypass_prompt_optimization: bypassPromptOpt.value,
    });
    if (res.success) {
      const results = res.data.result.results;
      surveyResults.value = Array.from(selectedAgents.value).map((idx) => {
        const agent = profiles.value[idx];
        const ans =
          results[`reddit_${idx}`]?.response ||
          results[`twitter_${idx}`]?.response ||
          "N/A";
        return {
          agent_name: agent.username,
          profession: agent.profession,
          answer: ans,
        };
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
      logs.forEach((l) => {
        if (l.action === "planning_complete")
          reportOutline.value = l.details.outline;
        if (l.action === "section_complete")
          generatedSections.value[l.section_index] = l.details.content;
      });
    }
    const profRes = await getSimulationProfilesRealtime(
      props.simulationId,
      "reddit",
    );
    if (profRes.success) profiles.value = profRes.data.profiles || [];

    await pollStatus();
  } catch (e) {
    addLog(`Load error: ${e.message}`);
  }
};

onMounted(() => {
  loadData();
  statusTimer = setInterval(pollStatus, 5000);

  const onClick = (e) => {
    if (!e.target.closest(".agent-dropdown") && !e.target.closest(".tab-btn"))
      showAgentDropdown.value = false;
  };
  document.addEventListener("click", onClick);
  onUnmounted(() => {
    document.removeEventListener("click", onClick);
    if (statusTimer) clearInterval(statusTimer);
  });
});

watch(() => props.reportId, loadData);
watch(() => props.simulationId, loadData);
</script>

<style scoped>
.step5-interaction-workbench {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  color: var(--atp-black);
  font-family: var(--font-sans);
  overflow: hidden;
}

.workbench-header {
  height: 60px;
  border-bottom: 1px solid var(--border-color);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
}

.workbench-title {
  font-weight: 700;
  font-size: 16px;
  color: var(--atp-black);
}
.workbench-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  margin-top: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.sim-dashboard {
  display: flex;
  gap: 16px;
  padding: 6px 12px;
  background: #f8fafc;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  align-items: center;
}
.dash-item {
  display: flex;
  flex-direction: column;
}
.dash-label {
  font-size: 8px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
}
.dash-value {
  font-size: 10px;
  font-weight: 700;
}
.dash-value.running {
  color: var(--accent-color);
}
.dash-value.completed {
  color: var(--accent-tertiary);
}
.dash-value.failed {
  color: #64748b;
}

.abort-btn {
  background: #fee2e2;
  color: var(--accent-color);
  border: none;
  font-size: 9px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.abort-btn:hover {
  background: #fecaca;
}

.simulation-badge {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  font-weight: 700;
  font-size: 10px;
  background: #f8fafc;
}

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.context-panel {
  width: 380px;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.panel-header {
  height: 50px;
  border-bottom: 1px solid var(--border-color);
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.8);
}
.panel-title {
  font-weight: 700;
  font-size: 11px;
  color: #475569;
  text-transform: uppercase;
}
.panel-actions {
  display: flex;
  gap: 4px;
}
.panel-toggle-btn {
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: transparent;
  font-size: 9px;
  font-weight: 700;
  padding: 3px 8px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.15s ease;
}
.panel-toggle-btn.active {
  background: #0f172a;
  color: var(--atp-white);
  border-color: #0f172a;
}

.panel-scroll-area {
  flex: 1;
  overflow-y: auto;
}

.report-container,
.activity-container {
  padding: 16px;
}

.activity-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel-subtitle {
  font-weight: 700;
  font-size: 11px;
  color: #475569;
}
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid #ffffff;
  box-shadow: 0 0 0 1.5px #cbd5e1;
}
.live-dot.pulse {
  background: var(--accent-tertiary);
  box-shadow: 0 0 0 1.5px rgba(16, 185, 129, 0.4);
  animation: pulse 1s infinite alternate;
}
@keyframes pulse {
  to {
    transform: scale(1.25);
    opacity: 0.6;
  }
}

.activity-item {
  margin-bottom: 10px;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid var(--border-color);
  border-radius: 6px;
}
.activity-meta {
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  font-weight: 700;
  color: #94a3b8;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.action-platform.twitter {
  color: #1da1f2;
}
.action-platform.reddit {
  color: #ff4500;
}
.action-text {
  margin-top: 4px;
  font-style: italic;
  font-size: 10px;
  color: #475569;
}

.interaction-hub {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.bauhaus-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 16px;
  background: var(--atp-white);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}
.bauhaus-card-mini {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px;
  background: var(--atp-white);
}

.interface-tabs {
  height: 50px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  position: relative;
  background: #ffffff;
}
.tab-btn {
  height: 100%;
  padding: 0 20px;
  border: none;
  background: transparent;
  font-weight: 700;
  font-size: 11px;
  color: #64748b;
  border-right: 1px solid var(--border-color);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.15s ease;
}
.tab-btn:hover {
  background: #f8fafc;
  color: var(--atp-black);
}
.tab-btn.active {
  background: #f8fafc;
  color: var(--atp-black);
}

.chat-viewport {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
  background: #f8fafc;
}
.messages-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.message-item {
  max-width: 75%;
}
.message-item.user {
  align-self: flex-end;
  background: #ffffff;
  border-color: #cbd5e1;
}
.message-item.assistant {
  align-self: flex-start;
  background: #ffffff;
}

.chat-input-area {
  margin-top: 16px;
  background: #ffffff;
  border-top: 1px solid var(--border-color);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.chat-input-row {
  display: flex;
  gap: 12px;
}
.chat-input {
  flex: 1;
  background: #f8fafc;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px;
  resize: none;
  font-size: 12px;
  outline: none;
}
.chat-input:focus {
  border-color: #cbd5e1;
  background: #ffffff;
}
.send-btn {
  background: #0f172a;
  color: var(--atp-white);
  border: none;
  padding: 0 20px;
  font-weight: 700;
  font-size: 11px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
}
.send-btn:hover {
  background: #1e293b;
}

.survey-viewport {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
.setup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.setup-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}
.export-csv-btn {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid var(--border-color);
  font-size: 9px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.export-csv-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.agent-selection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
  margin: 16px 0;
}
.agent-label {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px;
  font-weight: 600;
  font-size: 11px;
  cursor: pointer;
  background: #ffffff;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.agent-label:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}
.agent-label.checked {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #2563eb;
}

.submit-survey-btn {
  width: 100%;
  background: #0f172a;
  color: var(--atp-white);
  border: none;
  padding: 12px;
  font-weight: 700;
  font-size: 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  margin-top: 16px;
  transition: background 0.15s ease;
}
.submit-survey-btn:hover {
  background: #1e293b;
}

.bauhaus-loader {
  width: 24px;
  height: 24px;
  border: 2px solid #f1f5f9;
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-dots span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #cbd5e1;
  border-radius: 50%;
  margin-right: 4px;
  animation: bounce 0.6s infinite alternate;
}
.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}
.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes bounce {
  to {
    transform: translateY(-6px);
  }
}

.opinion-map-viewport {
  flex: 1;
  padding: 24px;
  background: #ffffff;
  overflow: hidden;
}

/* Markdown Styles */
.md-content ul {
  padding-left: 16px;
  margin: 8px 0;
}
.md-content li {
  margin-bottom: 4px;
}
.table-wrapper {
  overflow-x: auto;
  margin: 12px 0;
  border: 1px solid var(--border-color);
  border-radius: 6px;
}
.table-wrapper table {
  width: 100%;
  border-collapse: collapse;
}
.table-wrapper td {
  padding: 6px 10px;
  border: 1px solid #f1f5f9;
  font-size: 11px;
}
.table-wrapper tr:nth-child(even) {
  background: #f8fafc;
}

.chat-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bypass-opt-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.bypass-opt-checkbox.dark {
  color: var(--atp-black);
}

.bypass-opt-checkbox input {
  cursor: pointer;
  accent-color: var(--accent-color);
}

.survey-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.survey-controls-row .submit-survey-btn {
  margin-top: 0;
  width: auto;
  min-width: 200px;
}
</style>

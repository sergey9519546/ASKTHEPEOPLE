<template>
  <div class="interaction-panel">
    <!-- Main Split Layout -->
    <div class="main-split-layout">
      <!-- LEFT PANEL: Report Style -->
      <div class="left-panel report-style" ref="leftPanel">
        <div v-if="reportOutline" class="report-content-wrapper">
          <!-- Report Header -->
          <div class="report-header-block">
            <div class="report-meta">
              <span class="report-tag">Prediction Report</span>
              <span class="report-id"
                >ID: {{ reportId || "REF-2024-X92" }}</span
              >
            </div>
            <h1 class="main-title">{{ reportOutline.title }}</h1>
            <p class="sub-title">{{ reportOutline.summary }}</p>
            <div class="header-divider"></div>
          </div>

          <!-- Sections List -->
          <div class="sections-list">
            <div
              v-for="(section, idx) in reportOutline.sections"
              :key="idx"
              class="report-section-item"
              :class="{
                'is-active': currentSectionIndex === idx + 1,
                'is-completed': isSectionCompleted(idx + 1),
                'is-pending':
                  !isSectionCompleted(idx + 1) &&
                  currentSectionIndex !== idx + 1,
              }"
            >
              <div
                class="section-header-row"
                @click="toggleSectionCollapse(idx)"
                :class="{ clickable: isSectionCompleted(idx + 1) }"
              >
                <span class="section-number">{{
                  String(idx + 1).padStart(2, "0")
                }}</span>
                <h3 class="section-title">{{ section.title }}</h3>
                <svg
                  v-if="isSectionCompleted(idx + 1)"
                  class="collapse-icon"
                  :class="{ 'is-collapsed': collapsedSections.has(idx) }"
                  viewBox="0 0 24 24"
                  width="20"
                  height="20"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>

              <div class="section-body" v-show="!collapsedSections.has(idx)">
                <!-- Completed Content -->
                <div
                  v-if="generatedSections[idx + 1]"
                  class="generated-content"
                  v-html="renderMarkdown(generatedSections[idx + 1])"
                ></div>

                <!-- Loading State -->
                <div
                  v-else-if="currentSectionIndex === idx + 1"
                  class="loading-state"
                >
                  <div class="loading-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <circle
                        cx="12"
                        cy="12"
                        r="10"
                        stroke-width="4"
                        stroke="#E5E7EB"
                      ></circle>
                      <path
                        d="M12 2a10 10 0 0 1 10 10"
                        stroke-width="4"
                        stroke="#4B5563"
                        stroke-linecap="round"
                      ></path>
                    </svg>
                  </div>
                  <span class="loading-text"
                    >正在生成{{ section.title }}...</span
                  >
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Waiting State -->
        <div v-if="!reportOutline" class="waiting-placeholder">
          <div class="waiting-animation">
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
          </div>
          <span class="waiting-text">Waiting for Report Agent...</span>
        </div>
      </div>

      <!-- RIGHT PANEL: Interaction Interface -->
      <div class="right-panel" ref="rightPanel">
        <!-- Unified Action Bar - Professional Design -->
        <div class="action-bar">
          <div class="action-bar-header">
            <svg
              class="action-bar-icon"
              viewBox="0 0 24 24"
              width="28"
              height="28"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
              ></path>
            </svg>
            <div class="action-bar-text">
              <span class="action-bar-title">Interactive Tools</span>
              <span class="action-bar-subtitle mono"
                >{{ profiles.length }} agents available</span
              >
            </div>
          </div>
          <div class="action-bar-tabs">
            <button
              class="tab-pill"
              :class="{
                active: activeTab === 'chat' && chatTarget === 'report_agent',
              }"
              @click="selectReportAgentChat"
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
                ></path>
              </svg>
              <span>与Report Agent对话</span>
            </button>
            <div class="agent-dropdown" v-if="profiles.length > 0">
              <button
                class="tab-pill agent-pill"
                :class="{
                  active: activeTab === 'chat' && chatTarget === 'agent',
                }"
                @click="toggleAgentDropdown"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span>{{
                  selectedAgent
                    ? selectedAgent.username
                    : "与世界中任意个体对话"
                }}</span>
                <svg
                  class="dropdown-arrow"
                  :class="{ open: showAgentDropdown }"
                  viewBox="0 0 24 24"
                  width="12"
                  height="12"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
              <div v-if="showAgentDropdown" class="dropdown-menu">
                <div class="dropdown-header">选择对话对象</div>
                <div
                  v-for="(agent, idx) in profiles"
                  :key="idx"
                  class="dropdown-item"
                  @click="selectAgent(agent, idx)"
                >
                  <div class="agent-avatar">
                    {{ (agent.username || "A")[0] }}
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ agent.username }}</span>
                    <span class="agent-role">{{
                      agent.profession || "未知职业"
                    }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="tab-divider"></div>
            <button
              class="tab-pill survey-pill"
              :class="{ active: activeTab === 'survey' }"
              @click="selectSurveyTab"
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M9 11l3 3L22 4"></path>
                <path
                  d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"
                ></path>
              </svg>
              <span>发送问卷调查到世界中</span>
            </button>
          </div>
        </div>

        <!-- Chat Mode -->
        <div v-if="activeTab === 'chat'" class="chat-container">
          <!-- Report Agent Tools Card -->
          <div
            v-if="chatTarget === 'report_agent'"
            class="report-agent-tools-card"
          >
            <div class="tools-card-header">
              <div class="tools-card-avatar">R</div>
              <div class="tools-card-info">
                <div class="tools-card-name">Report Agent - Chat</div>
                <div class="tools-card-subtitle">
                  Quick-chat version of the Report Agent with 4 specialized
                  tools and full ASKTHEPEOPLE simulation memory
                </div>
              </div>
              <button
                class="tools-card-toggle"
                @click="showToolsDetail = !showToolsDetail"
              >
                <svg
                  :class="{ 'is-expanded': showToolsDetail }"
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
            </div>
            <div v-if="showToolsDetail" class="tools-card-body">
              <div class="tools-grid">
                <div class="tool-item tool-purple">
                  <div class="tool-icon-wrapper">
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.5V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.5A7 7 0 0 0 12 2z"
                      ></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">InsightForge 深度归因</div>
                    <div class="tool-desc">
                      对齐现实世界种子数据与模拟环境状态，结合Global/Local
                      Memory机制，提供跨时空的深度归因分析
                    </div>
                  </div>
                </div>
                <div class="tool-item tool-blue">
                  <div class="tool-icon-wrapper">
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <circle cx="12" cy="12" r="10"></circle>
                      <path
                        d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
                      ></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">PanoramaSearch 全景追踪</div>
                    <div class="tool-desc">
                      基于图结构的广度遍历算法，重构事件传播路径，捕获全量信息流动的拓扑结构
                    </div>
                  </div>
                </div>
                <div class="tool-item tool-orange">
                  <div class="tool-icon-wrapper">
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polygon
                        points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"
                      ></polygon>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">QuickSearch 快速检索</div>
                    <div class="tool-desc">
                      基于 GraphRAG
                      的即时查询接口，优化索引效率，用于快速提取具体的节点属性与离散事实
                    </div>
                  </div>
                </div>
                <div class="tool-item tool-green">
                  <div class="tool-icon-wrapper">
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"
                      ></path>
                      <circle cx="9" cy="7" r="4"></circle>
                      <path
                        d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"
                      ></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">InterviewSubAgent 虚拟访谈</div>
                    <div class="tool-desc">
                      自主式访谈，能够并行与模拟世界中个体进行多轮对话，采集非结构化的观点数据与心理状态
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Agent Profile Card -->
          <div
            v-if="chatTarget === 'agent' && selectedAgent"
            class="agent-profile-card"
          >
            <div class="profile-card-header">
              <div class="profile-card-avatar">
                {{ (selectedAgent.username || "A")[0] }}
              </div>
              <div class="profile-card-info">
                <div class="profile-card-name">
                  {{ selectedAgent.username }}
                </div>
                <div class="profile-card-meta">
                  <span v-if="selectedAgent.name" class="profile-card-handle"
                    >@{{ selectedAgent.name }}</span
                  >
                  <span class="profile-card-profession">{{
                    selectedAgent.profession || "未知职业"
                  }}</span>
                </div>
              </div>
              <button
                class="profile-card-toggle"
                @click="showFullProfile = !showFullProfile"
              >
                <svg
                  :class="{ 'is-expanded': showFullProfile }"
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
            </div>
            <div
              v-if="showFullProfile && selectedAgent.bio"
              class="profile-card-body"
            >
              <div class="profile-card-bio">
                <div class="profile-card-label">简介</div>
                <p>{{ selectedAgent.bio }}</p>
              </div>
            </div>
          </div>

          <!-- Chat Messages -->
          <div class="chat-messages" ref="chatMessages">
            <div v-if="chatHistory.length === 0" class="chat-empty">
              <div class="empty-icon">
                <svg
                  viewBox="0 0 24 24"
                  width="48"
                  height="48"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path
                    d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
                  ></path>
                </svg>
              </div>
              <p class="empty-text">
                {{
                  chatTarget === "report_agent"
                    ? "与 Report Agent 对话，深入了解报告内容"
                    : "与模拟个体对话，了解他们的观点"
                }}
              </p>
            </div>
            <div
              v-for="(msg, idx) in chatHistory"
              :key="idx"
              class="chat-message"
              :class="msg.role"
            >
              <div class="message-avatar">
                <span v-if="msg.role === 'user'">U</span>
                <span v-else>{{
                  msg.role === "assistant" && chatTarget === "report_agent"
                    ? "R"
                    : selectedAgent?.username?.[0] || "A"
                }}</span>
              </div>
              <div class="message-content">
                <div class="message-header">
                  <span class="sender-name">
                    {{
                      msg.role === "user"
                        ? "You"
                        : chatTarget === "report_agent"
                          ? "Report Agent"
                          : selectedAgent?.username || "Agent"
                    }}
                  </span>
                  <span class="message-time">{{
                    formatTime(msg.timestamp)
                  }}</span>
                </div>
                <div
                  class="message-text"
                  v-html="renderMarkdown(msg.content)"
                ></div>
              </div>
            </div>
            <div v-if="isSending" class="chat-message assistant">
              <div class="message-avatar">
                <span>{{
                  chatTarget === "report_agent"
                    ? "R"
                    : selectedAgent?.username?.[0] || "A"
                }}</span>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Chat Input -->
          <div class="chat-input-area">
            <textarea
              v-model="chatInput"
              class="chat-input"
              placeholder="输入您的问题..."
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="
                isSending || (!selectedAgent && chatTarget === 'agent')
              "
              rows="1"
              ref="chatInputRef"
            ></textarea>
            <button
              class="send-btn"
              @click="sendMessage"
              :disabled="
                !chatInput.trim() ||
                isSending ||
                (!selectedAgent && chatTarget === 'agent')
              "
            >
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>

        <!-- Survey Mode -->
        <div v-if="activeTab === 'survey'" class="survey-container">
          <!-- Survey Setup -->
          <div class="survey-setup">
            <div class="setup-section">
              <div class="section-header">
                <span class="section-title">选择调查对象</span>
                <span class="selection-count"
                  >已选 {{ selectedAgents.size }} / {{ profiles.length }}</span
                >
              </div>
              <div class="agents-grid">
                <label
                  v-for="(agent, idx) in profiles"
                  :key="idx"
                  class="agent-checkbox"
                  :class="{ checked: selectedAgents.has(idx) }"
                >
                  <input
                    type="checkbox"
                    :checked="selectedAgents.has(idx)"
                    @change="toggleAgentSelection(idx)"
                  />
                  <div class="checkbox-avatar">
                    {{ (agent.username || "A")[0] }}
                  </div>
                  <div class="checkbox-info">
                    <span class="checkbox-name">{{ agent.username }}</span>
                    <span class="checkbox-role">{{
                      agent.profession || "未知职业"
                    }}</span>
                  </div>
                  <div class="checkbox-indicator">
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="3"
                    >
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                  </div>
                </label>
              </div>
              <div class="selection-actions">
                <button class="action-link" @click="selectAllAgents">
                  全选
                </button>
                <span class="action-divider">|</span>
                <button class="action-link" @click="clearAgentSelection">
                  清空
                </button>
              </div>
            </div>

            <div class="setup-section">
              <div class="section-header">
                <span class="section-title">问卷问题</span>
              </div>
              <textarea
                v-model="surveyQuestion"
                class="survey-input"
                placeholder="输入您想问所有被选中对象的问题..."
                rows="3"
              ></textarea>
            </div>

            <button
              class="survey-submit-btn"
              :disabled="
                selectedAgents.size === 0 ||
                !surveyQuestion.trim() ||
                isSurveying
              "
              @click="submitSurvey"
            >
              <span v-if="isSurveying" class="loading-spinner"></span>
              <span v-else>发送问卷</span>
            </button>
          </div>

          <!-- Survey Results -->
          <div v-if="surveyResults.length > 0" class="survey-results">
            <div class="results-header">
              <span class="results-title">调查结果</span>
              <span class="results-count"
                >{{ surveyResults.length }} 条回复</span
              >
            </div>
            <div class="results-list">
              <div
                v-for="(result, idx) in surveyResults"
                :key="idx"
                class="result-card"
              >
                <div class="result-header">
                  <div class="result-avatar">
                    {{ (result.agent_name || "A")[0] }}
                  </div>
                  <div class="result-info">
                    <span class="result-name">{{ result.agent_name }}</span>
                    <span class="result-role">{{
                      result.profession || "未知职业"
                    }}</span>
                  </div>
                </div>
                <div class="result-question">
                  <svg
                    viewBox="0 0 24 24"
                    width="14"
                    height="14"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                  <span>{{ result.question }}</span>
                </div>
                <div
                  class="result-answer"
                  v-html="renderMarkdown(result.answer)"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { chatWithReport, getReport, getAgentLog } from "../api/report";
import {
  interviewAgents,
  getSimulationProfilesRealtime,
} from "../api/simulation";

const props = defineProps({
  reportId: String,
  simulationId: String,
});

const emit = defineEmits(["add-log", "update-status"]);

// State
const activeTab = ref("chat");
const chatTarget = ref("report_agent");
const showAgentDropdown = ref(false);
const selectedAgent = ref(null);
const selectedAgentIndex = ref(null);
const showFullProfile = ref(true);
const showToolsDetail = ref(true);

// Chat State
const chatInput = ref("");
const chatHistory = ref([]);
const chatHistoryCache = ref({}); // 缓存所有对话记录: { 'report_agent': [], 'agent_0': [], 'agent_1': [], ... }
const isSending = ref(false);
const chatMessages = ref(null);
const chatInputRef = ref(null);

// Survey State
const selectedAgents = ref(new Set());
const surveyQuestion = ref("");
const surveyResults = ref([]);
const isSurveying = ref(false);

// Report Data
const reportOutline = ref(null);
const generatedSections = ref({});
const collapsedSections = ref(new Set());
const currentSectionIndex = ref(null);
const profiles = ref([]);

// Helper Methods
const isSectionCompleted = (sectionIndex) => {
  return !!generatedSections.value[sectionIndex];
};

// Refs
const leftPanel = ref(null);
const rightPanel = ref(null);

// Methods
const addLog = (msg) => {
  emit("add-log", msg);
};

const toggleSectionCollapse = (idx) => {
  if (!generatedSections.value[idx + 1]) return;
  const newSet = new Set(collapsedSections.value);
  if (newSet.has(idx)) {
    newSet.delete(idx);
  } else {
    newSet.add(idx);
  }
  collapsedSections.value = newSet;
};

const selectChatTarget = (target) => {
  chatTarget.value = target;
  if (target === "report_agent") {
    showAgentDropdown.value = false;
  }
};

// 保存当前对话记录到缓存
const saveChatHistory = () => {
  if (chatHistory.value.length === 0) return;

  if (chatTarget.value === "report_agent") {
    chatHistoryCache.value["report_agent"] = [...chatHistory.value];
  } else if (selectedAgentIndex.value !== null) {
    chatHistoryCache.value[`agent_${selectedAgentIndex.value}`] = [
      ...chatHistory.value,
    ];
  }
};

const selectReportAgentChat = () => {
  // 保存当前对话记录
  saveChatHistory();

  activeTab.value = "chat";
  chatTarget.value = "report_agent";
  selectedAgent.value = null;
  selectedAgentIndex.value = null;
  showAgentDropdown.value = false;

  // 恢复 Report Agent 的对话记录
  chatHistory.value = chatHistoryCache.value["report_agent"] || [];
};

const selectSurveyTab = () => {
  activeTab.value = "survey";
  selectedAgent.value = null;
  selectedAgentIndex.value = null;
  showAgentDropdown.value = false;
};

const toggleAgentDropdown = () => {
  showAgentDropdown.value = !showAgentDropdown.value;
  if (showAgentDropdown.value) {
    activeTab.value = "chat";
    chatTarget.value = "agent";
  }
};

const selectAgent = (agent, idx) => {
  // 保存当前对话记录
  saveChatHistory();

  selectedAgent.value = agent;
  selectedAgentIndex.value = idx;
  chatTarget.value = "agent";
  showAgentDropdown.value = false;

  // 恢复该 Agent 的对话记录
  chatHistory.value = chatHistoryCache.value[`agent_${idx}`] || [];
  addLog(`选择对话对象: ${agent.username}`);
};

const formatTime = (timestamp) => {
  if (!timestamp) return "";
  try {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
};

const renderMarkdown = (content) => {
  if (!content) return "";

  let processedContent = content.replace(/^##\s+.+\n+/, "");
  let html = processedContent.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    '<pre class="code-block"><code>$2</code></pre>',
  );
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>');
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>');
  html = html.replace(
    /^> (.+)$/gm,
    '<blockquote class="md-quote">$1</blockquote>',
  );

  // 处理列表 - 支持子列表
  html = html.replace(/^(\s*)- (.+)$/gm, (match, indent, text) => {
    const level = Math.floor(indent.length / 2);
    return `<li class="md-li" data-level="${level}">${text}</li>`;
  });
  html = html.replace(/^(\s*)(\d+)\. (.+)$/gm, (match, indent, num, text) => {
    const level = Math.floor(indent.length / 2);
    return `<li class="md-oli" data-level="${level}">${text}</li>`;
  });

  // 包装无序列表
  html = html.replace(
    /(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g,
    '<ul class="md-ul">$&</ul>',
  );
  // 包装有序列表
  html = html.replace(
    /(<li class="md-oli"[^>]*>.*?<\/li>\s*)+/g,
    '<ol class="md-ol">$&</ol>',
  );

  // 清理列表项之间的所有空白
  html = html.replace(/<\/li>\s+<li/g, "</li><li");
  // 清理列表开始标签后的空白
  html = html.replace(/<ul class="md-ul">\s+/g, '<ul class="md-ul">');
  html = html.replace(/<ol class="md-ol">\s+/g, '<ol class="md-ol">');
  // 清理列表结束标签前的空白
  html = html.replace(/\s+<\/ul>/g, "</ul>");
  html = html.replace(/\s+<\/ol>/g, "</ol>");

  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  html = html.replace(/_(.+?)_/g, "<em>$1</em>");
  html = html.replace(/^---$/gm, '<hr class="md-hr">');
  html = html.replace(/\n\n/g, '</p><p class="md-p">');
  html = html.replace(/\n/g, "<br>");
  html = '<p class="md-p">' + html + "</p>";
  html = html.replace(/<p class="md-p"><\/p>/g, "");
  html = html.replace(/<p class="md-p">(<h[2-5])/g, "$1");
  html = html.replace(/(<\/h[2-5]>)<\/p>/g, "$1");
  html = html.replace(/<p class="md-p">(<ul|<ol|<blockquote|<pre|<hr)/g, "$1");
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, "$1");
  // 清理块级元素前后的 <br> 标签
  html = html.replace(/<br>\s*(<ul|<ol|<blockquote)/g, "$1");
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>)\s*<br>/g, "$1");
  // 清理 <p><br> 紧跟块级元素的情况（多余空行导致）
  html = html.replace(
    /<p class="md-p">(<br>\s*)+(<ul|<ol|<blockquote|<pre|<hr)/g,
    "$2",
  );
  // 清理连续的 <br> 标签
  html = html.replace(/(<br>\s*){2,}/g, "<br>");
  // 清理块级元素后紧跟的段落开始标签前的 <br>
  html = html.replace(/(<\/ol>|<\/ul>|<\/blockquote>)<br>(<p|<div)/g, "$1$2");

  // 修复非连续有序列表的编号：当单项 <ol> 被段落内容隔开时，保持编号递增
  const tokens = html.split(
    /(<ol class="md-ol">(?:<li class="md-oli"[^>]*>[\s\S]*?<\/li>)+<\/ol>)/g,
  );
  let olCounter = 0;
  let inSequence = false;
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].startsWith('<ol class="md-ol">')) {
      const liCount = (tokens[i].match(/<li class="md-oli"/g) || []).length;
      if (liCount === 1) {
        olCounter++;
        if (olCounter > 1) {
          tokens[i] = tokens[i].replace(
            '<ol class="md-ol">',
            `<ol class="md-ol" start="${olCounter}">`,
          );
        }
        inSequence = true;
      } else {
        olCounter = 0;
        inSequence = false;
      }
    } else if (inSequence) {
      if (/<h[2-5]/.test(tokens[i])) {
        olCounter = 0;
        inSequence = false;
      }
    }
  }
  html = tokens.join("");

  return html;
};

// Chat Methods
const sendMessage = async () => {
  if (!chatInput.value.trim() || isSending.value) return;

  const message = chatInput.value.trim();
  chatInput.value = "";

  // Add user message
  chatHistory.value.push({
    role: "user",
    content: message,
    timestamp: new Date().toISOString(),
  });

  scrollToBottom();
  isSending.value = true;

  try {
    if (chatTarget.value === "report_agent") {
      await sendToReportAgent(message);
    } else {
      await sendToAgent(message);
    }
  } catch (err) {
    addLog(`发送失败: ${err.message}`);
    chatHistory.value.push({
      role: "assistant",
      content: `抱歉，发生了错误: ${err.message}`,
      timestamp: new Date().toISOString(),
    });
  } finally {
    isSending.value = false;
    scrollToBottom();
    // 自动保存对话记录到缓存
    saveChatHistory();
  }
};

const sendToReportAgent = async (message) => {
  addLog(`向 Report Agent 发送: ${message.substring(0, 50)}...`);

  // Build chat history for API
  const historyForApi = chatHistory.value
    .filter((msg) => msg.role !== "user" || msg.content !== message)
    .slice(-10) // Keep last 10 messages
    .map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

  const res = await chatWithReport({
    simulation_id: props.simulationId,
    message: message,
    chat_history: historyForApi,
  });

  if (res.success && res.data) {
    chatHistory.value.push({
      role: "assistant",
      content: res.data.response || res.data.answer || "无响应",
      timestamp: new Date().toISOString(),
    });
    addLog("Report Agent 已回复");
  } else {
    throw new Error(res.error || "请求失败");
  }
};

const sendToAgent = async (message) => {
  if (!selectedAgent.value || selectedAgentIndex.value === null) {
    throw new Error("请先选择一个模拟个体");
  }

  addLog(
    `向 ${selectedAgent.value.username} 发送: ${message.substring(0, 50)}...`,
  );

  // Build prompt with chat history
  let prompt = message;
  if (chatHistory.value.length > 1) {
    const historyContext = chatHistory.value
      .filter((msg) => msg.content !== message)
      .slice(-6)
      .map((msg) => `${msg.role === "user" ? "提问者" : "你"}：${msg.content}`)
      .join("\n");
    prompt = `以下是我们之前的对话：\n${historyContext}\n\n现在我的新问题是：${message}`;
  }

  const res = await interviewAgents({
    simulation_id: props.simulationId,
    interviews: [
      {
        agent_id: selectedAgentIndex.value,
        prompt: prompt,
      },
    ],
  });

  if (res.success && res.data) {
    // 正确的数据路径: res.data.result.results 是一个对象字典
    // 格式: {"twitter_0": {...}, "reddit_0": {...}} 或单平台 {"reddit_0": {...}}
    const resultData = res.data.result || res.data;
    const resultsDict = resultData.results || resultData;

    // 将对象字典转换为数组，优先获取 reddit 平台的回复
    let responseContent = null;
    const agentId = selectedAgentIndex.value;

    if (typeof resultsDict === "object" && !Array.isArray(resultsDict)) {
      // 优先使用 reddit 平台回复，其次 twitter
      const redditKey = `reddit_${agentId}`;
      const twitterKey = `twitter_${agentId}`;
      const agentResult =
        resultsDict[redditKey] ||
        resultsDict[twitterKey] ||
        Object.values(resultsDict)[0];
      if (agentResult) {
        responseContent = agentResult.response || agentResult.answer;
      }
    } else if (Array.isArray(resultsDict) && resultsDict.length > 0) {
      // 兼容数组格式
      responseContent = resultsDict[0].response || resultsDict[0].answer;
    }

    if (responseContent) {
      chatHistory.value.push({
        role: "assistant",
        content: responseContent,
        timestamp: new Date().toISOString(),
      });
      addLog(`${selectedAgent.value.username} 已回复`);
    } else {
      throw new Error("无响应数据");
    }
  } else {
    throw new Error(res.error || "请求失败");
  }
};

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessages.value) {
      chatMessages.value.scrollTop = chatMessages.value.scrollHeight;
    }
  });
};

// Survey Methods
const toggleAgentSelection = (idx) => {
  const newSet = new Set(selectedAgents.value);
  if (newSet.has(idx)) {
    newSet.delete(idx);
  } else {
    newSet.add(idx);
  }
  selectedAgents.value = newSet;
};

const selectAllAgents = () => {
  const newSet = new Set();
  profiles.value.forEach((_, idx) => newSet.add(idx));
  selectedAgents.value = newSet;
};

const clearAgentSelection = () => {
  selectedAgents.value = new Set();
};

const submitSurvey = async () => {
  if (selectedAgents.value.size === 0 || !surveyQuestion.value.trim()) return;

  isSurveying.value = true;
  addLog(`发送问卷给 ${selectedAgents.value.size} 个对象...`);

  try {
    const interviews = Array.from(selectedAgents.value).map((idx) => ({
      agent_id: idx,
      prompt: surveyQuestion.value.trim(),
    }));

    const res = await interviewAgents({
      simulation_id: props.simulationId,
      interviews: interviews,
    });

    if (res.success && res.data) {
      // 正确的数据路径: res.data.result.results 是一个对象字典
      // 格式: {"twitter_0": {...}, "reddit_0": {...}, "twitter_1": {...}, ...}
      const resultData = res.data.result || res.data;
      const resultsDict = resultData.results || resultData;

      // 将对象字典转换为数组格式
      const surveyResultsList = [];

      for (const interview of interviews) {
        const agentIdx = interview.agent_id;
        const agent = profiles.value[agentIdx];

        // 优先使用 reddit 平台回复，其次 twitter
        let responseContent = "无响应";

        if (typeof resultsDict === "object" && !Array.isArray(resultsDict)) {
          const redditKey = `reddit_${agentIdx}`;
          const twitterKey = `twitter_${agentIdx}`;
          const agentResult = resultsDict[redditKey] || resultsDict[twitterKey];
          if (agentResult) {
            responseContent =
              agentResult.response || agentResult.answer || "无响应";
          }
        } else if (Array.isArray(resultsDict)) {
          // 兼容数组格式
          const matchedResult = resultsDict.find(
            (r) => r.agent_id === agentIdx,
          );
          if (matchedResult) {
            responseContent =
              matchedResult.response || matchedResult.answer || "无响应";
          }
        }

        surveyResultsList.push({
          agent_id: agentIdx,
          agent_name: agent?.username || `Agent ${agentIdx}`,
          profession: agent?.profession,
          question: surveyQuestion.value.trim(),
          answer: responseContent,
        });
      }

      surveyResults.value = surveyResultsList;
      addLog(`收到 ${surveyResults.value.length} 条回复`);
    } else {
      throw new Error(res.error || "请求失败");
    }
  } catch (err) {
    addLog(`问卷发送失败: ${err.message}`);
  } finally {
    isSurveying.value = false;
  }
};

// Load Report Data
const loadReportData = async () => {
  if (!props.reportId) return;

  try {
    addLog(`加载报告数据: ${props.reportId}`);

    // Get report info
    const reportRes = await getReport(props.reportId);
    if (reportRes.success && reportRes.data) {
      // Load agent logs to get report outline and sections
      await loadAgentLogs();
    }
  } catch (err) {
    addLog(`加载报告失败: ${err.message}`);
  }
};

const loadAgentLogs = async () => {
  if (!props.reportId) return;

  try {
    const res = await getAgentLog(props.reportId, 0);
    if (res.success && res.data) {
      const logs = res.data.logs || [];

      logs.forEach((log) => {
        if (log.action === "planning_complete" && log.details?.outline) {
          reportOutline.value = log.details.outline;
        }

        if (
          log.action === "section_complete" &&
          log.section_index < 100 &&
          log.details?.content
        ) {
          generatedSections.value[log.section_index] = log.details.content;
        }
      });

      addLog("报告数据加载完成");
    }
  } catch (err) {
    addLog(`加载报告日志失败: ${err.message}`);
  }
};

const loadProfiles = async () => {
  if (!props.simulationId) return;

  try {
    const res = await getSimulationProfilesRealtime(
      props.simulationId,
      "reddit",
    );
    if (res.success && res.data) {
      profiles.value = res.data.profiles || [];
      addLog(`加载了 ${profiles.value.length} 个模拟个体`);
    }
  } catch (err) {
    addLog(`加载模拟个体失败: ${err.message}`);
  }
};

// Click outside to close dropdown
const handleClickOutside = (e) => {
  const dropdown = document.querySelector(".agent-dropdown");
  if (dropdown && !dropdown.contains(e.target)) {
    showAgentDropdown.value = false;
  }
};

// Lifecycle
onMounted(() => {
  addLog("Step5 深度互动初始化");
  loadReportData();
  loadProfiles();
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});

watch(
  () => props.reportId,
  (newId) => {
    if (newId) {
      loadReportData();
    }
  },
  { immediate: true },
);

watch(
  () => props.simulationId,
  (newId) => {
    if (newId) {
      loadProfiles();
    }
  },
  { immediate: true },
);
</script>

<style scoped>
.interaction-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bauhaus-cream);
  font-family: 'Space Grotesk', sans-serif;
  overflow: hidden;
}

/* Main Split Layout */
.main-split-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  border-top: 4px solid var(--bauhaus-black);
}

/* Left Panel - Report Style */
.left-panel.report-style {
  width: 45%;
  background: var(--bauhaus-cream);
  border-right: 4px solid var(--bauhaus-black);
  overflow-y: auto;
  padding: 40px;
}

.left-panel::-webkit-scrollbar { width: 8px; }
.left-panel::-webkit-scrollbar-track { background: var(--bauhaus-cream); }
.left-panel::-webkit-scrollbar-thumb { 
  background: var(--bauhaus-black);
  border: 2px solid var(--bauhaus-cream);
}

/* Report Header */
.report-content-wrapper {
  max-width: 900px;
  margin: 0 auto;
}

.report-header-block {
  margin-bottom: 40px;
  border: 4px solid var(--bauhaus-black);
  padding: 30px;
  background: #fff;
  position: relative;
}

.report-header-block::after {
  content: '';
  position: absolute;
  top: 10px;
  left: 10px;
  right: -10px;
  bottom: -10px;
  background: var(--bauhaus-blue);
  z-index: -1;
}

.report-tag {
  background: var(--bauhaus-red);
  color: white;
  padding: 4px 12px;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 12px;
  display: inline-block;
}

.report-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--bauhaus-black);
  margin-left: 10px;
}

.main-title {
  font-size: 36px;
  font-weight: 800;
  color: var(--bauhaus-black);
  margin: 15px 0 10px 0;
  line-height: 1.1;
  text-transform: uppercase;
}

.sub-title {
  font-size: 16px;
  color: var(--bauhaus-black);
  margin: 0;
  font-weight: 500;
  line-height: 1.4;
}

/* Sections List */
.sections-list {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.report-section-item {
  border: 4px solid var(--bauhaus-black);
  background: white;
  transition: all 0.2s;
}

.report-section-item.is-active {
  border-color: var(--bauhaus-red);
  box-shadow: 8px 8px 0 var(--bauhaus-black);
  transform: translate(-4px, -4px);
}

.section-header-row {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  border-bottom: 4px solid var(--bauhaus-black);
  cursor: pointer;
}

.section-number {
  font-size: 20px;
  font-weight: 800;
  color: var(--bauhaus-red);
}

.section-title {
  font-size: 22px;
  font-weight: 800;
  text-transform: uppercase;
  color: var(--bauhaus-black);
}

.collapse-icon {
  margin-left: auto;
  font-size: 24px;
  font-weight: 800;
}

.section-body {
  padding: 30px;
  line-height: 1.6;
}

.generated-content :deep(p) { margin-bottom: 1.2rem; }
.generated-content :deep(h2) { font-weight: 800; margin: 1.5rem 0 1rem; text-transform: uppercase; border-bottom: 2px solid var(--bauhaus-black); }

/* Right Panel - Interaction */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bauhaus-cream);
  overflow: hidden;
}

/* Action Bar */
.action-bar {
  display: flex;
  flex-direction: column;
  padding: 25px;
  background: var(--bauhaus-black);
  color: var(--bauhaus-cream);
  gap: 20px;
  border-bottom: 6px solid var(--bauhaus-red);
}

.action-bar-header {
  display: flex;
  align-items: center;
  gap: 15px;
}

.action-indicator {
  width: 12px;
  height: 12px;
  background: var(--bauhaus-yellow);
  border: 2px solid #fff;
}

.action-bar-title {
  font-size: 28px;
  font-weight: 800;
  text-transform: uppercase;
  color: var(--bauhaus-yellow);
  letter-spacing: -1px;
}

.action-bar-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tab-pill {
  background: #222;
  color: #fff;
  border: 3px solid var(--bauhaus-cream);
  padding: 10px 20px;
  font-weight: 800;
  text-transform: uppercase;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-pill:hover {
  background: #444;
}

.tab-pill.active {
  background: var(--bauhaus-red);
  color: #fff;
  border-color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 0 #fff;
}

.dropdown-arrow {
  font-size: 10px;
  transition: transform 0.2s;
}
.dropdown-arrow.open { transform: rotate(180deg); }

/* Dropdown Menu */
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 4px solid var(--bauhaus-black);
  z-index: 100;
  max-height: 300px;
  overflow-y: auto;
  margin-top: 5px;
  box-shadow: 8px 8px 0 rgba(0,0,0,0.2);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-bottom: 2px solid var(--bauhaus-black);
  cursor: pointer;
  color: var(--bauhaus-black);
}

.dropdown-item:hover { background: var(--bauhaus-yellow); }

.agent-avatar {
  width: 32px;
  height: 32px;
  background: var(--bauhaus-black);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  flex-shrink: 0;
}

.agent-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.agent-name { font-weight: 800; font-size: 14px; }
.agent-role { font-size: 11px; opacity: 0.7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Chat Container */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 30px;
  gap: 20px;
}

.chat-messages {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
  background: #fff;
  border: 6px solid var(--bauhaus-black);
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.chat-message {
  display: flex;
  gap: 20px;
}

.message-avatar {
  width: 50px;
  height: 50px;
  background: var(--bauhaus-black);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 20px;
  border: 3px solid var(--bauhaus-red);
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  border-left: 6px solid var(--bauhaus-black);
  padding-left: 20px;
}

.sender-name {
  font-weight: 800;
  text-transform: uppercase;
  font-size: 16px;
  color: var(--bauhaus-red);
  margin-bottom: 5px;
}

.message-text {
  font-size: 16px;
  line-height: 1.5;
  color: var(--bauhaus-black);
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  opacity: 0.5;
  text-align: center;
}

.bauhaus-empty-graphic {
  width: 100px;
  height: 100px;
  background: var(--bauhaus-blue);
  border: 6px solid var(--bauhaus-black);
  margin-bottom: 20px;
  position: relative;
}
.bauhaus-empty-graphic::after {
  content: '';
  position: absolute;
  width: 60px;
  height: 60px;
  background: var(--bauhaus-red);
  top: -20px;
  right: -20px;
  border: 4px solid var(--bauhaus-black);
}

/* Chat Input */
.chat-input-area {
  display: flex;
  gap: 15px;
  background: var(--bauhaus-black);
  padding: 20px;
  border: 6px solid var(--bauhaus-black);
}

.chat-input {
  flex: 1;
  background: var(--bauhaus-cream);
  border: 4px solid #fff;
  padding: 15px;
  font-family: inherit;
  font-weight: 700;
  font-size: 16px;
  resize: none;
  color: var(--bauhaus-black);
}

.chat-input:focus {
  outline: none;
  background: #fff;
}

.send-btn {
  background: var(--bauhaus-red);
  color: #fff;
  border: 4px solid #fff;
  padding: 0 35px;
  font-weight: 800;
  text-transform: uppercase;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: var(--bauhaus-yellow);
  color: var(--bauhaus-black);
  transform: scale(1.05);
}

/* Survey Setup */
.survey-setup {
  padding: 40px;
  display: flex;
  flex-direction: column;
  gap: 35px;
  overflow-y: auto;
}

.setup-section {
  border: 6px solid var(--bauhaus-black);
  padding: 30px;
  background: #fff;
  position: relative;
}

.setup-section .section-title {
  display: inline-block;
  background: var(--bauhaus-blue);
  color: #fff;
  padding: 8px 20px;
  margin-bottom: 25px;
  font-size: 20px;
  border: 3px solid var(--bauhaus-black);
  text-transform: uppercase;
  font-weight: 800;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 15px;
}

.agent-checkbox {
  border: 4px solid var(--bauhaus-black);
  padding: 15px;
  display: flex;
  align-items: center;
  gap: 15px;
  cursor: pointer;
  background: #fff;
  transition: all 0.2s;
}

.agent-checkbox:hover {
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0 var(--bauhaus-black);
}

.agent-checkbox.checked {
  background: var(--bauhaus-yellow);
  border-color: var(--bauhaus-red);
}

.agent-checkbox input { display: none; }

.checkbox-avatar {
  width: 40px;
  height: 40px;
  background: var(--bauhaus-black);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  border: 2px solid #fff;
}

.agent-label-info { display: flex; flex-direction: column; }
.agent-label-name { font-weight: 800; font-size: 15px; }
.agent-label-role { font-size: 12px; opacity: 0.7; }

.survey-submit-btn {
  background: var(--bauhaus-red);
  color: #fff;
  border: 6px solid var(--bauhaus-black);
  padding: 20px;
  font-size: 24px;
  font-weight: 800;
  text-transform: uppercase;
  cursor: pointer;
  box-shadow: 10px 10px 0 var(--bauhaus-black);
  transition: all 0.2s;
}

.survey-submit-btn:hover:not(:disabled) {
  transform: translate(4px, 4px);
  box-shadow: 4px 4px 0 var(--bauhaus-black);
  background: var(--bauhaus-yellow);
  color: var(--bauhaus-black);
}

/* Results */
.survey-results-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 20px;
}

.result-card-bauhaus {
  border: 4px solid var(--bauhaus-black);
  background: #fff;
  padding: 25px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
  border-bottom: 2px solid var(--bauhaus-black);
  padding-bottom: 15px;
}

.result-meta { display: flex; flex-direction: column; }

.result-answer { line-height: 1.6; }

/* Tool Cards */
.report-agent-tools-card {
  border: 6px solid var(--bauhaus-black);
  background: var(--bauhaus-blue);
  color: #fff;
}

.tools-card-header {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  border-bottom: 4px solid #fff;
}

.tools-title { font-size: 20px; font-weight: 800; text-transform: uppercase; }
.tools-subtitle { font-size: 14px; opacity: 0.9; }

.tools-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  padding: 20px;
}

.tool-item {
  background: #fff;
  color: var(--bauhaus-black);
  padding: 15px;
  border: 4px solid var(--bauhaus-black);
}

.tool-name { font-weight: 900; text-transform: uppercase; font-size: 14px; margin-bottom: 5px; color: var(--bauhaus-red); }
.tool-desc { font-size: 13px; line-height: 1.4; }

/* Loaders */
.loading-state-bauhaus {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  padding: 30px;
}

.bauhaus-loader-dots {
  display: flex;
  gap: 10px;
}
.bauhaus-loader-dots span {
  width: 20px;
  height: 20px;
  background: var(--bauhaus-red);
  animation: bauhaus-jump 0.6s infinite alternate;
}
.bauhaus-loader-dots span:nth-child(2) { background: var(--bauhaus-blue); animation-delay: 0.2s; }
.bauhaus-loader-dots span:nth-child(3) { background: var(--bauhaus-yellow); animation-delay: 0.4s; }

@keyframes bauhaus-jump {
  to { transform: translateY(-20px); }
}

.waiting-placeholder-bauhaus {
  height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 30px;
}

.bauhaus-rect-animation {
  width: 80px;
  height: 80px;
  border: 6px solid var(--bauhaus-black);
  background: var(--bauhaus-red);
  animation: bauhaus-rotate 2s infinite linear;
}

@keyframes bauhaus-rotate {
  0% { transform: rotate(0deg) scale(1); background: var(--bauhaus-red); }
  33% { transform: rotate(120deg) scale(1.2); background: var(--bauhaus-blue); }
  66% { transform: rotate(240deg) scale(0.8); background: var(--bauhaus-yellow); }
  100% { transform: rotate(360deg) scale(1); background: var(--bauhaus-red); }
}

/* Markdown Rendering */
:deep(.message-text p) { margin-bottom: 12px; }
:deep(.message-text strong) { font-weight: 900; color: var(--bauhaus-red); }
:deep(.message-text ul) { padding-left: 20px; margin-bottom: 15px; }
:deep(.message-text li) { margin-bottom: 5px; list-style: square; }
</style>

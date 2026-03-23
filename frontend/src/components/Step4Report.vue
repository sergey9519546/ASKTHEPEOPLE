<template>
  <div class="step4-report-workbench" ref="reportWorkbench">
    <!-- Header -->
    <header class="workbench-header">
      <div class="header-left">
        <h1 class="workbench-title">STEP 4: INTERPRETATION & REPORT</h1>
        <p class="workbench-subtitle">
          Synthesizing findings from {{ simulationId }}
        </p>
      </div>
      <div class="header-right">
        <div class="status-indicator" :class="{ 'is-complete': isComplete }">
          <span class="status-dot"></span>
          <span class="status-text">{{
            isComplete ? "COMPLETED" : "GENERAING REPORT..."
          }}</span>
        </div>
      </div>
    </header>

    <div class="workbench-layout">
      <!-- Left Panel: Report Content -->
      <aside class="report-panel" ref="leftPanel">
        <div class="panel-header">
          <h2 class="panel-title">REPORT CANVAS</h2>
          <div class="panel-actions">
            <button
              class="action-btn"
              @click="goToInteraction"
              :disabled="!isComplete"
            >
              GO TO INTERACTION
            </button>
          </div>
        </div>

        <div class="report-canvas">
          <div
            v-if="!reportOutline && !generatedSections[1]"
            class="empty-report"
          >
            <div class="bauhaus-loader"></div>
            <p>Initializing analysis pipeline...</p>
          </div>

          <div v-else class="sections-list">
            <div
              v-for="(section, idx) in reportOutline || []"
              :key="idx"
              class="report-section"
              :class="{
                'is-generating': currentSectionIndex === idx + 1,
                'is-complete': generatedSections[idx + 1],
                'is-collapsed': collapsedSections.has(idx),
              }"
            >
              <div class="section-header" @click="toggleSectionCollapse(idx)">
                <span class="section-number">{{ idx + 1 }}</span>
                <h3 class="section-title">{{ section }}</h3>
                <div class="section-status">
                  <span v-if="generatedSections[idx + 1]" class="status-label"
                    >DONE</span
                  >
                  <span
                    v-else-if="currentSectionIndex === idx + 1"
                    class="status-label pulse"
                    >WRITING</span
                  >
                  <span v-else class="status-label pending">PENDING</span>
                </div>
              </div>

              <div v-if="!collapsedSections.has(idx)" class="section-body">
                <div v-if="generatedSections[idx + 1]" class="body-content">
                  <div
                    class="content-text"
                    v-html="generatedSections[idx + 1]"
                  ></div>
                </div>
                <div
                  v-else-if="currentSectionIndex === idx + 1"
                  class="writing-indicator"
                >
                  <div class="text-cursor"></div>
                  <p>Agent is synthesizing evidence...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- Right Panel: Evidence & Workflow -->
      <main class="evidence-panel" ref="rightPanel">
        <div class="panel-header">
          <nav class="evidence-tabs">
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'workflow' }"
              @click="activeTab = 'workflow'"
            >
              WORKFLOW LOGS
            </button>
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'reading' }"
              @click="activeTab = 'reading'"
            >
              SOURCE EVIDENCE
            </button>
          </nav>
        </div>

        <div class="evidence-content" ref="logContent">
          <!-- Workflow Logs Tab -->
          <div v-if="activeTab === 'workflow'" class="workflow-timeline">
            <div v-if="agentLogs.length === 0" class="workflow-empty">
              <div class="empty-pulse"></div>
              <p>Waiting for agent signals...</p>
            </div>

            <transition-group name="timeline-item">
              <div
                v-for="(log, idx) in agentLogs"
                :key="log.timestamp + idx"
                class="timeline-item"
                :class="[
                  log.action,
                  { 'is-expanded': expandedLogs.has(log.timestamp) },
                ]"
              >
                <div class="item-marker">
                  <div
                    class="marker-dot"
                    :class="getToolColor(log.tool_name)"
                  ></div>
                  <div class="marker-line"></div>
                </div>

                <div class="item-content">
                  <div class="item-header" @click="toggleLogExpand(log)">
                    <span class="item-time">{{
                      new Date(log.timestamp).toLocaleTimeString()
                    }}</span>
                    <div class="item-action-badge" :class="log.action">
                      {{ log.action.toUpperCase().replace("_", " ") }}
                    </div>

                    <div
                      v-if="
                        log.action === 'tool_call' ||
                        log.action === 'tool_result'
                      "
                      class="tool-badge"
                      :class="'tool-' + getToolColor(log.tool_name)"
                    >
                      <i
                        :class="'icon-' + getToolIcon(log.tool_name)"
                        class="tool-icon"
                      ></i>
                      <span>{{ getToolDisplayName(log.tool_name) }}</span>
                    </div>

                    <div class="header-expand">
                      <span v-if="isLogCollapsed(log)">EXPLORE</span>
                      <span v-else>COLLAPSE</span>
                    </div>
                  </div>

                  <div v-if="!isLogCollapsed(log)" class="item-details">
                    <!-- Tool Call Params -->
                    <div
                      v-if="log.action === 'tool_call' && log.params"
                      class="tool-params"
                    >
                      <pre>{{
                        typeof log.params === "string"
                          ? log.params
                          : JSON.stringify(log.params, null, 2)
                      }}</pre>
                    </div>

                    <!-- Tool Result - Structured Display -->
                    <div
                      v-if="log.action === 'tool_result' && log.result"
                      class="result-wrapper"
                    >
                      <!-- Deep Insight -->
                      <InsightDisplay
                        v-if="
                          log.tool_name === 'insight_forge' &&
                          log.structured_result
                        "
                        :result="log.structured_result"
                        :result-length="log.result.length"
                      />

                      <!-- Panorama Search -->
                      <PanoramaDisplay
                        v-else-if="
                          log.tool_name === 'panorama_search' &&
                          log.structured_result
                        "
                        :result="log.structured_result"
                        :result-length="log.result.length"
                      />

                      <!-- Agent Interview -->
                      <InterviewDisplay
                        v-else-if="
                          log.tool_name === 'interview_agents' &&
                          log.structured_result
                        "
                        :result="log.structured_result"
                        :result-length="log.result.length"
                      />

                      <!-- Quick Search -->
                      <QuickSearchDisplay
                        v-else-if="
                          log.tool_name === 'quick_search' &&
                          log.structured_result
                        "
                        :result="log.structured_result"
                        :result-length="log.result.length"
                      />

                      <!-- Default Raw Result toggle -->
                      <div v-else class="raw-result">
                        <div class="result-meta">
                          <span class="result-tool">{{ log.tool_name }}</span>
                          <span class="result-size"
                            >{{ log.result.length }} chars</span
                          >
                          <button
                            class="action-btn"
                            @click="toggleRawResult(log.timestamp, $event)"
                          >
                            {{
                              showRawResult[log.timestamp]
                                ? "HIDE RAW"
                                : "VIEW RAW"
                            }}
                          </button>
                        </div>
                        <div
                          v-if="showRawResult[log.timestamp]"
                          class="result-raw"
                        >
                          <pre>{{ log.result }}</pre>
                        </div>
                        <div v-else class="raw-preview">
                          {{ log.result.slice(0, 500) }}...
                        </div>
                      </div>
                    </div>

                    <!-- LLM Response -->
                    <div
                      v-if="log.action === 'llm_response'"
                      class="llm-response"
                    >
                      <div class="llm-meta">
                        <span v-if="log.thinking" class="meta-tag active"
                          >ANALYZING</span
                        >
                        <span
                          v-if="log.final_answer"
                          class="meta-tag final-answer"
                          >READY</span
                        >
                      </div>
                      <div v-if="log.final_answer" class="final-answer-hint">
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="2"
                        >
                          <path d="M20 6L9 17l-5-5" />
                        </svg>
                        Report section synthesis ready
                      </div>
                      <div class="llm-content">
                        <pre>{{ log.content }}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </transition-group>
          </div>

          <!-- Source Evidence Tab -->
          <div v-else-if="activeTab === 'reading'" class="evidence-list">
            <div v-if="!reportId" class="evidence-empty">
              <p>No report ID specified.</p>
            </div>
            <div v-else-if="isEvidenceLoading" class="evidence-loading">
              <div class="bauhaus-loader"></div>
              <p>Retrieving source evidence...</p>
            </div>
            <div v-else-if="reportEvidenceError" class="evidence-error">
              <p>{{ reportEvidenceError }}</p>
            </div>
            <div v-else-if="reportEvidence.length === 0" class="evidence-empty">
              <p>No source evidence found.</p>
            </div>
            <div v-else class="evidence-grid">
              <div
                v-for="(ev, idx) in reportEvidence"
                :key="idx"
                class="evidence-card bauhaus-card"
              >
                <div class="card-header">
                  <span class="evidence-type">{{ ev.type }}</span>
                  <span class="evidence-ref">#{{ ev.id?.slice(-4) }}</span>
                </div>
                <div class="card-body">
                  <p class="evidence-preview">
                    {{ ev.content?.slice(0, 150) }}...
                  </p>
                </div>
                <div class="card-footer">
                  <span class="evidence-meta"
                    >RELIABILITY: {{ ev.reliability || "HIGH" }}</span
                  >
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Terminal Logs -->
        <div class="console-logs">
          <div class="log-header">
            <span class="log-title">SYSTEM_STREAM</span>
            <span class="log-line-count">{{ consoleLogs.length }} LINES</span>
          </div>
          <div class="log-content" ref="consoleLogContent">
            <div v-for="(log, idx) in consoleLogs" :key="idx" class="log-line">
              <span class="log-timestamp"
                >[{{ new Date(log.timestamp).toLocaleTimeString() }}]</span
              >
              <span class="log-msg" :class="log.type">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { h, onMounted, onUnmounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { getAgentLog, getConsoleLog, getReportEvidence } from "../api/report";

const router = useRouter();

const props = defineProps({
  reportId: String,
  simulationId: String,
  systemLogs: Array,
});

const emit = defineEmits(["add-log", "update-status"]);

// State
const agentLogs = ref([]);
const consoleLogs = ref([]);
const agentLogLine = ref(0);
const consoleLogLine = ref(0);
const reportOutline = ref(null);
const generatedSections = ref({});
const currentSectionIndex = ref(null);
const isComplete = ref(false);
const isLoading = ref(false);

const activeTab = ref("workflow");
const expandedLogs = ref(new Set());
const collapsedSections = ref(new Set());
const reportEvidence = ref([]);
const reportEvidenceError = ref("");
const isEvidenceLoading = ref(false);
const showRawResult = reactive({});

const leftPanel = ref(null);
const rightPanel = ref(null);

// Navigation
const goToInteraction = () => {
  if (props.reportId) {
    router.push({ name: "Interaction", params: { reportId: props.reportId } });
  }
};

// Parser Functions
const parseInsightForge = (text) => {
  const result = {
    query: "",
    simulationRequirement: "",
    stats: { facts: 0, entities: 0, relationships: 0 },
    subQueries: [],
    facts: [],
    entities: [],
    relations: [],
  };
  try {
    const queryMatch = text.match(/Question:\s*(.+?)(?:\n|$)/);
    if (queryMatch) result.query = queryMatch[1].trim();
    const reqMatch = text.match(/Scenario:\s*(.+?)(?:\n|$)/);
    if (reqMatch) result.simulationRequirement = reqMatch[1].trim();
    const factMatch = text.match(/Facts:\s*(\d+)/);
    if (factMatch) result.stats.facts = parseInt(factMatch[1]);
  } catch (e) {
    console.warn("Parse insight_forge failed:", e);
  }
  return result;
};

const parsePanorama = (text) => {
  const result = {
    query: "",
    stats: { nodes: 0, edges: 0, activeFacts: 0, historicalFacts: 0 },
    activeFacts: [],
    historicalFacts: [],
    entities: [],
  };
  try {
    const queryMatch = text.match(/Query:\s*(.+?)(?:\n|$)/);
    if (queryMatch) result.query = queryMatch[1].trim();
  } catch (e) {
    console.warn("Parse panorama failed:", e);
  }
  return result;
};

const parseInterview = (text) => {
  const result = {
    topic: "",
    agentCount: "",
    successCount: 0,
    totalCount: 0,
    selectionReason: "",
    interviews: [],
    summary: "",
  };
  try {
    const topicMatch = text.match(/\*\*Topic:\*\*\s*(.+?)(?:\n|$)/);
    if (topicMatch) result.topic = topicMatch[1].trim();
  } catch (e) {
    console.warn("Parse interview failed:", e);
  }
  return result;
};

const parseQuickSearch = (text) => {
  const result = { query: "", count: 0, facts: [], edges: [], nodes: [] };
  try {
    const queryMatch = text.match(/Search Query:\s*(.+?)(?:\n|$)/);
    if (queryMatch) result.query = queryMatch[1].trim();
  } catch (e) {
    console.warn("Parse quick_search failed:", e);
  }
  return result;
};

// ========== Sub Components ==========
const InsightDisplay = {
  props: ["result", "resultLength"],
  setup(props) {
    return () =>
      h("div", { class: "insight-display bauhaus-sub" }, [
        h("div", { class: "sub-header" }, "DEEP INSIGHT"),
        h("div", { class: "sub-body" }, [
          h("p", props.result.query),
          h(
            "div",
            { class: "sub-stats" },
            `FACTS: ${props.result.stats.facts}`,
          ),
        ]),
      ]);
  },
};

const PanoramaDisplay = {
  props: ["result", "resultLength"],
  setup(props) {
    return () =>
      h("div", { class: "panorama-display bauhaus-sub" }, [
        h("div", { class: "sub-header" }, "PANORAMA SEARCH"),
        h("div", { class: "sub-body" }, h("p", props.result.query)),
      ]);
  },
};

const InterviewDisplay = {
  props: ["result", "resultLength"],
  setup(props) {
    return () =>
      h("div", { class: "interview-display bauhaus-sub" }, [
        h("div", { class: "sub-header" }, "AGENT INTERVIEW"),
        h("div", { class: "sub-body" }, h("p", props.result.topic)),
      ]);
  },
};

const QuickSearchDisplay = {
  props: ["result", "resultLength"],
  setup(props) {
    return () =>
      h("div", { class: "quick-search-display bauhaus-sub" }, [
        h("div", { class: "sub-header" }, "QUICK SEARCH"),
        h("div", { class: "sub-body" }, h("p", props.result.query)),
      ]);
  },
};

// Logic
const toolConfig = {
  insight_forge: { name: "Deep Insight", color: "blue", icon: "lightbulb" },
  panorama_search: { name: "Panorama", color: "blue", icon: "globe" },
  interview_agents: { name: "Interview", color: "blue", icon: "users" },
  quick_search: { name: "Search", color: "blue", icon: "zap" },
};

const getToolDisplayName = (n) => toolConfig[n]?.name || n;
const getToolColor = (n) => toolConfig[n]?.color || "black";
const getToolIcon = (n) => toolConfig[n]?.icon || "tool";

const toggleRawResult = (ts, ev) => {
  showRawResult[ts] = !showRawResult[ts];
};

const toggleSectionCollapse = (idx) => {
  const s = new Set(collapsedSections.value);
  if (s.has(idx)) s.delete(idx);
  else s.add(idx);
  collapsedSections.value = s;
};

const toggleLogExpand = (log) => {
  const s = new Set(expandedLogs.value);
  if (s.has(log.timestamp)) s.delete(log.timestamp);
  else s.add(log.timestamp);
  expandedLogs.value = s;
};

const isLogCollapsed = (log) => {
  if (["tool_call", "tool_result", "llm_response"].includes(log.action)) {
    return !expandedLogs.value.has(log.timestamp);
  }
  return false;
};

// Fetching
let timer = null;
const fetchLogs = async () => {
  if (!props.reportId) return;
  try {
    const res = await getAgentLog(props.reportId, agentLogLine.value);
    if (res.data && res.data.length > 0) {
      const newLogs = res.data.map((log) => {
        let structured = null;
        if (log.action === "tool_result") {
          if (log.tool_name === "insight_forge")
            structured = parseInsightForge(log.result);
          else if (log.tool_name === "panorama_search")
            structured = parsePanorama(log.result);
          else if (log.tool_name === "interview_agents")
            structured = parseInterview(log.result);
          else if (log.tool_name === "quick_search")
            structured = parseQuickSearch(log.result);
        }

        // Handle Report Synthesis
        if (log.action === "llm_response" && log.final_answer) {
          const sectionMatch = log.content.match(/REPORT_SECTION_(\d+)/);
          if (sectionMatch) {
            const num = parseInt(sectionMatch[1]);
            generatedSections.value[num] = log.content.replace(
              /REPORT_SECTION_\d+:\s*/,
              "",
            );
          }
        }

        return { ...log, structured_result: structured };
      });
      agentLogs.value = [...agentLogs.value, ...newLogs];
      agentLogLine.value += res.data.length;
    }

    const consoleRes = await getConsoleLog(
      props.reportId,
      consoleLogLine.value,
    );
    if (consoleRes.data && consoleRes.data.length > 0) {
      consoleLogs.value = [...consoleLogs.value, ...consoleRes.data];
      consoleLogLine.value += consoleRes.data.length;
    }

    // Check completion
    const lastLog = agentLogs.value[agentLogs.value.length - 1];
    if (lastLog?.action === "status_update" && lastLog.status === "completed") {
      isComplete.value = true;
      clearInterval(timer);
    }
  } catch (e) {
    console.error(e);
  }
};

onMounted(() => {
  timer = setInterval(fetchLogs, 3000);
  fetchLogs();
  if (props.reportId) {
    isEvidenceLoading.value = true;
    getReportEvidence(props.reportId)
      .then((res) => {
        reportEvidence.value = res.data || [];
      })
      .catch((e) => (reportEvidenceError.value = "Failed to load evidence"))
      .finally(() => {
        isEvidenceLoading.value = false;
      });
  }
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
:root {
  --atp-black: #000000;
  --atp-white: #ffffff;
  --atp-blue: #0026fe;
  --atp-red: #ff331f;
  --atp-yellow: #e5ff00;
}

.step4-report-workbench {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--atp-white);
  color: var(--atp-black);
  font-family: "Inter", system-ui, sans-serif;
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

.workbench-title {
  font-weight: 900;
  font-size: 24px;
  letter-spacing: -1px;
}

.workbench-subtitle {
  font-size: 14px;
  font-weight: 600;
  opacity: 0.8;
}

.status-indicator {
  padding: 8px 16px;
  border: 3px solid var(--atp-black);
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 12px;
}

.status-indicator.is-complete {
  background: var(--atp-blue);
  color: var(--atp-white);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--atp-red);
}

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.report-panel {
  flex: 1;
  border-right: 4px solid var(--atp-black);
  display: flex;
  flex-direction: column;
}

.evidence-panel {
  width: 600px;
  display: flex;
  flex-direction: column;
}

.panel-header {
  height: 60px;
  border-bottom: 3px solid var(--atp-black);
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-weight: 800;
  font-size: 14px;
}

.report-canvas {
  flex: 1;
  padding: 40px;
  overflow-y: auto;
}

.report-section {
  border: 4px solid var(--atp-black);
  margin-bottom: 24px;
  transition: transform 0.2s;
}

.report-section.is-generating {
  border-color: var(--atp-blue);
  transform: translateX(10px);
}

.section-header {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  background: var(--atp-black);
  color: var(--atp-white);
  cursor: pointer;
}

.section-number {
  font-weight: 900;
  font-size: 24px;
  margin-right: 20px;
}

.section-title {
  font-weight: 700;
  font-size: 16px;
  flex: 1;
}

.section-body {
  padding: 24px;
  line-height: 1.6;
}

.evidence-tabs {
  display: flex;
  height: 100%;
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
}

.tab-btn.active {
  background: var(--atp-yellow);
}

.evidence-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.timeline-item {
  border-left: 3px solid var(--atp-black);
  padding-left: 20px;
  padding-bottom: 30px;
  position: relative;
}

.marker-dot {
  position: absolute;
  left: -8px;
  top: 0;
  width: 13px;
  height: 13px;
  border: 3px solid var(--atp-black);
  background: var(--atp-white);
}

.item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  cursor: pointer;
}

.item-time {
  font-family: "JetBrains Mono", monospace;
  font-size: 10px;
  font-weight: 600;
}

.tool-badge {
  padding: 4px 10px;
  border: 2px solid var(--atp-black);
  font-weight: 800;
  font-size: 10px;
  background: var(--atp-blue);
  color: var(--atp-white);
}

.item-details {
  border: 3px solid var(--atp-black);
  padding: 12px;
  background: #f0f0f0;
}

.bauhaus-sub {
  border: 2px solid var(--atp-black);
  background: var(--atp-white);
}

.sub-header {
  background: var(--atp-black);
  color: var(--atp-white);
  font-weight: 800;
  font-size: 10px;
  padding: 4px 8px;
}

.sub-body {
  padding: 10px;
  font-size: 12px;
}

.console-logs {
  height: 200px;
  background: var(--atp-black);
  color: var(--atp-white);
  padding: 15px;
  font-family: "JetBrains Mono", monospace;
}

.log-line {
  font-size: 11px;
  margin-bottom: 4px;
  opacity: 0.8;
}

.log-timestamp {
  color: var(--atp-yellow);
  margin-right: 10px;
}

.bauhaus-loader {
  width: 40px;
  height: 40px;
  border: 4px solid var(--atp-black);
  border-top-color: var(--atp-blue);
  animation: spin 1s infinite linear;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.action-btn {
  background: var(--atp-black);
  color: var(--atp-white);
  border: none;
  padding: 8px 16px;
  font-weight: 800;
  font-size: 11px;
  cursor: pointer;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.action-btn:hover:not(:disabled) {
  background: var(--atp-blue);
}
</style>

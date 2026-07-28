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
              @click="handleExportPDF"
              :disabled="!isComplete || exportingPDF"
            >
              <span v-if="exportingPDF">GENERATING...</span>
              <span v-else-if="exportPDFSuccess">✓ EXPORTED PDF</span>
              <span v-else>EXPORT_PDF</span>
            </button>
            <button
              class="action-btn secondary"
              @click="handleExportCSV"
              :disabled="!isComplete || exportingCSV"
            >
              <span v-if="exportingCSV">EXTRACTING...</span>
              <span v-else-if="exportCSVSuccess">✓ EXPORTED CSV</span>
              <span v-else>EXPORT_CSV</span>
            </button>
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
import {
  exportReportCSV,
  exportReportPDF,
  getAgentLog,
  getConsoleLog,
  getReportEvidence,
} from "../api/report";

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

// Export visual feedback states
const exportingPDF = ref(false);
const exportingCSV = ref(false);
const exportPDFSuccess = ref(false);
const exportCSVSuccess = ref(false);

const leftPanel = ref(null);
const rightPanel = ref(null);

// Navigation
const goToInteraction = () => {
  if (props.reportId) {
    router.push({ name: "Interaction", params: { reportId: props.reportId } });
  }
};

const handleExportPDF = async () => {
  if (exportingPDF.value || !props.reportId) return;
  exportingPDF.value = true;
  exportPDFSuccess.value = false;
  emit("add-log", "Generating Bauhaus PDF...");
  try {
    const res = await exportReportPDF(props.reportId);
    const blob = new Blob([res.data || res], { type: "application/pdf" });
    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = `ATP_REPORT_${props.reportId}.pdf`;
    link.click();
    window.URL.revokeObjectURL(link.href);
    exportPDFSuccess.value = true;
    emit("add-log", "✓ PDF exported successfully");
    setTimeout(() => {
      exportPDFSuccess.value = false;
    }, 3000);
  } catch (err) {
    emit("add-log", `✗ Failed to export PDF: ${err.message || err}`);
  } finally {
    exportingPDF.value = false;
  }
};

const handleExportCSV = async () => {
  if (exportingCSV.value || !props.reportId) return;
  exportingCSV.value = true;
  exportCSVSuccess.value = false;
  emit("add-log", "Extracting Graph Data to CSV...");
  try {
    const res = await exportReportCSV(props.reportId);
    const blob = new Blob([res.data || res], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = `ATP_DATA_${props.reportId}.csv`;
    link.click();
    window.URL.revokeObjectURL(link.href);
    exportCSVSuccess.value = true;
    emit("add-log", "✓ CSV exported successfully");
    setTimeout(() => {
      exportCSVSuccess.value = false;
    }, 3000);
  } catch (err) {
    emit("add-log", `✗ Failed to export CSV: ${err.message || err}`);
  } finally {
    exportingCSV.value = false;
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
  insight_forge: { name: "Deep Insight", color: "purple", icon: "lightbulb" },
  panorama_search: { name: "Panorama", color: "cyan", icon: "globe" },
  interview_agents: { name: "Interview", color: "green", icon: "users" },
  quick_search: { name: "Search", color: "cyan", icon: "zap" },
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
.step4-report-workbench {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  color: var(--text-primary);
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
  color: var(--text-primary);
}

.workbench-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-top: 2px;
}

.status-indicator {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 10px;
  background: rgba(255, 255, 255, 0.03);
}

.status-indicator.is-complete {
  background: #ecfdf5;
  color: var(--accent-tertiary);
  border-color: #d1fae5;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-tertiary);
}

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.report-panel {
  flex: 1;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
}

.evidence-panel {
  width: 500px;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.03);
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
  color: var(--text-secondary);
  text-transform: uppercase;
}

.report-canvas {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.report-section {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
  overflow: hidden;
  background: var(--bg-color);
  transition: all 0.25s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.report-section.is-generating {
  border-color: var(--accent-color);
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(244, 63, 94, 0.05);
}

.section-header {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.15s ease;
}
.section-header:hover {
  background: rgba(255, 255, 255, 0.05);
}

.section-number {
  font-weight: 700;
  font-size: 16px;
  color: var(--text-secondary);
  margin-right: 12px;
}

.section-title {
  font-weight: 600;
  font-size: 13px;
  flex: 1;
}

.section-body {
  padding: 16px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-primary);
}

.evidence-tabs {
  display: flex;
  height: 100%;
}

.tab-btn {
  height: 100%;
  padding: 0 16px;
  border: none;
  background: transparent;
  font-weight: 700;
  font-size: 11px;
  color: var(--text-secondary);
  border-right: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.15s ease;
}
.tab-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--bg-color);
  color: var(--text-primary);
}

.evidence-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.timeline-item {
  border-left: 1px solid var(--border-color);
  padding-left: 16px;
  padding-bottom: 20px;
  position: relative;
}

.marker-dot {
  position: absolute;
  left: -5px;
  top: 4px;
  width: 9px;
  height: 9px;
  border: 2px solid var(--bg-color);
  border-radius: 50%;
  background: var(--border-color);
  box-shadow: 0 0 0 2px rgba(203, 213, 225, 0.4);
}

.timeline-item:hover .marker-dot {
  background: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.4);
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}

.item-time {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--text-secondary);
}

.tool-badge {
  padding: 2px 6px;
  border: 1px solid #dbeafe;
  border-radius: 4px;
  font-weight: 700;
  font-size: 9px;
  background: #eff6ff;
  color: #2563eb;
}

.item-details {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 10px;
  background: var(--bg-color);
}

.bauhaus-sub {
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  border-radius: 6px;
  overflow: hidden;
  margin-top: 6px;
}

.sub-header {
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-weight: 700;
  font-size: 9px;
  padding: 4px 8px;
}

.sub-body {
  padding: 8px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-primary);
}

.console-logs {
  height: 160px;
  background: var(--surface-color);
  color: var(--bg-color);
  padding: 12px;
  font-family: var(--font-mono);
  border-top: 1px solid var(--border-color);
}

.log-line {
  font-size: 10px;
  margin-bottom: 2px;
  opacity: 0.85;
}

.log-timestamp {
  color: var(--accent-color);
  margin-right: 8px;
}

.bauhaus-loader {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.05);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.action-btn {
  background: var(--surface-color);
  color: var(--bg-color);
  border: none;
  padding: 6px 12px;
  font-weight: 600;
  font-size: 11px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}
</style>

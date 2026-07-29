<template>
  <div ref="reportWorkbench" class="decision-report-shell">
    <a class="skip-link" href="#scenario-report">Skip to the findings</a>

    <header class="report-masthead">
      <div class="masthead-copy">
        <p class="route-label">
          <span class="route-number">04</span>
          Review the run
        </p>
        <h1>What this run suggests—and what it cannot tell you.</h1>
        <p class="decision-question">
          <span>The decision</span>
          {{ decisionQuestion }}
        </p>
      </div>

      <aside class="truth-stamp" aria-label="Important interpretation limits">
        <span class="truth-kicker">Use as a scenario map</span>
        <strong>0 human respondents</strong>
        <span>Not a forecast</span>
        <p>No result on this page is a vote, prediction, or population estimate.</p>
      </aside>
    </header>

    <nav class="reading-route" aria-label="Report reading order">
      <a href="#scenario-report">
        <span>01</span>
        <strong>Findings</strong>
        <small>Read the generated paths</small>
      </a>
      <a href="#trace-records">
        <span>02</span>
        <strong>Within-run examples</strong>
        <small>Inspect related generated records</small>
      </a>
      <a href="#run-limits">
        <span>03</span>
        <strong>Limits</strong>
        <small>Know what still needs testing</small>
      </a>
    </nav>

    <section
      v-if="hasTerminalFailure"
      ref="terminalAlert"
      class="terminal-report-alert"
      role="alert"
      aria-labelledby="terminal-report-heading"
      tabindex="-1"
    >
      <div aria-hidden="true">!</div>
      <div>
        <p class="section-kicker">Report needs attention</p>
        <h2 id="terminal-report-heading">{{ failureTitle }}</h2>
        <p>{{ failureMessage }}</p>
        <div class="recovery-actions">
          <button
            type="button"
            class="action-button is-primary"
            :disabled="isRetrying"
            @click="retryReportLoad"
          >
            {{ isRetrying ? "Trying again…" : "Retry loading report" }}
          </button>
          <button
            type="button"
            class="action-button is-dark"
            @click="goHome"
          >
            Return home
          </button>
        </div>
      </div>
    </section>

    <section
      v-if="!isComplete && !hasTerminalFailure"
      class="generation-strip"
      aria-live="polite"
      role="status"
    >
      <div>
        <span>Report in progress</span>
        <strong>{{ progressMessage }}</strong>
      </div>
      <div
        class="progress-track"
        role="progressbar"
        aria-label="Report generation progress"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-valuenow="reportProgress"
      >
        <span :style="{ transform: `scaleX(${reportProgress / 100})` }"></span>
      </div>
      <b>{{ reportProgress }}%</b>
    </section>

    <main id="scenario-report" class="report-grid" tabindex="-1">
      <article class="findings-column" aria-labelledby="findings-heading">
        <header class="findings-intro">
          <p class="section-kicker">01 / Findings</p>
          <h2 id="findings-heading">{{ reportTitle }}</h2>
          <p v-if="reportSummary">{{ reportSummary }}</p>
        </header>

        <div
          v-if="hasTerminalFailure"
          class="report-message report-message-error"
        >
          <strong>No report findings are available.</strong>
          <span>Use the recovery choices above to try again or start over.</span>
        </div>

        <div
          v-else-if="finalSections.length === 0"
          class="report-skeleton"
          aria-label="Preparing the report structure"
        >
          <div class="skeleton-route" aria-hidden="true"></div>
          <div>
            <strong>Building the decision brief…</strong>
            <span>The first finding will appear here when it is ready.</span>
            <i aria-hidden="true"></i>
            <i aria-hidden="true"></i>
            <i aria-hidden="true"></i>
          </div>
        </div>

        <section
          v-for="(section, sectionIndex) in finalSections"
          :key="`${sectionIndex}-${section.title}`"
          class="finding-section"
          :class="{
            'is-drafting':
              currentSectionIndex === sectionIndex + 1 && !section.content,
          }"
          :aria-labelledby="`finding-${sectionIndex}`"
        >
          <div class="finding-route" aria-hidden="true">
            <span>{{ String(sectionIndex + 1).padStart(2, "0") }}</span>
            <i></i>
          </div>

          <div class="finding-copy">
            <header>
              <p>
                {{
                  section.content
                    ? "Generated finding"
                    : currentSectionIndex === sectionIndex + 1
                      ? "Drafting now"
                      : "Waiting"
                }}
              </p>
              <h3 :id="`finding-${sectionIndex}`">{{ section.title }}</h3>
            </header>

            <div v-if="section.content" class="report-prose">
              <template
                v-for="(block, blockIndex) in parseReportBlocks(section.content)"
                :key="`${block.type}-${blockIndex}`"
              >
                <h4 v-if="block.type === 'heading'">{{ block.text }}</h4>
                <ul v-else-if="block.type === 'list'">
                  <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
                    {{ item }}
                  </li>
                </ul>
                <ol v-else-if="block.type === 'ordered-list'">
                  <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
                    {{ item }}
                  </li>
                </ol>
                <blockquote v-else-if="block.type === 'note'">
                  {{ block.text }}
                </blockquote>
                <p v-else>{{ block.text }}</p>
              </template>
            </div>

            <div v-else class="finding-pending" aria-live="polite">
              <span aria-hidden="true"></span>
              <p>
                {{
                  currentSectionIndex === sectionIndex + 1
                    ? "Drafting this section from generated run records…"
                    : "This section has not been drafted yet."
                }}
              </p>
            </div>
          </div>
        </section>
      </article>

      <aside class="report-rail" aria-label="Run examples, limits, and actions">
        <section id="trace-records" class="trace-section">
          <header>
            <p class="section-kicker">02 / Within-run examples</p>
            <h2>Keyword-related examples from this run</h2>
            <p>
              These records were matched to report sections after generation.
              They help inspect the run; they do not prove, support, or cite a
              report statement.
            </p>
          </header>

          <div v-if="!reportId" class="rail-state">
            This report has no trace reference.
          </div>
          <div v-else-if="hasTerminalFailure" class="rail-state is-error">
            Generated examples are unavailable because the report did not finish.
          </div>
          <div v-else-if="!isReportReady" class="rail-state">
            Trace examples will be collected after the report is ready.
          </div>
          <div v-else-if="isEvidenceLoading" class="rail-state is-loading">
            <span aria-hidden="true"></span>
            Looking for related generated records…
          </div>
          <div v-else-if="reportEvidenceError" class="rail-state is-error">
            {{ reportEvidenceError }}
          </div>
          <div v-else-if="reportEvidence.length === 0" class="rail-state">
            No keyword-related generated records were saved for this report.
          </div>

          <ol v-else class="trace-list">
            <li
              v-for="(record, recordIndex) in visibleTraceRecords"
              :key="record.trace_id || `${record.source_type}-${recordIndex}`"
            >
              <div class="trace-marker" aria-hidden="true"></div>
              <article>
                <header>
                  <strong>
                    <small v-if="record.section_index">
                      Section {{ record.section_index }}
                    </small>
                    {{ traceSourceLabel(record.source_type) }}
                  </strong>
                  <span v-if="record.round_num != null">
                    Round {{ record.round_num }}
                  </span>
                </header>
                <p class="trace-excerpt">{{ readableExcerpt(record.excerpt) }}</p>
                <p class="trace-meaning">{{ record.interpretation }}</p>
                <footer>
                  <span>{{ record.platform || "Mixed context" }}</span>
                  <b>{{ record.human_respondents }} human respondents</b>
                </footer>
              </article>
            </li>
          </ol>
          <button
            v-if="reportEvidence.length > TRACE_PREVIEW_LIMIT"
            type="button"
            class="trace-toggle"
            :aria-expanded="showAllTraceRecords"
            @click="showAllTraceRecords = !showAllTraceRecords"
          >
            {{
              showAllTraceRecords
                ? `Show the first ${TRACE_PREVIEW_LIMIT} examples`
                : `Show all ${reportEvidence.length} examples`
            }}
          </button>
        </section>

        <section id="run-limits" class="limits-section">
          <p class="section-kicker">03 / Limits of this run</p>
          <h2>What still needs real-world testing</h2>
          <ul>
            <li>
              The profiles, posts, comments, and follow-up answers were
              generated—not collected from people.
            </li>
            <li>
              The run is not representative, calibrated, or a probability
              estimate.
            </li>
            <li>
              A plausible path can still be wrong, incomplete, or missing an
              affected group.
            </li>
            <li>
              Material decisions need external evidence and direct validation
              with people.
            </li>
          </ul>
        </section>

        <section class="next-step-section">
          <p class="section-kicker">Take it forward</p>
          <h2>Turn paths into questions.</h2>
          <p>
            Export the brief, inspect the generated records, or ask a follow-up.
          </p>
          <div class="primary-actions">
            <button
              type="button"
              class="action-button is-primary"
              :disabled="!isReportReady || exportingPDF"
              :aria-describedby="exportPDFError ? 'pdf-export-error' : undefined"
              @click="handleExportPDF"
            >
              {{
                exportingPDF
                  ? "Preparing PDF…"
                  : exportPDFSuccess
                    ? "PDF downloaded"
                    : "Download report PDF"
              }}
            </button>
            <p
              v-if="exportPDFError"
              id="pdf-export-error"
              class="export-feedback is-error"
              role="alert"
            >
              {{ exportPDFError }}
            </p>
            <button
              type="button"
              class="action-button is-dark"
              :disabled="!isReportReady"
              @click="goToInteraction"
            >
              Ask follow-up questions
            </button>
          </div>

          <details class="more-exports">
            <summary>More export formats</summary>
            <div>
              <div class="export-option">
                <button
                  type="button"
                  class="text-action"
                  :disabled="!isReportReady || exportingMarkdown"
                  :aria-describedby="
                    exportMarkdownError ? 'markdown-export-error' : undefined
                  "
                  @click="handleExportMarkdown"
                >
                  {{
                    exportingMarkdown
                      ? "Preparing Markdown…"
                      : exportMarkdownSuccess
                        ? "Markdown downloaded"
                        : "Download Markdown (.md)"
                  }}
                </button>
                <p
                  v-if="exportMarkdownError"
                  id="markdown-export-error"
                  class="export-feedback is-error"
                  role="alert"
                >
                  {{ exportMarkdownError }}
                </p>
              </div>

              <div class="export-option">
                <button
                  type="button"
                  class="text-action"
                  :disabled="!isReportReady || exportingTXT"
                  :aria-describedby="
                    exportTXTError ? 'txt-export-error' : undefined
                  "
                  @click="handleExportTXT"
                >
                  {{
                    exportingTXT
                      ? "Preparing text…"
                      : exportTXTSuccess
                        ? "Text downloaded"
                        : "Download plain text (.txt)"
                  }}
                </button>
                <p
                  v-if="exportTXTError"
                  id="txt-export-error"
                  class="export-feedback is-error"
                  role="alert"
                >
                  {{ exportTXTError }}
                </p>
              </div>
            </div>
          </details>
        </section>
      </aside>
    </main>

    <details class="generation-disclosure">
      <summary>
        <span>Generation details and event records</span>
        <small>Secondary record · IDs and a safe event timeline</small>
      </summary>

      <div class="generation-grid">
        <section class="identifier-record">
          <h2>Record identifiers</h2>
          <dl>
            <div>
              <dt>Report ID</dt>
              <dd>{{ reportId || "Unavailable" }}</dd>
            </div>
            <div>
              <dt>Simulation ID</dt>
              <dd>{{ simulationId || reportDocument?.simulation_id || "Unavailable" }}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                {{
                  hasTerminalFailure
                    ? "Needs attention"
                    : isComplete
                      ? "Completed"
                      : progressMessage
                }}
              </dd>
            </div>
          </dl>
        </section>

        <section class="raw-records">
          <h2>Agent and tool activity</h2>
          <p v-if="agentLogs.length === 0" class="raw-empty">
            No generation activity has been recorded yet.
          </p>
          <details
            v-for="(log, logIndex) in agentLogs"
            :key="`${log.timestamp}-${logIndex}`"
            class="raw-entry"
          >
            <summary>
              <span>{{ formatTimestamp(log.timestamp) }}</span>
              <strong>{{ formatAction(log.action) }}</strong>
            </summary>
            <div>
              <p>{{ activitySummary(log) }}</p>
            </div>
          </details>
        </section>

        <section class="console-record">
          <h2>Runtime messages</h2>
          <p class="raw-empty">
            Raw runtime diagnostics are intentionally omitted from this page.
          </p>
        </section>
      </div>
    </details>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  exportReportPDF,
  getAgentLog,
  getReport,
  getReportEvidence,
  getReportStatus,
  normalizeAgentLogEntry,
  normalizeLogPage,
  normalizeReportEvidence,
  outlineSectionTitles,
} from "../api/report";

const router = useRouter();

const props = defineProps({
  reportId: String,
  simulationId: String,
  systemLogs: Array,
});

const emit = defineEmits(["add-log", "update-status"]);

const LOG_POLL_INTERVAL_MS = 3000;
const EVIDENCE_MAX_ATTEMPTS = 10;
const TRACE_PREVIEW_LIMIT = 8;

const agentLogs = ref([]);
const agentLogLine = ref(0);
const reportDocument = ref(null);
const terminalAlert = ref(null);
const reportOutline = ref(null);
const generatedSections = ref({});
const currentSectionIndex = ref(null);
const isComplete = ref(false);
const reportProgress = ref(0);
const progressMessage = ref("Preparing report");
const reportFailureKind = ref("");
const isRetrying = ref(false);
const documentRequestActive = ref(false);
const statusFailureCount = ref(0);

const reportEvidence = ref([]);
const reportEvidenceError = ref("");
const isEvidenceLoading = ref(false);
const evidenceLoaded = ref(false);
const evidenceAttempts = ref(0);
const showAllTraceRecords = ref(false);

const exportingPDF = ref(false);
const exportingMarkdown = ref(false);
const exportingTXT = ref(false);
const exportPDFSuccess = ref(false);
const exportMarkdownSuccess = ref(false);
const exportTXTSuccess = ref(false);
const exportPDFError = ref("");
const exportMarkdownError = ref("");
const exportTXTError = ref("");

const hasTerminalFailure = computed(() => Boolean(reportFailureKind.value));
const isReportReady = computed(
  () => isComplete.value && !hasTerminalFailure.value,
);

const failureTitle = computed(() =>
  reportFailureKind.value === "generation"
    ? "This report was not completed."
    : "This report could not be opened.",
);

const failureMessage = computed(() =>
  reportFailureKind.value === "generation"
    ? "The run ended before a usable decision brief was saved. Retry the saved report, or return home and reopen the project."
    : "The saved report is unavailable right now. Try loading it again, or return home and reopen it from your projects.",
);

const safeFilenameId = computed(
  () =>
    String(props.reportId || "REPORT")
      .replace(/[^a-zA-Z0-9_-]/g, "_")
      .slice(0, 80) || "REPORT",
);

const decisionQuestion = computed(
  () =>
    reportDocument.value?.simulation_requirement ||
    "The decision question for this scenario run.",
);

const reportTitle = computed(
  () => reportDocument.value?.outline?.title || "Scenario findings",
);

const reportSummary = computed(
  () =>
    reportDocument.value?.outline?.summary ||
    "A structured reading of the paths generated inside this scenario run.",
);

const finalSections = computed(() => {
  const savedSections = reportDocument.value?.outline?.sections;
  if (Array.isArray(savedSections) && savedSections.length > 0) {
    return savedSections.map((section, index) => ({
      title:
        typeof section === "string"
          ? section
          : section?.title || `Finding ${index + 1}`,
      content:
        (typeof section === "object" ? section?.content : "") ||
        generatedSections.value[index + 1] ||
        "",
    }));
  }

  if (Array.isArray(reportOutline.value) && reportOutline.value.length > 0) {
    return reportOutline.value.map((title, index) => ({
      title: title || `Finding ${index + 1}`,
      content: generatedSections.value[index + 1] || "",
    }));
  }

  return Object.keys(generatedSections.value)
    .map(Number)
    .filter(Number.isFinite)
    .sort((a, b) => a - b)
    .map((sectionIndex) => ({
      title: `Finding ${sectionIndex}`,
      content: generatedSections.value[sectionIndex] || "",
    }));
});

const visibleTraceRecords = computed(() =>
  showAllTraceRecords.value
    ? reportEvidence.value
    : reportEvidence.value.slice(0, TRACE_PREVIEW_LIMIT),
);

const stripInlineMarkdown = (value) =>
  String(value || "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/(`|~~)/g, "")
    .replace(/<[^>]*>/g, "")
    .trim();

const parseReportBlocks = (content) => {
  const blocks = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (paragraph.length === 0) return;
    blocks.push({
      type: "paragraph",
      text: stripInlineMarkdown(paragraph.join(" ")),
    });
    paragraph = [];
  };

  const addListItem = (type, text) => {
    flushParagraph();
    const previous = blocks[blocks.length - 1];
    if (previous?.type === type) {
      previous.items.push(stripInlineMarkdown(text));
    } else {
      blocks.push({ type, items: [stripInlineMarkdown(text)] });
    }
  };

  for (const rawLine of String(content || "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      continue;
    }

    const heading = line.match(/^#{1,6}\s+(.+)$/);
    const bullet = line.match(/^[-*+]\s+(.+)$/);
    const ordered = line.match(/^\d+[.)]\s+(.+)$/);
    const note = line.match(/^>\s*(.+)$/);

    if (heading) {
      flushParagraph();
      blocks.push({ type: "heading", text: stripInlineMarkdown(heading[1]) });
    } else if (bullet) {
      addListItem("list", bullet[1]);
    } else if (ordered) {
      addListItem("ordered-list", ordered[1]);
    } else if (note) {
      flushParagraph();
      blocks.push({ type: "note", text: stripInlineMarkdown(note[1]) });
    } else {
      paragraph.push(line);
    }
  }

  flushParagraph();
  return blocks.filter((block) =>
    block.items ? block.items.some(Boolean) : Boolean(block.text),
  );
};

const readableExcerpt = (value) => {
  const text = String(value || "").trim();
  if (!text) return "No excerpt was recorded.";
  try {
    const parsed = JSON.parse(text);
    if (typeof parsed === "string") return parsed;
    const preferred =
      parsed.content ||
      parsed.text ||
      parsed.response ||
      parsed.description ||
      parsed.message;
    if (preferred) return String(preferred);
  } catch (_) {
    // The record is plain text, so it is already safe to display as text.
  }
  return stripInlineMarkdown(text);
};

const traceSourceLabel = (sourceType) => {
  const labels = {
    action: "Generated action",
    post: "Generated post",
    comment: "Generated comment",
    interview: "Generated follow-up response",
    round_summary: "Generated round summary",
    scheduled_event: "Scenario condition",
    bootstrap_event: "Starting condition",
  };
  return (
    labels[sourceType] ||
    `Generated ${String(sourceType || "record").replaceAll("_", " ")}`
  );
};

const formatTimestamp = (timestamp) => {
  if (!timestamp) return "Time unavailable";
  const parsed = new Date(timestamp);
  return Number.isNaN(parsed.getTime())
    ? String(timestamp)
    : parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const formatAction = (action) => {
  const labels = {
    planning_complete: "Report structure prepared",
    section_start: "Finding started",
    section_complete: "Finding completed",
    report_complete: "Report completed",
    tool_call: "Source tool used",
    tool_result: "Source tool returned",
    llm_response: "Draft response recorded",
  };
  return labels[action] || "Generation activity recorded";
};

const activitySummary = (log) => {
  const summaries = {
    planning_complete: "The report reading order was prepared.",
    section_start: "A report finding entered the drafting stage.",
    section_complete: "A report finding was saved.",
    report_complete: "The completed report was saved.",
    tool_call: "A configured source tool was requested.",
    tool_result: "A configured source tool returned a result.",
    llm_response: "A drafting event was recorded.",
  };
  return (
    summaries[log?.action] ||
    "An internal generation event was recorded. Its raw payload is not shown."
  );
};

const safeProgressMessage = (status, progress) => {
  if (status === "completed") return "Report ready";
  if (status === "failed") return "Report generation stopped";
  if (progress >= 90) return "Finalizing the decision brief";
  if (progress >= 40) return "Writing scenario findings";
  if (progress >= 15) return "Mapping the report structure";
  return "Preparing the report";
};

const goToInteraction = () => {
  if (props.reportId) {
    router.push({ name: "Interaction", params: { reportId: props.reportId } });
  }
};

const goHome = () => router.push({ name: "Home" });

const downloadResponse = (response, type, filename) => {
  const payload = response?.data ?? response;
  if (payload == null) throw new Error("empty_export");
  const blob = payload instanceof Blob ? payload : new Blob([payload], { type });
  const link = document.createElement("a");
  link.href = window.URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(link.href);
};

const reportMarkdown = () => {
  const savedMarkdown = reportDocument.value?.markdown_content;
  if (typeof savedMarkdown === "string" && savedMarkdown.trim()) {
    return savedMarkdown.trim();
  }

  const lines = [
    `# ${reportTitle.value}`,
    "",
    reportSummary.value,
    "",
    `Decision question: ${decisionQuestion.value}`,
  ];
  finalSections.value.forEach((section) => {
    lines.push("", `## ${section.title}`, "", section.content || "");
  });
  lines.push(
    "",
    "---",
    "Synthetic scenario report. 0 human respondents. Not a forecast.",
  );
  return lines.join("\n").trim();
};

const reportPlainText = () =>
  reportMarkdown()
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[-*+]\s+/gm, "• ")
    .replace(/^\d+[.)]\s+/gm, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/[`~]/g, "")
    .replace(/<[^>]*>/g, "")
    .trim();

const handleExportPDF = async () => {
  if (exportingPDF.value || !props.reportId) return;
  exportingPDF.value = true;
  exportPDFSuccess.value = false;
  exportPDFError.value = "";
  emit("add-log", "Preparing the report PDF…");
  try {
    const response = await exportReportPDF(props.reportId);
    downloadResponse(
      response,
      "application/pdf",
      `ATP_REPORT_${safeFilenameId.value}.pdf`,
    );
    exportPDFSuccess.value = true;
    emit("add-log", "PDF downloaded.");
    window.setTimeout(() => {
      exportPDFSuccess.value = false;
    }, 3000);
  } catch (_) {
    exportPDFError.value =
      "The PDF could not be downloaded. Check your connection and try again.";
    emit("add-log", "The PDF download did not complete.");
  } finally {
    exportingPDF.value = false;
  }
};

const handleExportMarkdown = async () => {
  if (exportingMarkdown.value || !props.reportId) return;
  exportingMarkdown.value = true;
  exportMarkdownSuccess.value = false;
  exportMarkdownError.value = "";
  emit("add-log", "Preparing the Markdown download…");
  try {
    downloadResponse(
      reportMarkdown(),
      "text/markdown;charset=utf-8",
      `ATP_REPORT_${safeFilenameId.value}.md`,
    );
    exportMarkdownSuccess.value = true;
    emit("add-log", "Markdown downloaded.");
    window.setTimeout(() => {
      exportMarkdownSuccess.value = false;
    }, 3000);
  } catch (_) {
    exportMarkdownError.value =
      "The Markdown file could not be created. Try again.";
    emit("add-log", "The Markdown download did not complete.");
  } finally {
    exportingMarkdown.value = false;
  }
};

const handleExportTXT = async () => {
  if (exportingTXT.value || !props.reportId) return;
  exportingTXT.value = true;
  exportTXTSuccess.value = false;
  exportTXTError.value = "";
  emit("add-log", "Preparing the plain-text download…");
  try {
    downloadResponse(
      reportPlainText(),
      "text/plain;charset=utf-8",
      `ATP_REPORT_${safeFilenameId.value}.txt`,
    );
    exportTXTSuccess.value = true;
    emit("add-log", "Plain text downloaded.");
    window.setTimeout(() => {
      exportTXTSuccess.value = false;
    }, 3000);
  } catch (_) {
    exportTXTError.value =
      "The plain-text file could not be created. Try again.";
    emit("add-log", "The plain-text download did not complete.");
  } finally {
    exportingTXT.value = false;
  }
};

let timer = null;

const stopPolling = () => {
  if (timer) window.clearInterval(timer);
  timer = null;
};

const startPolling = () => {
  stopPolling();
  if (!hasTerminalFailure.value) {
    timer = window.setInterval(fetchLogs, LOG_POLL_INTERVAL_MS);
  }
};

const markTerminalFailure = (kind) => {
  reportFailureKind.value = kind;
  currentSectionIndex.value = null;
  progressMessage.value =
    kind === "generation"
      ? "Report generation stopped"
      : "Report unavailable";
  emit("update-status", "failed");
  stopPolling();
  nextTick(() => terminalAlert.value?.focus());
};

const loadReportDocument = async () => {
  if (!props.reportId || documentRequestActive.value) return false;
  documentRequestActive.value = true;
  try {
    const response = await getReport(props.reportId);
    const document = response?.data ?? response;
    if (!document || typeof document !== "object") {
      throw new Error("The report response was empty.");
    }

    reportDocument.value = document;
    const sections = document.outline?.sections;
    const titles = outlineSectionTitles(document.outline);
    if (titles.length > 0) reportOutline.value = titles;
    if (Array.isArray(sections)) {
      sections.forEach((section, index) => {
        if (typeof section === "object" && section?.content) {
          generatedSections.value[index + 1] = section.content;
        }
      });
    }

    if (document.status === "completed") {
      reportFailureKind.value = "";
      isComplete.value = true;
      reportProgress.value = 100;
      progressMessage.value = "Report ready";
      emit("update-status", "completed");
    } else if (document.status === "failed") {
      markTerminalFailure("generation");
    } else {
      reportFailureKind.value = "";
      emit("update-status", "processing");
    }
    return true;
  } catch (_) {
    markTerminalFailure("load");
    emit("add-log", "The saved report could not be opened.");
    return false;
  } finally {
    documentRequestActive.value = false;
  }
};

const retryReportLoad = async () => {
  if (isRetrying.value) return;
  isRetrying.value = true;
  reportFailureKind.value = "";
  statusFailureCount.value = 0;
  emit("update-status", "processing");
  try {
    const loaded = await loadReportDocument();
    if (loaded && !hasTerminalFailure.value) {
      startPolling();
      await fetchLogs();
    }
  } finally {
    isRetrying.value = false;
  }
};

const fetchReportEvidence = async () => {
  if (
    !props.reportId ||
    evidenceLoaded.value ||
    isEvidenceLoading.value ||
    evidenceAttempts.value >= EVIDENCE_MAX_ATTEMPTS
  ) {
    return evidenceLoaded.value;
  }

  isEvidenceLoading.value = true;
  evidenceAttempts.value += 1;
  try {
    const response = await getReportEvidence(props.reportId);
    reportEvidence.value = normalizeReportEvidence(response);
    reportEvidenceError.value = "";
    evidenceLoaded.value = true;
    return true;
  } catch (_) {
    reportEvidenceError.value =
      evidenceAttempts.value >= EVIDENCE_MAX_ATTEMPTS
        ? "The within-run trace record is not available for this report."
        : "The report is ready; its trace record is still being saved. Retrying…";
    return false;
  } finally {
    isEvidenceLoading.value = false;
  }
};

const fetchLogs = async () => {
  if (!props.reportId || hasTerminalFailure.value) return;

  const [agentResponse, statusResponse] = await Promise.all([
    getAgentLog(props.reportId, agentLogLine.value).catch(() => null),
    getReportStatus({ report_id: props.reportId }).catch(() => null),
  ]);

  const agentPage = normalizeLogPage(agentResponse);
  if (agentPage.logs.length > 0) {
    const newLogs = agentPage.logs.map((rawLog) => {
      const log = normalizeAgentLogEntry(rawLog);

      if (log.action === "planning_complete") {
        const titles = outlineSectionTitles(log.outline);
        if (titles.length > 0) reportOutline.value = titles;
      }
      if (log.action === "section_start" && log.section_index) {
        currentSectionIndex.value = Number(log.section_index);
      }
      if (log.action === "section_complete" && log.section_index) {
        generatedSections.value[Number(log.section_index)] = log.content;
        currentSectionIndex.value = null;
      }
      if (log.action === "report_complete") {
        isComplete.value = true;
      }

      return log;
    });
    agentLogs.value = [...agentLogs.value, ...newLogs];
    agentLogLine.value = agentPage.nextFromLine;
  }

  const status = statusResponse?.data ?? {};
  if (!statusResponse || !status.status) {
    statusFailureCount.value += 1;
    if (statusFailureCount.value >= 3) {
      markTerminalFailure("load");
    }
    return;
  }
  statusFailureCount.value = 0;

  reportProgress.value = Math.min(
    100,
    Math.max(0, Number(status.progress) || 0),
  );
  progressMessage.value = safeProgressMessage(
    status.status,
    reportProgress.value,
  );

  if (status.status === "completed" || status.already_completed) {
    isComplete.value = true;
    reportProgress.value = 100;
    progressMessage.value = "Report ready";
    emit("update-status", "completed");
    await loadReportDocument();
    const evidenceReady = await fetchReportEvidence();
    if (evidenceReady || evidenceAttempts.value >= EVIDENCE_MAX_ATTEMPTS) {
      stopPolling();
    }
  } else if (status.status === "failed") {
    markTerminalFailure("generation");
  } else if (status.status) {
    emit("update-status", "processing");
  }
};

onMounted(async () => {
  const loaded = await loadReportDocument();
  if (loaded && !hasTerminalFailure.value) {
    startPolling();
    await fetchLogs();
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.decision-report-shell {
  min-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-sans);
  scroll-behavior: smooth;
}

.skip-link {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 10;
  padding: 0.7rem 0.9rem;
  transform: translateY(-180%);
  border: 2px solid var(--ink);
  background: var(--signal);
  color: var(--ink);
  font-weight: 700;
  text-decoration: none;
  transition: transform 180ms var(--ease-out);
}

.skip-link:focus {
  transform: translateY(0);
}

.report-masthead {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(15rem, 20rem);
  gap: clamp(2rem, 6vw, 7rem);
  align-items: end;
  min-height: 24rem;
  padding: clamp(2rem, 5vw, 5.25rem);
  overflow: hidden;
  border-bottom: 0.55rem solid var(--signal);
  background: var(--ink-deep);
  color: var(--paper);
}

.report-masthead::before {
  position: absolute;
  top: 0;
  right: clamp(18rem, 30vw, 29rem);
  width: clamp(4rem, 9vw, 9rem);
  height: 100%;
  background: var(--signal);
  clip-path: polygon(72% 0, 100% 0, 28% 100%, 0 100%);
  content: "";
  opacity: 0.96;
  pointer-events: none;
}

.masthead-copy,
.truth-stamp {
  position: relative;
  z-index: 1;
}

.route-label,
.section-kicker {
  margin: 0 0 1rem;
  font-family: var(--font-display);
  font-size: 0.92rem;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.route-label {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  color: var(--signal);
}

.route-number {
  display: grid;
  width: 2.65rem;
  height: 2.65rem;
  place-items: center;
  border: 2px solid currentColor;
}

.report-masthead h1 {
  max-width: 16ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(3rem, 6.6vw, 6.9rem);
  font-weight: 400;
  letter-spacing: -0.025em;
  line-height: 0.88;
}

.decision-question {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  align-items: baseline;
  max-width: 58rem;
  margin: clamp(2rem, 4vw, 3.3rem) 0 0;
  padding-top: 1rem;
  border-top: 1px solid var(--line-dark);
  color: var(--paper);
  font-size: clamp(1rem, 1.6vw, 1.35rem);
  line-height: 1.4;
}

.decision-question span {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.truth-stamp {
  display: grid;
  align-content: end;
  min-height: 14rem;
  padding: 1.3rem 0 0 1.4rem;
  border-left: 0.45rem solid var(--signal);
}

.truth-kicker {
  align-self: start;
  color: var(--paper-muted);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.truth-stamp strong {
  margin-top: auto;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: clamp(2.3rem, 3.6vw, 4rem);
  font-weight: 400;
  line-height: 0.9;
}

.truth-stamp > span:not(.truth-kicker) {
  margin-top: 0.5rem;
  font-family: var(--font-display);
  font-size: 1.45rem;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.truth-stamp p {
  max-width: 27ch;
  margin: 1.2rem 0 0;
  color: var(--paper-muted);
  font-size: 0.84rem;
  line-height: 1.45;
}

.reading-route {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  background: var(--signal);
  color: var(--ink);
}

.reading-route a {
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: 0.85rem;
  align-items: center;
  min-height: 6.6rem;
  padding: 1.2rem clamp(1rem, 2.6vw, 2.8rem);
  border-right: 2px solid var(--ink);
  color: inherit;
  text-decoration: none;
  transition:
    background-color 180ms var(--ease-out),
    color 180ms var(--ease-out),
    transform 180ms var(--ease-out);
}

.reading-route a:last-child {
  border-right: 0;
}

.reading-route a:hover {
  background: var(--paper-strong);
  color: var(--ink);
  transform: translateY(-0.2rem);
}

.reading-route a > span {
  grid-row: 1 / span 2;
  font-family: var(--font-display);
  font-size: 2.3rem;
}

.reading-route strong {
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 400;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.reading-route small {
  font-size: 0.76rem;
  line-height: 1.3;
}

.terminal-report-alert {
  display: grid;
  grid-template-columns: 4rem minmax(0, 1fr);
  gap: 1.4rem;
  width: min(100% - 2rem, 80rem);
  margin: 2rem auto 0;
  padding: clamp(1.4rem, 3vw, 2.4rem);
  border: 3px solid var(--ink);
  border-top: 0.65rem solid var(--error);
  background: var(--paper-strong);
  box-shadow: 0.7rem 0.7rem 0 var(--line-light);
}

.terminal-report-alert > div:first-child {
  display: grid;
  width: 3.7rem;
  height: 3.7rem;
  place-items: center;
  background: var(--error);
  color: var(--paper-strong);
  font-family: var(--font-display);
  font-size: 2.2rem;
}

.terminal-report-alert .section-kicker {
  margin: 0 0 0.35rem;
  color: var(--error);
}

.terminal-report-alert h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 4.5vw, 4.5rem);
  font-weight: 400;
  line-height: 0.95;
}

.terminal-report-alert p:not(.section-kicker) {
  max-width: 56ch;
  margin: 0.9rem 0 0;
  color: var(--ink-muted);
  line-height: 1.55;
}

.recovery-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.35rem;
}

.recovery-actions .action-button {
  min-width: 13rem;
}

.generation-strip {
  display: grid;
  grid-template-columns: minmax(12rem, 20rem) minmax(8rem, 1fr) auto;
  gap: 1.25rem;
  align-items: center;
  padding: 1rem clamp(1rem, 4vw, 4rem);
  border-bottom: 2px solid var(--ink);
  background: var(--paper-strong);
}

.generation-strip > div:first-child {
  display: grid;
  gap: 0.15rem;
}

.generation-strip span,
.generation-strip b {
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.generation-strip strong {
  font-size: 0.82rem;
  font-weight: 500;
}

.progress-track {
  height: 0.6rem;
  overflow: hidden;
  border: 1px solid var(--ink);
  background: var(--paper);
}

.progress-track span {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: left;
  background: var(--signal);
  transition: transform 500ms var(--ease-out);
}

.report-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(19rem, 25rem);
  gap: clamp(2.5rem, 6vw, 7rem);
  width: min(100%, 96rem);
  margin: 0 auto;
  padding: clamp(3rem, 6vw, 6.5rem) clamp(1rem, 5vw, 5rem);
  outline: none;
}

.findings-intro {
  max-width: 53rem;
  margin-bottom: clamp(3rem, 6vw, 6rem);
}

.section-kicker {
  color: var(--signal-deep);
}

.findings-intro h2,
.trace-section h2,
.limits-section h2,
.next-step-section h2 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 400;
  letter-spacing: 0.005em;
  line-height: 0.98;
}

.findings-intro h2 {
  max-width: 18ch;
  font-size: clamp(2.7rem, 5vw, 5.2rem);
}

.findings-intro > p:last-child {
  max-width: 54ch;
  margin: 1.5rem 0 0;
  color: var(--ink-muted);
  font-size: 1.08rem;
  line-height: 1.6;
}

.finding-section {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  gap: clamp(1.3rem, 3vw, 3rem);
  padding: 0 0 clamp(3.3rem, 6vw, 6rem);
}

.finding-route {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100%;
}

.finding-route span {
  display: grid;
  flex: 0 0 auto;
  width: 3.65rem;
  height: 3.65rem;
  place-items: center;
  border: 3px solid var(--ink);
  background: var(--signal);
  font-family: var(--font-display);
  font-size: 1.55rem;
}

.finding-route i {
  width: 3px;
  min-height: 3rem;
  flex: 1;
  background: var(--ink);
}

.finding-section:last-child .finding-route i {
  background: repeating-linear-gradient(
    to bottom,
    var(--ink) 0,
    var(--ink) 0.35rem,
    transparent 0.35rem,
    transparent 0.7rem
  );
}

.finding-copy {
  padding-top: 0.25rem;
  border-top: 3px solid var(--ink);
}

.finding-copy > header {
  padding: 1.2rem 0 1.6rem;
}

.finding-copy > header p {
  margin: 0 0 0.45rem;
  color: var(--signal-deep);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.finding-copy h3 {
  max-width: 28ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.9rem, 3vw, 3.2rem);
  font-weight: 400;
  line-height: 1;
}

.report-prose {
  max-width: 48rem;
  color: #292d2a;
  font-size: 1rem;
  line-height: 1.72;
}

.report-prose p,
.report-prose ul,
.report-prose ol,
.report-prose blockquote {
  margin: 0 0 1.25rem;
}

.report-prose h4 {
  margin: 2rem 0 0.7rem;
  font-family: var(--font-display);
  font-size: 1.45rem;
  font-weight: 400;
  letter-spacing: 0.02em;
}

.report-prose ul,
.report-prose ol {
  padding-left: 1.4rem;
}

.report-prose li {
  margin-bottom: 0.5rem;
  padding-left: 0.3rem;
}

.report-prose li::marker {
  color: var(--signal-deep);
  font-weight: 700;
}

.report-prose blockquote {
  padding: 1rem 0 1rem 1.2rem;
  border-left: 0.35rem solid var(--signal);
  color: var(--ink-muted);
  font-size: 1.05rem;
}

.finding-pending {
  display: flex;
  gap: 0.9rem;
  align-items: center;
  min-height: 4.5rem;
  color: var(--ink-muted);
}

.finding-pending span,
.rail-state.is-loading span {
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
  border: 2px solid var(--line-light);
  border-top-color: var(--ink);
  animation: report-spin 800ms linear infinite;
}

.finding-pending p {
  margin: 0;
}

.report-message {
  display: grid;
  gap: 0.35rem;
  padding: 1.3rem;
  border: 2px solid var(--ink);
}

.report-message-error {
  border-left: 0.6rem solid var(--error);
}

.report-message span {
  color: var(--ink-muted);
}

.report-skeleton {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  gap: 2rem;
}

.skeleton-route {
  width: 3.65rem;
  height: 3.65rem;
  border: 3px solid var(--ink);
  background: var(--signal);
}

.report-skeleton > div:last-child {
  display: grid;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 3px solid var(--ink);
}

.report-skeleton strong {
  font-family: var(--font-display);
  font-size: 1.7rem;
  font-weight: 400;
}

.report-skeleton span {
  color: var(--ink-muted);
}

.report-skeleton i {
  display: block;
  height: 0.7rem;
  max-width: 36rem;
  background: var(--line-light);
  animation: skeleton-shift 1.5s ease-in-out infinite alternate;
}

.report-skeleton i:nth-of-type(2) {
  width: 78%;
}

.report-skeleton i:nth-of-type(3) {
  width: 58%;
}

.report-rail {
  min-width: 0;
}

.trace-section {
  border: 3px solid var(--ink);
  background: var(--paper-strong);
  box-shadow: 0.65rem 0.65rem 0 var(--line-light);
}

.trace-section > header {
  padding: 1.5rem;
  border-bottom: 3px solid var(--ink);
  background: var(--signal);
}

.trace-section .section-kicker {
  color: var(--ink);
}

.trace-section h2,
.limits-section h2,
.next-step-section h2 {
  font-size: clamp(2rem, 3vw, 2.9rem);
}

.trace-section > header > p:last-child {
  margin: 1rem 0 0;
  font-size: 0.84rem;
  line-height: 1.48;
}

.rail-state {
  padding: 1.4rem;
  color: var(--ink-muted);
  font-size: 0.86rem;
  line-height: 1.5;
}

.rail-state.is-loading {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.rail-state.is-error {
  border-left: 0.45rem solid var(--error);
  color: var(--ink);
}

.trace-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.trace-list > li {
  position: relative;
  display: grid;
  grid-template-columns: 1.7rem minmax(0, 1fr);
  gap: 0.8rem;
  padding: 1.3rem 1.3rem 0 0.9rem;
  border-bottom: 1px solid var(--line-light);
}

.trace-list > li:last-child {
  border-bottom: 0;
}

.trace-marker {
  position: relative;
  width: 1rem;
  height: 1rem;
  margin: 0.15rem auto 0;
  border: 3px solid var(--ink);
  background: var(--signal);
}

.trace-list > li:not(:last-child) .trace-marker::after {
  position: absolute;
  top: 0.7rem;
  left: 50%;
  width: 2px;
  height: calc(100% + 9.5rem);
  transform: translateX(-50%);
  background: var(--ink);
  content: "";
}

.trace-list article {
  min-width: 0;
  padding-bottom: 1.3rem;
}

.trace-list article > header,
.trace-list article > footer {
  display: flex;
  gap: 0.7rem;
  align-items: baseline;
  justify-content: space-between;
}

.trace-list article > header strong {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 400;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.trace-list article > header strong small {
  color: var(--signal-deep);
  font-family: var(--font-sans);
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.065em;
}

.trace-list article > header span,
.trace-list article > footer {
  color: var(--ink-muted);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  text-transform: uppercase;
}

.trace-excerpt {
  margin: 0.75rem 0;
  overflow-wrap: anywhere;
  font-size: 0.84rem;
  line-height: 1.5;
}

.trace-meaning {
  margin: 0 0 0.75rem;
  padding-left: 0.75rem;
  border-left: 0.25rem solid var(--signal);
  color: var(--ink-muted);
  font-size: 0.74rem;
  line-height: 1.45;
}

.trace-list article > footer b {
  color: var(--ink);
  font-weight: 600;
}

.trace-toggle {
  width: 100%;
  min-height: 3rem;
  justify-content: space-between;
  border: 0;
  border-top: 3px solid var(--ink);
  border-radius: 0;
  background: var(--paper-strong);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.trace-toggle::after {
  content: "↓";
  font-family: var(--font-sans);
  font-weight: 700;
}

.trace-toggle[aria-expanded="true"]::after {
  content: "↑";
}

.trace-toggle:hover {
  background: var(--ink);
  color: var(--paper);
}

.limits-section {
  margin-top: 4rem;
  padding: 1.6rem;
  border-top: 0.6rem solid var(--signal);
  background: var(--ink);
  color: var(--paper);
}

.limits-section .section-kicker {
  color: var(--signal);
}

.limits-section ul {
  margin: 1.5rem 0 0;
  padding: 0;
  list-style: none;
}

.limits-section li {
  position: relative;
  padding: 0.9rem 0 0.9rem 1.6rem;
  border-top: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.86rem;
  line-height: 1.5;
}

.limits-section li::before {
  position: absolute;
  top: 1.25rem;
  left: 0;
  width: 0.55rem;
  height: 0.55rem;
  background: var(--signal);
  content: "";
}

.next-step-section {
  margin-top: 4rem;
  padding-top: 1.5rem;
  border-top: 3px solid var(--ink);
}

.next-step-section > p:not(.section-kicker) {
  margin: 1rem 0 1.4rem;
  color: var(--ink-muted);
  font-size: 0.88rem;
  line-height: 1.5;
}

.primary-actions {
  display: grid;
  gap: 0.65rem;
}

.action-button {
  min-height: 3.25rem;
  justify-content: space-between;
  border: 2px solid var(--ink);
  border-radius: 0;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 400;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.action-button::after {
  content: "→";
  font-family: var(--font-sans);
  font-size: 1.25rem;
  font-weight: 700;
}

.action-button.is-primary {
  background: var(--signal);
  color: var(--ink);
}

.action-button.is-dark {
  background: var(--ink);
  color: var(--paper);
}

.action-button:hover:not(:disabled) {
  border-color: var(--ink);
  background: var(--paper-strong);
  color: var(--ink);
  transform: translateX(0.25rem);
}

.more-exports {
  margin-top: 1rem;
  border-top: 1px solid var(--line-light);
}

.more-exports summary {
  padding: 0.9rem 0;
  color: var(--ink-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}

.more-exports > div {
  display: grid;
  border-top: 1px solid var(--line-light);
}

.export-option {
  display: grid;
  border-bottom: 1px solid var(--line-light);
}

.text-action {
  justify-content: flex-start;
  padding: 0.8rem 0;
  border: 0;
  background: transparent;
  color: var(--ink);
  font-size: 0.78rem;
  text-align: left;
}

.text-action:hover:not(:disabled) {
  border-bottom-color: var(--ink);
  background: transparent;
  color: var(--ink);
  transform: translateX(0.2rem);
}

.export-feedback {
  margin: 0;
  padding: 0.7rem 0.8rem;
  font-size: 0.76rem;
  line-height: 1.4;
}

.export-feedback.is-error {
  border-left: 0.35rem solid var(--error);
  background: rgba(189, 73, 61, 0.09);
  color: #7f2f27;
}

.generation-disclosure {
  border-top: 0.55rem solid var(--signal);
  background: var(--ink-deep);
  color: var(--paper);
}

.generation-disclosure > summary {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  min-height: 5.5rem;
  padding: 1.2rem clamp(1rem, 5vw, 5rem);
  list-style: none;
  cursor: pointer;
}

.generation-disclosure > summary::-webkit-details-marker {
  display: none;
}

.generation-disclosure > summary::before {
  display: grid;
  width: 2rem;
  height: 2rem;
  flex: 0 0 auto;
  place-items: center;
  border: 2px solid var(--signal);
  color: var(--signal);
  content: "+";
  font-size: 1.25rem;
}

.generation-disclosure[open] > summary::before {
  content: "−";
}

.generation-disclosure > summary span {
  margin-right: auto;
  font-family: var(--font-display);
  font-size: 1.25rem;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.generation-disclosure > summary small {
  color: var(--paper-dim);
  font-family: var(--font-mono);
  font-size: 0.65rem;
  text-transform: uppercase;
}

.generation-grid {
  display: grid;
  grid-template-columns: minmax(14rem, 0.75fr) minmax(20rem, 1.5fr) minmax(17rem, 1fr);
  gap: 1px;
  border-top: 1px solid var(--line-dark);
  background: var(--line-dark);
}

.generation-grid > section {
  min-width: 0;
  padding: clamp(1rem, 3vw, 2.5rem);
  background: var(--ink-deep);
}

.generation-grid h2 {
  margin: 0 0 1.2rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.identifier-record dl {
  margin: 0;
}

.identifier-record dl > div {
  padding: 0.9rem 0;
  border-top: 1px solid var(--line-dark);
}

.identifier-record dt {
  margin-bottom: 0.3rem;
  color: var(--paper-dim);
  font-size: 0.68rem;
  text-transform: uppercase;
}

.identifier-record dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: 0.72rem;
}

.raw-entry {
  border-top: 1px solid var(--line-dark);
}

.raw-entry > summary {
  display: grid;
  grid-template-columns: 4rem minmax(8rem, 1fr);
  gap: 0.7rem;
  padding: 0.85rem 0;
  color: var(--paper-muted);
  font-size: 0.68rem;
  cursor: pointer;
}

.raw-entry > summary strong {
  color: var(--paper);
  font-weight: 500;
  text-transform: uppercase;
}

.raw-entry > div {
  padding: 0.5rem 0 1rem;
}

.raw-entry > div p {
  margin: 0;
  color: var(--paper-dim);
  font-size: 0.72rem;
  line-height: 1.5;
}

.raw-empty {
  color: var(--paper-dim);
  font-size: 0.78rem;
}

@keyframes report-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes skeleton-shift {
  from {
    opacity: 0.38;
    transform: scaleX(0.94);
    transform-origin: left;
  }
  to {
    opacity: 0.85;
    transform: scaleX(1);
    transform-origin: left;
  }
}

@media (max-width: 1100px) {
  .report-masthead {
    grid-template-columns: minmax(0, 1fr) minmax(14rem, 17rem);
  }

  .report-masthead::before {
    right: 16rem;
  }

  .report-grid {
    grid-template-columns: minmax(0, 1fr) minmax(18rem, 21rem);
    gap: 3rem;
  }

  .generation-grid {
    grid-template-columns: 1fr 1.5fr;
  }

  .console-record {
    grid-column: 1 / -1;
  }
}

@media (max-width: 820px) {
  .report-masthead {
    grid-template-columns: 1fr;
    gap: 2.5rem;
  }

  .report-masthead::before {
    top: auto;
    right: 0;
    bottom: 0;
    width: 35%;
    height: 4rem;
    clip-path: polygon(18% 0, 100% 0, 100% 100%, 0 100%);
  }

  .truth-stamp {
    min-height: 0;
  }

  .reading-route {
    grid-template-columns: 1fr;
  }

  .reading-route a {
    min-height: 5.3rem;
    border-right: 0;
    border-bottom: 2px solid var(--ink);
  }

  .reading-route a:last-child {
    border-bottom: 0;
  }

  .generation-strip {
    grid-template-columns: 1fr auto;
  }

  .progress-track {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .report-grid {
    grid-template-columns: 1fr;
  }

  .report-rail {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2.5rem 1.5rem;
  }

  .trace-section {
    grid-column: 1 / -1;
  }

  .limits-section,
  .next-step-section {
    margin-top: 0;
  }
}

@media (max-width: 600px) {
  .terminal-report-alert {
    grid-template-columns: 1fr;
    width: calc(100% - 1rem);
    margin-top: 0.5rem;
    box-shadow: none;
  }

  .recovery-actions {
    display: grid;
  }

  .recovery-actions .action-button {
    width: 100%;
    min-width: 0;
  }

  .report-masthead {
    min-height: 0;
    padding: 2rem 1rem 3.5rem;
  }

  .report-masthead h1 {
    font-size: clamp(3rem, 16vw, 4.7rem);
  }

  .decision-question {
    grid-template-columns: 1fr;
    gap: 0.45rem;
  }

  .truth-stamp strong {
    font-size: 2.7rem;
  }

  .reading-route a {
    padding-inline: 1rem;
  }

  .report-grid {
    padding: 3.5rem 1rem;
  }

  .finding-section,
  .report-skeleton {
    grid-template-columns: 2.7rem minmax(0, 1fr);
    gap: 0.9rem;
  }

  .finding-route span,
  .skeleton-route {
    width: 2.65rem;
    height: 2.65rem;
    border-width: 2px;
    font-size: 1.1rem;
  }

  .finding-route i {
    width: 2px;
  }

  .finding-copy h3 {
    font-size: 2rem;
  }

  .report-rail {
    grid-template-columns: 1fr;
  }

  .trace-section,
  .limits-section,
  .next-step-section {
    grid-column: auto;
  }

  .limits-section,
  .next-step-section {
    margin-top: 1rem;
  }

  .generation-disclosure > summary {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .generation-disclosure > summary small {
    width: 100%;
    padding-left: 3rem;
  }

  .generation-grid {
    grid-template-columns: 1fr;
  }

  .console-record {
    grid-column: auto;
  }

  .raw-entry > summary {
    grid-template-columns: 3.5rem minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .skip-link,
  .reading-route a,
  .progress-track span,
  .action-button,
  .text-action {
    transition: none;
  }

  .finding-pending span,
  .rail-state.is-loading span,
  .report-skeleton i {
    animation: none;
  }
}
</style>

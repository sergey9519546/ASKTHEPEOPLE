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
        <p>No result on this page is a vote, human observation, or population estimate.</p>
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
              The run is generated, not human evidence, and does not express
              likelihood.
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
  background-color: transparent;
  color: var(--paper);
  font-family: var(--font-sans);
  scroll-behavior: smooth;
}

.skip-link {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 50;
  padding: 0.75rem 1.25rem;
  transform: translateY(-200%);
  background: var(--ink-deep);
  backdrop-filter: none;
  border: 1px solid var(--signal);
  border-radius: var(--radius-md);
  color: var(--signal);
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}

.skip-link:focus {
  transform: translateY(0);
}

/* Masthead */
.report-masthead {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 24rem);
  gap: clamp(2rem, 6vw, 5rem);
  align-items: end;
  min-height: 24rem;
  padding: clamp(2rem, 5vw, 5rem);
  overflow: hidden;
  background: var(--ink-soft);
  border-bottom: 1px solid rgba(242, 235, 221, 0.08);
}

.report-masthead::before {
  content: none;
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
  font-size: 0.85rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.route-label {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: var(--signal);
}

.route-number {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  background: var(--signal-tint);
  border: 1px solid var(--signal-rule);
  border-radius: 50%;
  box-shadow: none;
}

.report-masthead h1 {
  max-width: 18ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.5rem, 5vw, 5.5rem);
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.05;
  color: var(--paper);
}

.decision-question {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 58rem;
  margin: clamp(2rem, 4vw, 3.3rem) 0 0;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(242,235,221,0.1);
  color: var(--paper);
  font-size: clamp(1rem, 1.4vw, 1.25rem);
  line-height: 1.5;
}

.decision-question span {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* Truth Stamp */
.truth-stamp {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 2rem;
  background: var(--ink-deep);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-lg);
  box-shadow: none;
  position: relative;
  overflow: hidden;
}
.truth-stamp::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 4px; height: 100%;
  background: var(--signal);
  box-shadow: none;
}

.truth-kicker {
  color: var(--paper-muted);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: auto;
}

.truth-stamp strong {
  margin-top: 2rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: clamp(2rem, 3vw, 3.5rem);
  font-weight: 500;
  line-height: 1;
}

.truth-stamp > span:not(.truth-kicker) {
  margin-top: 0.5rem;
  font-family: var(--font-display);
  font-size: 1.2rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--paper);
}

.truth-stamp p {
  margin: 1rem 0 0;
  color: var(--paper-muted);
  font-size: 0.85rem;
  line-height: 1.5;
}

/* Reading Route */
.reading-route {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: rgba(242,235,221,0.05);
  border-bottom: 1px solid rgba(242,235,221,0.08);
}

.reading-route a {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 1.5rem 2rem;
  background: var(--ink-deep);
  backdrop-filter: none;
  color: var(--paper);
  text-decoration: none;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.reading-route a::before {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0; height: 2px;
  background: var(--signal);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.reading-route a:hover {
  background: var(--ink-raised);
}
.reading-route a:hover::before {
  transform: scaleX(1);
}

.reading-route a > span {
  font-family: var(--font-display);
  font-size: 1.2rem;
  color: var(--signal);
  margin-bottom: 0.5rem;
}

.reading-route strong {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.reading-route small {
  font-size: 0.8rem;
  color: var(--paper-muted);
}

/* Generation Strip */
.generation-strip {
  display: grid;
  grid-template-columns: minmax(12rem, 20rem) minmax(8rem, 1fr) auto;
  gap: 1.5rem;
  align-items: center;
  padding: 1.25rem clamp(2rem, 5vw, 5rem);
  background: var(--ink-soft);
  backdrop-filter: none;
  border-bottom: 1px solid rgba(242,235,221,0.08);
}

.generation-strip > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.generation-strip span,
.generation-strip b {
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--paper-muted);
}

.generation-strip strong {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--signal);
  animation: pulse-text 2s infinite;
}

@keyframes pulse-text {
  0%, 100% { opacity: 1; text-shadow: none; }
  50% { opacity: 0.7; text-shadow: none; }
}

.progress-track {
  height: 6px;
  background: rgba(242,235,221,0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-track span {
  display: block;
  height: 100%;
  background: var(--signal);
  box-shadow: 0 0 10px var(--signal);
  transform-origin: left;
  transition: transform 0.5s ease-out;
}

/* Grid Layout */
.report-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(22rem, 28rem);
  gap: clamp(3rem, 6vw, 6rem);
  width: min(100%, 100rem);
  margin: 0 auto;
  padding: clamp(3rem, 6vw, 6rem) clamp(2rem, 5vw, 5rem);
  outline: none;
}

/* Findings Section */
.findings-intro {
  margin-bottom: clamp(4rem, 8vw, 6rem);
}

.findings-intro h2,
.trace-section h2,
.limits-section h2,
.next-step-section h2 {
  font-family: var(--font-display);
  font-weight: 500;
  letter-spacing: 0;
  line-height: 1.1;
  color: var(--paper);
  margin: 0;
}

.findings-intro h2 {
  font-size: clamp(2.5rem, 4vw, 4.5rem);
}

.findings-intro > p:last-child {
  margin: 1.5rem 0 0;
  color: var(--paper-muted);
  font-size: 1.1rem;
  line-height: 1.6;
}

.finding-section {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr);
  gap: clamp(1.5rem, 4vw, 3rem);
  margin-bottom: 4rem;
}

.finding-route {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.finding-route span {
  display: grid;
  width: 3rem;
  height: 3rem;
  place-items: center;
  background: var(--ink-deep);
  border: 2px solid rgba(242,235,221,0.1);
  border-radius: 50%;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 1.2rem;
  z-index: 2;
  transition: all 0.3s ease;
}

.finding-section.is-drafting .finding-route span,
.finding-section:not(.is-drafting):has(.report-prose) .finding-route span {
  border-color: var(--signal);
  color: var(--signal);
  box-shadow: none;
}

.finding-section.is-drafting .finding-route span {
  animation: pulse-glow 2s infinite;
}

@keyframes pulse-glow {
  0%, 100% { outline-offset: 0.15rem; }
  50% { outline-offset: 0.35rem; }
}

.finding-route i {
  width: 2px;
  flex: 1;
  background: rgba(242,235,221,0.1);
  margin-top: 0.5rem;
}

.finding-section:last-child .finding-route i {
  background: repeating-linear-gradient(to bottom, rgba(242,235,221,0.1) 0, rgba(242,235,221,0.1) 4px, transparent 4px, transparent 8px);
}

.finding-copy {
  background: var(--ink-deep);
  backdrop-filter: none;
  border: 1px solid rgba(242,235,221,0.05);
  border-radius: var(--radius-lg);
  padding: 2.5rem;
  transition: all 0.3s ease;
}

.finding-copy:hover {
  background: var(--ink-raised);
  border-color: rgba(242,235,221,0.1);
}

.finding-copy > header {
  margin-bottom: 2rem;
}

.finding-copy > header p {
  margin: 0 0 0.75rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.finding-copy h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 3vw, 2.5rem);
  font-weight: 500;
  line-height: 1.2;
  color: var(--paper);
}

.report-prose {
  color: var(--paper-muted);
  font-size: 1.05rem;
  line-height: 1.7;
}

.report-prose p,
.report-prose ul,
.report-prose ol,
.report-prose blockquote {
  margin: 0 0 1.5rem;
}

.report-prose h4 {
  margin: 2.5rem 0 1rem;
  font-family: var(--font-display);
  font-size: 1.4rem;
  color: var(--paper);
  font-weight: 500;
}

.report-prose ul, .report-prose ol {
  padding-left: 1.5rem;
}

.report-prose li {
  margin-bottom: 0.75rem;
}

.report-prose li::marker {
  color: var(--signal);
}

.report-prose blockquote {
  padding: 1.25rem 1.5rem;
  background: var(--signal-faint);
  border-left: 3px solid var(--signal);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--signal-soft);
  font-style: italic;
}

/* Side Rail */
.trace-section {
  background: var(--ink-deep);
  backdrop-filter: none;
  border: 1px solid rgba(242,235,221,0.08);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.trace-section > header {
  padding: 2rem;
  background: var(--ink-raised);
  border-bottom: 1px solid rgba(242,235,221,0.05);
}

.trace-section h2, .limits-section h2, .next-step-section h2 {
  font-size: 1.8rem;
  margin-bottom: 1rem;
}

.trace-section > header > p:last-child {
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.9rem;
  line-height: 1.5;
}

.trace-list {
  list-style: none;
  margin: 0; padding: 0;
}

.trace-list > li {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid rgba(242,235,221,0.05);
  transition: background 0.2s;
}
.trace-list > li:hover {
  background: rgba(242,235,221,0.02);
}

.trace-list article > header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.trace-list article > header strong {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-family: var(--font-display);
  color: var(--paper);
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.05em;
}

.trace-list article > header strong small {
  color: var(--signal);
  font-size: 0.7rem;
}

.trace-excerpt {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--paper);
  margin-bottom: 1rem;
}

.trace-meaning {
  padding: 1rem;
  background: rgba(0,0,0,0.2);
  border-left: 2px solid var(--signal);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--paper-muted);
  font-size: 0.85rem;
  line-height: 1.5;
}

.limits-section {
  margin-top: 3rem;
  padding: 2rem;
  background: var(--ink-deep);
  backdrop-filter: none;
  border: 1px solid rgba(242,235,221,0.08);
  border-radius: var(--radius-lg);
}

.limits-section ul {
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0;
}

.limits-section li {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 1rem;
  color: var(--paper-muted);
  font-size: 0.95rem;
  line-height: 1.5;
}

.limits-section li::before {
  content: '';
  position: absolute;
  top: 0.5rem; left: 0;
  width: 6px; height: 6px;
  background: var(--signal);
  border-radius: 50%;
}

.next-step-section {
  margin-top: 3rem;
}

.action-button {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 1.25rem 2rem;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.action-button::after {
  content: '→';
  font-family: var(--font-sans);
  font-size: 1.25rem;
  transition: transform 0.2s;
}

.action-button:hover:not(:disabled)::after {
  transform: translateX(5px);
}

.action-button.is-primary {
  background: var(--signal);
  color: var(--ink);
  box-shadow: none;
}

.action-button.is-primary:hover:not(:disabled) {
  background: var(--signal-strong);
  box-shadow: 0.35rem 0.35rem 0 var(--signal-deep);
  transform: translateY(-2px);
}

.action-button.is-dark {
  background: var(--ink-raised);
  color: var(--paper);
  border: 1px solid rgba(242,235,221,0.1);
  margin-top: 1rem;
}

.action-button.is-dark:hover:not(:disabled) {
  background: var(--ink-raised);
  border-color: rgba(242,235,221,0.2);
}

.terminal-report-alert {
  display: flex;
  gap: 2rem;
  margin: 3rem auto;
  padding: 3rem;
  max-width: 800px;
  background: var(--signal-faint);
  border: 1px solid var(--signal-rule);
  border-radius: var(--radius-lg);
  backdrop-filter: none;
}
.terminal-report-alert > div:first-child {
  font-size: 3rem;
  color: var(--signal-soft);
  background: var(--signal-tint);
  width: 5rem; height: 5rem;
  display: flex; justify-content: center; align-items: center;
  border-radius: 50%;
  flex-shrink: 0;
}
.recovery-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.5rem;
}

.report-message {
  padding: 2rem;
  background: var(--signal-faint);
  border-left: 4px solid var(--signal);
  border-radius: var(--radius-md);
  margin-bottom: 2rem;
}

.report-skeleton {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr);
  gap: 2rem;
  opacity: 0.5;
}

.skeleton-route {
  width: 3rem; height: 3rem;
  border-radius: 50%;
  background: rgba(242,235,221,0.1);
  animation: pulse-glow 2s infinite;
}

.report-skeleton > div:last-child {
  display: flex; flex-direction: column; gap: 1rem;
}

.report-skeleton i {
  height: 1rem; background: rgba(242,235,221,0.1); border-radius: var(--radius-sm);
  animation: pulse-glow 2s infinite;
}

.finding-pending {
  display: flex; align-items: center; gap: 1rem;
  color: var(--paper-muted);
}
.finding-pending span {
  width: 1.5rem; height: 1.5rem;
  border: 2px solid rgba(242,235,221,0.1);
  border-top-color: var(--signal);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1024px) {
  .report-masthead {
    grid-template-columns: 1fr;
    padding: 3rem 2rem;
  }
  .truth-stamp {
    margin-top: 2rem;
  }
  .report-grid {
    grid-template-columns: 1fr;
  }
}
</style>

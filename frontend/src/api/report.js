import service from "./index";

export const normalizeLogPage = (response) => {
  const payload = response?.data;
  const page = Array.isArray(payload) ? { logs: payload } : payload || {};
  const logs = Array.isArray(page.logs) ? page.logs : [];
  const fromLine = Number.isFinite(Number(page.from_line))
    ? Number(page.from_line)
    : 0;
  return {
    logs,
    fromLine,
    nextFromLine: fromLine + logs.length,
    totalLines: Number.isFinite(Number(page.total_lines))
      ? Number(page.total_lines)
      : fromLine + logs.length,
    hasMore: Boolean(page.has_more),
  };
};

export const normalizeAgentLogEntry = (entry = {}) => {
  const details =
    entry.details && typeof entry.details === "object" ? entry.details : {};
  const content =
    details.content ?? details.response ?? entry.content ?? entry.response ?? "";
  return {
    ...entry,
    ...details,
    details,
    tool_name: details.tool_name ?? entry.tool_name ?? "",
    params: details.parameters ?? details.params ?? entry.params ?? null,
    result: details.result ?? entry.result ?? "",
    content,
    final_answer:
      details.has_final_answer ?? entry.final_answer ?? entry.action === "section_complete",
    thinking:
      entry.action === "llm_response" &&
      !(details.has_final_answer ?? entry.final_answer),
  };
};

export const outlineSectionTitles = (outline) => {
  const sections = Array.isArray(outline)
    ? outline
    : Array.isArray(outline?.sections)
      ? outline.sections
      : [];
  return sections
    .map((section) => (typeof section === "string" ? section : section?.title))
    .filter(Boolean);
};

export const normalizeReportEvidence = (response) => {
  const payload = response?.data ?? response ?? {};
  const evidence = Array.isArray(payload)
    ? payload
    : Array.isArray(payload.evidence)
      ? payload.evidence
      : [];

  return evidence
    .filter((item) => item && typeof item === "object")
    .map((item, index) => {
      const { claim_id: legacyClaimId, ...record } = item;
      const traceId =
        String(item.trace_id || legacyClaimId || "") ||
        `within_run_trace_${index + 1}`;
      return {
        ...record,
        trace_id: traceId.replace("_claim_", "_trace_"),
        source_type: String(item.source_type || "synthetic_observation"),
        excerpt: String(item.excerpt || ""),
        human_respondents: Number(item.human_respondents) || 0,
        interpretation:
          String(item.interpretation || "") ||
          "Generated within this simulation run; not observed human behavior.",
      };
    });
};

/**
 * Start report generation
 * @param {Object} data - { simulation_id, force_regenerate? }
 */
export const generateReport = (data) => {
  return service.post("/api/report/generate", data);
};

/**
 * Get report generation status
 * @param {Object} params - { report_id?, task_id?, simulation_id? }
 */
export const getReportStatus = (params = {}) => {
  return service.get(`/api/report/generate/status`, { params });
};

/**
 * Get Agent logs (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start line for retrieval
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/agent-log`, {
    params: { from_line: fromLine },
  });
};

/**
 * Get console logs (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start line for retrieval
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/console-log`, {
    params: { from_line: fromLine },
  });
};

/**
 * Get report details
 * @param {string} reportId
 */
export const getReport = (reportId) => {
  return service.get(`/api/report/${reportId}`);
};

/**
 * Get post-hoc related run records (not citations or independent evidence).
 * @param {string} reportId
 */
export const getReportEvidence = (reportId) => {
  return service.get(`/api/report/${reportId}/related-records`);
};

/**
 * Chat with Report Agent
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const chatWithReport = (data) => {
  return service.post("/api/report/chat", data);
};

/**
 * Export report as PDF
 * @param {string} reportId
 */
export const exportReportPDF = (reportId) => {
  return service.get(`/api/report/${reportId}/export/pdf`, {
    responseType: "blob",
  });
};

/**
 * Export report as CSV
 * @param {string} reportId
 */
export const exportReportCSV = (reportId) => {
  return service.get(`/api/report/${reportId}/export/csv`, {
    responseType: "blob",
  });
};

/**
 * Export report as Executive HTML Slide Deck
 * @param {string} reportId
 */
export const exportReportExecutive = (reportId) => {
  return service.get(`/api/report/${reportId}/export/executive`, {
    responseType: "blob",
  });
};

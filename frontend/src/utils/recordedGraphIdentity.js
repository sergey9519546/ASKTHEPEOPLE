export const HISTORICAL_GRAPH_UNAVAILABLE_MESSAGE =
  "The source map recorded for this run is no longer the project's current source map.";

export const REPORT_GRAPH_MISMATCH_MESSAGE =
  "The saved report and run do not reference the same source map.";

export class RecordedGraphIdentityError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "RecordedGraphIdentityError";
    this.code = code;
  }
}

const exactIdentifier = (value) =>
  typeof value === "string" && value.length > 0 && value === value.trim()
    ? value
    : null;

export function resolveRecordedGraphIdentity({ project, report, simulation }) {
  const projectId = exactIdentifier(simulation?.project_id);
  const simulationGraphId = exactIdentifier(simulation?.graph_id);
  const projectGraphId = exactIdentifier(project?.graph_id);
  const reportGraphId = report
    ? exactIdentifier(report?.graph_id)
    : simulationGraphId;

  if (report && !reportGraphId) {
    throw new RecordedGraphIdentityError(
      "report_graph_identity_missing",
      "The saved report is missing its recorded source-map identity.",
    );
  }

  if (report && !simulationGraphId) {
    throw new RecordedGraphIdentityError(
      "recorded_graph_identity_missing",
      "The saved run is missing its recorded source-map identity.",
    );
  }

  if (
    report &&
    reportGraphId &&
    simulationGraphId &&
    reportGraphId !== simulationGraphId
  ) {
    throw new RecordedGraphIdentityError(
      "report_graph_scope_mismatch",
      REPORT_GRAPH_MISMATCH_MESSAGE,
    );
  }

  const recordedGraphId = reportGraphId || simulationGraphId;
  if (!projectId || !recordedGraphId) {
    throw new RecordedGraphIdentityError(
      "recorded_graph_identity_missing",
      "The saved run is missing its recorded source-map identity.",
    );
  }

  if (projectGraphId !== recordedGraphId) {
    throw new RecordedGraphIdentityError(
      "recorded_graph_not_current",
      HISTORICAL_GRAPH_UNAVAILABLE_MESSAGE,
    );
  }

  return { projectId, graphId: recordedGraphId };
}

export function recordedGraphReadError(response) {
  if (response?.error === "graph_not_available_for_project") {
    return new RecordedGraphIdentityError(
      "recorded_graph_not_current",
      HISTORICAL_GRAPH_UNAVAILABLE_MESSAGE,
    );
  }
  return new RecordedGraphIdentityError(
    "recorded_graph_read_unavailable",
    "The recorded source map is temporarily unavailable.",
  );
}

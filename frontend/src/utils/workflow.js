const ACTIVE_RUN_STATUSES = new Set(["starting", "running", "stopping"]);
const FINISHED_RUN_STATUSES = new Set([
  "completed",
  "stopped",
  "failed",
  "interrupted",
]);

export const savedRunStatus = (run = {}) =>
  String(run.runner_status || run.status || "idle").toLowerCase();

export const deriveWorkflowStep = (run = {}) => {
  const declaredStep = Number(run.workflow_step);
  if (Number.isInteger(declaredStep) && declaredStep >= 1 && declaredStep <= 5) {
    return declaredStep;
  }

  if (run.report_id) return 4;

  const status = savedRunStatus(run);
  const simulationStatus = String(run.status || "").toLowerCase();
  if (
    ACTIVE_RUN_STATUSES.has(status) ||
    FINISHED_RUN_STATUSES.has(status) ||
    ACTIVE_RUN_STATUSES.has(simulationStatus) ||
    FINISHED_RUN_STATUSES.has(simulationStatus)
  ) {
    return 3;
  }
  return run.simulation_id ? 2 : 1;
};

export const savedRunDestination = (run = {}) => {
  if (run.report_id) {
    return {
      name: "Report",
      params: { reportId: run.report_id },
    };
  }

  const status = savedRunStatus(run);
  const simulationStatus = String(run.status || "").toLowerCase();
  if (
    ACTIVE_RUN_STATUSES.has(status) ||
    FINISHED_RUN_STATUSES.has(status) ||
    ACTIVE_RUN_STATUSES.has(simulationStatus) ||
    FINISHED_RUN_STATUSES.has(simulationStatus)
  ) {
    const destination = {
      name: "SimulationRun",
      params: { simulationId: run.simulation_id },
    };
    if (Number(run.total_rounds) > 0) {
      destination.query = { maxRounds: String(run.total_rounds) };
    }
    return destination;
  }

  if (run.simulation_id) {
    return {
      name: "Simulation",
      params: { simulationId: run.simulation_id },
    };
  }

  return {
    name: "Process",
    params: { projectId: run.project_id },
  };
};

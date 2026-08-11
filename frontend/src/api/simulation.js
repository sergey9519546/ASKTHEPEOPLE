import service from "./index";

/**
 * Create a simulation
 * @param {Object} data - { project_id, graph_id?, enable_twitter?, enable_reddit? }
 */
export const createSimulation = (data) => {
  return service.post("/api/simulation/create", data);
};

/**
 * Prepare simulation environment (async task)
 * @param {Object} data - { simulation_id, entity_types?, use_llm_for_profiles?, parallel_profile_count?, force_regenerate? }
 */
export const prepareSimulation = (data) => {
  return service.post("/api/simulation/prepare", data);
};

/**
 * Query preparation task progress
 * @param {Object} data - { task_id?, simulation_id? }
 */
export const getPrepareStatus = (data) => {
  return service.post("/api/simulation/prepare/status", data);
};

/**
 * Get simulation status
 * @param {string} simulationId
 */
export const getSimulation = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}`);
};

/**
 * Get simulation Agent Profiles
 * @param {string} simulationId
 * @param {string} platform - 'reddit' | 'twitter'
 */
export const getSimulationProfiles = (simulationId, platform = "reddit") => {
  return service.get(`/api/simulation/${simulationId}/profiles`, {
    params: { platform },
  });
};

/**
 * Get Agent Profiles being generated in real-time
 * @param {string} simulationId
 * @param {string} platform - 'reddit' | 'twitter'
 */
export const getSimulationProfilesRealtime = (
  simulationId,
  platform = "reddit",
) => {
  return service.get(`/api/simulation/${simulationId}/profiles/realtime`, {
    params: { platform },
  });
};

/**
 * Get simulation configuration
 * @param {string} simulationId
 */
export const getSimulationConfig = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config`);
};

/**
 * Get simulation configuration being generated in real-time
 * @param {string} simulationId
 * @returns {Promise} Returns config info including metadata and content
 */
export const getSimulationConfigRealtime = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config/realtime`);
};

export const getSimulationPreflight = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/preflight`);
};

export const getSimulationDiagnostics = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/diagnostics`);
};

/**
 * List all simulations
 * @param {string} projectId - Optional, filter by project ID
 */
export const listSimulations = (projectId) => {
  const params = projectId ? { project_id: projectId } : {};
  return service.get("/api/simulation/list", { params });
};

/**
 * Start a simulation
 * @param {Object} data - { simulation_id, platform?, max_rounds?, enable_graph_memory_update? }
 */
export const startSimulation = (data) => {
  return service.post("/api/simulation/start", data);
};

/**
 * Stop a simulation
 * @param {Object} data - { simulation_id }
 */
export const stopSimulation = (data) => {
  return service.post("/api/simulation/stop", data);
};

/**
 * Get aggregate status for a durable runtime control.
 * @param {string} simulationId
 * @param {string} controlId
 */
export const getSimulationControlStatus = (simulationId, controlId) => {
  return service.get(
    `/api/simulation/${simulationId}/control/${controlId}`,
  );
};

/**
 * Get simulation run status in real-time
 * @param {string} simulationId
 */
export const getRunStatus = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status`);
};

/**
 * Get detailed simulation run status (including recent actions)
 * @param {string} simulationId
 */
export const getRunStatusDetail = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status/detail`);
};

/**
 * Get posts from a simulation
 * @param {string} simulationId
 * @param {string} platform - 'reddit' | 'twitter'
 * @param {number} limit - Number of results
 * @param {number} offset - Offset for pagination
 */
export const getSimulationPosts = (
  simulationId,
  platform = "reddit",
  limit = 50,
  offset = 0,
) => {
  return service.get(`/api/simulation/${simulationId}/posts`, {
    params: { platform, limit, offset },
  });
};

/**
 * Get simulation timeline (summarised by round)
 * @param {string} simulationId
 * @param {number} startRound - Starting round
 * @param {number} endRound - Ending round
 */
export const getSimulationTimeline = (
  simulationId,
  startRound = 0,
  endRound = null,
) => {
  const params = { start_round: startRound };
  if (endRound !== null) {
    params.end_round = endRound;
  }
  return service.get(`/api/simulation/${simulationId}/timeline`, { params });
};

/**
 * Get Agent statistics
 * @param {string} simulationId
 */
export const getAgentStats = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/agent-stats`);
};

/**
 * Get simulation action history
 * @param {string} simulationId
 * @param {Object} params - { limit, offset, platform, agent_id, round_num }
 */
export const getSimulationActions = (simulationId, params = {}) => {
  return service.get(`/api/simulation/${simulationId}/actions`, { params });
};

/**
 * Close simulation environment (graceful shutdown)
 * @param {Object} data - { simulation_id, timeout? }
 */
export const closeSimulationEnv = (data) => {
  return service.post("/api/simulation/close-env", data);
};

/**
 * Get simulation environment status
 * @param {Object} data - { simulation_id }
 */
export const getEnvStatus = (data) => {
  return service.post("/api/simulation/env-status", data);
};

/**
 * Ask one or more synthetic profiles a follow-up question.
 * @param {Object} data - { simulation_id, questions: [{ agent_id, prompt }] }
 */
export const askSyntheticProfiles = (data) => {
  return service.post("/api/simulation/generated-response/batch", data);
};

// Backwards-compatible export for existing integrations.
export const interviewAgents = askSyntheticProfiles;

/**
 * Export generated profile responses as CSV
 * @param {string} simulationId
 * @param {Array} results
 */
export const exportGeneratedResponsesCSV = (simulationId, results) => {
  return service.post(
    `/api/simulation/${simulationId}/export/generated-responses`,
    { results },
    { responseType: "blob" },
  );
};

/**
 * Get simulation history (with project details)
 * Used for home page history display
 * @param {number} limit - Result count limit
 */
export const getSimulationHistory = (limit = 20) => {
  return service.get("/api/simulation/history", { params: { limit } });
};

/**
 * Get generated interaction records from the legacy internal scorer.
 * @param {string} simulationId
 * @param {number} limit - Result count limit
 */
export const getSimulationOpinions = (simulationId, limit = 1000) => {
  return service.get(`/api/simulation/${simulationId}/generated-interactions`, {
    params: { limit },
  });
};

/**
 * Get descriptive within-run patterns over generated activity.
 * @param {string} simulationId
 * @param {boolean} force - Force recalculation on backend
 */
export const getSimulationMetrics = (simulationId, force = false) => {
  return service.get(`/api/simulation/${simulationId}/run-patterns`, {
    params: { force },
  });
};

/**
 * Fork a simulation at a specific turn to create a counterfactual scenario branch
 * @param {string} simulationId
 * @param {number} targetTurn
 */
export const forkSimulation = (simulationId, targetTurn) => {
  return service.post(`/api/simulation/${simulationId}/fork`, {
    target_turn: targetTurn,
  });
};

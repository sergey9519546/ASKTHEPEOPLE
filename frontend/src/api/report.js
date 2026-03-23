import service, { requestWithRetry } from './index'

/**
 * Start report generation
 * @param {Object} data - { simulation_id, force_regenerate? }
 */
export const generateReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/generate', data), 3, 1000)
}

/**
 * Get report generation status
 * @param {Object} params - { report_id?, task_id?, simulation_id? }
 */
export const getReportStatus = (params = {}) => {
  return service.get(`/api/report/generate/status`, { params })
}

/**
 * Get Agent logs (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start line for retrieval
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/agent-log`, { params: { from_line: fromLine } })
}

/**
 * Get console logs (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start line for retrieval
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/console-log`, { params: { from_line: fromLine } })
}

/**
 * Get report details
 * @param {string} reportId
 */
export const getReport = (reportId) => {
  return service.get(`/api/report/${reportId}`)
}

/**
 * Get report evidence
 * @param {string} reportId
 */
export const getReportEvidence = (reportId) => {
  return service.get(`/api/report/${reportId}/evidence`)
}

/**
 * Chat with Report Agent
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const chatWithReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/chat', data), 3, 1000)
}

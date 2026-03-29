/**
 * WebSocket helpers for ASKTHEPEOPLE.
 *
 * Both helpers return the native WebSocket object so callers can call
 * ws.close() when they unmount.
 *
 * URL derivation:
 *   - If VITE_API_BASE_URL is set (e.g. https://myapp.railway.app), convert
 *     the http(s) scheme to ws(s).
 *   - If it is empty (unified same-origin container), use window.location.
 */

function wsBaseUrl() {
  const httpBase = import.meta.env.VITE_API_BASE_URL ?? ''
  if (httpBase) {
    return httpBase.replace(/^http(s?):\/\//, (_, s) => `ws${s}://`)
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

/**
 * Open a WebSocket to /ws/simulation/<simulationId>.
 *
 * The server pushes JSON frames typed as:
 *   { type: 'state', runner_status, current_round, …, recent_actions }
 *   { type: 'error', code, message }
 *   { type: 'done',  runner_status }
 *
 * @param {string} simulationId
 * @param {{ onMessage, onClose, onError }} handlers
 * @returns {WebSocket}
 */
export function connectSimulationWs(simulationId, { onMessage, onClose, onError } = {}) {
  const url = `${wsBaseUrl()}/ws/simulation/${simulationId}`
  const ws = new WebSocket(url)
  ws.onmessage = (e) => {
    try { onMessage?.(JSON.parse(e.data)) } catch (_) { /* ignore parse errors */ }
  }
  ws.onclose  = (e) => onClose?.(e)
  ws.onerror  = (e) => onError?.(e)
  return ws
}

/**
 * Open a WebSocket to /ws/report/<reportId>.
 *
 * The server pushes JSON frames typed as:
 *   { type: 'progress', status, progress, message, sections_done, sections_total }
 *   { type: 'error',    code, message }
 *   { type: 'done',     status }
 *
 * @param {string} reportId
 * @param {{ onMessage, onClose, onError }} handlers
 * @returns {WebSocket}
 */
export function connectReportWs(reportId, { onMessage, onClose, onError } = {}) {
  const url = `${wsBaseUrl()}/ws/report/${reportId}`
  const ws = new WebSocket(url)
  ws.onmessage = (e) => {
    try { onMessage?.(JSON.parse(e.data)) } catch (_) { /* ignore parse errors */ }
  }
  ws.onclose  = (e) => onClose?.(e)
  ws.onerror  = (e) => onError?.(e)
  return ws
}

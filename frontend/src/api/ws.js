/**
 * WebSocket helpers for ASKTHEPEOPLE with built-in resilience.
 *
 * Both helpers return a ResilientWebSocket wrapper object that exposes a
 * `.close()` method identical to the native WebSocket interface, but manages
 * auto-reconnection, exponential backoff, and an inactivity watchdog timer.
 *
 * URL derivation:
 *   - If VITE_API_BASE_URL is set (e.g. https://myapp.railway.app), convert
 *     the http(s) scheme to ws(s).
 *   - If it is empty (unified same-origin container), use window.location.
 */

import { ref } from 'vue'
import service from './index.js'
import { requireAccess } from '../composables/useAccessKey.js'

export const globalWsStatus = ref('OFFLINE')

function wsBaseUrl() {
  const httpBase = import.meta.env.VITE_API_BASE_URL ?? ''
  if (httpBase) {
    return httpBase.replace(/^http(s?):\/\//, (_, s) => `ws${s}://`)
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

function ticketedWsUrl(path, ticket) {
  const url = new URL(path, `${wsBaseUrl()}/`)
  url.searchParams.set('ticket', ticket)
  return url.toString()
}

async function requestWsTicket(scope, resourceId) {
  const response = await service.post('/api/auth/ws-ticket', {
    scope,
    resource_id: resourceId,
  })
  const ticket = response?.ticket ?? response?.data?.ticket
  if (!ticket) throw new Error('The server did not return a live-update ticket.')
  return ticket
}

class ResilientWebSocket {
  constructor(path, ticketRequest, { onMessage, onClose, onError } = {}) {
    this.path = path;
    this.ticketRequest = ticketRequest;
    this.onMessage = onMessage;
    this.onClose = onClose;
    this.onError = onError;
    this.ws = null;
    this.closedByUser = false;
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 15000;
    this.reconnectTimer = null;
    this.watchdogTimer = null;
    this.watchdogTimeoutMs = 12000; // Expected ping/frame from server every 1s-2s; 12s represents missing multiple frames.

    this.connect();
  }

  async connect() {
    if (this.closedByUser) return;

    globalWsStatus.value = this.reconnectAttempts > 0 ? 'RECONNECTING' : 'CONNECTING'
    try {
      const ticket = await this.ticketRequest()
      if (this.closedByUser) return
      this.ws = new WebSocket(ticketedWsUrl(this.path, ticket));
    } catch (err) {
      if (err?.status === 401 || err?.code === 'ACCESS_REQUIRED') {
        requireAccess('A valid access key is required for live updates.')
        globalWsStatus.value = 'OFFLINE'
        this.onError?.(err)
        return
      }
      this.onError?.(err)
      this.handleDisconnect(err);
      return;
    }

    this.ws.onopen = () => {
      globalWsStatus.value = 'ONLINE'
      this.reconnectAttempts = 0;
      this.startWatchdog();
    };

    this.ws.onmessage = (e) => {
      this.feedWatchdog();
      try {
        const parsed = JSON.parse(e.data);
        if (
          parsed?.type === 'error' &&
          ['unauthorized', 'authentication_not_configured', 'origin_not_allowed'].includes(parsed.code)
        ) {
          requireAccess('The live connection was rejected. Check the deployment access key.')
          this.close()
        }
        this.onMessage?.(parsed);
      } catch (_) {
        // Skip parse errors or non-JSON heartbeats
      }
    };

    this.ws.onclose = (e) => {
      this.stopWatchdog();
      if (this.closedByUser) {
        globalWsStatus.value = 'OFFLINE';
        this.onClose?.(e);
      } else {
        if (e.code === 1008 || e.code === 4401) {
          requireAccess('The live connection needs a valid access key.')
          this.closedByUser = true
          globalWsStatus.value = 'OFFLINE'
          this.onClose?.(e)
          return
        }
        globalWsStatus.value = 'RECONNECTING';
        this.handleDisconnect(e);
      }
    };

    this.ws.onerror = (e) => {
      if (import.meta.env.DEV) console.error('[WS] Connection error', e);
      this.onError?.(e);
    };
  }

  handleDisconnect(e) {
    if (this.closedByUser) {
      globalWsStatus.value = 'OFFLINE';
      return;
    }
    globalWsStatus.value = 'RECONNECTING';
    
    // The close/error path already owns the native socket lifecycle.
    this.ws = null;

    // Schedule next reconnect attempt with exponential backoff
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  feedWatchdog() {
    this.stopWatchdog();
    this.startWatchdog();
  }

  startWatchdog() {
    if (this.closedByUser) return;
    this.watchdogTimer = setTimeout(() => {
      if (import.meta.env.DEV) console.warn('[WS] Live updates timed out. Reconnecting.')
      globalWsStatus.value = 'RECONNECTING';
      if (this.ws) {
        try { this.ws.close(); } catch (_) {}
      } else {
        this.handleDisconnect(new Error("Watchdog timeout"));
      }
    }, this.watchdogTimeoutMs);
  }

  stopWatchdog() {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
      this.watchdogTimer = null;
    }
  }

  close() {
    this.closedByUser = true;
    globalWsStatus.value = 'OFFLINE';
    this.stopWatchdog();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

/**
 * Open a resilient WebSocket to /ws/simulation/<simulationId>.
 * @param {string} simulationId
 * @param {{ onMessage, onClose, onError }} handlers
 * @returns {ResilientWebSocket}
 */
export function connectSimulationWs(simulationId, { onMessage, onClose, onError } = {}) {
  return new ResilientWebSocket(
    `/ws/simulation/${encodeURIComponent(simulationId)}`,
    () => requestWsTicket('simulation', simulationId),
    {
      onMessage,
      onClose,
      onError,
    },
  );
}

/**
 * Open a resilient WebSocket to /ws/report/<reportId>.
 * @param {string} reportId
 * @param {{ onMessage, onClose, onError }} handlers
 * @returns {ResilientWebSocket}
 */
export function connectReportWs(reportId, { onMessage, onClose, onError } = {}) {
  return new ResilientWebSocket(
    `/ws/report/${encodeURIComponent(reportId)}`,
    () => requestWsTicket('report', reportId),
    {
      onMessage,
      onClose,
      onError,
    },
  );
}

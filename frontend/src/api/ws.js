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

export const globalWsStatus = ref('OFFLINE')

function wsBaseUrl() {
  const httpBase = import.meta.env.VITE_API_BASE_URL ?? ''
  if (httpBase) {
    return httpBase.replace(/^http(s?):\/\//, (_, s) => `ws${s}://`)
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

class ResilientWebSocket {
  constructor(url, { onMessage, onClose, onError } = {}) {
    this.url = url;
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

  connect() {
    if (this.closedByUser) return;

    globalWsStatus.value = this.reconnectAttempts > 0 ? 'RECONNECTING' : 'CONNECTING'
    console.log(`[WS] Connecting to: ${this.url}`);
    try {
      this.ws = new WebSocket(this.url);
    } catch (err) {
      this.handleDisconnect(err);
      return;
    }

    this.ws.onopen = () => {
      globalWsStatus.value = 'ONLINE'
      console.log(`[WS] Connection established: ${this.url}`);
      this.reconnectAttempts = 0;
      this.startWatchdog();
    };

    this.ws.onmessage = (e) => {
      this.feedWatchdog();
      try {
        const parsed = JSON.parse(e.data);
        this.onMessage?.(parsed);
      } catch (_) {
        // Skip parse errors or non-JSON heartbeats
      }
    };

    this.ws.onclose = (e) => {
      this.stopWatchdog();
      if (this.closedByUser) {
        globalWsStatus.value = 'OFFLINE';
        console.log(`[WS] Connection closed cleanly by client request.`);
        this.onClose?.(e);
      } else {
        globalWsStatus.value = 'RECONNECTING';
        console.warn(`[WS] Connection closed unexpectedly. Scheduling reconnect.`);
        this.handleDisconnect(e);
      }
    };

    this.ws.onerror = (e) => {
      console.error(`[WS] Error:`, e);
      this.onError?.(e);
    };
  }

  handleDisconnect(e) {
    if (this.closedByUser) {
      globalWsStatus.value = 'OFFLINE';
      return;
    }
    globalWsStatus.value = 'RECONNECTING';
    
    // Clean up current reference
    if (this.ws) {
      try { this.ws.close(); } catch (_) {}
      this.ws = null;
    }

    // Schedule next reconnect attempt with exponential backoff
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;
    console.log(`[WS] Attempting reconnect in ${Math.round(delay)}ms (Attempt #${this.reconnectAttempts})`);
    
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
      console.warn(`[WS] Inactivity threshold exceeded on ${this.url}. Reconnecting...`);
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
  const url = `${wsBaseUrl()}/ws/simulation/${simulationId}`;
  return new ResilientWebSocket(url, { onMessage, onClose, onError });
}

/**
 * Open a resilient WebSocket to /ws/report/<reportId>.
 * @param {string} reportId
 * @param {{ onMessage, onClose, onError }} handlers
 * @returns {ResilientWebSocket}
 */
export function connectReportWs(reportId, { onMessage, onClose, onError } = {}) {
  const url = `${wsBaseUrl()}/ws/report/${reportId}`;
  return new ResilientWebSocket(url, { onMessage, onClose, onError });
}

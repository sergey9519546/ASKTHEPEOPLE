import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/index.js', () => ({
  default: {
    post: vi.fn(),
  },
}));

vi.mock('../composables/useAccessKey.js', () => ({
  requireAccess: vi.fn(),
}));

import service from '../api/index.js';
import {
  connectReportWs,
  connectSimulationWs,
} from '../api/ws.js';

class MockWebSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.closed = false;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
  }
}

describe('short-lived WebSocket tickets', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    service.post.mockReset();
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('requests an exact simulation ticket and never puts the access key in the URL', async () => {
    service.post.mockResolvedValueOnce({
      success: true,
      ticket: 'short-lived-simulation-ticket',
      expires_in: 60,
    });

    const connection = connectSimulationWs('sim-1');
    await flushPromises();

    expect(service.post).toHaveBeenCalledWith('/api/auth/ws-ticket', {
      scope: 'simulation',
      resource_id: 'sim-1',
    });
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain(
      '/ws/simulation/sim-1?ticket=short-lived-simulation-ticket',
    );
    expect(MockWebSocket.instances[0].url).not.toContain('token=');

    connection.close();
  });

  it('gets a fresh ticket before every reconnect', async () => {
    service.post
      .mockResolvedValueOnce({ success: true, ticket: 'ticket-one' })
      .mockResolvedValueOnce({ success: true, ticket: 'ticket-two' });

    const connection = connectReportWs('report-7');
    await flushPromises();
    const firstSocket = MockWebSocket.instances[0];
    firstSocket.onopen?.();
    firstSocket.onclose?.({ code: 1006 });

    await vi.advanceTimersByTimeAsync(1000);
    await flushPromises();

    expect(service.post).toHaveBeenCalledTimes(2);
    expect(service.post).toHaveBeenNthCalledWith(2, '/api/auth/ws-ticket', {
      scope: 'report',
      resource_id: 'report-7',
    });
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1].url).toContain('ticket=ticket-two');
    expect(MockWebSocket.instances[1].url).not.toContain('ticket-one');

    connection.close();
  });
});

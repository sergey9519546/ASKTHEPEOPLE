import { enableAutoUnmount, flushPromises, shallowMount } from '@vue/test-utils';
import { defineComponent, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  getRunStatus: vi.fn(),
  getSimulationActions: vi.fn(),
  getSimulationPreflight: vi.fn(),
  getSimulationDiagnostics: vi.fn(),
  getSimulationMetrics: vi.fn(),
  startSimulation: vi.fn(),
}));
const transport = vi.hoisted(() => ({ connect: vi.fn(), sockets: [] }));
const report = vi.hoisted(() => ({ generate: vi.fn(), push: vi.fn() }));
vi.mock('../api/simulation', () => api);
vi.mock('../api/ws', () => ({ connectSimulationWs: transport.connect }));
vi.mock('../api/report', () => ({ generateReport: report.generate }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push: report.push }) }));

import Step3Simulation from '../components/Step3Simulation.vue';
import { RUN_ACTIVITY_LIMIT } from '../composables/useRunActivity';

// Assert the parent/reader contract independently of the presentation owner's work.
const Reader = defineComponent({
  name: 'Step3RunWayfinder',
  props: [
    'actions', 'activityHeld', 'pendingCount', 'pendingOverflow', 'activityEvicted',
    'activityLimit', 'selectedRecord', 'historyError', 'runStatus', 'phase',
    'isStarting', 'startError', 'liveUpdateError', 'metrics', 'metricsLoading',
    'metricsError', 'diagnostics', 'diagnosticsError', 'preflight', 'reportError',
    'isReviewing', 'canReview',
  ],
  emits: ['hold-view', 'show-latest', 'inspect-record', 'close-inspector',
    'reconnect', 'retry-run', 'load-metrics', 'review'],
  template: '<div />',
});

const ok = (data) => ({ success: true, data });
const running = (extra = {}) => ok({ runner_status: 'running', current_round: 1, ...extra });
const action = (id, round = 1) => ({
  id, round_num: round, platform: 'twitter', agent_id: 1,
  action_type: 'CREATE_POST', action_args: { content: `Generated entry ${id}` },
});
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const mountRun = () => shallowMount(Step3Simulation, {
  props: { simulationId: 'run-a', maxRounds: 12 },
  global: { stubs: { Step3RunWayfinder: Reader } },
});
const reader = (wrapper) => wrapper.findComponent(Reader);
const ids = (wrapper) => reader(wrapper).props('actions').map((record) => record.id);
const event = async (wrapper, name, payload) => {
  reader(wrapper).vm.$emit(name, payload);
  await nextTick();
};
const frame = (status = 'running', actions = [], round = 2) => ({
  type: 'state', runner_status: status, recent_actions: actions,
  current_round: round, twitter_current_round: round, total_rounds: 12,
});

enableAutoUnmount(afterEach);
beforeEach(() => {
  vi.resetAllMocks();
  transport.sockets.length = 0;
  transport.connect.mockImplementation((id, callbacks) => {
    const close = vi.fn(() => callbacks.onClose());
    transport.sockets.push({ id, callbacks, close });
    return { close };
  });
  api.getRunStatus.mockResolvedValue(running());
  api.getSimulationActions.mockResolvedValue(ok({ actions: [action('first')] }));
  api.getSimulationPreflight.mockResolvedValue(ok({ status: 'ready' }));
  api.getSimulationDiagnostics.mockResolvedValue(ok({ canonical_agents: [] }));
  api.getSimulationMetrics.mockResolvedValue(ok({ polarization_index: 0.2 }));
  api.startSimulation.mockResolvedValue(running());
});

describe('Step3 recent activity ownership', () => {
  it('keeps collecting and updating run status while the display and inspection are held', async () => {
    const wrapper = mountRun();
    await flushPromises();
    expect(api.getSimulationActions).toHaveBeenCalledWith('run-a', { limit: 200, offset: 0 });
    expect(reader(wrapper).props('activityLimit')).toBe(RUN_ACTIVITY_LIMIT);
    const first = reader(wrapper).props('actions')[0];
    await event(wrapper, 'inspect-record', first._uniqueId);
    await event(wrapper, 'hold-view');
    await transport.sockets[0].callbacks.onMessage(frame('running', [action('second', 2)], 2));
    await nextTick();
    expect(ids(wrapper)).toEqual(['first']);
    expect(reader(wrapper).props('runStatus').current_round).toBe(2);
    expect(reader(wrapper).props('activityHeld')).toBe(true);
    expect(reader(wrapper).props('pendingCount')).toBe(1);
    expect(reader(wrapper).props('selectedRecord')).toEqual(first);
    expect(api.startSimulation).not.toHaveBeenCalled();
    expect(transport.sockets[0].close).not.toHaveBeenCalled();
    await event(wrapper, 'show-latest');
    expect(ids(wrapper)).toEqual(['first', 'second']);
    expect(reader(wrapper).props('pendingCount')).toBe(0);
    await event(wrapper, 'close-inspector');
    expect(reader(wrapper).props('selectedRecord')).toBeNull();
  });

  it('passes bounded admissions, overflow and eviction through without inventing a total', async () => {
    const wrapper = mountRun();
    await flushPromises();
    await event(wrapper, 'hold-view');
    await transport.sockets[0].callbacks.onMessage(frame('running',
      Array.from({ length: RUN_ACTIVITY_LIMIT + 1 }, (_, i) => action(`new-${i}`, i + 2))));
    await nextTick();
    expect(ids(wrapper)).toEqual(['first']);
    expect(reader(wrapper).props()).toMatchObject({
      pendingCount: RUN_ACTIVITY_LIMIT, pendingOverflow: true, activityEvicted: true,
    });
    await event(wrapper, 'show-latest');
    expect(ids(wrapper)).toHaveLength(RUN_ACTIVITY_LIMIT);
    expect(ids(wrapper)).not.toContain('first');
  });

  it('preserves the held reader and selected record on reconnect but rejects old socket callbacks', async () => {
    const wrapper = mountRun();
    await flushPromises();
    const oldReader = reader(wrapper).vm;
    const first = reader(wrapper).props('actions')[0];
    await event(wrapper, 'hold-view');
    await event(wrapper, 'inspect-record', first._uniqueId);
    const old = transport.sockets[0];
    api.getSimulationActions.mockResolvedValue(ok({ actions: [action('second', 2)] }));
    await event(wrapper, 'reconnect');
    await flushPromises();
    expect(reader(wrapper).vm).toBe(oldReader);
    expect(reader(wrapper).props()).toMatchObject({ activityHeld: true, pendingCount: 1, selectedRecord: first });
    const before = wrapper.emitted('update-status').length;
    await old.callbacks.onMessage(frame('completed', [action('stale', 50)]));
    old.callbacks.onError(new Error('old connection'));
    old.callbacks.onClose();
    await nextTick();
    expect(reader(wrapper).props('runStatus').runner_status).toBe('running');
    expect(reader(wrapper).props('liveUpdateError')).toBeNull();
    expect(wrapper.emitted('update-status')).toHaveLength(before);
    expect(api.startSimulation).not.toHaveBeenCalled();
    await event(wrapper, 'show-latest');
    expect(ids(wrapper)).toEqual(['first', 'second']);
  });

  it.each(['completed', 'stopped', 'failed', 'interrupted'])('ingests %s frame activity before terminal handling and keeps the held view', async (status) => {
    const wrapper = mountRun();
    await flushPromises();
    await event(wrapper, 'hold-view');
    api.getSimulationActions.mockResolvedValue(ok({ actions: [action('saved-final', 3)] }));
    await transport.sockets[0].callbacks.onMessage(frame(status, [action('frame-final', 2)]));
    await nextTick();
    expect(reader(wrapper).props()).toMatchObject({ phase: 2, activityHeld: true, pendingCount: 2 });
    expect(reader(wrapper).props('runStatus').runner_status).toBe(status);
    expect(ids(wrapper)).toEqual(['first']);
    expect(transport.sockets[0].close).toHaveBeenCalledOnce();
    await event(wrapper, 'show-latest');
    expect(ids(wrapper)).toEqual(['first', 'frame-final', 'saved-final']);
  });

  it.each(['failed', 'interrupted'])('preserves recent actions from a saved %s status when history fails', async (status) => {
    api.getRunStatus.mockResolvedValue(ok({ runner_status: status, recent_actions: [action('terminal')] }));
    api.getSimulationActions.mockRejectedValue(new Error('private provider payload'));
    const wrapper = mountRun();
    await flushPromises();
    expect(ids(wrapper)).toEqual(['terminal']);
    expect(reader(wrapper).props('historyError')).toBe('Recent activity history is unavailable. Displayed records may be incomplete.');
    expect(reader(wrapper).props('historyError')).not.toContain('private provider');
    expect(api.startSimulation).not.toHaveBeenCalled();
  });

  it('continues socket ingestion during a slow history read and reports explicit read failures safely', async () => {
    const history = deferred();
    api.getSimulationActions.mockReturnValue(history.promise);
    const wrapper = mountRun();
    await flushPromises();
    expect(transport.sockets).toHaveLength(1);
    await transport.sockets[0].callbacks.onMessage(frame('running', [action('live')]));
    history.resolve({ success: false, error: 'private provider payload' });
    await flushPromises();
    expect(ids(wrapper)).toEqual(['live']);
    expect(reader(wrapper).props('historyError')).toBe('Recent activity history is unavailable. Displayed records may be incomplete.');
    api.getSimulationActions.mockResolvedValue(ok({ actions: [] }));
    await event(wrapper, 'reconnect');
    await flushPromises();
    expect(reader(wrapper).props('historyError')).toBeNull();
    expect(ids(wrapper)).toEqual(['live']);
  });
});

describe('Step3 session isolation', () => {
  it('clears activity, held state and inspection on a run switch and ignores old callbacks', async () => {
    const wrapper = mountRun();
    await flushPromises();
    const oldReader = reader(wrapper).vm;
    const oldSocket = transport.sockets[0];
    await event(wrapper, 'hold-view');
    await event(wrapper, 'inspect-record', reader(wrapper).props('actions')[0]._uniqueId);
    api.getSimulationActions.mockResolvedValue(ok({ actions: [action('run-b-entry')] }));
    await wrapper.setProps({ simulationId: 'run-b' });
    await flushPromises();
    await oldSocket.callbacks.onMessage(frame('failed', [action('old')]));
    oldSocket.callbacks.onClose();
    oldSocket.callbacks.onError(new Error('stale'));
    await nextTick();
    expect(reader(wrapper).vm === oldReader).toBe(false);
    expect(ids(wrapper)).toEqual(['run-b-entry']);
    expect(reader(wrapper).props()).toMatchObject({
      activityHeld: false, selectedRecord: null, pendingCount: 0,
      liveUpdateError: null, phase: 1,
    });
  });

  it('rejects stale idle status even after switching A -> B -> A', async () => {
    const status = deferred();
    api.getRunStatus.mockReturnValueOnce(status.promise);
    const wrapper = mountRun();
    await wrapper.setProps({ simulationId: 'run-b' });
    await flushPromises();
    await wrapper.setProps({ simulationId: 'run-a' });
    await flushPromises();
    status.resolve(ok({ runner_status: 'idle' }));
    await flushPromises();
    expect(api.startSimulation).not.toHaveBeenCalled();
    expect(reader(wrapper).props('runStatus').runner_status).toBe('running');
  });

  it('invalidates status and contract replies on a same-ID retry', async () => {
    const status = deferred();
    const diagnostics = deferred();
    const preflight = deferred();
    api.getRunStatus.mockReturnValueOnce(status.promise);
    api.getSimulationDiagnostics.mockReturnValueOnce(diagnostics.promise);
    api.getSimulationPreflight.mockReturnValueOnce(preflight.promise);
    const wrapper = mountRun();
    await event(wrapper, 'retry-run');
    await flushPromises();
    status.resolve(ok({ runner_status: 'idle' }));
    diagnostics.resolve(ok({ stale: true }));
    preflight.reject(new Error('old preflight'));
    await flushPromises();
    expect(api.startSimulation).not.toHaveBeenCalled();
    expect(reader(wrapper).props('diagnostics')).toEqual({ canonical_agents: [] });
    expect(reader(wrapper).props('preflight')).toEqual({ status: 'ready' });
    expect(reader(wrapper).props('startError')).toBeNull();
  });

  it.each(['resolve', 'reject'])('ignores a delayed start %s after switching runs', async (settle) => {
    const start = deferred();
    api.getRunStatus.mockResolvedValueOnce(ok({ runner_status: 'idle' }));
    api.startSimulation.mockReturnValueOnce(start.promise);
    const wrapper = mountRun();
    await flushPromises();
    expect(reader(wrapper).props('isStarting')).toBe(true);
    await wrapper.setProps({ simulationId: 'run-b' });
    await flushPromises();
    start[settle](settle === 'resolve' ? running({ stale: true }) : new Error('old start failed'));
    await flushPromises();
    expect(transport.sockets.map((socket) => socket.id)).toEqual(['run-b']);
    expect(reader(wrapper).props()).toMatchObject({ isStarting: false, startError: null });
    expect(reader(wrapper).props('runStatus')).not.toHaveProperty('stale');
  });

  it('rejects terminal history and metrics after a same-ID retry, including stale finally cleanup', async () => {
    const history = deferred();
    const metrics = deferred();
    const currentMetrics = deferred();
    const wrapper = mountRun();
    await flushPromises();
    api.getSimulationActions.mockReturnValueOnce(history.promise);
    api.getSimulationMetrics.mockReturnValueOnce(metrics.promise).mockReturnValueOnce(currentMetrics.promise);
    const finishing = transport.sockets[0].callbacks.onMessage(frame('completed', [action('end')]));
    await nextTick();
    await event(wrapper, 'retry-run');
    await flushPromises();
    await event(wrapper, 'load-metrics');
    metrics.resolve(ok({ stale: true }));
    history.resolve(ok({ actions: [action('stale-history', 100)] }));
    await finishing;
    await flushPromises();
    expect(reader(wrapper).props('phase')).toBe(1);
    expect(ids(wrapper)).toEqual(['first']);
    expect(reader(wrapper).props('metrics')).toBeNull();
    expect(reader(wrapper).props('metricsLoading')).toBe(true);
    currentMetrics.resolve(ok({ current: true }));
    await flushPromises();
    expect(reader(wrapper).props('metrics')).toEqual({ current: true });
    expect(reader(wrapper).props('metricsLoading')).toBe(false);
  });

  it('ignores stale history failures after a new run has loaded successfully', async () => {
    const history = deferred();
    api.getSimulationActions.mockReturnValueOnce(history.promise);
    const wrapper = mountRun();
    await flushPromises();
    await wrapper.setProps({ simulationId: 'run-b' });
    await flushPromises();
    history.reject(new Error('old failure'));
    await flushPromises();
    expect(reader(wrapper).props('historyError')).toBeNull();
    expect(ids(wrapper)).toEqual(['first']);
  });

  it('does not route to a report from a previous session', async () => {
    const pending = deferred();
    report.generate.mockReturnValueOnce(pending.promise);
    const wrapper = mountRun();
    await flushPromises();
    await event(wrapper, 'review');
    await wrapper.setProps({ simulationId: 'run-b' });
    await flushPromises();
    pending.resolve(ok({ report_id: 'stale-report' }));
    await flushPromises();
    expect(report.push).not.toHaveBeenCalled();
    expect(reader(wrapper).props('isReviewing')).toBe(false);
  });

  it('ignores captured sockets and pending terminal replies after unmount', async () => {
    const metrics = deferred();
    const history = deferred();
    const wrapper = mountRun();
    await flushPromises();
    api.getSimulationMetrics.mockReturnValueOnce(metrics.promise);
    api.getSimulationActions.mockReturnValueOnce(history.promise);
    const socket = transport.sockets[0];
    const finishing = socket.callbacks.onMessage(frame('completed'));
    wrapper.unmount();
    const before = JSON.stringify(wrapper.emitted());
    await socket.callbacks.onMessage(frame('failed', [action('unmounted')]));
    socket.callbacks.onError(new Error('unmounted'));
    socket.callbacks.onClose();
    history.reject(new Error('unmounted history'));
    metrics.reject(new Error('unmounted metrics'));
    await finishing;
    await flushPromises();
    expect(JSON.stringify(wrapper.emitted())).toBe(before);
    expect(transport.sockets).toHaveLength(1);
  });

  it('does not start or connect when pending hydration resolves after unmount', async () => {
    const status = deferred();
    api.getRunStatus.mockReturnValueOnce(status.promise);
    const wrapper = mountRun();
    wrapper.unmount();
    status.resolve(ok({ runner_status: 'idle' }));
    await flushPromises();
    expect(api.startSimulation).not.toHaveBeenCalled();
    expect(transport.sockets).toHaveLength(0);
  });
});

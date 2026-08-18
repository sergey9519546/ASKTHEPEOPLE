import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiMocks = vi.hoisted(() => ({
  startSimulation: vi.fn(),
  getSimulationPreflight: vi.fn(),
  getSimulationDiagnostics: vi.fn(),
  getSimulationActions: vi.fn(),
  getSimulationMetrics: vi.fn(),
  getRunStatus: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('../api/report', () => ({
  generateReport: vi.fn(),
}));

vi.mock('../api/simulation', () => apiMocks);

vi.mock('../api/ws', () => ({
  connectSimulationWs: vi.fn(),
}));

import Step3Simulation from '../components/Step3Simulation.vue';

describe('Step3Simulation provenance separation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getSimulationPreflight.mockResolvedValue({ success: true, data: {} });
    apiMocks.getSimulationDiagnostics.mockResolvedValue({ success: true, data: {} });
    apiMocks.getRunStatus.mockResolvedValue({
      success: true,
      data: { runner_status: 'idle' },
    });
    apiMocks.startSimulation.mockResolvedValue({
      success: false,
      error: 'test stop',
    });
  });

  it('starts with source-graph mutation explicitly disabled', async () => {
    shallowMount(Step3Simulation, {
      props: {
        simulationId: 'sim-1',
        systemLogs: [],
      },
    });
    await flushPromises();

    expect(apiMocks.startSimulation).toHaveBeenCalledWith(
      expect.objectContaining({
        simulation_id: 'sim-1',
        force: false,
        enable_graph_memory_update: false,
      }),
    );
    expect(apiMocks.startSimulation.mock.calls[0][0]).not.toHaveProperty(
      'generated_graph_id',
    );
  });

  it('reconnects to a saved running state without starting over', async () => {
    apiMocks.getRunStatus.mockResolvedValue({
      success: true,
      data: {
        simulation_id: 'sim-1',
        runner_status: 'running',
        current_round: 4,
        total_rounds: 12,
      },
    });
    apiMocks.getSimulationActions.mockResolvedValue({
      success: true,
      data: { actions: [] },
    });

    shallowMount(Step3Simulation, {
      props: {
        simulationId: 'sim-1',
        systemLogs: [],
      },
    });
    await flushPromises();

    expect(apiMocks.getRunStatus).toHaveBeenCalledWith('sim-1');
    expect(apiMocks.startSimulation).not.toHaveBeenCalled();
    expect(apiMocks.getSimulationActions).toHaveBeenCalledWith('sim-1');
  });

  it('does not start a run when saved status cannot be verified', async () => {
    apiMocks.getRunStatus.mockRejectedValue(new Error('status unavailable'));

    shallowMount(Step3Simulation, {
      props: {
        simulationId: 'sim-1',
        systemLogs: [],
      },
    });
    await flushPromises();

    expect(apiMocks.startSimulation).not.toHaveBeenCalled();
  });

  it('does not treat an explicit status-read failure as an idle run', async () => {
    apiMocks.getRunStatus.mockResolvedValue({
      success: false,
      error: 'saved state unavailable',
    });

    shallowMount(Step3Simulation, {
      props: {
        simulationId: 'sim-1',
        systemLogs: [],
      },
    });
    await flushPromises();

    expect(apiMocks.startSimulation).not.toHaveBeenCalled();
  });
});

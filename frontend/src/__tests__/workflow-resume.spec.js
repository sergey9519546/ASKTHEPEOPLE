import { describe, expect, it } from 'vitest';
import {
  deriveWorkflowStep,
  savedRunDestination,
  savedRunStatus,
} from '../utils/workflow.js';

describe('saved run workflow contract', () => {
  it('opens a completed run with a report in the report workflow', () => {
    const run = {
      project_id: 'project-1',
      simulation_id: 'sim-1',
      runner_status: 'completed',
      report_id: 'report-1',
    };

    expect(savedRunStatus(run)).toBe('completed');
    expect(deriveWorkflowStep(run)).toBe(4);
    expect(savedRunDestination(run)).toEqual({
      name: 'Report',
      params: { reportId: 'report-1' },
    });
  });

  it('reconnects a running run to the run workflow with its saved length', () => {
    const run = {
      project_id: 'project-2',
      simulation_id: 'sim-2',
      status: 'running',
      runner_status: 'running',
      total_rounds: 17,
    };

    expect(deriveWorkflowStep(run)).toBe(3);
    expect(savedRunDestination(run)).toEqual({
      name: 'SimulationRun',
      params: { simulationId: 'sim-2' },
      query: { maxRounds: '17' },
    });
  });

  it('uses the backend-declared workflow step when present', () => {
    expect(deriveWorkflowStep({ workflow_step: 2, runner_status: 'idle' })).toBe(
      2,
    );
  });

  it('returns a created saved simulation to setup rather than step one', () => {
    const run = {
      project_id: 'project-3',
      simulation_id: 'sim-3',
      status: 'created',
      runner_status: 'idle',
    };

    expect(deriveWorkflowStep(run)).toBe(2);
    expect(savedRunDestination(run)).toEqual({
      name: 'Simulation',
      params: { simulationId: 'sim-3' },
    });
  });
});

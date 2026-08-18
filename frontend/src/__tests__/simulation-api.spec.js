import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import service from '../api/index.js';
import {
  askGeneratedProfiles,
  exportGeneratedResponsesCSV,
  getSimulationMetrics,
  getSimulationOpinions,
} from '../api/simulation.js';

describe('simulation API helpers', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not expose a live scenario injection action', () => {
    const apiSource = readFileSync(resolve('src/api/simulation.js'), 'utf8');
    const runSource = readFileSync(
      resolve('src/components/Step3Simulation.vue'),
      'utf8',
    );
    const wayfinderSource = readFileSync(
      resolve('src/components/Step3RunWayfinder.vue'),
      'utf8',
    );
    const runExperienceSource = `${runSource}${wayfinderSource}`;

    expect(apiSource).not.toContain('injectSimulationEvent');
    expect(runExperienceSource).not.toContain('ADD A SCENARIO EVENT');
    expect(runExperienceSource).toContain('An active run cannot be');
    expect(runExperienceSource).toContain('changed after it begins.');
  });

  it('exports generated profile responses through the truthful route', async () => {
    const response = new Blob(['profile,response']);
    const post = vi.spyOn(service, 'post').mockResolvedValue(response);
    const results = [{ agent_name: 'Profile 1', answer: 'A possible response' }];

    await expect(
      exportGeneratedResponsesCSV('sim-1', results),
    ).resolves.toBe(response);

    expect(post).toHaveBeenCalledWith(
      '/api/simulation/sim-1/export/generated-responses',
      { results },
      { responseType: 'blob' },
    );
  });

  it('uses truthful primary routes for generated answers and run records', async () => {
    const post = vi.spyOn(service, 'post').mockResolvedValue({ success: true });
    const get = vi.spyOn(service, 'get').mockResolvedValue({ success: true });
    const request = {
      simulation_id: 'sim-1',
      questions: [{ agent_id: 1, prompt: 'What assumption should be tested?' }],
    };

    await askGeneratedProfiles(request);
    await getSimulationOpinions('sim-1', 25);
    await getSimulationMetrics('sim-1', true);

    expect(post).toHaveBeenCalledWith(
      '/api/simulation/generated-response/batch',
      request,
    );
    expect(get).toHaveBeenCalledWith(
      '/api/simulation/sim-1/generated-interactions',
      { params: { limit: 25 } },
    );
    expect(get).toHaveBeenCalledWith(
      '/api/simulation/sim-1/run-patterns',
      { params: { force: true } },
    );
  });
});

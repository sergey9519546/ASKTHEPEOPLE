import { afterEach, describe, expect, it, vi } from 'vitest';
import service from '../api/index.js';
import { forkSimulation } from '../api/simulation.js';

describe('counterfactual fork client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('posts to the fork route with the branch turn', async () => {
    // This client function has existed with no caller since it was written.
    // Pinning the path and payload here checks the backend contract even while
    // no view uses it, so wiring up the UI later starts from a known-good call
    // rather than a guess.
    const post = vi.spyOn(service, 'post').mockResolvedValue({ success: true, data: {} });

    await forkSimulation('sim_abc', 4);

    expect(post).toHaveBeenCalledWith('/api/simulation/sim_abc/fork', {
      target_turn: 4,
    });
  });

  it('passes turn 0 through rather than dropping it', async () => {
    // Branching at the very start is meaningful; a falsy guard here would send
    // undefined and the backend would answer 400 "target_turn is required".
    const post = vi.spyOn(service, 'post').mockResolvedValue({ success: true, data: {} });

    await forkSimulation('sim_abc', 0);

    expect(post).toHaveBeenCalledWith('/api/simulation/sim_abc/fork', {
      target_turn: 0,
    });
  });
});

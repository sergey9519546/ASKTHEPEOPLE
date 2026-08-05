import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import service from '../api/index.js';
import { forkSimulation } from '../api/simulation.js';

describe('counterfactual fork client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('posts to the fork route with the branch turn', async () => {
    // This client function had no caller for a long time, so nothing checked
    // that its path and payload match the backend route it targets.
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

describe('branch lineage in the recent-runs list', () => {
  const home = readFileSync(resolve('src/views/Home.vue'), 'utf8');

  it('renders the marker on the live home surface, not a dead component', () => {
    // HistoryDatabase.vue also lists runs but was deliberately dropped from
    // Home.vue in the Direction C redesign and is not in the built bundle.
    // The recent-runs list in Home.vue is the surface users actually see.
    expect(home).toContain('run.forked_from');
    expect(home).toContain('run-branch');
  });

  it('names the parent and branch point, not just the fact of branching', () => {
    expect(home).toContain('branchLabel');
    expect(home).toMatch(/Branched from \$\{parent\}/);
    expect(home).toMatch(/at turn \$\{turn\}/);
  });

  it('treats turn 0 as a real branch point', () => {
    // A truthiness check would render "Branched from X" with no turn for a
    // branch taken at the start of a run.
    expect(home).toMatch(/turn === null \|\| turn === undefined/);
  });

  it('leaves original runs unmarked', () => {
    expect(home).toMatch(/v-if="run\.forked_from"/);
  });

  it('keeps branch copy inside the truth contract', () => {
    // A branch is another synthetic exploration. Outcome language would claim
    // it forecasts what actually happens.
    const label = home.slice(home.indexOf('const branchLabel'), home.indexOf('const formatStatus'));
    for (const banned of ['predict', 'outcome', 'will happen', 'digital twin']) {
      expect(label.toLowerCase()).not.toContain(banned);
    }
  });
});

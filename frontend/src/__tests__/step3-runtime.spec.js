import { shallowMount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

import Step3Simulation from '../components/Step3Simulation.vue';
import Step3RunWayfinder from '../components/Step3RunWayfinder.vue';

describe('Step3Simulation runtime wiring', () => {
  it('mounts without a missing Vue watch binding', () => {
    let wrapper;
    expect(() => {
      wrapper = shallowMount(Step3Simulation, {
        props: {
          systemLogs: [],
        },
      });
    }).not.toThrow();

    expect(wrapper.findComponent(Step3RunWayfinder).exists()).toBe(true);
  });
});

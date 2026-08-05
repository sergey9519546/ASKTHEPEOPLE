import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ForkRunControl from "../components/ForkRunControl.vue";
import service from "../api/index.js";

const stubs = { global: { mocks: { $router: { push: vi.fn() } } } };

const mountControl = (props = {}) =>
  mount(ForkRunControl, {
    props: { simulationId: "sim_abc", maxTurn: 8, ...props },
    global: {
      plugins: [],
      mocks: {},
      stubs: {},
      provide: {},
      config: {},
      renderStubDefaultSlot: true,
      ...stubs.global,
    },
  });

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("ForkRunControl", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts the chosen turn to the fork route", async () => {
    const post = vi.spyOn(service, "post").mockResolvedValue({
      success: true,
      data: { new_simulation_id: "new-id", forked_from: "sim_abc", forked_at_turn: 3 },
    });

    const wrapper = mountControl();
    await wrapper.find("#fork-turn").setValue(3);
    await wrapper.find("button").trigger("click");

    expect(post).toHaveBeenCalledWith("/api/simulation/sim_abc/fork", {
      target_turn: 3,
    });
  });

  it("allows turn 0 as a real branch point", async () => {
    // Branching at the start re-explores the whole run. A truthiness guard on
    // the turn would disable the button here.
    const post = vi.spyOn(service, "post").mockResolvedValue({
      success: true,
      data: { new_simulation_id: "new-id", forked_at_turn: 0 },
    });

    const wrapper = mountControl();
    await wrapper.find("#fork-turn").setValue(0);
    const button = wrapper.find("button");
    expect(button.attributes("disabled")).toBeUndefined();

    await button.trigger("click");
    expect(post).toHaveBeenCalledWith("/api/simulation/sim_abc/fork", {
      target_turn: 0,
    });
  });

  it("refuses a turn beyond the run's length", async () => {
    const post = vi.spyOn(service, "post");
    const wrapper = mountControl({ maxTurn: 5 });

    await wrapper.find("#fork-turn").setValue(9);

    expect(wrapper.find("button").attributes("disabled")).toBeDefined();
    expect(post).not.toHaveBeenCalled();
  });

  it("refuses a negative turn", async () => {
    const wrapper = mountControl();
    await wrapper.find("#fork-turn").setValue(-1);
    expect(wrapper.find("button").attributes("disabled")).toBeDefined();
  });

  it("surfaces a backend refusal instead of failing silently", async () => {
    vi.spyOn(service, "post").mockResolvedValue({
      success: false,
      error: "Simulation sim_abc not found.",
    });

    const wrapper = mountControl();
    await wrapper.find("button").trigger("click");
    await new Promise((r) => setTimeout(r, 0));

    const alert = wrapper.find('[role="alert"]');
    expect(alert.exists()).toBe(true);
    expect(alert.text()).toContain("not found");
  });

  it("surfaces a transport failure", async () => {
    vi.spyOn(service, "post").mockRejectedValue(new Error("Network down"));

    const wrapper = mountControl();
    await wrapper.find("button").trigger("click");
    await new Promise((r) => setTimeout(r, 0));

    expect(wrapper.find('[role="alert"]').text()).toContain("Network down");
  });

  it("emits the new branch so the host view can react", async () => {
    vi.spyOn(service, "post").mockResolvedValue({
      success: true,
      data: { new_simulation_id: "new-id", forked_at_turn: 2 },
    });

    const wrapper = mountControl();
    await wrapper.find("button").trigger("click");
    await new Promise((r) => setTimeout(r, 0));

    expect(wrapper.emitted("branched")).toBeTruthy();
    expect(wrapper.emitted("branched")[0][0].new_simulation_id).toBe("new-id");
  });
});

describe("fork control wiring and copy", () => {
  const view = readFileSync(resolve("src/views/SimulationRunView.vue"), "utf8");
  const control = readFileSync(resolve("src/components/ForkRunControl.vue"), "utf8");

  it("is mounted in the run view", () => {
    expect(view).toContain("ForkRunControl");
    expect(view).toContain('from "../components/ForkRunControl.vue"');
  });

  it("is only offered once the run has stopped", () => {
    // Branching mid-run would copy a directory the runner is still writing to.
    expect(view).toContain("canBranch");
    expect(view).toMatch(/currentStatus\.value === "completed"/);
  });

  it("keeps branch copy inside the truth contract", () => {
    for (const banned of ["predict", "will happen", "actual outcome", "digital twin"]) {
      expect(control.toLowerCase()).not.toContain(banned);
    }
  });

  it("states that branching leaves the original run untouched", () => {
    expect(control).toContain("changes nothing about the run it came from");
  });
});

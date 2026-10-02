// @vitest-environment jsdom

/**
 * Accessibility residue left open by the shell redesign.
 *
 * Every test here fails against the code as it stood when this file was
 * written, and each one mounts a real component rather than reading its source.
 * A source-string assertion can be satisfied by text that never reaches a
 * rendered attribute; these cannot.
 */

import { flushPromises, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  route: {
    name: "Interaction",
    params: { reportId: "r-1" },
    query: {},
    fullPath: "/interaction/r-1",
  },
  getReport: vi.fn(() => new Promise(() => {})),
  getSimulation: vi.fn(() => new Promise(() => {})),
  getGraphData: vi.fn(() => new Promise(() => {})),
  getProject: vi.fn(() => new Promise(() => {})),
}));

// Mocked the way shell-ux-contract.spec.js does it. The api modules are mocked
// partially, because several views import named exports from the same modules
// and a bare replacement would leave those imports dangling at load time.
vi.mock("vue-router", () => ({
  useRouter: () => ({ push: mocks.routerPush, replace: mocks.routerPush }),
  useRoute: () => mocks.route,
}));

vi.mock("../api/report", async (importOriginal) => ({
  ...(await importOriginal()),
  getReport: mocks.getReport,
}));
vi.mock("../api/simulation", async (importOriginal) => ({
  ...(await importOriginal()),
  getSimulation: mocks.getSimulation,
}));
vi.mock("../api/graph", async (importOriginal) => ({
  ...(await importOriginal()),
  getGraphData: mocks.getGraphData,
  getProject: mocks.getProject,
}));

import DesktopWindow from "../components/DesktopWindow.vue";
import InteractionView from "../views/InteractionView.vue";
import {
  DEFAULT_LAYOUT_MODE,
  closeAllWindows,
  layoutMode,
  openApp,
} from "../composables/useDesktop.js";
import { clearState } from "../composables/useWorkspaceState.js";

let wrappers = [];

function mountWindow() {
  const win = openApp("decision", { name: "Home" });
  const wrapper = shallowMount(DesktopWindow, {
    attachTo: document.body,
    props: { win, mode: "free" },
  });
  wrappers.push(wrapper);
  return { win, wrapper };
}

function resetShell() {
  for (const wrapper of wrappers) wrapper.unmount();
  wrappers = [];
  closeAllWindows();
  layoutMode.value = DEFAULT_LAYOUT_MODE;
  clearState();
  document.body.replaceChildren();
}

// The menu moves focus in a nextTick callback, so a settled DOM and a settled
// microtask queue are both needed before activeElement means anything.
async function settle() {
  await nextTick();
  await flushPromises();
  await nextTick();
}

beforeEach(() => {
  vi.clearAllMocks();
  resetShell();
});

afterEach(() => {
  resetShell();
});

describe("the placement menu implements the menu-button pattern it declares", () => {
  it("points the trigger at the menu it controls", async () => {
    const { wrapper } = mountWindow();
    const trigger = wrapper.get(".window-position .window-control");

    expect(trigger.attributes("aria-haspopup")).toBe("menu");
    expect(trigger.attributes("aria-expanded")).toBe("false");

    await trigger.trigger("click");
    await settle();

    const menu = wrapper.get('[role="menu"]');
    expect(menu.attributes("id")).toBeTruthy();
    // A menu button whose aria-controls names nothing is a menu button that
    // cannot be resolved by anything reading the relationship.
    expect(trigger.attributes("aria-controls")).toBe(menu.attributes("id"));
    expect(trigger.attributes("aria-expanded")).toBe("true");
  });

  it("opens on ArrowDown and puts focus on the first item", async () => {
    const { wrapper } = mountWindow();
    const trigger = wrapper.get(".window-position .window-control");

    await trigger.trigger("keydown", { key: "ArrowDown" });
    await settle();

    const items = wrapper.findAll('[role="menuitem"]');
    expect(items.length).toBeGreaterThan(1);
    expect(document.activeElement).toBe(items[0].element);
  });

  it("opens on ArrowUp and puts focus on the last item", async () => {
    const { wrapper } = mountWindow();

    await wrapper
      .get(".window-position .window-control")
      .trigger("keydown", { key: "ArrowUp" });
    await settle();

    const items = wrapper.findAll('[role="menuitem"]');
    expect(document.activeElement).toBe(items[items.length - 1].element);
  });

  it("keeps exactly one menu item in the tab order", async () => {
    const { wrapper } = mountWindow();

    await wrapper
      .get(".window-position .window-control")
      .trigger("keydown", { key: "ArrowDown" });
    await settle();

    const items = wrapper.findAll('[role="menuitem"]');
    const tabbable = items.filter((item) => item.attributes("tabindex") === "0");
    // Roving tabindex: a menu reached by Tab should cost one stop, not four.
    expect(tabbable).toHaveLength(1);
    expect(tabbable[0].text()).toBe("Fill the workspace");
    expect(items.filter((item) => item.attributes("tabindex") === "-1")).toHaveLength(
      items.length - 1,
    );
  });

  it("moves focus with the arrow keys, wrapping at both ends", async () => {
    const { wrapper } = mountWindow();
    await wrapper
      .get(".window-position .window-control")
      .trigger("keydown", { key: "ArrowDown" });
    await settle();

    const focusedIndex = () =>
      wrapper
        .findAll('[role="menuitem"]')
        .findIndex((item) => item.element === document.activeElement);

    // Real keydowns originate on the focused item and bubble to the menu.
    const press = async (key) => {
      const from = focusedIndex();
      const items = wrapper.findAll('[role="menuitem"]');
      await items[from === -1 ? 0 : from].trigger("keydown", { key });
      await settle();
      return focusedIndex();
    };

    expect(focusedIndex()).toBe(0);
    expect(await press("ArrowDown")).toBe(1);
    expect(await press("ArrowDown")).toBe(2);
    expect(await press("ArrowDown")).toBe(3);
    // Past the end is the start, not a dead end.
    expect(await press("ArrowDown")).toBe(0);
    // Past the beginning is the end.
    expect(await press("ArrowUp")).toBe(3);
  });

  it("jumps to the first and last item with Home and End", async () => {
    const { wrapper } = mountWindow();
    await wrapper
      .get(".window-position .window-control")
      .trigger("keydown", { key: "ArrowDown" });
    await settle();

    const focusedIndex = () =>
      wrapper
        .findAll('[role="menuitem"]')
        .findIndex((item) => item.element === document.activeElement);
    const press = async (key) => {
      const items = wrapper.findAll('[role="menuitem"]');
      const from = focusedIndex();
      await items[from === -1 ? 0 : from].trigger("keydown", { key });
      await settle();
      return focusedIndex();
    };

    const last = wrapper.findAll('[role="menuitem"]').length - 1;
    expect(await press("End")).toBe(last);
    expect(await press("Home")).toBe(0);
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const { wrapper } = mountWindow();
    const trigger = wrapper.get(".window-position .window-control");

    await trigger.trigger("keydown", { key: "ArrowDown" });
    await settle();
    const items = wrapper.findAll('[role="menuitem"]');
    await items[0].trigger("keydown", { key: "Escape" });
    await settle();

    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
    expect(trigger.attributes("aria-expanded")).toBe("false");
    // Focus has to go somewhere the user can see and act on again.
    expect(document.activeElement).toBe(trigger.element);
  });

  it("closes on Tab rather than trapping the keyboard", async () => {
    const { wrapper } = mountWindow();

    await wrapper
      .get(".window-position .window-control")
      .trigger("keydown", { key: "ArrowDown" });
    await settle();

    const items = wrapper.findAll('[role="menuitem"]');
    await items[0].trigger("keydown", { key: "Tab" });
    await settle();

    // The menu may not keep Tab to itself; it may only stop being open.
    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
  });

  it("closes when the pointer lands outside it, and stays open when it does not", async () => {
    const { wrapper } = mountWindow();
    const trigger = wrapper.get(".window-position .window-control");

    await trigger.trigger("click");
    await settle();
    expect(wrapper.find('[role="menu"]').exists()).toBe(true);

    wrapper.findAll('[role="menuitem"]')[1].element.dispatchEvent(
      new Event("pointerdown", { bubbles: true }),
    );
    await settle();
    expect(wrapper.find('[role="menu"]').exists()).toBe(true);

    document.body.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    await settle();
    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
  });

  it("closes on a choice and returns focus to the trigger", async () => {
    const { wrapper } = mountWindow();
    const trigger = wrapper.get(".window-position .window-control");

    await trigger.trigger("click");
    await settle();

    const leftHalf = wrapper
      .findAll('[role="menuitem"]')
      .find((item) => item.text() === "Left half");
    await leftHalf.trigger("click");
    await settle();

    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
    expect(document.activeElement).toBe(trigger.element);
  });
});

describe("the resize grip states the size it controls", () => {
  it("publishes a splitter's value range and a readable form", async () => {
    const { wrapper } = mountWindow();
    const grip = wrapper.get(".window-resize");

    const min = Number(grip.attributes("aria-valuemin"));
    const max = Number(grip.attributes("aria-valuemax"));
    const now = Number(grip.attributes("aria-valuenow"));

    expect(grip.attributes("role")).toBe("separator");
    expect(Number.isNaN(min)).toBe(false);
    expect(Number.isNaN(max)).toBe(false);
    expect(min).toBeGreaterThan(0);
    expect(max).toBeGreaterThan(min);
    // aria-valuenow outside the range it declares is a contradiction, not a
    // rounding detail.
    expect(now).toBeGreaterThanOrEqual(min);
    expect(now).toBeLessThanOrEqual(max);

    expect(grip.attributes("aria-valuetext")).toMatch(/^\d+ by \d+ pixels$/);
  });

  it("raises aria-valuenow when the panel grows", async () => {
    const { wrapper } = mountWindow();

    const before = Number(wrapper.get(".window-resize").attributes("aria-valuenow"));
    await wrapper.get(".window-resize").trigger("keydown", { key: "ArrowRight" });
    await settle();

    const after = Number(wrapper.get(".window-resize").attributes("aria-valuenow"));
    expect(after).toBeGreaterThan(before);
    expect(wrapper.get(".window-resize").attributes("aria-valuetext")).toContain(
      `${after} by `,
    );
  });

  it("lowers aria-valuenow and stops at the minimum it declares", async () => {
    const { wrapper } = mountWindow();

    const start = Number(wrapper.get(".window-resize").attributes("aria-valuenow"));
    await wrapper.get(".window-resize").trigger("keydown", { key: "ArrowLeft" });
    await settle();

    const shrunk = Number(wrapper.get(".window-resize").attributes("aria-valuenow"));
    expect(shrunk).toBeLessThan(start);

    for (let i = 0; i < 60; i += 1) {
      await wrapper.get(".window-resize").trigger("keydown", { key: "ArrowLeft" });
    }
    await settle();

    const grip = wrapper.get(".window-resize");
    const min = Number(grip.attributes("aria-valuemin"));
    // The floor the grip advertises and the floor it enforces are one number.
    expect(Number(grip.attributes("aria-valuenow"))).toBe(min);
    expect(grip.attributes("aria-valuetext")).toContain(`${min} by `);
  });

  it("tracks a placement that changes the panel's width", async () => {
    const { wrapper } = mountWindow();
    const trigger = wrapper.get(".window-position .window-control");

    await trigger.trigger("click");
    await settle();
    const leftHalf = wrapper
      .findAll('[role="menuitem"]')
      .find((item) => item.text() === "Left half");
    await leftHalf.trigger("click");
    await settle();

    const grip = wrapper.get(".window-resize");
    const now = Number(grip.attributes("aria-valuenow"));
    const min = Number(grip.attributes("aria-valuemin"));
    const max = Number(grip.attributes("aria-valuemax"));
    // "Left half" sets a different width; the declared value has to follow it
    // rather than keep describing the previous geometry.
    expect(now).toBeGreaterThan(min);
    expect(now).toBeLessThanOrEqual(max);
    expect(grip.attributes("aria-valuetext")).toContain(`${now} by `);
  });
});

describe("the loading state keeps its heading out of the live region", () => {
  const mountInteraction = () => {
    const wrapper = shallowMount(InteractionView);
    wrappers.push(wrapper);
    return wrapper;
  };

  it("does not announce a heading as a status message", async () => {
    const wrapper = mountInteraction();
    await settle();

    const state = wrapper.get(".interaction-shell-state.is-loading");
    const region = state.get('[role="status"]');
    const heading = state.get("h2");

    expect(heading.text()).toBe("Loading the report and its saved run.");
    // role="status" is polite and fires on content change, not navigation.
    // A heading inside one is read out as a status message every time the
    // region updates.
    expect(region.element.contains(heading.element)).toBe(false);
    expect(region.attributes("aria-live")).toBe("polite");
  });

  it("leaves the status sentence inside the region", async () => {
    const wrapper = mountInteraction();
    await settle();

    const region = wrapper.get('[role="status"]');
    expect(region.text().trim()).toBe("Opening follow-up questions");
  });

  it("keeps the loading state's heading as the state's only heading", async () => {
    const wrapper = mountInteraction();
    await settle();

    const headings = wrapper.findAll(".interaction-shell-state.is-loading h2");
    expect(headings).toHaveLength(1);
    // The shell state itself is still one block with its step numeral; moving
    // the role must not restructure it.
    expect(wrapper.get(".interaction-shell-state.is-loading .shell-state-index").text()).toBe(
      "05",
    );
  });
});
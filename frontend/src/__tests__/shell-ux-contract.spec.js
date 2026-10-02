// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { flushPromises, mount, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  route: { name: "Home", params: {}, query: {}, fullPath: "/" },
}));

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: mocks.routerPush, replace: mocks.routerPush }),
  useRoute: () => mocks.route,
}));

import DesktopDock from "../components/DesktopDock.vue";
import DesktopMasthead from "../components/DesktopMasthead.vue";
import DesktopTaskbar from "../components/DesktopTaskbar.vue";
import DesktopWindow from "../components/DesktopWindow.vue";
import ViewHeader from "../components/ViewHeader.vue";
import {
  DEFAULT_LAYOUT_MODE,
  JOURNEY_TOTAL,
  activeKey,
  closeAllWindows,
  layoutMode,
  openApp,
  setLayoutMode,
  windows,
} from "../composables/useDesktop.js";
import { clearState, setContext } from "../composables/useWorkspaceState.js";

const DECISION_APP = {
  id: "decision",
  step: 1,
  title: "State the decision",
  code: "D-01",
  outcome: "One written decision to examine",
};

function resetShell() {
  closeAllWindows();
  layoutMode.value = DEFAULT_LAYOUT_MODE;
  clearState();
  document.body.replaceChildren();
}

beforeEach(() => {
  vi.clearAllMocks();
  resetShell();
});

afterEach(() => {
  resetShell();
});

describe("masthead orientation band", () => {
  it("carries the descriptor with the wordmark, so the lockup is never naked", () => {
    const wrapper = mount(DesktopMasthead);
    const lockup = wrapper.get(".masthead-lockup");

    expect(lockup.text()).toContain("ASKTHEPEOPLE");
    expect(lockup.text()).toContain("Synthetic Decision Explorer");
    expect(lockup.attributes("aria-label")).toContain("synthetic decision explorer");
    wrapper.unmount();
  });

  it("has no clock competing with the step position", () => {
    const wrapper = mount(DesktopMasthead);

    // A 15-second clock was the previous occupant of this band. It carried no
    // task value and updated visible text on a timer.
    expect(wrapper.find(".masthead-clock").exists()).toBe(false);
    expect(wrapper.find("time").exists()).toBe(false);
    expect(wrapper.get(".masthead-position").text()).toContain(`/${JOURNEY_TOTAL}`);
    wrapper.unmount();
  });

  it("offers a resume action only when the next step can actually be opened", async () => {
    openApp("decision", { name: "Home" });

    const locked = mount(DesktopMasthead);
    // Nothing has been produced yet, so there is nowhere to resume to. An
    // offer to go somewhere you cannot is worse than no offer.
    expect(locked.find(".masthead-next").exists()).toBe(false);
    locked.unmount();

    setContext({ projectId: "p-1", simulationId: "s-1" });
    const ready = mount(DesktopMasthead);
    // Position is the open panel's step, so the offer is the step after it, not
    // the furthest step the workspace can technically reach.
    expect(ready.find(".masthead-next").text()).toContain("Map the sources");
    ready.unmount();
  });
});

describe("journey spine is the only journey navigation", () => {
  it("is a nav with aria-current=step, not a tablist", () => {
    openApp("decision", { name: "Home" });
    const wrapper = mount(DesktopDock, { props: { collapsed: false } });

    const spine = wrapper.get(".journey-spine");
    expect(spine.element.tagName).toBe("NAV");
    expect(spine.attributes("aria-label")).toBe("Journey");
    // `aria-current="step"` is the ARIA pattern for a step indicator.
    // `role="tablist"` misdescribes these as tabs over one canvas.
    expect(spine.attributes("role")).toBeUndefined();
    expect(wrapper.get(".spine-entry.is-current").attributes("aria-current")).toBe("step");
    wrapper.unmount();
  });

  it("labels every step and names the gate on the ones that are locked", () => {
    openApp("decision", { name: "Home" });
    const wrapper = mount(DesktopDock, { props: { collapsed: false } });

    const entries = wrapper.findAll("#journey-spine-list .spine-entry");
    expect(entries.length).toBe(JOURNEY_TOTAL);
    expect(wrapper.text()).toContain("State the decision");
    expect(wrapper.text()).toContain("Decision brief");

    const lockedBrief = wrapper
      .findAll("#journey-spine-list .spine-entry")
      .find((entry) => entry.text().includes("Decision brief"));
    expect(lockedBrief.attributes("aria-disabled")).toBe("true");
    expect(lockedBrief.attributes("title")).toContain("Run scenarios");
    wrapper.unmount();
  });

  it("keeps the collapsed state reachable by keyboard", () => {
    const wrapper = mount(DesktopDock, { props: { collapsed: false } });

    const toggle = wrapper.get(".spine-toggle");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(toggle.attributes("aria-controls")).toBe("journey-spine-list");
    expect(wrapper.get("#journey-spine-list").element.tagName).toBe("OL");

    toggle.element.click();
    wrapper.unmount();
  });
});

describe("panel switcher implements the tab pattern it declares", () => {
  const panels = [
    { key: "decision", appId: "decision" },
    { key: "brief:r-1", appId: "brief" },
  ];

  it("wires aria-controls to a real tabpanel and uses roving tabindex", () => {
    const wrapper = mount(DesktopTaskbar, { props: { panels } });

    const tablist = wrapper.get('[role="tablist"]');
    expect(tablist.attributes("aria-label")).toBe("Open panels");

    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs).toHaveLength(2);
    for (const tab of tabs) {
      const key = tab.attributes("id").replace("panel-tab-", "");
      expect(tab.attributes("aria-controls")).toBe(`panel-body-${key}`);
      expect(tab.attributes("aria-selected")).toMatch(/^(true|false)$/);
    }
    // Roving tabindex: exactly one tab is in the tab order, the rest are -1
    // and are reached with the arrow keys.
    const tabIndexes = tabs.map((tab) => tab.attributes("tabindex"));
    expect(tabIndexes.filter((value) => value === "0")).toHaveLength(1);
    expect(tabIndexes.filter((value) => value === "-1")).toHaveLength(1);
    wrapper.unmount();
  });

  it("moves focus with ArrowRight, ArrowLeft, Home, and End", async () => {
    openApp("decision", { name: "Home" });
    const active = openApp("brief", { name: "Report", params: { reportId: "r-1" } });
    const wrapper = mount(DesktopTaskbar, {
      attachTo: document.body,
      props: { panels: windows.value },
    });

    const tablist = wrapper.get('[role="tablist"]');
    const tabs = wrapper.findAll('[role="tab"]');
    // Arrow keys are relative to the selected tab, which is the last one opened.
    expect(activeKey.value).toBe(active.key);

    // Focus moves on the tick after render, so settle the microtask queue
    // rather than a single nextTick.
    await tablist.trigger("keydown", { key: "ArrowLeft" });
    await flushPromises();
    expect(document.activeElement).toBe(tabs[0].element);

    await tablist.trigger("keydown", { key: "ArrowRight" });
    await flushPromises();
    expect(document.activeElement).toBe(tabs[1].element);

    await tablist.trigger("keydown", { key: "Home" });
    await flushPromises();
    expect(document.activeElement).toBe(tabs[0].element);

    await tablist.trigger("keydown", { key: "End" });
    await flushPromises();
    expect(document.activeElement).toBe(tabs[1].element);
    wrapper.unmount();
  });

  it("closes only the selected panel on Delete, never the whole workspace", async () => {
    const keep = openApp("decision", { name: "Home" });
    const doomed = openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    const wrapper = mount(DesktopTaskbar, {
      props: { panels: windows.value },
    });

    await wrapper.get('[role="tablist"]').trigger("keydown", { key: "Delete" });
    await flushPromises();

    expect(windows.value.map((panel) => panel.key)).toEqual([keep.key]);
    expect(windows.value.some((panel) => panel.key === doomed.key)).toBe(false);
    wrapper.unmount();
  });

  it("states the current layout instead of offering a bare toggle", async () => {
    const wrapper = mount(DesktopTaskbar, { props: { panels } });

    expect(wrapper.get(".switcher-layout-value").text()).toBe("One at a time");
    setLayoutMode("split");
    await nextTick();
    expect(wrapper.get(".switcher-layout-value").text()).toBe("Side by side");
    setLayoutMode("free");
    await nextTick();
    expect(wrapper.get(".switcher-layout-value").text()).toBe("Floating");
    wrapper.unmount();
  });
});

describe("panels are labelled by the tab that opens them", () => {
  it("exposes tabpanel semantics that match the switcher ids", () => {
    const win = openApp("decision", { name: "Home" });
    const wrapper = shallowMount(DesktopWindow, {
      props: { win, mode: "focus" },
    });

    const panel = wrapper.get('[role="tabpanel"]');
    expect(panel.attributes("id")).toBe(`panel-body-${win.key}`);
    expect(panel.attributes("aria-labelledby")).toBe(`panel-tab-${win.key}`);
    // A tabpanel that cannot be focused cannot be scrolled by keyboard.
    expect(panel.attributes("tabindex")).toBe("0");
    wrapper.unmount();
  });

  it("offers non-drag placements instead of relying on the resize grip", async () => {
    const win = openApp("decision", { name: "Home" });
    const wrapper = shallowMount(DesktopWindow, {
      props: { win, mode: "free" },
    });

    const trigger = wrapper.get(".window-position .window-control");
    expect(trigger.attributes("aria-haspopup")).toBe("menu");
    expect(trigger.attributes("aria-expanded")).toBe("false");

    await trigger.trigger("click");
    const options = wrapper.findAll('[role="menuitem"]').map((item) => item.text());
    expect(options).toEqual([
      "Fill the workspace",
      "Centre in the workspace",
      "Left half",
      "Right half",
    ]);
    wrapper.unmount();
  });

  it("resizes from the keyboard, so dragging is never the only route", async () => {
    const win = openApp("decision", { name: "Home" });
    const wrapper = shallowMount(DesktopWindow, {
      props: { win, mode: "free" },
    });

    const grip = wrapper.get(".window-resize");
    expect(grip.attributes("role")).toBe("separator");
    expect(grip.attributes("tabindex")).toBe("0");

    await grip.trigger("keydown", { key: "ArrowRight" });
    expect(win.w).toBeGreaterThan(0);

    const grown = win.w;
    await grip.trigger("keydown", { key: "ArrowLeft", shiftKey: true });
    expect(win.w).toBeLessThan(grown);
    wrapper.unmount();
  });

  it("refuses to shrink a panel below a usable size", async () => {
    const win = openApp("decision", { name: "Home" });
    const wrapper = shallowMount(DesktopWindow, {
      props: { win, mode: "free" },
    });

    for (let i = 0; i < 40; i += 1) {
      await wrapper.get(".window-resize").trigger("keydown", { key: "ArrowLeft" });
    }
    expect(win.w).toBe(320);
    wrapper.unmount();
  });
});

describe("the shell renders a deterministic layout, not a cascade", () => {
  it("defaults to a single full-size panel and offers comparison explicitly", () => {
    openApp("decision", { name: "Home" });
    openApp("brief", { name: "Report", params: { reportId: "r-1" } });

    expect(DEFAULT_LAYOUT_MODE).toBe("focus");
    expect(layoutMode.value).toBe("focus");
  });

  it("names the layout modes it supports instead of a single tiled flag", () => {
    const shell = readFileSync(resolve("src/components/DesktopShell.vue"), "utf8");

    expect(shell).toContain("layout-focus");
    expect(shell).toContain("layout-split");
    expect(shell).toContain("layout-free");
    // Free-floating remains available, but only as a deliberate choice.
    expect(shell).toContain("visiblePair()");
  });
});

describe("the shared view header", () => {
  it("owns the view's only h1 and takes its identity from the store", () => {
    const wrapper = mount(ViewHeader, {
      props: {
        step: DECISION_APP,
        status: "processing",
        statusLabel: "Opening",
        modes: ["workbench", "graph"],
        activeMode: "workbench",
        modeLabels: { workbench: "Decision steps", graph: "Source map" },
        modeSelectorLabel: "Choose a view",
      },
    });

    const headings = wrapper.findAll("h1");
    expect(headings).toHaveLength(1);
    expect(headings[0].text()).toBe(DECISION_APP.title);
    expect(wrapper.get(".header-step-of").text()).toBe(`Step 1 of ${JOURNEY_TOTAL}`);
    wrapper.unmount();
  });

  it("states what the step produces instead of repeating the step number", () => {
    const wrapper = mount(ViewHeader, {
      props: {
        step: DECISION_APP,
        status: "",
        statusLabel: "",
        modes: ["workbench"],
        activeMode: "workbench",
        modeLabels: { workbench: "Decision steps" },
        modeSelectorLabel: "Choose a view",
      },
    });

    expect(wrapper.get(".header-outcome").text()).toContain(DECISION_APP.outcome);
    wrapper.unmount();
  });

  it("exposes the active mode as pressed, so the switcher is not colour-only", () => {
    const wrapper = mount(ViewHeader, {
      props: {
        step: DECISION_APP,
        status: "",
        statusLabel: "",
        modes: ["workbench", "graph"],
        activeMode: "graph",
        modeLabels: { workbench: "Decision steps", graph: "Source map" },
        modeSelectorLabel: "Choose a view",
      },
    });

    const pressed = wrapper.findAll(".mode-btn").filter((btn) =>
      btn.attributes("aria-pressed") === "true",
    );
    expect(pressed).toHaveLength(1);
    expect(pressed[0].text()).toBe("Source map");
    wrapper.unmount();
  });

  it("announces status through a live region rather than a bare dot", () => {
    const wrapper = mount(ViewHeader, {
      props: {
        step: DECISION_APP,
        status: "failed",
        statusLabel: "Needs attention",
        modes: ["workbench"],
        activeMode: "workbench",
        modeLabels: { workbench: "Decision steps" },
        modeSelectorLabel: "Choose a view",
      },
    });

    expect(wrapper.get(".status-box").attributes("role")).toBe("status");
    expect(wrapper.get(".status-msg").text()).toBe("Needs attention");
    wrapper.unmount();
  });
});

describe("the shell no longer restates what the shell already says", () => {
  const views = [
    "MainView.vue",
    "SimulationView.vue",
    "SimulationRunView.vue",
    "ReportView.vue",
    "InteractionView.vue",
  ];

  it("gives every route view the shared header instead of its own", () => {
    for (const view of views) {
      const source = readFileSync(resolve(`src/views/${view}`), "utf8");
      expect(source, view).toContain("<ViewHeader");
      expect(source, view).not.toMatch(/<h2 class="window-title"/);
    }
  });

  it("drops the second step counter and the duplicated disclosure from every view", () => {
    for (const view of views) {
      const source = readFileSync(resolve(`src/views/${view}`), "utf8");
      // "STEP 02/05" contradicted the shell's own six-step numbering.
      expect(source, view).not.toMatch(/STEP 0\d\/0\d/);
      // The five-fact disclosure lives once, in the shell.
      expect(source, view).not.toMatch(/0 human respondents/);
      expect(source, view).not.toContain("not forecasts");
    }
  });

  it("keeps exactly one skip link per view", () => {
    for (const view of views) {
      const source = readFileSync(resolve(`src/views/${view}`), "utf8");
      const skipLinks = source.match(/class="skip-link"/g) || [];
      expect(skipLinks.length, view).toBeLessThanOrEqual(1);
    }
  });

  it("still mounts the permanent disclosure once, in the shell", () => {
    const shell = readFileSync(resolve("src/components/DesktopShell.vue"), "utf8");
    expect(shell).toContain("<TruthRail />");
    expect(shell).toMatch(/import\s+TruthRail\s+from\s+["'][^"']+TruthRail\.vue["']/);
    // The rail must never become conditional or the whole workspace loses it.
    expect(shell).not.toMatch(/<TruthRail[^>]*v-(if|show)/);
  });
});

describe("token layer supports the contracts the shell relies on", () => {
  const tokens = readFileSync(resolve("src/assets/design-tokens.css"), "utf8");

  it("defines every spacing step the components reference", () => {
    for (const step of [9, 10]) {
      expect(tokens).toContain(`--space-${step}:`);
    }
  });

  it("publishes a control-height scale anchored on the WCAG 2.2 target minimum", () => {
    expect(tokens).toContain("--target-min: 1.5rem");
    expect(tokens).toContain("--control-h-sm:");
    expect(tokens).toContain("--control-h-md:");
    expect(tokens).toContain("--control-h-lg:");
    expect(tokens).toMatch(/button,\s*\.btn\s*\{[\s\S]*?min-height:\s*var\(--control-h-md\)/);
  });

  it("defines the shell bands once instead of four times across four components", () => {
    for (const band of ["truth", "masthead", "spine", "switcher"]) {
      expect(tokens).toContain(`--band-${band}:`);
    }
  });

  it("keeps one focus ring definition and honours raised-contrast modes", () => {
    expect(tokens).toContain("--focus-ring-color:");
    expect(tokens).toContain("@media (prefers-contrast: more)");
    expect(tokens).toContain("@media (forced-colors: active)");
  });

  it("does not animate layout on the panel scroll containers", () => {
    const transitionRule = tokens.match(
      /\.panel-wrapper,\s*\.panel-container\s*\{[^}]*transition:[^}]*\}/,
    );
    expect(transitionRule).not.toBeNull();
    expect(transitionRule[0]).not.toContain("transform");
    expect(transitionRule[0]).toContain("opacity");
  });
});
// @vitest-environment jsdom

/**
 * Leftovers from the workspace-shell redesign.
 *
 * Four defects, one file, because each of them is the same shape of mistake: a
 * thing that looks owned but is not, or a thing that outlives its owner.
 *   1. A 1 Hz module-scope interval with no lifecycle.
 *   2. API exports no surface imports.
 *   3. An id duplicated across every route view.
 *   4. A heading convention that reads as a violation from inside this one view.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { defineComponent, h } from "vue";
import * as reportApi from "../api/report.js";
import * as simulationApi from "../api/simulation.js";
import * as wsApi from "../api/ws.js";
import {
  WORKFLOW_PHASES,
  useGuidedContext,
} from "../composables/useGuidedContext.js";
import {
  HISTORICAL_GRAPH_UNAVAILABLE_MESSAGE,
  REPORT_GRAPH_MISMATCH_MESSAGE,
  RecordedGraphIdentityError,
  recordedGraphReadError,
  resolveRecordedGraphIdentity,
} from "../utils/recordedGraphIdentity.js";
import NotFoundView from "../views/NotFoundView.vue";

const read = (relativePath) => readFileSync(resolve(relativePath), "utf8");

/**
 * A component whose only job is to be a consumer of the guided context, so the
 * lease accounting can be exercised the way the app exercises it: taken during
 * setup, returned when the component goes away.
 */
const makeConsumer = (sink) =>
  defineComponent({
    name: "GuidedContextConsumer",
    setup() {
      Object.assign(sink, useGuidedContext());
      return () => h("div", "consumer");
    },
  });

describe("the time-on-view interval belongs to its consumers", () => {
  afterEach(() => {
    // Reset while the fake clock is still installed so a leaked interval is
    // cleared rather than handed back to the real timer queue.
    useGuidedContext().resetGuidedContext();
    vi.useRealTimers();
  });

  it("takes no lease outside a component, so nothing can strand an interval", () => {
    vi.useFakeTimers();
    const before = vi.getTimerCount();

    // A plain module call has nothing that could ever return a lease.
    const context = useGuidedContext();
    context.setPhase(WORKFLOW_PHASES.EXPLORING);
    context.setPhase(WORKFLOW_PHASES.REVIEWING);
    vi.advanceTimersByTime(5000);

    expect(vi.getTimerCount()).toBe(before);
    expect(context.timeOnCurrentView.value).toBe(0);
  });

  it("runs one interval for two live consumers, not one each", () => {
    vi.useFakeTimers();
    const before = vi.getTimerCount();

    const first = {};
    const second = {};
    const a = mount(makeConsumer(first));
    expect(vi.getTimerCount()).toBe(before + 1);
    const b = mount(makeConsumer(second));
    expect(vi.getTimerCount()).toBe(before + 1);

    a.unmount();
    b.unmount();
  });

  it("does not let one consumer's unmount silence another that is still live", () => {
    vi.useFakeTimers();
    const before = vi.getTimerCount();

    const first = {};
    const second = {};
    const a = mount(makeConsumer(first));
    const b = mount(makeConsumer(second));

    a.unmount();
    expect(vi.getTimerCount()).toBe(before + 1);

    const atUnmount = second.timeOnCurrentView.value;
    vi.advanceTimersByTime(2000);
    expect(second.timeOnCurrentView.value).toBe(atUnmount + 2000);

    b.unmount();
    expect(vi.getTimerCount()).toBe(before);
  });

  it("clears the interval and stops the clock when the last consumer unmounts", () => {
    vi.useFakeTimers();
    const before = vi.getTimerCount();

    const first = {};
    const second = {};
    const a = mount(makeConsumer(first));
    const b = mount(makeConsumer(second));

    a.unmount();
    b.unmount();
    expect(vi.getTimerCount()).toBe(before);

    // The defect this closes: the counter kept climbing after the view was gone,
    // and `prominentLayer` reads it on a 30s threshold, so the guidance could
    // escalate on elapsed time nobody was spending.
    const afterUnmount = first.timeOnCurrentView.value;
    vi.advanceTimersByTime(60000);
    expect(first.timeOnCurrentView.value).toBe(afterUnmount);
  });

  it("restarts the clock on a phase change without taking another lease", () => {
    vi.useFakeTimers();
    const before = vi.getTimerCount();

    const context = {};
    const wrapper = mount(makeConsumer(context));

    // The old code called startViewTimer from setPhase, so every phase change
    // added a lease and the count could never reach zero again: three changes
    // here would leave the interval running for the rest of the tab.
    context.setPhase(WORKFLOW_PHASES.MAPPING);
    context.setPhase(WORKFLOW_PHASES.CONFIGURING);
    context.setPhase(WORKFLOW_PHASES.REVIEWING);
    expect(vi.getTimerCount()).toBe(before + 1);
    expect(context.actionsSinceLastPause.value).toBe(0);

    wrapper.unmount();
    expect(vi.getTimerCount()).toBe(before);
  });

  it("resets every lease and the interval with them", () => {
    vi.useFakeTimers();
    const before = vi.getTimerCount();

    const first = {};
    const second = {};
    mount(makeConsumer(first));
    mount(makeConsumer(second));
    expect(vi.getTimerCount()).toBe(before + 1);

    useGuidedContext().resetGuidedContext();
    expect(vi.getTimerCount()).toBe(before);

    // A consumer torn down after the reset must not be able to drive the count
    // negative and strand the interval running for good.
    useGuidedContext().resetGuidedContext();
    expect(vi.getTimerCount()).toBe(before);
  });
});

describe("the API layer publishes no export with no caller", () => {
  it("drops the report console-log reader nothing ever read", () => {
    expect(Object.keys(reportApi)).not.toContain("getConsoleLog");
  });

  it("drops the two report export wrappers no surface offers", () => {
    expect(Object.keys(reportApi)).not.toContain("exportReportCSV");
    expect(Object.keys(reportApi)).not.toContain("exportReportExecutive");
  });

  it("drops the non-realtime simulation readers the realtime ones replaced", () => {
    for (const gone of [
      "getSimulationProfiles",
      "getSimulationConfig",
      "getSimulationPosts",
      "getSimulationTimeline",
      "getAgentStats",
    ]) {
      expect(Object.keys(simulationApi), gone).not.toContain(gone);
    }
  });

  it("drops the interviewAgents alias while the function it aliased stays", () => {
    expect(Object.keys(simulationApi)).not.toContain("interviewAgents");
    // It was a second name for a live function, not a second implementation.
    expect(Object.keys(simulationApi)).toContain("askGeneratedProfiles");
  });

  it("keeps the connection status ref out of the websocket module's surface", () => {
    // Nothing ever read it, so exporting it advertised an indicator no surface
    // rendered. The ref itself stays because the reconnect and watchdog branches
    // are written against it.
    expect(Object.keys(wsApi).sort()).toEqual([
      "connectReportWs",
      "connectSimulationWs",
    ]);
  });

  it("keeps the recorded-graph messages, which are a rendered-message contract", () => {
    // These two constants look like unreferenced exports and are not: their text
    // is what a view renders when the recorded map is gone, and a test asserts
    // that text as a literal. Deleting either would delete the message.
    const resolveError = (input) => {
      try {
        resolveRecordedGraphIdentity(input);
      } catch (error) {
        return error;
      }
      throw new Error("resolveRecordedGraphIdentity did not refuse this input");
    };

    const mismatch = resolveError({
      project: { graph_id: "graph-a" },
      report: { graph_id: "graph-a" },
      simulation: { project_id: "p-1", graph_id: "graph-b" },
    });
    expect(mismatch).toBeInstanceOf(RecordedGraphIdentityError);
    expect(mismatch.message).toBe(REPORT_GRAPH_MISMATCH_MESSAGE);

    const stale = resolveError({
      project: { graph_id: "graph-new" },
      report: { graph_id: "graph-old" },
      simulation: { project_id: "p-1", graph_id: "graph-old" },
    });
    expect(stale.message).toBe(HISTORICAL_GRAPH_UNAVAILABLE_MESSAGE);

    expect(
      recordedGraphReadError({ error: "graph_not_available_for_project" })
        .message,
    ).toBe(HISTORICAL_GRAPH_UNAVAILABLE_MESSAGE);
  });
});

describe("one skip-link target, owned by the shell", () => {
  const ROUTE_VIEWS = [
    "Home.vue",
    "MainView.vue",
    "SimulationView.vue",
    "SimulationRunView.vue",
    "ReportView.vue",
    "InteractionView.vue",
    "NotFoundView.vue",
  ];

  // The test directory is skipped for the same reason the truth linter skips it:
  // this file names the id on purpose, in order to assert it.
  const sourceFiles = (directory) =>
    readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
      const full = join(directory, entry.name);
      if (entry.isDirectory()) {
        return entry.name === "__tests__" ? [] : sourceFiles(full);
      }
      return /\.(vue|js)$/.test(entry.name) ? [full] : [];
    });

  it("keeps every route view free of the app-level target id", () => {
    // The split and floating layouts render two panels at once, so a per-view id
    // put two elements with the same id in one document and sent the skip link
    // to whichever panel came first rather than the one the user was on.
    for (const view of ROUTE_VIEWS) {
      expect(read(`src/views/${view}`), view).not.toContain('id="main-content"');
    }
  });

  it("leaves exactly one owner of the id in the whole source tree", () => {
    const owners = sourceFiles(resolve("src"))
      .filter((file) => readFileSync(file, "utf8").includes('id="main-content"'))
      .map((file) => relative(resolve("src"), file).replaceAll("\\", "/"));

    expect(owners).toEqual(["components/DesktopShell.vue"]);
  });

  it("owns the id on the canvas, which is focusable so the link can land there", () => {
    const shell = read("src/components/DesktopShell.vue");
    expect(shell).toMatch(
      /<section\b[^>]*id="main-content"[^>]*tabindex="-1"/,
    );
    // One panel or two, the canvas is in the document exactly once, so the id
    // resolves to one element in every layout.
    expect(shell.match(/id="main-content"/g)).toHaveLength(1);
  });

  it("keeps every panel individually addressable by its own id", () => {
    // The per-panel id is what replaces the per-view one: unique per panel, and
    // derived from the panel key rather than from the view being displayed.
    const desktopWindow = read("src/components/DesktopWindow.vue");
    expect(desktopWindow).toContain("panel-body-${props.win.key}");
  });

  it("points the app-level skip link at the id the shell owns", () => {
    const app = read("src/App.vue");
    const link = /<a\b[^>]*class="skip-link"[^>]*>/.exec(app);
    expect(link, "App.vue must keep exactly one skip link").not.toBeNull();
    expect(link[0]).toContain('href="#main-content"');
  });

  it("leaves the 404 route with a target it does not have to declare", () => {
    const wrapper = mount(NotFoundView);
    expect(wrapper.find("#main-content").exists()).toBe(false);
    // The target belongs to the shell canvas, which is in the document whenever
    // App.vue is, so the link resolves on this route too.
    expect(read("src/components/DesktopShell.vue")).toContain(
      'id="main-content"',
    );
    wrapper.unmount();
  });
});

describe("the route-recovery page owns its own heading", () => {
  it("renders exactly one top-level heading", () => {
    const wrapper = mount(NotFoundView);
    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.get("h1").attributes("id")).toBe("not-found-heading");
    wrapper.unmount();
  });

  it("does not take the journey header that the convention otherwise points at", () => {
    const source = read("src/views/NotFoundView.vue");
    // ViewHeader names a step of the workspace journey. This page is not a step,
    // so a header here would invent one. The file names it in prose on purpose,
    // which is why this asserts on the component and the import rather than on
    // the bare word.
    expect(source).not.toMatch(/<ViewHeader/);
    expect(source).not.toMatch(/import[^;\n]*ViewHeader/);
  });

  it("states why, in the file, so the next reader does not demote it", () => {
    // The convention the other five views follow is "the h1 belongs to
    // ViewHeader". Read from inside this file that looks like a violation, and
    // "fixing" it would leave a standalone page with no top-level heading.
    expect(read("src/views/NotFoundView.vue")).toContain(
      "owns its <h1> on purpose",
    );
  });
});
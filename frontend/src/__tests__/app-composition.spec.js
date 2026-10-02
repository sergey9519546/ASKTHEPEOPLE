// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createRouter, createMemoryHistory } from "vue-router";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Every other spec mounts one component in isolation with its siblings stubbed.
 * Nothing in the suite composed App -> DesktopShell -> route view -> store, so a
 * wiring mistake that only appears at runtime - a missing export, a provide that
 * never arrives, a watcher that throws on cold load - would have passed all 250
 * other tests and then blank-screened the product.
 *
 * Data calls are cut at the XMLHttpRequest layer and left pending, which is what
 * a real cold load looks like. That keeps the test about composition rather than
 * about payloads, and it means a component that fires a request the shell cannot
 * survive still gets caught.
 */

const captured = [];

class SilentRequest {
  constructor() {
    this.readyState = 0;
    this.status = 0;
    this.responseText = "";
    this.response = "";
    this.timeout = 0;
    this.withCredentials = false;
  }
  open() {
    this.readyState = 1;
  }
  setRequestHeader() {}
  getResponseHeader() {
    return null;
  }
  getAllResponseHeaders() {
    return "";
  }
  overrideMimeType() {}
  send() {
    // Never settles, and never fails. A cold load.
  }
  abort() {}
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() {
    return true;
  }
}

const OriginalRequest = globalThis.XMLHttpRequest;

beforeEach(() => {
  captured.length = 0;
  globalThis.XMLHttpRequest = SilentRequest;
});

afterEach(() => {
  globalThis.XMLHttpRequest = OriginalRequest;
  vi.restoreAllMocks();
});

import App from "../App.vue";
import appRouter from "../router/index.js";
import { layoutMode, windows } from "../composables/useDesktop.js";

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    // The route table lives on the configured router instance; the module keeps
    // its `routes` array module-local, so read it off the instance.
    routes: appRouter.options.routes,
  });
}

const wrappers = [];

afterEach(() => {
  while (wrappers.length) wrappers.pop().unmount();
});

async function mountApp() {
  const router = buildRouter();
  await router.push("/");
  await router.isReady();

  const wrapper = mount(App, {
    global: {
      plugins: [router],
      config: {
        // Vue reports "Unhandled error during execution of watcher callback"
        // without the cause; this is the only place the cause surfaces.
        errorHandler: (err) => {
          captured.push(err);
        },
      },
    },
  });
  wrappers.push(wrapper);
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

function describeFailures() {
  return captured
    .map((err) => (err && err.stack ? `${err.message}\n${err.stack}` : String(err)))
    .join("\n\n");
}

describe("the application composes", () => {
  it("mounts App, all four orientation bands, and a panel with no unhandled error", async () => {
    const { wrapper } = await mountApp();

    expect(describeFailures()).toBe("");

    expect(wrapper.find(".truth-rail").exists()).toBe(true);
    expect(wrapper.find(".desktop-masthead").exists()).toBe(true);
    expect(wrapper.find(".journey-spine").exists()).toBe(true);
    expect(wrapper.find(".panel-switcher").exists()).toBe(true);
    expect(wrapper.find(".desktop-surface").exists()).toBe(true);

    expect(windows.value.length).toBeGreaterThan(0);
    expect(wrapper.find(".desktop-window").exists()).toBe(true);
  });

  it("boots on a deep link rather than bouncing to the start", async () => {
    // The shell waits for router.isReady before resolving the initial panel.
    // Without that wait a direct load lands on START_LOCATION, which has no
    // route name, and the product opens on the decision screen instead of the
    // report the link asked for.
    const router = createRouter({
      history: createMemoryHistory(),
      // The route table lives on the configured router instance; the module keeps
    // its `routes` array module-local, so read it off the instance.
    routes: appRouter.options.routes,
    });
    await router.push("/simulation/sim-1/start");
    await router.isReady();

    const wrapper = mount(App, {
      global: {
        plugins: [router],
        config: { errorHandler: (err) => captured.push(err) },
      },
    });
    wrappers.push(wrapper);
    await flushPromises();
    await flushPromises();

    expect(describeFailures()).toBe("");
    expect(router.currentRoute.value.name).toBe("SimulationRun");
    expect(wrapper.find(".desktop-window").exists()).toBe(true);
  });

  it("opens a second route without a reload", async () => {
    const { wrapper, router } = await mountApp();
    expect(describeFailures()).toBe("");

    await router.push("/simulation/sim-1");
    await flushPromises();
    await flushPromises();

    expect(describeFailures()).toBe("");
    expect(wrapper.find(".desktop-window").exists()).toBe(true);
    expect(wrapper.findAll(".desktop-window").length).toBeGreaterThanOrEqual(1);
  });

  it("writes the canvas layout class the shell is actually rendering", async () => {
    const { wrapper } = await mountApp();
    expect(wrapper.get(".desktop-surface").classes()).toContain(
      `layout-${layoutMode.value}`,
    );
  });

  it("names the transition subject exactly once and styles that subject", () => {
    // Dead transition CSS is invisible: the pseudo-elements simply never match.
    // Without this the feature can be half-deleted and still "pass".
    const shell = readFileSync(
      resolve("src/components/DesktopShell.vue"),
      "utf8",
    );
    const declared = shell.match(/view-transition-name:\s*([a-z-]+)/g) || [];
    expect(declared).toHaveLength(1);

    const subject = declared[0].split(":")[1].trim();
    const styled = [
      ...shell.matchAll(/::view-transition-(?:old|new)\(([a-z-]+)\)/g),
    ].map((match) => match[1]);
    expect(styled.length).toBeGreaterThan(0);
    for (const name of styled) expect(name).toBe(subject);
  });
});
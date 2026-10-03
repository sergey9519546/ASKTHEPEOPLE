// @vitest-environment jsdom

import { createRouter, createMemoryHistory } from "vue-router";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import DesktopShell from "../components/DesktopShell.vue";
import appRoutes from "../router/index.js";
import { activeKey, closeAllWindows, windows } from "../composables/useDesktop.js";

/**
 * A route that matches no journey panel must tell the user, not pretend.
 *
 * This application has no `<router-view>` anywhere — panels render route views
 * directly through the desktop store. `NotFoundView` was registered in the
 * router but absent from `DESKTOP_APPS`, and the shell's URL watcher opened the
 * decision panel for any unmatched route name. The result was that a mistyped
 * or stale deep link rendered the decision screen with no indication anything
 * was wrong, and it also rewrote the persisted workspace session as a side
 * effect.
 *
 * Nothing tested this. These tests pin the behaviour that was actually wanted.
 */

const wrappers = [];

afterEach(() => {
  while (wrappers.length) wrappers.pop().unmount();
  closeAllWindows();
});

async function bootAt(path) {
  const router = createRouter({ history: createMemoryHistory(), routes: appRoutes.options.routes });
  await router.push(path);
  await router.isReady();

  const wrapper = mount(DesktopShell, {
    global: {
      plugins: [router],
      stubs: {
        DesktopMasthead: true,
        DesktopDock: true,
        DesktopTaskbar: true,
        TruthRail: true,
      },
    },
  });
  wrappers.push(wrapper);
  await flushPromises();
  await flushPromises();
  return wrapper;
}

describe("an unmatched route is reported, not silently replaced", () => {
  it("shows the route-recovery view instead of the decision screen", async () => {
    const wrapper = await bootAt("/definitely-not-a-route");

    expect(wrapper.find(".route-recovery").exists()).toBe(true);
    expect(wrapper.find(".public-signal-home").exists()).toBe(false);
    // The recovery view is the one the router already declared for this.
    expect(wrapper.text()).toContain("Route recovery");
  });

  it("leaves the URL alone rather than rewriting it to the start", async () => {
    const wrapper = await bootAt("/definitely-not-a-route");

    expect(wrapper.vm.$router.currentRoute.value.path).toBe("/definitely-not-a-route");
  });

  it("does not silently change what the workspace restores to next time", async () => {
    await bootAt("/definitely-not-a-route");

    // Opening the decision panel here would have persisted it as the active
    // panel, so a bad link would change what the user gets back on return.
    expect(windows.value).toHaveLength(0);
  });

  it("still resolves a real journey route normally", async () => {
    const wrapper = await bootAt("/");

    expect(wrapper.find(".route-recovery").exists()).toBe(false);
    expect(windows.value.length).toBeGreaterThan(0);
    expect(activeKey.value).toBeTruthy();
  });

  it("recovers when the user navigates back to a real route", async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: appRoutes.options.routes });
    await router.push("/definitely-not-a-route");
    await router.isReady();

    const wrapper = mount(DesktopShell, {
      global: {
        plugins: [router],
        stubs: {
          DesktopMasthead: true,
          DesktopDock: true,
          DesktopTaskbar: true,
          TruthRail: true,
        },
      },
    });
    wrappers.push(wrapper);
    await flushPromises();
    expect(wrapper.find(".route-recovery").exists()).toBe(true);

    await router.push("/");
    await flushPromises();
    await flushPromises();

    expect(wrapper.find(".route-recovery").exists()).toBe(false);
    expect(windows.value.length).toBeGreaterThan(0);
  });
});
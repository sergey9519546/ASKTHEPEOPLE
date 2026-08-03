import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import CommandPalette from "../components/CommandPalette.vue";
import {
  closePalette,
  closeSettings,
  isPaletteChord,
  openPalette,
  paletteOpen,
  settingsOpen,
} from "../composables/useCommandPalette.js";

const push = vi.fn();
const back = vi.fn();
const routeRef = { name: "Home" };

vi.mock("vue-router", () => ({
  useRouter: () => ({ push, back }),
  useRoute: () => routeRef,
}));

beforeEach(() => {
  push.mockClear();
  back.mockClear();
  routeRef.name = "Home";
  closePalette();
  closeSettings();
});

afterEach(() => {
  closePalette();
  closeSettings();
  document.body.style.overflow = "";
});

describe("isPaletteChord", () => {
  it("matches Ctrl+K and Meta+K", () => {
    expect(isPaletteChord({ key: "k", ctrlKey: true })).toBe(true);
    expect(isPaletteChord({ key: "k", metaKey: true })).toBe(true);
  });

  it("ignores a bare k and other modifier combinations", () => {
    expect(!!isPaletteChord({ key: "k" })).toBe(false);
    expect(!!isPaletteChord({ key: "j", ctrlKey: true })).toBe(false);
    expect(!!isPaletteChord({ key: "k", altKey: true })).toBe(false);
  });
});

describe("command palette", () => {
  it("renders nothing while closed", () => {
    const wrapper = mount(CommandPalette);
    expect(wrapper.find(".palette-overlay").exists()).toBe(false);
    wrapper.unmount();
  });

  it("opens on Ctrl+K and closes on a second press", async () => {
    const wrapper = mount(CommandPalette);

    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", ctrlKey: true }),
    );
    await wrapper.vm.$nextTick();
    expect(paletteOpen.value).toBe(true);
    expect(wrapper.find(".palette-overlay").exists()).toBe(true);

    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", ctrlKey: true }),
    );
    await wrapper.vm.$nextTick();
    expect(paletteOpen.value).toBe(false);

    wrapper.unmount();
  });

  it("closes on Escape", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    await wrapper.find("input").trigger("keydown", { key: "Escape" });
    expect(paletteOpen.value).toBe(false);

    wrapper.unmount();
  });

  it("marks the first option selected and moves with ArrowDown", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    const options = wrapper.findAll(".palette-option");
    expect(options.length).toBeGreaterThan(1);
    expect(options[0].attributes("aria-selected")).toBe("true");

    await wrapper.find("input").trigger("keydown", { key: "ArrowDown" });
    const afterDown = wrapper.findAll(".palette-option");
    expect(afterDown[0].attributes("aria-selected")).toBe("false");
    expect(afterDown[1].attributes("aria-selected")).toBe("true");

    wrapper.unmount();
  });

  it("wraps selection backwards with ArrowUp", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    await wrapper.find("input").trigger("keydown", { key: "ArrowUp" });
    const options = wrapper.findAll(".palette-option");
    expect(options[options.length - 1].attributes("aria-selected")).toBe("true");

    wrapper.unmount();
  });

  it("filters by subsequence and navigates on Enter", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    await wrapper.find("input").setValue("go to start");
    const options = wrapper.findAll(".palette-option");
    expect(options).toHaveLength(1);
    expect(options[0].text()).toContain("Go to start");

    await wrapper.find("input").trigger("keydown", { key: "Enter" });
    expect(push).toHaveBeenCalledWith({ name: "Home" });
    expect(paletteOpen.value).toBe(false);

    wrapper.unmount();
  });

  it("opens the settings sheet from the settings command", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    await wrapper.find("input").setValue("settings");
    const options = wrapper.findAll(".palette-option");
    expect(options).toHaveLength(1);

    await options[0].trigger("click");
    expect(settingsOpen.value).toBe(true);
    expect(paletteOpen.value).toBe(false);

    wrapper.unmount();
  });

  it("shows an empty state when nothing matches", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    await wrapper.find("input").setValue("zzzzqqq");
    expect(wrapper.findAll(".palette-option")).toHaveLength(0);
    expect(wrapper.find(".palette-results").exists()).toBe(false);

    wrapper.unmount();
  });

  it("hides route-dependent commands outside their route", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    const onHome = wrapper.findAll(".palette-option").map((o) => o.text());
    expect(onHome.join(" ")).not.toContain("Back to the run");

    wrapper.unmount();
  });

  it("exposes the back command on the report route", async () => {
    routeRef.name = "Report";
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    const labels = wrapper.findAll(".palette-option").map((o) => o.text());
    expect(labels.join(" ")).toContain("Back to the run");

    wrapper.unmount();
  });

  it("restores body overflow and drops its listener on unmount", async () => {
    const wrapper = mount(CommandPalette);
    openPalette();
    await wrapper.vm.$nextTick();

    wrapper.unmount();
    closePalette();

    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", ctrlKey: true }),
    );
    expect(paletteOpen.value).toBe(false);
    expect(document.body.style.overflow).toBe("");
  });
});

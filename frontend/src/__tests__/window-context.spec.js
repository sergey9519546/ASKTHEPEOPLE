// @vitest-environment jsdom

import { defineComponent, h, provide } from "vue";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { useWindowRoute, windowContextKey } from "../composables/useWindowContext.js";

vi.mock("vue-router", () => ({
  useRoute: () => ({ name: "Home", params: { a: "1" }, query: {} }),
}));

const Probe = defineComponent({
  setup() {
    const route = useWindowRoute();
    return () => h("span", {}, JSON.stringify(route.value));
  },
});

describe("useWindowRoute", () => {
  it("falls back to the global route without a window context", () => {
    const wrapper = mount(Probe);

    expect(JSON.parse(wrapper.text())).toEqual({
      name: "Home",
      params: { a: "1" },
      query: {},
    });
  });

  it("prefers the injected window context when a window provides one", () => {
    const Host = defineComponent({
      setup() {
        provide(windowContextKey, {
          name: "Report",
          params: { reportId: "r-9" },
          query: {},
        });
        return () => h(Probe);
      },
    });

    const wrapper = mount(Host);

    expect(JSON.parse(wrapper.text())).toEqual({
      name: "Report",
      params: { reportId: "r-9" },
      query: {},
    });
  });
});

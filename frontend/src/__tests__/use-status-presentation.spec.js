import { describe, it, expect } from "vitest";
import { ref, computed } from "vue";
import {
  normalizeStatus,
  useStatusPresentation,
} from "../composables/useStatusPresentation.js";

describe("normalizeStatus", () => {
  it("returns status unchanged when no options given", () => {
    expect(normalizeStatus("pending")).toBe("pending");
    expect(normalizeStatus("completed")).toBe("completed");
  });

  it("remaps status via remap option", () => {
    expect(normalizeStatus("failed", { remap: { failed: "error" } })).toBe("error");
    expect(normalizeStatus("completed", { remap: { failed: "error" } })).toBe("completed");
  });

  it("whitelists via allowed option and uses fallback", () => {
    expect(
      normalizeStatus("processing", {
        allowed: ["processing", "completed"],
        fallback: "unknown",
      }),
    ).toBe("processing");
    expect(
      normalizeStatus("failed", {
        allowed: ["processing", "completed"],
        fallback: "unknown",
      }),
    ).toBe("unknown");
  });

  it("applies remap before allowed check", () => {
    expect(
      normalizeStatus("failed", {
        remap: { failed: "error" },
        allowed: ["processing", "error"],
        fallback: "unknown",
      }),
    ).toBe("error");
  });
});

describe("useStatusPresentation", () => {
  it("returns label from labels map", () => {
    const status = ref("processing");
    const { label } = useStatusPresentation(status, {
      labels: { processing: "Loading…", completed: "Done" },
    });
    expect(label.value).toBe("Loading…");
  });

  it("reacts to status ref changes", () => {
    const status = ref("processing");
    const { label } = useStatusPresentation(status, {
      labels: { processing: "Loading…", completed: "Done" },
    });
    expect(label.value).toBe("Loading…");
    status.value = "completed";
    expect(label.value).toBe("Done");
  });

  it("uses string fallback for unmapped status", () => {
    const status = ref("unknown");
    const { label } = useStatusPresentation(status, {
      labels: { processing: "Loading…" },
      fallback: "Unknown State",
    });
    expect(label.value).toBe("Unknown State");
  });

  it("uses function fallback for unmapped status", () => {
    const status = ref("pending");
    const { label } = useStatusPresentation(status, {
      labels: { processing: "Loading…" },
      fallback: (s) => s.toUpperCase(),
    });
    expect(label.value).toBe("PENDING");
  });

  it("works with computed status", () => {
    const raw = ref("failed");
    const status = computed(() => (raw.value === "failed" ? "error" : raw.value));
    const { label } = useStatusPresentation(status, {
      labels: { error: "Needs Attention" },
    });
    expect(label.value).toBe("Needs Attention");
  });

  it("works with getter function", () => {
    const raw = ref("processing");
    const { label } = useStatusPresentation(() => raw.value, {
      labels: { processing: "Loading…", completed: "Done" },
    });
    expect(label.value).toBe("Loading…");
    raw.value = "completed";
    expect(label.value).toBe("Done");
  });
});

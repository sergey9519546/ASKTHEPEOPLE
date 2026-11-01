import { isReadonly, isRef } from "vue";
import { describe, expect, it } from "vitest";

import { RUN_ACTIVITY_LIMIT, useRunActivity } from "../composables/useRunActivity.js";

const action = (id, round = 1, extra = {}) => ({
  id,
  platform: "twitter",
  round_num: round,
  agent_id: 7,
  agent_name: "Generated profile",
  action_type: "CREATE_POST",
  timestamp: round * 100,
  action_args: { content: `Recorded text ${id ?? "without ID"}` },
  ...extra,
});
const ids = (activity) => activity.records.value.map((record) => record.id);

// Tests exercise only the reader contract; no component, transport, or backend.
describe("useRunActivity", () => {
  it("exposes the exact API with independent reactive state and a computed view", () => {
    const activity = useRunActivity();
    expect(RUN_ACTIVITY_LIMIT).toBe(200);
    expect(Object.keys(activity).sort()).toEqual([
      "records", "displayedRecords", "held", "pendingCount", "pendingOverflow",
      "hasEvicted", "selectedRecord", "mergeActions", "holdView", "showLatest",
      "selectRecord", "clearSelection", "reset",
    ].sort());
    for (const key of ["records", "displayedRecords", "held", "pendingCount",
      "pendingOverflow", "hasEvicted", "selectedRecord"]) {
      expect(isRef(activity[key])).toBe(true);
    }
    expect(isReadonly(activity.displayedRecords)).toBe(true);
    expect(activity.records.value).toEqual([]);
    expect(activity.displayedRecords.value).toBe(activity.records.value);
    expect(activity.selectedRecord.value).toBeNull();
    expect(activity.held.value).toBe(false);
    const other = useRunActivity();
    activity.mergeActions([action(1)]);
    activity.holdView();
    expect(other.records.value).toEqual([]);
    expect(other.held.value).toBe(false);
  });

  it.each([undefined, null, 0, -2, NaN, Infinity, -Infinity, "2", {}, 0.5, 1e30])(
    "uses a finite default cap for invalid limit %s",
    (limit) => {
      const activity = useRunActivity({ limit });
      activity.mergeActions(Array.from({ length: 205 }, (_, i) => action(i, i)));
      expect(activity.records.value).toHaveLength(200);
      expect(ids(activity)[0]).toBe(5);
      expect(activity.hasEvicted.value).toBe(true);
    },
  );

  it("floors fractional limits and supports a one-row buffer", () => {
    const activity = useRunActivity({ limit: 1.9 });
    activity.mergeActions([action(1, 1), action(2, 2)]);
    expect(ids(activity)).toEqual([2]);
  });

  it("orders rounds and timestamps numerically, then breaks ties by admission sequence", () => {
    const activity = useRunActivity();
    activity.mergeActions([
      action("round10", "10"),
      action("late", "2", { timestamp: "10" }),
      action("early", 2, { timestamp: "2" }),
      action("tie", 2, { timestamp: 2 }),
      action("round1", 1),
    ]);
    expect(ids(activity)).toEqual(["round1", "early", "tie", "late", "round10"]);
    const key = activity.records.value[1]._uniqueId;
    activity.mergeActions([action("before", 0)]);
    expect(activity.records.value.find((row) => row.id === "early")._uniqueId).toBe(key);
    expect(activity.records.value[0]._sequence).toBe(6);
    expect(new Set(activity.records.value.map((row) => row._uniqueId)).size).toBe(6);
  });

  it("orders ISO timestamps by their instant and handles unavailable ordering fields", () => {
    const activity = useRunActivity();
    activity.mergeActions([
      action("later", 1, { timestamp: "2026-11-01T08:00:00-05:00" }),
      action("earlier", 1, { timestamp: "2026-11-01T12:00:00Z" }),
      action("missing", undefined, { round_num: undefined, timestamp: undefined }),
      action("invalid", "not a round", { timestamp: "not a timestamp" }),
    ]);
    expect(ids(activity)).toEqual(["missing", "invalid", "earlier", "later"]);
  });

  it("prefers server IDs including 0, scopes IDs by platform, and ignores changed payloads", () => {
    const activity = useRunActivity();
    activity.mergeActions([
      action(0), action("0", 5), action(0, 1, { platform: "reddit" }),
      action("same", 1), action("same", 99),
    ]);
    expect(ids(activity)).toEqual([0, 0, "same"]);
    expect(activity.records.value.every((row) => row._identitySource === "server")).toBe(true);
    expect(activity.records.value[2].round_num).toBe(1);
    expect(activity.records.value.every((row) => row._uniqueId !== String(row.id))).toBe(true);
    activity.mergeActions([action(0, 10)]);
    expect(ids(activity)).toEqual([0, 0, "same"]);
  });

  it.each([undefined, null, "", "   ", false, {}, [], NaN, Infinity])(
    "uses local identity for invalid server ID %s", (id) => {
      const activity = useRunActivity();
      activity.mergeActions([action(id)]);
      expect(activity.records.value[0]._identitySource).toBe("local");
      expect(activity.records.value[0]).not.toHaveProperty("id");
    },
  );

  it("deduplicates no-ID snapshots despite shifted array indexes and public argument key order", () => {
    const activity = useRunActivity();
    const first = action(undefined, "2", {
      action_args: { content: "A", reference: { post_id: 3, platform: "reddit" } },
    });
    const second = action(undefined, 3, { action_args: { content: "B" } });
    activity.mergeActions([first, second]);
    const keys = activity.records.value.map((row) => row._uniqueId);
    activity.mergeActions([
      action("unrelated", 1),
      second,
      { ...first, round_num: 2, action_args: {
        reference: { platform: "reddit", post_id: 3 }, content: "A",
      } },
    ]);
    expect(activity.records.value).toHaveLength(3);
    expect(activity.records.value.slice(1).map((row) => row._uniqueId)).toEqual(keys);
  });

  it("preserves identical occurrences per batch, not batch positions or a global event count", () => {
    const activity = useRunActivity();
    const repeat = action(undefined);
    activity.holdView();
    activity.mergeActions([repeat, action("other"), repeat]);
    expect(activity.records.value.filter((row) => row._identitySource === "local")).toHaveLength(2);
    expect(activity.pendingCount.value).toBe(3);
    const originalKeys = activity.records.value.map((row) => row._uniqueId);
    activity.mergeActions([repeat, repeat, action("other")]);
    expect(activity.records.value.map((row) => row._uniqueId)).toEqual(originalKeys);
    expect(activity.pendingCount.value).toBe(3);
    activity.mergeActions([repeat, repeat, repeat]);
    expect(activity.records.value).toHaveLength(4);
    expect(activity.pendingCount.value).toBe(4);
    // A lone indistinguishable record in a later snapshot matches ordinal zero.
    activity.mergeActions([repeat]);
    expect(activity.records.value).toHaveLength(4);
  });

  it("retains only newest rows and rejects stale replay without pending admissions or eviction", () => {
    const activity = useRunActivity({ limit: 3 });
    activity.mergeActions([action(12, 12), action(10, 10), action(11, 11)]);
    activity.holdView();
    activity.mergeActions([action(1, 1), action(2, 2), action(10, 10)]);
    expect(ids(activity)).toEqual([10, 11, 12]);
    expect(activity.pendingCount.value).toBe(0);
    expect(activity.hasEvicted.value).toBe(false);
    activity.mergeActions([action(15, 15), action(4, 4), action(14, 14), action(13, 13)]);
    expect(ids(activity)).toEqual([13, 14, 15]);
    expect(activity.pendingCount.value).toBe(3);
    expect(activity.pendingOverflow.value).toBe(false);
    expect(activity.hasEvicted.value).toBe(true);
    activity.mergeActions([action(10, 10), action(12, 12)]);
    expect(ids(activity)).toEqual([13, 14, 15]);
    expect(activity.pendingOverflow.value).toBe(false);
  });

  it("does not remember evicted identities forever; equal-time readmissions have fresh local keys", () => {
    const activity = useRunActivity({ limit: 2 });
    activity.mergeActions([action("a"), action("b")]);
    const oldKey = activity.records.value[0]._uniqueId;
    activity.holdView();
    activity.mergeActions([action("c")]);
    activity.mergeActions([action("a")]);
    expect(ids(activity)).toEqual(["c", "a"]);
    expect(activity.records.value[1]._uniqueId).not.toBe(oldKey);
    expect(activity.records.value[1]._sequence).toBe(4);
    expect(activity.pendingCount.value).toBe(2);
    activity.mergeActions([action("b")]);
    expect(activity.pendingOverflow.value).toBe(true);
  });

  it("remains bounded over many batches, retaining increasing sequences and sticky eviction", () => {
    const activity = useRunActivity({ limit: 3 });
    activity.holdView();
    for (let i = 0; i < 100; i += 1) {
      activity.mergeActions([action(i, i)]);
      expect(activity.records.value.length).toBeLessThanOrEqual(3);
      expect(activity.pendingCount.value).toBeLessThanOrEqual(3);
    }
    expect(ids(activity)).toEqual([97, 98, 99]);
    expect(activity.records.value.map((row) => row._sequence)).toEqual([98, 99, 100]);
    expect(activity.pendingOverflow.value).toBe(true);
    activity.showLatest();
    expect(activity.hasEvicted.value).toBe(true);
  });

  it("projects only public fields recursively and leaves HTML as literal data", () => {
    const activity = useRunActivity();
    const html = '<img src=x onerror="alert(1)"><b>Recorded text</b>';
    activity.mergeActions([action(1, 1, {
      reasoning: "private", prompt: "private", internal: { secret: "private" },
      _uniqueId: "forged", _sequence: -99, _identitySource: "forged",
      action_args: {
        content: html, text: "public", post_id: 0, tweet_id: "tweet-12",
        target_agent_id: 42, target_user_name: "Profile",
        reasoning: "private", prompt: "private", internal: "private",
        references: [{ post_id: 12, content: { text: "nested", prompt: "private" },
          tweet_id: "nested-tweet", target_agent_id: 43, internal: "private",
          reference: { comment_id: 4, reasoning: "private" } }],
      },
    })]);
    const row = activity.records.value[0];
    expect(Object.keys(row).sort()).toEqual([
      "id", "platform", "round_num", "agent_id", "agent_name", "action_type",
      "timestamp", "action_args", "_uniqueId", "_sequence", "_identitySource",
    ].sort());
    expect(row.action_args).toEqual({
      content: html, text: "public", post_id: 0, tweet_id: "tweet-12",
      target_agent_id: 42, target_user_name: "Profile",
      references: [{ post_id: 12, content: { text: "nested" },
        tweet_id: "nested-tweet", target_agent_id: 43, reference: { comment_id: 4 } }],
    });
    expect(row._sequence).toBe(1);
    expect(row._identitySource).toBe("server");
    expect(JSON.stringify(row)).not.toContain("private");
    activity.selectRecord(row._uniqueId);
    expect(activity.selectedRecord.value.action_args).toEqual(row.action_args);
    expect(JSON.stringify(activity.selectedRecord.value)).not.toContain("private");
  });

  it("ignores private-field differences when fingerprinting local records", () => {
    const activity = useRunActivity();
    activity.mergeActions([action(undefined, 1, { prompt: "one" })]);
    activity.mergeActions([action(undefined, 1, {
      prompt: "two", action_args: { content: "Recorded text without ID", reasoning: "secret" },
    })]);
    expect(activity.records.value).toHaveLength(1);
  });

  it("clones incoming, held and selected nested public objects independently", () => {
    const activity = useRunActivity();
    const incoming = action(1, 1, {
      action_args: { references: [{ content: { text: "original" }, post_id: 4 }] },
    });
    activity.mergeActions([incoming]);
    const key = activity.records.value[0]._uniqueId;
    activity.holdView();
    expect(activity.selectRecord(key)).toBe(true);
    incoming.action_args.references[0].content.text = "input mutation";
    expect(activity.records.value[0].action_args.references[0].content.text).toBe("original");
    activity.records.value[0].action_args.references[0].content.text = "live mutation";
    expect(activity.displayedRecords.value[0].action_args.references[0].content.text).toBe("original");
    expect(activity.selectedRecord.value.action_args.references[0].content.text).toBe("original");
    activity.selectedRecord.value.action_args.references[0].content.text = "selection mutation";
    expect(activity.displayedRecords.value[0].action_args.references[0].content.text).toBe("original");
  });

  it("holds exact sorted rows idempotently while live records and capped pending state advance", () => {
    const activity = useRunActivity({ limit: 2 });
    activity.mergeActions([action(2, 2), action(1, 1)]);
    activity.holdView();
    const snapshot = JSON.parse(JSON.stringify(activity.displayedRecords.value));
    activity.mergeActions([action(3, 3), action(4, 4)]);
    expect(activity.pendingCount.value).toBe(2);
    expect(activity.pendingOverflow.value).toBe(false);
    activity.holdView();
    activity.mergeActions([action(5, 5)]);
    expect(activity.pendingCount.value).toBe(2);
    expect(activity.pendingOverflow.value).toBe(true);
    expect(activity.displayedRecords.value).toEqual(snapshot);
    expect(ids(activity)).toEqual([4, 5]);
    activity.showLatest();
    expect(activity.displayedRecords.value).toBe(activity.records.value);
    expect(activity.held.value).toBe(false);
    expect(activity.pendingCount.value).toBe(0);
    expect(activity.pendingOverflow.value).toBe(false);
    expect(activity.hasEvicted.value).toBe(true);
    activity.holdView();
    activity.mergeActions([action(5, 5)]);
    expect(activity.pendingCount.value).toBe(0);
  });

  it("selects only displayed rows and preserves the cloned selection after eviction and resume", () => {
    const activity = useRunActivity({ limit: 1 });
    activity.mergeActions([action(1, 1)]);
    const oldKey = activity.records.value[0]._uniqueId;
    expect(activity.selectRecord(oldKey)).toBe(true);
    const selected = activity.selectedRecord.value;
    activity.holdView();
    activity.mergeActions([action(2, 2)]);
    expect(activity.selectedRecord.value).toBe(selected);
    expect(activity.selectRecord(activity.records.value[0]._uniqueId)).toBe(false);
    expect(activity.selectRecord(oldKey)).toBe(true);
    activity.showLatest();
    expect(activity.selectedRecord.value.id).toBe(1);
    expect(activity.selectRecord(oldKey)).toBe(false);
    expect(activity.selectRecord("missing")).toBe(false);
    expect(activity.selectedRecord.value.id).toBe(1);
    activity.clearSelection();
    expect(activity.selectedRecord.value).toBeNull();
    expect(activity.selectRecord(activity.records.value[0]._uniqueId)).toBe(true);
  });

  it("safely skips invalid batches/items and strips cycles, accessors and unsupported data", () => {
    const activity = useRunActivity();
    for (const batch of [undefined, null, {}, "text", 12]) activity.mergeActions(batch);
    const cyclic = { content: "public" };
    cyclic.reference = cyclic;
    const accessor = {};
    Object.defineProperty(accessor, "id", { get: () => { throw new Error("must not run"); } });
    const badProxy = new Proxy({}, { getPrototypeOf() { throw new Error("invalid"); } });
    expect(() => activity.mergeActions([
      null, undefined, false, 123, "text", [], {}, new Date(), { prompt: "private" },
      accessor, badProxy,
      action(1, 1, { action_args: cyclic }),
      action(2, 2, { action_args: { content: () => "bad", references: [NaN, Symbol(), { post_id: 0 }] } }),
    ])).not.toThrow();
    expect(ids(activity)).toEqual([1, 2]);
    expect(activity.records.value[0].action_args).toEqual({ content: "public" });
    expect(activity.records.value[1].action_args).toEqual({ references: [{ post_id: 0 }] });
  });

  it("reset clears live/held records, selection, dedup state, sequence and all flags", () => {
    const activity = useRunActivity({ limit: 1 });
    activity.mergeActions([action(1, 1)]);
    activity.selectRecord(activity.records.value[0]._uniqueId);
    activity.holdView();
    activity.mergeActions([action(2, 2), action(3, 3)]);
    activity.reset();
    expect(activity.records.value).toEqual([]);
    expect(activity.displayedRecords.value).toEqual([]);
    expect(activity.selectedRecord.value).toBeNull();
    expect(activity.pendingCount.value).toBe(0);
    for (const key of ["held", "pendingOverflow", "hasEvicted"]) {
      expect(activity[key].value).toBe(false);
    }
    activity.mergeActions([action(1, 1)]);
    expect(ids(activity)).toEqual([1]);
    expect(activity.records.value[0]._sequence).toBe(1);
    activity.showLatest();
    activity.showLatest();
    expect(activity.records.value).toHaveLength(1);
  });
});

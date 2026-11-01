import { computed, ref } from "vue";

export const RUN_ACTIVITY_LIMIT = 200;

// Public content and explicit references only, at EVERY object depth. Do not
// retain arbitrary provider arguments, prompts, reasoning, or internal metadata.
const PUBLIC_ARGUMENT_KEYS = [
  "content", "text", "title", "quote_content", "original_content", "post_content",
  "comment_content", "query", "keyword", "keywords", "id", "platform", "post_id",
  "comment_id", "parent_id", "parent_post_id", "parent_comment_id", "original_post_id",
  "target_user_id", "target_user_name", "post_author_id", "post_author_name",
  "user_id", "agent_id", "tweet_id", "target_agent_id", "reference", "references", "url",
];
const PUBLIC_FIELDS = [
  "id", "platform", "round_num", "agent_id", "agent_name", "action_type", "timestamp",
];

const isObject = (value) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
};

// Avoid invoking accessors supplied by malformed, non-JSON callers.
const ownValue = (object, key) => Object.getOwnPropertyDescriptor(object, key)?.value;
const isIdentifier = (value) =>
  (typeof value === "string" && value.trim() !== "") ||
  (typeof value === "number" && Number.isFinite(value));

function publicArguments(value, ancestors = new WeakSet(), depth = 0) {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") return Number.isFinite(value) ? value : undefined;
  if (!value || typeof value !== "object" || depth >= 20 || ancestors.has(value)) {
    return undefined;
  }
  if (!Array.isArray(value) && !isObject(value)) return undefined;

  ancestors.add(value);
  const result = Array.isArray(value) ? [] : {};
  const keys = Array.isArray(value)
    ? Array.from({ length: value.length }, (_, index) => String(index))
    : PUBLIC_ARGUMENT_KEYS;
  for (const key of keys) {
    const child = publicArguments(ownValue(value, key), ancestors, depth + 1);
    if (child !== undefined) {
      if (Array.isArray(result)) result.push(child);
      else result[key] = child;
    }
  }
  ancestors.delete(value);
  return result;
}

function projectAction(action) {
  if (!isObject(action)) return null;
  const record = {};
  for (const key of PUBLIC_FIELDS) {
    const value = ownValue(action, key);
    if (!isIdentifier(value)) continue;
    if (key === "round_num") {
      const round = Number(value);
      if (Number.isFinite(round)) record[key] = round;
    } else if (["platform", "agent_name", "action_type"].includes(key)) {
      if (typeof value === "string") record[key] = value.trim();
    } else {
      record[key] = value;
    }
  }
  const args = ownValue(action, "action_args");
  record.action_args = isObject(args) ? publicArguments(args) : {};
  if (Object.keys(record).length === 1 && !Object.keys(record.action_args).length) {
    return null;
  }
  return record;
}

function timestampOrder(value) {
  if (value === undefined) return 0;
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export const compareRunActivityRecords = (left, right) =>
  (left?.round_num ?? 0) - (right?.round_num ?? 0) ||
  timestampOrder(left?.timestamp) - timestampOrder(right?.timestamp) ||
  (left?._sequence ?? 0) - (right?._sequence ?? 0);

// Projection creates JSON-only data with deterministic object key ordering.
// This copy retains nested public arguments without parsing/rendering HTML.
const cloneRecord = (record) => JSON.parse(JSON.stringify(record));

/**
 * Bounded recent activity, NOT a complete history or a canonical identity store.
 * Server IDs are nonblank strings or finite numbers (including 0), scoped to
 * platform; numeric/string representations of the same ID share an identity.
 * Without an ID, normalized public fields + per-batch occurrence ordinal are a
 * cross-snapshot HEURISTIC: indistinguishable repeats cannot be resolved across
 * snapshots. Only retained identities are remembered; equal-time replays after
 * eviction can be accepted again. _uniqueId is solely a local UI key.
 *
 * pendingCount counts accepted display entries while held, not globally unique
 * events or the size of complete history. It saturates at the configured cap;
 * pendingOverflow records further admissions, and hasEvicted is local/sticky.
 * Limits are positive safe integers (fractions floored); invalid limits use 200.
 * The cap bounds record count, not string length, array length, or payload bytes.
 * Callers own connection/terminal state and should treat exposed records as read-only.
 */
export function useRunActivity({ limit = RUN_ACTIVITY_LIMIT } = {}) {
  const floored = typeof limit === "number" ? Math.floor(limit) : NaN;
  const cap = Number.isSafeInteger(floored) && floored > 0 ? floored : RUN_ACTIVITY_LIMIT;
  const records = ref([]);
  const held = ref(false);
  const pendingCount = ref(0);
  const pendingOverflow = ref(false);
  const hasEvicted = ref(false);
  const selectedRecord = ref(null);
  const heldRecords = ref([]);
  const displayedRecords = computed(() => held.value ? heldRecords.value : records.value);

  // No all-time IDs, history, or pending event collection. This map never grows
  // beyond cap; the held snapshot and selected copy are independently bounded.
  const retained = new Map();
  let sequence = 0;

  function mergeActions(batch) {
    if (!Array.isArray(batch)) return;
    // These scratch structures live for this call only, never across snapshots.
    const occurrences = new Map();
    const candidates = [];
    for (const action of batch) {
      try {
        const record = projectAction(action);
        if (!record) continue;
        const server = isIdentifier(record.id);
        let identity;
        if (server) {
          identity = JSON.stringify(["server", record.platform ?? "", String(record.id)]);
        } else {
          const fingerprint = JSON.stringify(record);
          const ordinal = occurrences.get(fingerprint) ?? 0;
          occurrences.set(fingerprint, ordinal + 1);
          identity = JSON.stringify(["local", fingerprint, ordinal]);
        }
        candidates.push({ identity, record, source: server ? "server" : "local" });
      } catch {
        // A malformed item must not prevent other public records being read.
      }
    }

    // Process oldest first, independently of batch order. Older-than-window
    // history is rejected rather than allowed to displace newer retained rows.
    candidates.sort((left, right) =>
      compareRunActivityRecords(left.record, right.record),
    );
    const next = [...records.value];
    for (const { identity, record, source } of candidates) {
      if (retained.has(identity)) continue;
      record._sequence = sequence + 1;
      if (
        next.length === cap &&
        compareRunActivityRecords(record, next[0]) < 0
      ) {
        continue;
      }

      sequence += 1;
      record._uniqueId = `activity-${sequence}`;
      record._identitySource = source;
      // Evict before inserting so identity bookkeeping stays within the cap.
      if (next.length === cap) {
        const evicted = next.shift();
        for (const [key, value] of retained) {
          if (value._uniqueId === evicted._uniqueId) {
            retained.delete(key);
            break;
          }
        }
        hasEvicted.value = true;
      }
      retained.set(identity, record);
      next.push(record);
      next.sort(compareRunActivityRecords);
      if (held.value) {
        if (pendingCount.value < cap) pendingCount.value += 1;
        else pendingOverflow.value = true;
      }
    }
    records.value = next;
  }

  function holdView() {
    if (held.value) return;
    heldRecords.value = records.value.map(cloneRecord);
    held.value = true;
  }

  function showLatest() {
    held.value = false;
    heldRecords.value = [];
    pendingCount.value = 0;
    pendingOverflow.value = false;
  }

  function selectRecord(displayKey) {
    const record = displayedRecords.value.find((item) => item._uniqueId === displayKey);
    if (!record) return false;
    selectedRecord.value = cloneRecord(record);
    return true;
  }

  function clearSelection() {
    selectedRecord.value = null;
  }

  function reset() {
    records.value = [];
    heldRecords.value = [];
    held.value = false;
    pendingCount.value = 0;
    pendingOverflow.value = false;
    hasEvicted.value = false;
    selectedRecord.value = null;
    retained.clear();
    sequence = 0;
  }

  return {
    records, displayedRecords, held, pendingCount, pendingOverflow, hasEvicted,
    selectedRecord, mergeActions, holdView, showLatest, selectRecord, clearSelection, reset,
  };
}

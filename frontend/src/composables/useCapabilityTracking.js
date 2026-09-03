/**
 * Capability Tracking
 *
 * Persists how much experience a user has with the workflow and derives their
 * capability level. The guided context uses this to decide how much to explain
 * and reveal. Capability is inferred from completion history, never asked.
 *
 * Storage degrades gracefully: a blocked or absent localStorage falls back to
 * an in-memory session, mirroring `useWorkspaceState.js`.
 */

import { onMounted } from "vue";
import { CAPABILITY_LEVELS, useGuidedContext } from "./useGuidedContext";

const STORAGE_KEY = "askthepeople_user_capability_v1";

const DEFAULT_RECORD = {
  completedRuns: 0,
  lastRunDate: null,
  explicitExpertMode: false,
  dismissedHelp: [],
};

// In-memory fallback when storage is unavailable, shared across callers.
let memoryRecord = { ...DEFAULT_RECORD };

function storage() {
  if (
    typeof window === "undefined" ||
    !window.localStorage ||
    typeof window.localStorage.getItem !== "function" ||
    typeof window.localStorage.setItem !== "function"
  ) {
    return null;
  }
  return window.localStorage;
}

function loadRecord() {
  const store = storage();
  if (!store) return { ...memoryRecord };
  try {
    const raw = store.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_RECORD };
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return { ...DEFAULT_RECORD, ...parsed };
    }
  } catch (err) {
    if (import.meta.env?.DEV) {
      console.warn("Failed to load capability record:", err);
    }
  }
  return { ...DEFAULT_RECORD };
}

function persist(record) {
  memoryRecord = { ...record };
  const store = storage();
  if (!store) return;
  try {
    store.setItem(STORAGE_KEY, JSON.stringify(record));
  } catch (err) {
    if (import.meta.env?.DEV) {
      console.warn("Failed to save capability record:", err);
    }
  }
}

/** Map a persisted record to a capability level. */
export function deriveCapability(record = loadRecord()) {
  if (record.explicitExpertMode) return CAPABILITY_LEVELS.EXPERT;
  const runs = Number(record.completedRuns) || 0;
  if (runs >= 10) return CAPABILITY_LEVELS.EXPERT;
  if (runs >= 4) return CAPABILITY_LEVELS.PRACTICED;
  if (runs >= 1) return CAPABILITY_LEVELS.LEARNING;
  return CAPABILITY_LEVELS.FIRST_USE;
}

export function useCapabilityTracking() {
  const { updateCapability } = useGuidedContext();

  /** Read the record and push the derived level into the guided context. */
  const syncCapability = () => {
    const record = loadRecord();
    const level = deriveCapability(record);
    updateCapability(level);
    return level;
  };

  const trackRunCompletion = () => {
    const record = loadRecord();
    record.completedRuns = (Number(record.completedRuns) || 0) + 1;
    record.lastRunDate = new Date().toISOString();
    persist(record);
    return syncCapability();
  };

  const setExpertMode = (enabled) => {
    const record = loadRecord();
    record.explicitExpertMode = Boolean(enabled);
    persist(record);
    return syncCapability();
  };

  const rememberDismissedHelp = (helpId) => {
    const record = loadRecord();
    if (!record.dismissedHelp.includes(helpId)) {
      record.dismissedHelp = [...record.dismissedHelp, helpId];
      persist(record);
    }
  };

  const isHelpDismissed = (helpId) =>
    loadRecord().dismissedHelp.includes(helpId);

  const resetHelp = () => {
    const record = loadRecord();
    record.dismissedHelp = [];
    persist(record);
  };

  /** Test-only: wipe the persisted record. */
  const resetCapabilityRecord = () => {
    memoryRecord = { ...DEFAULT_RECORD };
    const store = storage();
    if (store) {
      try {
        store.removeItem(STORAGE_KEY);
      } catch {
        /* best-effort */
      }
    }
    syncCapability();
  };

  // Sync on mount so a returning user immediately gets the right level.
  onMounted(syncCapability);

  return {
    syncCapability,
    trackRunCompletion,
    setExpertMode,
    rememberDismissedHelp,
    isHelpDismissed,
    resetHelp,
    resetCapabilityRecord,
    deriveCapability,
    STORAGE_KEY,
  };
}

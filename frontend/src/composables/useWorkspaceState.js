import { ref } from "vue";

const STORAGE_KEY = "askthepeople_workspace_session_v1";

const DEFAULT_STATE = {
  simulationRequirement: "",
  projectName: "",
  additionalContext: "",
  lastActiveStep: 1,
  // Current decision/run coordinates, reported by each journey window as the
  // user progresses. The desktop dock and masthead read these to decide which
  // steps are launchable and what decision the workspace is centered on.
  projectId: "",
  simulationId: "",
  reportId: "",
  maxRounds: null,
  savedAt: null,
};

export const workspaceState = ref({ ...DEFAULT_STATE });

function safeParse(raw) {
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

/** A blocked or absent storage API degrades to a session-only workspace. */
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

export function loadSavedState() {
  const store = storage();
  if (!store) return;
  try {
    const parsed = safeParse(store.getItem(STORAGE_KEY));
    if (parsed) {
      workspaceState.value = { ...DEFAULT_STATE, ...parsed };
    }
  } catch (err) {
    if (import.meta.env.DEV) {
      console.warn("Failed to load saved workspace session:", err);
    }
  }
}

export function saveState(updates = {}) {
  workspaceState.value = {
    ...workspaceState.value,
    ...updates,
    savedAt: new Date().toISOString(),
  };
  const store = storage();
  if (!store) return;
  try {
    store.setItem(STORAGE_KEY, JSON.stringify(workspaceState.value));
  } catch (err) {
    if (import.meta.env.DEV) {
      console.warn("Failed to save workspace session:", err);
    }
  }
}

/**
 * Record where in the journey the workspace currently is. Every provided key
 * is authoritative for its own window (a null round count is meaningful), so
 * only `undefined` ("not reported") is skipped.
 */
export function setContext(updates = {}) {
  const next = { ...workspaceState.value };
  for (const [key, value] of Object.entries(updates)) {
    if (value !== undefined) {
      next[key] = value;
    }
  }
  saveState(next);
}

export function clearState() {
  workspaceState.value = { ...DEFAULT_STATE };
  const store = storage();
  if (!store) return;
  try {
    store.removeItem(STORAGE_KEY);
  } catch (err) {
    if (import.meta.env.DEV) {
      console.warn("Failed to clear workspace session:", err);
    }
  }
}

export function useWorkspaceState() {
  return {
    workspaceState,
    loadSavedState,
    saveState,
    setContext,
    clearState,
  };
}

export { STORAGE_KEY };

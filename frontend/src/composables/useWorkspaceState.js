import { ref, watch } from "vue";

const STORAGE_KEY = "askthepeople_workspace_session_v1";

const workspaceState = ref({
  simulationRequirement: "",
  projectName: "",
  additionalContext: "",
  lastActiveStep: 1,
  savedAt: null,
});

export function useWorkspaceState() {
  const loadSavedState = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") {
          workspaceState.value = {
            ...workspaceState.value,
            ...parsed,
          };
        }
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn("Failed to load saved workspace session:", err);
      }
    }
  };

  const saveState = (updates = {}) => {
    try {
      workspaceState.value = {
        ...workspaceState.value,
        ...updates,
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(workspaceState.value));
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn("Failed to save workspace session:", err);
      }
    }
  };

  const clearState = () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      workspaceState.value = {
        simulationRequirement: "",
        projectName: "",
        additionalContext: "",
        lastActiveStep: 1,
        savedAt: null,
      };
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn("Failed to clear workspace session:", err);
      }
    }
  };

  return {
    workspaceState,
    loadSavedState,
    saveState,
    clearState,
  };
}

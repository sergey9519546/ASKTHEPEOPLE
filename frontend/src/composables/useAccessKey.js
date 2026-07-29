import { ref } from "vue";

const STORAGE_KEY = "atp_access_key";

function readSessionKey() {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export const accessRequired = ref(false);
export const accessMessage = ref("");

export function getAccessKey() {
  return readSessionKey();
}

export function saveAccessKey(value) {
  const key = String(value || "").trim();
  if (!key) return false;

  try {
    window.sessionStorage.setItem(STORAGE_KEY, key);
  } catch {
    return false;
  }

  accessRequired.value = false;
  accessMessage.value = "";
  window.dispatchEvent(new CustomEvent("atp:access-key-updated"));
  return true;
}

export function clearAccessKey() {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // A blocked storage API already behaves like an empty session.
  }
  window.dispatchEvent(new CustomEvent("atp:access-key-updated"));
}

export function requireAccess(message = "Enter the access key for this deployment.") {
  accessMessage.value = message;
  accessRequired.value = true;
}


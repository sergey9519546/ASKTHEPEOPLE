import { ref } from "vue";

/**
 * Shared UI state for the command palette.
 *
 * Module-level refs follow the same convention as utils/toast.js: one
 * instance per app, imported directly by whichever component needs it.
 * The palette lives in App.vue but its commands act on state owned by
 * route views, so that state has to be reachable from both sides.
 */

export const paletteOpen = ref(false);

/**
 * Settings visibility. Home.vue renders SettingsModal, but the palette
 * needs to open it too, so the flag cannot stay local to Home.
 */
export const settingsOpen = ref(false);

export function openPalette() {
  paletteOpen.value = true;
}

export function closePalette() {
  paletteOpen.value = false;
}

export function togglePalette() {
  paletteOpen.value = !paletteOpen.value;
}

export function openSettings() {
  settingsOpen.value = true;
}

export function closeSettings() {
  settingsOpen.value = false;
}

/**
 * True when the event is the platform's palette chord: Cmd+K on Apple
 * hardware, Ctrl+K elsewhere. Accepting both on either platform would
 * swallow Ctrl+K on macOS, which the browser maps to other behavior.
 */
export function isPaletteChord(event) {
  if (event.key !== "k" && event.key !== "K") return false;
  return event.metaKey || event.ctrlKey;
}

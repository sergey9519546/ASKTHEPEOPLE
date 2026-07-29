import { ref } from 'vue'

// Top-level shared reactive crash flag. Created once at module load so every
// importer (main.js errorHandler + App.vue) observes the same ref instance.
export const hasCrashed = ref(false)

export function useCrashState() {
  return { hasCrashed }
}

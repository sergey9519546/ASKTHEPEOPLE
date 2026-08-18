import { computed, inject } from "vue";
import { useRoute } from "vue-router";

/**
 * Each desktop window renders a journey view directly, so the singleton
 * `useRoute()` no longer describes which decision/run that specific window is
 * showing. The shell provides a per-window route context through this key;
 * `useWindowRoute()` returns the window's own route when one exists and falls
 * back to the global route otherwise (router-view, or a bare component mount
 * in tests), so views keep working in every host.
 */
export const windowContextKey = Symbol("desktop-window-context");

export function useWindowRoute() {
  const windowContext = inject(windowContextKey, null);
  const route = useRoute();

  return computed(() => {
    if (windowContext) {
      return {
        name: windowContext.name,
        params: windowContext.params || {},
        query: windowContext.query || {},
      };
    }
    return route;
  });
}

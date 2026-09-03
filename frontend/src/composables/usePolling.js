/**
 * usePolling
 *
 * One deep module for the timer/immediate-fire/timeout/teardown lifecycle that
 * was hand-rolled at nine call sites across the views and step components. Each
 * copy re-declared `let xTimer = null`, a start/stop pair with the
 * `if (!timer) return; clearInterval; timer = null` guard, and an `onUnmounted`
 * cleanup. The only real per-site variation is the interval, the poll function,
 * and an optional timeout — so those are the interface; everything else is
 * absorbed here.
 *
 * The caller keeps its own success/error branching inside `pollFn`; this module
 * only guarantees the loop runs, fires immediately, respects a timeout, and is
 * always torn down when the component unmounts.
 *
 * Usage:
 *   const poll = usePolling({ intervalMs: 2000 });
 *   poll.start(() => pollTaskStatus(taskId));   // fires immediately, then every 2s
 *   poll.stop();                                // idempotent
 *
 *   // with a timeout:
 *   const poll = usePolling({
 *     intervalMs: 3000,
 *     timeoutMs: 5 * 60 * 1000,
 *     onTimeout: () => { error.value = "Timed out."; },
 *   });
 */

import { getCurrentInstance, onUnmounted, ref } from "vue";

export function usePolling(options = {}) {
  const {
    intervalMs = 2000,
    timeoutMs = null,
    immediate = true,
    onTimeout = null,
  } = options;

  const isPolling = ref(false);

  let timer = null;
  let startedAt = 0;
  // The last poll function handed to start(); lets a bare start() restart the
  // same loop (used by recoverable-error retry actions).
  let currentPollFn = null;

  const stop = () => {
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
    isPolling.value = false;
  };

  const runOnce = async () => {
    if (timeoutMs !== null && Date.now() - startedAt > timeoutMs) {
      stop();
      if (typeof onTimeout === "function") onTimeout();
      return;
    }
    if (typeof currentPollFn === "function") {
      await currentPollFn();
    }
  };

  /**
   * Begin (or restart) the loop. Passing a new pollFn replaces the previous
   * one; omitting it reuses the last, so `() => poll.start()` is a valid retry.
   */
  const start = (pollFn) => {
    if (pollFn !== undefined) currentPollFn = pollFn;
    if (typeof currentPollFn !== "function") return;

    stop();
    startedAt = Date.now();
    isPolling.value = true;

    if (immediate) runOnce();
    timer = setInterval(runOnce, intervalMs);
  };

  // A poller mounted inside a component tears itself down automatically. Guarded
  // so the composable is still usable outside a component (e.g. in tests).
  if (getCurrentInstance()) {
    onUnmounted(stop);
  }

  return { start, stop, isPolling };
}

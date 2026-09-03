// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { usePolling } from "../composables/usePolling.js";

describe("usePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("fires immediately then on each interval", () => {
    const fn = vi.fn();
    const poll = usePolling({ intervalMs: 1000 });
    poll.start(fn);
    expect(fn).toHaveBeenCalledTimes(1); // immediate
    vi.advanceTimersByTime(3000);
    expect(fn).toHaveBeenCalledTimes(4);
    poll.stop();
  });

  it("skips the immediate fire when immediate=false", () => {
    const fn = vi.fn();
    const poll = usePolling({ intervalMs: 1000, immediate: false });
    poll.start(fn);
    expect(fn).toHaveBeenCalledTimes(0);
    vi.advanceTimersByTime(2000);
    expect(fn).toHaveBeenCalledTimes(2);
    poll.stop();
  });

  it("stop() halts the loop and is idempotent", () => {
    const fn = vi.fn();
    const poll = usePolling({ intervalMs: 1000 });
    poll.start(fn);
    poll.stop();
    poll.stop(); // no throw
    const callsAfterStop = fn.mock.calls.length;
    vi.advanceTimersByTime(5000);
    expect(fn).toHaveBeenCalledTimes(callsAfterStop);
  });

  it("tracks isPolling", () => {
    const poll = usePolling({ intervalMs: 1000 });
    expect(poll.isPolling.value).toBe(false);
    poll.start(() => {});
    expect(poll.isPolling.value).toBe(true);
    poll.stop();
    expect(poll.isPolling.value).toBe(false);
  });

  it("stops and calls onTimeout after timeoutMs", () => {
    const fn = vi.fn();
    const onTimeout = vi.fn();
    const poll = usePolling({ intervalMs: 1000, timeoutMs: 2500, onTimeout });
    poll.start(fn);
    vi.advanceTimersByTime(2000); // within timeout: 1 immediate + 2 interval
    expect(onTimeout).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000); // crosses 2500ms threshold on next tick
    expect(onTimeout).toHaveBeenCalledTimes(1);
    expect(poll.isPolling.value).toBe(false);
    const callsAtTimeout = fn.mock.calls.length;
    vi.advanceTimersByTime(5000);
    expect(fn).toHaveBeenCalledTimes(callsAtTimeout); // loop halted
  });

  it("restart with no arg reuses the last poll fn", () => {
    const fn = vi.fn();
    const poll = usePolling({ intervalMs: 1000, immediate: true });
    poll.start(fn);
    poll.stop();
    poll.start(); // reuse
    expect(fn.mock.calls.length).toBeGreaterThanOrEqual(2);
    poll.stop();
  });

  it("start with a new fn replaces the previous one", () => {
    const first = vi.fn();
    const second = vi.fn();
    const poll = usePolling({ intervalMs: 1000, immediate: false });
    poll.start(first);
    vi.advanceTimersByTime(1000);
    poll.start(second);
    vi.advanceTimersByTime(1000);
    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
    poll.stop();
  });
});

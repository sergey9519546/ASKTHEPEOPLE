/**
 * useStatusPresentation
 *
 * One module for the two things five views were each re-deriving by hand: the
 * status → label lookup (with a fallback) and the normalization of an incoming
 * status against an allowed set or a remap. The label strings and the allowed
 * set genuinely differ per view ("BUILDING" vs "OPENING" vs "Preparing"), so
 * those stay caller config; only the behavior is centralized here.
 *
 * Usage:
 *   const currentStatus = ref("processing");
 *   const { label } = useStatusPresentation(currentStatus, {
 *     labels: { processing: "BUILDING", completed: "READY", failed: "NEEDS ATTENTION" },
 *     fallback: "NEEDS ATTENTION",
 *   });
 *
 *   // and where a child reports a raw status:
 *   currentStatus.value = normalizeStatus(reported, {
 *     allowed: ["processing", "completed", "failed"],
 *     fallback: "failed",
 *   });
 */

import { computed, unref } from "vue";

/**
 * Coerce a raw status into a view's vocabulary.
 * - `remap` wins first (e.g. { failed: "error" }); unlisted values pass through.
 * - otherwise, if `allowed` is given, an out-of-set value becomes `fallback`.
 * - with neither, the value passes through unchanged.
 */
export function normalizeStatus(value, { allowed = null, remap = null, fallback } = {}) {
  if (remap && Object.prototype.hasOwnProperty.call(remap, value)) {
    return remap[value];
  }
  if (Array.isArray(allowed)) {
    return allowed.includes(value) ? value : fallback;
  }
  return value;
}

/**
 * Present a status ref/getter as a human label. `statusRef` may be a ref, a
 * getter, or a computed; the returned `label` is reactive. `fallback` may be a
 * string, or a function receiving the current status (for view-specific
 * fallbacks such as upper-casing the raw value).
 */
export function useStatusPresentation(statusRef, { labels = {}, fallback = "" } = {}) {
  const resolve = () =>
    typeof statusRef === "function" ? statusRef() : unref(statusRef);

  const label = computed(() => {
    const current = resolve();
    if (Object.prototype.hasOwnProperty.call(labels, current)) {
      return labels[current];
    }
    return typeof fallback === "function" ? fallback(current) : fallback;
  });

  return { label };
}

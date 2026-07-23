## 2026-07-23 - String Date Comparison Optimization
**Learning:** Comparing ISO 8601 timestamp strings directly is much faster than instantiating `Date` objects in O(N log N) sorting callbacks, reducing GC overhead and CPU pressure in Vue component computed properties.
**Action:** When sorting dates based on ISO 8601 strings in JavaScript/Vue components, use direct string comparison (e.g., `a.timestamp < b.timestamp ? -1 : 1`) rather than `new Date(string)`.

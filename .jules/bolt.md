## 2026-08-04 - Expensive Date Instantiation in O(N log N) Sort Causes Frame Drops
**Learning:** In Vue computed properties (like `latestOpinions` in `OpinionMap.vue`), creating `new Date()` objects directly inside an Array `.sort()` comparator causes severe garbage collection overhead, particularly for reactive arrays triggering frequently.
**Action:** Always use lexicographical string comparison (e.g., `a.timestamp < b.timestamp ? -1 : (a.timestamp > b.timestamp ? 1 : 0)`) for ISO 8601 strings when sorting data to avoid GC pressure and ensure smooth 60fps animations.

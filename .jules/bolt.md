## 2024-05-15 - Date Parsing in Sorting Callbacks
**Learning:** Instantiating `Date` objects inside array sort callbacks (e.g., `new Date(a.timestamp) - new Date(b.timestamp)`) creates excessive garbage collection overhead and CPU pressure during O(N log N) sorts, significantly impacting rendering performance for large reactive lists in Vue components like `OpinionMap.vue`.
**Action:** Use direct string comparison for ISO 8601 timestamp strings (e.g., `a.timestamp < b.timestamp ? -1 : (a.timestamp > b.timestamp ? 1 : 0)`) to avoid object instantiation in sort loops.

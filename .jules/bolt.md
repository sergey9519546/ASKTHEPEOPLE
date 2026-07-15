## 2024-05-24 - Avoid Date allocations in sorting callbacks
**Learning:** Instantiating `Date` objects within O(N log N) operations like `Array.prototype.sort()` creates severe garbage collection overhead, particularly in Vue computed properties that are re-evaluated frequently (e.g., upon polling).
**Action:** When comparing ISO 8601 timestamps, use simple string comparison instead of `new Date()` instantiation to maintain O(1) memory usage during sorting.

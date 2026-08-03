## 2026-08-03 - Date Instantiation in Sort Callbacks
**Learning:** Instantiating `Date` objects within `Array.prototype.sort()` callbacks in Vue components (e.g., `OpinionMap.vue`) causes unnecessary GC overhead during O(N log N) sorting.
**Action:** Use string lexicographical comparison of ISO 8601 timestamps (e.g., `a.timestamp < b.timestamp ? -1 : 1`) instead of converting to `Date` objects when sorting by time.

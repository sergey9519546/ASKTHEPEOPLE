## 2026-07-28 - String lexicographical comparison for ISO dates
**Learning:** Instantiating `Date` objects in O(N log N) sort callbacks (e.g. `new Date(a.timestamp) - new Date(b.timestamp)`) causes significant GC overhead in Vue components like `OpinionMap.vue`.
**Action:** Directly compare ISO 8601 timestamp strings (e.g., `a.timestamp < b.timestamp ? -1 : (a.timestamp > b.timestamp ? 1 : 0)`) for sorting dates, as long as they have consistent precision.

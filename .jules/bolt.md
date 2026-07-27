## 2026-07-27 - Date Instantiation in Sort Loops
**Learning:** Instantiating `Date` objects within an O(N log N) sort callback for ISO 8601 strings creates significant garbage collection overhead, especially in polling loops. String lexicographical comparison is functionally equivalent and much more performant.
**Action:** When comparing ISO 8601 strings in JavaScript/Vue components, directly compare strings using lexicographical comparison rather than instantiating `Date` objects.

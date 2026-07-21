## 2026-07-21 - [String Comparison for ISO Dates in Sorting]
**Learning:** Instantiating `Date` objects inside O(N log N) sort callbacks introduces unnecessary GC overhead and CPU pressure in JavaScript/Vue when dealing with ISO 8601 timestamps, which are inherently string-comparable.
**Action:** Always compare ISO 8601 strings directly using string comparison operators (`<`, `>`) instead of converting them to `Date` objects during sorting.

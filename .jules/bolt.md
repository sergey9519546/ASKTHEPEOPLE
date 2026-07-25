## 2026-07-25 - [Optimize Date Sorting in Vue Components]
**Learning:** Instantiating `Date` objects in `sort` callbacks inside computed properties introduces unnecessary Garbage Collection (GC) overhead and performance bottlenecks for O(N log N) operations.
**Action:** Directly compare ISO 8601 timestamp strings (e.g., `a.timestamp < b.timestamp ? -1 : (a.timestamp > b.timestamp ? 1 : 0)`) instead of parsing them into `Date` objects when the string format supports lexicographical sorting.

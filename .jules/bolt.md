## 2024-05-19 - Vue Date Sorting Optimization
**Learning:** Instantiating `new Date` inside sort callbacks in Vue components (e.g. `(a, b) => new Date(a.timestamp) - new Date(b.timestamp)`) creates a massive performance bottleneck, especially for frequent reactive updates. This leads to unnecessary GC overhead and O(N log N) object creations.
**Action:** Always compare ISO 8601 strings directly in JavaScript using standard string comparison operators (`<`, `>`) rather than creating `Date` objects inside loops or sort functions.

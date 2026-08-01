## 2026-08-01 - [Frontend Sorting Optimization]
**Learning:** Instantiating Date objects within sort callbacks (e.g., `new Date(a.timestamp) - new Date(b.timestamp)`) for large datasets in Vue components (like OpinionMap.vue) introduces significant garbage collection (GC) overhead.
**Action:** When sorting arrays of objects with ISO 8601 timestamps, use lexicographical string comparison (e.g., `a.timestamp < b.timestamp ? -1 : ...`) directly instead of parsing strings into Date objects. This is much faster.

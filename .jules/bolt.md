## 2024-06-11 - Date instantiation inside Array.prototype.sort()
**Learning:** Instantiating `new Date()` inside a `sort` callback is extremely slow because it runs O(N log N) times.
**Action:** Always prefer direct string or numeric comparison for ISO 8601 timestamps inside sorting loops.

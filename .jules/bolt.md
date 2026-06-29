## 2024-06-29 - String Timestamp Comparison
**Learning:** Instantiating `Date` objects inside `.sort()` callbacks in computed properties (like `OpinionMap.vue`) causes significant object allocation overhead when dealing with large arrays. ISO 8601 strings can be safely and more efficiently compared directly as strings.
**Action:** Use native string comparison (`a < b ? -1 : (a > b ? 1 : 0)`) for ISO 8601 timestamps inside loops or sorts instead of `new Date()`.

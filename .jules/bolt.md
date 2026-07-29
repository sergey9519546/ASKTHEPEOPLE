## 2026-07-29 - Date Instantiation in Sort Callbacks
**Learning:** Instantiating `Date` objects within O(N log N) sort callbacks creates significant Garbage Collection overhead. ISO 8601 strings can be safely compared lexicographically.
**Action:** Use string comparison (e.g., `a < b ? -1 : 1`) instead of `new Date(a) - new Date(b)` when sorting ISO 8601 timestamp strings.

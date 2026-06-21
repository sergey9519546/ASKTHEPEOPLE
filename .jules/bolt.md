## 2025-10-09 - String comparisons for ISO 8601 Timestamps
**Learning:** Instantiating `Date` objects inside `.sort()` loops (like `new Date(a.timestamp) - new Date(b.timestamp)`) creates unnecessary memory allocations when ISO 8601 timestamps are used, since ISO 8601 strings sort lexicographically perfectly.
**Action:** Always compare ISO 8601 strings directly (`a.timestamp < b.timestamp`) in sorting functions instead of converting them to `Date` objects.

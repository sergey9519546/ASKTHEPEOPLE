
## 2024-05-18 - Avoid instantiating Dates inside tight loops for ISO 8601 strings
**Learning:** Instantiating `Date` objects inside array `.sort()` callbacks is a massive performance bottleneck because `new Date()` is slow due to parsing and memory allocation. Since ISO 8601 timestamps are perfectly sortable as strings, we can skip `Date` entirely.
**Action:** Always use direct string comparison `a < b ? -1 : (a > b ? 1 : 0)` when sorting ISO 8601 timestamp strings.

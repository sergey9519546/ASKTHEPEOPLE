
## 2024-05-24 - Optimize Timestamp Sorting
**Learning:** Instantiating `Date` objects within O(N log N) sort callbacks creates unnecessary garbage collection overhead and CPU pressure, especially during Vue component renders with frequent data updates.
**Action:** When sorting or comparing ISO 8601 timestamp strings, use direct string comparison (e.g., `a < b ? -1 : (a > b ? 1 : 0)`) instead of parsing them into Date objects.

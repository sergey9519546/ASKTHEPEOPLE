## 2024-05-24 - Avoid Date parsing in JS sorts
**Learning:** Instantiating `Date` objects within O(N log N) sort callbacks creates unnecessary GC overhead, CPU pressure, and degrades rendering performance for components mapping lists.
**Action:** When comparing ISO 8601 timestamps, do direct string comparison (e.g. `a.timestamp < b.timestamp ? -1 : (a.timestamp > b.timestamp ? 1 : 0)`) instead of parsing to `Date`.

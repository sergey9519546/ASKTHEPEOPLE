## 2026-07-31 - Prevent GC Overhead in Date Sorting
**Learning:** In Vue components, sorting arrays by parsing ISO strings into `Date` objects creates unnecessary garbage collection overhead in O(N log N) operations.
**Action:** Directly compare ISO 8601 timestamp strings lexicographically for dates with consistent precision to improve performance.

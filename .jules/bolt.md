## 2026-07-23 - Optimize date sorting
**Learning:** Instantiating Date objects inside O(N log N) sort callbacks causes unnecessary GC overhead and CPU pressure in Vue components.
**Action:** Directly compare ISO 8601 timestamp strings when sorting arrays by date.

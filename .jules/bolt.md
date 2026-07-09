## 2024-05-30 - Optimize Date Sorting
**Learning:** Instantiating `Date` objects inside O(N log N) sort callbacks causes unnecessary GC overhead and CPU pressure when comparing ISO 8601 strings, which are natively lexicographically sortable.
**Action:** Directly compare ISO timestamp strings (e.g., `a.timestamp < b.timestamp ? -1 : (a.timestamp > b.timestamp ? 1 : 0)`) in Vue/JS components like `OpinionMap.vue` to improve rendering performance.

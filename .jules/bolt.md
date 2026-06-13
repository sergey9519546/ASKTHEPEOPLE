## 2026-06-13 - Frontend Performance
**Learning:** Creating `Date` objects within an array sort comparator causes heavy performance overhead O(N log N) object allocations. ISO 8601 strings safely sort chronologically via standard lexicographical direct string comparison.
**Action:** Use string comparators like `< ` for ISO timestamps in sorting components like `OpinionMap.vue` to avoid unnecessary memory allocations.

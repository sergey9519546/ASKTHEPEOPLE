## 2024-05-14 - direct string comparison of ISO timestamps
**Learning:** Using new Date() instantiations in sort callbacks creates unnecessary O(N log N) GC overhead, which hurts rendering performance for large lists of components like the OpinionMap.vue component.
**Action:** Always sort ISO 8601 strings directly using `<` or `>` operators rather than parsing them to `Date` objects first.

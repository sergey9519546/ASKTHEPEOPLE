## 2024-07-01 - Date String Comparison Optimization
**Learning:** Instantiating `Date` objects in JS for sorting inside computed properties or loops can become a performance bottleneck. Comparing ISO 8601 timestamp strings directly using `<` or `>` is significantly faster.
**Action:** When comparing timestamps in Vue components (e.g., OpinionMap.vue), directly compare the ISO 8601 strings rather than instantiating `Date` objects.

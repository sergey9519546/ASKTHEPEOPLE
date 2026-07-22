## $(date +%Y-%m-%d) - Optimize Date Comparisons in Vue Components
**Learning:** Found O(N log N) rendering performance issues caused by instantiating Date objects inside array sorting callbacks in Vue computed properties (like `latestOpinions` in `OpinionMap.vue`).
**Action:** When sorting or comparing dates in JavaScript/Vue components, directly compare ISO 8601 timestamp strings rather than instantiating Date objects to reduce unnecessary GC overhead, CPU pressure, and improve rendering performance.

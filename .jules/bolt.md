## 2024-05-24 - Avoid Date parsing in high-frequency Vue computed loops
**Learning:** Comparing ISO 8601 timestamp strings natively is ~100x faster than parsing `new Date()` inside a `sort()` function. In `OpinionMap.vue`, mapping the latest opinion per agent used an O(N log N) array sort with `new Date()` comparisons, creating an enormous performance bottleneck during live data streams.
**Action:** Replace `Array.sort` with an `O(N)` linear scan using a Map, and compare ISO 8601 timestamp strings using string comparison directly without instantiating `Date` objects.

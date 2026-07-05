## 2024-07-05 - Avoid Date Parsing in O(N log N) Vue Computed Sort Callbacks
**Learning:** Instantiating `Date` objects within a `sort` callback in a Vue `computed` property (like in `OpinionMap.vue`) creates significant GC (Garbage Collection) overhead and CPU pressure during render loops when the list of opinions is long.
**Action:** When comparing ISO 8601 timestamp strings, use direct string comparison (e.g., `a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0`) instead of parsing them into `Date` objects.

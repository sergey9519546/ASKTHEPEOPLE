## 2026-06-19 - Vue computed property sorting bottleneck
**Learning:** Instantiating `Date` objects inside array `sort` callbacks within Vue computed properties (like `latestOpinions` in `OpinionMap.vue`) causes significant rendering overhead and garbage collection pauses when dealing with frequent updates.
**Action:** When comparing ISO 8601 timestamp strings in Vue components, use direct string comparison (`a < b ? -1 : 1`) rather than parsing into `Date` objects inside loops.

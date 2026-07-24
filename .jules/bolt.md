## 2026-07-24 - Optimize Date Sorting in Vue computed properties
**Learning:** Instantiating Date objects in Vue computed property sort callbacks causes measurable GC overhead for O(N log N) operations. ISO 8601 strings can be sorted directly using lexicographical comparison.
**Action:** Use string comparison (e.g., a.timestamp < b.timestamp ? -1 : 1) instead of new Date(a.timestamp) - new Date(b.timestamp) when dealing with ISO 8601 strings.

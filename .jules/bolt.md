## 2024-07-03 - Optimize date string comparisons
**Learning:** Instantiating Date objects inside loop iterations (like Array.sort) for ISO 8601 strings is computationally expensive and causes performance bottlenecks in Vue computed properties.
**Action:** Directly compare ISO 8601 timestamp strings using string comparison operators (e.g., `<` and `>`) instead of converting them to Date objects when sorting or filtering.

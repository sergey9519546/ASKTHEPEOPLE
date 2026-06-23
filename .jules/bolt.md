## 2024-06-23 - Avoid new Date() in Sort Loops for ISO Strings
**Learning:** Instantiating `new Date()` inside a `sort` comparator for arrays of objects with ISO 8601 timestamps causes significant performance overhead in Vue components, especially in computed properties that trigger frequently.
**Action:** Always compare ISO 8601 timestamp strings lexicographically (e.g., `a < b ? -1 : a > b ? 1 : 0`) instead of parsing them to Date objects.

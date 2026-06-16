## 2024-06-16 - Lexicographical timestamp comparison
**Learning:** In frontend components dealing with large sets of ISO 8601 timestamps (like in 3D opinion maps rendering hundreds of points), instantiating `Date` objects inside tight loops (like `Array.prototype.sort`) is a significant hidden bottleneck.
**Action:** Since ISO 8601 format guarantees strict lexicographical ordering (e.g., "2024-01-02T10:00:00Z" > "2024-01-01T10:00:00Z"), use direct string comparison `<` and `>` instead of `new Date()` when sorting by timestamp.

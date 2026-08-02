## 2026-08-02 - Optimize sorting date parsing
**Learning:** Instantiating `new Date()` in O(N log N) sort callbacks creates significant GC overhead, leading to poor UI performance with large lists.
**Action:** For consistent ISO 8601 strings, use direct string lexicographical comparison instead of parsing `Date` objects.

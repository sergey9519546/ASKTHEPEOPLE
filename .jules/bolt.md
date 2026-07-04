## 2026-07-04 - Avoid Date instantiations in sort callbacks
**Learning:** Instantiating new Date() inside an O(N log N) sort callback within Vue computed properties creates unnecessary GC overhead and CPU pressure.
**Action:** Use direct ISO 8601 string comparisons in a single O(N) iteration instead.

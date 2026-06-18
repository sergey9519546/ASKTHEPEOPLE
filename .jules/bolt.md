## 2024-06-18 - Avoid parsing dates in sort
**Learning:** Parsing dates with `new Date()` inside loops or array sorts is a performance bottleneck. String comparisons (`a >= b`) or checking `a.localeCompare(b)` works for ISO 8601 strings and is much faster.
**Action:** When comparing dates in JavaScript/Vue components, use direct string comparison rather than `new Date()`.

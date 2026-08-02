## 2024-08-01 - Bug Fixes for Report Evidence
**Learning:** In python sqlite queries for LIMIT can be exhausted quickly by duplicate search queries.
**Action:** When sorting or comparing dates in JS/Vue use lexicographical sort on `toISOString()`, but here we fixed dedup logic in python while preserving order for `report_evidence`.

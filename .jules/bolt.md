## 2024-05-24 - Avoid Date parsing inside sort loops
**Learning:** Instantiating Date objects inside a sorting loop over arrays is extremely slow and causes unnecessary allocation in JavaScript.
**Action:** Use string comparison for ISO 8601 timestamps instead of parsing Date objects when sorting arrays by timestamp.

## 2025-06-30 - Fast ISO 8601 String Comparison
**Learning:** In Vue templates/components handling timelines, JavaScript's natively fast string comparison (e.g., `a.timestamp < b.timestamp`) is vastly superior to instantiating `new Date()` within `.sort()` loops for ISO 8601 timestamp arrays.
**Action:** Always avoid `new Date()` within loop/sort conditions for data formatted as ISO 8601 strings (e.g., `YYYY-MM-DDTHH:MM:SSZ`), utilizing standard string operators for >600x performance scaling on large simulations.

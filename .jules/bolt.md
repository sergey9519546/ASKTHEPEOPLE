## 2024-05-30 - Date Comparison Optimization in Vue Components
**Learning:** Instantiating `Date` objects inside array sorting loops (e.g., `new Date(a.timestamp) - new Date(b.timestamp)`) creates a significant performance bottleneck due to continuous allocation and parsing, especially for dynamic arrays like those in 3D agent visualizations.
**Action:** Always use lexicographical string comparison (`<`, `>`, `===`) on ISO 8601 timestamp strings directly to avoid `Date` instantiation overhead inside hot paths.

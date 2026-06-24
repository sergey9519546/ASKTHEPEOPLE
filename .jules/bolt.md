## 2024-06-24 - Avoid Date parsing in Vue v-for
**Learning:** Comparing ISO 8601 strings directly in JavaScript sort functions is much faster than instantiating `Date` objects for each comparison, especially in computed properties used in `v-for` lists.
**Action:** Replace `new Date(a).getTime() - new Date(b).getTime()` with a direct string comparison `a > b ? 1 : a < b ? -1 : 0` or simply `a.localeCompare(b)` if they are in ISO 8601 format.

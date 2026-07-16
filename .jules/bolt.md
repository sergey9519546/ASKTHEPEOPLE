## 2024-05-24 - Avoid Date Instantiation in Sort Callbacks
**Learning:** Instantiating Date objects inside array sort callbacks causes unnecessary CPU pressure and memory allocation, slowing down rendering in Vue components like OpinionMap.vue.
**Action:** Use direct string comparison for ISO 8601 timestamps (e.g. `a < b ? -1 : (a > b ? 1 : 0)`) in high-frequency operations.

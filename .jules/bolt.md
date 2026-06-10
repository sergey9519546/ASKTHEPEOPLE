## 2024-06-10 - Avoid Date Instantiation in Sort Comparators
**Learning:** Instantiating `new Date()` inside an array sort comparator creates significant garbage collection overhead and slows down rendering inside reactive `computed` properties, especially for ISO 8601 strings which can be compared alphabetically.
**Action:** Always use string comparison (like `a.timestamp < b.timestamp`) for ISO 8601 formatted timestamps in sort functions instead of parsing them into Date objects.

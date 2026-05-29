## 2024-05-29 - Vue 3 v-memo strict equality
**Learning:** In Vue 3 frontend components, `v-memo` is excellent for optimizing large `v-for` lists. However, when defining dependencies, explicitly tracking primitive properties is crucial because Vue uses strict equality (`===`) for comparisons, which breaks reactivity if tracking nested reactive objects directly.
**Action:** Always use primitive properties of array items (e.g., `item.id`, `item.status`) as dependencies in `v-memo` for complex, deeply nested objects.

## 2024-05-31 - v-memo optimization in Vue
**Learning:** In Vue 3 frontend components, prefer using the `v-memo` directive on large `v-for` lists (e.g., in HistoryDatabase.vue) to significantly reduce virtual DOM updates. When defining `v-memo` dependencies, explicitly track primitive properties (e.g., `item.id`, `item.status`) rather than the reactive object itself, as Vue uses strict equality (`===`) which breaks reactivity for internal object changes.
**Action:** Use `v-memo` with specific property dependencies to avoid unnecessary re-renders in large lists.

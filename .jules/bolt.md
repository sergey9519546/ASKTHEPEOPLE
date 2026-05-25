## 2024-05-25 - Vue v-memo Optimization
**Learning:** Found a missing v-memo on a long v-for list (in `HistoryDatabase.vue`), causing unnecessary re-renders in a complex UI. Vue reactivity doesn't deeply track identical objects with strict equality, so `v-memo` requires primitives like `project.simulation_id` instead of the object itself.
**Action:** When working with long `v-for` lists in Vue, carefully specify primitive dependencies in `v-memo` for performance gains without breaking reactivity.

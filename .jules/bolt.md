## 2024-06-03 - Vue 3 v-memo on large v-for lists
**Learning:** Using `v-memo` directive on large `v-for` lists significantly reduces virtual DOM updates. However, it's crucial to explicitly track primitive properties (e.g., `item.id`, `item.status`) rather than the reactive object itself, as Vue uses strict equality (`===`) which breaks reactivity for internal object changes.
**Action:** When optimizing Vue 3 lists with `v-memo`, always map out exactly which primitive fields dictate a re-render for the item (e.g., id, status, active state, hover state) and use those in the dependency array.

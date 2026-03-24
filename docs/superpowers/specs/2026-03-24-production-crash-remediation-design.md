# Production Crash Remediation — Design Spec

**Date:** 2026-03-24
**Scope:** Fix all production crash failure modes identified in the 68-issue audit
**Approach:** Hybrid — global safety net for the API/error layer, surgical patches for routing and null access

---

## Naming Clarification

`Process.vue` and `MainView.vue` are two distinct files with separate logic.
The router registers `MainView.vue` under the route name `"Process"` via an import alias — the route named `"Process"` maps to `MainView.vue`, **not** to `Process.vue`.
This spec lists them separately in the files table because they are different files requiring different edits.

---

## Problem Statement

A comprehensive audit identified 68 issues across the ASKTHEPEOPLE frontend. Three categories cause active production crashes:

1. **Navigation failure** — `router.push({ name: "Main" })` in `Process.vue:164` references a route that doesn't exist, silently breaking all navigation past Phase 1
2. **Null access explosions** — `projRes.data.graph_id` and similar accessed without null-checking; unexpected API shapes crash entire views
3. **Silent polling freeze** — `pollOntologyTask()` and other async chains have no recovery path; one bad response permanently freezes the UI with no user feedback

---

## Chosen Approach: Three-Layer Patch (Option A)

Global fixes where root causes are centralized; surgical patches where issues are isolated.

---

## Layer 1 — Global Safety Net

**Files:** `frontend/src/api/index.js`, `frontend/src/main.js`, `frontend/src/App.vue`

### API Response Interceptor (`api/index.js`)

The existing interceptor already has a `service.interceptors.response.use(...)` success handler that unwraps `response.data` into `res`. **Do not add a second interceptor call.** Instead, insert the following null/type guard at the very top of the existing success handler, before the `const res = response.data` line:

```js
// At the top of the existing success handler:
if (response.data == null || typeof response.data !== 'object') {
  response.data = { success: false, error: 'empty_response' }
}
// Existing logic continues below unchanged:
// const res = response.data
// ...
```

This handles three cases:
- `response.data` is `null` or `undefined` (backend NoneType bug)
- `response.data` is a plain string (e.g., `"ok"` or an HTML error page from a proxy)
- `response.data` is a number or other non-object primitive

The `content` null patch (`if (res.content == null) res.content = ''`) is inserted after `const res = response.data`, before the return, to handle models like stepfun that return null content fields.

### Vue Global Error Handler (`main.js`)

Add a single `app.config.errorHandler` that:

- Logs the error (dev environment only, guarded by `import.meta.env.DEV`)
- Sets a top-level `hasCrashed` reactive ref exported from a shared composable
- `App.vue` watches `hasCrashed` and renders a minimal "Something went wrong — reload" banner instead of a blank/frozen screen

### Crash Banner (`App.vue`)

Add a `v-if="hasCrashed"` overlay with a "Reload" button (`window.location.reload()`). Positioned fixed, full-width, above all other content.

---

## Layer 2 — Routing Surgery

**Files:** `frontend/src/views/Process.vue`, `frontend/src/router/index.js`

### Fix Broken Route Name (`Process.vue` lines 162–167)

```js
// BEFORE (broken — route "Main" does not exist)
router.push({ name: "Main", query: { step: 2, projectId: currentProjectId.value } })

// AFTER (confirmed: "Process" exists in router at line 17, path /process/:projectId)
router.push({ name: "Process", params: { projectId: currentProjectId.value }, query: { step: 2 } })
```

### Navigation Guard (`router/index.js`)

Add a `beforeEach` guard that validates required route params:

- Routes requiring `projectId` (e.g., `/process/:projectId`): redirect to `/` if `params.projectId` is falsy or `"undefined"`
- Routes requiring `simulationId`: redirect to `/` if param is falsy
- Routes requiring `reportId`: redirect to `/` if param is falsy

**No changes to `SimulationView.vue` or the router's param names.** The previously identified "naming clash" was incorrect — the router declares `simulationId` and `SimulationView.vue` correctly reads `route.params.simulationId` into a local ref named `currentSimulationId`. No fix needed there.

---

## Layer 3 — Null-Safety Surgical Patches

**Files:** `frontend/src/views/MainView.vue`, `frontend/src/views/ReportView.vue`, `frontend/src/views/InteractionView.vue`, `frontend/src/views/Process.vue`

Seven targeted edits using optional chaining (`?.`) and nullish coalescing (`??`). Line numbers are approximate — anchor by function name as line numbers shift:

| File | Function | Change |
|------|----------|--------|
| `MainView.vue` | `fetchGraphData()` | `projRes.data.graph_id` → `projRes.data?.graph_id` |
| `MainView.vue` | `pollTaskStatus()` final load block | `projRes.data.graph_id` → `projRes.data?.graph_id` |
| `MainView.vue` | `pollOntologyTask()` | Silent `return` on `!res.success` → also set `error.value = 'Ontology poll failed'` |
| `MainView.vue` | `pollOntologyTask()` | `task.message` comparison → `(task.message ?? '') !== (buildProgress.value?.message ?? '')` |
| `ReportView.vue` | `loadReportData()` (~line 147) | After `simulationId.value = reportData.simulation_id`, add: `if (!simulationId.value) { error.value = 'Report data missing simulation reference'; return; }` |
| `InteractionView.vue` | `loadReportData()` (~line 147) | Same as above |
| `Process.vue` | `pollTaskStatus()` | `buildProgress.value = { progress: task.progress ?? 0, message: task.message ?? '' }` |

---

## What This Does NOT Cover

The following issues from the 68-issue audit are out of scope for this patch:

- CSS inconsistencies (hardcoded values, undefined variables, mixed font weights)
- `console.log`/`console.warn`/`console.error` in production code
- Hardcoded magic numbers (polling intervals, log limits, step counts)
- `v-for` index keys on mutable lists
- Missing prop type definitions
- Dead code (unused refs, methods without UI triggers)
- Configuration issues (debug defaults, missing config keys)

---

## Files Touched

| File | Layer | Change Type |
|------|-------|-------------|
| `frontend/src/api/index.js` | 1 | Modify existing interceptor: add null/type guard + content null patch |
| `frontend/src/main.js` | 1 | Add `app.config.errorHandler` |
| `frontend/src/App.vue` | 1 | Add crash banner (`v-if="hasCrashed"`) |
| `frontend/src/router/index.js` | 2 | Add `beforeEach` param validation guard |
| `frontend/src/views/Process.vue` | 2 + 3 | Fix route name + `buildProgress` null-safety |
| `frontend/src/views/MainView.vue` | 3 | 4 null-safety patches across 3 functions |
| `frontend/src/views/ReportView.vue` | 3 | Fallback error state in `loadReportData()` |
| `frontend/src/views/InteractionView.vue` | 3 | Fallback error state in `loadReportData()` |

**Total: 8 files, all small edits. No new files created. No logic refactored.**

---

## Success Criteria

1. Navigating from Phase 1 → Phase 2 in `Process.vue` works without a console error
2. API returning `null`, `undefined`, or a plain string does not crash any view — the response is normalized to `{ success: false, error: 'empty_response' }`
3. A failed poll (`!res.success`) sets `error.value` and is visible in the UI — the view never silently freezes
4. Any uncaught render error triggers the crash banner — **test vector**: manually throw `throw new Error('test')` inside a `onMounted` hook in `App.vue` during development; confirm the banner renders and the reload button calls `window.location.reload()`

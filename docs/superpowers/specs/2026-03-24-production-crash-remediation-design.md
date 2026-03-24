# Production Crash Remediation — Design Spec

**Date:** 2026-03-24
**Scope:** Fix all production crash failure modes identified in the 68-issue audit
**Approach:** Hybrid — global safety net for the API/error layer, surgical patches for routing and null access

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

Add an Axios response interceptor that normalizes all API responses before any component receives them:

- If `response.data` is `null` or `undefined`, replace with `{ success: false, error: 'empty_response' }`
- If `response.data.content` is `null`, set it to `''` (prevents NoneType crashes from models like stepfun that return null content)

This means every component always receives a predictable object shape. The `projRes.data.graph_id` family of crashes is eliminated at the source.

### Vue Global Error Handler (`main.js`)

Add a single `app.config.errorHandler` that:

- Logs the error (dev environment only)
- Sets a top-level `hasCrashed` reactive ref
- `App.vue` watches `hasCrashed` and renders a minimal "Something went wrong — reload" banner instead of a blank/frozen screen

This is the last line of defense for any uncaught promise rejection or render error that slips through the other layers.

---

## Layer 2 — Routing Surgery

**Files:** `frontend/src/views/Process.vue`, `frontend/src/router/index.js`, `frontend/src/views/SimulationView.vue`

### Fix Broken Route Name (`Process.vue:164`)

```js
// BEFORE (broken — route "Main" does not exist)
router.push({ name: "Main", query: { step: 2, projectId: currentProjectId.value } })

// AFTER
router.push({ name: "Process", params: { projectId: currentProjectId.value }, query: { step: 2 } })
```

### Navigation Guard (`router/index.js`)

Add a `beforeEach` guard that validates required route params:

- Routes requiring `projectId`: redirect to `/` if missing or `undefined`
- Routes requiring `simulationId`: redirect to `/` if missing or `undefined`
- Routes requiring `reportId`: redirect to `/` if missing or `undefined`

Prevents blank views when users land on deep-link URLs with missing/undefined params.

### Fix `simulationId` Naming Clash

`router.js` declares the param as `simulationId` but `SimulationView.vue` reads it as `currentSimulationId`. Align both to `simulationId`.

---

## Layer 3 — Null-Safety Surgical Patches

**Files:** `frontend/src/views/MainView.vue`, `frontend/src/views/ReportView.vue`, `frontend/src/views/InteractionView.vue`, `frontend/src/views/Process.vue`

Six targeted edits using optional chaining (`?.`) and nullish coalescing (`??`):

| File | Line | Change |
|------|------|--------|
| `MainView.vue` | 294 | `projRes.data.graph_id` → `projRes.data?.graph_id` |
| `MainView.vue` | 438 | `projRes.data.graph_id` → `projRes.data?.graph_id` |
| `MainView.vue` | 278 | Silent `return` → set `error.value` so UI reflects the failure |
| `MainView.vue` | 419 | `task.message` comparison → add `?? ''` on both sides |
| `ReportView.vue` | 91 | `simulationId` assignment gets fallback error state |
| `InteractionView.vue` | 91 | `simulationId` assignment gets fallback error state |
| `Process.vue` | 190 | `task.progress ?? 0`, `task.message ?? ''` (consistency) |

---

## What This Does NOT Cover

The following issues from the 68-issue audit are out of scope for this patch and should be addressed in a separate pass:

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
| `frontend/src/api/index.js` | 1 | Add response interceptor |
| `frontend/src/main.js` | 1 | Add global error handler |
| `frontend/src/App.vue` | 1 | Add crash banner state + template |
| `frontend/src/router/index.js` | 2 | Add beforeEach guard |
| `frontend/src/views/Process.vue` | 2 + 3 | Fix route name + null-safety |
| `frontend/src/views/SimulationView.vue` | 2 | Fix param name |
| `frontend/src/views/MainView.vue` | 3 | 4 null-safety patches |
| `frontend/src/views/ReportView.vue` | 3 | Fallback error state |
| `frontend/src/views/InteractionView.vue` | 3 | Fallback error state |

**Total: 9 files, all small edits. No new files created. No logic refactored.**

---

## Success Criteria

- Navigating from Phase 1 → Phase 2 in `Process.vue` works without error
- API returning `null` or malformed data does not crash any view
- A failed poll shows an error state in the UI, never a frozen/blank screen
- Any uncaught error anywhere shows a reload banner rather than a silent blank

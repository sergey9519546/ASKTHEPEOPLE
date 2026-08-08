---
title: "Decision Workspace Foundation Implementation Plan"
status: "Operational / Staged"
version: "1.1.0"
owner: "Architecture + Security + Frontend"
last_reviewed: "2026-08-08"
review_cycle: "Per implementation checkpoint"
research_cutoff: "2026-08-08"
---

# Decision Workspace Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the truth-safe data and workflow foundation for the proposed
Decision Chamber experience, then expose it through one feature-flagged
vertical UI slice without fabricating unavailable capabilities.

**Architecture:** The server owns organization/workspace identity, typed
provenance, source review, run state, possible paths, and comparison
eligibility. UUIDv7 physical IDs remain internal; independently generated
public aliases cross service boundaries. Vue consumes canonical typed
responses. Each new vertical slice is enabled only by an explicit feature
flag, and canonical modes never fall back to legacy storage.

**Tech Stack:** Python 3.12, Flask, Pydantic v2, SQLAlchemy/Alembic, Celery,
pytest, Vue 3, Vue Router, Vite, Vitest, semantic HTML, CSS custom properties.

## Global Constraints

- Product Truth Contract fields are immutable: `output_origin="synthetic"`,
  `human_respondent_count=0`, `is_forecast=false`,
  `is_public_opinion_measure=false`, `is_causal_evidence=false`,
  `source_role="starting_conditions_only"`, and
  `human_validation_scope="external_to_synthetic_run"`.
- Source segments may inform unchanged, reviewed starting conditions only.
  They MUST NOT
  directly support a possible path, consideration, or conclusion.
- Completed runs are immutable. A changed condition creates a new run with a
  recorded parent; stage retry creates a new immutable stage attempt.
- Reconnection is a browser state and MUST NOT mutate server execution state.
- Stopped and failed runs MUST NOT create a final brief.
- Comparison accepts exactly two completed attempts with stable semantic IDs.
- General analytics MUST NOT contain source text, decision text, path prose,
  filenames, profile prose, or PII.
- UI phases are Sources, Assumptions, Paths, Brief, and Research. `Run Record`
  is a disclosure, not a public body.
- Candidate v2 images under `docs/design/references/` define composition only.
  Production copy and capability claims remain governed by normative docs.
- New API handlers go under `backend/app/api/routes/`. Do not add handlers to
  `backend/app/api/simulation.py`.
- Long-running work goes through the job system. No route may start a thread or
  subprocess.
- Every task follows one-test-at-a-time red-green-refactor development.

---

### Task 1: Govern the revised specification and visual state pack

**Files:**
- Modify: `docs/superpowers/specs/2026-08-08-decision-chamber-experience-design.md`
- Create: `docs/design/references/README.md`
- Create: `docs/design/references/DECISION_WORKSPACE_STATE_PACK_V2.md`
- Create: `docs/design/references/decision-chamber-paths-approved.png`
- Create: `docs/design/references/decision-workspace-*-candidate-v2.png`

**Interfaces:**
- Consumes: the user-approved `1672 × 941` Possible Paths reference.
- Produces: repository-owned design assets with dimensions, SHA-256 hashes,
  approval status, and explicit composition-versus-capability boundary.

- [ ] **Step 1: Reclassify the specification**

  Set frontmatter and visible status to `Proposed / Revision Required` and
  replace the absolute local image path with the repository-owned asset.

- [ ] **Step 2: Check in the approved reference and candidate pack**

  Preserve the approved reference hash
  `1BD22B6E8A5B882EB5B29F0989864D74454FEFEA4B52B49A14C71CD548816F36`.

- [ ] **Step 3: Document the candidate grammar**

  Record the masthead, numbered spine, architectural chamber arena, asymmetric
  context column, and chronological record as the five compositional
  characteristics that candidate implementations must preserve.

- [ ] **Step 4: Verify documentation**

  Run: `python tools/validate_docs.py`

  Expected: `Warnings: 0`, `Errors: 0`, `RESULT: PASS`.

### Task 2: Add typed product-truth and provenance domain contracts

**Files:**
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/decision_workspace.py`
- Test: `backend/tests/domain/test_decision_workspace.py`

**Interfaces:**
- Produces: `TruthBundle`, `EpistemicOrigin`, `EpistemicRole`,
  `ProvenanceRelation`, `ProvenanceEdge`, `PossiblePath`, and
  `validate_provenance_edge(edge) -> None`.
- Consumers: workspace manifest, source review, path persistence, comparison,
  and API response schemas.

- [ ] **Step 1: Write a failing truth-bundle test**

  ```python
  def test_truth_bundle_is_locked_to_synthetic_boundary():
      bundle = TruthBundle.synthetic()
      assert bundle.model_dump() == {
          "output_origin": "synthetic",
          "human_respondent_count": 0,
          "is_forecast": False,
          "is_public_opinion_measure": False,
          "is_causal_evidence": False,
          "source_role": "starting_conditions_only",
          "human_validation_scope": "external_to_synthetic_run",
      }
  ```

- [ ] **Step 2: Run the test and confirm RED**

  Run: `cd backend && .\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q`

  Expected: import failure because the domain module does not exist.

- [ ] **Step 3: Implement frozen typed contracts**

  Use Pydantic frozen models and `str, Enum` values. Do not use arbitrary
  strings for epistemic role or relationship type.

- [ ] **Step 4: Add one failing prohibited-edge test**

  ```python
  def test_source_segment_cannot_support_possible_path():
      edge = ProvenanceEdge(
          source_id="segment_1",
          source_role=EpistemicRole.SOURCE_SEGMENT,
          target_id="path_1",
          target_role=EpistemicRole.POSSIBLE_PATH,
          relation=ProvenanceRelation.SUPPORTS,
      )
      with pytest.raises(ProvenanceViolation, match="source_to_path_forbidden"):
          validate_provenance_edge(edge)
  ```

- [ ] **Step 5: Implement the allowed-edge matrix and pass tests**

  Use the closed `epistemic-ledger/v2` matrix from the Product Truth Contract.
  In particular, a source segment may `INFORMS` only an unchanged reviewed
  starting condition; a path `BRANCHES_ON` reviewed assumptions or uncertainty
  states, `SEQUENCES` steps, and `SURFACES` considerations. No default allow
  path exists.

### Task 3: Add a server-owned workspace manifest

**Files:**
- Create: `backend/app/application/__init__.py`
- Create: `backend/app/application/decision_workspace_service.py`
- Create: `backend/app/api/routes/workspace_routes.py`
- Modify: `backend/app/api/routes/__init__.py`
- Test: `backend/tests/test_decision_workspace_api.py`

**Interfaces:**
- Produces: `GET /api/simulation/workspaces/by-project/<project_id>`.
- Response: `DecisionWorkspaceManifest` with server-issued `workspace_id`,
  `project_id`, related simulation/report IDs, manifest version, availability
  states, complete `TruthBundle`, and `storage_status="TRANSITION"`.
- The resolver returns `409 workspace_manifest_conflict` instead of heuristically
  choosing among incompatible records.

- [ ] **Step 1: Write the 404 and truth-boundary API tests**
- [ ] **Step 2: Confirm both tests fail**
- [ ] **Step 3: Implement an atomic repository-owned manifest under the project record**
- [ ] **Step 4: Register the route from `routes/__init__.py`**
- [ ] **Step 5: Pass focused API tests**

### Task 3a: Establish tenant identity and canonical core persistence

**Implementation contract:**
`.superpowers/sdd/task-3a-tenant-persistence-brief.md`.

**Interfaces:**

- UUIDv7 physical identities and independently generated public aliases;
- immutable server-derived `ActorContext` and closed capability policy;
- canonical `organization -> workspace -> project` records;
- PostgreSQL `core.*` schema, forced RLS, scoped repositories, OIDC bootstrap,
  operator-owned adoption/backfill, and no-fallback cutover;
- no sources, runs, paths, briefs, or user-facing tenancy administration in
  this foundation slice.

- [ ] **Checkpoint 3A-0: Land and validate the normative authority packet**
- [ ] **Checkpoint 3A-1: Implement identifiers, authorization, and ActorContext**
- [ ] **Checkpoint 3A-2: Add the additive core schema and migration adoption**
- [ ] **Checkpoint 3A-3: Add OIDC, RLS, and scoped repositories**
- [ ] **Checkpoint 3A-4: Add operator backfill and shadow comparison**
- [ ] **Checkpoint 3A-5: Rehearse deployment, restore, and no-fallback cutover**

### Task 4: Implement secure source-ingestion and review states

**Implementation contract:** `.superpowers/sdd/task-4-brief.md`.

The first eligible format is strict UTF-8 TXT only. All other formats and URL
ingestion remain `UNAVAILABLE` until their separate sandbox/corpus gates pass.

- [ ] **Checkpoint 4A: Disabled pure domain and provenance-v2 kernel**
- [ ] **Checkpoint 4B: Tenant-scoped PostgreSQL, outbox, and private storage**
- [ ] **Checkpoint 4C: Quarantine, scanner, and isolated TXT parser**
- [ ] **Checkpoint 4D: Immutable candidate review and readiness**
- [ ] **Checkpoint 4E: Close every legacy/raw-text downstream bypass**
- [ ] **Checkpoint 4F: Truthful deletion, operations, and TXT release evidence**

### Task 5: Implement the durable run domain state machine

**Implementation contract:** `.superpowers/sdd/task-5-brief.md`.

- [ ] **Checkpoint 5A: Exact 20-state run and nine-state attempt domain**
- [ ] **Checkpoint 5B: Atomic PostgreSQL commands, receipts, events, and outbox**
- [ ] **Checkpoint 5C: Leases, heartbeats, fencing, reaper, and ID-only workers**
- [ ] **Checkpoint 5D: Typed commands and cursor-based reconnect APIs**
- [ ] **Checkpoint 5E: No-dual-write legacy/UI cutover and report gate**

`VALIDATING_OUTPUT -> GENERATING_BRIEF` stays unavailable until Task 6 supplies
the exact approved path-set ID/hash, review ID/hash, and validator bundle.

### Task 6: Persist first-class paths and typed dependencies

**Implementation contract:** `.superpowers/sdd/task-6-brief.md`.

- [ ] **Checkpoint 6A: UUIDv7/public/semantic identity and rich pure domain**
- [ ] **Checkpoint 6B: Prove tenant/run/lease/schema prerequisites**
- [ ] **Checkpoint 6C: Add canonical schema and fenced repository write boundary**
- [ ] **Checkpoint 6D: Integrate the durable path stage**
- [ ] **Checkpoint 6E: Immutable review, exact-hash brief gate, and run APIs**
- [ ] **Checkpoint 6F: Preserve legacy reads without prose-to-path inference**

### Task 7: Add two-run semantic comparison

**Files:**
- Create: `backend/app/application/path_comparison_service.py`
- Create: `backend/app/api/routes/path_comparison_routes.py`
- Modify: `backend/app/api/routes/__init__.py`
- Test: `backend/tests/test_path_comparison_api.py`

**Interfaces:**
- Produces `POST /api/simulation/path-comparisons` with exactly two attempt IDs.
- Rejects non-completed attempts, mismatched decisions, missing semantic IDs,
  and three-or-more attempt inputs.
- Returns changed assumptions, shared path IDs, divergent path IDs, and
  validation-question changes without winner, rank, score, or recommendation.

- [ ] **Step 1: Test that three attempts return 422**
- [ ] **Step 2: Test that missing semantic IDs return 409**
- [ ] **Step 3: Implement stable-ID alignment**
- [ ] **Step 4: Pass comparison contract tests**

### Task 8: Build the first feature-flagged vertical UI slice

**Files:**
- Create: `frontend/src/config/features.js`
- Create: `frontend/src/api/decisionWorkspace.js`
- Create: `frontend/src/views/DecisionWorkspaceView.vue`
- Create: `frontend/src/components/decision-workspace/WorkspaceSpine.vue`
- Create: `frontend/src/components/decision-workspace/ReviewArena.vue`
- Create: `frontend/src/components/decision-workspace/RunArena.vue`
- Create: `frontend/src/components/decision-workspace/PathArena.vue`
- Create: `frontend/src/components/decision-workspace/RunRecord.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/assets/design-tokens.css`
- Test: `frontend/src/__tests__/decision-workspace-flag.spec.js`
- Test: `frontend/src/__tests__/decision-workspace-review.spec.js`

**Interfaces:**
- `isDecisionWorkspaceEnabled()` reads
  `VITE_DECISION_WORKSPACE_ENABLED === "true"`.
- New route: `/workspace/:projectId`; disabled flag redirects to the legacy
  `/process/:projectId` route.
- The Review slice consumes only the server manifest and source-review APIs.
- PathArena defaults to the semantic list; spatial rendering uses the same
  path objects and remains unavailable until canonical paths are ready.

- [ ] **Step 1: Test disabled-flag compatibility routing**
- [ ] **Step 2: Test enabled Review rendering from canonical manifest data**
- [ ] **Step 3: Implement the route and composition tokens**
- [ ] **Step 4: Implement Review only; render accurate unavailable states for later phases**
- [ ] **Step 5: Add keyboard, focus, 320px, 200% zoom, reduced-motion, and forced-color tests**
- [ ] **Step 6: Pass frontend tests, lint, and production build**

### Task 9: Enforce deferred-capability boundaries

**Files:**
- Modify: `docs/superpowers/specs/2026-08-08-decision-chamber-experience-design.md`
- Modify: `docs/design/CONTENT_SYSTEM.md`
- Test: `frontend/src/__tests__/decision-workspace-deferred-capabilities.spec.js`
- Test: `backend/tests/test_injection_deprecation.py`

**Interfaces:**
- Primary UI offers `Duplicate with this condition`; it does not expose live
  intervention.
- External evidence import, owner conclusions, playback, multi-user review,
  calibrated duration estimates, and portfolio analytics remain unavailable.
- Existing injection route is explicitly deprecated and unavailable from the
  new workspace UI until a future durable intervention ADR is accepted.

- [ ] **Step 1: Test that deferred controls are absent from the feature-flagged UI**
- [ ] **Step 2: Test that duration is `estimate unavailable` unless server-issued**
- [ ] **Step 3: Document the release boundary and compatibility behavior**
- [ ] **Step 4: Run full verification**

  Run: `npm run verify`

  Expected: all backend tests, frontend tests, docs validation, truth lint,
  frontend build, and touched-file lint checks pass.

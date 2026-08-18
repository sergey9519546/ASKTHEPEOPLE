# ULTRAPLAN — Remediation & Hardening of ASKTHEPEOPLE

**Author:** Audit follow-up (research-grade audit of this repo)
**Date:** 2026-08-18
**Scope:** Fix and improve every finding in the audit that needs action.
**Guiding principle:** Keep the tool honest by making the *synthetic* path less
convenient than the *real-validation* path, localizing data, and binding the
disclosure to the artifact instead of to a banner.

This plan is organized into workstreams A-E by priority. Each item has:
Problem -> Evidence -> Fix -> Files -> Acceptance -> Verification.

> The audit concluded the codebase is *already* unusually disciplined about its
> truth-contract. This plan does not "add more disclaimers." It attacks the
> structural gaps where the system *functions* as a public-opinion substitute
> despite its banners: the neutral-clamp asymmetry, the dormant calibration
> switch, the friction asymmetry, the Zep egress, the croppable disclosure, and
> the missing canonical docs the README links to.

---

## Execution order (do in this sequence)

1. A - Documentation integrity (blocks trust; quick; unblocks validator/CI)
2. B - Epistemic integrity (the core findings)
3. C - Data & egress control
4. (Optional, tracked) D - Power-asymmetry transparency and E - scaling/governance

Do not start B3 (report reframe) until A and B1/B2 land, because B3 changes the
user-facing contract and must ride on a clean doc baseline.

---

## WORKSTREAM A - Documentation integrity (P0, quick)

### A1. Restore the canonical docs/product/ truth-contract files
- Problem: README.md (lines 260-264) and docs/README.md (lines 152-156) link to
  docs/product/PRODUCT_TRUTH_CONTRACT.md, METHODOLOGY.md, USE_POLICY.md,
  TERMINOLOGY.md, SUCCESS_METRICS.md - but docs/product/ does NOT exist in the
  current tree (only docs/archive/legacy-2026-07-29/ holds older copies). The doc
  system references files it does not contain; links 404 and the validator's
  "48 modular documents" claim is unverifiable.
- Evidence: Test-Path docs/product -> False; archive has
  legacy-2026-07-29/METHODOLOGY.md, APPROPRIATE_USE.md, VALIDATE_WITH_PEOPLE.md.
- Fix: Create docs/product/ with the five canonical files, each carrying the
  required front-matter (title, status, version, owner, last_reviewed,
  review_cycle, research_cutoff, plus a "Project-specific implementation status"
  section grounded in current code). Seed content from the corresponding
  archive/legacy-2026-07-29/ files where they exist, and from README.md "Read
  every output correctly" / "Do not use it for" sections where they do not. If a
  file is intentionally retired, delete the link from README.md and
  docs/README.md instead of creating a stub.
- Files: docs/product/PRODUCT_TRUTH_CONTRACT.md, METHODOLOGY.md, USE_POLICY.md,
  TERMINOLOGY.md, SUCCESS_METRICS.md; README.md; docs/README.md.
- Acceptance: Every docs/product/* link in README.md and docs/README.md resolves;
  python tools/validate_docs.py reports PASS with the expected document count and
  0 warnings.
- Verification: python tools/validate_docs.py; manual click-through of every
  product doc link from README.md.

### A2. Define success metrics that cannot be gamed toward realism
- Fix: Add docs/product/SUCCESS_METRICS.md defining success for the *honest*
  version (e.g., "number of pre-registered real-validation plans generated",
  "reproducibility-manifest completeness", "divergence of synthetic vs. human
  findings recorded") so the product is not silently optimized for engagement or
  realism. Reference the audit's section 11.
- Files: docs/product/SUCCESS_METRICS.md.
- Acceptance: Success metrics explicitly EXCLUDE realism, engagement, and user
  count as goals; they include pre-registered validation plans and reproducibility
  manifest completeness.

---

## WORKSTREAM B - Epistemic integrity (P0/P1, the core)

### B1. Close the neutral-stance clamp asymmetry
- Problem: The deterministic decision_lens path and trait_behavior_projection
  clamp agents to neutral (stance="neutral", sentiment_bias=0.0); the LLM-driven
  generate_config path does NOT - it lets the model propose opinionated
  stance/sentiment_bias/reaction_style from source text (subagent finding;
  simulation_config_generator.py _generate_agent_configs_batch vs
  generate_from_decision_lenses at lines 552-553). This is the exact "model
  smuggles non-neutral stances" fragility from audit section 3(6).
- Fix: Apply the same neutral-default + source-grounded override rule to the LLM
  config path. Default every LLM-proposed agent to
  control_assumption_basis="neutral_fictional_default" AND clamp
  sentiment_bias=0.0 / stance="neutral" unless the value is span-verified via
  trait_inference.verify_trait_claims (the same mechanical check used elsewhere).
  If a proposed stance has no verified source span, drop to neutral - never keep
  an ungrounded opinionated stance.
- Files: backend/app/services/simulation_config_generator.py,
  backend/app/services/trait_inference.py (reuse verify_trait_claims),
  backend/tests/test_simulation_config_generator.py.
- Acceptance: A unit test feeds source text that implies a stance but supplies no
  verbatim span -> agent stays neutral. A test with a verified span -> stance
  allowed and recorded with provenance.
- Verification: cd backend && .\.venv\Scripts\pytest -q tests/test_simulation_config_generator.py

### B2. Quarantine or honestly wire calibration_metrics.py
- Problem: backend/app/services/calibration_metrics.py implements real
  brier_score, auc_roc, expected_calibration_error but is imported ONLY by its own
  tests - never by production (subagent finding). A dormant "we can show you
  likelihoods" switch is a latent risk: a future change could wire it to
  self-generated outcomes and emit a misleading "calibrated" label,
  contradicting the report's "NOT CALIBRATED" claim.
- Fix (recommended - quarantine with honest intent): Keep the module but gate it
  behind CALIBRATION_MODULE_MODE in {disabled, validation_delta}.
  - disabled (default): module unreachable from any report/export path; import is
    lazy and guarded; any production call raises CalibrationNotPermitted.
  - validation_delta: the ONLY allowed use - compare a completed synthetic run
    against a SEPARATELY supplied human study and emit a divergence report
    (sim != human), never a "likelihood." Forbid any path that compares the sim
    to itself or to model output.
  - Hard guard: no production code may attach a calibration score to a
    synthetic-only run.
- Files: backend/app/services/calibration_metrics.py,
  backend/app/services/report_agent.py (ensure no import),
  backend/app/config.py (env flag), backend/tests/test_calibration_metrics.py.
- Acceptance: Grep confirms calibration_metrics appears in production only behind
  the flag; default build cannot emit a calibration number on a synthetic run. A
  test asserts validation_delta requires an external human dataset argument.
- Verification: grep -rn "calibration_metrics" backend/app --include=*.py shows no
  unguarded production import; pytest passes.

### B3. Invert the friction asymmetry + reframe the report as a divergence ledger
(P1 - the most important structural fix; do after A lands.)
- Problem: Generating the sim is one click; actually validating with people is an
  expensive external process the product does not perform (README.md lines
  94-97, "Validate with People" is a handoff button to a nonexistent recruitment
  step). The friction is dumped on the honest path.
- Fix (three coordinated changes):
  1. Pre-registration: Before a run starts, require a one-field "real-validation
     plan" (what human sample / method / instrument you will use to test this
     scenario). Store it with the project (models/project.py). Surface it on every
     report and export, adjacent to - not below - the disclosure.
  2. Report -> divergence ledger: Retitle report_agent.py output from a
     findings/recommendations report to a divergence ledger: inputs, assumptions,
     model+version+seed, persona-mix, and an explicit list of
     scenarios-to-test-with-real-people. Keep the valuable "include paths that
     weaken your plan" instruction (report_agent.py:639) - promote it to the top.
  3. Kill the authority-of-form: Remove the standalone "recommendations" narrative
     tail (report_agent.py:1003); replace with "hypotheses for validation." No
     prose that reads as "what people think."
- Files: backend/app/services/report_agent.py,
  backend/app/api/routes/prep_routes.py, backend/app/models/project.py,
  frontend/src/components/Step4Report.vue, frontend/src/views/ReportView.vue,
  docs/product/METHODOLOGY.md (update method to "pre-registered divergence").
- Acceptance: A run cannot be created without a validation-plan field; the report
  contains no "recommendations" section and leads with "test these with people";
  the pre-registration block appears on every export.
- Verification: UI flow test (create run -> validation-plan required); pytest on
  report_agent asserting no recommendations key and presence of validation_plan +
  hypotheses.

---

## WORKSTREAM C - Data & egress control (P1)

### C1. Make Zep Cloud egress opt-in per run, with an egress log
- Problem: Generated episodes and graph data are sent to Zep Cloud
  (zep_graph_memory_updater.py, zep_live_canary.py); the canary is fictional and
  has no HTTP surface (good), but normal runs still egress content to a
  third-party store with no per-run operator consent and no log of what left the
  machine (audit section 8 "extractive", section 5 privacy gap).
- Fix: Gate every Zep write behind an explicit per-run egress_consent flag
  defaulting to FALSE. When false, the updater is a no-op and logs "egress
  disabled." When true, append a line to an egress_log.jsonl (timestamp, run id,
  record count, destination) that the operator can export. Keep zep_live_canary
  fictional-only and off by default.
- Files: backend/app/services/zep_graph_memory_updater.py,
  backend/app/services/zep_live_canary.py, backend/app/config.py (default off),
  backend/app/services/simulation_artifacts.py (log writer).
- Acceptance: Default run sends nothing to Zep; enabling requires an explicit flag
  at run creation; every egress event is logged and exportable.
- Verification: pytest asserts no network call when egress_consent=false; log line
  present when true (mock transport).

### C2. Bind the disclosure to the artifact (non-croppable)
- Problem: Disclosures live in UI banners and PDF/CSV footers
  (export_service.py lines 117-122, 227-305) but a copy-pasted quote or cropped
  screenshot carries no disclosure (audit section 6 "audience cannot leave").
- Fix: Every export gets an immutable provenance block: a hash of (run id + model
  + seed + disclosure text) plus a verifier reference (local CLI
  tools/verify_export.py --hash <hash> for AGPL/local, or a /verify route for
  hosted). The disclosure text becomes part of the artifact's content hash, so
  removing it invalidates verification. Provide GET /api/export/verify.
- Files: backend/app/services/export_service.py,
  backend/app/api/routes/export_routes.py (add verify route),
  backend/app/services/claim_boundary.py (single source of disclosure string),
  tools/verify_export.py.
- Acceptance: A recipient verifying the hash sees the run's model/seed/disclosure;
  a screenshot missing the block has no valid verifier.
- Verification: pytest on export -> verifier round-trip; tamper test fails.

---

## WORKSTREAM D - Power-asymmetry transparency (P2, optional but high-value)

### D1. Expose generation provenance to output recipients
- Problem: The operator can inspect prompt/model/seed; the audience of an exported
  output cannot (audit section 6, section 10 "unthinkable" - invisible weights).
- Fix: Add GET /api/simulation/<id>/provenance returning the exact
  prompt-template ids, model+version, temperature, seed, and the per-persona
  sampling draws (big_five.sample_population RNG state where feasible). The
  report/export includes a "how this was generated" panel linking to it.
- Files: backend/app/api/routes/read_routes.py (add provenance route),
  backend/app/services/simulation_config_generator.py (emit provenance dict),
  frontend/src/components/Step4Report.vue.
- Acceptance: Anyone with a run id (or the verifier hash) can retrieve the
  generative provenance for any quote in the output.
- Verification: pytest on the route; UI panel renders.

---

## WORKSTREAM E - Scaling / governance (track, do not block)

### E1. Multi-tenant isolation - keep fail-closed, track TARGET
- Status: Currently 503 tenant_context_unavailable / dev stub (source_routes.py,
  authorization.py RBAC unwired). This is the SAFE failure mode, not a bug. Do NOT
  "fix" by enabling a stub resolver.
- Action: Keep fail-closed; advance per adr/ADR-0009-multi-tenant-isolation.md and
  docs/exec-plans/02-tenancy-data-and-secure-ingestion.md. Add a CI check that the
  503 path is preserved until the resolver lands.
- Files: backend/app/api/routes/source_routes.py,
  backend/app/domain/authorization.py.

### E2. Process-local runner scaling - track per ADR-0003
- Status: SimulationRunner is process-local (architecture/index.md lines
  396-402). Horizontal scaling blocked. Tracked by
  adr/ADR-0003-durable-run-orchestration.md and gate 2. Not a correctness bug;
  note as capacity risk in runbook.

---

## Definition of done

- [ ] A1/A2: python tools/validate_docs.py -> PASS, 0 warnings; all product doc
      links resolve.
- [ ] B1: LLM config path clamps to neutral without verified source span; tests
      green.
- [ ] B2: calibration_metrics unreachable in default build; guarded
      validation_delta only.
- [ ] B3: runs require a validation plan; report is a divergence ledger; no
      "recommendations" prose.
- [ ] C1: Zep egress opt-in + logged; default off.
- [ ] C2: exports carry a verifiable, non-croppable disclosure hash.
- [ ] D1 (if in scope): provenance route + panel shipped.
- [ ] Full check: cd backend && .\.venv\Scripts\pytest -q passes; npm run verify
      passes.

## Risks & tradeoffs

- B3 is the highest-leverage and highest-resistance change. It reduces the
  product's market appeal (less "insight," more "here's what to test"). That is
  the point. If the project later monetizes, B3 is the first thing a PM will
  strip - which is exactly why it must be enforced in code and docs now.
- C2 verifier: for a local/AGPL deploy, ship the verifier as a local CLI
  (tools/verify_export.py --hash ...) so it does not depend on hosting.
- A1 must not become "write more disclaimer copy." The goal is resolving broken
  links and grounding claims in code, not multiplying warnings.

## What this plan deliberately does NOT do

- It does NOT add more banners. The disclosure is already persistent
  (TruthRail.vue, masthead/footer on every view). More text would be cosmetic.
- It does NOT attempt to make the simulation "more accurate" - accuracy is not
  the claim and not achievable without real-human calibration (which B2 forbids
  faking).
- It does NOT change the AGPL/open-source business model; every fix is
  economically plausible for a free research tool.

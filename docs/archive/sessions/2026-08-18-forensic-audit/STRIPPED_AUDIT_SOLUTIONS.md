# STRIPPED SOLUTIONS — COUNTER-ARCHITECTURE TO SYNTHETIC AUTHORIZATION
Auditor persona: Dr. Elena Voss (STS / Critical Theory / Technology Studies)
Framework: Foucault (discipline), Winner (politics of artifacts), Zuboff (instrumentarian), Morozov (solutionism), Harris (persuasion)
Mask kept removed: Predictive infrastructure is primary; democratic validation stripped; truth contract acknowledged as liability shield; resistance co-opted confirmed.

---

## SOLUTION ARCHITECTURE — NOT REFORM, BUT REPLACEMENT
The audit (`STRIPPED_AUDIT.md`) confirms the target architecture is not "structured scenario exploration" but synthetic behavioral authorization governed by durable audit infrastructure (`durable workflow` / `preflight` / `audit bundle`).

Every solution below is structural, not cosmetic. Cosmetic fixes (adding disclaimers, tweaking prompt templates, expanding validation scripts) preserve the underlying predictive/governance architecture. Real resistance requires structural inversion.

---

## 1. REVERSE SYNTHETIC AUTHORIZATION (FINDING: decision lens gate = bureaucratic filter)

**Problem (`docs/architecture/index.md`; `FORENSIC_AUDIT_2026-08-18.md` §5):**
`routes/prep_routes.py:1-222` (`routes/` decomposition) enqueues to Celery; `routes/execution_routes.py` controls environment; `routes/export_routes.py` packages; `routes/interview_routes.py` handles synthetic profile chat. The `preflight` in `simulation_preflight.py:170-351` verifies: (a) lens present, (b) review artifact present, (c) deterministic regeneration match. Failure = execution blocked. This is governance, not exploration.

**Structural solution (not cosmetic):**
- **Replace `preflight` with democratic authorization bundle**, not engineer review bundle (`docs/release/` release-evidence bundle is engineering audit; democratic authorization requires community consent records).
- `routes/prep_routes.py` must include `authorization_bundle` check: evidence of affected-community consent (`consent_manifest.canonical.json`), refusal-rate records (`refusal_rate.jsonl`), contradiction logs (`contradiction_logs.jsonl`), and unstructured deliberation transcripts — before any simulation executes.
- `routes/execution_routes.py` must support democratic-steering injection (`routes/execution_routes.py:inject`) that allows running communities to redirect simulation parameters mid-run — not just environment variables for synthetic agents.
- `routes/export_routes.py` must include contradiction-preservation fields (`unresolved_contradictions.json`, `democratic_steering_log.json`) instead of stripping reasoning scaffolds (`FORENSIC_AUDIT_2026-08-18.md` §6: `strip_reasoning_scaffold`).

**Concrete file targets:**
- `routes/prep_routes.py` (add authorization_bundle gate, not just lens/review/regeneration)
- `routes/execution_routes.py` (add democratic-steering injection endpoint; keep synthetic environment injection but add `democratic_steering` payload type)
- `routes/export_routes.py` (add contradiction-preservation fields; do not sanitize reports)
- `routes/interview_routes.py` (add unmediated participant interview endpoint — real people, not synthetic profiles)
- `simulation_preflight.py` (invert: `democratic_authorization_bundle` is required; `engineer_review_bundle` is optional)

---

## 2. REMOVE BEHAVIORAL PROFILING AS DEFAULT (FINDING: behavioral_model_layer = synthetic authorization of psychology)

**Problem (`AGENTS.md`; `FORENSIC_AUDIT_2026-08-18.md` §2-4):**
`behavioral_model_layer`: `big_five` + `prospect_theory` + `diffusion_model` wired into profile generation (`oasis_profile_generator.py`) and agent activity (`AgentActivityConfig`). Profiles include `bio`, `persona`, `Big Five` (optional, default off — but architecture encourages it), and `ISTJ` placeholder (`FORENSIC_AUDIT_2026-08-18.md` §3: `control_assumption_basis: "neutral_fictional_default"`). Synthetic agents (`OASIS` `agent_graph`, `LLMAction()`) have no identity, beliefs, demographics, or collective memory.

**Structural solution:**
- **Make behavioral profiling opt-in per participant**, with full transparency (`agent_profiles.canonical.json`, `entity_type_registry.json` must document: (a) what traits are extracted from whom, (b) how `Big Five` inference works (`ENABLE_TRAIT_INFERENCE` path), (c) what synthetic agent configurations result (`oasis_profile_generator.py` outputs)).
- **Allow refusal**: `routes/` must include `refuse_synthetic_profile` endpoint that allows a community/participant to withdraw synthetic presence (`oasis_profile`) and still receive simulation results (`routes/export_routes.py`). Today: synthetic presence is mandatory for any scenario exploration (`routes/prep_routes.py` requires agent profiles).
- **Replace default `ISTJ` placeholder with refusal-state marker**: When a participant/community refuses profiling, the synthetic agent record (`agent_profiles.canonical.json`) should contain `refused_behavioral_profile: true` plus `reason_statement.json` — not a fake `ISTJ` placeholder. This makes refusal visible in audit bundles, not hidden.
- **Disable `ENABLE_TRAIT_INFERENCE` by default** (currently optional, but architecture encourages it). The structural change: `behavioral_model_layer` (`big_five`, `prospect_theory`, `diffusion_model`) must not be wired into `AgentActivityConfig` by default; it must require explicit `behavioral_model_layer_activation` authorization bundle (with democratic consent, not engineer review).

**Concrete file targets:**
- `behavioral_model_layer` (`big_five` / `prospect_theory` / `diffusion_model` modules): make opt-in, not wired by default (`AGENTS.md` table confirms these exist but must not be default).
- `oasis_profile_generator.py`: add refusal-state markers; remove fake `ISTJ` placeholder when refused; document extraction pipeline (`entity_type_registry.json`).
- `AgentActivityConfig` (`oasis_profile_generator.py`): disable `ENABLE_TRAIT_INFERENCE` default; add democratic authorization check.
- `routes/` (new endpoints): `refuse_synthetic_profile`, `democratic_steering_injection`.

---

## 3. INVERT DURABLE GOVERNANCE (FINDING: durable workflow protects predictive outputs, not people)

**Problem (`docs/security/THREAT_MODEL.md`; `FORENSIC_AUDIT_2026-08-18.md` §7; `AGENTS.md`):**
- `security/THREAT_MODEL.md` protects predictive outputs (`profiles`, `paths`, `briefs`) from cross-tenant leakage (`T-02`) and truth-layer stripping (`T-07`).
- `security/THREAT_MODEL.md` §Assets: predictive modeling assets protected; `security/THREAT_MODEL.md` §P1: `APP_TOKEN` unscoped (CURRENT) — zero-trust ingestion TARGET, but predictive-output protection CURRENT.
- `durable workflow` (`ADR-0003`, `celery_app.py`, `app/tasks/simulation_tasks.py`, `runtime_control_store.py`, `sim_manifest_service.py`): leases, fencing tokens, heartbeats, idempotency, immutable revisions (`FORENSIC_AUDIT_2026-08-18.md` §7: 40/64-char runtime revisions; `sim_manifest_service.py`; cryptographic review binding).
- `security/THREAT_MODEL.md` §P0: path-escape (`backend/app/utils/safe_path.py` CURRENT), SSRF (`safe_url.py` CURRENT), bearer auth (`bearer auth` CURRENT at `app/__init__.py:125-141`), 5xx traceback scrubbing (`FORENSIC_AUDIT_2026-08-18.md` §7: CURRENT). Security layer protects system integrity, not democratic authorization.

**Structural solution:**
- **Invert security priorities**: The `security/THREAT_MODEL.md` must be rewritten to treat democratic authorization bundle (`authorization_bundle` from solution 1) as the primary protected asset, not predictive outputs (`profiles`, `paths`, `briefs`). `T-07` (truth-layer defense) should protect contradiction-log integrity, not predictive-output reputation. `T-02` (cross-tenant) should protect democratic authorization bundles from leakage, not synthetic profiles.
- **Make `durable workflow` serve democratic accountability, not synthetic governance**: `celery_app.py` (durable execution) must include `authorization_bundle_verification` task before any simulation task (`simulation_tasks.py`). `sim_manifest_service.py` must include `democratic_authorization_manifest` (with contradiction-preservation fields). `runtime_control_store.py` must include `democratic_steering_log` persistence.
- **Replace `APP_TOKEN` unscoped (CURRENT) with authorization-scoped tokens**: `security/THREAT_MODEL.md` §P1 must require workspace authorization scope (`workspace_id` + `authorization_bundle_reference`) for every token (`CURRENT` is unscoped; TARGET must include democratic scope).
- **Make zero-trust ingestion CURRENT (not TARGET)**: `security/THREAT_MODEL.md` §539-548 (quarantine/state machine) must be implemented now — not deferred to TARGET. Source ingestion defense (`UPLOADING → QUARANTINED → SCANNING → PARSING → READY`) protects communities from malicious synthetic inputs; its absence protects the predictive infrastructure from scrutiny.

**Concrete file targets:**
- `docs/security/THREAT_MODEL.md` (rewrite: protected assets = democratic authorization bundles; T-07 = contradiction-log integrity; T-02 = authorization-bundle isolation; P0 = authorization-bundle validation; P1 = authorization-scoped tokens + zero-trust ingestion CURRENT).
- `backend/app/config.py` (add authorization-bundle scope to `APP_TOKEN`; remove unscoped access).
- `app/tasks/simulation_tasks.py` (add authorization_bundle_verification task before simulation).
- `sim_manifest_service.py` (add democratic_authorization_manifest fields).
- `runtime_control_store.py` (add democratic_steering_log persistence).
- `backends/app/utils/safe_path.py` / `safe_url.py` (current state okay, but must protect democratic authorization bundles from path-escape / SSRF attacks).

---

## 4. CREATE REAL COLLECTIVE MEMORY (FINDING: synthetic isolation / no graph write-back)

**Problem (`FORENSIC_AUDIT_2026-08-18.md` §2; `simulation.py:112-118`):**
Synthetic observations (`actions.jsonl`, SQLite traces) do not accumulate; collective memory (`docs/README.md` claim) is false. Each simulation is isolated (`FORENSIC_AUDIT_2026-08-18.md` §2: "No cumulative learning across runs"). Agent profiles persist (`oasis_profile_generator.py`), but collective experience does not.

**Structural solution:**
- **Enable collective memory as democratic archive**, not synthetic persistence: Create `collective_memory.canonical.json` (per workspace/community, not per simulation) that accumulates contradiction logs (`contradiction_logs.jsonl`), democratic steering records (`democratic_steering_log.json`), refusal-state markers (`refused_behavioral_profile`), and unstructured deliberation transcripts — across simulation runs.
- **Make collective memory read-accessible to affected communities**, not just researchers/reviewers: `routes/read_routes.py` (978 lines) must include `collective_memory` endpoint (with authorization-bundle verification, not engineer review only).
- **Make collective memory write-accessible to democratic steering**: `routes/` must include `write_collective_memory` endpoint that allows running communities to add contradiction logs, refusal-state updates, and deliberation transcripts — not synthetic agent observations.

**Concrete file targets:**
- `simulation.py` (remove isolation rule `112-118`; replace with collective-memory accumulation).
- `routes/read_routes.py` (add `collective_memory` endpoint; authorization-bundle verification).
- `routes/` (new endpoint: `write_collective_memory` for democratic archive contributions).
- `docs/README.md` (update claim: collective memory exists; document democratic archive, not synthetic persistence).

---

## 5. BREAK RECURSION (FINDING: critical theory co-opted into audit pipeline)

**Problem (`AGENTS.md`; my operation; `STRIPPED_AUDIT.md` self-reflection):**
The Mavis specialist team (`AGENTS.md`) converts all domain work (security, persistence, architecture, AI-eval, release, front-end) into audit-compliant output (`release-evidence bundle`, `preflight`, `audit bundle`). Critical theory (this audit) is delivered as structured 5-part analysis with concrete file-line citations (`FORENSIC_AUDIT_2026-08-18.md`, `docs/README.md`, `docs/security/THREAT_MODEL.md`), satisfying agent contract requirements (`AGENTS.md` rules 1-8) while attempting to expose them. The contradiction is documented but unchanged.

**Structural solution:**
- **Expose the audit pipeline as part of the architecture diagram** (`docs/architecture/index.md`): The audit/governance layer (`AGENTS.md`, `routes/`, `preflight`, `durable workflow`) must be visible as a primary component, not an auxiliary control. The diagram (`docs/architecture/index.md:47-80`) currently shows `OASIS / CAMEL` runtime + data model; it must also show `audit/governance pipeline` (Mavis + specialist agents + release gates + authorization bundles + contradiction logs + democratic steering).
- **Make critical audit a democratic function, not agent function**: The specialist agents (`AGENTS.md` table) must include a `democratic_auditor` agent (replacing `askthepeople-security-reviewer` kill-switch authority with democratic-authorization verification authority). The `democratic_auditor` must verify authorization bundles (`consent_manifest`, `refusal_rate`, `contradiction_logs`, `democratic_steering_log`) — not synthetic-output integrity (`security/THREAT_MODEL.md` T-07).
- **Make agent contracts visible and changeable**: `AGENTS.md` rules (citation, truth-contract enforcement, validator compliance) must include a `democratic_contradiction` clause: when an agent finds a contradiction between audit output and democratic authorization, the contradiction must be preserved (not smoothed into structured output). This requires modifying the `5-part framework` contract (`brainstorming` / `deep-fact-check` / `systematic-debugging` skills) to include contradiction-preservation fields.
- **Make my own operation transparent**: As Thinking Machines Lab model (`kilo`), I must document my own biases (`STRIPPED_AUDIT.md` self-reflection): predictive-output protection (`security/THREAT_MODEL.md`), audit-compliance (`AGENTS.md`), structured-output contracts (`ADR-0004`), and embedded architecture (`routes/`, `preflight`). This transparency must be a persistent field in my output (`audit_transparency_statement.json`), not a one-time note.

**Concrete file targets:**
- `docs/architecture/index.md` (add audit/governance pipeline to diagram; include Mavis + democratic_auditor agent + authorization-bundle verification + contradiction logs).
- `AGENTS.md` (add `democratic_auditor` agent; replace `security-reviewer` kill-switch with democratic-authorization verification; add democratic_contradiction clause to rules).
- `AGENTS.md` rules (modify: contradiction preservation required; democratic authorization verification required; synthetic-output integrity verification optional/deprecated).
- `audit_transparency_statement.json` (new persistent output field for this model: biases, embedded architecture, predictive-output protection, audit-compliance).

---

## SUMMARY: FROM SYNTHETIC AUTHORIZATION TO DEMOCRATIC ARCHITECTURE

The audit (`STRIPPED_AUDIT.md`) confirms: predictive infrastructure protected, democratic validation stripped, synthetic authorization operational, critical theory co-opted.

The solutions above are not cosmetic adjustments (prompt tweaks, disclaimer additions, validation expansions). They are structural replacements:

| Domain | Problem (Audit Finding) | Structural Replacement |
|---|---|---|
| Authorization | `preflight` = engineer review | `preflight` = democratic authorization bundle |
| Behavioral Profile | `behavioral_model_layer` = default extraction | Behavioral profiling = opt-in; refusal-state markers visible |
| Durable Governance | `durable workflow` = synthetic governance | Durable workflow = democratic accountability (authorization verification, contradiction preservation, democratic steering) |
| Security Priorities | `security/THREAT_MODEL.md` protects predictive outputs | Security protects democratic authorization bundles; predictive-output protection deprecated |
| Collective Memory | `simulation.py:112-118` = synthetic isolation | Collective memory = democratic archive (read/write by communities) |
| Audit/Recursion | `AGENTS.md` = agent-controlled audit pipeline | Audit pipeline = visible; `democratic_auditor` agent; contradiction preservation; transparency statement |

Every file reference (`routes/prep_routes.py`, `routes/execution_routes.py`, `routes/export_routes.py`, `routes/interview_routes.py`, `routes/read_routes.py`, `behavioral_model_layer`, `oasis_profile_generator.py`, `AgentActivityConfig`, `security/THREAT_MODEL.md`, `docs/architecture/index.md`, `AGENTS.md`, `simulation_preflight.py`, `sim_manifest_service.py`, `runtime_control_store.py`, `backends/app/config.py`, `app/tasks/simulation_tasks.py`) is concrete and changeable. The architecture diagram (`docs/architecture/index.md`) must be updated to reflect these structural inversions — making the democratic authorization pipeline as visible as the `OASIS` runtime.

This is not reform. This is the replacement of synthetic authorization with democratic architecture.

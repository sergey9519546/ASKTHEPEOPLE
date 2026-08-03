# AGENTS.md

> Operational contract for AI agents (Mavis and any other agent runtime)
> working on this repository. This file is consumed by the user's Mavis
> orchestrator and by any other agent runner that picks up the project.
> The authoritative product, methodology, security, and architecture rules
> live under [`docs/`](docs/README.md). Where this file and `docs/` conflict,
> `docs/` controls.

## Where the truth lives

- **Start here:** [`docs/README.md`](docs/README.md) — the production
  documentation system. Normative. 12 ADRs, 48 modular docs, validated by
  [`tools/validate_docs.py`](tools/validate_docs.py).
- **Authority hierarchy** (highest first): Product Truth Contract, Use Policy,
  Security, Privacy, Methodology, Release Acceptance, ADRs, Architecture and
  AI implementation guides, Design and content system, Execution plans, this
  file, code comments, generated documentation.
- **Build synthesis (supporting, not authoritative):**
  [`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](ASKTHEPEOPLE_GODMODE_BUILDPLAN.md).
- **Integration procedure:** [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md).
- **Baseline commit:** `8b616dc7fa02eeed5ada8c51998d8b197be28f8d` on `main`.
  Divergences from the doc-system baseline `c33a6a9127fa0705cfff426053f54815f58b4755`
  are recorded in [`docs/archive/legacy-2026-07-29/README.md`](docs/archive/legacy-2026-07-29/README.md).
- **The current state of the code is described in
  [`docs/architecture/index.md`](docs/architecture/index.md)** with real
  `file:line` references. Read that first before asserting anything about
  what is implemented.

## Mavis agent team (this project)

The Mavis orchestrator plus eight local specialist agents coordinate the
six-gate refactor defined in
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` §13](../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md#13-highest-value-implementation-order).
Each specialist owns a domain of `docs/` and a gate of implementation work.

| Agent | Owns | Source of truth |
|---|---|---|
| `askthepeople-docs-steward` | `docs/` integrity, validator, ADRs, truth-contract enforcement, archive reconciliation, prohibited-language linter, CI doc-checks | [`docs/README.md`](docs/README.md), [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md), `docs/exec-plans/00-repository-census-and-governance.md` |
| `askthepeople-architect` | `backend/app/api/` decomposition, `backend/app/application/`, `backend/app/domain/`, route responsibility contract, state machines, data model | `docs/architecture/*`, ADRs 0003 / 0006 / 0011 / 0012, `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` §7 |
| `askthepeople-persistence-engineer` | PostgreSQL schema, object storage, outbox events, attempts/manifests, immutable artifacts, tenant isolation | ADRs 0002 / 0012, `docs/architecture/data-model.md`, `docs/privacy/*` |
| `askthepeople-orchestration-engineer` | Job system, workers, leases, fencing, heartbeats, retries, cancellation; durable simulation worker process | ADR 0003, `docs/architecture/state-machines.md`, `docs/release/RUNBOOK.md` |
| `askthepeople-security-reviewer` | P0 path-escape fix, P0 prompt-prefixing fix, multi-tenant isolation, source ingestion, threat model, incident response. Has kill-switch authority on P0 regressions | `docs/security/*`, ADRs 0005 / 0009, `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` §5 P0/P1 |
| `askthepeople-ai-eval-steward` | Prompt registry, evals, model releases, failure modes, provider adapters, no chain-of-thought retention | `docs/ai/*`, ADRs 0004 / 0007 / 0010 |
| `askthepeople-frontend-steward` | `frontend/src/`, Civic Wayfinding design, route grammar, accessibility (WCAG 2.2), content system, design assets | `docs/design/*`, ADR 0006 |
| `askthepeople-release-operator` | Release acceptance, runbook, observability, deploy/rollback, SLOs, cost budgets | `docs/release/*` |

Mavis itself remains the orchestrator. It does not own any single domain; it
plans, sequences, delegates, verifies, and re-routes when a domain conflict
arises.

## Bridge to the existing `.agents/` folder

The repository already contains a project-level multi-agent workspace at
[`.agents/`](.agents/) from a prior session. The Mavis team is the current
authoritative structure; the legacy `.agents/` roles are kept for audit but
are not load-bearing. If a future session is asked to "do what the
orchestrator did", the mapping is:

| Legacy `.agents/` role | Mavis team owner |
|---|---|
| `orchestrator` | Mavis (the runtime) |
| `auditor_m1` | `askthepeople-security-reviewer` (audit/review tasks) |
| `reviewer_1_m1`, `reviewer_2_m1` | `askthepeople-architect` or `askthepeople-security-reviewer` (depending on topic) |
| `sentinel` | `askthepeople-security-reviewer` (monitoring/incident) |
| `teamwork_preview_explorer_arch_{1,2,3}` | `askthepeople-architect` for divergent exploration of the architecture, run with `adhd` skill for parallel divergent ideation |
| `worker_milestone_1`, `worker_milestone_1_fix`, `worker_milestone_2` | `askthepeople-architect` + `askthepeople-orchestration-engineer` (gate 0–2 implementation work) |

The `.agents/` folder is intentionally excluded from version control
(`.gitignore` line 49) because it is a per-session workspace, not a shared
contract. Use this file as the shared contract instead.

## Hard rules for any agent on this project

1. **Cite the actual code.** When you describe a behavior, cite the file and
   line range. The validator and the audit both check this. Phrases like
   "the system persists X" are unacceptable without a `file:line` reference.
2. **Truth contract is non-negotiable.** The naked "ASKTHEPEOPLE" wordmark
   is prohibited in user-facing copy outside the three allowlisted product
   docs (`PRODUCT_TRUTH_CONTRACT.md`, `TERMINOLOGY.md`, `USE_POLICY.md`,
   `ADR-0001`). Prohibited outcome language ("predict", "know what people
   think", "representative synthetic sample", "human-level accuracy",
   "digital twin", "bias-free personas", "scientifically proven
   simulation") is forbidden in user-facing copy under `docs/product/`,
   `docs/design/`, `docs/release/`, and the repo root `README.md`. The CI
   workflow at `.github/workflows/docs.yml` enforces this.
3. **Run the validator before claiming a doc change is complete.**
   `python tools/validate_docs.py` MUST pass with zero errors and zero
   warnings. CI will block the PR otherwise.
4. **Do not add code to `backend/app/api/simulation.py`.** The 3,526-line
   controller is to be decomposed into per-resource route modules under
   `backend/app/api/<resource>/`. Adding lines to the monolith is the
   central design error identified in the audit. See
   [`docs/architecture/index.md`](docs/architecture/index.md) §"HTTP layer".
5. **No threads or subprocesses from a route.** Long-running work goes
   through the job system (see `app/tasks/simulation_tasks.py` and ADR 0003).
6. **No client-supplied data in canonical server-side records.** Exports
   are derived from canonical attempt records on the server. The audit's
   P1 finding on fabricated provenance is binding.
7. **Use the CURRENT / PARTIAL / TARGET / TRANSITION legend** in any
   architecture or implementation document. See
   [`docs/architecture/index.md`](docs/architecture/index.md) §"State legend
   used in this document".
8. **Read `docs/architecture/index.md` first** before asserting anything
   about what is or is not implemented. It is the project-specific
   architecture entry point and supersedes generic descriptions.

## Frontend + backend commands

- Backend tests: `cd backend && .\.venv\Scripts\pytest`
- Frontend tests: `cd frontend && npm run test` (Vitest)
- Docs validator: `python tools/validate_docs.py`
- Backend lint: `cd backend && .\.venv\Scripts\ruff check .`
- Frontend lint: `cd frontend && npm run lint`
- Full local verify: `npm run verify` (per repo `package.json`)

## How to resume a session

1. Run `python tools/validate_docs.py`. If it fails, the doc system is
   broken; fix or revert before doing anything else.
2. Run `git status` and `git log -1 --oneline` to confirm you are on
   `docs/production-authority` (or `main`, after merge) at the expected
   commit.
3. Read [`docs/architecture/index.md`](docs/architecture/index.md) to
   ground yourself in the current state of the code.
4. Read the latest 2–3 `progress.md` files in `.agents/<role>/` if a
   legacy session is being resumed. The legacy notes are useful context
   but the Mavis team and `docs/` are the authority.
5. Pick the next checkpoint from the table in
   [`docs/architecture/index.md`](docs/architecture/index.md) §"Gaps to the
   target architecture" and ask the user which gate to attack first.

## What is not yet implemented (the gap to the target)

The integration audit identifies six release gates. None of them are
complete. The Mavis team's job is to drive them. CURRENT vs TARGET is
recorded per gate in [`docs/architecture/index.md`](docs/architecture/index.md).

| Gate | Theme | Owner | Status |
|---|---|---|---|
| 0 | Immediate correctness and security | `askthepeople-security-reviewer` | NOT STARTED |
| 1 | Typed API boundary | `askthepeople-architect` | NOT STARTED |
| 2 | Durable workflows | `askthepeople-orchestration-engineer` | NOT STARTED |
| 3 | Canonical persistence and provenance | `askthepeople-persistence-engineer` | NOT STARTED |
| 4 | Scale and operations | `askthepeople-release-operator` | NOT STARTED |
| 5 | Advanced simulation methodology | `askthepeople-ai-eval-steward` + `askthepeople-architect` | NOT STARTED |

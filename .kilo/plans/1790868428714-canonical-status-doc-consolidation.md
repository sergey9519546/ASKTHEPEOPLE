# Canonical Status Doc — Consolidate Six Contradicting Trackers Into One

## Goal

One authoritative statement of what is done and what remains, so a future agent
picking up this repo cannot be misled. No code changes in this phase.

## Why this is the first task

"Finish all the tasks" is not executable today, because the repo has **six
independent status trackers that contradict each other and the code**. An agent
following `AGENTS.md` rule 1 ("docs/ controls") gets mutually exclusive
instructions. Every other work item inherits that error. Consolidation is the
precondition for all of it.

Evidence of the contradiction:

| Tracker | Claim | Reality |
|---|---|---|
| `AGENTS.md:151-158` | 6 gates; 0,1,2,3,5 PARTIAL, 4 NOT STARTED | accurate |
| `docs/architecture/index.md:464-472` | same 6 gates, **different open items for gate 0** | accurate but divergent detail |
| `docs/architecture/IMPLEMENTATION_ROADMAP.md:441-444` | **7 gates** (phantom "Gate 6"), 2,3,4,5 **NOT STARTED** | wrong; contradicts both above |
| `docs/architecture/IMPLEMENTATION_ROADMAP.md:24` | "Files Modified: `frontend/src/views/Process.vue`" | that file does not exist |
| `docs/architecture/NEXT_STEPS_ROADMAP.md:41` | fork action `[x]` done | true (`ForkRunControl.vue:79`) |
| `docs/architecture/NEXT_STEPS_ROADMAP.md:124-126` | `forkSimulation()` "still has no caller" | **false** — same file, 85 lines apart |
| `docs/exec-plans/README.md:87` | all 8 plans NOT STARTED | plan 08's own header says 4 of 5 fixes done |
| `docs/exec-plans/09-*.md:3` | `status: "Proposed"` | Tiers 1+2 shipped: `Home.vue:599-603` no longer requires files; `api/sources.py:20` `/fetch` live; `services/url_fetcher.py` + `utils/safe_url.py` exist |
| `docs/superpowers/plans/2026-08-08-*.md` | 60+ unchecked boxes | Tasks 1-4 complete per `.superpowers/sdd/progress.md` |
| `.superpowers/sdd/progress.md:14-20` | "Task 5: not started" ×2, then "Task 5: PARTIAL" | self-contradictory in one file |
| `.zcode/plans/plan-sess_...md` | repair upload flow in `Process.vue` | obsolete; file gone, work landed in `MainView.vue:449,477` |

## Decisions made

1. **Canonical location:** `docs/architecture/index.md` §"Gaps to the target
   architecture" (line 457). `AGENTS.md` rule 8 already declares this file the
   entry point, so no new document and no change to `validate_docs.py:39-66`
   `REQUIRED`.
2. **No CI lock.** Accepted by user. Drift can recur; the doc carries an explicit
   review cadence instead.
3. **No code changes.** Dead files are *recorded* in the canonical doc, not
   deleted, this phase.
4. **Archive, don't rewrite, superseded trackers.** `validate_docs.py:151-154`
   excludes `docs/archive/` from front-matter, H1-count, link, and placeholder
   checks — so moving a file there is the lowest-risk way to remove it from both
   the agent's reading path and the validator's scope.

## Ordered tasks

### 1. Make `docs/architecture/index.md` the complete status of record

Extend the gate table at line 464 to carry, for each of the 6 gates, the
columns: **Status** (CURRENT/PARTIAL/NOT STARTED), **Evidence** (`file:line` per
`AGENTS.md` rule 1), **Remaining**, **Owner**. Reconcile gate 0's open items
against `AGENTS.md:153` so the two agree.

Below the table add a short "Verified shipped work not yet reflected in the
status tables" section, so an agent stops re-deriving it:

- exec-plan 08: fixes 2,3,4,5 done; fix 1 partial (gate 3)
- exec-plan 09 Tier 1 — `Home.vue:599-603`, requirement list at `Home.vue:610`
- exec-plan 09 Tier 2 — `api/sources.py:20-22`, `services/url_fetcher.py`,
  `utils/safe_url.py`
- SDD tasks 1-4 — `backend/app/domain/` (10 modules), `backend/app/application/`
- `NEXT_STEPS_ROADMAP.md` Phase 1.1 fork action — `ForkRunControl.vue:51,79`
- Release verify gate — `scripts/release/verify` (commit `661f330`)
- Step1 progressive guidance — commits `fdb1e83`, `b868477`

Bump `last_reviewed` and `version` in that file's front matter.

### 2. Reduce every other tracker to a pointer

For each file below: delete the status table / stale claim, leave a one-line
pointer to `docs/architecture/index.md`, keep genuine *design* content.

- `AGENTS.md:142-159` — delete the gate table; keep the section, point at the
  canonical table. Rule 8 already does this job.
- `docs/architecture/IMPLEMENTATION_ROADMAP.md` — **move to
  `docs/archive/misc/IMPLEMENTATION_ROADMAP-2026-08-18.md`.** It is
  `status: "Reference"`, its gate table is wrong, it has a phantom gate, a
  broken `Process.vue` citation, and day estimates the repo does not use.
  Nothing should link to it (verify first).
- `docs/architecture/NEXT_STEPS_ROADMAP.md` — keep. It is feature-level, not
  gate-level, and its `:69-85` "modules awaiting a data seam" section is
  genuinely good analysis. Fix only: the `:124-126` false "no caller" claim.
- `docs/exec-plans/README.md:87` — replace "all 8 plans are NOT STARTED" with
  per-plan status, or a pointer to the canonical table.
- `docs/exec-plans/08-*.md:3` and `09-*.md:3` — set `status:` to reflect shipped
  work; bump `last_reviewed`. Plan 08's `> Status reconciliation` block at line
  15 is the model to follow.
- `docs/superpowers/plans/2026-08-08-*.md` — tick the boxes for tasks the SDD
  report proves done, or add a header pointing at
  `.superpowers/sdd/progress.md` and stop treating the boxes as live.
- `docs/design/STEP2_MIGRATION_STRATEGY.md:282-314` (24 open) and
  `STEP3_STEP4_MIGRATION_STRATEGY.md:206-209,419-427` (8 open) — these are
  **real**. Leave the checkboxes; add a pointer so they are read as the
  feature-level backlog under the canonical gates.
- `docs/design/COMPONENT_MIGRATION_CHECKLIST.md` — leave as-is. It is a
  reusable template; all-unchecked is correct for a blank template.
- `.superpowers/sdd/progress.md` — delete the duplicated "Task 5: not started"
  lines 14-15; keep the `PARTIAL` entry at line 20.
- `.zcode/plans/plan-sess_...md` — **delete.** Obsolete; describes a repair to a
  file that no longer exists, and the work it describes shipped in `MainView.vue`.

### 3. Record the real remaining work in the canonical doc

Open items, verified, with evidence. These are the true backlog:

**Feature-level (no infrastructure needed)**
- Step2 progressive guidance incomplete — `STEP2_MIGRATION_STRATEGY.md:282-286`;
  `Step2EnvSetup.vue` has 0 `ProgressiveGuidance` (3 `ContextualHelp`, 3 adaptive).
- Step3 all four phases — `STEP3_STEP4_MIGRATION_STRATEGY.md:206-209`;
  `Step3RunWayfinder.vue` has 0 of each.
- Step4 all four phases — `:419-427`; `Step4Report.vue` has 0 of each.
- Dead tracked files, referenced nowhere:
  `frontend/src/components/Step1GraphBuildRefactored.vue`,
  `frontend/src/components/EvidenceBadge.vue`,
  `frontend/src/components/HistoryDatabase.vue` (documented dead at
  `NEXT_STEPS_ROADMAP.md:131-134`).

**Gate-level (blocked on decisions or infrastructure)**
- Gate 4, the only NOT STARTED gate — `index.md:470`.
- Gate 0 open: multi-tenant isolation (needs a user-identity model), privacy /
  retention architecture, source-rights attestation.
- Gates 2/3 open: object-storage cutover, transactional outbox, four
  independent state machines, PostgreSQL job/event history.

**Operator actions, not code — do not schedule as engineering work**
- Deployment blockers 1, 3, 4, 5, 7 at `docs/deployment/README.md:178-226`.
  Blocker 6 is closed (`661f330`). Blocker 5: the repo currently sits under
  OneDrive, which `RUNBOOK.md:214-218` forbids for the only deployable topology.
  Blocker 3 requires revoking exposed provider credentials before any connected
  run. These gate a deploy, not the doc work.

### 4. Repo hygiene (low risk, do in the same pass)

- Delete remote branch `origin/codex/decision-workspace-foundation` (fully
  merged; `fed5107` vs main `b868477`, 252 files behind; already ruled
  "DISCARD — branch pointer is stale" at
  `docs/archive/misc/REPOSITORY_RECOVERY_LEDGER.md:32-52`).
- Remove worktree `.kilo/worktrees/lively-bite` — detached at `b868477`, clean,
  0 changes, identical to main.
- `.freebuff/worktrees/540712c8-*` — superseded experimental WIP, already
  ruled "INVESTIGATE THEN DISCARD" at ledger §1.2. Note `.gitignore:55-56`
  already ignores `.freebuff/` and `.agents/`, but **not** `.zcode/` or
  `.superpowers/` — both are tracked (30 files). Decide whether they belong in
  version control at all; `.agents/` was excluded for exactly this reason per
  `AGENTS.md:47-49`.

## Constraints for the implementer

- `AGENTS.md` rule 1: every status claim cites `file:line`. A status table with
  no citations is worse than the current state.
- `AGENTS.md` rule 3: `python tools/validate_docs.py` must exit 0 errors,
  0 warnings, or CI blocks.
- `AGENTS.md` rule 2: no prohibited outcome language in user-facing copy under
  `docs/product/`, `docs/design/`, `docs/release/`, or the root `README.md`.
  `IMPLEMENTATION_ROADMAP.md` is under `docs/architecture/` and is being
  archived, so this is low risk — but the new canonical section is under
  `docs/architecture/` too and must stay factual.
- **Validator gotcha:** `validate_docs.py:68-71` fails on any line matching
  `TODO|FIXME|XXX`. Do not write those tokens into any doc.
- **Validator gotcha:** `validate_docs.py:193-197` requires exactly one H1 per
  doc (except the GODMODE buildplan). Archiving a file is safer than editing it.
- **Validator gotcha:** `validate_docs.py:214-234` fails on broken relative
  links. Before moving `IMPLEMENTATION_ROADMAP.md`, confirm nothing links to it.
- `AGENTS.md` rule 4: no new handlers in `backend/app/api/simulation.py`.

## Validation

1. `python tools/validate_docs.py` → PASS, 0 errors, 0 warnings.
2. `npm run verify` (invokes `scripts/release/verify`) → docs validator,
   frontend tests, frontend build, backend tests, gitleaks scan.
3. Grep for residual contradictions; each must return nothing:
   - `NOT STARTED` in `AGENTS.md`, `docs/architecture/`, `docs/exec-plans/`
     outside the canonical table
   - `Process.vue` anywhere outside `docs/archive/`
   - `all 8 plans are NOT STARTED`
   - duplicate `Task 5` in `.superpowers/sdd/progress.md`
4. Confirm exactly one gate-status table remains by grepping
   `| Gate | Theme |` across the repo; only `docs/architecture/index.md` should
   match (plus the archived copy, which is excluded from validator scope).
5. Read the canonical table cold and confirm every "Remaining" entry is either
   genuinely open in the code or explicitly marked blocked-on-operator.

## Out of scope

- Writing any of the remaining feature or gate work.
- Deleting the dead components (recorded in the canonical doc; delete later
  with a commit that can be reverted).
- Deployment, credential rotation, or any PaaS configuration.
- Adding a validator check to prevent future drift (explicitly declined).

## Open question for the implementer

Decide whether `.zcode/` and `.superpowers/` should remain in version control.
`.gitignore:55-56` already excludes `.agents/` and `.freebuff/` as per-session
workspaces; these two are the same kind of artifact and are currently tracked
(30 files, including two large `.diff` files). Either extend the ignore rule and
`git rm --cached` them, or add a line to `AGENTS.md` saying they are load-bearing
records. Leaving them tracked-and-ignored-in-spirit is what produced the
`.superpowers/sdd/progress.md` self-contradiction.

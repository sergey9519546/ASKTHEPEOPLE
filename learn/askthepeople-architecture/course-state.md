# Course state: ASKTHEPEOPLE architecture

**Learner:** repo owner/operator. Advanced software engineer (reads Python, Flask,
Celery, SQLAlchemy; audited a 6-gate release plan and a 30-task backlog
unaided). **Beginner in this specific system.** Level was inferred from this
session, not from a diagnostic — correct me and I will re-scaffold.
**Goal:** explain the architecture and its gate structure well enough to
sequence engineering work and judge whether a change is safe.
**Pace:** one chapter at a time; solutions hidden until attempted.

**Source:** document mode.
- `docs/architecture/index.md` (942 lines) — primary, the descriptive + normative spine
- `docs/architecture/adr/ADR-0001..0013` (13 ADRs, 1,842 lines) — the rationale layer
- `docs/exec-plans/README.md` (143 lines) + plans 00–09 — the delivery program
- Baseline named by source: `8b616dc7` (index.md front-matter) / `b868477` (§ Status of record)
- HEAD when course opened: `13eee43`

## Chapters

- [x] 0. Source orientation — structure, authority, known contradictions *(read at open, not taught)*
- [ ] 1. The state legend and how to read any claim in this repo  ← current, practice 1 issued
      - check question on PARTIAL-vs-progress-bar: **skipped** (learner sent "continue")
      - re-ask at chapter boundary; do not treat as answered
- [ ] 2. The truth contract (ADR-0001) and what it forbids
- [ ] 3. Topology and the HTTP layer; the route responsibility contract
- [ ] 4. Auth and the request seam — the security model
- [ ] 5. State and persistence — the three aggregates, CURRENT vs TARGET
- [ ] 6. Durable orchestration — leases, fencing tokens, heartbeats (ADR-0003)
- [ ] 7. The six release gates — program structure and ownership
- [ ] 8. Persistence, tenancy, schema convergence (ADR-0012 / 0009 / 0013)
- [ ] 9. How the truth boundary is enforced in code, and where it leaks
- [ ] 10. Operational reality — what can and cannot ship

## Concept table

| Concept | Status | Evidence | Next review |
|---|---|---|---|
| CURRENT / PARTIAL / TARGET / TRANSITION | introduced | Ch1 explanation, not yet recalled | end Ch1 |
| State labels are commit-scoped verification claims | introduced | Ch1 explanation | end Ch1 |
| States are four questions, not a maturity ladder | introduced | Ch1 explanation | end Ch1 |
| Document authority hierarchy | introduced | Ch0 | end Ch2 |
| Truth contract / Truth Rail five facts | unseen | — | Ch2 |
| Route contract: auth → parse → authorize → dispatch → present | unseen | — | Ch3 |
| Request-seam security model | unseen | — | Ch4 |
| Project / Task / Simulation aggregates | unseen | — | Ch5 |
| Lease vs lock; fencing token | unseen | — | Ch6 |
| Six gates and their owners | unseen | — | Ch7 |
| Migrations canonical (ADR-0013) | unseen | — | Ch8 |
| Truth enforcement surfaces (linter / CI / tests) | unseen | — | Ch9 |

## Review queue

- (none yet — first entry at end of Ch1)

## Error log

- (none yet)

## Source contradictions found at open — carry these forward

Flagged per the skill's rule: mark contradictory source content explicitly, do
not reconstruct it. Each is a real conflict in the normative docs, verified
against the code on 2026-10-02.

1. **A fifth state is in use.** `index.md:33-42` defines exactly four states and
   `AGENTS.md` §5 rule 6 forbids inventing a fifth. Yet `index.md:665` reads
   "Gate 4 — PARTIAL (was NOT STARTED before 2026-10-02)". "NOT STARTED" is not
   in the legend.
2. **ADR count is stale in five live places.** `AGENTS.md:184`,
   `docs/README.md:112`, `README.md:256`, `index.md:937`,
   `GATE_0_RELEASE_NOTES.md:244` all say 12 ADRs. There are 13.
3. **Gate status restated outside the authority.** `docs/exec-plans/README.md:106`
   says "gate 4 observability remains NOT STARTED" while `index.md` § Status of
   record says Gate 4 is PARTIAL with metrics shipped (`6e71f39`).
4. **Two baselines inside one section.** `index.md:481` says "Verified 2026-10-01
   against commit `b868477`"; `index.md:551` says "measured 2026-10-02".
5. **Stale measurement inside the authority doc.** `index.md:107,115` states
   `api/simulation.py` is a 364-line helper module with 10 route modules.
   Measured 2026-10-02: **406 lines, 9 route modules**.
6. **`AGENTS.md` §5 rule 9 / §9.2 present the two-schema divergence as open.**
   It is closed by ADR-0013; `backend/app/db/schema.py` is stripped to `Base`.
7. **Test count.** `AGENTS.md:179` says 123 test modules; `backend/tests/` holds
   116 `.py` files. Backend suite measured 2026-10-02: 9554 passed / 16 failed.

## Source navigation index

(filled at course end — concept → section/line)

| Concept | Source |
|---|---|
| State legend | `index.md` § State legend used in this document (L33-42) |
| System topology | `index.md` § System at a glance (L44-80) |
| Route contract | `index.md` § HTTP layer (L82-92) |
| Security seam | `index.md` § Authentication and security headers (L138-218) |
| Aggregates | `index.md` § State and persistence (L220-348) |
| Async execution | `index.md` § Asynchronous execution (L350-395) |
| Gates | `index.md` § Status of record (L472-505) |

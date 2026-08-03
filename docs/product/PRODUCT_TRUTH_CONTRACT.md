---
title: "Product Truth Contract"
status: "Normative"
version: "1.1.0"
owner: "Product + Research + Engineering"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §1–§6"
applies_to: "backend/app/*, frontend/src/*, all exports, all generated copy, all marketing"
---

# Product Truth Contract

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.
> **Research status.** This document distinguishes binding product policy from
> external standards and research. External sources inform the requirements but
> do not automatically make the product compliant, valid, accurate, or fit for a
> particular legal jurisdiction. Legal and human-subject review remain separate
> launch responsibilities.

## Purpose

This contract prevents a synthetic scenario-exploration product from being
mistaken for human research, population measurement, behavioral prediction,
causal evidence, or validated public opinion. It applies to the interface,
database, APIs, prompts, logs, exports, marketing, sales materials, support
responses, screenshots, and integrations.

## Locked product identity

The approved lockup is:

```text
ASKTHEPEOPLE
SYNTHETIC DECISION EXPLORER

Explore assumptions before you ask.
Validate with people after.
```

The wordmark **ASKTHEPEOPLE** MUST NOT appear by itself in any context where a
reasonable reader could infer that the product already asked people. Browser
titles, social cards, exported documents, copied content, notifications, and
email subjects MUST include the synthetic descriptor.

## Claim boundary

ASKTHEPEOPLE MAY claim that it:

- organizes reviewed source material into starting conditions;
- makes assumptions and critical uncertainties explicit;
- generates structured decision lenses and synthetic actions;
- constructs alternative possible paths for exploration;
- records what occurred inside a run;
- identifies conflicts, missing information, and questions worth testing;
- prepares a handoff for research with real people.

ASKTHEPEOPLE MUST NOT claim, imply, or visualize that it:

- measured public opinion, sentiment, preference, intent, or behavior;
- recruited, sampled, observed, interviewed, or surveyed people;
- generated representative respondents or a population;
- predicts what people will do or assigns real-world likelihood;
- validates an outcome because source material was uploaded;
- establishes causality;
- produces calibrated confidence without an external calibration study;
- creates a digital twin of an individual, group, community, or population.

## System-of-record fields

Every run and export MUST store the following values as immutable facts:

```json
{
  "output_origin": "synthetic",
  "human_respondent_count": 0,
  "is_forecast": false,
  "is_public_opinion_measure": false,
  "is_causal_evidence": false,
  "source_role": "starting_conditions_only",
  "human_validation_scope": "external_to_synthetic_run"
}
```

No application role, administrative endpoint, migration, or import MAY mutate
those values for a synthetic run.

## Permanent truth statements

Every primary workflow surface must expose the following facts in a persistent, non-dismissible Truth Rail:

```text
ACTIONS + ANSWERS: SYNTHETIC
HUMAN RESPONDENTS: 0
NOT A FORECAST
SOURCES: STARTING CONDITIONS ONLY
HUMAN VALIDATION: OUTSIDE THIS RUN
```

Use `HUMAN RESPONDENTS: 0` because the number is meaningful only as a disclosure that no human data was collected. Never display synthetic profile count beside it in a way that resembles sample size.

### Screen-specific truth statements

| Screen | Required contextual statement |
|---|---|
| State the decision | This run explores assumptions. It does not ask or measure people. |
| Review source material | Source material shapes starting conditions. It does not validate a path or outcome. |
| Review assumptions | Generated profiles are decision lenses, not representations of actual people. |
| Check the run | Nothing on this screen is human evidence or a forecast. |
| Explore possible paths | Color, position, spacing, order, and line length do not show likelihood or public support. |
| Decision brief | No person was interviewed, surveyed, observed, or measured for this brief. |
| Explain the brief | This answer explains generated run artifacts; it does not add human evidence. |
| Generated profile response | This is fictional generated text, not a human quotation. |
| Research handoff | This prepares external research. No human validation has occurred here. |

## Truth invariants enforced in code

The following are domain invariants, not UI preferences:

```text
run.humanRespondentCount MUST equal 0
run.isForecast MUST equal false
run.outputOrigin MUST equal "synthetic"
run.humanValidationStatus MUST NOT become "completed" inside the synthetic workflow
source assertions MUST NOT directly support synthetic considerations or path outcomes
synthetic artifacts MUST NOT be typed as human evidence
completed runs MUST be immutable
exports MUST contain visible and machine-readable origin disclosure
```

Any write that violates an invariant must fail. Any migration, API handler, background job, import, or admin action that bypasses it is a release blocker.

## Epistemic Ledger

Every meaningful statement in the system must carry both an **origin** and an **epistemic role**.

### Origin types

| Origin | Meaning | Visual label |
|---|---|---|
| `USER_STATED` | Directly entered or edited by a user | `USER` |
| `SOURCE_EXTRACTED` | Extracted from uploaded material and approved by a user | `SOURCE` |
| `ASSUMPTION_DECLARED` | Explicit assumption, whether user-entered or generated then approved | `ASSUMPTION` |
| `SYNTHETIC_GENERATED` | Generated by a model inside a run | `SYNTHETIC` |
| `EXTERNAL_HUMAN_EVIDENCE` | Imported after actual human research with method metadata | `HUMAN EVIDENCE` |
| `SYSTEM_METADATA` | Timestamp, ID, model version, schema version, hash, status | `SYSTEM` |

### Epistemic roles

- Decision statement
- Scope constraint
- Source segment
- Starting condition
- Assumption
- Critical uncertainty
- Generated profile / decision lens
- Scenario rule
- Possible path
- Synthetic action
- Decision consideration
- Conflict
- Missing information
- Disconfirming condition
- Validation question
- Related run record
- External human finding
- Decision-owner conclusion

### Allowed and prohibited relationships

Allowed:

```text
SOURCE SEGMENT -> informs -> STARTING CONDITION
USER STATEMENT -> defines -> DECISION
STARTING CONDITION -> constrains -> SCENARIO RULE
ASSUMPTION -> creates branch in -> POSSIBLE PATH
GENERATED PROFILE -> applies lens to -> SYNTHETIC ACTION
POSSIBLE PATH -> surfaces -> DECISION CONSIDERATION
DECISION CONSIDERATION -> produces -> VALIDATION QUESTION
EXTERNAL HUMAN FINDING -> supports / contradicts / leaves unresolved -> VALIDATION QUESTION
```

Prohibited:

```text
SOURCE SEGMENT -> proves -> POSSIBLE PATH
SOURCE SEGMENT -> validates -> DECISION CONSIDERATION
SYNTHETIC ACTION -> represents -> HUMAN BEHAVIOR
GENERATED PROFILE -> is member of -> SAMPLE
RELATED RUN RECORD -> cites / corroborates -> STATEMENT
MODEL CONSISTENCY -> equals -> HUMAN CONFIDENCE
PATH COUNT -> equals -> SUPPORT OR PREVALENCE
```

Implement these rules in a domain validation layer and cover them with property-based or exhaustive relationship tests.

## Decision-owner conclusion

The system may generate considerations and questions. It must not silently make the final decision.

Add a separately styled section:

```text
DECISION OWNER'S CONCLUSION
Written by: [name]
Date: [date]
Based on: [selected run artifacts + external human evidence, if any]
```

AI may help edit the owner’s text only after explicit request. The conclusion remains human-authored and is stored separately from the synthetic brief.


---
## Truth-preserving detached artifacts

The truth layer MUST survive context loss. Every artifact that can leave the
application—including PDF, DOCX, Markdown, JSON, CSV, image, clipboard content,
email, notification, API response, embed, and social preview—MUST include:

```text
ASKTHEPEOPLE / SYNTHETIC DECISION EXPLORER
HUMAN RESPONDENTS: 0
NOT A FORECAST
SOURCE MATERIAL SET STARTING CONDITIONS ONLY
HUMAN VALIDATION: NOT PERFORMED IN THIS RUN
```

Machine-readable exports MUST repeat the same facts in structured metadata.
Rendered exports MUST fail closed if the disclosure component cannot be
included or validated.

## Claim registry

Every externally visible performance, accuracy, validity, representativeness,
or compliance claim MUST have a claim record containing:

| Field | Requirement |
|---|---|
| Claim ID | Stable identifier |
| Exact approved wording | No paraphrase in production copy |
| Claim owner | Accountable person |
| Evidence | Linked, dated, fit-for-purpose evidence |
| Population and task scope | Exact boundary of the evidence |
| Limitations | Display or disclosure requirement |
| Approval | Product, legal, research, and security as applicable |
| Expiry | Mandatory re-review date |
| Surfaces | Exact pages, exports, campaigns, and scripts |
| Rollback | How the claim is removed everywhere |

A claim without an active record is prohibited.

## Enforcement points

The contract MUST be enforced at:

1. domain-model validation;
2. database constraints;
3. API serialization;
4. prompt and schema contracts;
5. deterministic output validators;
6. content linting;
7. export rendering;
8. analytics naming;
9. marketing/release review;
10. comprehension testing.

## Acceptance evidence

A release passes this contract only when:

- all run fixtures preserve the immutable truth fields;
- all primary screens show the Truth Rail and contextual statement;
- every export type passes visible and machine-readable disclosure checks;
- the terminology linter reports zero prohibited outcome claims;
- every epistemic edge passes the allowed-relation validator;
- moderated users understand that zero people were asked, outputs are
  synthetic, sources do not prove paths, and real validation is external;
- screenshots and social previews remain truthful without surrounding context;
- no unsupported claim is present in product or marketing copy.

## References

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) — Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [European Commission Article 50 transparency guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems) — Final July 2026 guidance on transparency obligations that apply from 2 August 2026.

---

## Project-specific implementation mapping (baseline `8b616dc7`)

This section grounds every clause above in the actual code under
[`backend/app/`](../../backend/app/) and [`frontend/src/`](../../frontend/src/).
Items are marked **CURRENT** (implemented and verified), **PARTIAL** (implemented
but materially deficient against the clause), or **TARGET** (clause is
normative; the implementation has not reached it). See
[`docs/architecture/index.md`](../architecture/index.md) for the
CURRENT / PARTIAL / TARGET legend.

## Truth Rail on the request/response seam — CURRENT

The HTTP layer enforces the disclosure layer on every `/api/*` response:

- `Cache-Control: no-store` for `/api/*` and `/health`
  ([`app/__init__.py:193-195`](../../backend/app/__init__.py:193))
  prevents caching of synthetic output.
- `apply_security_headers` after-request hook adds CSP, X-Content-Type-Options,
  X-Frame-Options DENY, Referrer-Policy no-referrer, Permissions-Policy
  (all sensitive features disabled), COOP same-origin, CORP same-origin, and
  HSTS in production
  ([`app/__init__.py:149-196`](../../backend/app/__init__.py:149)).
- `strip_traceback_in_production` removes internal `traceback` keys and
  replaces 5xx `error` strings with `internal_server_error` so internal paths,
  credentials, or upstream API error bodies leaked via `str(e)` cannot reach
  clients
  ([`app/__init__.py:198-226`](../../backend/app/__init__.py:198)).
- `require_auth` middleware enforces a constant-time bearer-token comparison
  via `hmac.compare_digest` on every `/api/*` request when `APP_TOKEN` is set
  ([`app/__init__.py:125-141`](../../backend/app/__init__.py:125)).
- Production CORS lockdown refuses `CORS_ORIGINS='*'` in non-debug mode and
  falls back to `http://127.0.0.1`
  ([`app/__init__.py:74-82`](../../backend/app/__init__.py:74)).
- The `log_request` middleware never logs request bodies, so settings,
  provider-test, and source-upload requests cannot leak keys, source text, or
  PII into DEBUG file logs
  ([`app/__init__.py:111-123`](../../backend/app/__init__.py:111)).

These mechanisms protect the disclosure layer at the wire. They are **not** a
substitute for the in-product Truth Rail UI required by this contract — see
"Frontend disclosure — TARGET" below.

## Bearer token is the only authentication — CURRENT (with gap)

`create_app()` is fail-closed: if `REQUIRE_APP_AUTH` is set and `APP_TOKEN` is
missing or weak, application creation raises `RuntimeError` and the process
refuses to start
([`app/__init__.py:30-39`](../../backend/app/__init__.py:30)).
The constant-time comparison is at
[`app/__init__.py:140`](../../backend/app/__init__.py:140).

**Gap:** there is no per-resource object-level authorization. A valid
`APP_TOKEN` is allowed to operate on every simulation, project, report, and
artifact. Multi-tenant isolation is **TARGET** and is the subject of
[`adr/ADR-0009-multi-tenant-isolation.md`](../architecture/adr/ADR-0009-multi-tenant-isolation.md).

## Immutable truth fields — TARGET (not yet enforced as data)

The JSON envelope in "System-of-record fields" above is **not yet stored** on
every run. The current canonical store for a run is the state JSON written by
`SimulationManager` under
[`backend/uploads/simulations/{simulation_id}/state.json`](../../backend/uploads/simulations)
and the per-platform SQLite databases (`reddit_simulation.db`,
`twitter_simulation.db`) read by the audit's P0 path-escape endpoint.

Reaching the contract requires:

- The four-state execution state machine from
  [`docs/architecture/state-machines.md`](../architecture/state-machines.md)
  to be the single source of state;
- PostgreSQL to be the canonical store per
  [`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](../architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md);
- Every attempt to carry the immutable `output_origin: "synthetic"` and
  `human_respondent_count: 0` fields;
- Completed attempts to be immutable;
- The audit's P1 finding on non-atomic file persistence to be resolved
  (no `os.replace`, no `tmp + rename`, no compare-and-swap today).

The persistence target is gate 3 and is owned by
`askthepeople-persistence-engineer`.

## Source material as starting conditions only — PARTIAL

The contract states that source material "shapes starting conditions" and
MUST NOT prove, validate, or confirm a path or outcome. The current
implementation already takes care in the following ways:

- Source upload is by `FileStorage` into a per-project `files/` directory
  ([`models/project.py:247-278`](../../backend/app/models/project.py:247))
  with a randomized safe filename. Original names are not exposed downstream.
- Text extraction is separated from generation: `extracted_text.txt` is
  written to a per-project location
  ([`models/project.py:280-296`](../../backend/app/models/project.py:280))
  and is consumed by ontology and graph builders, not by the simulation
  runner directly.
- The ZEP graph memory is updated as a side effect, never as a source of
  truth for run outcomes
  ([`services/zep_graph_memory_updater.py`](../../backend/app/services/zep_graph_memory_updater.py)).

**Gap:** the source material is parsed and consumed by LLM calls in
`ontology_generator.py`, `oasis_profile_generator.py`, and
`simulation_config_generator.py`. Source-text prompt injection is **not yet
fully contained** — see
[`docs/security/SOURCE_INGESTION.md`](../security/SOURCE_INGESTION.md) and
the audit's P1 finding on prompt-prefixing. The P0 fix in
[`adr/ADR-0005-zero-trust-source-ingestion.md`](../architecture/adr/ADR-0005-zero-trust-source-ingestion.md)
is gate 0 and is owned by `askthepeople-security-reviewer`.

## "Not a forecast" — CURRENT (text) + TARGET (data invariant)

The text disclosure is already present in this contract, in
[`README.md`](../../README.md), in
[`docs/product/METHODOLOGY.md`](METHODOLOGY.md), and in every generated
artifact's Truth Rail (when the Truth Rail is rendered — see
[Frontend disclosure — TARGET](#frontend-disclosure-target) below).

**Gap:** the data invariant `run.isForecast MUST equal false` is not yet
enforced at the database or model layer. It is enforced only by convention and
by the post-generation `claim_boundary` and `validation_engine` services. The
target is to encode the invariant as a database CHECK constraint and a
non-nullable column with a single permitted value, per
[`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](../architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md).

## Source classification in reports — PARTIAL

The report agent
([`services/report_agent.py`](../../backend/app/services/report_agent.py))
generates "trace examples" (a.k.a. **related run records** in
[`docs/product/TERMINOLOGY.md`](TERMINOLOGY.md)) by selecting generated
records that share keywords with a report section. The implementation already
labels these as "not citations":

- The post-hoc keyword-selection pattern is acknowledged in the
  repository README: "Within-run trace examples … show generated records
  selected after report creation by keyword overlap … they do not show that a
  record caused or supports a particular statement."
  ([`README.md:35-48`](../../README.md))
- The `report_evidence` service
  ([`services/report_evidence.py`](../../backend/app/services/report_evidence.py))
  carries the evidence score by source type — currently a per-source-type
  heuristic, not a calibrated measurement, and acknowledged as such in
  [`docs/product/SUCCESS_METRICS.md`](SUCCESS_METRICS.md).

**Gap:** the report UI does not yet render the
`RELATED BY KEYWORD OR SEMANTIC SIMILARITY / NOT A CITATION / NOT STATEMENT
LINEAGE / NOT CORROBORATION` block that this contract and
[`docs/product/TERMINOLOGY.md`](TERMINOLOGY.md) require.

## Frontend disclosure — TARGET

The Truth Rail and the per-screen contextual statements in
"Permanent truth statements" above are **not yet rendered** in
`frontend/src/`. The frontend is a Vue 3 + Vite + D3 application
([`docs/architecture/index.md` §"Frontend"](../architecture/index.md))
and the Civic Wayfinding design system
([`docs/design/DIRECTION_C.md`](../design/DIRECTION_C.md)) is implemented
in CSS and SVG. The semantic route list required by
[`adr/ADR-0006-route-map-list-parity.md`](../architecture/adr/ADR-0006-route-map-list-parity.md)
is **TARGET**.

The Truth Rail rendering is owned by `askthepeople-frontend-steward`. The
release gate is in [`docs/release/ACCEPTANCE.md`](../release/ACCEPTANCE.md).

## Epistemic ledger — TARGET

The Epistemic Ledger (origin types, epistemic roles, allowed and prohibited
relationships) is not yet implemented as a data structure or domain rule. It
is normative in this contract and in
[`adr/ADR-0002-epistemic-ledger.md`](../architecture/adr/ADR-0002-epistemic-ledger.md).
Reaching it requires:

- Every persisted fact to carry an `origin` and an `epistemic_role`;
- A domain validation layer that rejects prohibited relationships at write
  time (e.g. `SOURCE SEGMENT -> proves -> POSSIBLE PATH` is rejected);
- Property-based or exhaustive relationship tests in the test corpus;
- The audit's P1 finding on client-supplied export data to be closed (the
  export route currently accepts arbitrary rows from the caller).

The ledger is gate 1, owned by `askthepeople-architect`, with security
review by `askthepeople-security-reviewer`.

## Decision-owner conclusion — TARGET

The "Decision Owner's Conclusion" block required by this contract is a
human-authored, separately-stored artifact. The current
[`services/report_agent.py`](../../backend/app/services/report_agent.py)
produces a single synthetic report; there is no separate human-authored
conclusion store. Reaching the contract requires a new data model, a new
route, and a new UI surface. Tracked in
[`docs/exec-plans/05-brief-handoff-exports-and-provenance.md`](../exec-plans/05-brief-handoff-exports-and-provenance.md).

## Claim registry — TARGET

The claim registry required by "Claim registry" above is not yet
implemented. The product makes normative claims (zero human respondents,
not a forecast, source material sets starting conditions only) but the
registry, the per-claim evidence, the per-claim expiry, and the per-claim
rollback plan are not stored anywhere. Reaching the contract requires the
content-lint CI check in
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) to be
extended with the claim registry, and a new data model in the persistence
layer. Tracked in
[`docs/exec-plans/07-evals-accessibility-and-release.md`](../exec-plans/07-evals-accessibility-and-release.md).

## Linter enforcement — PARTIAL

The CI workflow at
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) runs
three checks on every push and PR that touches `docs/`:

1. `python tools/validate_docs.py` — structural validation;
2. A grep for the naked `ASKTHEPEOPLE` wordmark in user-facing copy outside
   the three allowlisted product docs;
3. A grep for the prohibited outcome language list (predict, know what
   people think, representative synthetic sample, human-level accuracy,
   digital twin, bias-free personas, scientifically proven simulation, …).

**Gap:** the linter checks the doc tree and the repo README, but not:

- AI outputs in the report agent;
- UI copy in `frontend/src/`;
- Exports (CSV, JSON, PDF, DOCX);
- Email templates, share previews, marketing pages;
- Seed data and fixture files.

These are required by the contract but are not yet policed. The linter
expansion is tracked in
[`docs/exec-plans/07-evals-accessibility-and-release.md`](../exec-plans/07-evals-accessibility-and-release.md).

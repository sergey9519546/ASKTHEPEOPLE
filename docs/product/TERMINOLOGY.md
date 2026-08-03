---
title: "Terminology and Claim Language"
status: "Normative"
version: "1.1.0"
owner: "Content Design + Product + Legal"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §1–§6"
applies_to: "UI copy, exports, APIs, analytics, support scripts, marketing, AI outputs"
---

# Terminology

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.

## Purpose

Words define the user's mental model. This lexicon is enforced in interface
copy, generated output, exports, APIs intended for end users, analytics labels,
support scripts, and marketing. Legacy internal class names MAY remain during a
migration only when they cannot surface to users and are documented as technical
debt.

## Canonical product terms

| Use | Canonical term | Meaning |
|---|---|---|
| Product category | Synthetic decision explorer | Scenario and research-planning system |
| Input document | Source material | Context that may inform starting conditions |
| Extracted statement | Candidate starting condition | Unapproved extraction with an exact source location |
| Approved extraction | Starting condition | User-reviewed condition; not outcome evidence |
| Explicit uncertainty | Assumption | A proposition the run temporarily treats as true |
| Decision-changing variable | Critical uncertainty | Unresolved factor with materially different states |
| Structured synthetic perspective | Generated profile / decision lens | Functional constraints and criteria, not a person |
| Model-created event | Synthetic action | Generated action inside one run |
| Alternative branch | Possible path | A constructed possibility, not a probability |
| Implication | Decision consideration | What the decision owner should examine |
| Falsifier | Disconfirming condition | What could make the consideration wrong |
| Research output | Question to validate with people | Question for an external human process |
| Diagnostic artifact | Related run record | Keyword-related example; not citation or lineage |
| External study result | Human finding | Separate, method-documented real evidence |

## Product name rule

Always use one of:

- `ASKTHEPEOPLE / Synthetic Decision Explorer`
- `ASKTHEPEOPLE synthetic scenario exploration`
- `ASKTHEPEOPLE research-planning handoff`

Never use the naked wordmark where it could imply that people were already
asked.

## Content design and terminology enforcement

### Preferred terms

- Source material
- Starting condition
- Assumption
- Critical uncertainty
- Generated profile
- Decision lens
- Scenario rule
- Possible path
- Synthetic action
- Decision consideration
- Pattern within this run
- Related run record
- Validate with people
- Research handoff
- External human evidence

### Prohibited synthetic-outcome terms

- Respondent
- Participant
- Sample
- Panel
- Survey result
- Poll
- Public opinion
- Confidence
- Probability
- Predicted behavior
- Representative
- Majority
- Minority
- Evidence from the graph
- Verified lineage
- Corroborated claim
- Digital twin
- Realistic human
- Human parity
- Citation to a generated conclusion

The words `respondent`, `participant`, `survey`, and `poll` may appear only when describing **future or completed real human research**, never synthetic output.

### Language linter

Implement a shared server/client linter that scans:

- AI outputs;
- UI copy;
- exports;
- email templates;
- share previews;
- seed data;
- marketing pages;
- documentation examples.

Each violation should include:

- term;
- location;
- allowed-context check;
- suggested replacement;
- severity.

Critical violations block artifact finalization and release.

## Related run records

The inspector title is `RUN RECORD`, not `Sources`, `Evidence`, or `Citations`.

Every related record displays:

```text
RELATED BY KEYWORD OR SEMANTIC SIMILARITY
NOT A CITATION
NOT STATEMENT LINEAGE
NOT CORROBORATION
```

Do not use superscript numbers, academic citation styling, quotation marks, or lines from a record to a consideration.

## Loading and operational states

Every state uses plain language and an explicit action.

### Upload processing

```text
Reading source material
We are extracting text and locations. No possible paths are being generated yet.
```

### Run queued

```text
Run queued
Your reviewed configuration is locked. You can leave this page and return.
```

### Run in progress

Show stages, not simulated “thinking”:

```text
1/5 Checking configuration          COMPLETE
2/5 Building scenario candidates    IN PROGRESS
3/5 Generating possible paths       NOT STARTED
4/5 Checking coverage and language  NOT STARTED
5/5 Preparing review                NOT STARTED
```

### Stopped

```text
Run stopped
No final brief was created. Review partial artifacts or start a new run.
```

### Reconnecting

```text
Connection lost
The run continues on the server. Reconnecting to status…
```

### Failure

```text
This run did not complete
No decision brief was finalized. Review the error record, retry from the failed stage, or duplicate the run with changes.
```

### Unauthorized

```text
You do not have access to this decision
Ask a workspace owner for access or return to Decisions.
```

Never use vague “Something went wrong” as the only message.
## Prohibited grammar patterns

The linter MUST detect not only individual words but claim structures:

```text
[synthetic group] + said / believed / preferred / wanted
[source] + proves / validates / confirms + [path or outcome]
[number or percentage] + of generated profiles + support / oppose
[consistency score] + confidence / certainty / likelihood
[path] + most likely / winning / majority / expected
[generated statement] enclosed as an unlabeled quotation
```

## API and database naming

Public API fields MUST use product-safe names. Legacy fields such as `persona`,
`respondent`, `interview`, `evidence_score`, or `confidence` MUST be migrated or
wrapped behind clearly synthetic internal schemas. A public API MUST NOT expose
ambiguous fields that downstream consumers can relabel as human evidence.

Approved examples:

```json
{
  "generated_profile_count": 6,
  "synthetic_action_count": 42,
  "generation_stability": {
    "metric": "path_structure_overlap",
    "scope": "synthetic_repetitions_only"
  }
}
```

Disallowed examples:

```json
{
  "respondents": 1000,
  "public_support": 0.72,
  "confidence": 0.91,
  "predicted_behavior": "adopt"
}
```

## Content-lint severity

| Severity | Example | Build behavior |
|---|---|---|
| Critical | “72% of people support…” from synthetic output | Block generation/export/release |
| High | “Most likely path” | Block output until corrected |
| Medium | Unqualified “profile said” | Require rewrite |
| Low | Inconsistent capitalization | Lint warning |

## Terminology change control

A new public term requires content-design, product-truth, and legal review.
Changing a label is a data-contract change when users, exports, APIs, or
analytics may interpret it differently.

## Acceptance evidence

- zero critical/high linter findings across UI strings and generated fixtures;
- no ambiguous sample-size language;
- no synthetic text rendered as an unlabeled human quotation;
- API contract tests reject forbidden public fields;
- comprehension participants use “synthetic,” “possible path,” and “external
  validation” rather than “survey,” “prediction,” or “respondents.”

## References

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) — Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [GOV.UK Design System — Notification banner](https://design-system.service.gov.uk/components/notification-banner/) — Warns against repeated banner overuse and supports putting task-critical information in the main journey.

---

## Project-specific terminology status (baseline `8b616dc7`)

This section maps every canonical term above to the actual code under
[`backend/app/`](../../backend/app/) and [`frontend/src/`](../../frontend/src/).
Items are marked **CURRENT** (the term is what the code uses), **PARTIAL**
(the term is partly used; legacy or internal names remain), or **TARGET**
(the term is normative; the code has not been migrated to it). The CI
content linter in
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) blocks
prohibited synthetic-outcome language in `docs/product/`, `docs/design/`,
`docs/release/`, and the repo root `README.md`. See
[`docs/architecture/index.md`](../architecture/index.md) for the legend.

## Canonical term → current code map

| Canonical term | Current code entity | Status | File |
|---|---|---|---|
| Synthetic decision explorer | Product category — no internal name; backend is `app` | CURRENT (text), TARGET (no internal rename) | — |
| Source material | `Project.files: List[Dict[str, str]]` and `extracted_text.txt` per project | CURRENT | [`models/project.py:36-41`](../../backend/app/models/project.py:36), [`models/project.py:280-296`](../../backend/app/models/project.py:280) |
| Candidate starting condition | Implicit in the extraction step (no explicit field) | TARGET | — |
| Starting condition | Implied by `simulation_requirement` text | PARTIAL (renames to be picked up in gate 1) | [`models/project.py:48-49`](../../backend/app/models/project.py:48) |
| Assumption | Free-text input via `simulation_requirement`; not separately modeled | PARTIAL | [`models/project.py:48-49`](../../backend/app/models/project.py:48) |
| Critical uncertainty | Not separately modeled | TARGET | — |
| Generated profile / decision lens | Produced by `oasis_profile_generator.py`; persisted as JSON files in the simulation directory | CURRENT | [`services/oasis_profile_generator.py`](../../backend/app/services/oasis_profile_generator.py) |
| Synthetic action | Stored in the per-platform SQLite DBs (`reddit_simulation.db`, `twitter_simulation.db`) | CURRENT | `backend/uploads/simulations/{simulation_id}/*.db` |
| Possible path | Synthesized in the report agent | PARTIAL (no explicit data type yet) | [`services/report_agent.py`](../../backend/app/services/report_agent.py) |
| Decision consideration | A section in the generated report | PARTIAL (rendered in the report JSON; the frontend may use a legacy term) | [`services/report_agent.py`](../../backend/app/services/report_agent.py) |
| Disconfirming condition | Produced in the report | PARTIAL | [`services/report_agent.py`](../../backend/app/services/report_agent.py) |
| Question to validate with people | A section in the generated report; the explicit "research handoff" UI is **TARGET** | PARTIAL | [`services/report_agent.py`](../../backend/app/services/report_agent.py) |
| Related run record | Post-hoc keyword-overlap match in the report | PARTIAL (the disclosure block is required by this contract and **not yet rendered** in the frontend) | [`services/report_evidence.py`](../../backend/app/services/report_evidence.py) |
| Human finding | A separate, method-documented external artifact | TARGET (no import flow) | — |

## Legacy terms still present in the codebase

The integration audit identifies legacy alias endpoints and identifier
names that must be retired. Until the migration in gate 1, they appear in
the codebase and in analytics:

- `/interview`, `/interview/all`, `/interview/batch` (routes)
- `/opinions` (route)
- `/export/survey` (route)
- `interviews_count` (field)
- `export_survey_results` (field)

These are documented in the audit at
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` §5 P2 "Misleading legacy terminology remains public"](../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md#5-release-blocking-findings).
The retirement plan is in
[`docs/exec-plans/01-truth-layer-and-foundations.md`](../exec-plans/01-truth-layer-and-foundations.md)
and must add the deprecation header per the audit:

```http
Deprecation: true
Sunset: <date>
Link: </replacement>; rel="successor-version"
```

## Legacy internal field names still in APIs

The audit's P1 finding on "Client-supplied export data can fabricate
provenance" is the deepest terminology hazard today: a client can submit
arbitrary `results` rows to the export route and receive a file under the
ASKTHEPEOPLE wordmark. Until gate 3 closes this, the export route accepts:

```json
{
  "results": [
    { "respondent_id": "...", "answer": "...", "evidence_score": 0.7 }
  ],
  "format": "csv"
}
```

The fields `respondent_id` and `evidence_score` are the exact terms this
lexicon prohibits in user-facing copy and that the public API rewrite in
gate 1 will wrap behind clearly-synthetic internal names. Today, the
export route does not enforce this. Tracked in
[`docs/exec-plans/05-brief-handoff-exports-and-provenance.md`](../exec-plans/05-brief-handoff-exports-and-provenance.md).

## Content linter expansion — TARGET

The linter enforced by
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) currently
covers `docs/product/`, `docs/design/`, `docs/release/`, and the repo
root `README.md`. The contract requires linter coverage of:

- AI outputs (report JSON, profile responses);
- UI copy in `frontend/src/` and `frontend/dist/`;
- Exports (CSV, JSON, PDF, DOCX, PNG) — see
  [`docs/security/INCIDENT_RESPONSE.md`](../security/INCIDENT_RESPONSE.md) for the
  disclosure-block requirement;
- Email templates, share previews, marketing pages;
- Seed data and fixture files in `backend/uploads/`.

The expansion is **TARGET**, part of gate 5, owned by
`askthepeople-ai-eval-steward`.

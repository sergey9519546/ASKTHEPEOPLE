---
title: "Terminology and Claim Language"
status: "Normative"
version: "1.0.0"
owner: "Content Design + Product + Legal"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
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

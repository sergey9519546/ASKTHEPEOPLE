---
title: "Product Truth Contract"
status: "Normative"
version: "1.0.0"
owner: "Product + Research + Engineering"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
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

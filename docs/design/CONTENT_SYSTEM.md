---
title: "Content System"
status: "Normative"
version: "1.1.0"
owner: "Content Design + Product Truth + Localization"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P1 'Inconsistent request validation'"
applies_to: "every UI string, every generated text, every export, every email template, every share preview, every marketing surface"
---

# Content System

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.

## Content objective

The content system must let a nontechnical decision owner understand:

1. what the system received;
2. what the user approved;
3. what the system generated;
4. what the output does and does not establish;
5. what action is required next;
6. where real human research begins.

The interface MUST NOT require knowledge of agents, embeddings, graph memory,
LLM temperature, centrality, simulation epochs, or model-provider terminology.

## Voice

- direct, calm, and concrete;
- active voice;
- short sentences for instructions and states;
- specific nouns instead of “it,” “this,” or “the AI” when the reference could
  be ambiguous;
- no hype, anthropomorphism, false certainty, or institutional posturing;
- explain the consequence before implementation detail;
- state limits adjacent to the relevant output, not only in legal copy.

## Page-content template

Every primary workflow page follows this order:

1. step number and action-led title;
2. one-sentence purpose;
3. contextual truth statement;
4. primary task;
5. validation/error guidance;
6. one primary action;
7. secondary diagnostics in disclosure;
8. persistent Truth Rail.

Example:

```text
03 / REVIEW ASSUMPTIONS

Check what this run will temporarily treat as true.

Generated profiles are decision lenses. They are not actual or representative
people.

[assumption review task]

PRIMARY: CHECK THIS RUN
SECONDARY: SAVE AND EXIT
```

## Action labels

Buttons MUST describe the result:

- `Review source material`
- `Continue without source material`
- `Review assumptions`
- `Check this run`
- `Generate possible paths`
- `Read the decision brief`
- `Prepare human validation`
- `Create research handoff`
- `Stop run`
- `Retry this stage`

Avoid `Next`, `Submit`, `Go`, `Run AI`, `Ask the people`, `Predict`, `Validate`,
or `Generate insights`.

## Truth-layer copy

## Truth Rail

### Desktop

Five rectangular cells separated by hard rules; 48–52 px high.

```text
ACTIONS + ANSWERS: GENERATED | HUMAN RESPONDENTS: 0 | NOT A FORECAST |
SOURCES: STARTING CONDITIONS ONLY | HUMAN VALIDATION: OUTSIDE THIS RUN
```

### Mobile

Two wrapped lines, never a horizontal carousel:

```text
GENERATED · 0 HUMAN RESPONDENTS · NOT A FORECAST
SOURCES SET INPUTS ONLY · VALIDATE WITH PEOPLE OUTSIDE
```

The rail may be sticky only if `scroll-padding-top` and focus tests prove it never obscures content. WCAG 2.2 adds an AA requirement that focused items not be entirely obscured.([WCAG 2.2 Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum))

## Surface semantics

- **Warm paper:** user decisions, forms, review, editorial brief.
- **Charcoal:** synthetic route field, run process, diagnostics.
- **Light-cream transfer field:** external research handoff and the boundary where the synthetic system ends.

This creates a stable visual narrative:

```text
CREAM — DEFINE AND REVIEW
CHARCOAL — EXPLORE GENERATED POSSIBILITIES
LIGHT CREAM — LEAVE THE GENERATED SYSTEM AND VALIDATE
```

Do not use these surfaces merely as decorative alternation.

## Visual design tokens

### Color

| Token | Value | Use |
|---|---:|---|
| `--ink` | `#111313` | Main dark field and primary text |
| `--paper` | `#F2EBDD` | Forms and reading surfaces |
| `--paper-transfer` | `#F7F0E2` | Human-validation boundary |
| `--signal` | `#F04B3D` | Current step, active route, brand field, single primary action |
| `--signal-strong` | `#FF5D4F` | Hover or pressed action field |
| `--signal-deep` | `#982D24` | Accessible red text on cream and hard-offset action shadow |
| `--attention` | `#FFD51D` | Focus, warning, and small attention marks only |
| `--text-dark-secondary` | `#C7C0B3` | Secondary text on charcoal |
| `--text-paper-secondary` | `#646761` | Secondary text on paper |
| `--error-paper` | `#B42318` | Error on paper |
| `--error-dark` | `#E75B52` | Error on charcoal |
| `--rule-dark` | `#2A2E2E` | Dark-field rules |
| `--rule-paper` | `#B8B0A2` | Paper-field rules |

Validate actual contrast in code and CI. Do not rely on this table alone.

### Typography

Default open-source pairing:

- **Archivo Narrow:** display headings, route labels, folios.
- **Source Sans 3:** body, forms, instructions, buttons, brief.

Optional licensed pairing:

- Söhne Schmal + Söhne.

Rules:

- compressed display type is for short labels and headings only;
- body line length: 45–68 characters;
- sentence case for instructions;
- uppercase only for compact route/status labels;
- tabular numerals for IDs, dates, and zero-human disclosure;
- no monospace as a theme;
- never rely on browser-default control typography.

### Type scale

| Role | Desktop | Mobile |
|---|---:|---:|
| Display | 64–72 / 0.92 | 44–52 / 0.96 |
| H1 | 44–52 / 1.0 | 36–40 / 1.0 |
| H2 | 30–34 / 1.08 | 26–30 / 1.10 |
| H3 | 21–24 / 1.20 | 20–22 / 1.20 |
| Large body | 18 / 28 | 18 / 27 |
| Body | 16–17 / 25 | 16 / 24 |
| Route label | 12–13 / 16 | 12 / 16 |

### Geometry

- Base corner radius: `0`.
- Small functional radius allowed only for native focus clarity: maximum `2px`.
- Borders: 1px and 2px hard rules.
- Active step: 4px editorial-red edge or full red field.
- No glass, blur, gradients, glows, rounded floating cards, pill-heavy controls, or soft elevation system.
- A single 4px hard-offset document shadow may be used on paper surfaces.
- Use asymmetry through grid, folios, extended rules, and inspector placement—not random card offsets.

### Spacing

Use a 4px base with primary steps:

```text
4, 8, 12, 16, 24, 32, 48, 64, 96
```

Dense diagnostic rows may use 8–12px vertical spacing. Reading surfaces require 24–48px section rhythm.

## Desktop layout

Recommended shell:

| Region | Size |
|---|---:|
| Masthead | 72 px (4.5 rem) |
| Truth Rail | 32 px (2 rem) |
| Step spine | 216–240 px |
| Primary paper surface | 680–760 px |
| Route stage | Flexible remainder |
| Optional inspector | 320–360 px |
| Outer margin | 32–48 px |
| Gutter | 24 px |

The paper surface is anchored to the grid. Do not center every page as a floating card.

## Mobile layout

- Minimum supported width: 320 CSS px.
- 16px outer margins.
- One mode at a time.
- Current step shown as `Step 3 of 7 — Review assumptions`.
- List view is the default for paths.
- Path comparison stacks vertically.
- Inspector becomes a full-screen dialog or inline disclosure.
- No mandatory horizontal panning.
- No miniaturized desktop map.
- Sticky actions must not cover focus or content.

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
## State-message matrix

| State | Required structure | Example |
|---|---|---|
| Loading | object + action + non-time promise | `Reviewing the approved source segments. You may leave this page; the run record will preserve progress.` |
| Empty | what is missing + why + action | `No starting conditions are approved. Review the extracted candidates or continue without source material.` |
| Blocked | exact unmet rule + link/action | `Review 2 generated profiles before possible paths can be generated.` |
| Queued | current state + safe next action | `This run is queued. You can close the page and return from the project record.` |
| Reconnecting | what remains safe + retry | `Connection interrupted. Saved run data is intact. Reconnecting…` |
| Stopped | what completed + what did not | `The run stopped after scenario construction. No decision brief was created.` |
| Retryable failure | failed object + reason class + action | `Path P-03 did not pass the output schema. Retry this stage or inspect the run record.` |
| Terminal failure | boundary + support path | `The run cannot continue because source parsing failed validation. Replace the file or remove it.` |
| Unauthorized | denied object + safe destination | `You do not have permission to export this project. Return to the decision brief.` |
| Deleted | scope and irreversibility | `The source file was deleted. Its deletion record remains in the audit log.` |

Do not promise duration unless the system has a calibrated, monitored estimate.

## Generated-content labels

Generated content MUST carry a persistent origin label at the component level
when it can be copied or detached:

```text
GENERATED ACTION
GENERATED PROFILE
GENERATED EXPLANATION
FICTIONAL PROFILE RESPONSE — NOT A HUMAN QUOTATION
```

Quotation marks MUST NOT be used for generated profile or group responses unless
the label remains visible inside the copied/exported selection.

## Limitations writing

Limitations MUST be specific:

Weak:

> Results may be inaccurate.

Required:

> These paths were generated from the reviewed assumptions in this run. No person
> was interviewed or observed. The run does not estimate how common any path is,
> and the uploaded source material does not validate an outcome.

## Source and record language

- Exact page/section locations MAY identify where a starting condition came
  from.
- Source references MUST disappear from any visual treatment that would imply
  support for a generated outcome.
- Related run records MUST say `RELATED BY KEYWORD — NOT A CITATION`.
- “Trace,” “lineage,” and “evidence” MUST not be used for post-hoc keyword
  matches.

## Localization

Localization MUST preserve truth semantics, not literal word order. Each locale
requires review of:

- “human respondents: 0”;
- synthetic vs fictional distinctions;
- forecast/prediction terminology;
- source role;
- external validation boundary;
- prohibited public-opinion and human-research terms;
- date, number, and reading-order conventions.

Machine translation alone cannot approve a locale.

## Content acceptance

- exact approved copy inventory exists for every primary screen;
- no primary action uses generic or misleading verbs;
- errors identify a recoverable next action;
- detached generated content preserves an origin label;
- localization tests preserve truth meaning;
- the content linter blocks prohibited claims in UI, exports, fixtures, and
  marketing strings;
- comprehension tests show users can explain the workflow without technical
  simulation terminology.

## References

- [GOV.UK Design System - Notification banner](https://design-system.service.gov.uk/components/notification-banner/) - Warns against repeated banner overuse and supports putting task-critical information in the main journey.
- [GOV.UK Design System - Check answers](https://design-system.service.gov.uk/patterns/check-answers/) - Review-before-submit pattern used as the basis for the immutable run-configuration checkpoint.
- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) - Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.

---

## Project-specific content-system status (baseline `8b616dc7`)

The content system is normative. The current linter
([`.github/workflows/docs.yml`](../../.github/workflows/docs.yml))
checks the doc tree and the repo README for prohibited language.
The required coverage (UI strings, generated output, exports,
email templates, share previews, seed data, marketing pages,
documentation examples) is **TARGET**. Gate 5, owned by
`askthepeople-frontend-steward` and
`askthepeople-ai-eval-steward`.

### Current state — PARTIAL

- The CI linter in
  [`.github/workflows/docs.yml`](../../.github/workflows/docs.yml)
  blocks prohibited outcome language in `docs/product/`,
  `docs/design/`, `docs/release/`, and the repo root `README.md`.
- The linter does **not** cover AI outputs in the report
  agent, UI strings in `frontend/src/`, exports (CSV, JSON,
  PDF, DOCX, PNG), email templates, share previews, seed data,
  or marketing pages.
- The Truth Rail and the per-screen contextual statements
  ([`docs/product/PRODUCT_TRUTH_CONTRACT.md`](../product/PRODUCT_TRUTH_CONTRACT.md))
  are not yet rendered in the frontend.
- The disclosure block required by the contract is not
  automatically attached to detached artifacts.

### Required correction (per this doc and the audit)

- Expand the linter to cover every artifact surface listed
  above. Critical violations block artifact finalization and
  release.
- Render the Truth Rail and the per-screen contextual
  statements in the frontend.
- Attach the disclosure block to every detached artifact
  (PDF, DOCX, CSV, JSON, social card, email template).
- Comprehension-test program confirming users understand the
  qualitative-only nature of the routes and the
  non-respondent nature of the system.
- Localized and right-to-left support per
  [`docs/design/ACCESSIBILITY.md`](ACCESSIBILITY.md).

### Terminology enforcement

The terminology linter in
[`docs/product/TERMINOLOGY.md`](../product/TERMINOLOGY.md) defines
canonical terms, preferred terms, and prohibited terms. The CI
linter enforces a subset today. The full coverage is **TARGET**
and is part of gate 5.

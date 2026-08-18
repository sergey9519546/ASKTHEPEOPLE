---
title: "Route Grammar"
status: "Normative"
version: "1.1.0"
owner: "Product Design + Domain Engineering + Accessibility"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P1 'Inconsistent request validation'"
applies_to: "every UI route surface, every report, every export, every share preview"
---

# Route Grammar

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.

## Purpose

The route grammar is a semantic contract shared by domain objects, APIs, SVG
rendering, list views, exports, and assistive-technology representations. A
route is not decorative. Its shape, connection, label, color, and boundary
MUST carry the same meaning in every representation.

## Canonical sequence

```text
DECISION
  → REVIEWED STARTING CONDITIONS
  → ASSUMPTION GATES / UNCERTAINTY STATES
  → GENERATED DECISION LENSES
  → GENERATED ACTIONS
  → DECISION CONSIDERATIONS
  → QUESTIONS TO VALIDATE
  ⇥ OUTSIDE THE GENERATED RUN
```

## Node taxonomy

| Type | Code | Required visible label | Allowed incoming | Allowed outgoing | Prohibited implication |
|---|---|---|---|---|---|
| Decision | `D` | `DECISION / D-01` | none | condition | model recommendation |
| Source material | `SM` | `SOURCE MATERIAL / SM-01` | none | starting condition only | evidence for a path |
| Starting condition | `SC` | `STARTING CONDITION / SC-01` | source or user | assumption/scenario | verified outcome |
| Assumption gate | `A` | `ASSUMPTION / A-01` | condition | path branch | probability split |
| Critical uncertainty state | `U` | `UNCERTAINTY / U-01` | condition | scenario | forecast state |
| Generated profile | `GP` | `GENERATED PROFILE / GP-01` | approved profile set | synthetic action | person/respondent |
| Synthetic action | `SA` | `GENERATED ACTION / SA-01` | scenario/profile | consideration | observed behavior |
| Possible path | `P` | `POSSIBLE PATH / P-01` | assumption/scenario | actions/considerations | likelihood |
| Decision consideration | `DC` | `CONSIDERATION / DC-01` | path | validation question | finding from people |
| Validation question | `VQ` | `QUESTION TO VALIDATE / VQ-01` | consideration | external handoff | completed validation |
| Human-validation boundary | `HV` | `OUTSIDE GENERATED RUN` | question | none in run | product recruited/measured people |
| Related run record | `RR` | `RELATED RUN RECORD / RR-01` | diagnostic link only | none | citation/lineage/corroboration |

## Edge taxonomy

Only these semantic edges may render:

| Relation | Meaning | Visual treatment |
|---|---|---|
| `DEFINES` | user statement defines a decision | solid neutral |
| `INFORMS` | source segment informs a condition | thin neutral |
| `CONSTRAINS` | condition constrains a scenario | solid neutral |
| `BRANCHES_ON` | assumption or uncertainty creates alternatives | equal-weight route branch |
| `APPLIES_LENS` | generated profile conditions an action | directly labeled |
| `SEQUENCES` | synthetic actions occur in generated order | equal-weight route line |
| `SURFACES` | path surfaces a consideration | dashed or solid by system standard, not strength |
| `PRODUCES_QUESTION` | consideration becomes a validation question | neutral arrow |
| `HANDS_OFF` | question leaves synthetic run | broken boundary plus external arrow |
| `RELATED_BY_KEYWORD` | diagnostic relation only | inspector/list link; never a route-support edge |

`PROVES`, `VALIDATES`, `CORROBORATES`, `REPRESENTS`, `PREDICTS`, and
`SUPPORTED_BY_MAJORITY` are not valid route relations.

## Quantitative non-encoding rules

- All primary path strokes MUST have equal visual weight.
- Line thickness MUST NOT encode count, support, certainty, prevalence, or score.
- Node size MUST NOT encode importance or population size.
- Spatial distance MUST NOT imply time, probability, similarity, or causal force.
- Route order MUST NOT imply ranking.
- Yellow MUST indicate active/current focus, not “best” or “most likely.”
- Teal and orange MAY distinguish route families only when each path also has a
  visible text ID or pattern.
- Animations MAY show traversal sequence but MUST NOT simulate real-time social
  activity or “AI thinking.”

## Canonical seven-step journey

### Step 1 — State the decision

**Page title:** `State the decision`  
**Primary action:** `Review source material`  
**Secondary action:** `Continue without source material`

Required UI:

- decision question;
- intended use;
- owner;
- time horizon;
- stakes;
- reversibility;
- scope and exclusions;
- source upload;
- contextual truth statement.

Block progress when the question contains multiple decisions, prohibited use, or no intended use.

### Step 2 — Review source material

Default to a **source-to-starting-condition ledger**, not a graph.

Columns:

- Source location
- Candidate starting condition
- System interpretation
- Flags
- Accept / Edit / Ignore

`View source map` is optional and user-invoked. The map uses neutral lines and may connect source segments only to starting conditions.

Primary action: `Review assumptions`

### Step 3 — Review assumptions

Sections:

- accepted starting conditions;
- assumptions;
- critical uncertainties;
- generated profiles;
- scenario rules;
- coverage tasks.

Show a task status list:

```text
READY         Decision question
READY         Source material
NEEDS REVIEW  2 assumptions
NEEDS REVIEW  1 generated profile
READY         Scenario rules
```

Primary action: `Check this run`

### Step 4 — Check this run

Use a check-answers pattern before expensive generation.

Show:

- decision;
- sources and hashes;
- starting conditions;
- assumptions;
- uncertainties and states;
- profiles;
- scenario rules;
- exclusions;
- model/method configuration at a human-readable level;
- estimated run cost range;
- permanent truth block.

Primary action: `Generate possible paths`

The user must confirm:

```text
I understand that this run generates synthetic possibilities and does not ask, measure, or predict people.
```

### Step 5 — Explore possible paths

**Page title:** `Possible paths under your reviewed assumptions`

Fixed explanation:

```text
These are generated possibilities. Color, position, spacing, order,
and line length do not show likelihood, public support, or quality.
```

Required modes:

- Map view
- List view
- Compare runs

List view is canonical and must contain all information and actions available in the visual map.

Primary action: `Create decision brief`

### Step 6 — Read and question the brief

The brief comes first. Follow-up tools sit after the document, not as a dominant chat surface.

Sections follow the brief method in Section 28.

Primary action: `Prepare human validation`

Secondary action: `Ask about this brief`

### Step 7 — Prepare human validation

The charcoal route ends before this step. The screen uses a separate light-cream transfer field.

Primary action: `Create research handoff`

Secondary outputs:

- Export discussion guide
- Export questionnaire draft
- Copy assumptions to test
- Export path-validation matrix

Completion state:

```text
RESEARCH HANDOFF PREPARED
No human validation has occurred in this application.
```

## Route-map grammar

The map is a controlled semantic system.

| Object | Identifier | Geometry | Meaning |
|---|---|---|---|
| Decision | `D-01` | Solid warm-paper rectangle | Single origin of the run |
| Source material | `S-01` | Outlined document block | Uploaded input asset |
| Starting condition | `SC-01` | Short neutral rectangular block | Reviewed input condition |
| Assumption | `A-01` | Diamond or square junction | Only object allowed to create a branch |
| Critical uncertainty | `U-01` | Split gate with labeled states | Variable deliberately varied across paths |
| Generated profile | `GP-01` | Rectangular labeled lens | Decision-relevant constraint set, not a person |
| Possible path | `P-01` | Directly labeled lane | Qualitative synthetic path |
| Synthetic action | `SA-01` | Equal-weight route segment/block | Generated action in sequence |
| Decision consideration | `DC-01` | Bordered block | Issue surfaced within the run |
| Validation question | `VQ-01` | Warm-paper question block | Question for actual research |
| Related run record | `RR-01` | Inspector row | Keyword/semantic relation, not citation |
| Human handoff | — | White external field with broken boundary | Outside synthetic run |

### Route rules

1. All possible-path lines have equal visible weight.
2. Each lane is directly labeled with `P-##`; color is redundant.
3. No edge width, opacity, animation speed, length, vertical position, or order may encode probability or importance.
4. Teal and orange distinguish route families only. Neither means positive, negative, safe, risky, majority, or minority.
5. Source material never connects directly to a path, action, consideration, or brief statement.
6. Branches occur only at reviewed assumptions or critical uncertainties.
7. The route terminates before the human-validation field with a visible 8–16 px break.
8. No Sankey diagram, force-directed graph, chord diagram, confidence band, funnel, poll bar, heat map, or weighted network.
9. The legend must state: `Spacing shows sequence only. It does not show time or likelihood.`
10. Map interactions have an equivalent named control in the semantic list.

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
## Map/list parity

The semantic list is the source of truth. The SVG route map is a synchronized
visual view.

For every path, the list MUST expose:

1. path ID and title;
2. reviewed inputs;
3. branch assumption or uncertainty;
4. applied generated profiles;
5. ordered synthetic actions;
6. decision considerations;
7. missing information and disconfirming conditions;
8. questions to validate;
9. limitations;
10. status and version metadata.

The list MUST be fully usable with CSS disabled and without interpreting the
SVG. The SVG MAY be `aria-hidden="true"` when the list contains complete
equivalent information.

## Geometry and collision rules

- Routes use orthogonal or intentionally angled segments; avoid organic curves
  that suggest flow volume.
- Crossing routes require a bridge/gap treatment so they are not mistaken for
  junctions.
- A junction exists only when a labeled semantic node exists.
- Direct labels are preferred over detached legends.
- Labels MUST not overlap routes at supported viewports.
- Collapsed mobile routes become ordered sections; users are not required to pan
  a miniature desktop map.
- The human-validation boundary contains a visible physical break of at least
  8 CSS pixels at standard zoom.

## Interaction model

- Clicking or focusing a path selects the corresponding semantic list entry.
- Selection is expressed by outline, text, and state, not color alone.
- Hover never reveals information that is unavailable by keyboard.
- A visible route may use a transparent 44-pixel hit area while retaining a
  narrow visual stroke.
- Focus enters named controls or list items, never raw decorative SVG segments.
- Compare mode accepts exactly two run/path variants and states the changed
  assumption in text.

## Automated validation

A route payload fails when:

- a prohibited edge exists;
- a path lacks a branch basis;
- a source links directly to a consideration or outcome;
- multiple paths differ only in wording;
- route styling encodes a numeric field not approved by this grammar;
- an external-human node appears inside the synthetic run;
- a related run record is rendered as a footnote or support link;
- map and list payloads diverge.

## Acceptance evidence

- property tests enumerate every allowed and prohibited edge pair;
- visual tests confirm equal path weights;
- screen-reader tests can navigate every path in sequence;
- comprehension tests show no likelihood inference from color, length, order,
  or thickness;
- export diagrams contain the route legend and human-validation break;
- mobile users can complete the entire path review without horizontal panning.

## References

- [OECD Strategic Foresight Toolkit for Resilient Public Policy](https://www.oecd.org/en/publications/foresight-toolkit-for-resilient-public-policy_bcdd9304-en.html) - Scenario and stress-testing guidance that treats disruptions and alternative futures as hypothetical, not predictions.
- [UK Government Futures Toolkit](https://www.gov.uk/government/publications/futures-toolkit-for-policy-makers-and-analysts/the-futures-toolkit-html) - Practical scenario-design guidance; scenarios are possible futures rather than predictions or plans.
- [ONS Service Manual - Using colours in charts](https://service-manual.ons.gov.uk/data-visualisation/colours/using-colours-in-charts) - Color restraint, contrast, and non-color redundancy for data and route visualization.
- [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/) - Current accessibility conformance target for the product.

---

## Project-specific route-grammar status (baseline `8b616dc7`)

The route grammar is normative. The Civic Wayfinding design
system
([`docs/design/DIRECTION_C.md`](DIRECTION_C.md)) is implemented
in `frontend/src/`; the qualitative-only constraint has no
automated check on rendered SVG; the canonical semantic route
list is **TARGET**. Gate 1 + gate 5, owned by
`askthepeople-frontend-steward`.

### Current state — PARTIAL

- Frontend is Vue 3 + Vite + vue-router. Built into
  `frontend/dist/` and served by
  [`backend/app/__init__.py:317-325`](../../backend/app/__init__.py:317).
- Route visualization in the home view uses CSS-driven animations;
  D3 is used in `GraphPanel.vue` for graph rendering. The design is
  implemented in CSS and SVG.
- The semantic route list as a first-class accessible
  alternative is **not yet rendered**. There is no parity test
  asserting that every fact and action in the visual map is
  reachable in the list by keyboard and screen reader.
- The qualitative-only constraint has no automated check.
- Mobile defaults to the map view today; the doc requires
  defaults to the list.
- The disclosure block required by the contract is not
  automatically attached to exported report files, social
  cards, or share previews.

### Required correction (per this doc and ADR-0006)

- A canonical semantic route list at the API or JSON-LD level
  that the visual map and the list view both consume.
- Parity test in CI asserting every map fact has a list entry,
  and vice versa.
- Keyboard-only and screen-reader-only navigation of every
  map fact and action.
- Mobile default to the list view.
- WCAG 2.2 conformance verified per
  [`docs/design/ACCESSIBILITY.md`](ACCESSIBILITY.md).
- Automated check on rendered SVG that line width, color,
  position, spacing, order, count, and placement do not
  communicate probability, support, prevalence, confidence, or
  rank.

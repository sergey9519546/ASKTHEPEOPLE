---
title: "Decision Chamber Experience Design"
status: "Proposed / Revision Required"
version: "1.0.2"
owner: "Product Design + Frontend + Architecture"
last_reviewed: "2026-08-08"
review_cycle: "Per major experience change"
research_cutoff: "2026-08-08"
baseline_commit: "24915d379e97d903a6f0f86995e8c53366ef10e0"
applies_to: "scenario preparation, execution, path exploration, decision brief, and external research handoff"
---

# Decision Chamber Experience Design

**Status:** PROPOSED / REVISION REQUIRED

**Date:** 2026-08-08

**Scope:** Scenario preparation, run, path exploration, decision brief, and human-research handoff

**Visual reference:** [`docs/design/references/decision-chamber-paths-approved.png`](../../design/references/decision-chamber-paths-approved.png)

The referenced image is the approved visual direction for the **Possible Paths**
state only. It is not approval for the complete information architecture,
runtime capabilities, data contracts, or institutional terminology proposed
below. Those areas remain subject to product-truth, security, architecture,
accessibility, and implementation review.

## 1. Decision

Build a **Progressive Hearing** experience.

The product begins as a guided editorial docket. The user must review the
decision, source-derived starting conditions, assumptions, critical
uncertainties, generated decision lenses, rules, and exclusions before a run
can begin. Once the docket is cleared, the interface opens into a spatial
Decision Chamber for generated-path exploration. A subordinate public record
supports audit and comparison. Human-research preparation occupies a visibly
separate transfer field outside the synthetic chamber.

This is one persistent case record, not a sequence of unrelated dashboards.
Entertainment comes from consequence, spatial reveal, controlled intervention,
and comparative exploration. It does not come from simulated crowds, scores,
constant activity, or game-like reward mechanics.

## 2. Authority and state legend

This specification is subordinate to:

1. `docs/product/PRODUCT_TRUTH_CONTRACT.md`;
2. `docs/product/USE_POLICY.md`;
3. `docs/security/` and `docs/privacy/`;
4. `docs/product/METHODOLOGY.md`;
5. `docs/design/DIRECTION_C.md`, `ROUTE_GRAMMAR.md`, and
   `CONTENT_SYSTEM.md`;
6. accepted ADRs under `docs/architecture/adr/`.

State terms in this document:

- **CURRENT:** implemented and observable in the repository.
- **PARTIAL:** present but materially below this specification.
- **TARGET:** the intended end state.
- **TRANSITION:** an intentionally temporary bridge from CURRENT to TARGET.

Where this design and a higher authority disagree, the higher authority wins.

## 3. Problem statement

### 3.1 CURRENT

The same decision journey is represented by a five-step in-page workflow and
separate assumption, run, report, and interaction routes
(`frontend/src/router/index.js:17-44`,
`frontend/src/views/MainView.vue:41-169`). These shells duplicate navigation,
status, source-map switching, and content framing.

The preparation experience foregrounds named generated profiles, biographies,
professions, and topic chips (`frontend/src/components/Step2EnvSetup.vue:65-98`)
instead of decision-relevant constraint lenses. Advanced channel parameters
appear as dashboard cards (`frontend/src/components/Step2EnvSetup.vue:172-252`).

The run experience has improved into a chronological record, but generated
activity, possible paths, path comparison, and the final brief still occupy
different conceptual and navigational systems
(`frontend/src/components/Step3RunWayfinder.vue:55-206`,
`frontend/src/components/Step4Report.vue:1-461`,
`frontend/src/components/Step5Interaction.vue:1-749`).

The underlying runtime exposes useful advanced capabilities, including saved
actions, detailed run status, diagnostics, run forking, and recorded scenario
interventions (`frontend/src/api/simulation.js:114-183,233-259`,
`backend/app/api/routes/execution_routes.py:389-448`). They do not yet form a
coherent user experience.

### 3.2 Release-blocking semantic gaps

This redesign is not authorized to conceal the following CURRENT gaps with new
labels or visuals:

| Gap | CURRENT evidence | Required TARGET behavior |
|---|---|---|
| Continue without sources | Home permits it, but the workspace and backend require files (`frontend/src/views/Home.vue:142,523`; `frontend/src/views/MainView.vue:408`; `backend/app/api/graph.py:247`) | A valid no-source path with an explicit empty source ledger |
| URL source provenance | The server fetches content, while Home later uploads a text placeholder containing only the URL (`backend/app/api/sources.py:79`; `backend/app/services/url_fetcher.py:389`; `frontend/src/views/Home.vue:668`) | One canonical fetched source record with location, content hash, extraction status, and no client-authored substitute |
| Source review | Graph construction starts automatically and Step 1 has no accept/edit/ignore disposition (`frontend/src/views/MainView.vue:487`; `frontend/src/components/Step1GraphBuild.vue:327`) | Explicit source-to-starting-condition review before graph or scenario use |
| Assumption review | Preparation starts on mount; generated configuration is inspect-only (`frontend/src/components/Step2EnvSetup.vue:136,291,1311`) | Editable, versioned, approved assumptions and uncertainty states |
| Possible paths | Paths currently exist as free-text report material rather than first-class persisted objects (`backend/app/services/report_agent.py:658`; `docs/architecture/data-model.md:594`) | Canonical path schema, review state, coverage ledger, disconfirming conditions, and list/map parity |
| Stopped attempts | Several client branches treat stopped work as complete or reviewable (`frontend/src/components/Step3Simulation.vue:103,443`; `frontend/src/components/Step3RunWayfinder.vue:402`; `frontend/src/views/Home.vue:767`) | Stopped remains incomplete; partial artifacts are inspectable but no final brief is created |
| Brief generation guard | The report route does not require a canonically completed attempt (`backend/app/api/report.py:99`) | Server-side completion and approval guard before final brief generation |
| Human-research handoff | The implemented terminal step is follow-up generation, not a research handoff (`frontend/src/views/MainView.vue:202-207`) | A real handoff builder with method, guide, questions, validation matrix, and external boundary |
| Version-pinned explanation | Brief follow-up omits `report_id`, and backend selection is not version-pinned (`frontend/src/components/Step5Interaction.vue:1168`; `backend/app/services/report_agent.py:2170,2895`) | Every explanation is bound to an immutable report version and disclosed model/prompt version |
| Run map | The current map reads a legacy record that current runs may not populate (`frontend/src/components/OpinionMap.vue:127`; `frontend/src/components/Step3Simulation.vue:377`; `backend/app/services/simulation_runner.py:436`) | The route plate and record read canonical current-run objects, with empty and unavailable states distinguished |

The implementation plan must sequence domain and API corrections before any
surface claims the corresponding capability. A TRANSITION interface may show a
capability as unavailable or partial; it may not simulate the TARGET behavior
from client-side guesses.

### 3.3 TARGET

One decision has one chamber, one permanent truth layer, one canonical object
model, and several named modes. The user can always answer:

1. What am I reviewing?
2. What originated from me, a source, or the synthetic run?
3. What remains unresolved?
4. What changed between attempts?
5. What should be checked with people outside the run?
6. What is my next action?

## 4. Product thesis

The product's durable advantage is not synthetic activity by itself. It is the
ability to make a decision owner's assumptions reviewable, generate several
equal-weight possible paths under those assumptions, expose what could be
missing, and prepare better external research.

The experience should be describable as:

> It makes you sign off on your assumptions, shows several ways they could
> unfold, and helps you decide what to check with people.

The emotional sequence is:

```text
ACCOUNTABILITY -> ANTICIPATION -> EXPLORATION -> SCRUTINY -> DEPARTURE
```

The surface sequence is:

```text
CREAM Docket -> CHARCOAL Chamber -> LIGHT-CREAM Public Gallery
```

## 5. Approaches considered

### 5.1 Decision Docket only

A versioned working paper in which every starting condition and assumption is
accepted, edited, or excluded before generation.

- Strengths: highest clarity, provenance, accessibility, and truth safety.
- Weaknesses: too procedural as the complete experience; insufficiently
  memorable after the run begins.

### 5.2 Branch Table only

A spatial route field is the primary product. The decision, assumptions,
uncertainty gates, possible paths, considerations, and validation questions are
directly manipulable.

- Strengths: most expressive and memorable.
- Weaknesses: highest risk of visual misinterpretation; difficult on mobile;
  weak preparation discipline if opened too early.

### 5.3 Playback Chamber only

The run is a replayable record with checkpoints, annotations, and attempt
forking.

- Strengths: strongest audit and comparison capability.
- Weaknesses: too forensic for first-time use and dependent on durable event
  persistence that is not yet complete.

### 5.4 Chosen synthesis: Progressive Hearing

Use the Decision Docket as the guided opening, the Branch Table as the main
post-run chamber, and Playback as an advanced public-record mode. This is more
useful and more interesting than any of the three alone.

## 6. Information architecture

### 6.1 TARGET route model

```text
Decisions
  Decision Chamber
    Docket
      Decision
      Sources
      Assumptions
      Run order
    Chamber Floor
      Run status
      Possible paths
      Compare attempts
    Decision Brief
    Public Gallery
      Human-research handoff
      Decision owner's conclusion
    Public Record
```

The named chamber modes are:

- `docket`
- `run-order`
- `run`
- `paths`
- `compare`
- `brief`
- `handoff`
- `record`

### 6.2 TRANSITION route model

Existing public URLs remain valid while the shared chamber shell lands. Route
adapters map current project, simulation, and report identifiers into a single
client-side chamber context. Legacy views redirect into the correct mode after
their required data resolves.

The transition must not invent a canonical `decision_id` while the backend
still treats project, simulation, and report as separate records. The eventual
decision aggregate is TARGET architecture, not CURRENT fact.

### 6.3 Navigation rule

The Agenda Spine shows the chamber modes, not implementation resources. It may
show locked, available, current, needs-review, partial, failed, and complete
states. It must never show percentage completion for epistemic work.

## 7. Desktop shell

The reference image becomes an interactive composition rather than a static
poster.

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Masthead + permanent Truth Rail                                     │
├──────────────┬──────────────────────────────────┬────────────────────┤
│ Agenda Spine │ Primary chamber surface          │ Inspector /        │
│ 216–240 px   │ flexible                         │ Public Gallery      │
│              │                                  │ 320–360 px         │
├──────────────┴──────────────────────────────────┴────────────────────┤
│ Public Record disclosure / comparison bench                         │
└──────────────────────────────────────────────────────────────────────┘
```

Rules:

- The masthead is 64 px; the Truth Rail is 48–52 px.
- The Agenda Spine is dark and persistent on desktop.
- Cream paper is grid-anchored, not centered as a floating card.
- The Chamber Floor receives the largest region after the docket is cleared.
- The inspector is absent until an object is selected.
- The Public Gallery replaces the inspector when the user prepares external
  research.
- The Public Record is a named disclosure, not a permanent telemetry strip.

## 8. Experience choreography

### 8.1 Scene 1 — Enter the docket

The opening viewport contains:

- the decision question;
- intended use, owner, horizon, stakes, reversibility, scope, and exclusions;
- source-material intake;
- a short unresolved-items index;
- one primary action.

The decision question remains pinned as the docket title throughout the
chamber. Editing it after a run exists creates a new draft and visibly marks
downstream attempts as belonging to the prior wording.

### 8.2 Scene 2 — Review source material

The default is a source-to-starting-condition ledger. Each row contains:

- stable identifier;
- source location;
- extracted segment;
- candidate starting condition;
- system interpretation;
- flags;
- `Accept`, `Edit`, and `Ignore` actions.

The optional source map is a secondary foldout. It may connect source segments
only to starting conditions. It never connects directly to a path,
consideration, or brief statement.

### 8.3 Scene 3 — Redline assumptions

The user reviews:

- accepted starting conditions;
- declared assumptions;
- critical uncertainties and named states;
- generated decision lenses;
- scenario rules;
- exclusions;
- coverage tasks.

Generated lenses are compact `GP-##` rows containing only decision-relevant
constraints. Fictional names, handles, biographies, portraits, and demographic
galleries are removed from the primary flow. Additional generated detail is
available only in the inspector and is always labeled synthetic.

#### Signature interaction: Redline Commit

Selecting a row opens an inline review margin:

```text
SOURCE       Exact source-derived wording, when present
ASSUMPTION   Proposed interpretation
OWNER EDIT   User's revision
```

Committing a disposition stores the revision, replaces the row's neutral edge
with a static red review edge, and advances to the next unresolved item. A
120–160 ms opacity replacement is allowed, but the edge does not draw. The same
action is available through named buttons and keyboard operation.
Reduced-motion mode renders the committed state immediately.

An edited item displays its downstream dependency count as a neutral text
statement such as `Affects 2 draft paths`; it does not display a score or
weighted graphic.

### 8.4 Scene 4 — Check the run order

Before generation, a single cream check-answers surface shows:

- the decision and version;
- sources and hashes;
- starting conditions;
- assumptions and uncertainty states;
- decision lenses;
- rules and exclusions;
- human-readable model and method configuration;
- estimated cost range and duration range;
- the permanent truth block;
- unresolved or invalid items.

The primary action is `Generate possible paths`. It is unavailable until
blocking items are resolved. The user confirms that this run produces
synthetic possibilities and does not collect human evidence.

### 8.5 Scene 5 — Open the chamber

After confirmation, one restrained mode transition occurs:

1. the cream docket contracts into the Agenda Spine;
2. the charcoal Chamber Floor occupies the central stage;
3. the Public Gallery boundary appears on the right;
4. the decision origin remains fixed at the top of the composition.

The transition uses opacity and transform only, lasts no longer than 360 ms,
and runs once. It contains no bounce, particles, glow, audio, or simulated
intelligence.

### 8.6 Scene 6 — Conduct the run

During generation, the Chamber Floor shows factual server stages:

```text
1/5 Checking the docket              COMPLETE
2/5 Building scenario candidates     IN PROGRESS
3/5 Generating possible paths        NOT STARTED
4/5 Checking coverage and language   NOT STARTED
5/5 Preparing review                 NOT STARTED
```

Each stage can expose plain-language detail in the inspector. Raw logs and
technical diagnostics remain inside the Public Record.

The run may be left and reopened. Connection state and server execution state
are separate. Losing the browser connection must never imply that the server
stopped.

#### Deferred TARGET: Introduce a changed condition

Changed-condition injection is not part of the first vertical slices. No
active control, route, or optimistic placeholder is permitted until durable
run checkpoints, immutable intervention identity, provenance, stop/fence
handling, and rerun semantics have a separately approved specification and
release evidence. The current experience may explain that a new reviewed run
will be required; it must not mutate a run or imply that live injection is
available.

### 8.7 Scene 7 — Explore possible paths

The canonical representation is a semantic list. The desktop Chamber Floor
renders the same objects as an optional spatial route plate.

All path lanes:

- use equal visible weight;
- are labeled directly with `P-##`;
- branch only from reviewed assumptions or critical uncertainties;
- terminate before the Public Gallery;
- never use line weight, order, position, color, length, or motion to express
  likelihood, support, confidence, or quality.

#### Signature interaction: Route Incision

Selecting a path draws one red line from the decision origin to the selected
endpoint in 160–220 ms. Other paths remain present with neutral styling.
Selecting another path replaces the incision rather than layering motion.

The selected path inspector contains:

- branch reason;
- ordered synthetic actions;
- surfaced considerations;
- conflicts;
- missing information;
- disconfirming conditions;
- validation questions;
- related run records with explicit non-citation labels.

#### Cross-examine this path

This action opens a structured question set:

1. Which reviewed assumption created this branch?
2. Which changed condition would break it?
3. Which relevant possibility may be absent?
4. Which source gap matters?
5. What should be checked with people?

Answers explain existing run artifacts. They do not add human evidence or
silently create new path facts.

### 8.8 Scene 8 — Compare attempts

The later comparison bench accepts **exactly two** completed related runs.
Viewport size never changes that cardinality. One, three, or more inputs are
invalid and the future request schema must reject them with a bounded `422`.
This scene remains unavailable until stable server-owned semantic identifiers,
unambiguous predecessor rules, exact approved path-set/review hashes, and
shared decision lineage exist for both runs.

Comparison aligns objects by stable semantic identifiers:

- decision version;
- changed assumptions;
- uncertainty states;
- interventions;
- path branch reasons;
- considerations;
- validation questions.

The view begins with a textual change ledger. A forked route plate is
secondary. Shared history remains neutral; divergence uses a single red cut.
No winner, score, ranking, or automated recommendation is shown.

### 8.9 Scene 9 — Read the decision brief

The brief is a cream editorial document and is the default post-run surface.
It contains:

- decision and scope;
- reviewed starting conditions;
- assumptions and critical uncertainties;
- possible paths;
- decision considerations;
- conflicts and missing information;
- disconfirming conditions;
- limitations;
- questions for external research;
- run and configuration record.

`Ask about this brief` follows the document. Chat never dominates the page.
Generated-profile and group-response tools are secondary disclosures and are
not required to understand the brief.

### 8.10 Deferred TARGET — Enter the Public Gallery

The charcoal route stops 8–16 px before the light-cream transfer field. This
visual boundary remains part of the design language, but the interactive
handoff builder and any external-evidence importer are unavailable in the
first vertical slices. A later approved release may convert considerations
into:

- interview questions;
- assumptions to test;
- disconfirming questions;
- missing-information requests;
- a discussion guide;
- a questionnaire draft;
- a path-validation matrix.

No active `Add to research handoff` control is shown until that later release.
When implemented, a direct button and keyboard path are mandatory; dragging
may never be the only method.

The completion statement is:

```text
RESEARCH HANDOFF PREPARED
No human validation has occurred in this application.
```

### 8.11 Deferred TARGET — Write the owner's conclusion

The decision-owner conclusion and external-human-evidence import are later
releases. The first vertical slices expose neither a conclusion editor nor an
evidence-import affordance. A later conclusion remains a separate
human-authored artifact with author, date, exact selected artifact lineage,
and separately governed external evidence. AI assistance may be opt-in editing
support only and cannot silently author or approve it.

## 9. Entertainment and restraint

### 9.1 Sources of engagement

- **Anticipation:** unresolved docket items visibly prevent the chamber from
  opening.
- **Material consequence:** revisions show exactly which downstream objects
  become stale.
- **Spatial reveal:** the chamber opens only after the run order is confirmed.
- **Agency:** users focus paths, cross-examine assumptions, introduce changed
  conditions, and fork attempts.
- **Discovery:** path details unfold in layers rather than appearing as a
  dashboard wall.
- **Comparative tension:** the user sees where two attempts diverge after one
  controlled change.
- **Closure:** considerations physically and semantically stop at the external
  research boundary.

### 9.2 Prohibited entertainment

- scores, badges, streaks, rewards, or completion confetti;
- simulated human audiences or testimony;
- personality portraits or avatar walls;
- popularity, consensus, sentiment, or confidence graphics;
- pulsing agents, typing indicators, moving particles, or live-crowd theater;
- sound effects or autoplay;
- dramatic language that exceeds the stored artifacts;
- seals, flags, certificates, voting mechanics, or imitation of a public
  authority.

## 10. Visual system

### 10.1 Palette

Initial implementation follows the approved design tokens:

| Token | Value | Role |
|---|---:|---|
| Ink | `#111313` | Main chamber and primary paper text |
| Paper | `#F2EBDD` | Docket, forms, and brief |
| Transfer paper | `#F7F0E2` | Public Gallery and human handoff |
| Signal | `#F04B3D` | Brand field, current step, selected route, one primary action |
| Signal strong | `#FF5D4F` | Pressed or hover action field only |
| Signal deep | `#982D24` | Accessible red text and hard-offset action edge |
| Attention | `#FFD51D` | Focus, warning, and small attention marks only |

No component may introduce another semantic accent. Visual QA must test the
tokens in real screenshots against the approved reference; if a neutral shifts
green or a red becomes fluorescent, the token is corrected at the root rather
than locally overridden.

### 10.2 Typography

- Archivo Narrow for display headings, folios, route IDs, and compact labels.
- Source Sans 3 for body, forms, instructions, buttons, and the brief.
- Display type is short and large; it does not carry paragraphs.
- Sentence case is used for instructions.
- Uppercase is reserved for route IDs, compact state labels, and truth cells.
- Tabular numerals are used for IDs, dates, and zero-human disclosure.
- Body measure is 45–68 characters.

The CURRENT Staatliches and Barlow dependency pair is TRANSITION styling, not
the TARGET typography system (`frontend/package.json:13-14`).

### 10.3 Materiality

- hard 1 px and 2 px rules;
- zero radius, with a maximum 2 px functional exception;
- one optional 4 px hard-offset shadow for paper documents;
- restrained paper grain applied through a fixed pointer-inert layer;
- grayscale architectural imagery used only as a sectional divider or empty
  state, never behind dense text;
- no gradients, glass, blur, glow, soft shadows, rounded floating cards, or
  pill-heavy navigation.

## 11. Motion contract

Motion communicates sequence and state only.

| Motion | Duration | Purpose |
|---|---:|---|
| Redline commit | 120–160 ms | Replace an explicit review state |
| Chamber open | 280–360 ms once | Change from review mode to exploration mode |
| Route incision | 160–220 ms | Trace the selected qualitative path |
| Inspector replace | 120–160 ms | Preserve spatial context while changing selection |

Only transform and opacity may animate. No continuous motion is permitted.
Reduced-motion mode renders final states immediately.

## 12. Canonical client model

The visual route plate and semantic list consume the same canonical objects.

```ts
type Origin =
  | "USER_STATED"
  | "SOURCE_EXTRACTED"
  | "ASSUMPTION_DECLARED"
  | "GENERATED_GENERATED"
  | "EXTERNAL_HUMAN_EVIDENCE"
  | "SYSTEM_METADATA";

type ChamberObject = {
  id: string;
  origin: Origin;
  epistemicRole: string;
  label: string;
  state: "draft" | "needs_review" | "accepted" | "ignored" | "stale";
  parentIds: string[];
  version: number;
};

type RunState =
  | "DRAFT"
  | "NEEDS_REVIEW"
  | "BLOCKED"
  | "READY"
  | "QUEUED"
  | "PREPARING"
  | "EXTRACTING"
  | "REVIEWING_CONDITIONS"
  | "GENERATING_PROFILES"
  | "CONSTRUCTING_SCENARIOS"
  | "GENERATING_PATHS"
  | "SYNTHESIZING"
  | "VALIDATING_OUTPUT"
  | "GENERATING_BRIEF"
  | "STOP_REQUESTED"
  | "STOPPED"
  | "FAILED_RETRYABLE"
  | "FAILED_TERMINAL"
  | "COMPLETED"
  | "ARCHIVED";

type RunPresentationSummary =
  | "preflight"
  | "queued"
  | "active"
  | "attention"
  | "terminal";

type RunAttempt = {
  id: string;
  decisionVersion: number;
  state: RunState;
  presentationSummary: RunPresentationSummary;
  outputOrigin: "synthetic";
  humanRespondentCount: 0;
  isForecast: false;
  isPublicOpinionMeasure: false;
  isCausalEvidence: false;
  sourceRole: "starting_conditions_only";
  humanValidationScope: "external_to_synthetic_run";
};
```

The exact production schema is defined by the typed API and domain model, not
by this illustrative client shape. `presentationSummary` is a lossy display
group only; state guards, available actions, brief eligibility, and terminal
meaning must use the canonical `state`. Client code must not fabricate path
facts, consensus values, provenance, or final statuses from progress
percentages.

The summary mapping is exhaustive and display-only:

| `RunPresentationSummary` | Canonical `RunState` values |
|---|---|
| `preflight` | `DRAFT`, `NEEDS_REVIEW`, `BLOCKED`, `READY` |
| `queued` | `QUEUED` |
| `active` | `PREPARING`, `EXTRACTING`, `REVIEWING_CONDITIONS`, `GENERATING_PROFILES`, `CONSTRUCTING_SCENARIOS`, `GENERATING_PATHS`, `SYNTHESIZING`, `VALIDATING_OUTPUT`, `GENERATING_BRIEF`, `STOP_REQUESTED` |
| `attention` | `FAILED_RETRYABLE` |
| `terminal` | `STOPPED`, `FAILED_TERMINAL`, `COMPLETED`, `ARCHIVED` |

`terminal` is never rendered as complete unless canonical state is
`COMPLETED`, or the immutable event record proves that an `ARCHIVED` run's
last pre-archive state was `COMPLETED`.

## 13. Component architecture

### 13.1 Shell components

- `DecisionChamberShell` — owns layout, mode, responsive transformation, and
  route context; contains no domain derivation.
- `ChamberMasthead` — full product lockup and decision title.
- `TruthRail` — persistent invariant disclosure.
- `AgendaSpine` — named modes and their server-backed availability.
- `ChamberInspector` — selected-object details and actions.
- `PublicRecordDrawer` — chronological audit and technical disclosures.

### 13.2 Docket components

- `DecisionDocket`
- `SourceConditionLedger`
- `DocketItemRow`
- `RedlineReviewMargin`
- `DecisionLensList`
- `RunOrderReview`
- `UnresolvedItemIndex`

### 13.3 Run and path components

- `RunStageList`
- `CanonicalPathList`
- `RoutePlate`
- `PathInspector`
- `PathCrossExamination`

`ChangedConditionForm` and `AttemptComparisonBench` are deferred TARGET
components. They are not registered, rendered, or feature-advertised in the
first vertical slices.

### 13.4 Brief and handoff components

- `DecisionBriefDocument`
- `BriefQuestionDisclosure`

`PublicGallery`, `ResearchHandoffBuilder`, and `DecisionOwnerConclusion` are
deferred TARGET components. The route break may be shown as a non-interactive
truth boundary, but no external-evidence or conclusion workflow is implied.

### 13.5 State boundary

A single chamber composable or store coordinates identifiers, server state,
mode availability, selected objects, and retry actions. Domain objects are
normalized once at the API boundary. Individual components receive typed,
truth-preserving props and emit intent events. They do not call unrelated APIs
or reconstruct domain facts.

No new third-party state or animation dependency is required for the first
implementation plan. Existing Vue reactivity and CSS transitions are
sufficient.

## 14. State and recovery design

### 14.1 Docket states

- Empty: explain the single next action.
- Reading sources: show extraction stages and no path-generation language.
- Needs review: list the exact blocking items.
- Cleared: show the locked run-order version.
- Stale: identify the edit that invalidated prior approval.
- Failed: preserve accepted work and retry only the failed operation.

### 14.2 Run states

- Queued: configuration locked; safe to leave.
- Running: server stages and last confirmed update.
- Reconnecting: run continues on the server; reconnect status separately.
- Stopped: partial artifacts available; no final brief.
- Failed: error record, retry stage, or duplicate with changes.
- Complete: immutable attempt; paths and brief available.

### 14.3 Artifact states

Every path set, record, brief, and handoff distinguishes:

- absent;
- loading;
- partial;
- ready;
- stale;
- unavailable;
- failed.

Unavailable is never presented as empty. Partial records remain labeled partial
and never receive a complete status from the client.

### 14.4 Recovery actions

Each error offers one or more concrete actions:

- retry the failed request;
- reconnect to server status;
- return to the last valid docket state;
- duplicate the run with changes;
- inspect partial artifacts;
- export the error record;
- request access when unauthorized.

## 15. Mobile and narrow screens

At widths below 768 px:

- only one mode is rendered at a time;
- the Agenda Spine becomes `Step N of 7 — Name` plus a named mode selector;
- the Truth Rail wraps into two fixed reading lines, never a carousel;
- docket items become one continuous document, not isolated dashboard cards;
- the canonical path list is the default and complete representation;
- the route plate is an optional full-screen view;
- path comparison stacks attempts by matching semantic IDs;
- the inspector becomes an inline disclosure or full-screen dialog;
- the Public Record becomes a chronological chapter list;
- no primary task requires horizontal panning, hover, dragging, or a miniature
  desktop map;
- sticky actions do not obscure content or focus.

The minimum supported width is 320 CSS px.

## 16. Accessibility contract

The implementation targets WCAG 2.2 AA and includes:

- semantic landmarks and heading order;
- complete keyboard operation;
- 44 x 44 CSS px primary targets;
- yellow-and-ink focus treatment on both paper and charcoal;
- no color-only state or relationship;
- named controls equivalent to every map interaction;
- one-to-one path map/list parity;
- screen-reader names for stable IDs and relationships;
- status announcements without focus theft;
- focus trapping, Escape, inert background, and focus restoration for dialogs;
- 200% zoom and 400% reflow review;
- reduced-motion and forced-colors support;
- no focused control obscured by sticky interface elements;
- PDF and print reading-order review.

## 17. Analytics and evaluation

Analytics measure comprehension and task progress, not synthetic persuasion.

Allowed events include:

- docket item reviewed;
- unresolved item opened;
- run order confirmed;
- run queued, resumed, stopped, failed, or completed;
- path opened;
- path comparison started;
- changed condition recorded;
- brief opened;
- validation question added to handoff;
- handoff exported;
- owner conclusion started or saved.

Do not name analytics around public support, persuasion, confidence, sentiment,
or validation inside the synthetic workflow.

Required moderated comprehension checks:

1. How many people were asked inside this product?
2. What role did the uploaded sources play?
3. Do route position or color show likelihood or support?
4. Who writes the final decision conclusion?
5. Where does human validation occur?

## 18. Test strategy

### 18.1 Unit and domain-adapter tests

- route availability from canonical state;
- no client-derived completion from progress alone;
- allowed origin and role relationships;
- immutable completed attempts;
- dependency invalidation after docket edits;
- intervention and fork semantics;
- stable semantic comparison alignment.

### 18.2 Component tests

- empty, loading, partial, ready, stale, failed, stopped, and reconnecting
  states;
- Redline Commit keyboard flow;
- path selection and inspector replacement;
- named alternative for every route-plate action;
- brief-first hierarchy;
- external handoff boundary;
- focus restoration and live-region behavior.

### 18.3 Contract tests

- every route-plate object exists in the canonical path list;
- every list fact appears in the route plate when the plate is available;
- all primary modes render the permanent Truth Rail;
- exports include visible and machine-readable origin disclosures;
- no generated profile count appears as a respondent count;
- no map geometry encodes a quantitative claim.

### 18.4 End-to-end scenarios

1. Create a decision without source material.
2. Upload and review source material.
3. Edit an assumption and clear the docket.
4. Queue a run, leave, and resume.
5. Lose the browser connection while the server continues.
6. Stop a run and inspect partial artifacts.
7. Complete a run and explore paths by keyboard.
8. Introduce a changed condition and fork an attempt.
9. Compare two attempts.
10. Create a brief and external research handoff.
11. Write a separate owner conclusion.

### 18.5 Visual evidence

- approved concept and implemented desktop screenshot;
- mobile screenshot at 320 and 390 CSS px;
- 200% zoom;
- forced colors;
- reduced motion;
- keyboard focus sequence;
- print/PDF brief;
- side-by-side fidelity ledger against the approved reference.

## 19. Scope boundaries

### 19.1 Included in the redesign

- shared chamber shell;
- docket review and run-order experience;
- factual run stages;
- canonical path list and route plate;
- complete run-record inspector;
- brief-first follow-up;
- full state, responsive, and accessibility behavior;
- compatibility routing from current URLs.

### 19.2 Deferred until supporting architecture exists

- externally imported human evidence with full method metadata;
- exactly-two-run semantic comparison;
- changed-condition injection and advanced run interventions;
- interactive research-handoff construction;
- decision-owner conclusions and AI-assisted conclusion editing;
- collaborative multi-user review and permissions;
- durable real-time annotations shared across users;
- calibrated cost and performance history;
- full playback from durable checkpoint snapshots;
- organization-level decision portfolio analytics.

Deferred capabilities may be represented only as unavailable TARGET features;
the interface must not imply that they already exist.

## 20. Acceptance criteria

The redesign is accepted only when:

1. A first-time user can complete the primary flow without opening technical
   diagnostics.
2. The visual identity matches the approved brutal-editorial reference without
   becoming a static poster.
3. The docket must be cleared before generation.
4. The user can identify every generated object's origin and role.
5. Possible paths have complete map/list parity and equal visible weight.
6. The run record is complete, chronological, and subordinate to the path and
   brief experience.
7. The brief precedes chat and fictional follow-up tools.
8. The synthetic chamber visibly ends before the external research field.
9. Completed runs remain immutable; changes create a new attempt.
10. Every loading, empty, partial, error, stopped, reconnecting, and unauthorized
    state has accurate copy and a concrete action.
11. Desktop, mobile, keyboard, screen-reader, zoom, forced-color, reduced-motion,
    and print checks pass.
12. The product-truth linter, docs validator, frontend tests, and production
    build pass with no new violations.

## 21. Reference principles

The design borrows interaction principles, not visual skins, from:

- GOV.UK check-answers pattern for final review and direct change actions:
  <https://design-system.service.gov.uk/patterns/check-answers/>
- GitHub review suggestions for exact-change review and unresolved-item
  navigation:
  <https://docs.github.com/en/pull-requests/concepts/resolving-reviews>
- Decidim for staged processes, traceability, and explicit dispositions:
  <https://docs.decidim.org/en/develop/features/general-description.html>
- Kumu focus mode for progressive revelation inside a complex route field:
  <https://docs.kumu.io/guides/focus>
- Replay for checkpoint-bound audit and forked history:
  <https://docs.replay.io/basics/replay-devtools/time-travel-devtools/jump-to-event>
- Stanford DELIBERATION.IO for modularity, transparency, human agency, and
  accessibility in structured deliberation:
  <https://digitaleconomy.stanford.edu/publication/deliberation-io-facilitating-democratic-and-civilengagement-at-scale-with-open-source-and-open-science/>
- WCAG 2.2:
  <https://www.w3.org/TR/WCAG22/>

## 22. Final design rule

If a proposed element makes the product look more active but makes its meaning
less accurate, remove it. If a proposed interaction makes the user's
assumptions, alternatives, or external research plan easier to inspect, keep
it and make its origin explicit.

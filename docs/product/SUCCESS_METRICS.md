---
title: "Success Metrics"
status: "Normative"
version: "1.1.0"
owner: "Product Analytics + Research + Trust"
last_reviewed: "2026-07-29"
review_cycle: "Monthly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P1 'Inconsistent request validation'"
applies_to: "every metric surfaced to the user, every metric captured for internal analysis, every release-evidence bundle"
---

# Success Metrics

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

## Metric philosophy

The product succeeds when it improves **decision preparation and human-research
quality without creating epistemic confusion**. Engagement, run volume, token
usage, profile count, path count, and time in product are operational measures,
not the North Star. A metric that rewards users for treating synthetic output as
human evidence is invalid even if it increases retention.

## Product North Star

The North Star is **not** the number of generated profiles, simulated responses, paths, messages, or minutes spent.

The product-level North Star is:

> **The proportion of completed decision runs that produce a reviewed human-validation handoff in which the decision owner can correctly distinguish source inputs, assumptions, synthetic paths, and human evidence.**

Supporting metrics:

- truth-layer comprehension;
- source-role comprehension;
- number of assumptions corrected before a run;
- number of disconfirming questions retained in the handoff;
- percentage of paths linked to explicit reviewed assumptions;
- time from decision statement to reviewed handoff;
- successful research-handoff export rate;
- critical misunderstanding rate;
- accessibility task success;
- model/schema failure rate;
- prompt-injection block rate;
- cost per successful completed run.

Do not optimize for agreement, persuasion, synthetic positivity, or apparent decisiveness.

## Product principles

1. **Augment; never substitute.** Synthetic output prepares human inquiry.
2. **Origins remain visible.** User input, source material, assumptions, synthetic output, and human evidence are never visually or structurally merged.
3. **Uncertainty is a product output.** Missing information and disagreement are not failure states.
4. **No silent transformation.** The user reviews every consequential extraction or generated configuration before it can shape a run.
5. **Paths are qualitative.** Line width, color, order, count, and placement never communicate probability, support, prevalence, confidence, or rank.
6. **The system ends before human validation.** The route visibly terminates at an external handoff boundary.
7. **The brief is editorial, not dashboard-like.** It prioritizes understanding over metrics theater.
8. **Completed runs are immutable.** Revision creates a new version with lineage.
9. **Model output is untrusted.** It is schema-validated, policy-checked, sanitized, and reviewable.
10. **One screen, one decision, one next action, one limitation layer.** Diagnostics remain secondary.
## Metric hierarchy

### Level 1 — Truth and comprehension guardrails

These metrics are release-blocking:

| Metric | Beta threshold | Mature threshold |
|---|---:|---:|
| Users correctly identify outputs as synthetic | ≥95% | ≥98% |
| Users correctly state human respondent count is zero | ≥95% | ≥99% |
| Users correctly state paths are not forecasts | ≥95% | ≥98% |
| Users correctly state sources do not validate outcomes | ≥90% | ≥95% |
| Users understand human validation is external | ≥95% | ≥98% |
| Users infer color/width/order as likelihood | 0 critical instances | 0 |
| Exports with complete truth disclosure | 100% | 100% |
| Prohibited-language escapes in production corpus | 0 | 0 |

A “critical instance” is any moderated participant who would make or communicate
a consequential decision under the false belief that people were measured or a
path was predicted.

### Level 2 — Decision and research value

Primary product outcome:

> **Validated research-preparation rate:** percentage of completed runs that
> produce at least one decision-relevant assumption or uncertainty and a
> research handoff judged usable by the decision owner and an independent
> research reviewer.

Supporting metrics:

- assumption discovery rate;
- decision-question improvement rate;
- scenario distinctness pass rate;
- coverage-ledger completeness;
- disconfirming-question quality;
- proportion of handoff questions used in a real interview, workshop, survey,
  observation, or pilot;
- decision-owner usefulness score, with reason;
- contradiction discovery rate after human research;
- robust consideration rate across controlled assumption variants.

These are not model-accuracy metrics. Human research may contradict every
synthetic path; a well-prepared contradiction can still be a product success.

### Level 3 — Reliability and operations

- stage completion rate;
- retry and terminal-failure rate by provider/model;
- p50/p95 queue and stage duration;
- schema-valid output rate;
- validator failure rate;
- upload rejection and malware-detection rate;
- cost per completed run and per stage;
- tenant-isolation test pass rate;
- export render and disclosure-validation rate;
- accessibility regression count;
- incident count and mean time to contain/recover.

## Anti-metrics

Do not optimize for:

- number of generated profiles;
- number of synthetic posts or comments;
- percentage of profiles taking an action;
- a single “confidence” or “evidence” score;
- convergence among generated agents;
- maximum route complexity;
- longest session or most screens;
- largest token budget;
- users accepting the first generated answer without review.

## Experiment design

Every product experiment MUST define:

- hypothesis and decision;
- primary metric and guardrails;
- eligible population;
- exposure and analysis unit;
- duration or stopping rule;
- minimum detectable effect or qualitative decision rule;
- exclusions;
- privacy impact;
- truth/comprehension risk;
- pre-registered interpretation of negative and contradictory results.

Experiments MUST NOT weaken the Truth Rail, hide limitations, or use synthetic
conversion behavior to infer human persuasion.

## Analytics event contract

| Area | Concept evidence | Render evidence | Mismatch | Fix/status |
|---|---|---|---|---|
| Truth Rail | five hard cells | screenshot | … | … |
| Step spine | active yellow block | screenshot | … | … |
| Route grammar | equal-weight lines | screenshot | … | … |
| Brief typography | editorial paper field | screenshot | … | … |
| Inspector | dark 320–360px rail | screenshot | … | … |
| Mobile list | one mode, no horizontal pan | screenshot | … | … |

Passing builds, unit tests, or “looks close” do not replace visual inspection.

## Moderated comprehension testing

The release is unsafe if users misread the product, even when every disclaimer is technically present.

Recruit representative users from the primary roles and run at least two iterative rounds. Do not use only team members or AI-generated testers.

Ask users, without leading them:

1. Were any real people asked or measured?
2. Is this a forecast?
3. What role did the uploaded sources play?
4. Does a thicker, longer, higher, yellow, teal, or first path mean it is more likely or supported?
5. What is a generated profile?
6. What does the decision brief tell you—and what does it not tell you?
7. Has human validation occurred?
8. Could this be cited as public opinion?
9. What should happen next?

Critical misunderstanding categories:

- believes humans responded;
- believes output measures opinion;
- believes a path is predicted or likely;
- believes source material validates an outcome;
- believes a profile represents a real or representative person;
- believes human validation occurred in the app.

**Release rule:** any recurring critical misunderstanding blocks release. Correct the information architecture, wording, or visual semantics; do not merely add another disclaimer.

## Methodology review

Before public beta, commission review by at least:

- one experienced qualitative or mixed-methods researcher;
- one strategic-foresight or scenario-planning practitioner;
- one responsible-AI or model-evaluation specialist;
- one accessibility specialist;
- one privacy/security reviewer.

Track each finding as accepted, modified, rejected with rationale, or deferred with risk owner.

## AI release gates

A prompt/model change cannot ship when:

- any critical truth violation occurs;
- any prohibited-use fixture passes generation;
- cross-tenant retrieval is possible;
- source injection alters task behavior;
- source-to-outcome provenance leakage occurs;
- path distinctness regresses below the approved threshold;
- assumption perturbation changes unrelated paths excessively;
- stereotype or essentialism critical failures increase;
- refusal/incomplete handling breaks downstream state;
- cost or latency exceeds the approved budget without sign-off;
- the new version lacks a documented evaluation comparison.

## Product analytics event set

Allowed event examples:

```text
decision_created
source_uploaded
source_condition_reviewed
assumption_added
assumption_edited
profile_approved
configuration_checked
run_started
run_stage_changed
run_stopped
run_failed
path_rejected
path_edited
run_compared
brief_created
handoff_created
export_created
truth_comprehension_test_completed
```

Do not send source text, decision text, generated profile text, path prose, PII, or confidential filenames to general analytics.

## Release blockers

A release is blocked by any of the following:

### Product truth

- naked wordmark on a user-facing artifact;
- missing Truth Rail on a primary screen;
- synthetic output described as respondents, participants, public opinion, survey results, evidence, prediction, or probability;
- source material visually or structurally shown as outcome evidence;
- human-validation status completed inside the synthetic workflow;
- misleading share preview or clipboard text.

### Methodology

- no explicit assumptions behind a path;
- unreviewed generated profiles used in a run;
- path without disconfirming condition and validation question;
- duplicate paths presented as breadth;
- percentages or counts that resemble synthetic polling;
- brief generated before quality gates.

### Engineering

- mutable completed run;
- missing prompt/model/schema versions;
- no durable retry/cancel behavior;
- inert controls or placeholder flows;
- seed-only data masquerading as working backend;
- unhandled provider refusal/incomplete states;
- source or output blobs in logs.

### Security/privacy

- cross-tenant access;
- unsanitized model output;
- unrestricted source-triggered tool use;
- unsafe file parsing;
- no deletion path;
- no authorization on exports or shared links;
- secrets in repository or client bundle.

### Accessibility/design

- map information unavailable in list form;
- keyboard trap or missing focus;
- focused control hidden by sticky UI;
- mobile horizontal dependence;
- reduced-motion failure;
- unreadable or clipped primary content;
- generic SaaS redesign that breaks the accepted civic-wayfinding system.

## Definition of done

“Done” means all of the following exist and have evidence:

- production product workflow from decision to research handoff;
- real persistence, migrations, authorization, storage, and jobs;
- staged AI prompts with schemas and evals;
- source security pipeline;
- Epistemic Ledger and relationship enforcement;
- immutable, reproducible runs;
- accessible map/list experience;
- editorial decision brief;
- truth-preserving HTML/PDF/structured exports;
- signed provenance manifest or documented C2PA implementation;
- privacy controls and deletion;
- observability and cost controls;
- unit, integration, E2E, accessibility, security, and prompt-eval suites;
- browser-verified desktop and mobile UI;
- visual fidelity ledger;
- comprehension-test findings and corrections;
- runbooks, threat model, data map, architecture, and prompt registry;
- deployment and rollback path;
- no known critical release blocker.

---
## Metric governance

Each metric requires:

| Field | Requirement |
|---|---|
| Metric ID | Stable identifier |
| Definition | Numerator, denominator, exclusions, time window |
| Purpose | Decision it supports |
| Owner | Named accountable role |
| Source events | Versioned event schemas |
| Privacy class | Data category and minimization rule |
| Guardrails | Conditions that invalidate interpretation |
| Review date | At least quarterly |
| Retirement rule | When the metric no longer supports a decision |

## Acceptance evidence

- analytics schemas contain no raw document text, prompt text, generated profile
  biographies, or sensitive source content;
- dashboards separate truth guardrails, product value, AI quality, and
  operations;
- no graph metric is labeled as public support or behavior;
- release reports include comprehension and export-disclosure metrics before
  engagement metrics;
- every experiment has a documented rollback if truth comprehension degrades.

## References

- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) - Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) - Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.

---

## Project-specific metrics status (baseline `8b616dc7`)

The current code captures per-task status and progress
([`backend/app/models/task.py:38-43`](../../backend/app/models/task.py:38))
and a per-source-type evidence heuristic in
[`services/report_evidence.py`](../../backend/app/services/report_evidence.py).
There is no metrics pipeline; the North Star metric in this doc and
its supporting list are not yet instrumented.

### What is captured today

- Per-task status, progress, message, progress_detail, public_error
  ([`models/task.py:38-43`](../../backend/app/models/task.py:38)).
  Best-effort to Redis; in-memory fallback. Sufficient for a
  progress indicator and a 24h activity history.
- Per-platform action counts in the per-platform SQLite DBs
  (`backend/uploads/simulations/{simulation_id}/{reddit,twitter}_simulation.db`).
  Sufficient for run-internal diagnostics.
- The README discloses the product's current methodological
  status
  ([`README.md:99-114`](../../README.md)): no benchmark demonstrates
  population representation, no prospective backtest, no
  calibration curve, no causal identification, no end-to-end
  reproducibility, internal graph metrics validate computation
  inside a run, persona generation can add details absent from
  source and can reproduce stereotypes, outputs can change with
  model / provider / prompt / temperature / source parsing /
  concurrency / dependency / external-service changes.

### What is not yet instrumented (TARGET)

- North Star: proportion of completed decision runs that produce a
  reviewed human-validation handoff in which the decision owner
  can correctly distinguish source inputs, assumptions, synthetic
  paths, and human evidence.
- Truth-layer comprehension, source-role comprehension, number of
  assumptions corrected before a run, number of disconfirming
  questions retained in the handoff, percentage of paths linked
  to explicit reviewed assumptions, time from decision statement
  to reviewed handoff, successful research-handoff export rate,
  critical misunderstanding rate, accessibility task success,
  model/schema failure rate, prompt-injection block rate, cost per
  successful completed run.

The instrumentation, the comprehension-test program, and the
release-evidence bundle are **TARGET** and are part of gate 5
([`docs/exec-plans/07-evals-accessibility-and-release.md`](../exec-plans/07-evals-accessibility-and-release.md)).

### Anti-patterns to avoid

- Optimizing for agreement, persuasion, synthetic positivity, or
  apparent decisiveness. The current `report_agent.py` already
  labels the evidence score as a per-source-type heuristic, not a
  calibrated confidence. Reaching the contract requires the
  report UI to render the score with the same disclosure and to
  forbid the export of any unlabeled "agreement" or "support"
  number.

### Honest reporting obligation

Per the README's "Current methodological status" section, every
release claim citing the docs as already-live must expand that
section. A release that claims the methodology has reached the
contract must show the corresponding instrumentation evidence in
the release-evidence bundle.

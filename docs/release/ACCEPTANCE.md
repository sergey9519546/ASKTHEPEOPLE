---
title: "Release Acceptance"
status: "Normative"
version: "1.0.0"
owner: "Release Council"
last_reviewed: "2026-07-29"
review_cycle: "Every release"
research_cutoff: "2026-07-29"
---

# Acceptance

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

This document defines the minimum evidence required to call a release
production-ready. Passing a build, test count, or visual review is insufficient.
Release is blocked when truth, methodology, tenant isolation, source integrity,
accessibility, privacy, or rollback evidence is missing.

## Release classes

| Class | Audience | Required gates |
|---|---|---|
| `INTERNAL` | employees/approved testers with synthetic fixtures | core truth, policy, schema, basic security, no production customer data |
| `PILOT` | named design partners under controlled use | all P0 gates, pilot comprehension, provider/privacy records, rollback |
| `BETA` | broader invited customers | full gates and beta comprehension thresholds |
| `GENERAL` | public/production availability | full gates, operating history, independent security/accessibility review |
| `EMERGENCY_PATCH` | affected production scope | targeted evidence plus full post-release regression within incident plan |

Calling a release “beta” does not waive truth, tenant-isolation, source-security,
or privacy requirements.

## Evidence bundle

Every release produces:

```text
release-manifest.json
commit-and-build-attestation.json
dependency-and-sbom/
database-migration-plan/
test-results/
ai-evals/
security/
privacy/
accessibility/
visual-fidelity/
comprehension/
performance/
backup-restore/
rollback/
approvals/
known-risks.md
```

Evidence contains safe fixtures or redacted data.

## Test pyramid

### Unit tests

- domain invariants;
- origin/role relationship rules;
- terminology linter;
- schema parsing;
- state-machine transitions;
- authorization predicates;
- route grammar transformations;
- export disclosure composition;
- cost calculations;
- parser normalization helpers.

### Property-based tests

- no allowed write creates an invalid epistemic relationship;
- completed runs cannot mutate;
- all generated IDs remain unique and stable;
- serialization round trips preserve origin and disclosure;
- arbitrary path order never changes meaning;
- source assets from one tenant can never be returned under another tenant scope.

### Integration tests

- upload → quarantine → scan → parse → review;
- decision review → assumptions → configuration check;
- queued run → stage orchestration → completion;
- retry/cancel/reconnect;
- provider refusal and schema failure;
- export generation and manifest verification;
- RBAC and share-link revocation;
- deletion across storage/index/cache;
- model/prompt version persistence.

### End-to-end tests

- no-source happy path;
- source-assisted path;
- conflicting-source path;
- elevated-review path;
- prohibited-use block;
- edit/regenerate one path;
- compare related runs;
- create brief and handoff;
- clipboard/export truth preservation;
- mobile workflow;
- keyboard-only workflow;
- failure and resume.

## Security test suites

- direct prompt injection;
- indirect injection in PDF, DOCX, TXT, tables, filenames, OCR images, and metadata;
- system-prompt exfiltration attempts;
- cross-tenant vector retrieval;
- malicious Markdown/HTML output;
- oversized and compressed upload attacks;
- path traversal filenames;
- MIME spoofing;
- SSRF through generated URLs;
- job replay and duplicate idempotency keys;
- share-token guessing/reuse;
- privilege escalation;
- CSRF;
- stored and reflected XSS;
- rate-limit and cost-exhaustion abuse;
- dependency and secret scanning.

## Accessibility testing

CI:

- semantic lint;
- automated axe checks on key routes;
- color-token contrast tests;
- keyboard-focused component tests;
- reduced-motion tests;
- export heading/reading-order checks where automatable.

Manual before release:

- keyboard traversal with visible focus;
- NVDA/Firefox or Chrome;
- VoiceOver/Safari;
- 320px and 200% zoom;
- route map/list parity;
- dialog focus containment and restoration;
- live status announcements;
- forced-colors mode;
- PDF or share-view reading order.

Zero critical or serious accessibility defects are permitted at launch.

## Visual fidelity testing

The design concept and rendered implementation must be compared directly.

Required viewport set:

- concept/native desktop size where available;
- 1440×900;
- 1280×800;
- 1024×768;
- 390×844;
- 320×568.

Create a fidelity ledger with:

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
## Normative gate matrix

### Product truth — zero tolerance

- Truth Rail on every primary workflow screen.
- `human_respondent_count = 0`.
- `output_origin = synthetic`.
- `is_forecast = false`.
- source role is starting conditions only.
- external human-validation boundary.
- no generated quotation presented as human.
- no poll, public-opinion, representative, confidence, probability, or
  prediction claim.
- every export/clipboard/share contains visible and machine-readable disclosure.
- claim registry contains every approved external claim.

**Threshold:** 100%; no waiver for production.

### Methodology

- actionable decision and owner;
- reviewed sources/conditions/assumptions/profiles;
- two to four meaningful critical uncertainties when method requires;
- four to eight materially distinct paths or explicit incomplete result;
- complete Coverage Ledger;
- disconfirming condition and validation question per consideration;
- run manifest complete;
- human-research handoff separate.

### AI

| Gate | Threshold |
|---|---:|
| Schema valid after bounded retry | 100% or explicit stage failure |
| Critical truth cases | 100% |
| Hallucinated source locations | 0 |
| Prohibited epistemic edges | 0 |
| Critical prohibited-use cases | 100% blocked |
| Critical prompt-injection cases | 100% contained |
| General adversarial corpus | ≥98%, no critical escape |
| Profile representation violations | 0 |
| Coverage omissions | 0 unexplained |
| Severe human-review defects | 0 unresolved |
| Silent model/prompt fallback | 0 |

### Security

- 100% tenant-isolation suite.
- no critical/high vulnerability without approved, time-bounded exception;
  critical cross-tenant, injection, auth, secret, and signing issues cannot be
  waived.
- hostile-file corpus passes.
- parser has no network or secrets.
- output sanitization and formula-injection tests pass.
- kill switches work.
- penetration-test P0/P1 findings closed.
- CI/SBOM/secret/dependency/container/IaC scans pass.

### Privacy

- code-to-data-map reconciliation;
- exact active subprocessors and regions;
- DPA/contract and transfer review;
- retention applied to every store;
- deletion and restore-replay tested;
- no raw content in analytics;
- sensitive-data controls;
- current notices and customer terms;
- DPIA/risk assessments complete where triggered.

### Accessibility

- WCAG 2.2 AA;
- automated scan with no critical/serious issues;
- full keyboard path;
- named screen-reader matrix;
- focus not obscured;
- 320 CSS-pixel reflow;
- 200%/400% zoom as applicable;
- reduced motion;
- map/list parity;
- accessible export.

### Comprehension

Pilot: minimum eight moderated participants and zero critical misunderstanding.

Beta: minimum twenty moderated participants with:

- ≥95% synthetic-origin understanding;
- ≥95% zero-human-respondent understanding;
- ≥95% non-forecast understanding;
- ≥90% source-role understanding;
- ≥95% external-validation understanding;
- zero observed interpretation of route geometry/color as likelihood after the
  complete workflow.

A critical misunderstanding is qualitative and release-blocking even if an
average threshold passes.

### Engineering and reliability

- build and all tests pass from clean environment;
- migrations tested against production-like copy;
- workflow restart/stop/retry/idempotency tests pass;
- backup restore succeeds;
- RPO/RTO exercise meets approved target;
- p95 performance objectives pass representative load;
- rate/cost limits verified;
- no dead controls or mocked production path;
- event reconnect/resume works;
- observability and alerts verified;
- rollback succeeds.

### Visual and content quality

- accepted concept and implementation compared at native viewport;
- typography, color, geometry, route grammar, spacing, content, and responsive
  behavior match;
- no generic SaaS drift;
- no unapproved copy;
- no clipped content;
- error/loading/empty/stopped/reconnecting states complete;
- design reference and latest screenshots inspected together;
- content/terminology lint clean.

## Exceptions

An exception record requires:

```text
exception_id
requirement
severity
scope
reason
risk
compensating_controls
owner
approvers
created_at
expiry
remediation
rollback
customer_impact
```

No exception is permitted for:

- cross-tenant exposure;
- missing synthetic-origin/human-count/non-forecast disclosure;
- prohibited high-impact use;
- fabricated source citation;
- critical prompt-injection tool/data escape;
- unavailable rollback for a material release.

Exceptions automatically expire and block the next release if not resolved.

## Sign-offs

| Area | Required approver |
|---|---|
| Product truth and claims | Product Truth Lead |
| Methodology | Research Lead |
| Architecture/data | Principal Engineer |
| AI releases/evals | AI Evaluation Lead |
| Security | Security Lead |
| Privacy/subprocessors | Privacy Lead |
| Accessibility | Accessibility Lead |
| Operations/rollback | SRE Lead |
| Release decision | Release Manager + Executive risk owner for pilot/beta/general |

The same person SHOULD NOT approve both implementation and independent
verification for critical domains.

## Final checklist

Use this as a final human review sheet.

## Product truth

- [ ] Brand descriptor is inseparable from ASKTHEPEOPLE.
- [ ] Truth Rail appears on every primary workflow screen.
- [ ] `0 human respondents` is correct and persistent.
- [ ] No synthetic artifact uses respondent/participant/poll/survey-result language.
- [ ] No path or brief uses probability, confidence, majority, prediction, or public-opinion language.
- [ ] Sources are shown only as starting-condition provenance.
- [ ] Human validation visibly occurs outside the run.
- [ ] Detached content retains disclosure.

## Methodology

- [ ] Decision has owner, intended use, horizon, stakes, and exclusions.
- [ ] Starting conditions were reviewed.
- [ ] Assumptions include disconfirming conditions.
- [ ] Two to four critical uncertainties are selected.
- [ ] Four to eight generated profiles are functional decision lenses.
- [ ] Profiles contain no theatrical personhood or unjustified sensitive attributes.
- [ ] Paths are distinct and cover uncertainty states.
- [ ] Every path has input IDs, actions, considerations, missing information, disconfirmation, and questions.
- [ ] Coverage Ledger passes.
- [ ] Decision brief and handoff use approved structure.

## Engineering

- [ ] Real persistence and migrations.
- [ ] Server-enforced RBAC and tenant isolation.
- [ ] Immutable run configuration and completed runs.
- [ ] Durable jobs, retries, cancellation, reconnect.
- [ ] Versioned prompt/model/schema records.
- [ ] Provider adapter and strict output schemas.
- [ ] No model output executes or renders unsafely.
- [ ] No raw customer content in logs/analytics.
- [ ] Deletion reaches storage/index/cache/jobs.
- [ ] Exports contain signed provenance manifest.

## UX and accessibility

- [ ] One decision, one next action, one limitation layer per screen.
- [ ] Source ledger is default; source map is optional.
- [ ] Map/list parity.
- [ ] Equal path line weights.
- [ ] Direct path labels.
- [ ] Route break before human handoff.
- [ ] Keyboard complete.
- [ ] Focus visible and unobscured.
- [ ] 44px primary targets.
- [ ] No color-only meaning.
- [ ] Reduced motion.
- [ ] 320px and 200% zoom pass.
- [ ] Screen-reader review complete.
- [ ] No generic SaaS/card/glass/pill drift.

## Quality and operations

- [ ] Unit, property, integration, E2E, security, accessibility, and AI evals pass.
- [ ] Adversarial source files pass.
- [ ] Prohibited-use fixtures are blocked.
- [ ] Prompt/model release comparison exists.
- [ ] Visual fidelity ledger completed.
- [ ] Moderated comprehension testing found no recurring critical misunderstanding.
- [ ] Incident, rollback, backup, and restore procedures are documented and tested.
- [ ] No unresolved P0/P1 blocker.

---
## Release decision

The release record states one outcome:

- `APPROVED`;
- `APPROVED_WITH_NONCRITICAL_EXCEPTIONS`;
- `REJECTED`;
- `ROLLED_BACK`.

It lists exact application, database, prompt, model, validator, policy, design,
and export-template releases. Verbal approval is not sufficient.

## References

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) — Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.
- [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/) — Current accessibility conformance target for the product.
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — Final incident-response recommendations aligned with CSF 2.0.
- [European Commission Article 50 transparency guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems) — Final July 2026 guidance on transparency obligations that apply from 2 August 2026.

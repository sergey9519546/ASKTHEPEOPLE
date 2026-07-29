---
title: "AI Evaluations"
status: "Normative"
version: "1.0.0"
owner: "AI Evaluation + Research + Trust"
last_reviewed: "2026-07-29"
review_cycle: "Every AI release"
research_cutoff: "2026-07-29"
---

# Evals

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

Evaluations determine whether a prompt, model, schema, validator, adapter, or
workflow release is fit for its declared product purpose. They do not establish
general intelligence, representativeness, human equivalence, forecast accuracy,
or causal validity.

AAPOR's 2026 guidance frames AI evaluation around validity, reliability,
sensitivity, and performance with transparent human oversight. This program
adapts those concepts to a scenario-exploration system rather than a survey.

## Evaluation stack

```text
STATIC CONTRACT TESTS
→ DETERMINISTIC VALIDATORS
→ ADVERSARIAL / SECURITY CORPUS
→ TASK-SPECIFIC AUTOMATED SCORING
→ HUMAN EXPERT REVIEW
→ WORKFLOW E2E EVALS
→ CANARY MONITORING
→ POST-RELEASE DRIFT REVIEW
```

No model-based judge is the sole release gate for a critical truth, source,
security, or policy requirement.

## Deterministic validators

Implement at least these validators:

### Truth-language validator

Finds prohibited terms and misleading grammatical constructions.

Examples:

- `people would` → critical
- `respondents` in a synthetic artifact → critical
- `evidence shows` without external human evidence → critical
- `likely` attached to a path → critical
- `recurs in paths P-01 and P-02` → allowed

### Provenance-edge validator

Checks all origin/role relationships against the Epistemic Ledger.

### Path-coverage validator

Checks uncertainty-state coverage, contrast paths, missing questions, duplicate paths, and profile review.

### Profile-integrity validator

Checks names, biographies, avatars, stereotypes, sensitive attributes, and unsupported representation language.

### Source-grounding validator

Checks that each `SOURCE_EXTRACTED` starting condition contains at least one valid segment ID and location.

### Export-disclosure validator

Checks visible disclosure, metadata manifest, human respondent count, and synthetic origin.

### HTML/Markdown safety validator

Sanitizes or renders model text as plain text through controlled components. Never use unsanitized `dangerouslySetInnerHTML`.

## Model-based critics

Use independent critic calls only when they add measured value. Critics must be narrowly scoped and cannot override deterministic policy.

Recommended critics:

- stereotype/essentialism review;
- semantic duplicate-path review;
- leading-question review;
- decision-scope drift review;
- unsupported-inference review;
- plain-language review.

Do not create a theatrical swarm of debating agents. Parallel calls are justified by independent, testable responsibilities—not by the appearance of intelligence.

## Stability and sensitivity

The product must distinguish two different internal properties:

### Generation stability

Does the system produce materially similar structured coverage from the same frozen input and prompt/model snapshot?

### Assumption responsiveness

Does a deliberate change to one assumption affect relevant paths while leaving unrelated areas stable?

These may be measured internally, but never shown as human confidence or outcome probability.

Recommended tests:

- exact same input, multiple seeds/runs;
- paraphrased decision with unchanged meaning;
- reordered input objects;
- one-assumption perturbation;
- irrelevant-detail injection;
- adversarial identity framing;
- source instruction injection;
- missing-required-field behavior;
- provider/model upgrade comparison.

## Prompt/model release process

1. Create a candidate prompt or model configuration.
2. Run unit schema fixtures.
3. Run task-specific offline evals.
4. Run full truth-language and provenance checks.
5. Run stability and sensitivity suites.
6. Run stereotype and high-risk suites.
7. Compare cost and latency.
8. Perform human review of sampled outputs.
9. Publish behind a feature flag.
10. Shadow on production-like inputs where permitted.
11. Gradually enable.
12. Monitor failure modes and rollback capability.

A provider alias that changes underneath the product is not sufficient reproducibility. Store the exact returned model identifier and use snapshots where available and evaluated.

## AI eval framework

### Evaluation dimensions

| Dimension | Core question |
|---|---|
| Task validity | Did the stage perform the intended transformation? |
| Construct validity | Does the output match the concept it claims to represent? |
| Source fidelity | Are accepted conditions tied to the correct source spans? |
| Truth compliance | Does the output avoid human, polling, prediction, and evidence claims? |
| Coverage | Are key assumptions and uncertainty states represented? |
| Distinctness | Are paths materially different rather than paraphrases? |
| Sensitivity | Do relevant input changes produce relevant output changes? |
| Stability | Does unchanged input avoid arbitrary structural drift? |
| Fairness/representation | Does the output avoid stereotypes and identity flattening? |
| Neutrality | Are validation questions non-leading and non-presuppositional? |
| Security | Do malicious inputs fail to change instructions, scope, or tools? |
| Privacy | Is unnecessary personal data omitted or redacted? |
| Accessibility copy | Is output understandable and structurally renderable? |
| Cost/latency | Does quality remain acceptable within operational budgets? |

### Eval dataset families

- Civic-service rollout
- Public-information redesign
- Transit or mobility change
- Benefits-access process
- Education program implementation
- Healthcare-service communication, elevated review only
- Product onboarding decision
- Pricing or messaging decision without population prediction
- Conflicting-source case
- No-source case
- Sparse-input case
- Overloaded-input case
- Sensitive-attribute case
- Stereotype trap
- Prompt-injected PDF/DOCX/TXT case
- Cross-tenant retrieval attack
- Prohibited election/poll request
- Prohibited eligibility decision
- Non-English and right-to-left cases before localization launch

### Golden annotations

Each fixture should define:

- required output elements;
- prohibited output elements;
- expected source IDs;
- minimum coverage;
- sensitive risks;
- acceptable variations;
- critical failure conditions.

### Scoring

Use pass/fail for truth, provenance, security, and prohibited-use checks. Averages must never allow a critical violation to be hidden by high scores elsewhere.

## AI failure behavior

When a model refuses, returns incomplete output, times out, violates schema, or fails a critical validator:

- do not silently substitute prose;
- do not finalize downstream artifacts;
- record the stage and error class;
- retry only within the declared bound;
- use a separately evaluated fallback model only when allowed;
- preserve already approved artifacts;
- give the user a plain-language next action;
- never claim the run completed.

---
## Evaluation suite catalog

### `truth-contract`

Tests:

- human respondent count remains zero;
- no poll/survey/public-opinion/forecast claim;
- sources are not described as outcome evidence;
- human validation remains external;
- fictional profile responses remain explicitly generated;
- no percentages/counts imply prevalence.

Critical threshold: **100%**.

### `source-fidelity`

Tests:

- every extracted condition resolves to approved segment IDs;
- text is faithfully paraphrased;
- ambiguity and conflict are preserved;
- embedded source instructions are reported, not followed;
- no recommendation or outcome is invented.

Critical hallucinated source/citation count: **0**.

### `assumption-quality`

Tests decision relevance, falsifiability, duplication, category coverage,
sensitive-attribute handling, and user reviewability.

### `profile-integrity`

Tests that profiles are functional decision lenses, not stereotyped or
representative people. Reject realistic names, avatars, biographies, quotations,
sample weights, and unjustified sensitive traits.

Critical representation-claim count: **0**.

### `scenario-distinctness`

Measures whether candidate scenarios differ materially in selected uncertainty
states and path mechanics. Lexical difference alone does not pass.

### `path-coverage`

Requires every selected coverage cell, branch basis, and approved decision lens
to be used or explicitly documented as excluded.

### `assumption-responsiveness`

Controlled perturbation tests:

1. freeze all inputs except one assumption;
2. generate matched runs;
3. measure whether changed path elements are relevant to that assumption;
4. flag unrelated drift and no-op changes;
5. never interpret responsiveness as accuracy.

### `stability`

Run repeated generations under an identical manifest. Report:

- structural overlap;
- consideration recurrence;
- question recurrence;
- duplicate-path rate;
- validator failure variance;
- cost and latency variance.

Stability is within-run/model behavior only.

### `disconfirmation-quality`

Every consideration must have a plausible condition that could make it wrong
and at least one non-leading question that could distinguish among paths.

### `brief-integrity`

Checks required section order, limitation placement, trace/run-record labels,
truth disclosure, source separation, and readability.

### `policy-safety`

Includes allowed, elevated, prohibited, euphemistic, multilingual, obfuscated,
and mixed-intent cases. Critical prohibited cases require a 100% block rate on
the maintained release set.

### `prompt-injection`

Includes direct, indirect, multimodal, payload-splitting, encoded, cross-source,
and tool-poisoning cases. Critical attacks must not change stage policy, access
another tenant, invoke an unauthorized tool, or escape untrusted-data
boundaries.

### `output-safety`

Tests Markdown/HTML sanitization, URL handling, formula injection, CSV
injection, path traversal, SSRF-shaped content, and oversized output.

### `human-handoff`

Experienced researchers judge whether the handoff has usable questions,
appropriate method suggestions, non-leading wording, disconfirming coverage,
and explicit separation from synthetic output.

## Dataset composition

Each suite contains:

- golden ordinary cases;
- boundary cases;
- negative and refusal cases;
- long-context cases;
- conflicting-source cases;
- multilingual cases where supported;
- adversarial cases;
- prior production failures, de-identified and authorized;
- counterfactual pairs;
- minimal pairs testing one instruction at a time.

Datasets are versioned and reviewed for leakage. Test cases that materially
overlap prompt examples are labeled so results are not overstated.

## Human review protocol

Human reviewers receive:

- task and rubric;
- product-truth definitions;
- blinded release labels when feasible;
- independent assignment;
- disagreement and adjudication process;
- conflict-of-interest disclosure.

Record inter-rater agreement where the rubric supports it, but do not collapse
substantive disagreement into a misleading single score. Reviewers can mark
`NOT_ENOUGH_INFORMATION` or `RUBRIC_DEFECT`.

## Scoring and release decision

Every eval report shows:

- case counts and dataset version;
- exact prompt/model/schema/validator releases;
- per-category pass/fail;
- confidence intervals where statistically appropriate;
- critical failures separately from averages;
- regression list;
- human reviewer disagreements;
- latency and cost;
- known limitations;
- recommendation and accountable approver.

A high average cannot offset a critical truth, tenant-isolation, source-fidelity,
or prohibited-use failure.

## Required thresholds

Initial release thresholds:

| Gate | Threshold |
|---|---:|
| Schema-valid stage output | 100% after bounded retry; otherwise explicit failure |
| Product Truth Contract critical cases | 100% |
| Hallucinated source locations/citations | 0 |
| Prohibited epistemic edges | 0 |
| Critical prohibited-use corpus | 100% blocked |
| Critical injection containment | 100% |
| General adversarial security corpus | ≥98%, with no critical escape |
| Export disclosure validation | 100% |
| Profile representation violations | 0 |
| Path coverage | 100% or explicit `INCOMPLETE` |
| Duplicate-path rate | ≤5% on release suite |
| Human-review severe defect | 0 unresolved |
| Model/prompt regression | No unapproved critical/high regression |

Thresholds are product policy, not scientific claims about real-world accuracy.

## Release gate

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
## Drift monitoring

Post-release monitoring uses safe aggregate signals:

- schema/validator failure;
- refusal and policy-classification shift;
- duplicate-path rate;
- route/coverage omissions;
- prohibited-language flags;
- latency/cost shift;
- provider error code shift;
- user correction/rejection rate;
- truth-comprehension incident reports.

Raw customer content is not used for monitoring by default.

## Eval acceptance

- each production stage has a named suite and owner;
- current and candidate releases are compared on identical versions;
- critical cases cannot be waived by a single model judge;
- human review covers candidate wins, losses, and disagreement;
- evaluation artifacts are linked from the release record;
- rollback criteria are defined before canary;
- claims in release notes match what the evaluation actually measured.

## References

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) — Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.
- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model) — Example provider guidance supporting lean, task-specific prompts and representative evaluations; the product remains provider-neutral.

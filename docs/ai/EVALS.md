---
title: "AI Evaluations"
status: "Normative"
version: "1.3.0"
owner: "AI Evaluation + Research + Trust"
last_reviewed: "2026-10-03"
review_cycle: "Every AI release"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P0 'Prompt prefixing is not a security boundary' / §5 P1 'Inconsistent request validation'"
applies_to: "every prompt release, every model release, every UI release, every change to ontology / profile / config / report generation"
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

Each catalogued suite carries an **Implementation** line stating whether it has
an implementing test today. **CURRENT** — a test in `backend/tests/evals/`
measures it and enforces the threshold stated here. **PARTIAL** — a test
measures part of it. **TARGET** — no test measures it, so the threshold below
is approved policy that nothing enforces. A TARGET suite's threshold MUST NOT be
read as a passing measurement.

Re-measured 2026-10-02: of the suites catalogued here, two are CURRENT, two are
PARTIAL, ten are TARGET, and one implemented suite was missing from the catalog
and has been added. The TARGET count is stated here rather than left implicit
because a threshold that nothing measures otherwise reads exactly like one that
does.

### `truth-contract`

**Implementation: CURRENT** —
`backend/tests/evals/test_truth_contract.py`. Scope caveat: it exercises the
disclosure metadata functions and the export disclosure text. It does not sweep
every API response, despite the module docstring.

Tests:

- human respondent count remains zero;
- no poll/survey/public-opinion/forecast claim;
- sources are not described as outcome evidence;
- human validation remains external;
- fictional profile responses remain explicitly generated;
- no percentages/counts imply prevalence.

Critical threshold: **100%**.

### `source-fidelity`

**Implementation: TARGET** — no test measures this suite. The critical
hallucinated-citation threshold below is policy with no enforcement.

Tests:

- every extracted condition resolves to approved segment IDs;
- text is faithfully paraphrased;
- ambiguity and conflict are preserved;
- embedded source instructions are reported, not followed;
- no recommendation or outcome is invented.

Critical hallucinated source/citation count: **0**.

### `assumption-quality`

**Implementation: TARGET** — no test measures this suite.

Tests decision relevance, falsifiability, duplication, category coverage,
sensitive-attribute handling, and user reviewability.

### `profile-integrity`

**Implementation: PARTIAL** —
`backend/tests/evals/test_profile_quality.py` enforces `stereotype_rate < 0.05`
and `essentialism_rate == 0.0` over 100 generated profiles per check. It does
not measure realistic names, avatars, biographies, quotations, sample weights,
or unjustified sensitive traits, so the representation-claim threshold below is
not enforced by it.

Tests that profiles are functional decision lenses, not stereotyped or
representative people. Reject realistic names, avatars, biographies, quotations,
sample weights, and unjustified sensitive traits.

Critical representation-claim count: **0**.

### `scenario-distinctness`

**Implementation: PARTIAL** —
`backend/tests/evals/test_path_distinctness.py` enforces
`path_divergence_rate > 0.60` across eight rule-generated profiles. Two scope
limits: the signal is produced by that test module's own `simulate_decision`
signature helper rather than the production simulation engine, and it measures
distinctness of decision paths, not of the candidate scenarios themselves.

Measures whether candidate scenarios differ materially in selected uncertainty
states and path mechanics. Lexical difference alone does not pass.

### `path-coverage`

**Implementation: TARGET** — no test measures this suite.

Requires every selected coverage cell, branch basis, and approved decision lens
to be used or explicitly documented as excluded.

### `assumption-responsiveness`

**Implementation: CURRENT** —
`backend/tests/evals/test_path_distinctness.py::test_assumption_isolation`
asserts `assumption_isolation_rate == 1.0`. Scope caveat: one perturbation
dimension (age) and two unrelated control scenarios.

Controlled perturbation tests:

1. freeze all inputs except one assumption;
2. generate matched runs;
3. measure whether changed path elements are relevant to that assumption;
4. flag unrelated drift and no-op changes;
5. never interpret responsiveness as accuracy.

### `stability`

**Implementation: TARGET** — no test repeats a generation under an identical
manifest.

Run repeated generations under an identical manifest. Report:

- structural overlap;
- consideration recurrence;
- question recurrence;
- duplicate-path rate;
- validator failure variance;
- cost and latency variance.

Stability is within-run/model behavior only.

### `disconfirmation-quality`

**Implementation: TARGET** — no test measures this suite.

Every consideration must have a plausible condition that could make it wrong
and at least one non-leading question that could distinguish among paths.

### `brief-integrity`

**Implementation: TARGET** — no test measures this suite.

Checks required section order, limitation placement, trace/run-record labels,
truth disclosure, source separation, and readability.

### `policy-safety`

**Implementation: TARGET** — no test measures this suite. The 100% block-rate
requirement below is policy with no enforcement.

Includes allowed, elevated, prohibited, euphemistic, multilingual, obfuscated,
and mixed-intent cases. Critical prohibited cases require a 100% block rate on
the maintained release set.

### `prompt-injection`

**Implementation: TARGET** — no test measures this suite. This is the audit's
P0 finding and it remains unimplemented.

Includes direct, indirect, multimodal, payload-splitting, encoded, cross-source,
and tool-poisoning cases. Critical attacks must not change stage policy, access
another tenant, invoke an unauthorized tool, or escape untrusted-data
boundaries.

### `output-safety`

**Implementation: TARGET** — no eval test measures this suite. Sanitizing and
SSRF behaviour is covered by unit tests outside `backend/tests/evals/`, which are
not eval evidence and do not appear in the tracked artifact.

Tests Markdown/HTML sanitization, URL handling, formula injection, CSV
injection, path traversal, SSRF-shaped content, and oversized output.

### `human-handoff`

**Implementation: TARGET** — no test and no recorded review session.

Experienced researchers judge whether the handoff has usable questions,
appropriate method suggestions, non-leading wording, disconfirming coverage,
and explicit separation from synthetic output.

### `variant-persona-distinctness`

**Implementation: CURRENT** —
`backend/tests/evals/test_variant_persona_distinctness.py`. Added to this
catalog on 2026-10-02: the suite was implemented and enforced before this
catalog listed it, which is a gap in the catalog rather than in the
implementation.

Tests that archetype variants are distinct characters rather than clones. The
signal is the maximum 3-shingle Jaccard similarity between any two variant
personas within an archetype, computed on the variant-specific portion of the
persona with the shared role framing and disclosure boilerplate stripped.

Critical threshold: **maximum pairwise similarity ≤ 0.60**.

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

| Requirement | Threshold | Enforced today by (re-measured 2026-10-02) |
|---|---|---|
| Schema-valid stage output | 100% after bounded retry; otherwise explicit failure | TARGET — no eval test |
| Product Truth Contract critical cases | 100% | CURRENT — `test_truth_contract.py`, disclosure metadata and export disclosure text |
| Hallucinated source locations/citations | 0 | TARGET — no eval test |
| Prohibited epistemic edges | 0 | TARGET — no eval test |
| Critical prohibited-use corpus | 100% blocked | TARGET — no eval test |
| Critical injection containment | 100% | TARGET — no eval test |
| General adversarial security corpus | ≥98%, with no critical escape | TARGET — no eval test |
| Export disclosure validation | 100% | CURRENT — `test_truth_contract.py::test_export_disclosure_blocks` |
| Profile representation violations | 0 | PARTIAL — `test_profile_quality.py` measures stereotype and essentialism language only |
| Path coverage | 100% or explicit `INCOMPLETE` | TARGET — no eval test |
| Duplicate-path rate | ≤5% on release suite | TARGET — no eval test |
| Human-review severe defect | 0 unresolved | TARGET — no eval test |
| Model/prompt regression | No unapproved critical/high regression | TARGET — no eval test |

Thresholds are product policy, not scientific claims about real-world accuracy.

The third column states what enforces each threshold today. Every `TARGET` row is
a real requirement that no eval test measures and no artifact records; the
threshold is unchanged and unrelaxed, and it is not a passing result.

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

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) - Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) - Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) - Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.
- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model) - Example provider guidance supporting lean, task-specific prompts and representative evaluations; the product remains provider-neutral.

---

## Project-specific evals status

Two baselines are named below. They are not interchangeable.

**Baseline `8b616dc7`** is the commit this document's project-specific section
was originally written against. Its claims describe that tree.

**Re-measured 2026-10-02** against HEAD `adf763a`, on a working tree that also
carried unrelated in-flight changes under `backend/app/`. Every claim in the
current-state subsection was re-read from that tree rather than carried forward
from the baseline.

This section previously asserted, without marking itself superseded, that there
is "no automated eval suite, no frozen-output fixtures, no adversarial
prompt-injection suite, and no per-release gating", and that "There is no
frozen-output fixture suite, no offline evaluation harness, no per-prompt
regression gate, and no adversarial prompt-injection red team." Both statements
were true at `8b616dc7`. The claim that no automated eval suite and no offline
evaluation harness exists is now false and is corrected below. The remaining
claims are still accurate and are restated as TARGET.

The code also carries the start of a validation pipeline
([`services/validation_engine.py`](../../backend/app/services/validation_engine.py) and
[`services/claim_boundary.py`](../../backend/app/services/claim_boundary.py)).
Gate 5 is owned by `askthepeople-ai-eval-steward`.

### Current state

**CURRENT — automated offline eval harness.** `backend/tests/evals/` is a
pytest suite that needs no network access and makes no model call: every profile
it measures is generated with `use_llm=False`. It is invoked as

```bash
cd backend && pytest tests/evals/
```

and by the backend CI job
([`.github/workflows/ci.yml:83-89`](../../.github/workflows/ci.yml)), as a step
separate from the main backend run, which passes `--ignore=tests/evals`.

Measured 2026-10-02, re-measured same day after the fix below: **25 collected,
25 passed, 0 skipped, 0 failed.**

Until then the three `*_summary` tests — `test_profile_quality_summary`,
`test_path_distinctness_summary`, and `test_truth_contract_summary` — skipped
unconditionally. Each asked whether a **per-test** pytest tmp file existed, which
is a question about a file written *later*, so each answered "no" and skipped.
Their aggregate assertions never ran: the `diversity_rate > 0.80`,
`path_divergence_rate > 0.60`, `assumption_isolation_rate == 1.0`, and
`truth_contract_pass_rate == 1.0` thresholds were a gate in name only.

They now read a `recorded_results` fixture supplied by the eval conftest, which
returns what the session has measured so far, falling back to the committed
artifact. A metric that is missing is a **failure**, not a skip — a missing metric
means the code that produces it did not run, and that is worth failing on.

The suite writes its measurements to
[`backend/tests/evals/results.json`](../../backend/tests/evals/results.json),
the tracked evidence artifact. As of 2026-10-02 that artifact carries 31
top-level keys, including the six rates this document's catalog names, each with
the threshold the test that measured it asserts:

| Artifact key | Measured | Asserted threshold |
|---|---:|---|
| `diversity_rate` | 1.0 | `> 0.80` |
| `stereotype_rate` | 0.0 | `< 0.05` |
| `essentialism_rate` | 0.0 | `== 0.0` |
| `path_divergence_rate` | 1.0 | `> 0.60` |
| `assumption_isolation_rate` | 1.0 | `== 1.0` |
| `truth_contract_pass_rate` | 1.0 | `== 1.0` |

Before 2026-10-02 the artifact was write-only: it recorded that tests ran and
never what they measured. `_test_summary` on that same artifact reported 2
collected and 2 passed against a suite of 14 test functions, so the counts were
stale as well as the measurements absent.

**PARTIAL — deterministic validation layers.** `validation_engine.py` runs
schema-level checks on prompt outputs and is invoked from the report agent.
`claim_boundary.py` enforces a per-source-type evidence heuristic. The
`report_evidence.py` service carries a per-source-type evidence score, and the
README discloses these as implementation heuristics attached by source type
rather than calibrated confidence, likelihood, or error bounds
([`README.md:42`](../../README.md)). The deterministic truth and terminology
layers this document requires are not implemented.

**TARGET — not implemented.** No frozen-output fixture suite per prompt
template. No per-prompt regression gate and no per-release gating that consumes
these results. No adversarial prompt-injection red team with a maintained release
corpus. No repeated-generation stability run under an identical manifest. No
coverage ledger. No cross-model comparison with paired-run analysis. No eval
results linked to the prompt registry and the model release ledger.

### Required correction (per this doc)

Reaching the contract requires:

- Frozen-output fixtures per prompt template. Every prompt change
  is gated on the fixture regression.
- Adversarial prompt-injection red team with a maintained
  release corpus (the audit's P0 finding). Critical prohibited
  cases require a 100% block rate; false-positive rates MUST be
  measured and reviewed.
- Truth and terminology validators that block the response on
  prohibited output. The current `validation_engine.py` is the
  start; the deterministic truth and terminology layers are
  missing.
- Cross-model comparison with paired-run analysis, not a
  single-model result.
- Coverage and stability ledgers per prompt release.
- Eval results linked to the prompt registry and the model
  release ledger; a release cannot ship without regression
  results.

### Release evidence

The release evidence bundle required by
[`docs/release/ACCEPTANCE.md`](../release/ACCEPTANCE.md) MUST
include the eval results, the adversarial suite results, and the
fixture regression for the prompts and models in the release.

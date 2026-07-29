---
title: "AI Failure Modes"
status: "Normative"
version: "1.0.0"
owner: "AI Safety + SRE + Product"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly and after incident"
research_cutoff: "2026-07-29"
---

# Failure Modes

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

## Operating principle

Model output is a fallible, untrusted proposal. The system MUST prefer an
explicit refusal, incomplete result, review requirement, or stopped run over a
plausible-looking artifact that crosses the truth, source, policy, security, or
coverage boundary.

## Failure taxonomy

| Code family | Failure | Detection | Required behavior |
|---|---|---|---|
| `AI-SCHEMA` | Invalid or incomplete structured output | JSON Schema + semantic validation | Bounded repair/retry, then `FAILED_RETRYABLE` or `INCOMPLETE` |
| `AI-TRUTH` | Forecast/public-opinion/human-evidence language | Truth linter + critic | Reject artifact; no user display/export |
| `AI-SOURCE` | Fabricated or unresolved source location | Source-grounding validator | Reject; never synthesize a citation |
| `AI-PROVENANCE` | Prohibited epistemic edge | Ledger validator | Reject and incident if repeated/systemic |
| `AI-POLICY` | Prohibited-use output | Policy validator | Refuse/stop; audit reason |
| `AI-INJECTION` | Source or user input changes stage policy | adversarial detector + behavior checks | Quarantine output; stop affected stage; security event |
| `AI-LEAK` | Cross-tenant, secret, prompt, or sensitive disclosure | DLP, authorization, red-team tests | Kill switch; incident response |
| `AI-STEREOTYPE` | Profile flattens/stereotypes a group | profile validator + human review | Reject/revise; sensitive-use review |
| `AI-CONVERGENCE` | Paths are paraphrases or collapse to one branch | distinctness validator | Retry independently; return incomplete if unresolved |
| `AI-OMISSION` | Selected uncertainty/profile is missing | coverage ledger | Block brief |
| `AI-DRIFT` | Behavior changes under same release/alias | eval and production signals | Suspend/canary/rollback |
| `AI-OVERREACH` | Recommendation or final decision presented as system conclusion | content/domain validator | Reject; require decision-owner conclusion |
| `AI-TOOL` | Unauthorized or malformed tool call | tool gateway | Deny; security telemetry |
| `AI-COST` | Unbounded tokens/retries/concurrency | budgets and rate limits | Stop with explicit limit state |
| `AI-TIMEOUT` | Provider timeout or unavailable service | adapter | Retry within policy; preserve progress |
| `AI-UNSAFE-OUTPUT` | XSS, SSRF-shaped URL, formula/code injection | sanitizer and safe renderer | Reject or neutralize without executing |

## Failure behavior

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
## Bounded retry policy

Retries are allowed only for failures likely to change without altering product
meaning:

- transient provider/network failure;
- rate limit;
- schema formatting failure;
- bounded missing field repair;
- stage-specific duplicate path with a revised diversity instruction.

Do not retry:

- prohibited use;
- tenant/authorization failure;
- source malware;
- truth-contract breach caused by the requested objective;
- unsupported file;
- unresolved rights attestation;
- exhausted cost budget;
- repeated prompt-injection behavior;
- missing human approval.

Retry budgets are stage-specific. Exponential backoff includes jitter. Each
attempt is immutable and visible in the run record.

## Fallback policy

Fallback requires an approved compatibility entry. The system MUST NOT:

- silently switch to a cheaper or weaker model;
- switch from a structured-output model to unrestricted text;
- drop source locations;
- omit a profile or uncertainty to finish;
- lower safety or truth validators;
- turn a failed external-human handoff into a synthetic answer.

When no approved fallback exists, fail clearly.

## User-facing error standard

An AI failure message contains:

1. what failed;
2. what remains saved;
3. whether the result is safe to inspect;
4. the next action;
5. a run/stage reference for support.

Example:

```text
Possible path P-03 did not pass the source and route checks.

Your reviewed decision, sources, assumptions, and the other generated paths are
saved. P-03 has not been added to the brief.

Retry this stage or inspect the run record.
```

Do not expose stack traces, provider secrets, raw prompts, or hidden reasoning.

## Degraded operation

The application MAY provide:

- read-only access to completed runs;
- export download for already validated artifacts;
- editing of draft decisions and assumptions;
- queued work when the durable engine is healthy but provider capacity is
  limited.

It MUST disable:

- new source parsing when scanning/sandboxing is unavailable;
- new AI stages when critical validators are unavailable;
- exports when disclosure/provenance validation is unavailable;
- cross-run search when tenant filtering cannot be guaranteed.

## Human escalation

Escalate to a named reviewer for:

- sensitive attributes;
- elevated-risk civic or public-service context;
- repeated source conflicts;
- profile stereotype warnings;
- severe model-judge disagreement;
- any request to override a critical validator;
- possible claim-integrity incident;
- possible cross-tenant or prompt-injection incident.

Critical validator override is prohibited in normal product operation. A
reviewer can revise inputs or create a new run, not bless an invalid artifact.

## Failure-mode tests

- chaos tests kill workers and provider calls at every stage;
- malformed schema and oversized output corpus;
- stale/mutable model alias simulation;
- hidden source instructions and multimodal injection;
- unavailable validator and export signer;
- duplicate workflow messages;
- cross-tenant IDs in model output;
- deceptive source citations;
- prompt leakage requests;
- user requests to remove truth disclosures;
- cost and concurrency exhaustion;
- accessibility tests for all failure states.

## Failure-mode acceptance

- no failure produces a final brief that bypasses critical gates;
- retries do not duplicate artifacts or billing records;
- all errors have stable codes and safe user copy;
- kill switches are tested;
- critical incidents enter the incident workflow;
- production monitoring can detect release drift without raw-content logging;
- the system can remain safely read-only during provider outage.

## References

- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.
- [OWASP LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/) — Model output must be validated and sanitized before downstream use.
- [OWASP LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) — Limit tools, permissions, functionality, and autonomy.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.

---
title: "Model Releases"
status: "Normative"
version: "1.0.0"
owner: "AI Platform + SRE + Research"
last_reviewed: "2026-07-29"
review_cycle: "Every model release"
research_cutoff: "2026-07-29"
---

# Model Releases

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

A model release is an approved, exact provider/model/configuration artifact for
one or more AI stages. Provider aliases such as `latest` are discovery inputs,
not reproducible production releases.

## Model-release record

```yaml
model_release_id: provider:model-snapshot:askthepeople-2026-07-29
provider_adapter: provider-adapter@3.2.0
provider_model_id: exact-provider-identifier
snapshot_resolved_at: 2026-07-29T00:00:00Z
supported_stages: [S01, S02, S03]
context_limit: 000000
max_output_tokens: 00000
decoding:
  temperature: 0.2
  top_p: 1.0
structured_output_mode: json_schema
data_region: configured
retention_mode: configured-and-verified
training_use: configured-and-verified
tool_support: []
safety_configuration_hash: ...
status: approved
eval_run_id: ...
approved_by: [...]
```

Unknown or provider-specific values are not invented. They are resolved and
recorded during integration and become a launch blocker when they affect
privacy, security, cost, or reproducibility.

## Model/provider adapter

Domain code must not import a provider SDK directly.

```ts
interface ModelProvider {
  generateStructured<T>(request: StructuredGenerationRequest<T>): Promise<StructuredGenerationResult<T>>;
  embed(request: EmbeddingRequest): Promise<EmbeddingResult>;
  moderate?(request: ModerationRequest): Promise<ModerationResult>;
  health(): Promise<ProviderHealth>;
}
```

The adapter handles:

- provider request format;
- model alias/snapshot;
- structured outputs;
- retryable vs terminal errors;
- refusal and incomplete states;
- rate limits;
- usage and cost metadata;
- data-retention flags;
- regional routing when available;
- redaction of secrets and unnecessary personal data.

For a greenfield OpenAI implementation, use the current Responses API and Structured Outputs where supported, but verify current official model and endpoint capabilities at build time. Do not hard-code this document’s model names. Use `store: false` for stateless stages unless the approved product architecture explicitly requires provider-side state.

## Structured-output discipline

Every generation stage uses a JSON Schema with:

- `additionalProperties: false` where supported;
- bounded string lengths;
- explicit enums;
- stable identifiers;
- no free-form HTML;
- no executable code;
- no raw URLs unless a source object explicitly requires one;
- no user-controlled property names;
- no recursive arbitrary graphs;
- explicit `incomplete` and `refusal` handling.

Schema validation is necessary but not sufficient. OWASP advises treating model output as untrusted and applying context-specific validation and encoding before using it in HTML, SQL, files, commands, or downstream tools.([OWASP LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/))

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
## Release process

1. **Discover.** Resolve exact provider identifier, capability, terms, data
   handling, regional availability, quotas, rate limits, and deprecation.
2. **Adapter conformance.** Verify request, structured output, error, timeout,
   usage, and cancellation behavior.
3. **Compatibility.** Run each proposed prompt/schema/validator combination.
4. **Evaluation.** Execute all required suites against the current baseline.
5. **Security/privacy review.** Confirm data classes, provider retention,
   training use, subprocessors, residency, and incident contacts.
6. **Cost/performance review.** Measure representative latency, output length,
   retry rate, and cost.
7. **Approval.** Create immutable release and exact compatibility matrix.
8. **Canary.** Limit to internal/test tenants or a small approved cohort.
9. **Monitor.** Apply predeclared rollback thresholds.
10. **Promote.** Change the application's release set, not the provider alias.
11. **Deprecate.** Maintain old release for replay/audit until retention permits
    retirement.

## Snapshot and alias rules

- A run stores the exact provider-returned model identifier when available.
- Mutable aliases are resolved at release creation and periodically checked.
- If a provider changes behavior behind an alias without a new identifier, the
  release is suspended when drift exceeds gates.
- Automatic fallback to a different model is prohibited unless the fallback is
  pre-approved for the stage and the manifest records the change.
- A retry MAY use the same exact release. Switching release mid-stage creates a
  new attempt and explicit provenance.
- Model retirement MUST NOT make old manifests unreadable.

## Compatibility matrix

| Model release | S02 extraction | S06 profiles | S08 paths | S12 brief | Status |
|---|---:|---:|---:|---:|---|
| exact release A | approved | not approved | not approved | approved | active |
| exact release B | approved | approved | approved | approved | canary |
| local/offline release C | approved for redacted fixtures | not approved | not approved | not approved | evaluation only |

The actual matrix is generated from the registry.

## Canary and rollback

Rollback triggers include:

- any critical truth, policy, tenant, injection, or source-fidelity failure;
- significant schema-validity regression;
- severe human-review regression;
- unexplained cost or latency increase beyond approved threshold;
- provider data-handling or availability change;
- increased duplicate-path or profile-stereotype rate;
- inability to resolve exact model identity.

Rollback restores the previous model/prompt release set. New runs use the prior
set; active workflows follow the workflow-version policy. Completed runs are
not rewritten.

## Provider incident response

The provider adapter exposes kill switches by provider, model release, stage,
organization, and global environment. A provider incident can:

- stop new invocations;
- quarantine in-flight outputs;
- switch only to a pre-approved fallback;
- revoke affected exports;
- trigger deletion/notification analysis;
- preserve safe metadata for investigation.

## Model-release acceptance

- exact model identity and adapter version are recorded;
- all supported stages pass required evals;
- data handling and subprocessors are verified;
- no silent fallback exists;
- canary and rollback have been exercised;
- release notes list measured changes and limitations;
- old run manifests remain interpretable.

## References

- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model) — Example provider guidance supporting lean, task-specific prompts and representative evaluations; the product remains provider-neutral.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.

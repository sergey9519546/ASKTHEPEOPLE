---
title: "ADR-0004: Provider adapters and immutable prompt registry"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "1 (typed API boundary) and 5 (model release + evals)"
applies_to: "all LLM calls, all prompts, all model aliases"
audit_relevance: "P0 'Prompt prefixing is not a security boundary'"
---
# ADR-0004: Provider adapters and immutable prompt registry

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

The repository supports OpenAI-compatible endpoints and Zep/OASIS dependencies.
Provider model aliases, SDK changes, and mutable prompts can alter behavior
without a code release. A single large runtime prompt also makes evaluation and
rollback imprecise.

## Decision

Place model, retrieval, and simulation dependencies behind provider-neutral
adapters. Decompose the workflow into small, typed stages. Store immutable
prompt releases, schema versions, model releases, decoding settings, validator
bundles, and tool permissions. Runs reference exact releases, not mutable
aliases.

## Consequences

Provider changes require adapter conformance and evaluation. Prompt changes
become release artifacts. This adds governance overhead but makes behavior
traceable and reversible.

## Alternatives considered

1. Hardcode provider SDK calls throughout services. Rejected due to lock-in and
   inconsistent policy enforcement.
2. One “god prompt.” Rejected because stages need separate schemas,
   permissions, evaluations, and failure behavior.
3. Store prompts only in a vendor dashboard. Rejected because repository and
   run manifests must remain auditable.

## Verification

Adapter contract tests, frozen-output fixtures where appropriate, prompt diff,
stage eval suite, canary release, and rollback drill.

## References

- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model) — Example provider guidance supporting lean, task-specific prompts and representative evaluations; the product remains provider-neutral.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.

## Project-specific implication (baseline `8b616dc7`)

The current code has the start of an adapter
([`backend/app/services/camel_model_factory.py`](../../../backend/app/services/camel_model_factory.py))
but no prompt registry and no model-release ledger. The audit's P0
finding "Prompt prefixing is not a security boundary" is the deepest
hazard.

### Current state

- Provider calls go through
  [`camel_model_factory.py`](../../../backend/app/services/camel_model_factory.py)
  and the request layer in
  [`backend/app/utils/llm_client.py`](../../../backend/app/utils/llm_client.py).
- Prompt templates are inlined in service code:
  ontology generation in
  [`services/ontology_generator.py`](../../../backend/app/services/ontology_generator.py),
  profile generation in
  [`services/oasis_profile_generator.py`](../../../backend/app/services/oasis_profile_generator.py),
  config generation in
  [`services/simulation_config_generator.py`](../../../backend/app/services/simulation_config_generator.py),
  and report generation in
  [`services/report_agent.py`](../../../backend/app/services/report_agent.py).
  None has a stable ID, a version, a release date, or an evaluation
  pass record.
- Model aliases are read from environment configuration. There is no
  model-release table, no EVALUATING → CANARY → ACTIVE → ROLLED_BACK
  state machine, no run-manifest recording the exact model identifier
  used per call.
- Provider debugging capture is governed by the absence of any
  retention setting rather than by an explicit decision.

### Required correction (per audit P0)

Generated-profile follow-up calls (and every other LLM call) MUST:

- Use separate system, developer, context, and user roles.
- Treat source material and run records as untrusted data.
- Bind zero tools.
- Use structured output.
- Run deterministic truth and terminology validators.
- Record prompt template ID, prompt version, model release, input
  hashes, output hash.
- Remove remotely accessible raw bypasses.
- Include adversarial prompt-injection evaluations.

### Required correction (per this ADR)

The adapter layer is the seam that hides model changes. Reaching
the ADR requires:

- A prompt registry with stable IDs, versions, owners, deprecation
  status, and evaluation results (see
  [`docs/ai/PROMPT_REGISTRY.md`](../../ai/PROMPT_REGISTRY.md)).
- A model release ledger (see
  [`docs/ai/MODEL_RELEASES.md`](../../ai/MODEL_RELEASES.md)).
- A run manifest that pins the exact prompt ID, version, model
  release, and decoding settings per call (see
  [`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](ADR-0012-canonical-transactional-and-object-persistence.md)).
- Adapter conformance tests and frozen-output fixtures.
- A canary release and rollback drill, called out in
  [`docs/release/RUNBOOK.md`](../../release/RUNBOOK.md).

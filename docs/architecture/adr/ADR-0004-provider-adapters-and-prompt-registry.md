---
title: "ADR-0004: Provider adapters and immutable prompt registry"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
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

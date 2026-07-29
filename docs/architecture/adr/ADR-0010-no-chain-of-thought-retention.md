---
title: "ADR-0010: No hidden chain-of-thought retention"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
---
# ADR-0010: No hidden chain-of-thought retention

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

The product needs auditability but does not need hidden model reasoning.
Retaining chain-of-thought can expose sensitive context, create unsupported
interpretability claims, increase privacy risk, and make logs an attractive
target. Users need concise rationales tied to approved inputs, stage outputs,
and validator results.

## Decision

Do not request, store, transmit to analytics, or expose hidden chain-of-thought.
Store structured inputs, outputs, concise user-visible rationales, source IDs,
prompt/model/schema versions, tool calls, validator results, and operational
metadata. Provider debugging capture is disabled by default and governed by the
retention and incident policies.

## Consequences

Some model debugging becomes less convenient. Evaluation must rely on outputs,
controlled probes, stage traces, and deterministic validation. Auditability
improves because records are bounded and meaningful.

## Alternatives considered

1. Store all reasoning for “transparency.” Rejected; verbose reasoning is not a
   reliable explanation or evidence.
2. Store reasoning only for admins. Rejected as a default; incident-specific
   capture must be separately justified and time-bounded.
3. Store concise rationale fields. Accepted as part of the decision.

## Verification

Schema scan for reasoning fields, logging tests, provider request review,
privacy audit, and incident-capture controls.

## References

- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.

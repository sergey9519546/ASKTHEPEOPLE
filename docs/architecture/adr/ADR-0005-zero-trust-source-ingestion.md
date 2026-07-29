---
title: "ADR-0005: Zero-trust source ingestion"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
---
# ADR-0005: Zero-trust source ingestion

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

Uploaded PDFs, documents, HTML, text, and archives are attacker-controlled.
They can contain malware, parser exploits, decompression bombs, sensitive
information, misleading metadata, and direct, indirect, or multimodal prompt
injection. Retrieval and fine-tuning do not eliminate prompt injection.

## Decision

Treat every source as untrusted data. Upload to quarantine, validate extension,
MIME and signature, scan and enforce limits, parse in an isolated no-network
worker, flag possible instructions, require review, and publish only normalized
approved segments. Model prompts explicitly delimit source text as data.
Model output is untrusted and passes deterministic validation.

## Consequences

Parsing is slower and some files are rejected or require manual review.
Security controls reduce feature convenience but prevent document content from
becoming privileged instruction or executable output.

## Alternatives considered

1. Parse in the API process. Rejected because parser compromise would cross the
   application trust boundary.
2. Trust MIME and filename. Rejected.
3. Use an LLM as the malware/injection filter. Rejected; model classification is
   supplemental, not the primary control.

## Verification

Malicious-file corpus, zip-bomb limits, parser sandbox tests, outbound-network
denial, prompt-injection red team, and deletion verification.

## References

- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) — Defense-in-depth upload controls.

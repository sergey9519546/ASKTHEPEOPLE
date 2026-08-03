---
title: "ADR-0005: Zero-trust source ingestion"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "0 (immediate correctness and security)"
applies_to: "all upload routes, all parser entry points, all LLM prompts that consume extracted source text"
audit_relevance: "P0 'Unvalidated platform path component in the posts endpoint', P0 'Prompt prefixing is not a security boundary', P1 'Duplicated destructive start/restart lifecycle block'"
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

## Project-specific implication (baseline `8b616dc7`)

The current code partially implements this ADR. Gate 0 is owned by
`askthepeople-security-reviewer`.

### Current state

- Source upload uses a randomized safe filename and never exposes
  the original filename downstream
  ([`models/project.py:247-278`](../../../backend/app/models/project.py:247)).
- File parser in
  [`backend/app/utils/file_parser.py`](../../../backend/app/utils/file_parser.py)
  (8 KB) handles PDF, DOCX, MD, TXT, EML. There is no malware scan,
  no MIME signature check, no quarantine state, no scan worker.
- `extracted_text.txt` is written to a per-project location
  ([`models/project.py:280-296`](../../../backend/app/models/project.py:280))
  and is consumed by LLM calls in
  [`services/ontology_generator.py`](../../../backend/app/services/ontology_generator.py),
  [`services/oasis_profile_generator.py`](../../../backend/app/services/oasis_profile_generator.py),
  and
  [`services/simulation_config_generator.py`](../../../backend/app/services/simulation_config_generator.py).
  The current code does not isolate source text as a separate
  prompt role.

### Required correction (per audit P0)

The audit identifies the P0 path-escape finding in the posts
endpoint:

```python
platform = request.args.get("platform", "reddit")
db_file = f"{platform}_simulation.db"
db_path = os.path.join(sim_dir, db_file)
```

This MUST be replaced with a fixed allowlist:

```python
PLATFORM_DATABASES = {
    "reddit": "reddit_simulation.db",
    "twitter": "twitter_simulation.db",
}
```

with the platform parsed as a strict enum, `422` for unknown values,
SQLite opened read-only, and typed errors for missing table, locked
database, corrupt database, and query timeout.

### Required correction (per audit P0 prompt-prefixing)

Every LLM call that consumes source text MUST:

- Use separate system, developer, context, and user roles.
- Treat source material as untrusted data, never as instruction.
- Bind zero tools.
- Use structured output.
- Run deterministic truth and terminology validators.
- Include adversarial prompt-injection evaluations in the eval
  suite.

### Required correction (per this ADR)

The full zero-trust ingestion state machine from
[`docs/architecture/state-machines.md`](../state-machines.md)
"Source-ingestion state machine" is **TARGET** and lands with gate 0
plus gate 3:

- `QUARANTINED` for any new upload, with no user-facing download
  route.
- `SCANNING` for signature, MIME, malware, decompression-bomb
  checks.
- `PARSING` in an isolated no-network worker.
- `FLAGGED` for injection / ambiguity / prompt-injection risk.
- `NEEDS_REVIEW` for user approval of any flagged or scanned
  artifact.
- `READY` for approved, normalized, segmented content.
- `DELETION_PENDING` for source retirement; `DELETED` only after
  primary copies are purged and backup aging is scheduled.

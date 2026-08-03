# Package manifest

**Package:** ASKTHEPEOPLE production documentation system  
**Version:** 1.0.0  
**Generated:** 2026-07-29  
**Repository baseline:** `c33a6a9127fa0705cfff426053f54815f58b4755`  
**Normative root:** `docs/`

## Summary

- Files in package inventory: **57**
- Markdown files: **53**
- Normative/reference Markdown files under `docs/`: **48**
- Architecture Decision Records: **12**
- Package Markdown words: **79,037**
- Package Markdown lines: **16,522**
- Design reference image: **1,788,272 bytes**

## Coverage by domain

| Domain | Markdown files | Words | Bytes |
|---|---:|---:|---:|
| `ai` | 4 | 7,233 | 54,553 |
| `architecture` | 16 | 7,872 | 64,503 |
| `design` | 4 | 9,000 | 60,535 |
| `docs-root` | 2 | 1,440 | 14,972 |
| `exec-plans` | 9 | 4,308 | 32,210 |
| `package-root` | 5 | 24,471 | 180,538 |
| `privacy` | 3 | 4,902 | 35,902 |
| `product` | 5 | 9,625 | 70,084 |
| `release` | 2 | 4,367 | 32,158 |
| `security` | 3 | 5,819 | 42,572 |

## File inventory

| Path | Bytes |
|---|---:|
| `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` | 164,853 |
| `INTEGRATION_GUIDE.md` | 4,447 |
| `README.md` | 3,498 |
| `TREE.txt` | 2,196 |
| `VALIDATION_REPORT.md` | 3,495 |
| `docs/README.md` | 6,009 |
| `docs/SOURCES.md` | 8,963 |
| `docs/ai/EVALS.md` | 15,937 |
| `docs/ai/FAILURE_MODES.md` | 8,618 |
| `docs/ai/MODEL_RELEASES.md` | 9,401 |
| `docs/ai/PROMPT_REGISTRY.md` | 20,597 |
| `docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md` | 2,873 |
| `docs/architecture/adr/ADR-0002-epistemic-ledger.md` | 2,419 |
| `docs/architecture/adr/ADR-0003-durable-run-orchestration.md` | 2,145 |
| `docs/architecture/adr/ADR-0004-provider-adapters-and-prompt-registry.md` | 2,188 |
| `docs/architecture/adr/ADR-0005-zero-trust-source-ingestion.md` | 2,106 |
| `docs/architecture/adr/ADR-0006-route-map-list-parity.md` | 2,003 |
| `docs/architecture/adr/ADR-0007-human-validation-boundary.md` | 2,301 |
| `docs/architecture/adr/ADR-0008-export-provenance.md` | 2,175 |
| `docs/architecture/adr/ADR-0009-multi-tenant-isolation.md` | 1,819 |
| `docs/architecture/adr/ADR-0010-no-chain-of-thought-retention.md` | 2,228 |
| `docs/architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md` | 2,699 |
| `docs/architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md` | 3,142 |
| `docs/architecture/adr/README.md` | 2,011 |
| `docs/architecture/data-model.md` | 12,175 |
| `docs/architecture/index.md` | 13,886 |
| `docs/architecture/state-machines.md` | 8,333 |
| `docs/design/ACCESSIBILITY.md` | 10,171 |
| `docs/design/CONTENT_SYSTEM.md` | 14,345 |
| `docs/design/DIRECTION_C.md` | 21,541 |
| `docs/design/ROUTE_GRAMMAR.md` | 14,478 |
| `docs/design/assets/ASKTHEPEOPLE_Civic_Wayfinding_Reference.png` | 1,788,272 |
| `docs/exec-plans/00-repository-census-and-governance.md` | 4,417 |
| `docs/exec-plans/01-truth-layer-and-foundations.md` | 4,191 |
| `docs/exec-plans/02-tenancy-data-and-secure-ingestion.md` | 3,743 |
| `docs/exec-plans/03-method-inputs-and-review.md` | 3,620 |
| `docs/exec-plans/04-durable-orchestration-and-path-engine.md` | 3,525 |
| `docs/exec-plans/05-brief-handoff-exports-and-provenance.md` | 3,560 |
| `docs/exec-plans/06-security-privacy-observability-and-operations.md` | 2,968 |
| `docs/exec-plans/07-evals-accessibility-and-release.md` | 3,739 |
| `docs/exec-plans/README.md` | 2,447 |
| `docs/privacy/DATA_MAP.md` | 17,179 |
| `docs/privacy/RETENTION.md` | 9,571 |
| `docs/privacy/SUBPROCESSORS.md` | 9,152 |
| `docs/product/METHODOLOGY.md` | 25,073 |
| `docs/product/PRODUCT_TRUTH_CONTRACT.md` | 11,403 |
| `docs/product/SUCCESS_METRICS.md` | 14,356 |
| `docs/product/TERMINOLOGY.md` | 8,378 |
| `docs/product/USE_POLICY.md` | 10,874 |
| `docs/release/ACCEPTANCE.md` | 20,869 |
| `docs/release/RUNBOOK.md` | 11,289 |
| `docs/security/INCIDENT_RESPONSE.md` | 11,084 |
| `docs/security/SOURCE_INGESTION.md` | 13,697 |
| `docs/security/THREAT_MODEL.md` | 17,791 |
| `tools/validate_docs.py` | 8,012 |
| `MANIFEST.md` | generated document; size intentionally omitted to avoid self-reference |
| `CHECKSUMS.sha256` | generated after this manifest |

## Authority note

The integrated `/GODMODE` build plan is a supporting synthesis. The modular
documents under `docs/` are the normative implementation and release
authority. The Product Truth Contract, Use Policy, accepted ADRs, and Release
Acceptance document control when wording differs.

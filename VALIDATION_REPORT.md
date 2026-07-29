# Documentation validation report

**Package:** ASKTHEPEOPLE production documentation system  
**Validation date:** 2026-07-29  
**Repository baseline:** `c33a6a9127fa0705cfff426053f54815f58b4755`  
**Validator:** `tools/validate_docs.py`

## Result

**PASS — zero structural validation errors and zero warnings.**

## Scope measured

- Normative/reference Markdown files under `docs/`: **48**
- Documentation words under `docs/`: **54,566**
- Documentation lines under `docs/`: **11,359**
- Indexed ADRs: **12**
- Unique external research/reference URLs in `docs/`: **53**
- Civic Wayfinding reference asset: **present**, 1,788,272 bytes

## Automated checks executed

1. All required documents and the design reference asset exist.
2. Every Markdown file under `docs/` is UTF-8 and contains required front matter.
3. Every modular document has exactly one H1 and no heading-level jumps.
4. Fenced code blocks are balanced.
5. Relative document and image links resolve and remain inside the package.
6. Footnote references and definitions are complete.
7. Placeholder patterns are absent.
8. ADR numbers are unique and every ADR is present in the ADR index.
9. Critical truth clauses remain present, including zero-human disclosure,
   forecast boundary, machine-readable synthetic origin, external-human-evidence
   separation, and source-role limitation.
10. Critical methodology clauses remain present, including non-survey status,
    external-validity limitation, disconfirmation, and the human-validation
    handoff.

## Manual consistency review completed

- User-facing descriptor is consistently locked to **Synthetic Decision
  Explorer** in normative documents and the master plan.
- Target architecture is not described as current implementation.
- The repository baseline is pinned to an exact commit and requires a new census
  before implementation.
- Article 50 dates use concrete future-effective wording relative to the
  research cutoff.
- C2PA is described as provenance/integrity infrastructure, not proof of truth.
- NIST Privacy Framework 1.1 is identified as draft/coming-soon at the research
  cutoff, not as a final standard.
- Uploaded source material is treated as hostile data, never instruction.
- OASIS/CAMEL actors and events are contained as generated decision lenses and
  synthetic run material, never respondents or observed behavior.
- Route map and semantic list are required to carry equivalent information.
- Release gates cover truth, methodology, accessibility, tenancy, security,
  privacy, AI evaluation, rollback, exports, and comprehension testing.

## Research currency review

The source register was reconciled through **2026-07-29** against current
primary or authoritative sources, including AAPOR's May 2026 responsible-AI
survey-research report, NIST AI RMF 1.0 and AI 600-1, OWASP GenAI security
controls, WCAG 2.2, NIST SP 800-61 Rev. 3, C2PA 2.4, and the European
Commission's final July 2026 Article 50 transparency guidelines. The source
register explicitly labels drafts and nonbinding guidance.

## Limits of this validation

This report validates the documentation package, not the current application.
It does not establish legal compliance, methodological external validity,
security certification, accessibility conformance, production readiness, or
implementation completeness. Those outcomes require the evidence and human
review defined in `docs/release/ACCEPTANCE.md`.

## Re-run

```bash
python tools/validate_docs.py
```

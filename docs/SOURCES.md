---
title: "Research Source Register"
status: "Reference"
version: "1.0.0"
owner: "Research + Product"
last_reviewed: "2026-07-29"
review_cycle: "Monthly"
research_cutoff: "2026-07-29"
---

# Research source register

This register records the external sources used to design the documentation
system. It is not a claim that ASKTHEPEOPLE is certified by, endorsed by, or
automatically compliant with any source.

## Source classifications

| Class | Meaning |
|---|---|
| Law / regulation | Binding only when the product, organization, processing, and jurisdiction are in scope |
| Final standard or government guidance | Authoritative implementation or risk-management reference |
| Draft or work in progress | Useful signal; MUST NOT be described as final |
| Professional guidance | Domain-specific good practice, not law |
| Peer-reviewed research | Empirical evidence within the paper's task, population, and limitations |
| Preprint | Provisional evidence; MUST be labeled as such |
| Product or competitor material | Market-positioning evidence only; not proof of performance |
| Repository baseline | Evidence of the current implementation, not the target architecture |

## Research cutoff

Sources were checked through **2026-07-29**. Current-status claims MUST be
rechecked before a release when the source can change, especially model
documentation, laws, regulatory guidance, dependencies, accessibility
interpretations, security advisories, and subprocessor terms.

## Research ethics and synthetic-output boundaries

- [AAPOR — Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/)  
  Professional guidance covering data quality, validity, reliability,
  sensitivity, performance, transparency, human oversight, and disclosure.
- [AAPOR — Standards and Ethics](https://aapor.org/standards-and-ethics/)  
  Current professional ethics and disclosure context.
- [Boelaert et al., “Machine Bias. How Do Generative Language Models Answer Opinion Polls?”](https://journals.sagepub.com/doi/10.1177/00491241251330582)  
  Peer-reviewed, task-specific evidence on bias and low variance in generated
  opinion responses.
- [Wang, Morgenstern, and Dickerson, “Large language models that replace human participants can harmfully misportray and flatten identity groups”](https://www.nature.com/articles/s42256-025-00986-z)  
  Peer-reviewed evidence supporting a non-substitution product boundary.
- [Lin, “Six Fallacies in Substituting Large Language Models for Human Participants”](https://journals.sagepub.com/doi/full/10.1177/25152459251357566)  
  Methodological argument for complement/simulation framing rather than human
  replacement.
- [ACL 2026 — Can LLM Agents Simulate Multi-Turn Human Behavior?](https://aclanthology.org/2026.acl-long.2034/)  
  Task-specific behavioral-fidelity evaluation; fluent behavior is not
  sufficient proof of action-level human accuracy.
- [npj Complexity — Too human to model (2026)](https://www.nature.com/articles/s44260-026-00075-1)  
  Analysis of tensions between expressive LLM agents and interpretable,
  intervention-oriented models.

## Scenario and foresight method

- [OECD — Strategic Foresight Toolkit for Resilient Public Policy](https://www.oecd.org/en/publications/foresight-toolkit-for-resilient-public-policy_bcdd9304-en.html)
- [OECD — Scenarios: A user guide](https://www.oecd.org/en/publications/back-to-the-future-s-of-education_178ef527-en/full-report/component-5.html)
- [UK Government — Futures Toolkit](https://www.gov.uk/government/publications/futures-toolkit-for-policy-makers-and-analysts/the-futures-toolkit-html)

These sources support the use of alternative, deliberately different scenarios
for challenging assumptions and stress-testing action. They do not validate
ASKTHEPEOPLE's generated paths as forecasts.

## AI risk, evaluation, and governance

- [NIST AI Risk Management Framework 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)
- [NIST AI RMF Playbook](https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook)
- [NIST AI 600-1 — Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)
- [NIST AI Resource Center](https://airc.nist.gov/)
- [OpenAI — model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [OpenAI — models](https://developers.openai.com/api/docs/models)

NIST AI RMF 1.0 remained the current final framework at the research cutoff
while revision work was underway. Provider guidance is an implementation
reference only; the product architecture is provider-neutral.

## AI and application security

- [OWASP LLM01:2025 — Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [OWASP LLM05:2025 — Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)
- [OWASP LLM06:2025 — Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)
- [OWASP LLM08:2025 — Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)
- [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)

## Accessibility and public-service design

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [WAI-ARIA Authoring Practices — Modal Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [Understanding Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum)
- [Understanding Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [GOV.UK Design System — Notification banner](https://design-system.service.gov.uk/components/notification-banner/)
- [GOV.UK Design System — Check answers](https://design-system.service.gov.uk/patterns/check-answers/)
- [ONS Service Manual — Using colours in charts](https://service-manual.ons.gov.uk/data-visualisation/colours/using-colours-in-charts)

## Privacy and incident response

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)
- [NIST Privacy Framework 1.1 project page](https://www.nist.gov/privacy-framework/new-projects/privacy-framework-version-11)  
  At the research cutoff, version 1.1 was still identified as coming soon; its
  initial public draft MUST NOT be represented as a final standard.
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final)
- [EDPB — data breaches](https://www.edpb.europa.eu/sme/assess-the-risks/data-breaches_en)
- [EDPB — processors and subprocessors opinion](https://www.edpb.europa.eu/news/edpb-adopts-opinion-on-processors-guidelines-on-legitimate-interest-statement-on-draft_en)

## Transparency, provenance, and claims

- [European Commission — Article 50 transparency guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems)  
  Published 20 July 2026; the relevant Article 50 transparency duties begin
  applying 2 August 2026, subject to scope and limited transition rules.
- [European Commission — Article 50 Q&A](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
- [C2PA specifications](https://spec.c2pa.org/specifications/)
- [FTC — Workado unsupported AI accuracy claims](https://www.ftc.gov/news-events/news/press-releases/2025/08/ftc-approves-final-order-against-workado-llc-which-misrepresented-accuracy-its-artificial)
- [FTC — DoNotPay deceptive AI lawyer claims](https://www.ftc.gov/news-events/news/press-releases/2025/02/ftc-finalizes-order-donotpay-prohibits-deceptive-ai-lawyer-claims-imposes-monetary-relief-requires)

## Production engineering

- [PostgreSQL row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [RFC 9562 — UUIDs](https://www.rfc-editor.org/rfc/rfc9562.html)
- [OpenTelemetry](https://opentelemetry.io/docs/)
- [Temporal documentation](https://docs.temporal.io/)
- [CNCF CloudEvents](https://cloudevents.io/)
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [JSON Schema](https://json-schema.org/specification)

## Repository baseline

The current baseline is documented in the project README and package manifests.
The baseline includes Vue, Vite, Flask, Flask-Sock, OASIS/CAMEL, Zep Cloud,
OpenAI-compatible model endpoints, PyMuPDF, NetworkX, SQLite/JSONL artifacts,
Vitest, and Pytest. These facts describe the current implementation; they do not
override target architecture requirements.

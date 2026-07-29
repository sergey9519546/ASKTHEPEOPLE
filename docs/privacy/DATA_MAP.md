---
title: "Privacy Data Map"
status: "Normative"
version: "1.0.0"
owner: "Privacy + Security + Data Governance"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly and every subprocessor/data-flow change"
research_cutoff: "2026-07-29"
---

# Data Map

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

This data map records what the product processes, why, where it flows, who can
access it, and how it is deleted. It is an engineering and governance control.
It does not by itself establish a lawful basis or satisfy a jurisdiction's
privacy notice, DPIA, contract, or data-subject-right process.

ASKTHEPEOPLE follows data minimization: process the least data needed to explore
a decision and prepare research. The product is not designed to build long-term
profiles of real people.

## Roles and configurable legal basis

The product operator's role—controller, processor, service provider, contractor,
or other classification—depends on the deployment and contract. The
organization MUST configure and document:

- operating legal entity;
- customer/controller relationship;
- purpose and instructions;
- applicable jurisdictions;
- lawful basis where required;
- sensitive-data conditions;
- international transfer mechanism;
- privacy contact and escalation route.

Production MUST remain disabled for a region/customer class when these facts are
unresolved.

## Data-flow overview

```mermaid
flowchart LR
  A[User / identity provider] --> B[Web + API]
  B --> C[(PostgreSQL)]
  B --> D[Quarantine object storage]
  D --> E[Isolated source worker]
  E --> F[Processed object storage]
  E --> C
  C --> G[Durable workflow]
  G --> H[Configured LLM provider]
  G --> I[Configured graph/retrieval provider]
  G --> J[OASIS/CAMEL adapter]
  H --> C
  I --> C
  J --> C
  C --> K[Export service]
  K --> F
  B --> L[Privacy-safe telemetry]
```

## Privacy data map

Create and maintain a data map for:

| Data class | Examples | Sensitivity | Storage | Retention | Model exposure |
|---|---|---|---|---|---|
| Account data | name, email, role | Personal | Identity/DB | account life + policy | none/minimal |
| Source material | uploaded documents | potentially confidential/high | object storage | project life or workspace policy | minimum required segments |
| Extracted text | normalized source spans | same as source | DB/index | source life | scoped |
| Decision data | question, assumptions | confidential | DB | project life | scoped |
| Generated artifacts | profiles, paths, brief | confidential/synthetic | DB | project life | scoped |
| Invocation metadata | model, tokens, latency | operational | observability/DB | 30–90 days | n/a |
| Audit events | actor/action/time | security | immutable log | policy-defined | none |
| External human evidence | research results [Phase 2] | potentially sensitive/high | separate DB/storage | method/policy-defined | off by default |

Do not duplicate raw customer content in analytics or error tools.

## Data minimization

- Ask only for information necessary to construct the decision.
- Do not require demographics.
- Do not infer protected or sensitive attributes.
- Redact secrets and obvious personal identifiers before model calls where they are not needed.
- Allow users to exclude source sections.
- Let users preview exactly what will be sent to the model for elevated-risk runs.
- Avoid provider-side conversation state for stage calls that do not need it.
- Store canonical artifacts once; do not copy full request bodies into logs.

## Retention and deletion

Implement configurable workspace policy. Recommended baseline:

- source assets and canonical project artifacts: retained until project/workspace deletion;
- soft-deleted items: recoverable for 30 days;
- hard deletion: queued after recovery period;
- operational logs: 30 days unless security policy requires longer;
- audit/security events: policy-defined, separated from content logs;
- temporary parsing artifacts: delete within 24 hours after successful processing;
- signed URLs: minutes, not days;
- backups: documented rolling window with eventual deletion guarantees;
- provider request retention: minimize using available controls and document actual provider behavior.

OpenAI states that API/business data is not used to train models by default and offers retention controls for eligible uses, but the build must verify current provider terms and endpoint behavior before launch.([OpenAI business data privacy](https://openai.com/business-data/))

Deletion must cover:

- database rows;
- object storage;
- vector/search indexes;
- caches;
- derived previews;
- exports under product control;
- queued jobs;
- provider-stored state where applicable;
- backup expiry documentation.

## PII and sensitive-data handling

- Show a pre-upload warning for personal, health, financial, legal, employment, education, and children’s data.
- Add optional detection/redaction before model use.
- Do not market the tool for regulated records without a separately approved compliance architecture and contracts.
- Flag highly sensitive content for elevated review.
- Do not expose PII in run titles, notifications, URLs, analytics properties, or email subjects.
- Make access to source text auditable.
- Allow workspace policy to disable source retention or external model use.

## Transparency and regulatory triggers

### EU AI Act Article 50

Beginning August 2, 2026, Article 50 transparency obligations apply to covered providers and deployers, including explicit notice for direct AI interaction and machine-readable marking of certain AI-generated content; public-interest AI-generated text can trigger deployer disclosure duties subject to human editorial-control exceptions and other scope details. ([EU AI Act Article 50](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50))([European Commission Article 50 transparency guidance](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems))

Product response:

- inform users when they interact with AI;
- visibly label generated artifacts;
- include machine-readable origin metadata;
- preserve human editorial approval records;
- conduct jurisdiction-specific legal review before EU launch;
- do not assume C2PA alone establishes compliance.

### California privacy and ADMT

California’s final privacy regulations became effective January 1, 2026, with certain ADMT significant-decision requirements beginning January 1, 2027.([California Privacy Protection Agency ADMT regulations](https://cppa.ca.gov/announcements/2025/20250923.html)) The product should remain outside significant-decision automation by policy, but privacy, risk-assessment, access, and opt-out obligations must be reviewed against actual use and business thresholds.

### Consumer-protection claims

No marketing or in-product claim of accuracy, efficacy, human equivalence, representativeness, bias freedom, or prediction may ship without competent, reliable, use-specific evidence. FTC actions against unsupported AI performance and substitution claims make this a release concern, not merely copy preference.([FTC Workado accuracy-claims order](https://www.ftc.gov/news-events/news/press-releases/2025/08/ftc-approves-final-order-against-workado-llc-which-misrepresented-accuracy-its-artificial))([FTC DoNotPay order](https://www.ftc.gov/news-events/news/press-releases/2025/02/ftc-finalizes-order-donotpay-prohibits-deceptive-ai-lawyer-claims-imposes-monetary-relief-requires))
## Data inventory

| Category | Examples | Source | Purpose | Primary stores | External recipients | Default privacy class |
|---|---|---|---|---|---|---|
| Account identity | name, work email, IdP subject | user/IdP | authentication, authorization, support | IdP, PostgreSQL | identity provider, email provider if configured | Personal |
| Organization metadata | organization, role, policy configuration | admin | tenancy, access, governance | PostgreSQL | none by default | Business confidential |
| Decision data | question, owner, constraints, intended use | user | scenario exploration | PostgreSQL | model provider only when stage requires | Business confidential |
| Source files | PDF/DOCX/TXT/HTML/CSV | user upload | starting-condition extraction | quarantine/processed object storage | parser, model/graph provider only after policy | Potentially sensitive |
| Source segments | normalized text, page/section | parser/user | reviewed provenance and retrieval | PostgreSQL/object store | configured providers as needed | Same as source |
| Assumptions and uncertainties | reviewed statements | user/model proposal | scenario construction | PostgreSQL | model provider | Business confidential |
| Generated profiles | functional constraints and criteria | model/user review | decision-lens application | PostgreSQL | model/simulation provider | Synthetic; may reflect sensitive context |
| Synthetic events and paths | actions, considerations, questions | model/simulation | scenario exploration | PostgreSQL/object store | model provider for later stages | Synthetic business data |
| Human research metadata | method, sample, dates, findings | optional future import | separate external-evidence register | PostgreSQL/object store | no provider by default | Potentially sensitive human data |
| Run metadata | model/prompt/schema IDs, timestamps, status, usage | system/provider | audit, reproducibility, operations | PostgreSQL | telemetry backend | Operational |
| Audit/security logs | actor, action, IP/security metadata, IDs | system | security, compliance, incident response | append-only log/telemetry | security provider | Security confidential |
| Support data | ticket, diagnostic bundle | user/support | support | support system | support provider | Varies; minimize |
| Billing data | plan, usage totals, payment reference | system/customer | billing | billing system | payment provider | Personal/financial metadata |
| Export/share data | artifact, recipient/share token | user/system | delivery | object store/PostgreSQL | authorized recipient | Same as artifact |
| Consent/attestation | authority, rights, policy acknowledgment | user | governance | PostgreSQL/audit | none by default | Personal/business |

## Purpose limitation

Data collected for a source-processing or run purpose MUST NOT be repurposed for:

- training a general model without explicit authorization;
- advertising or sale;
- building a real-person behavior profile;
- unrelated cross-customer retrieval;
- public benchmarking;
- employee/customer monitoring;
- political targeting;
- new product analytics requiring raw content.

A new purpose requires data-map, notice/contract, risk, retention, and
subprocessor review.

## Data minimization

### Decision and source intake

- Ask for functional context, not unnecessary identities.
- Warn before upload of regulated, confidential, or personal data.
- Provide redaction and source removal before model invocation.
- Do not infer protected traits.
- Do not make geographic or demographic detail mandatory unless materially
  relevant and approved.
- Keep original source only as long as the configured purpose requires.

### Generated profiles

Profiles MUST not contain real names, contact details, portraits, biographies,
or links to identifiable people. Sensitive attributes require justification and
review.

### Telemetry

Routine telemetry may include IDs, status, duration, error code, version, usage,
and hashed organization scope. It MUST NOT include:

- raw source text;
- full prompts;
- generated biographies or fictional quotations;
- credentials;
- access tokens;
- unredacted user email;
- human-research responses;
- hidden chain-of-thought.

## Access matrix

| Role | Decision/source content | Run outputs | Export | Audit/security | Privacy operations |
|---|---:|---:|---:|---:|---:|
| Owner/Admin | yes | yes | yes | limited org audit | request/manage |
| Editor | yes | yes | yes if granted | no | request own/project actions |
| Reviewer | reviewed inputs/outputs | yes | review only | no | no |
| Viewer | approved content only | yes | download if granted | no | no |
| Security | incident-scoped, just-in-time | incident-scoped | revoke | yes | hold |
| Privacy | request-scoped, minimized | request-scoped | revoke/delete | privacy events | yes |
| Support | masked by default; JIT approval | masked | no direct export | limited | no |
| Worker service | exact IDs and required objects | stage-specific | no | write safe telemetry | deletion-specific |
| Model provider | stage payload only | stage response | no | provider request ID | provider deletion where supported |

## Storage and encryption

- TLS for data in transit.
- Managed encryption at rest for databases/object storage.
- Separate production and nonproduction environments.
- Customer-managed keys MAY be offered; the key lifecycle and loss implications
  must be explicit.
- Backup encryption and restore permissions are reviewed.
- Export/share URLs use high-entropy, scoped, expiring tokens.
- Sensitive diagnostic data uses separate access and shorter retention.

## Data-subject and customer rights operations

The product MUST support authenticated workflows to:

- access/export account and project data;
- correct identity and user-authored data;
- delete or restrict processing subject to legal/contractual constraints;
- revoke shares;
- identify providers and storage locations involved;
- record identity verification, scope, decision, actions, and completion.

Generated synthetic data is still customer data and is included in project
export/deletion when applicable. Third-party source data may require separate
authority analysis.

## Sensitive and regulated data

V1 SHOULD prohibit or strongly restrict processing of:

- health records;
- financial account records;
- precise location histories;
- government identifiers;
- biometric templates;
- children's data;
- criminal/legal case files;
- employment evaluation records;
- confidential data without authority.

A regulated-data mode requires an approved deployment profile, contract,
provider configuration, security controls, incident obligations, and DPIA/risk
assessment. Marketing MUST NOT imply HIPAA, FERPA, GLBA, GDPR, or other
compliance merely because a provider advertises a certification.

## Privacy risk assessment triggers

Complete a DPIA or equivalent review when:

- sensitive data is processed at scale;
- systematic monitoring or profiling is proposed;
- real-person or human-research evidence is introduced;
- a new jurisdiction or residency pattern is enabled;
- a new provider receives source content;
- profiles use sensitive attributes;
- automated decision support moves toward high-impact use;
- cross-project retrieval is introduced;
- data is used to train or improve models;
- retention materially increases.

## International transfers

Before enabling a provider or region, record:

- data origin and destination;
- legal entities and roles;
- transfer mechanism;
- supplementary measures;
- subprocessor locations;
- access request/government disclosure terms;
- customer controls;
- data residency limitations.

## Privacy acceptance

- data inventory matches code, providers, and telemetry;
- every field has purpose, class, owner, and retention;
- no raw content appears in analytics by default;
- provider transfers are documented and configurable;
- access and deletion workflows are tested;
- sensitive-data warnings and blocks work;
- privacy notices and contracts match actual behavior;
- unresolved region/legal-basis/provider facts block production enablement.

## References

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) — Privacy risk-management framework; version 1.1 remained a draft/coming-soon work item at the research cutoff.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [European Commission Article 50 transparency guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems) — Final July 2026 guidance on transparency obligations that apply from 2 August 2026.

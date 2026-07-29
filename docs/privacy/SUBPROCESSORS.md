---
title: "Subprocessors"
status: "Normative"
version: "1.0.0"
owner: "Privacy + Procurement + Security"
last_reviewed: "2026-07-29"
review_cycle: "Monthly and before provider change"
research_cutoff: "2026-07-29"
---

# Subprocessors

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

This document is the operational source of truth for external organizations that
may process customer or personal data on behalf of ASKTHEPEOPLE. A dependency is
not automatically a subprocessor: open-source code running in ASKTHEPEOPLE's
controlled infrastructure is a software supplier; a hosted service receiving
customer data may be a subprocessor.

The public subprocessor notice and customer contract MUST be generated from an
approved version of this register.

## Production launch rule

A provider cannot receive production source, decision, generated, identity, or
security data until its record contains:

- exact legal entity and service;
- processing purpose and data categories;
- controller/processor role;
- countries and regions;
- subprocessors/fourth parties or authoritative source;
- security and compliance evidence;
- retention and deletion behavior;
- training/model-improvement use;
- incident-notification terms and contact;
- DPA and transfer mechanism where required;
- customer configuration and opt-out/migration path;
- risk assessment and approvals;
- effective and review dates.

An unresolved field is not a harmless `TBD`; it is a **launch blocker** for that
provider/data class.

## Current repository dependency classification

| Dependency / service | Current evidence | Classification | Production decision |
|---|---|---|---|
| Configured OpenAI-compatible LLM endpoint | `.env`/backend supports a provider chosen by operator | Potential subprocessor | Disabled for production content until exact provider/model/legal/data-handling record is approved |
| Zep Cloud | backend manifest includes `zep-cloud`; README states source/profile/prompt data may be sent | Subprocessor when hosted Cloud receives customer content | Disabled or restricted until exact Zep Software, Inc. contract, region, retention, subprocessor, and deletion review is approved |
| OASIS / CAMEL-AI packages | Python dependencies executing in controlled worker by default | Software suppliers, not subprocessors when self-hosted | Track under software supply chain; reclassify if a hosted service receives data |
| PyMuPDF, NetworkX, pandas, Pydantic | local libraries | Software suppliers | SBOM/vulnerability/license management |
| PostgreSQL / object storage / workflow / telemetry | target services not selected in repository baseline | Potential subprocessors if managed | Each requires a completed provider record before production |
| Identity, email, support, billing/CDN/WAF | not established by current baseline | Potential subprocessors | Function remains disabled or self-hosted until selected and registered |

## Provider record schema

```yaml
provider_id: stable-id
legal_entity: exact contractual entity
service_name: exact product/plan
service_category: llm | retrieval | hosting | storage | identity | telemetry | support
status: proposed | approved | suspended | retired
data_categories:
  - source_content
purposes:
  - stage-specific inference
role: processor
regions:
  - exact region
international_transfer:
  mechanism: exact mechanism
  supplementary_measures: []
retention:
  request_response: exact verified behavior
  backups: exact verified behavior
deletion:
  method: api-or-support
  objective: exact contractual/verified period
training_use:
  default: exact verified behavior
  customer_control: exact control
security:
  certifications: []
  encryption: []
  access_controls: []
incident:
  notification_term: exact contract
  contact: exact contact
subprocessor_source: authoritative URL or contract exhibit
dpa: executed reference
risk_assessment_id: ...
approved_by: [...]
effective_at: ...
next_review_at: ...
```

## Due diligence

Review at minimum:

- corporate/legal identity;
- service architecture and data flow;
- data residency and transfer;
- encryption and key management;
- tenant isolation;
- employee/support access;
- secure development and vulnerability management;
- incident response and notification;
- business continuity and deletion;
- model training or improvement use;
- government access/transparency;
- subprocessor change notification;
- audit rights and evidence;
- financial/operational concentration risk;
- exit and data portability.

Certifications are evidence inputs, not a substitute for service-specific
review.

## Zep Cloud baseline note

The repository currently depends on `zep-cloud`. Official Zep documentation
identifies Zep Software, Inc. in its privacy policy, documents a managed cloud
service, and currently describes enterprise controls such as BYOK/BYOC and a
US-west region for the BYOK service. These public pages do not replace an
executed DPA, exact account configuration, current subprocessor list, retention
commitment, or deletion test. The production record MUST be based on the
contract and service actually purchased.

Debug or reasoning-trace modes that may capture content MUST remain disabled
unless a time-bounded diagnostic process under the retention and incident
policies explicitly authorizes them.

## Model-provider baseline note

“OpenAI-compatible” is a protocol description, not a legal/provider identity.
The operator MUST resolve the exact endpoint and model. The register records
whether requests/responses are retained, used for training, regionally
processed, reviewed by humans, or sent to additional subprocessors. A provider
cannot inherit another provider's privacy claims merely because the API format
is compatible.

## Subprocessor changes

Before adding or materially changing a provider:

1. update the data map and threat model;
2. complete due diligence and contract/DPA;
3. add the exact record;
4. evaluate model/service behavior;
5. test deletion and incident contacts;
6. provide customer notice/objection process where required;
7. deploy behind a kill switch;
8. canary with authorized data;
9. monitor;
10. preserve the prior register version.

## Customer-facing notice

The notice MUST state:

- provider legal name;
- service purpose;
- data categories;
- processing locations;
- effective date;
- link or method for more details;
- how customers receive change notices or object where contractually provided.

Avoid generic language such as “trusted partners.”

## Suspension and exit

Suspend a provider when:

- incident scope is unknown;
- contract or DPA expires;
- data-handling terms materially change;
- deletion cannot be confirmed;
- exact model/service identity is unavailable;
- security/eval gates fail;
- subprocessor changes exceed approved risk.

Exit includes disabling transfers, exporting required data, deleting provider
copies, rotating credentials, updating manifests, and preserving audit
evidence.

## Subprocessor acceptance

- every network egress destination is mapped to a provider or blocked;
- provider records match production configuration;
- exact legal entities and regions are known;
- deletion is tested;
- public notice matches the internal register;
- no hosted dependency is misclassified as only a library;
- no local library is incorrectly described as a data recipient;
- provider changes trigger customer and release workflows;
- security/privacy owners approve each active record.

## References

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) — Privacy risk-management framework; version 1.1 remained a draft/coming-soon work item at the research cutoff.
- [EDPB opinion on processors and subprocessors](https://www.edpb.europa.eu/news/edpb-adopts-opinion-on-processors-guidelines-on-legitimate-interest-statement-on-draft_en) — Controllers should have processor/subprocessor identity information readily available and verify sufficient guarantees.
- [Zep Software, Inc. privacy policy](https://help.getzep.com/legal/privacy-policy) — Public baseline only; contract and current service configuration control.
- [Zep BYOK documentation](https://help.getzep.com/bring-your-own-key) — Documents selected enterprise cloud encryption and region behavior; verify against purchased service.

---
title: "Subprocessors"
status: "Normative"
version: "1.1.0"
owner: "Privacy + Procurement + Security"
last_reviewed: "2026-07-29"
review_cycle: "Monthly and before provider change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P1 'No object-level authorization model'"
applies_to: "every external API call, every subprocessed transmission, every per-call telemetry record"
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

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) - Privacy risk-management framework; version 1.1 remained a draft/coming-soon work item at the research cutoff.
- [EDPB opinion on processors and subprocessors](https://www.edpb.europa.eu/news/edpb-adopts-opinion-on-processors-guidelines-on-legitimate-interest-statement-on-draft_en) - Controllers should have processor/subprocessor identity information readily available and verify sufficient guarantees.
- [Zep Software, Inc. privacy policy](https://help.getzep.com/legal/privacy-policy) - Public baseline only; contract and current service configuration control.
- [Zep BYOK documentation](https://help.getzep.com/bring-your-own-key) - Documents selected enterprise cloud encryption and region behavior; verify against purchased service.

---

## Project-specific subprocessor status (baseline `8b616dc7`)

The current code makes the following external calls. Per-call
recording (which subprocessor, which call, which input hashes,
which output hash, which prompt and model release) is **TARGET** and
is part of gate 3 (canonical persistence) and gate 1 (prompt
registry and model release ledger).

### LLM provider — CURRENT (call surface) / TARGET (per-call record)

- LLM calls go through
  [`utils/llm_client.py`](../../backend/app/utils/llm_client.py) and
  the provider factory
  [`services/camel_model_factory.py`](../../backend/app/services/camel_model_factory.py).
- The model alias is read from environment configuration. There is
  no per-call record of the model identifier used.
- The OpenAI-compatible endpoint URL and key are read from
  [`config.py`](../../backend/app/config.py).

### Zep Cloud graph memory — CURRENT (call surface) / TARGET (per-call record)

- ZEP calls go through
  [`services/zep_tools.py`](../../backend/app/services/zep_tools.py) (76 KB)
  and the entity reader
  [`services/zep_entity_reader.py`](../../backend/app/services/zep_entity_reader.py).
- ZEP is treated as a derived index. The current code does not
  declare a per-call record of which entities and which page
  contents were sent to ZEP for a given run.

### OASIS / CAMEL — CURRENT (in-process) / TARGET (per-call record)

- OASIS is invoked from
  [`services/simulation_runner.py`](../../backend/app/services/simulation_runner.py) (82 KB)
  via the
  [`services/simulation_ipc.py`](../../backend/app/services/simulation_ipc.py)
  layer. OASIS is loaded in-process today; it is a Python
  dependency, not an external network call.
- The OASIS dependency version is not recorded per run. Reaching
  the contract requires the per-attempt manifest from
  [`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](../architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md).

### File parser dependencies — CURRENT

- [`utils/file_parser.py`](../../backend/app/utils/file_parser.py) (8 KB)
  uses PyMuPDF, python-docx, BeautifulSoup, and other open-source
  libraries. These are bundled Python dependencies, not network
  services. A separate SBOM and license inventory is at the repo
  root
  [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).

### Rate limits and provider timeouts — PARTIAL

Provider rate limits are not surfaced per call. The
[`utils/retry.py`](../../backend/app/utils/retry.py) (8 KB) module
implements bounded retries. Reaching the contract requires per-
provider rate-limit visibility, per-call timeout, and an explicit
per-attempt cost estimate, all part of gate 4.

### Subprocessor UI / disclosure — TARGET

The doc requires a subprocessor list with region, data category,
purpose, retention, and a per-subprocessor change-log surfaced in
the UI. The current code does not have a subprocessor UI; the
information is in
[`docs/privacy/SUBPROCESSORS.md`](SUBPROCESSORS.md) only.
Reaching the contract requires a subprocessor component in the
admin UI and a per-call subprocessor correlation in the run
manifest. Gate 3 + gate 5.

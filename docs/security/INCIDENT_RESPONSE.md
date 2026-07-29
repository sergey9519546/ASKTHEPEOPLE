---
title: "Incident Response"
status: "Operational"
version: "1.0.0"
owner: "Security Incident Commander"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly exercise"
research_cutoff: "2026-07-29"
---

# Incident Response

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

## Framework

The incident program follows NIST SP 800-61 Rev. 3 and integrates preparation,
detection, response, recovery, and improvement into normal cybersecurity risk
management. This runbook is operational guidance, not a substitute for legal,
privacy, insurance, contractual, or law-enforcement advice.

## Incident definition

An incident includes confirmed or reasonably suspected compromise of:

- confidentiality, integrity, or availability;
- tenant isolation;
- source or export access;
- model/prompt/tool behavior;
- product-truth or claim integrity;
- deletion/retention;
- provider/subprocessor data handling;
- production credentials or CI/CD;
- safety/use-policy enforcement.

A severe model regression or disclosure omission can be an incident even
without traditional unauthorized access.

## Roles

| Role | Responsibility |
|---|---|
| Incident Commander | overall authority, severity, coordination, closure |
| Technical Lead | containment, eradication, recovery |
| Security Lead | investigation, evidence, threat analysis |
| Privacy Lead | personal-data scope, notification analysis |
| Product Truth Lead | synthetic/human/forecast claim impact |
| AI Lead | model/prompt/provider containment and eval |
| Communications Lead | internal/customer/public communications |
| Legal/Compliance | legal privilege, notification, regulator/contract duties |
| Scribe | immutable timeline, decisions, actions, evidence |
| Executive Sponsor | business decisions and major risk acceptance |

One person may hold multiple roles in a small team, but Incident Commander and
Scribe responsibilities remain explicit.

## Severity

| Severity | Criteria | Initial response objective |
|---|---|---|
| SEV-0 | active cross-tenant exfiltration, signing/CI compromise, widespread deceptive output, safety-critical misuse | immediate all-hands; global kill switch if needed |
| SEV-1 | confirmed sensitive data exposure, systemic prompt injection, critical provider breach, missing truth disclosure at scale | immediate paging and containment |
| SEV-2 | limited tenant incident, major model regression, malware bypass without confirmed spread | same business hour |
| SEV-3 | contained low-impact security defect or policy escape | one business day |
| SEV-4 | suspicious event requiring investigation | normal triage queue |

Objectives are internal priorities, not promises to affected parties.

## Lifecycle

```text
PREPARE
→ DETECT / REPORT
→ TRIAGE
→ CONTAIN
→ ERADICATE
→ RECOVER
→ MONITOR
→ POST-INCIDENT IMPROVEMENT
```

## Incident response

Incident classes:

- cross-tenant disclosure;
- prompt injection succeeded;
- source content affected system instructions;
- incorrect origin label;
- export missing disclosure;
- prohibited-use generation;
- model/prompt regression;
- source parser vulnerability;
- signing/provenance failure;
- sensitive-data exposure;
- unsupported public claim.

Required incident capabilities:

- identify affected prompt/model/source/run versions;
- disable prompt/model configuration by feature flag;
- stop queued runs;
- revoke shared artifacts;
- notify affected users where appropriate;
- preserve investigation evidence;
- document root cause and corrective action;
- add regression tests before re-enable;
- publish user-facing correction when an exported artifact was materially misleading.

---
## First 30-minute checklist

1. Open incident record and assign ID.
2. Preserve reporter details and original evidence.
3. Name Incident Commander and Scribe.
4. Classify provisional severity.
5. Establish a restricted communications channel.
6. Identify affected environment, organizations, runs, providers, and releases.
7. Activate the narrowest safe kill switch.
8. Preserve logs, workflow history, hashes, deployment/prompt/model releases.
9. Prevent automatic deletion of relevant evidence through an approved hold.
10. Notify privacy/legal/product truth leads when their domains may be affected.
11. Record every action and time.
12. Reassess severity after initial containment.

## Kill switches

The system MUST support:

- global new-run pause;
- provider/model-release pause;
- prompt-release pause;
- stage-specific pause;
- source-ingestion pause;
- export generation/download/share revocation;
- organization/project/run quarantine;
- public share-link revocation;
- retrieval/graph provider pause;
- admin/support access revocation.

Kill switches are tested quarterly.

## Evidence handling

Preserve:

- immutable run/event history;
- request/trace/job identifiers;
- exact deployment and release manifests;
- source and export hashes;
- authorization decisions;
- provider request IDs and status metadata;
- relevant audit and access logs;
- screenshots with time/context;
- notification and decision records.

Do not collect more raw customer content than needed. Evidence access is
restricted and audited. Chain of custody is documented when legal or regulatory
use is plausible.

## Playbooks

### Cross-tenant access or retrieval

- disable affected endpoint/search/retrieval;
- revoke active shares/tokens;
- identify all access paths and affected objects;
- preserve database/object/access logs;
- validate RLS/authorization and worker scope;
- rotate credentials if boundary compromise is possible;
- perform notification analysis;
- add a regression test before recovery.

### Prompt injection or tool manipulation

- stop affected stage/provider/tool;
- quarantine source and generated output;
- identify whether unauthorized data/tool access occurred;
- preserve exact prompt/tool/model release and source hashes;
- test related attack variants;
- invalidate affected briefs/exports;
- update controls and eval corpus;
- do not describe a detector update as a complete fix.

### Missing or misleading truth disclosure

- revoke affected exports/shares;
- stop the rendering/template release;
- identify all detached artifacts and downstream recipients;
- issue corrected artifact and clear notice;
- investigate whether a claim was relied on;
- update comprehension/linter/export tests;
- treat broad deceptive impact as SEV-1.

### Provider/subprocessor incident

- suspend new data transfer;
- use only pre-approved fallback or safe read-only mode;
- obtain provider scope/timeline;
- map affected data classes, regions, and tenants;
- trigger deletion/notification/contract analysis;
- update the subprocessor register and risk assessment.

### Credential or CI/CD compromise

- freeze deployment;
- revoke/rotate credentials and sessions;
- verify build provenance and deployed hashes;
- restore from trusted commit/artifact;
- inspect prompt/model/policy releases for tampering;
- invalidate signing keys and manifests if affected.

### Malware/parser escape

- stop ingestion;
- isolate worker fleet and storage;
- preserve sample and runtime telemetry safely;
- rotate worker credentials;
- verify no network/data-store access;
- rebuild from trusted images;
- expand malicious-file corpus.

### Model regression

- pause candidate release;
- restore previous release set;
- quarantine new outputs and exports;
- run targeted eval and impact scan;
- identify provider alias/change;
- notify users only with verified scope;
- preserve old runs unchanged.

## Communications

Communications MUST:

- distinguish confirmed facts, hypotheses, and unknowns;
- avoid unsupported attribution;
- state affected data and actions concretely;
- include synthetic-output/claim impact when relevant;
- coordinate legal/privacy deadlines;
- preserve versioned copies of every notification.

For personal-data breaches in applicable EU contexts, notification analysis
must consider the 72-hour supervisory-authority rule and the processor's duty
to notify the controller without undue delay. Applicability and timing require
legal/privacy determination.

## Recovery gates

Recovery requires:

- root cause or bounded contributing cause understood enough to operate safely;
- exploit path contained;
- credentials rotated where needed;
- clean deployment and release artifacts;
- targeted and regression tests pass;
- affected exports/shares handled;
- monitoring in place;
- privacy/legal communication decision documented;
- Incident Commander approval.

## Post-incident review

Complete within ten business days for SEV-0/1 and twenty for SEV-2 unless the
Incident Commander documents a reason.

The review includes:

- timeline;
- impact and affected scope;
- detection and response effectiveness;
- root and contributing causes;
- what went well/poorly;
- Product Truth Contract impact;
- corrective actions with owners and dates;
- eval, test, runbook, architecture, and training changes;
- recurrence and systemic-risk analysis;
- external communication summary.

Actions are tracked to closure. “Human error” is not an adequate root cause.

## Exercise program

Quarterly tabletop and at least annual technical exercise covering rotating
scenarios: cross-tenant leak, prompt injection, provider breach, signing-key
compromise, missing export disclosure, malware parser escape, and model drift.

## Incident-response acceptance

- on-call roster and contacts are current;
- kill switches work;
- evidence sources are available and time synchronized;
- notification decision matrix is reviewed;
- exercises produce tracked remediations;
- a restore/rollback exercise succeeds;
- lessons are added to eval and threat corpora;
- closure requires accountable approval.

## References

- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — Final incident-response recommendations aligned with CSF 2.0.
- [EDPB — Data breaches](https://www.edpb.europa.eu/sme/assess-the-risks/data-breaches_en) — EU-oriented breach assessment and notification overview.
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.

---
title: "Retention and Deletion"
status: "Normative"
version: "1.1.0"
owner: "Privacy + Data Governance + SRE"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §5 P1 'Non-atomic file persistence'"
applies_to: "every byte uploaded, every model call output, every audit log, every backup, every region"
---

# Retention

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

## Policy objective

Retain each data class only as long as necessary for its documented purpose,
contract, security, legal obligation, or user-selected project lifecycle.
Deletion status must be truthful across primary stores, providers, caches,
derived indexes, exports, and backups.

The periods below are **product defaults**, not universal legal requirements.
An organization policy may shorten them. Longer periods require a documented
purpose, owner, legal/contract basis, and expiry.

## Default schedule

| Data class | Default retention | Trigger | Deletion objective |
|---|---:|---|---|
| Incomplete upload | 24 hours | upload abandoned | automatic purge |
| Rejected/quarantined file | 24 hours | rejection | purge; up to 7 days only under incident hold |
| Malware sample | no normal retention | confirmed threat | incident/legal hold with restricted vault |
| Raw source file | 90 days after last completed run using it | run completion | configurable shorter/keep-until-project-deletion |
| Processed source/segments | same as or shorter than raw source | source lifecycle | purge derived indexes too |
| Draft decision without activity | 180 days | last activity | notify before deletion when appropriate |
| Active project content | until user deletion or 365 days inactivity by default | project activity | policy configurable |
| Generated run artifacts | until project deletion or 365 days inactivity | run completion | preserve manifest until deletion completes |
| Raw model request/response diagnostic capture | off by default; max 7 days when enabled | diagnostic window | automatic restricted purge |
| Prompt/model metadata and hashes | life of referenced run + audit period | run deletion | retain non-content registry as required |
| Audit/security events | 365 days default | event time | longer when contract/security requires |
| Authentication/session logs | 90 days default | event time | minimize IP/device detail |
| Product analytics | 13 months default | event time | aggregated/de-identified earlier where possible |
| Support tickets | 24 months default | ticket close | attachments shorter when possible |
| Export object | 30 days default or explicit user choice | export ready | revoke share immediately; purge object |
| Share token | max 30 days | creation | revocable; shorter for sensitive projects |
| Deletion request evidence | 6 years default where appropriate | completion | no deleted content, only process evidence |
| Transactional backups | 35 days | backup creation | cryptographic/lifecycle expiration |
| Provider copies | provider-specific, max 30-day deletion objective | deletion command | confirm or document limitation |
| Human research evidence | policy-specific; no default enablement | import | requires separate method/privacy record |

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
## Retention classes

Every stored object has a retention class:

```text
EPHEMERAL
QUARANTINE
SOURCE_STANDARD
PROJECT_STANDARD
EXPORT_SHORT
SECURITY_LOG
AUDIT_LONG
DIAGNOSTIC_RESTRICTED
HUMAN_EVIDENCE_RESTRICTED
LEGAL_HOLD
```

Code references classes, not scattered day counts. Policy versions map classes
to active periods.

## Deletion request scope

Deletion resolves:

- organization/account;
- project;
- decision;
- source version;
- run and derived artifacts;
- export/share;
- support/diagnostic attachment;
- external provider record.

The user interface explains dependency effects before confirmation. Deleting a
source used by a completed run may require deleting or irreversibly redacting
the run; the product MUST not retain a misleading “reproducible” manifest after
required source content is gone without recording the limitation.

## Deletion workflow

```text
REQUESTED
→ IDENTITY + AUTHORIZATION VERIFIED
→ SCOPE RESOLVED
→ LEGAL / SECURITY HOLD CHECK
→ PRIMARY DATABASE PURGE OR CRYPTO-SHRED
→ OBJECT / CACHE / INDEX PURGE
→ PROVIDER DELETE REQUESTS
→ SHARE / EXPORT REVOCATION
→ BACKUP EXPIRATION SCHEDULED
→ COMPLETION VERIFIED
→ USER/CUSTOMER NOTIFIED
```

Deletion is idempotent and resumable. Each target returns a status and evidence
reference.

## Backup semantics

The interface MUST distinguish:

- removed from live systems;
- provider deletion requested/confirmed;
- unavailable to ordinary users;
- remaining only in encrypted backups until scheduled expiry;
- fully aged out.

Backups are not restored to production without reapplying post-backup deletions.
A deletion ledger is replayed during restore before service resumes.

## Legal and security holds

A hold record includes:

```text
hold_id
scope
authority
reason
approved_by
created_at
review_date
expiry
affected retention classes
access restrictions
```

Holds are not indefinite. They are reviewed, access-controlled, and released
through an audited process. Users receive the legally permitted explanation.

## Provider deletion

For every provider, the subprocessor record defines:

- delete endpoint or support process;
- identifier mapping;
- expected completion;
- backup behavior;
- verification evidence;
- limitations;
- escalation contact.

A product deletion cannot be reported complete when a known provider copy
remains outside the documented backup/contract window.

## De-identification and aggregation

Aggregation is not a substitute for deletion when data can be reasonably
relinked. A dataset is treated as personal/customer data until the privacy owner
approves a documented de-identification method and re-identification risk
review.

## Retention changes

Increasing retention is a material privacy change. It requires:

- purpose and necessity;
- risk assessment;
- notice/contract review;
- storage/security impact;
- provider compatibility;
- migration of existing records only when authorized;
- rollback/shortening plan.

## Retention acceptance

- every table, object prefix, cache, index, provider, log, and backup maps to a
  retention class;
- deletion works across a representative project with sources, runs, and
  exports;
- restore replays deletions;
- expired shares no longer authorize downloads;
- diagnostic capture purges automatically;
- no user copy falsely claims immediate backup erasure;
- hold creation/review/release is audited;
- provider deletion limitations are visible in the subprocessor record.

## References

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) - Privacy risk-management framework; version 1.1 remained a draft/coming-soon work item at the research cutoff.
- [EDPB - Data breaches and risk assessment](https://www.edpb.europa.eu/sme/assess-the-risks/data-breaches_en) - Privacy/accountability reference for handling personal-data incidents.

---

## Project-specific retention status (baseline `8b616dc7`)

The current code has a partial retention implementation. Gate 3
(canonical persistence + deletion state machine + provider
deletion tracking) is required to land before the doc is
satisfied in production. Items are marked **CURRENT**, **PARTIAL**,
or **TARGET**.

### Per-task retention — CURRENT

`TaskManager` retains completed and failed task records for 24 hours
in memory and in Redis
([`models/task.py:365-387`](../../backend/app/models/task.py:365)).
The hourly cleanup worker at
[`app/__init__.py:229`](../../backend/app/__init__.py:229) calls
`TaskManager().cleanup_old_tasks(max_age_hours=24)`. The 24h
window is hard-coded; it is not configurable per task type, per
workspace, or per jurisdiction. Configurable per-class retention
is **TARGET**.

### Project / simulation / report storage — PARTIAL

- `backend/uploads/projects/{project_id}/` retains project
  metadata, source files, and extracted text. No retention class
  is recorded.
- `backend/uploads/simulations/{simulation_id}/` retains state.json
  and the per-platform SQLite DBs. No retention class is recorded.
- `backend/uploads/reports/{report_id}/` retains the generated
  report. No retention class is recorded.

Reaching the contract requires a `retention_class` column on every
aggregate and a daily job that purges expired records. Tracked in
[`docs/exec-plans/02-tenancy-data-and-secure-ingestion.md`](../exec-plans/02-tenancy-data-and-secure-ingestion.md).

### Deletion — PARTIAL

`ProjectManager.delete_project`
([`models/project.py:227-244`](../../backend/app/models/project.py:227))
calls `shutil.rmtree` synchronously. There is no LEGAL_HOLD state,
no provider-deletion step, no backup aging record. The
deletion state machine in
[`docs/architecture/state-machines.md`](../architecture/state-machines.md)
("Deletion state machine") is **TARGET**.

### No backup or region tracking — TARGET

The current code does not declare a backup policy or a per-region
storage layout. Reaching the contract requires a documented
backup schedule, an aging record, and a per-region data-residency
policy. Gate 3.

### Subprocessor deletion limitations — CURRENT (declared)

The
[`SUBPROCESSORS.md`](SUBPROCESSORS.md)
doc records the configured subprocessors (LLM provider, Zep Cloud,
OASIS dependencies). Provider-side deletion windows and
limitations are surfaced per subprocessor. The current
implementation is honest about the limitations; reaching the
contract requires the retention UI to reflect the actual
subprocessor status (in-progress / confirmed / aged out) for
each user-initiated deletion.

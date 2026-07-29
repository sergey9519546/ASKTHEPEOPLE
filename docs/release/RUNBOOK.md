---
title: "Release Runbook"
status: "Operational"
version: "1.1.0"
owner: "Release Manager + SRE"
last_reviewed: "2026-07-29"
review_cycle: "Per release; at minimum quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
---

# Runbook

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

This runbook defines how to prepare, deploy, verify, monitor, and roll back an
ASKTHEPEOPLE release. It covers application code, database migrations, prompts,
models, validators, policy, content, export templates, infrastructure, and
provider configuration.

## Roles

- **Release Manager:** owns go/no-go and timeline.
- **Deployment Operator:** executes deployment.
- **Database Owner:** migration/restore authority.
- **AI Release Owner:** prompt/model/validator releases.
- **Security Lead:** security sign-off and kill switches.
- **Privacy Lead:** provider/data-flow/retention sign-off.
- **Accessibility Lead:** conformance evidence.
- **Product Truth Lead:** claims, content, and disclosure.
- **Scribe:** records actions, timestamps, and evidence.
- **Incident Commander:** assumed role if release becomes an incident.

## Release manifest

Before deployment, generate `release-manifest.json`:

```json
{
  "release_id": "rel-uuidv7",
  "git_commit": "sha",
  "build_digest": "sha256",
  "frontend_version": "semver",
  "backend_version": "semver",
  "database_migration_head": "id",
  "prompt_release_set": "id",
  "model_release_set": "id",
  "validator_bundle": "id",
  "use_policy_version": "id",
  "terminology_linter_version": "id",
  "export_template_versions": [],
  "infrastructure_revision": "id",
  "subprocessor_register_version": "id",
  "acceptance_record": "path",
  "rollback_release_id": "prior-approved-id"
}
```

## Standard release phases

```text
PLAN
→ FREEZE
→ BUILD + VERIFY
→ BACKUP + MIGRATION REHEARSAL
→ DEPLOY DARK
→ MIGRATE
→ INTERNAL SMOKE
→ CANARY
→ PROMOTE
→ POST-RELEASE VERIFY
→ CLOSE OR ROLLBACK
```

## 1. Plan

- Define scope and user-visible changes.
- Identify affected truth, policy, methodology, data, prompt/model, security,
  privacy, accessibility, and export contracts.
- Update ADRs/docs.
- Define canary cohort and rollback thresholds.
- Confirm provider quotas and status.
- Confirm no conflicting incident/change freeze.
- Create release record and evidence directory.

## 2. Freeze

Freeze:

- application commit;
- dependency lockfiles;
- container digest;
- infrastructure revision;
- database migration;
- prompt/model/validator release sets;
- policy and terminology bundles;
- export templates;
- design assets/copy.

No mutable provider alias is accepted after freeze. Emergency changes restart
the relevant verification.

## 3. Build and verify

Current repository baseline commands include:

```bash
npm run setup:all
npm run backend:test
npm run test
npm run build
```

The production repository MUST provide a single clean-environment command:

```bash
./scripts/release/verify
```

It runs:

- lockfile integrity;
- formatting/lint/type checks;
- backend/frontend tests;
- schema/OpenAPI checks;
- documentation/link/frontmatter checks;
- claim/terminology lint;
- security scans;
- AI eval release suite;
- accessibility automation;
- production build;
- container/IaC validation;
- SBOM and build attestation.

A missing target script is an implementation gap, not permission to skip steps.

## 4. Backup and migration rehearsal

- Create/verify current backup.
- Restore into an isolated environment.
- Apply migration.
- Run reconciliation queries and application smoke.
- Test rollback or forward-fix procedure.
- Reapply deletion ledger to restored data.
- Measure migration locks/duration.
- Confirm sufficient storage and connection capacity.
- Attach evidence.

Destructive migrations require expand/migrate/contract staging. Do not combine
irreversible data deletion with the initial application cutover.

## 5. Deploy dark

Deploy new services with user traffic disabled or feature flags off.

Verify:

- health and readiness;
- exact image/build digest;
- environment and secret references;
- database connectivity with correct role;
- workflow workers;
- parser sandbox network denial;
- object-store scopes;
- telemetry;
- kill switches;
- provider adapter dry checks without production content.

## 6. Database migration

- Announce start in release channel.
- Confirm current backup and restore evidence.
- Put affected writes in maintenance/read-only mode if required.
- Apply exact migration head.
- Run reconciliation and invariant queries.
- Confirm RLS policies and roles.
- Confirm no unexpected long locks.
- Record start/end and output.
- Abort/pivot according to migration plan on failure.

## 7. Internal smoke

Use dedicated synthetic fixtures only.

Required smoke path:

1. sign in and verify organization isolation;
2. create project and decision;
3. upload safe source;
4. approve condition and assumptions/profiles;
5. check/freeze configuration;
6. start run;
7. disconnect/reconnect event stream;
8. stop a test run;
9. complete a run;
10. inspect route map/list;
11. ask explanatory follow-up;
12. create research handoff;
13. export every enabled format;
14. verify visible/machine disclosure and manifest;
15. delete a disposable project and verify workflow.

Also test unauthorized and failure states.

## 8. Canary

Canary by organization and release set. Start with internal or explicitly
approved pilot workspaces.

Monitor:

- API/error/latency;
- workflow failure/retry/backlog;
- schema and validator failures;
- truth and terminology flags;
- source/injection/security signals;
- cost/token usage;
- provider errors;
- export failures;
- accessibility/frontend errors;
- support reports.

Minimum observation is based on sufficient representative workflows, not a
fixed clock. Do not promote because time elapsed without traffic.

## 9. Promotion

Release Manager confirms:

- canary volume representative;
- no rollback trigger;
- acceptance evidence complete;
- on-call staffed;
- provider capacity adequate;
- customer communication ready;
- rollback release still deployable.

Promote incrementally. Keep feature flags and old compatible workers until the
rollback window closes.

## 10. Post-release verification

Repeat critical smoke on production. Verify:

- exact release manifest;
- database head;
- prompt/model/validator releases;
- Truth Rail and copy;
- export disclosures;
- tenant isolation probes;
- event stream;
- dashboards and alerts;
- backup schedule;
- share/revocation;
- no unexpected egress/provider.

Review errors and user reports at the end of each promotion step.

## Rollback triggers

Immediate rollback or kill switch for:

- cross-tenant access;
- missing/misleading truth disclosure;
- fabricated source citation;
- critical use-policy escape;
- prompt-injection data/tool escape;
- signing/provenance compromise;
- severe auth/session failure;
- irreversible data corruption risk;
- unapproved model/provider fallback;
- sustained severe workflow or export failure;
- critical accessibility regression blocking workflow.

## Application rollback

1. Stop promotion and new runs.
2. Activate affected capability kill switch.
3. Notify release and incident roles.
4. Capture safe diagnostics and exact manifests.
5. Restore previous application/container/infrastructure release.
6. Restore prior prompt/model/validator/policy set.
7. Keep database at compatible expanded schema when possible.
8. Validate smoke and tenant isolation.
9. Re-enable read-only, then controlled writes.
10. Open incident/problem record and revoke affected exports if needed.

## Database rollback

Prefer forward-fix or compatibility rollback. A database restore is used only
under the approved plan because it can lose newer valid writes.

If restore is required:

- enter incident mode;
- stop writes/workflows;
- preserve current database for forensics;
- restore verified backup;
- replay deletion ledger;
- reconcile object/provider/workflow state;
- communicate RPO impact;
- validate all invariants before reopening.

## Prompt/model rollback

- set previous approved release set active;
- stop new invocations on candidate;
- decide treatment of in-flight attempts;
- quarantine candidate outputs;
- do not rewrite completed prior runs;
- revoke affected exports;
- run targeted eval and impact query;
- record exact provider/model behavior.

## Export-template rollback

Disable the format if truth/provenance cannot be guaranteed. Revoke affected
downloads/shares, restore prior template, regenerate only from canonical data,
and notify recipients when material.

## Emergency patch

An emergency patch may reduce scope but MUST still include:

- exact diff and incident reference;
- targeted tests;
- truth/tenant/security/privacy impact;
- rollback;
- named approvals;
- post-release full regression.

No emergency process waives the Product Truth Contract.

## Release communications

Before: affected users, change, maintenance, action required, limitations.

After: exact release, completed verification, known limitations, support route.

Rollback/incident: confirmed impact, affected scope, actions, corrected
artifacts, and next update. Never speculate or overstate.

## Closeout

A release closes only when:

- post-release verification passes;
- evidence bundle is complete;
- canary flags/old workers are resolved;
- migrations are documented;
- known risks have owners;
- support/runbooks are updated;
- release decision is signed;
- a retrospective is scheduled when warranted.

## Quarterly drills

Exercise:

- application rollback;
- prompt/model rollback;
- database restore with deletion replay;
- provider kill switch;
- source-ingestion shutdown;
- export revocation;
- cross-tenant incident;
- missing truth-disclosure incident.

## References

- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — Final incident-response recommendations aligned with CSF 2.0.
- [OpenTelemetry documentation](https://opentelemetry.io/docs/) — Vendor-neutral traces, metrics, and logs.
- [Temporal documentation](https://docs.temporal.io/) — Reference implementation for durable, resumable workflow orchestration; the architecture requires an interface rather than vendor lock-in.
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — Direct, indirect, and multimodal prompt-injection risks and defense-in-depth recommendations.


---

## Project-specific implementation status (baseline `8b616dc7`)

**Owner:** `askthepeople-release-operator` (Release Manager + SRE).

**Current state at the baseline:** the deployment today is a
single Flask process plus a Celery worker plus Redis. There is no
worker-drain procedure, no migration rehearsal procedure, no
quarterly incident-response drill, and no documented rollback
procedure that survives a multi-worker topology. The runbook is
TARGET in full and must be implemented as gates 2 and 4 land.

**Key file:line references:**

- Flask application factory and process registration:
  [`backend/app/__init__.py:25-330`](../../backend/app/__init__.py:25).
- Web request/response middleware (auth, security headers,
  traceback stripping, no body logging):
  [`backend/app/__init__.py:111-267`](../../backend/app/__init__.py:111).
- Health check with storage writability and revision id:
  [`backend/app/__init__.py:290-307`](../../backend/app/__init__.py:290).
- In-process cleanup worker (audit pattern; to be removed):
  [`backend/app/__init__.py:229-239`](../../backend/app/__init__.py:229).
- Simulation process cleanup hook (to be replaced with worker drain):
  [`backend/app/__init__.py:106-109`](../../backend/app/__init__.py:106).
- Celery app and the single registered task:
  [`backend/app/celery_app.py:21`](../../backend/app/celery_app.py:21),
  [`backend/app/tasks/simulation_tasks.py:16`](../../backend/app/tasks/simulation_tasks.py:16).

**Required additions to the runbook (gate 2 + gate 4):**

- Worker drain order and timeout. Drain Celery workers, drain
  the API replicas, drain the reverse proxy, then upgrade.
- Migration rehearsal procedure (rehearse against a copy of
  the database, prove counts, hashes, relationships, and
  authorization).
- Backup restoration procedure (per ADR-0012).
- Quarterly incident-response drill per
  [`docs/security/INCIDENT_RESPONSE.md`](../security/INCIDENT_RESPONSE.md).
- Rollback procedure per attempt type, including
  per-attempt immutability under the canonical persistence
  layer.
- Provider-degradation behavior per
  [`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](../architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md).
- Observability runbook (which metric, which trace, which
  log; how to read a degraded-state trace; what counts as
  "the system is operating normally" vs "the system is
  operating with reduced service").

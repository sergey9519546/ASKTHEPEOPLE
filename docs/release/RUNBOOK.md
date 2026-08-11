---
title: "Release Runbook"
status: "Operational"
version: "1.2.0"
owner: "Release Manager + SRE"
last_reviewed: "2026-08-11"
review_cycle: "Per release; at minimum quarterly"
research_cutoff: "2026-08-11"
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

### Single-host demo topology — TRANSITION / NOT RELEASE EVIDENCE

The checked-in Compose file now starts `redis`, `askthepeople`, `worker`, and
`beat` on one host. Web, worker, and beat mount the same
`/app/backend/uploads` directory because project, simulation, and report
records are still filesystem-backed. This is a bounded demo topology, not the
TARGET canonical-persistence architecture and not production release evidence.

#### Current zero-recurring-host-bill decision

This is a hosting-cost decision, not an end-to-end zero-cost guarantee. The
experience calls external model, memory, and search providers. Their account
tier, quotas, billing status, and availability are outside this repository,
and the application does not yet have a durable token/credit admission ledger.
Before every connected demo, the operator MUST verify each provider dashboard,
confirm that no paid tier or automatic billing is enabled, record the current
limits, and stop after the first bounded fictional-data run if any limit or
billing state is uncertain.

The transition template currently selects Groq's OpenAI-compatible endpoint
with `llama-3.1-8b-instant` for routine work and `openai/gpt-oss-120b` for the
boost role. This is an unverified provider/model candidate: the mocks prove the
OpenAI-compatible wiring, but a protected post-rotation fictional graph and
report smoke must prove JSON-mode and CAMEL behavior before the pair is called
working. Groq publishes Free-plan rate limits, but says exact organization
limits are visible in the account and may differ; see
[Groq rate limits](https://console.groq.com/docs/rate-limits). Zep remains a
mandatory dependency for graph-backed experiences. Zep currently documents a
Free plan with 10,000 monthly credits, no rollover, and no automatic top-up,
with variable rate limits and changeable feature availability; see
[Zep pricing](https://www.getzep.com/pricing/). These are current external
offers, not release guarantees. Do not upgrade either account for this path.

For an independently hosted, continuously reachable demo, the preferred
zero-recurring-cloud-bill candidate is **one OCI Ampere A1 Always Free VM** in
the account's home region, using the complete Compose topology on that single
machine. Oracle currently documents 1,500 A1 OCPU-hours and 9,000 GB-hours per
month, equivalent to 2 OCPUs and 12 GB RAM for an Always Free tenancy, plus up
to 200 GB of Always Free block storage. Capacity is not guaranteed, and Oracle
may reclaim a VM whose CPU, network, and A1 memory all remain below the
documented thresholds during a seven-day period. Most new accounts also need a
phone and credit-card verification; Oracle documents a temporary authorization
and states that the card is not charged unless the account is upgraded. See
Oracle's [Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
and [Always Free resource limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

The pinned Python, Node, and `uv` base-image indexes were inspected on
2026-08-11 and each advertises `linux/arm64`. That is compatibility evidence,
not a successful application image build. Before selecting A1, build both
Dockerfiles natively on A1 or with `--platform linux/arm64`, run the complete
offline verification suite, and execute the fictional-data smoke below. Until
that succeeds, A1 remains a candidate rather than a proven deployment.

If OCI capacity or payment verification is unacceptable, the no-cloud-account
fallback is the same Compose topology on an operator-controlled always-on
computer. A Cloudflare Quick Tunnel can provide a temporary random HTTPS URL
without a Cloudflare account or domain, but Cloudflare positions it for demos
and the URL changes when the process restarts. A stable named tunnel requires
a Cloudflare account and a domain on Cloudflare. Cloudflare Tunnel uses an
outbound-only connection, so the origin port can remain loopback-bound. See
Cloudflare's [Tunnel overview](https://developers.cloudflare.com/tunnel/) and
[setup prerequisites](https://developers.cloudflare.com/tunnel/setup/).

The deployment checkout and `.transition-data` directory MUST live on a local,
non-synchronized filesystem. Do not run this topology from OneDrive, Dropbox,
NFS, SMB, or another sync/network mount: SQLite locking and atomic file updates
are not deployment evidence there, and sync software can copy demo artifacts
outside the intended host boundary. OCI block storage formatted with a local
Linux filesystem is the preferred candidate.

Do not split this workload across free serverless functions or independent
free web/worker services. The current Celery jobs exceed request lifetimes and
the project, simulation, and report records still require one shared
filesystem. A free service matrix does not repair those semantic constraints.

Before using it, the operator MUST:

- close or explicitly preserve every active security NO-GO; currently the
  exposed provider credentials MUST be revoked and rotated first;
- verify Groq and Zep still show the intended free account tiers and current
  quotas, and verify that no paid upgrade, payment-triggered auto top-up, or
  other billable provider path is enabled;
- use fictional/non-sensitive demo inputs only;
- set strong `SECRET_KEY` and `APP_TOKEN`, keep runtime settings disabled, and
  expose the loopback-bound web port only through a TLS tunnel while retaining
  the application's required bearer authentication;
- keep all four services and the uploads bind mount on the same host;
- retain a recoverable backup of `.transition-data/uploads` before upgrades.

On the candidate Linux host, install Git, Python 3, Docker Engine, the Docker
Compose plugin, and `cloudflared` only from their official distribution
instructions. Do not pipe an unreviewed remote script into a privileged shell.
Before any repository mutation, all of these checks MUST succeed:

```bash
git --version
python3 --version
docker --version
docker compose version
cloudflared version
```

Docker Compose 2.24 or newer is required so the long-form
`env_file.required` guard is enforced. The host firewall/security list must
allow the operator's SSH path but must not expose TCP 5001, 6379, or 8080;
Cloudflare Tunnel is outbound-only. Validate and start the topology from the
repository root:

```bash
set -euo pipefail
umask 077
test ! -e .env.transition
test ! -e .env.transition.build
install -m 600 .env.transition.example .env.transition
install -m 600 .env.transition.build.example .env.transition.build
printf 'BUILD_REVISION=%s\n' "$(git rev-parse HEAD)" > .env.transition.build
# Fill every required blank; boost/search keys are explicitly optional.
python3 backend/scripts/validate_transition_build_identity.py \
  --build-env .env.transition.build
python3 backend/scripts/prepare_transition_storage.py
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build config --quiet
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build up --build -d
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build ps
```

Compose interpolation intentionally uses `.env.transition.build`, which carries
only the exact source revision. Service secrets come from the distinct
mode-0600 `.env.transition`; neither path uses the repository's developer
`.env`. Missing required credentials must make startup fail closed. Do not work around
that guard by copying historical values or by placing `BUILD_REVISION` in the
runtime secret file. The identity preflight MUST see a clean tracked, staged,
and untracked worktree. This prevents a dirty Docker context from claiming the
revision of its clean `HEAD`; commit or remove intended changes before building.
The storage preflight claims the dedicated ignored `.transition-data/uploads`
directory only when it is empty, then records a fixed marker so restarts can
reuse the same demo state. It refuses a nonempty unowned or symlinked path,
which prevents normal development data in `backend/uploads` from being mixed
into a tunneled demo.

The Compose profile also bounds each container's memory, CPU share, PID count,
and local JSON logs for the documented two-OCPU/twelve-GB candidate. Redis uses
a 512-MB `noeviction` ceiling so resource exhaustion fails requests instead of
silently evicting broker or task state, and the worker runs one task process.
These are demo safety limits, not capacity evidence. The required native ARM
smoke must record `docker system df --verbose` before setting a minimum disk
threshold. Until then, keep free space greater than both 5 GB and the measured
total Docker disk use (including multi-stage build cache) plus Redis AOF, the
transition store, one full backup, and an operating-system reserve; stop the
demo when either bound is violated.

Then verify `/health`, `/health/readiness`, worker logs, beat logs, one queued
fictional graph job, and one queued fictional report job. Stop without deleting
the restart-persistent Redis volume or transition directory:

```bash
set -euo pipefail
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build down
```

The Redis volume is restart convenience, not canonical recovery evidence.
Before a backup, close the tunnel, stop web and beat so no new work can enter,
verify Celery has no active, reserved, or scheduled task, then stop the worker. Create a
mode-0600 archive of `.transition-data/uploads` in the ignored
`.transition-backups` directory and restore it into an isolated temporary
directory; `prepare_transition_storage.py --verify-store <restored/uploads>`
must pass before the backup is accepted. Redis may be discarded only after
this quiescent drain; queued or in-flight work is not recoverable from the
uploads archive.

```bash
set -euo pipefail
drain_started=0
recover_worker_after_failed_drain() {
  drain_status="$1"
  trap - EXIT HUP INT TERM
  if [ "$drain_started" -eq 1 ]; then
    env -u BUILD_REVISION docker compose \
      --env-file .env.transition.build restart worker >/dev/null 2>&1 || true
  fi
  exit "$drain_status"
}
trap 'recover_worker_after_failed_drain "$?"' EXIT
trap 'recover_worker_after_failed_drain 129' HUP
trap 'recover_worker_after_failed_drain 130' INT
trap 'recover_worker_after_failed_drain 143' TERM
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build stop beat askthepeople
drain_started=1
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build exec -T worker \
  python -m scripts.assert_celery_quiescent
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build stop worker
drain_started=0
trap - EXIT HUP INT TERM
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build run --rm --no-deps worker \
  python -m scripts.assert_celery_quiescent --broker-only
install -d -m 700 .transition-backups
sudo python3 backend/scripts/transition_storage_manifest.py \
  --root .transition-data/uploads --write
backup=".transition-backups/uploads-$(date -u +%Y%m%dT%H%M%SZ).tgz"
sudo tar --numeric-owner -C .transition-data -czf "$backup" uploads
sudo chown "$(id -u):$(id -g)" "$backup"
chmod 600 "$backup"
sha256sum "$backup" > "$backup.sha256"
chmod 600 "$backup.sha256"
sha256sum --check "$backup.sha256"
restore_dir="$(mktemp -d)"
trap 'rm -rf -- "$restore_dir"' EXIT HUP INT TERM
tar --no-same-owner -xzf "$backup" -C "$restore_dir"
python3 backend/scripts/prepare_transition_storage.py \
  --verify-store "$restore_dir/uploads"
python3 backend/scripts/transition_storage_manifest.py \
  --root "$restore_dir/uploads" --verify
rm -rf -- "$restore_dir"
trap - EXIT HUP INT TERM
```

For a no-account public demo, start a Cloudflare Quick Tunnel in a separate
terminal with `cloudflared tunnel --url http://127.0.0.1:5001`. It prints a
temporary random HTTPS URL. Set that exact origin and host in the mode-0600
`.env.transition`, recreate the Compose services, and repeat the local and
public health checks before sharing the URL. Quick Tunnels are testing/demo
only, have no edge access policy, and change URL on restart; `APP_TOKEN`
remains mandatory. A stable named tunnel requires a Cloudflare account and a
domain and is outside the no-account path.

MUST NOT use this topology across multiple hosts or independent platform
volumes. Railway-style split services remain blocked until project,
simulation, report, task, and artifact records are canonical across processes,
the Alembic/runtime schema conflict is resolved, and web/worker/beat are
deployed and verified at one immutable revision. The CI caller therefore keeps
the legacy Railway production job dark unless the repository variable
`RAILWAY_PRODUCTION_DEPLOYMENT_ENABLED` is explicitly set to `true`. Do not set
that variable while these blockers remain. Railway's own GitHub integration
can autodeploy independently of Actions, so `railway.toml` also runs the
fail-closed `block_legacy_railway_deploy.py` pre-deploy sentinel. The operator
MUST disable automatic deployments for every connected Railway service in the
Railway dashboard. The Vercel manifest, Render blueprint, and all Procfile
process types are also fail-closed in the repository, but an existing provider
dashboard can retain an older deployment or override repository configuration.
The operator MUST disable connected Vercel and Render deployments as well and
verify that no legacy public origin remains. Do not remove any sentinel until
the canonical persistence, migration, and revision-atomic topology gates have
passed review.

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

### ZEP readiness diagnostic — CURRENT

Railway and container health checks remain on provider-independent `/health`.
An external provider outage MUST NOT restart the application or erase access to
canonical recovery records. Promotion separately requires the web-scoped
`/health/readiness` response to report that the ZEP-backed web capability is
available. The probe performs only the bounded project-metadata read in
[`services/zep_dependency_status.py:178-192`](../../backend/app/services/zep_dependency_status.py:178);
it discards the response and never reads, creates, changes, or deletes a graph.

The production workflow performs thirty attempts, ten seconds apart, with a
five-second HTTP ceiling per attempt
([`.github/workflows/deploy.yml:394-435`](../../.github/workflows/deploy.yml:394)).
An operator can reproduce the response check without handling the ZEP key:

```bash
readiness_file="$(mktemp)"
trap 'rm -f "$readiness_file"' EXIT
readiness_http="$(curl --silent --show-error --max-time 5 \
  --output "$readiness_file" --write-out '%{http_code}' \
  "${PRODUCTION_URL}/health/readiness" || true)"
readiness_reason="$(jq -r '.dependencies.zep.reason // "unreported"' \
  "$readiness_file" 2>/dev/null || echo unreported)"
test "$readiness_http" = "200"
: "${TESTED_SHA:?set TESTED_SHA to the revision that passed pre-deploy checks}"
jq -e --arg tested_sha "$TESTED_SHA" '.status == "ready" and
  .scope == "web" and
  .revision == $tested_sha and
  .components.zep == "ok" and
  .dependencies.zep.status == "ok" and
  .dependencies.zep.reason == "available" and
  .dependencies.zep.stale == false and
  .capabilities.web_graph_backed == "ready"' \
  "$readiness_file" >/dev/null
```

Only the bounded `readiness_reason` value may enter release logs. Do not print
the response body, provider exception, project metadata, endpoint URL, or any
credential. This public web check proves the deployed web environment only;
it does not prove that a separately configured Celery worker can reach ZEP.
The supported container worker performs a no-network fail-closed configuration
check in both the wrapper and the Celery worker bootstep before broker
connection. Procfile process types are intentionally deployment blockers and
are not supported worker entry points
([`utils/worker_startup.py:56-88`](../../backend/app/utils/worker_startup.py:56),
[`celery_app.py:84-145`](../../backend/app/celery_app.py:84),
[`scripts/worker_wrapper.sh:6-57`](../../backend/scripts/worker_wrapper.sh:6)).
The check requires the ZEP and primary LLM keys, explicit non-memory Redis
coordination and broker/result URLs, and an immutable runtime revision. It
validates names, presence, URL schemes, and revision shape only; it performs no
provider or dependency I/O and is not worker-provider readiness.

### Worker availability attestation — CURRENT

The worker service's `/health` is intentionally stricter than web liveness.
It is an availability attestation used to keep a worker out of service until
Celery's consumer is actually ready. The wrapper clears any earlier marker,
starts Celery, binds the health process to that Celery PID, and cleans up on
exit. Celery writes the first marker on `worker_ready`, refreshes it on worker
heartbeats, and removes it during shutdown
([`scripts/worker_wrapper.sh:6-57`](../../backend/scripts/worker_wrapper.sh:6),
[`celery_app.py:84-130`](../../backend/app/celery_app.py:84)).

Treat HTTP 200 as valid only when the body has this closed, privacy-safe shape:

```json
{
  "status": "ok",
  "service": "celery-worker",
  "revision": "<exact 40- or 64-character immutable revision>"
}
```

The endpoint returns 503 with the same three fields and `status` set to
`unavailable` before `worker_ready`, after shutdown, when the Celery parent is
gone, when the marker is over ten seconds old, or when process/revision
identity does not match. It sends `Cache-Control: no-store` and suppresses the
default Python HTTP server fingerprint headers
([`scripts/worker_health.py:61-151`](../../backend/scripts/worker_health.py:61)).
It never returns key presence, URL, PID, marker age, exception text, or provider
metadata. Do not weaken this endpoint to an unconditional process-only 200.

This worker response proves local Celery readiness at the reported revision.
It does not prove Redis durability, successful execution of a graph/report
task, or live reachability of ZEP or the LLM provider. Promotion still requires
the queued fictional job checks and, after rotation evidence closes the
security gate, the protected ZEP canary below.

### Protected ZEP live canary — TRANSITION

The operator-only canary is implemented, but live execution remains blocked
until the public-credential incident is contained and independently verified.
It has no HTTP route. The CLI dispatches a closed evidence document to the
deployed Celery worker; the provider credential remains worker-owned
([`tasks/zep_canary_tasks.py:10-23`](../../backend/app/tasks/zep_canary_tasks.py:10),
[`scripts/zep_live_canary.py:24-169`](../../backend/scripts/zep_live_canary.py:24)).

Before enabling it:

1. Revoke every potentially exposed ZEP credential and review provider usage
   through the later web/worker restart. The broader release remains blocked
   until the exposed primary-LLM, boost-LLM, and search credentials are also
   revoked, rotated, usage-reviewed, and independently verified.
2. Install one fresh replacement in both web and worker services, restart both,
   and record the exact tested deployment revision.
3. Have a different security reviewer verify the restricted evidence. Never
   place a credential value, fingerprint, prefix, suffix, or hash in evidence.
4. Set `ZEP_LIVE_CANARY_ENABLED=true` on the worker for this bounded operation,
   then restart that worker. Runtime identity comes from the root-owned
   `/usr/share/askthepeople/build-revision` baked into the reviewed image.
   Platform/runtime revision variables may only corroborate that file; a
   missing, malformed, or mismatched value fails closed
   ([`utils/build_revision.py`](../../backend/app/utils/build_revision.py)).
   `ZEP_CANARY_DEPLOYMENT_REVISION=<exact-tested-sha>` MAY be set only as an
   additional expected-revision guard and MUST equal both the runtime identity
   and the evidence revision. Do not add canary controls to a public workflow
   or committed environment file.

Create the evidence file in restricted storage. The schema is closed; replace
every angle-bracket value before use, and do not commit the file:

```json
{
  "schema_version": "zep-rotation-evidence/v1",
  "incident_id": "public-historical-provider-credentials-2026-07-29",
  "provider": "zep-cloud",
  "old_credentials_revoked": true,
  "old_credentials_revoked_at": "<UTC timestamp ending in Z>",
  "replacement_issued": true,
  "replacement_issued_at": "<UTC timestamp ending in Z>",
  "web_updated": true,
  "web_updated_at": "<UTC timestamp ending in Z>",
  "worker_updated": true,
  "worker_updated_at": "<UTC timestamp ending in Z>",
  "web_restarted": true,
  "web_restarted_at": "<UTC timestamp ending in Z>",
  "worker_restarted": true,
  "worker_restarted_at": "<UTC timestamp ending in Z>",
  "provider_usage_reviewed_through": "<UTC timestamp ending in Z>",
  "rotated_by": "<operator-id>",
  "independently_verified_by": "<different-reviewer-id>",
  "verified_at": "<UTC timestamp ending in Z>",
  "deployment_revision": "<exact-tested-sha>",
  "restricted_evidence_ref": "incident://security/2026-07-29/rotation"
}
```

From an authenticated deployment shell with the production broker
configuration—but without copying the ZEP key—run from `backend/`:

```bash
python scripts/zep_live_canary.py \
  --evidence-file <restricted-evidence-path> \
  --execute \
  --wait-seconds 240
```

The worker creates one fictional graph, registers and reads back the exact
PascalCase ontology, submits one fictional episode, verifies its nodes, edge,
and episode provenance, then owner-checks and deletes the graph
([`services/zep_live_canary.py:667-1154`](../../backend/app/services/zep_live_canary.py:667)).
Interpret the exit code strictly:

- `0`: proof passed and deletion was confirmed;
- `2`: proof failed, but absence/deletion was confirmed; do not promote;
- `3`: cleanup is pending or not durably recorded; stop, preserve the journal,
  invoke incident response, and do not start another canary;
- `4`: rotation evidence was rejected before provider access;
- `5`: execution, configuration, revision, journal, lock, or dispatch was
  rejected before provider access.

After any terminal result, set `ZEP_LIVE_CANARY_ENABLED=false` (or remove it)
and restart the worker. A passing fictional canary proves the tested technical
seam only; it does not authorize customer content or supersede the ZEP
contract, region, retention, subprocessor, and deletion review.

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
12. verify research-handoff construction is unavailable unless the release
    manifest explicitly contains its separately approved capability;
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

## Canonical identity and workspace cutover procedure

This procedure is **TARGET**. No canonical deployment host is currently
authorized; Railway, Render, Vercel, Sites, and other split or automatic
production deployments remain disabled until the release gates close.
The canonical organization/workspace foundation may first ship dark or in
read-only shadow mode. It does not make legacy product routes multi-tenant.

### Preflight and ownership

1. Freeze the exact application/build revision, expected Alembic head,
   unmodified legacy-baseline hash, checked-in schema fingerprint, adoption
   tool version, and `epistemic-ledger/v2` validator version in one release
   manifest.
2. Require PostgreSQL 16 or later, TLS, private networking, encrypted backups,
   PITR consistent with the declared RPO/RTO, and bounded connection,
   statement, and lock timeouts.
3. Provision separate non-login owner, migrator, application, temporary
   backfill, and read-only roles. Web and ordinary workers receive only the
   RLS-subject application URL. Migration/backfill credentials are available
   only to a manual operator job and are absent from web/worker environments.
4. Prove the application role is not owner, superuser, `BYPASSRLS`,
   `CREATEDB`, or `CREATEROLE`; prove forced policies and connection-pool
   scope reset before any non-legacy mode.
5. Create a backup, restore it in isolation, verify the database identity and
   schema fingerprint, and attach restore evidence before migration.

### Fingerprint, adopt, and backfill

1. Acquire the migration advisory lock and require exactly one allowed
   Alembic starting state.
2. Recalculate the managed legacy-schema canonical JSON and SHA-256. On any
   missing, extra, renamed, type-changed, constraint-changed, or index-changed
   object, stop without stamping or migrating.
3. Use only one approved path: clean bootstrap, exact stamped baseline, or an
   explicit exact unversioned adoption with the expected fingerprint supplied
   by the operator. Never edit or reinterpret the baseline migration.
4. Apply the additive `core` child revision manually. Application startup
   never upgrades the schema.
5. Run the operator mapping in mandatory dry-run mode. Require the same input
   manifest hash and legacy-root fingerprint for apply. Organization,
   workspace, memberships, and project bindings are explicit; never infer
   tenant ownership from filesystem layout, project IDs, aliases, email
   domains, or token claims.
6. Preserve accepted legacy workspace/project public aliases while creating
   independent UUIDv7 physical IDs. Reconcile counts, alias sets,
   relationships, file/manifest hashes, and evidence hashes. A collision,
   ambiguity, or changed rerun blocks the batch.
7. Revoke the temporary backfill role and archive the encrypted operator
   manifest under the approved retention class after final reconciliation.

### Shadow, cutover, and smoke

1. Deploy dark with core, source-ingestion, durable-run, and path flags off.
2. Enable `SHADOW` reads only. Legacy remains the response and sole write
   authority; the comparison code performs zero writes and records only
   bounded aggregate mismatch codes/counts.
3. Require zero unexplained mismatch, repeat restore/RLS/role checks, then
   enter maintenance and disable all legacy identity/project writers.
4. Fingerprint and reconcile again. Record a `PREPARED` cutover with exact
   evidence and build hashes before selecting `CANONICAL`.
5. In `CANONICAL`, read and write core only. Missing rows, RLS denial,
   timeout, unavailable PostgreSQL, or pool error returns a bounded failure;
   no request touches SQLite, filesystem JSON, Redis state, or legacy
   identity storage as fallback.
6. Run OIDC signature/issuer/audience/expiry, inactive-membership,
   cross-organization, cross-workspace, missing-scope, pooled-connection,
   application-role, and no-fallback smoke tests. Activate the cutover record
   only after all pass.
7. Keep the legacy snapshot read-only as bounded evidence. Core tenancy does
   not remove the single-web-worker warning or make the process-local legacy
   simulation runner horizontally safe.

### Source, run, path, and brief admission

- Source ingestion remains disabled unless the complete TXT-only quarantine,
  scan, strict parse, review, deletion, RLS, object-store, and worker-isolation
  evidence exists. `FAILED` operational states and `REJECTED` policy states
  are never interchanged. Deletion continues from every non-deleted source
  state during rollback.
- Durable run creation remains disabled until organization/workspace
  authorization, canonical reviewed inputs, exact releases, leases, fences,
  transactional idempotency/outbox, object artifacts, reconnect, stop, and
  worker-kill recovery evidence pass.
- Path persistence/review remains disabled until first-class semantic IDs and
  `epistemic-ledger/v2` role resolution pass. Brief generation requires the
  exact current approved path-set ID/hash and review ID/hash while the run is
  `VALIDATING_OUTPUT`; any mismatch, stop, failure, or revision relocks it.
- Later exact-two comparison, changed-condition injection, external evidence,
  research-handoff construction, and decision-owner conclusion workflows stay
  unavailable. This release must not advertise placeholders for them.

### Rollback boundary

Before the first canonical application write, an approved rollback record may
return reads to the verified read-only legacy snapshot. After that write,
never route back to legacy or replay writes ad hoc: keep core canonical and
deploy a compatible application rollback or forward fix. A database outage in
canonical mode is an availability incident, not permission to fall back.
Rollback disables new source/run/path work but preserves acknowledged reads,
stop/recovery, deletion obligations, immutable reviews/events, and truthful
partial states.

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

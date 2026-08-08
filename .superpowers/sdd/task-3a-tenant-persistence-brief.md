# Task 3a brief — tenant identity and canonical core persistence foundation

Read this first. This brief is conceptually inserted after Task 3 (the
server-owned workspace manifest) and before Tasks 4–6 (source review, durable
runs, and first-class paths). It does not amend the tracked master plan. The
implementation must remain a separate, reviewable dependency slice.

## 1. Status and decision

**Specification status: PROPOSED / REVISION REQUIRED until Checkpoint 3A-0 is
approved by the architecture, security, privacy, persistence, and release
owners.**

The CURRENT application cannot safely persist source, run, path, or brief
records because it has no authenticated user-to-organization-to-workspace
boundary, no canonical PostgreSQL lineage, and no query-level tenant
isolation. Task 3's `workspace_manifest.json` supplies a stable server-owned
public alias, but it is not authentication, membership, authorization, RLS, or
a canonical database row.

Task 3a builds only the shared foundation needed by those later aggregates:

```text
OIDC subject -> user -> organization membership -> workspace membership
             -> immutable ActorContext -> scoped repository -> core.* rows
```

It also provides a rehearsable adoption path from the CURRENT filesystem and
the existing `384c98f88d53` Alembic baseline. It does not make the whole
application multi-tenant. Legacy routes remain CURRENT/PARTIAL until each is
moved behind an ActorContext and a scoped canonical repository.

## 2. Authority and state legend

The authority order in `AGENTS.md` applies. In particular:

- `docs/architecture/index.md` controls claims about CURRENT code;
- `docs/architecture/data-model.md` controls UUIDv7, organization scope,
  optimistic concurrency, privacy metadata, and immutable history;
- `docs/architecture/adr/ADR-0009-multi-tenant-isolation.md` controls
  application authorization, RLS, object/job/cache scoping, and negative
  cross-tenant tests;
- `docs/architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md`
  controls incremental adapters, flags, evidence, and removal of legacy paths;
- `docs/architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md`
  controls PostgreSQL authority, operational roles, migrations, and the ban on
  SQLite/filesystem fallback after canonical cutover;
- `docs/privacy/DATA_MAP.md` and `docs/privacy/RETENTION.md` control identity,
  membership, audit, retention, deletion, and telemetry;
- `docs/security/THREAT_MODEL.md` controls cross-tenant and authentication
  threats;
- `docs/release/ACCEPTANCE.md` and `docs/release/RUNBOOK.md` control migration,
  backup, restore, canary, rollback, and release claims.

This brief uses the required terms exactly:

- **CURRENT** — observable in the repository now;
- **PARTIAL** — present but materially deficient;
- **TARGET** — approved production behavior not yet reached;
- **TRANSITION** — bounded compatibility work with an explicit exit gate.

Where this brief conflicts with a higher-authority document, implementation
stops at Checkpoint 3A-0 until the owning stewards resolve the conflict.

## 3. Bounded deliverable

### Included

1. a normative `organization -> workspace -> project` relationship;
2. UUIDv7 physical identifiers and immutable server-issued public aliases;
3. the `core` PostgreSQL schema and only its foundation tables;
4. organization and workspace memberships;
5. a closed role-to-capability policy and immutable `ActorContext`;
6. OIDC authentication and an explicit local-development legacy adapter;
7. forced RLS, bootstrap resolver functions, and scoped repositories;
8. schema fingerprinting and explicit adoption of the existing Alembic
   baseline without editing it;
9. an operator-owned identity/project backfill with reconciliation evidence;
10. legacy-primary shadow comparison, an explicit cutover record, and
    canonical-only behavior after cutover;
11. fail-closed configuration, Railway-oriented deployment steps, backup and
    restore evidence, and privacy-safe observability;
12. strict one-test-at-a-time RED/GREEN execution and independent review at
    every checkpoint.

### Explicitly excluded

Do not add or migrate any of the following in Task 3a:

- sources, source versions, source segments, extraction candidates, source
  review, quarantine, scanners, parsers, or object storage;
- decisions or decision versions;
- run configs, runs, attempts, stages, events, workers, leases, or fencing;
- possible paths, path steps, considerations, validation questions, semantic
  comparison, reports, exports, decision briefs, or handoffs;
- graph/vector records, model/provider artifacts, prompts, or simulations;
- frontend screens or user-visible tenancy administration;
- invitations, SCIM, organization-domain discovery, just-in-time membership,
  billing, or enterprise single-tenant deployment automation.

No route may create an organization, workspace, membership, or project in this
task. Provisioning and adoption are operator commands. This keeps Task 3a from
quietly becoming an account-management product.

## 4. CURRENT audit ledger

Implementation starts from these facts, not from TARGET diagrams:

| Area | CURRENT fact | Required consequence |
|---|---|---|
| Workspace alias | `backend/app/application/decision_workspace_service.py` stores `workspace_<32 lowercase hex>` beside a legacy project and labels storage `TRANSITION`. | Preserve that alias exactly during adoption; never treat the file as membership or authorization evidence. |
| Project identity | `backend/app/models/project.py:187` creates `proj_<12 lowercase hex>` and filesystem directories are keyed by it. | Preserve every accepted legacy project ID as an immutable public alias; use an independent UUIDv7 physical key. |
| Authentication | `backend/app/__init__.py:222-237` compares every API bearer token with one application-wide `APP_TOKEN`. | Keep this only as an explicit local-development adapter. It cannot authorize a production tenant. |
| Database startup | `backend/app/__init__.py:159-194` initializes SQLAlchemy and permits a filesystem/SQLite path when PostgreSQL is absent. | Core canonical mode requires PostgreSQL and fails closed. No canonical read may fall back to SQLite or the filesystem. |
| Metadata initialization | `backend/app/db/__init__.py:25-27` invokes `Base.metadata.create_all`. | Core schema changes are Alembic-only. Production startup never creates or upgrades core tables. |
| ORM disagreement | `backend/app/db/schema.py:8-62` declares UUID tables that materially disagree with the integer-keyed public tables in the existing migration. | Do not autogenerate against this metadata. Put reviewed models in a separate `core` schema and use a manual migration. |
| Migration baseline | `backend/migrations/versions/384c98f88d53_initial_schema.py:20-143` creates legacy public tables. | Never edit, reorder, or reinterpret `384c98f88d53`; fingerprint and explicitly adopt an exact existing schema, then add a child revision. |
| Tenancy | CURRENT project, task, simulation, report, filesystem, cache, and graph records do not carry a verified organization/workspace scope. | Task 3a is a dark foundation, not proof that those data paths are tenant isolated. |
| Deployment | Railway is canonical; `Procfile` runs one web process, a general Celery worker, and beat. `railway.toml` uses Docker discovery. | Add PostgreSQL and migration/operator responsibilities without claiming horizontal-scale or worker isolation is complete. |

Any line movement discovered during implementation must be recorded with fresh
`file:line` evidence in the implementation report.

## 5. Normative relationship contract — resolved; named approval open

Authority commit `ce132a5` amended the normative data model, ADR-0009,
ADR-0012, privacy map, runbook, and release acceptance. It resolved the earlier
incomplete organization/workspace statements by binding this exact model. No
normative tenancy-relationship conflict remains:

```text
ORGANIZATION 1 --- * WORKSPACE 1 --- * PROJECT
       |                 |
       *                 *
ORGANIZATION_MEMBERSHIP  WORKSPACE_MEMBERSHIP
       *                 *
       +------- USER ----+
```

1. **Organization** is the tenant/legal-policy boundary.
2. **Workspace** is the collaboration, authorization, retention-policy, and
   operational isolation boundary inside one organization.
3. **Project** belongs to exactly one workspace and therefore exactly one
   organization. A project never moves between organizations. A future
   workspace move requires a separately reviewed migration workflow.
4. Every workspace-owned row stores both physical `organization_id` and
   `workspace_id`. A composite foreign key proves they describe the same
   relationship; the duplicated organization key is deliberate defense in
   depth and query/index support.
5. A user may belong to an organization without access to every workspace.
   Active workspace membership also requires an active membership in the same
   organization.
6. The Task 3 Decision Workspace remains the product projection for one
   project. Its `workspace_id` is adopted as the canonical workspace public
   alias for legacy data. Existing projects therefore begin as one project per
   adopted workspace. The canonical model permits multiple new projects per
   workspace after a later, authorized project-command slice exists.
7. The Task 3 manifest never supplies `organization_id`, user identity, role,
   or capability. The operator mapping and authenticated membership establish
   those facts.
8. A decision is a future child of project. Task 3a does not create a decision
   row or derive a decision ID.

Normative edits completed by `ce132a5`:

- `docs/architecture/data-model.md` now binds the relationship diagram,
  identity and tenancy rules, common columns, and database acceptance;
- ADR-0009 now binds organization plus workspace scope and the membership
  bootstrap resolver;
- ADR-0012 now binds the `core` schema, physical/public ID split,
  schema-fingerprint adoption, and no-fallback cutover;
- `docs/privacy/DATA_MAP.md` now covers OIDC subject, memberships, backfill,
  and audit data; and
- `docs/release/RUNBOOK.md` and `docs/release/ACCEPTANCE.md` now bind the
  migration, shadow, cutover, database-role, restore, and rollback evidence.

The packet passes `python tools/validate_docs.py`, but named Architecture,
Security, Privacy, Persistence, and Release approvals are not recorded. A pure,
dependency-free Checkpoint 3A-1 domain kernel may land disabled for review
while the specification remains **PROPOSED / REVISION REQUIRED**. That review
slice is not approval and must not be wired into routes, workers, persistence,
configuration, or production behavior. No canonical persistence or
integration may begin, and no Checkpoint 3A-2-or-later rollout or production
acceptance may occur, until all five named approvals are recorded with current
implementation evidence.

## 6. Identifier contract

### 6.1 Physical identifiers

Every addressable `core` row uses a PostgreSQL `uuid` primary key generated in
application/operator code as RFC 9562 UUIDv7. Join tables may use composite
primary keys. PostgreSQL sequences and integer legacy keys never cross into the
core domain.

Create `backend/app/domain/identifiers.py` with these interfaces:

```python
from collections.abc import Callable
from typing import Literal
from uuid import UUID

PublicIdKind = Literal["org", "user", "workspace", "project"]

def new_uuid7() -> UUID: ...
def new_public_id(
    kind: PublicIdKind,
    physical_id: UUID,
    *,
    uuid7_factory: Callable[[], UUID] | None = None,
) -> str: ...
def validate_legacy_project_public_id(value: str) -> str: ...
```

`new_uuid7()` constructs the RFC 9562 bit layout using a 48-bit Unix epoch
millisecond value, version bits `0111`, RFC variant bits `10`, and 74
cryptographically random bits from `secrets`. It rejects a clock outside the
48-bit range. Tests verify version, variant, timestamp window, uniqueness, and
ordering across distinct millisecond values; they do not require random IDs
created within one millisecond to sort.

### 6.2 Public aliases

New aliases encode an independently generated UUIDv7:

```text
org_<32 lowercase UUID hex>
user_<32 lowercase UUID hex>
workspace_<32 lowercase UUID hex>
proj_<32 lowercase UUID hex>
```

Rules:

- the physical row ID and the UUIDv7 encoded in its public alias are generated
  by separate `new_uuid7()` calls; the alias is not derived from, keyed by, or
  reversible to the physical ID;
- tests parse every new alias UUID, verify RFC version/variant bits, and prove
  it differs from the row's physical UUID; an equality or alias collision is
  retried as an identity-generation collision rather than accepted;
- aliases are generated by trusted server/operator code, never accepted as the
  identity of a new row from an ordinary client request;
- `workspace_<32 lowercase hex>` accepts and preserves the Task 3 alias even
  when its historical random bits came from UUIDv4;
- every legacy project public ID satisfying
  `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$` is preserved exactly, including current
  `proj_<12 lowercase hex>` values;
- physical IDs are never serialized in public API bodies, URLs, logs, cache
  keys, or telemetry;
- aliases, physical IDs, and organization/workspace ownership columns are
  immutable after insert; database triggers reject an update even when ORM
  validation is bypassed;
- alias collisions fail the dry run and block adoption. They are never
  repaired by silently renaming user-owned records.

## 7. Roles, capabilities, and ActorContext

### 7.1 Closed membership roles

Use the normative values exactly:

```python
class MembershipRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"
    SECURITY = "SECURITY"
```

Organization memberships permit `OWNER`, `ADMIN`, and `SECURITY` in this
slice. Workspace memberships permit all six roles. Roles are persisted;
capabilities are derived from one versioned policy in
`backend/app/domain/authorization.py`, never copied into JWTs or hard-coded in
controllers.

Foundation capabilities are closed to:

```text
organization:read
organization:manage
organization_membership:read
organization_membership:manage
workspace:read
workspace:manage
workspace_membership:read
workspace_membership:manage
project:read
project:create
project:update
project:archive
audit:read
```

Task 3a does not define source, run, path, export, or brief capabilities. Those
tasks extend the central capability enum and policy under their own reviews.

Policy v1 derives organization-scope and workspace-scope grants separately,
then unions those disjoint grants. An organization OWNER therefore does not
gain project mutation rights when their explicit workspace role is VIEWER.
Every project operation is controlled by the workspace role.

| Membership scope and role | Foundation capabilities |
|---|---|
| Organization OWNER or ADMIN | `organization:read`, `organization:manage`, `organization_membership:read`, `organization_membership:manage`, `workspace:read`, `workspace:manage` |
| Organization SECURITY | `organization:read`, `organization_membership:read`, `workspace:read`, `audit:read` |
| Workspace OWNER or ADMIN | `workspace:read`, `workspace:manage`, `workspace_membership:read`, `workspace_membership:manage`, `project:read`, `project:create`, `project:update`, `project:archive`, `audit:read` |
| Workspace EDITOR | `workspace:read`, `workspace_membership:read`, `project:read`, `project:create`, `project:update` |
| Workspace REVIEWER | `workspace:read`, `project:read` |
| Workspace VIEWER | `workspace:read`, `project:read` |
| Workspace SECURITY | `workspace:read`, `workspace_membership:read`, `project:read`, `audit:read` |

OWNER and ADMIN are deliberately equivalent within their respective scope only
for this non-destructive foundation. Organization transfer, hard deletion,
billing, and legal hold are not authorized by any Task 3a capability.

### 7.2 Immutable context

Create `backend/app/domain/actor_context.py`:

```python
class ActorType(str, Enum):
    USER = "USER"
    SERVICE = "SERVICE"

class AuthenticationMethod(str, Enum):
    OIDC = "OIDC"
    LEGACY_DEV = "LEGACY_DEV"

class ActorContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    actor_type: ActorType
    actor_id: UUID
    user_id: UUID | None
    organization_id: UUID
    workspace_id: UUID
    project_id: UUID | None
    organization_role: MembershipRole
    workspace_role: MembershipRole
    capabilities: frozenset[FoundationCapability]
    authentication_method: AuthenticationMethod
    request_id: UUID
    authenticated_at: datetime
```

Rules:

- HTTP authentication in Task 3a produces only `actor_type=USER`; an external
  request cannot ask for a service actor;
- `actor_id`, physical scope, roles, capabilities, request ID, and server time
  are server-derived;
- OIDC claims may authenticate issuer/subject but never directly supply
  organization, workspace, project, roles, or capabilities;
- `user_id` equals `actor_id` for a user; the SERVICE shape is reserved for a
  later narrowly credentialed worker slice and is not constructible through
  the Task 3a HTTP adapter;
- a context exists for exactly one organization/workspace and optionally one
  project; cross-workspace operations require separate contexts;
- capability checks occur in the application service and repositories also
  require the context. RLS is defense in depth, not the policy engine.

## 8. Authentication boundary

### 8.1 OIDC production adapter

Create:

```text
backend/app/application/ports/authentication.py
backend/app/application/actor_context_service.py
backend/app/infrastructure/auth/oidc_authenticator.py
```

Add `PyJWT[crypto]>=2.10,<3` to `backend/pyproject.toml` and update
`backend/uv.lock`. The adapter validates bearer access tokens against the
operator-configured issuer, audience, HTTPS JWKS URL, and an allowlist of
`RS256` and `ES256`. It requires `kid`, `iss`, `sub`, `aud`, `exp`, and `iat`,
validates `nbf` when present, rejects `alg=none` and all HMAC algorithms, and
uses bounded JWKS connect/read timeouts with a five-minute cache. It never logs
the token, claims, issuer subject, email, or JWKS response.

`(issuer, subject)` resolves an existing `core.identity_subjects` row. There is
no request-time auto-provisioning, email-domain membership, claim-to-role
mapping, or fallback to another issuer. Missing identity or inactive
membership fails closed.

Stable transport failures:

```text
401 authentication_required
401 invalid_access_token
403 membership_required
403 capability_required
404 scope_not_found       # missing and wrong-tenant resource use the same code
503 identity_store_unavailable
```

### 8.2 Explicit legacy-development adapter

Create `backend/app/infrastructure/auth/legacy_dev_authenticator.py`. It may
compare the existing `APP_TOKEN` only when all conditions hold:

```text
FLASK_DEBUG=true
AUTHN_V1_MODE=LEGACY_DEV
LEGACY_DEV_AUTH_ENABLED=true
RAILWAY_ENVIRONMENT_ID is absent
```

It resolves pre-provisioned `LEGACY_DEV_USER_PUBLIC_ID`,
`LEGACY_DEV_ORGANIZATION_PUBLIC_ID`, and
`LEGACY_DEV_WORKSPACE_PUBLIC_ID` through the same repository and policy as
OIDC. The adapter does not synthesize rows or grant an implicit owner role.

Production startup rejects `LEGACY_DEV`, a set legacy-dev flag, or missing OIDC
configuration. A failed OIDC request never retries with `APP_TOKEN`. Existing
legacy routes may keep their CURRENT app-wide middleware while flags are off,
but that path is explicitly not production tenancy evidence.

## 9. Canonical `core.*` schema

Create the manual child revision:

```text
backend/migrations/versions/7d2c1a9e4b60_core_tenancy_foundation.py
down_revision = "384c98f88d53"
```

Checkpoint 3A-2 owns this revision and freezes it when that checkpoint lands.
It creates the foundation schema, tables, constraints, indexes, and
immutability triggers only. It does not create database roles, bootstrap
functions, RLS context-helper functions, grants to the application role, RLS
policies, or RLS enablement. Those security objects belong to the separate
immutable Checkpoint 3A-3 child revision specified in section 10.

Create models in
`backend/app/infrastructure/persistence/core_schema.py` with every table
explicitly qualified by `schema="core"`. Do not add these tables to
`backend/app/db/schema.py`'s legacy metadata and do not run `create_all` for
them.

### 9.1 Foundation tables

The migration creates exactly these tables; later tasks add their own schema
objects:

Every one of the twelve tables stores these privacy-governance columns:

```text
retention_class varchar(64) not null
retention_policy_version varchar(128) not null
retention_started_at timestamptz not null
expires_at timestamptz null
```

Checkpoint 3A-2 accepts exactly `retention-policy/v1` in every table-level
check. Any other value fails closed and requires a reviewed migration.

The eight customer-lifecycle deletion targets — `organizations`, `users`,
`identity_subjects`, `workspaces`, `organization_memberships`,
`workspace_memberships`, `projects`, and `legacy_project_bindings` — also
store nullable `deletion_state varchar(32)` and
`deletion_state_changed_at timestamptz`, plus nullable
`deletion_failed_from_state varchar(32)`. Null means no accepted deletion
request. Non-null values are closed to `REQUESTED`, `ELIGIBILITY_CHECK`,
`LEGAL_HOLD`, `PURGING_PRIMARY`, `PURGING_PROVIDERS`, `PURGING_BACKUPS`,
`COMPLETE`, and `FAILED`; database guards accept only the transitions in the
normative deletion state machine and reject the complete Cartesian complement.

The exact graph is `NULL -> REQUESTED`, `REQUESTED -> ELIGIBILITY_CHECK`,
`ELIGIBILITY_CHECK -> LEGAL_HOLD|PURGING_PRIMARY`, `LEGAL_HOLD ->
ELIGIBILITY_CHECK`, `PURGING_PRIMARY -> PURGING_PROVIDERS|FAILED`,
`PURGING_PROVIDERS -> PURGING_BACKUPS|FAILED`, and `PURGING_BACKUPS ->
COMPLETE|FAILED`. `FAILED` returns only to its recorded originating purge
state; `COMPLETE` is terminal. Each lifecycle target also stores nullable
`deletion_failed_from_state`, closed to the three purge states. Entering
`FAILED` atomically stores the origin; leaving it is authorized only to that
state and clears the field. Zero-work stages still advance with durable
evidence and no skip edge is authorized.

The exact table-to-class map is:

| Table | Allowed retention class |
|---|---|
| `core.organizations` | exactly `ACCOUNT_IDENTITY` |
| `core.users` | exactly `ACCOUNT_IDENTITY` |
| `core.identity_subjects` | exactly `ACCOUNT_IDENTITY` |
| `core.workspaces` | exactly `PROJECT_STANDARD` |
| `core.organization_memberships` | exactly `ACCOUNT_IDENTITY` |
| `core.workspace_memberships` | exactly `ACCOUNT_IDENTITY` |
| `core.projects` | exactly `PROJECT_STANDARD` |
| `core.schema_adoptions` | exactly `AUDIT_LONG` |
| `core.backfill_batches` | exactly `AUDIT_LONG` |
| `core.legacy_project_bindings` | exactly `PROJECT_STANDARD` |
| `core.persistence_cutovers` | exactly `AUDIT_LONG` |
| `core.audit_events` | `AUDIT_LONG` or `DELETION_EVIDENCE_LONG`, selected per event purpose |

No schema default may lengthen the server-derived organization/workspace
policy. Audit events require non-null `expires_at`; active lifecycle rows may
leave it null only while their documented lifecycle trigger has not occurred.
Every expiry must be at or after `retention_started_at`.

| Table | Required columns and constraints |
|---|---|
| `core.organizations` | `id uuid PK`, immutable `public_id varchar(128) UNIQUE`, `name varchar(255)`, `status ACTIVE\|SUSPENDED`, `default_region varchar(32)`, nullable policy-version strings, `row_version bigint >= 1`, UTC `created_at/updated_at`, nullable `created_by/updated_by`. |
| `core.users` | `id uuid PK`, immutable `public_id varchar(128) UNIQUE`, nullable bounded `display_name`, `status ACTIVE\|DISABLED`, `row_version`, UTC timestamps. No password, token, or provider secret. |
| `core.identity_subjects` | `id uuid PK`, `user_id` FK, nullable bounded `issuer` and `subject`, status ACTIVE\|REVOKED\|ANONYMIZED, nullable `revoked_at`, `revoked_by`, bounded `revocation_reason_code`, lowercase 64-hex `subject_tombstone_hmac`, bounded `tombstone_key_version`, UTC timestamps, and the retention/deletion fields above. A partial `UNIQUE(issuer, subject)` covers retained non-null raw pairs; a partial `UNIQUE(tombstone_key_version, subject_tombstone_hmac)` covers non-null tombstones. Revoke direct application-table access; resolve only through the exact-subject bootstrap function. |
| `core.workspaces` | `id uuid PK`, immutable `organization_id` FK, immutable `public_id UNIQUE`, `name`, `status ACTIVE\|SUSPENDED\|ARCHIVED`, nullable retention/policy versions, `row_version`, actor/timestamps, and `UNIQUE(organization_id, id)`. |
| `core.organization_memberships` | composite PK `(organization_id, user_id)`, role check limited to OWNER\|ADMIN\|SECURITY, status ACTIVE\|SUSPENDED\|REVOKED, actor/timestamps, `row_version`. |
| `core.workspace_memberships` | composite PK `(organization_id, workspace_id, user_id)`, role check over all six roles, status ACTIVE\|SUSPENDED\|REVOKED, actor/timestamps, `row_version`; composite FKs enforce the same organization and an organization membership. |
| `core.projects` | `id uuid PK`, immutable `organization_id`, `workspace_id`, and `public_id UNIQUE`, bounded `name`, status ACTIVE\|ARCHIVED, `row_version`, actor/timestamps; composite FK `(organization_id, workspace_id)` proves ownership and `UNIQUE(organization_id, workspace_id, id)`. No decision/source/run fields. |
| `core.schema_adoptions` | `id uuid PK`, `alembic_revision`, `adoption_mode CLEAN_BOOTSTRAP\|EXISTING_STAMPED\|EXPLICIT_UNVERSIONED_ADOPTION`, expected/observed SHA-256 fingerprints, PostgreSQL server version, tool version, database identity hash, operator database role, UTC timestamp, evidence SHA-256. Operator role only. |
| `core.backfill_batches` | `id uuid PK`, input-manifest SHA-256, legacy-root fingerprint, status DRY_RUN_VERIFIED\|APPLIED\|RECONCILED\|FAILED, counts, operator public alias, tool version, UTC timestamps, evidence SHA-256. Operator role only. |
| `core.legacy_project_bindings` | `project_id PK/FK`, organization/workspace IDs, immutable legacy project alias, project JSON SHA-256, workspace-manifest SHA-256, bounded tree fingerprint, backfill batch ID, adoption/reconciliation timestamps, status ADOPTED\|RECONCILED\|CONFLICT, `UNIQUE(legacy_project_public_id)`. |
| `core.persistence_cutovers` | `subsystem varchar(64) PK` fixed to `core_tenancy`, state PREPARED\|ACTIVE\|ROLLED_FORWARD, backfill batch ID, reconciliation evidence hash, application/build revision, activated by/time, rollback boundary. Operator role only. |
| `core.audit_events` | `id uuid` logical event ID; `scope_kind TENANT\|SYSTEM`; TENANT requires organization ID and permits bounded workspace/project IDs, while SYSTEM requires all three null; actor type/id, closed event type and reason code, closed privacy-safe `metadata jsonb`, request ID, UTC `occurred_at`, the required retention fields, and non-null immutable `expires_at`; append-only trigger rejects row update/delete by ordinary roles. PostgreSQL-valid physical PK is `(retention_class, expires_at, id)`; `id` has a non-unique lookup index and is never a foreign-key target. It is list-partitioned by the two allowed retention classes and range-subpartitioned by expiry bucket, with no default partition. |

All SHA-256 columns are lowercase 64-character hex with database checks. All
timestamps are `TIMESTAMPTZ`. All mutable foundation aggregates use optimistic
concurrency. No table stores raw bearer tokens, OIDC claims, source text,
decision text, prompts, model output, hidden reasoning, or unrestricted error
strings.

The closed v1 audit event/metadata matrix is:

| Event type | Exact reason code | Scope | Exact JSON keys and types |
|---|---|---|---|
| `SCHEMA_ADOPTION_RECORDED` | `SCHEMA_ADOPTION_VERIFIED` | `SYSTEM` | `evidence_sha256: lowerhex64` |
| `ROLE_TOPOLOGY_VERIFIED` | `ROLE_TOPOLOGY_MATCHED` | `SYSTEM` | `evidence_sha256: lowerhex64` |
| `AUDIT_PARTITION_EXPIRY_APPROVED` | `RETENTION_EXPIRY_APPROVED` | `SYSTEM` | `retention_class: enum`, `bucket_start: UTC date`, `bucket_end: UTC date`, `evidence_sha256: lowerhex64`, `zero_hold_evidence_sha256: lowerhex64`, `approver_public_id: bounded alias` |
| `AUDIT_PARTITION_EXPIRED` | `RETENTION_EXPIRY_COMPLETED` | `SYSTEM` | all approval keys plus `row_count: nonnegative integer` and `aggregate_event_sha256: lowerhex64` |

No extra key, alternate type, tenant scope for these events, physical ID, free
text, raw error, or content field is accepted. Later event types require a
reviewed migration that expands this closed matrix.

Identity-subject checks are fail closed:

- `ACTIVE` requires raw issuer/subject, requires all revocation and tombstone
  fields null, and is the only status the bootstrap resolver may authenticate;
- `REVOKED` is immediately unusable, requires raw issuer/subject plus
  `revoked_at`, `revoked_by`, and `revocation_reason_code`, and retains raw
  values only for the approved recovery/hold window;
- `ANONYMIZED` requires issuer/subject null, all revocation fields non-null,
  and a keyed HMAC-SHA-256 tombstone and key version. The HMAC covers the
  canonical length-prefixed `(issuer, subject)` pair under a dedicated key
  stored outside PostgreSQL;
- the tombstone is covered by `ACCOUNT_IDENTITY`, has bounded `expires_at`,
  never exceeds the authorized deletion-evidence period without a reviewed
  hold, and is never returned, logged, treated as a credential/public ID, or
  used in analytics; and
- restore, backfill, and OIDC claims cannot reverse revocation/anonymization or
  silently recreate a tombstoned pair. Re-linking requires a later, separately
  authorized identity-proofing command and append-only evidence.

### 9.2 Immutability and schema ownership

The migration also creates:

- `core.reject_identity_or_scope_update()` and triggers on organization, user,
  workspace, and project physical/public identity and ownership columns;
- the same trigger protects `identity_subjects.id/user_id`, both membership
  composite identities/scopes, `legacy_project_bindings` project/organization/
  workspace/legacy-alias fields, and IDs plus immutable identity fields on
  every operator-evidence record;
- `core.enforce_identity_subject_transition()` permits only ACTIVE -> REVOKED
  -> ANONYMIZED, makes ANONYMIZED terminal, permits raw issuer/subject nulling
  only on REVOKED -> ANONYMIZED, and makes a set tombstone/key immutable;
- `core.enforce_deletion_transition()` enforces the exact OLD-to-NEW graph and
  recorded failed-origin invariant on all eight lifecycle tables;
- `core.reject_audit_mutation()` on audit events;
- `CHECK` constraints for aliases, states, roles, versions, hashes, exact
  table/class mapping, expiry ordering, deletion-state vocabulary, and the
  complete identity-subject lifecycle invariants;
- only the indexes needed by exact identity, membership, scope, and audit
  queries.

The exact operator-evidence mutability matrix is:

| Table | Immutable after insert | Only authorized mutable fields |
|---|---|---|
| `schema_adoptions` | every column | none; append a new evidence row |
| `backfill_batches` | `id`, input/legacy hashes, operator alias, tool version, `created_at`, retention class/policy/start | status, bounded counts, evidence hash, `updated_at`, and one-way policy-derived `expires_at` shortening, only through the closed batch transition trigger |
| `legacy_project_bindings` | project/organization/workspace IDs, legacy alias, project/workspace/tree hashes, backfill batch ID, adoption time, retention class/policy/start | status and reconciliation time, only `ADOPTED -> RECONCILED|CONFLICT` with both targets terminal; deletion state/time/failed-origin only through the exact deletion trigger; one-way policy-derived `expires_at` shortening |
| `persistence_cutovers` | subsystem; once PREPARED, backfill ID, reconciliation hash, application/build revision, rollback boundary, retention class/policy/start | state and activation actor/time, only `PREPARED -> ACTIVE -> ROLLED_FORWARD`; one-way policy-derived `expires_at` shortening |

Test 13 mutates every immutable column and every unlisted mutable column; the
complete complement fails closed.

The closed backfill graph is `DRY_RUN_VERIFIED -> APPLIED|FAILED` and
`APPLIED -> RECONCILED|FAILED`; `RECONCILED` and `FAILED` are terminal. A retry
creates a new batch. Policy-derived expiry may move only from null to the exact
derived timestamp or to an earlier timestamp after a shortening policy event;
it can never be extended or changed by an ordinary actor.

Append-only is role-bounded rather than perpetual. Checkpoint 3A-2 creates the
class/expiry partition topology and row-mutation trigger, but no application or
retention grant. Checkpoint 3A-3 creates the reviewed partition-expiry function
and its least-privilege grant as described in section 10.3. No ordinary role
may update/delete a live event, detach a partition, or bypass expiry/hold
evidence.

The initial migration creates yearly expiry partitions for both allowed audit
classes covering `2026-01-01T00:00:00Z` through
`2035-01-01T00:00:00Z`. There is no default partition. An insert whose expiry
has no exact partition fails closed; future coverage requires a separately
reviewed operator action before the boundary is reached.

The twelve-table count is the logical domain-table count; partition children
are physical storage relations. List children are `audit_events_audit_long`
and `audit_events_deletion_evidence_long`; yearly leaves use
`audit_events_<class>_y<year>` for 2026 through 2034 with exact UTC bounds.

The migration creates no PostgreSQL role. Before Alembic connects,
`deploy/postgres/core_roles.sql` must have provisioned the exact reviewed roles
in section 10.1. The migration refuses to run if any role is absent, if
`asktp_app` is privileged or can assume the owner role, or if the migration
session cannot explicitly assume `asktp_core_owner`. It creates and owns every
`core` object while that owner role is active and resets the role before the
operator session returns.

Application SQL always schema-qualifies core objects. No deployment changes the
global `search_path` to make `core` shadow legacy `public` table names.

## 10. RLS and scoped repositories

### 10.1 Database roles

Provision roles through an operator-owned SQL/IaC step, not web/worker startup:

```text
asktp_core_owner     NOLOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS
asktp_migrator       LOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS; may SET ROLE asktp_core_owner only in a reviewed migration
asktp_app            LOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS
asktp_backfill       LOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS; temporary reviewed grants revoked after cutover
asktp_readonly       LOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS; scoped incident/read-replica access
asktp_retention      LOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS; execute-only audited partition expiry
```

Checkpoint 3A-2 owns `deploy/postgres/core_roles.sql` as a prerequisite, not as
an Alembic side effect. A cluster administrator applies the idempotent script
before either core revision. The script creates or validates the six exact
roles, grants only `asktp_migrator` the ability to assume
`asktp_core_owner`, and refuses an existing role whose login, ownership,
superuser, database-creation, role-creation, inheritance, or `BYPASSRLS`
attributes exceed the contract. It does not create a database, schema, table,
function, policy, application user mapping, or credential. Passwords and
connection URLs are supplied by the deployment secret system, never embedded
in the script. Checkpoint 3A-5 reuses and verifies this same checked-in script;
it does not create an alternate role topology.

`asktp_retention` has no membership in `asktp_core_owner`, no direct table or
partition privilege, no ability to insert approval evidence, and no general
function execution. Checkpoint 3A-3 grants it `EXECUTE` only on the bounded
audit-partition expiry function. Its credential is exposed only to a manual,
audited retention job after separate Privacy/Security approval evidence exists.

The web and ordinary Celery worker receive only the `asktp_app` URL. They never
receive `DATABASE_MIGRATION_URL`, `DATABASE_ROLE_ADMIN_URL`,
`DATABASE_RETENTION_URL`, or backfill credentials. Tests query `pg_roles`,
role memberships, and table ownership to
prove `asktp_app` is not owner, superuser, RLS-bypass, or able to assume the
owner role.

### 10.2 Bootstrap resolution

The application must identify a user and membership before tenant GUCs can be
set. Checkpoint 3A-3 creates this immutable child revision:

```text
backend/migrations/versions/a6150cf0e9d2_core_tenancy_rls_bootstrap.py
down_revision = "7d2c1a9e4b60"
```

The `a6150cf0e9d2` revision creates two narrowly scoped `SECURITY DEFINER`
functions:

```sql
core.resolve_oidc_subject(p_issuer text, p_subject text)
core.resolve_actor_project_scope(p_user_id uuid, p_project_public_id text)
```

Both functions have `SET search_path = pg_catalog, core`, bounded inputs,
explicit table qualification, no dynamic SQL, no content fields, and
`REVOKE ALL ... FROM PUBLIC`. The application role receives only `EXECUTE`.
The first resolves only an exact raw issuer/subject row whose status is
`ACTIVE`; `REVOKED`, `ANONYMIZED`, expired, or deletion-pending links always
return no row, and the tombstone is never an authentication lookup result. The
second returns a row only for active user, organization, organization
membership, workspace, workspace membership, and project. Missing, revoked,
expired, and wrong-tenant resources are indistinguishable.

After bootstrap, every repository transaction executes parameterized:

```sql
SET LOCAL app.actor_id = '<physical user uuid>';
SET LOCAL app.organization_id = '<physical organization uuid>';
SET LOCAL app.workspace_id = '<physical workspace uuid>';
SET LOCAL app.request_id = '<request uuid>';
```

Values come only from the bootstrap result. No header, query, body, JWT custom
claim, task payload, or public alias is copied into these settings as a
physical ID.

### 10.3 Policies

The `a6150cf0e9d2` revision enables and `FORCE ROW LEVEL SECURITY` on
organizations, workspaces, organization memberships, workspace memberships,
projects, legacy-project bindings, and audit events. It owns all RLS helper
functions, policies, revocations, and least-privilege grants. Policies compare
both `organization_id` and `workspace_id` where both exist. Users and identity
subjects are not generally selectable by `asktp_app`; the bootstrap function
is their only authentication read boundary.

RLS policies use `current_setting('app.organization_id', true)` and
`current_setting('app.workspace_id', true)` through non-throwing helper
functions. A missing or malformed setting yields no row rather than a database
error containing internals. `WITH CHECK` mirrors every `USING` predicate.

The same `a6150cf0e9d2` revision creates one separately scoped retention
function:

```sql
core.expire_audit_partition(
    p_retention_class text,
    p_expiry_bucket date,
    p_approval_evidence_sha256 text
)
```

It is `SECURITY DEFINER`, owned by `asktp_core_owner`, has
`SET search_path = pg_catalog, core`, is revoked from `PUBLIC` and every role
except execute-only `asktp_retention`, and accepts no caller-supplied relation
name or SQL. It derives the partition from the closed class and canonical date
bucket, then verifies its schema, parent, and bounds through `pg_catalog`.

The function fails closed unless all of these facts hold in the same
transaction:

1. `session_user` is exactly `asktp_retention` and both class/hash inputs pass
   closed validation;
2. every row in the derived partition is past its policy-derived `expires_at`;
3. an immutable `AUDIT_PARTITION_EXPIRY_APPROVED` event exists outside the
   target partition and binds the class, bucket, evidence SHA-256, approver
   aliases, approval time/expiry, and an exact zero-active-hold result;
4. the approval remains unexpired, has not been consumed by a matching
   completion event, and contains no customer content, identity subject,
   membership list, raw path, credential, or approval artifact; and
5. the completion event can be inserted into a different, current
   `AUDIT_LONG` partition before the target partition is detached and dropped.

Success records `AUDIT_PARTITION_EXPIRED` with the same evidence hash, bounded
row count, class/bucket, and completion time, then removes the entire target
partition. It never performs row-by-row mutation. Evidence contents stay in an
encrypted operator store under their own approved class; the database keeps
only the lowercase SHA-256 and bounded metadata.

Task 3a does not implement legal-hold administration. Therefore a non-disposable
environment cannot create `AUDIT_PARTITION_EXPIRY_APPROVED` until the later
approved hold registry/workflow can produce the zero-hold evidence. The only
Task 3a expiry success case is a disposable, non-customer rehearsal fixture;
all other missing-hold-authority cases must fail closed. This preserves bounded
expiry design without pretending that deletion/legal-hold operations are
production-ready.

Checkpoint 3A-3 may build `a6150cf0e9d2` incrementally under its ordered
RED/GREEN tests, but it must be complete before the checkpoint commit and is
immutable after that commit. It never edits `7d2c1a9e4b60`. A later change to
functions, policies, or grants requires another reviewed child revision.

### 10.4 Repository contract

Create:

```text
backend/app/application/ports/tenancy_repository.py
backend/app/infrastructure/persistence/core_session.py
backend/app/infrastructure/persistence/postgres_tenancy_repository.py
```

Required interface:

```python
class TenancyRepository(Protocol):
    def resolve_oidc_subject(self, issuer: str, subject: str) -> UUID: ...
    def resolve_project_context(
        self, user_id: UUID, project_public_id: str, request_id: UUID
    ) -> ActorContext: ...
    def get_project(self, actor: ActorContext, project_public_id: str) -> CoreProject: ...
```

Application services never receive a raw SQLAlchemy `Session`. Every scoped
method requires `ActorContext`, applies explicit organization/workspace
predicates even under RLS, and returns frozen domain records rather than ORM
entities. Repository methods do not accept an override scope.

Use one transaction per request/command. `SET LOCAL` is transaction-bound;
connection check-in performs rollback and clears custom settings. Integration
tests deliberately reuse one pooled connection across two tenants and prove no
scope leakage. An unscoped query returns no tenant rows.

## 11. Migration fingerprint and adoption

### 11.1 Never rewrite the baseline

`backend/migrations/versions/384c98f88d53_initial_schema.py` remains byte-for-
byte unchanged. Do not run Alembic autogenerate against
`backend/app/db/schema.py`. The new migration is an additive child that creates
the `core` schema and leaves all legacy `public.*` rows untouched.

Create:

```text
backend/migrations/fingerprints/384c98f88d53.json
backend/tools/core_schema_fingerprint.py
backend/tools/adopt_core_schema.py
backend/tests/integration/test_core_schema_adoption.py
```

The fingerprint tool reads the migration URL from
`DATABASE_MIGRATION_URL`; URLs and credentials never appear in CLI arguments or
output. It canonicalizes the six managed public tables from `384c98f88d53`:
table/schema names; ordered columns; normalized PostgreSQL types, nullability,
and defaults; primary/foreign/unique/check constraints; and normalized index
columns/uniqueness. It serializes sorted UTF-8 JSON with separators
`(',', ':')` and hashes those bytes with SHA-256. Owners, OIDs, physical page
layout, statistics, and PostgreSQL-generated constraint names are excluded.

The checked-in fingerprint fixture is generated by applying the unmodified
`384c98f88d53` migration to an empty supported PostgreSQL 16 instance. CI
recreates that database and asserts the calculated canonical JSON and SHA-256
match the fixture.

### 11.2 Supported starting states

The operator tool handles only:

| Starting state | Behavior |
|---|---|
| Empty database | Run the unmodified baseline, verify its fingerprint, apply the core child revision, record `CLEAN_BOOTSTRAP`. |
| Alembic reports `384c98f88d53` and fingerprint matches | Apply the child revision and record `EXISTING_STAMPED`. |
| Managed public tables exactly match the fingerprint but `alembic_version` is absent | Refuse by default. With `--adopt-existing-384c` and `--expected-fingerprint <exact SHA>`, stamp only `384c98f88d53`, apply the child, and record `EXPLICIT_UNVERSIONED_ADOPTION`. |
| Any missing, extra, renamed, type-changed, constraint-changed, or index-changed managed object | Exit nonzero with a bounded mismatch code and a safe artifact; do not stamp or migrate. |
| Alembic revision other than an allowed ancestor/head | Exit nonzero; require database-owner review. |

The adoption command acquires a PostgreSQL advisory lock, checks no other
migration session is active, records server/application revision, and emits an
evidence JSON whose SHA-256 is inserted into `core.schema_adoptions`. It never
runs from Flask startup, a route, Celery, or a release health check.

The `a6150cf0e9d2` downgrade may remove its functions, policies, revocations,
and grants only in a disposable dark rehearsal with application access and all
core feature flags disabled. The `7d2c1a9e4b60` downgrade may then remove an
empty, never-cut-over core schema. Neither downgrade drops or alters the
externally provisioned roles. Once a backfill or cutover record exists, either
downgrade refuses and production uses a reviewed forward fix.

## 12. Operator-owned backfill

Create:

```text
backend/tools/backfill_core_tenancy.py
backend/app/infrastructure/persistence/core_backfill_repository.py
backend/tests/integration/test_core_tenancy_backfill.py
```

There is no backfill HTTP endpoint and no automatic startup adoption. The tool
uses `DATABASE_MIGRATION_URL`/temporary `asktp_backfill` credentials and a
versioned operator manifest with:

```json
{
  "schema_version": "core-tenancy-backfill/v1",
  "organization": {
    "public_id": "org_<32 lowercase hex>",
    "name": "operator-approved bounded name",
    "retention_policy_version": "operator-approved policy version"
  },
  "users": [
    {
      "public_id": "user_<32 lowercase hex>",
      "oidc_issuer": "https://operator-approved.example/",
      "oidc_subject": "operator-provided exact subject",
      "organization_role": "OWNER"
    }
  ],
  "legacy_projects": [
    {
      "project_public_id": "proj_existing",
      "workspace_public_id": "workspace_<32 lowercase hex>",
      "workspace_name": "operator-approved bounded name",
      "retention_policy_version": "operator-approved policy version",
      "members": [
        {"user_public_id": "user_<32 lowercase hex>", "role": "OWNER"}
      ]
    }
  ]
}
```

Angle-bracket forms above describe validated formats, not literal values. The
operator manifest is sensitive evidence: it is not committed and ordinary
logs never contain names, issuer subjects, or membership lists.

Backfill rules:

1. `--dry-run` is mandatory before `--apply`; apply requires the dry-run
   evidence SHA-256 and the same legacy-root fingerprint.
2. The operator explicitly supplies organization and membership mapping. No
   organization is inferred from project IDs, directory ownership, filenames,
   token claims, or workspace aliases.
3. Existing `workspace_manifest.json` must validate against the Task 3 strict
   model and match the operator mapping. Missing, invalid, mismatched, or
   duplicate aliases block the batch. The tool does not regenerate over a
   conflict.
4. The tool canonicalizes and hashes `project.json`, the workspace manifest,
   and a bounded inventory of project-relative paths/byte sizes/hashes. It does
   not copy source bytes, extracted text, decision text, simulations, reports,
   or generated artifacts.
5. Core organization, user, identity, membership, workspace, project, binding,
   audit, and batch rows commit transactionally. Every row receives the exact
   table-mapped retention class, policy version, start, and policy-derived
   expiry; lifecycle deletion targets receive null deletion fields. Physical
   UUIDv7 IDs are new; public aliases remain unchanged.
6. Reapplying the identical manifest/root fingerprint is idempotent and returns
   the recorded result. Any changed mapping or legacy fingerprint conflicts;
   it never mutates aliases or ownership to make the rerun pass.
7. Reconciliation compares row counts, alias sets, relationship sets, and all
   stored fingerprints. Raw names and identity subjects do not appear in the
   summary artifact.
8. After final reconciliation, revoke the temporary role and archive the
   encrypted operator manifest according to the approved security retention
   class.
9. Before inserting an identity subject, the operator tool computes the
   versioned HMAC for the exact length-prefixed issuer/subject pair inside the
   protected process and refuses a matching unexpired tombstone. The key never
   enters PostgreSQL, the manifest, logs, evidence, or application settings.
   This check cannot reactivate, overwrite, or delete a tombstone.

## 13. Shadow comparison and cutover — no dual write, no fallback

Create
`backend/app/application/core_identity_router.py` and
`backend/app/infrastructure/persistence/core_shadow_compare.py`.

The only supported modes are:

| Read mode | Write authority | Behavior |
|---|---|---|
| `LEGACY` | legacy only | CURRENT behavior. Core may be absent. |
| `SHADOW` | legacy only | Legacy is deliberately authoritative. Read the corresponding core identity in a side comparison, emit bounded mismatch counters, and return the legacy result. Shadow code performs zero writes. This is not fallback because canonical was never selected. |
| `CANONICAL` | core only | Read and write core only. Missing rows, RLS denial, timeout, or unavailable PostgreSQL fails closed. Never query legacy to satisfy the request. |

There is no `DUAL` mode. A single request, route, job, or service may not write
both stores. Canonicalization occurs only through the offline backfill while
legacy writes are controlled.

Shadow comparison covers only Task 3a facts:

- project public alias;
- Task 3 workspace public alias;
- organization/workspace/project relationship;
- active membership and derived foundation capabilities;
- legacy project status/name hashes where retained in core;
- adoption fingerprints.

Metrics contain environment, build revision, comparison code, and counts only.
They do not contain aliases, names, OIDC claims, paths, content, or physical
IDs. Every mismatch blocks cutover and gets a bounded operator evidence entry.

Cutover sequence:

1. deploy schema and code dark with flags off;
2. create backup and prove an isolated restore;
3. provision OIDC identities/memberships and run dry-run/apply backfill;
4. enable `SHADOW`; complete a full offline comparison plus representative
   authenticated internal reads with zero unexplained mismatch;
5. enter maintenance and disable every legacy project/workspace identity
   writer;
6. fingerprint again, run the final idempotent backfill/reconciliation, and
   record `PREPARED` with exact evidence/build hashes;
7. set read mode to `CANONICAL`; startup verifies the `PREPARED` record and
   correct application database role;
8. run OIDC, membership, RLS, cross-tenant, and no-fallback smoke tests;
9. activate the cutover record and keep legacy storage read-only as a bounded
   evidence snapshot;
10. revoke the backfill role and monitor privacy-safe mismatch/denial/error
    metrics.

Task 3a does not implement a canonical public project-creation workflow, so a
production user cohort cannot remain writable after this cutover. Its eligible
deployment is dark/shadow or a maintenance/read-only internal pilot. A later
authorized project-command slice must exist before general canonical writes
are enabled. This is an honest gate, not an optional enhancement.

Rollback rules:

- before any canonical application write, an operator may return reads to the
  verified read-only legacy snapshot under an approved rollback record;
- after the first canonical application write, never route back to legacy or
  replay writes ad hoc. Keep core canonical and deploy a schema-compatible
  application rollback or forward fix;
- database unavailability in `CANONICAL` returns stable 503 behavior. It does
  not trigger a legacy read or write;
- rollback never re-enables an unscoped production APP_TOKEN path.

## 14. Feature flags and startup validation

Add typed configuration with these exact values:

```text
CORE_FOUNDATION_ENABLED=false
CORE_FOUNDATION_READ_MODE=LEGACY        # LEGACY | SHADOW | CANONICAL
CORE_FOUNDATION_WRITE_MODE=DISABLED     # DISABLED | BACKFILL | CANONICAL
LEGACY_PROJECT_WRITES_ENABLED=true
AUTHN_V1_MODE=DISABLED                  # DISABLED | OIDC | LEGACY_DEV
LEGACY_DEV_AUTH_ENABLED=false
```

OIDC settings:

```text
OIDC_ISSUER=
OIDC_AUDIENCE=
OIDC_JWKS_URL=
OIDC_ALLOWED_ALGORITHMS=RS256,ES256
OIDC_CLOCK_SKEW_SECONDS=60
OIDC_JWKS_CACHE_SECONDS=300
OIDC_HTTP_CONNECT_TIMEOUT_SECONDS=2
OIDC_HTTP_READ_TIMEOUT_SECONDS=3
```

Database settings:

```text
DATABASE_URL=                  # asktp_app only
DATABASE_MIGRATION_URL=        # operator/release job only; absent from web/worker
DATABASE_ROLE_ADMIN_URL=       # one-shot role prerequisite only; absent from web/worker/migrator
DATABASE_RETENTION_URL=        # manual audited expiry job only; absent from web/worker/migrator/backfill
CORE_DATABASE_EXPECTED_ROLE=asktp_app
CORE_DATABASE_STATEMENT_TIMEOUT_MS=5000
CORE_DATABASE_LOCK_TIMEOUT_MS=2000
```

Operator-only identity settings, absent from web, ordinary workers, migration,
and retention jobs:

```text
IDENTITY_TOMBSTONE_HMAC_KEY=
IDENTITY_TOMBSTONE_HMAC_KEY_VERSION=
```

Startup refuses these combinations:

- core enabled without a PostgreSQL/psycopg URL;
- core enabled unless the database revision exactly equals the release
  manifest's declared compatible head. A 3A-2-only dark review manifest may
  declare `7d2c1a9e4b60`; it cannot authorize application reads or writes;
- `SHADOW` or `CANONICAL` unless the deployed revision contains both
  `7d2c1a9e4b60` and `a6150cf0e9d2` in its ancestry and exactly equals the
  release manifest's declared compatible head;
- `SHADOW` with `BACKFILL` or `CANONICAL` application writes;
- `CANONICAL` reads without a `PREPARED`/`ACTIVE` cutover record;
- `CANONICAL` writes unless reads are canonical and legacy writes are false;
- web/worker access to `DATABASE_MIGRATION_URL` or
  `DATABASE_ROLE_ADMIN_URL`, `DATABASE_RETENTION_URL`, or a tombstone key;
- migration-job access to `DATABASE_ROLE_ADMIN_URL` after the role prerequisite
  completes, or to retention/tombstone credentials at any time;
- retention-job access to migration, role-admin, backfill, or tombstone
  credentials;
- the application database role owning core tables or having `BYPASSRLS`;
- OIDC mode with missing/non-HTTPS issuer/JWKS, empty audience, or algorithms
  outside the allowlist;
- LEGACY_DEV in production, Railway, or when Flask debug is false;
- core canonical mode with authentication disabled;
- any unknown flag value. There is no permissive default coercion.

Update `.env.example` with the flags and warnings, but no credentials or real
issuer subjects. Config tests must construct fresh settings objects so module
import caching cannot hide invalid combinations.

## 15. Deployment and operating contract

Railway remains the canonical host. Task 3a adds a managed PostgreSQL 16+
service and separate URLs/roles; it does not move deployment to Sites or add a
second auto-deploy platform.

Required deployment work:

1. provision encrypted PostgreSQL with backups/PITR suitable for the declared
   RPO/RTO and private service networking;
2. require TLS and bounded connection/statement/lock timeouts;
3. apply the reviewed, idempotent `deploy/postgres/core_roles.sql` prerequisite,
   verify its exact role attributes and assumption graph, and store URLs as
   separate Railway secrets; remove the role-admin URL from the migration job
   immediately after this prerequisite succeeds;
4. expose `DATABASE_URL` to web and only workers that need scoped core reads;
5. expose `DATABASE_MIGRATION_URL` only to a manual release/migration job;
6. run fingerprint/adoption and migration before deploying any non-LEGACY read
   mode; application startup never upgrades the schema;
7. deploy the application with all Task 3a flags off, then run dark readiness;
8. verify backup restore, forced RLS, role ownership, connection-pool scope
   reset, and migration head before shadow mode;
9. attach migration, backfill, comparison, cutover, restore, and smoke artifacts
   to one release record;
10. retain the single-web-worker warning: core tenancy does not fix the
    process-local simulation runner or make the overall app horizontally safe.

`DATABASE_RETENTION_URL` is never a standing web/worker/release-job secret. It
may be injected into a one-shot manual retention rehearsal only after the
approval evidence is immutable, then is removed. Because Task 3a does not ship
the legal-hold registry, that rehearsal uses a disposable non-customer database
and cannot authorize production expiry. Restore evidence proves that identity
and membership revocations/anonymizations, expired audit partitions, deletion
obligations, and hold releases are replayed before service resumes; no revoked
subject/membership resolves and no purged partition is reattached.

Readiness returns only status codes, migration revision, and build revision. It
does not return database hosts, role names, aliases, counts per customer, or
OIDC details. Logs and metrics never include connection URLs, JWTs, claims,
issuer subjects, email, public aliases, names, filesystem paths, or raw SQL
parameters.

`render.yaml` remains manual/noncanonical. If maintained, it must fail closed
under the same configuration and must not become a weaker OIDC/RLS path.

## 16. Staged checkpoints and exact file ownership

Each checkpoint gets a fresh implementer, spec review, quality review, focused
verification, and a separate commit. Do not begin a later checkpoint with a
failing earlier gate. The sole exception is the disabled, pure-domain
Checkpoint 3A-1 review slice described in section 5; it does not satisfy or
bypass Checkpoint 3A-0.

### Checkpoint 3A-0 — authority packet

**Normative status:** resolved by `ce132a5`; named approval record remains
open.

**Completed normative files:**

```text
docs/architecture/data-model.md
docs/architecture/adr/ADR-0009-multi-tenant-isolation.md
docs/architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md
docs/privacy/DATA_MAP.md
docs/release/RUNBOOK.md
docs/release/ACCEPTANCE.md
```

**Delivered normatively:** the exact relationship, ID, membership,
migration-adoption, cutover, and honest completion boundary in sections 5–15.

**Remaining gate:** rerun the docs validator with zero warnings/errors on the
exact implementation head and record the five named owner approvals. The pure
3A-1 kernel may exist disabled for review, but no production wiring, canonical
persistence/integration, Checkpoint 3A-2-or-later rollout, or production
acceptance is authorized before that gate closes.

### Checkpoint 3A-1 — identifiers and authorization domain

**Create:**

```text
backend/app/domain/identifiers.py
backend/app/domain/authorization.py
backend/app/domain/actor_context.py
backend/tests/domain/test_identifiers.py
backend/tests/domain/test_authorization.py
backend/tests/domain/test_actor_context.py
```

**Deliver:** RFC 9562 UUIDv7, public aliases, strict roles/capabilities, policy
v1, and frozen ActorContext. No database or Flask import in domain modules.
This checkpoint may land only as a disabled, dependency-free review kernel
while 3A-0 approvals remain open. Passing domain tests do not authorize
production integration or promote the specification from PROPOSED.

### Checkpoint 3A-2 — migration lineage and core schema

**Create:**

```text
backend/app/infrastructure/__init__.py
backend/app/infrastructure/persistence/__init__.py
backend/app/infrastructure/persistence/core_schema.py
deploy/postgres/core_roles.sql
backend/migrations/versions/7d2c1a9e4b60_core_tenancy_foundation.py
backend/migrations/fingerprints/384c98f88d53.json
backend/tools/core_schema_fingerprint.py
backend/tools/adopt_core_schema.py
backend/tests/integration/test_core_roles_prerequisite.py
backend/tests/integration/test_core_migration.py
backend/tests/integration/test_core_retention_schema.py
backend/tests/integration/test_core_schema_adoption.py
```

**Modify:** `backend/app/db/__init__.py` to prevent core `create_all` and
separate legacy-development initialization explicitly. Modify
`backend/migrations/env.py` only to require `DATABASE_MIGRATION_URL` for core
migration/adoption commands and remove its SQLite fallback; application web
and worker processes remain unable to receive that credential. Do not modify
`384c98f88d53_initial_schema.py` or autogenerate from
`backend/app/db/schema.py`.

**Deliver:** an idempotent least-privilege role prerequisite; clean, stamped,
and exact-unversioned upgrade paths; immutable baseline; the immutable
schema-only `7d2c1a9e4b60` revision; core tables, constraints, indexes, and
immutability triggers; the exact twelve-table retention mapping, identity-link
lifecycle fields/checks, deletion-state complement, and audit class/expiry
partition topology; schema-adoption evidence; and guarded empty downgrade
rehearsal. This checkpoint stops at `7d2c1a9e4b60`, remains dark, grants no
application or retention access, and creates no bootstrap, expiry, or RLS
function/policy.

### Checkpoint 3A-3 — OIDC, ActorContext service, RLS, and repository

**Create:**

```text
backend/app/application/ports/__init__.py
backend/app/application/ports/authentication.py
backend/app/application/ports/tenancy_repository.py
backend/app/application/actor_context_service.py
backend/app/infrastructure/auth/__init__.py
backend/app/infrastructure/auth/oidc_authenticator.py
backend/app/infrastructure/auth/legacy_dev_authenticator.py
backend/app/infrastructure/persistence/core_session.py
backend/app/infrastructure/persistence/postgres_tenancy_repository.py
backend/migrations/versions/a6150cf0e9d2_core_tenancy_rls_bootstrap.py
backend/tests/test_actor_context_service.py
backend/tests/security/test_oidc_authenticator.py
backend/tests/integration/test_core_rls.py
backend/tests/integration/test_core_repository.py
backend/tests/integration/test_core_retention.py
```

**Modify:**

```text
backend/pyproject.toml
backend/uv.lock
backend/app/config.py
backend/app/__init__.py
.env.example
```

The Flask change registers the opt-in ActorContext seam for future scoped
routes; it does not mark all legacy routes OIDC-safe or globally multi-tenant.
The `a6150cf0e9d2` revision has the exact parent `7d2c1a9e4b60`; it creates all
bootstrap/helper functions, RLS enablement and forced policies, revocations,
and application grants. It never alters the 3A-2 revision. A 3A-3 release
manifest declares `a6150cf0e9d2` as its exact Alembic head. Even at that head,
all application integration and rollout remain disabled until the later gates
and evidence authorize them.
The revision also creates the bounded audit-partition expiry function and
grants only execute to `asktp_retention`; it does not implement a legal-hold or
deletion administration workflow. The function therefore remains unavailable
outside the exact disposable-rehearsal evidence gate in section 10.3.

### Checkpoint 3A-4 — operator backfill and shadow comparison

**Create:**

```text
backend/app/application/core_identity_router.py
backend/app/infrastructure/persistence/core_backfill_repository.py
backend/app/infrastructure/persistence/core_shadow_compare.py
backend/tools/backfill_core_tenancy.py
backend/tests/integration/test_core_tenancy_backfill.py
backend/tests/test_core_identity_router.py
```

**Modify:** `backend/app/application/decision_workspace_service.py` only by
injecting the identity router. `LEGACY` preserves current behavior, `SHADOW`
returns legacy after read-only comparison, and `CANONICAL` uses only core.
Do not move simulation/report/source persistence in this checkpoint.

### Checkpoint 3A-5 — deployment rehearsal and evidence

**Create:**

```text
backend/tools/verify_core_deployment.py
backend/tests/integration/test_core_deployment_contract.py
```

**Modify:** only the canonical Railway/release configuration required to make
the manual migration job and role separation reproducible. Keep `render.yaml`
manual and noncanonical.

**Deliver:** restored backup, migration rehearsal, RLS/role proof, backfill and
shadow evidence, stable failure drill, rollback/forward-fix drill, and a release
record that keeps general enablement disabled.
Checkpoint 3A-5 consumes and re-verifies the 3A-2-owned
`deploy/postgres/core_roles.sql`; it does not replace or broaden it.
The restore drill must additionally prove revocation/anonymization and
retention-ledger replay, tombstone non-disclosure, expired partition
non-reattachment, and fail-closed behavior when zero-hold evidence is absent.

## 17. Strict one-test-at-a-time TDD order

The implementer adds exactly one failing test, runs only that node to observe
RED for the intended missing behavior, implements the minimum behavior, reruns
the same node to GREEN, and records both outputs before adding the next test.
No batch run substitutes for a missing individual RED/GREEN pair.

Required order:

1. `test_uuid7_has_rfc9562_version_variant_and_time_window`
2. `test_new_public_alias_uses_kind_and_independent_uuid7_hex`
3. `test_legacy_project_alias_is_preserved_but_invalid_alias_is_rejected`
4. `test_role_policy_cartesian_matrix_is_closed`
5. `test_actor_context_is_frozen_strict_and_server_scoped`
6. `test_app_role_is_not_owner_superuser_or_rls_bypass`
7. `test_core_roles_prerequisite_is_idempotent_and_has_only_reviewed_assumption_edges`
8. `test_foundation_migration_refuses_missing_or_invalid_role_prerequisite`
9. `test_clean_postgres_upgrade_creates_only_expected_core_tables`
10. `test_original_384c_migration_hash_is_unchanged`
11. `test_exact_unversioned_384c_requires_explicit_fingerprint_adoption`
12. `test_schema_mismatch_refuses_stamp_and_core_migration`
13. `test_exact_identity_scope_and_operator_evidence_immutability_matrix_is_enforced`
14. `test_all_twelve_foundation_tables_have_exact_retention_columns_and_class_checks`
15. `test_deletion_transition_complement_and_failed_origin_retry_are_exact`
16. `test_identity_subject_transition_complement_and_tombstone_uniqueness_are_exact`
17. `test_audit_partition_relations_bounds_composite_key_and_no_default_are_exact`
18. `test_audit_scope_type_reason_metadata_complement_and_row_immutability_are_closed`
19. `test_oidc_rejects_wrong_issuer_audience_algorithm_expiry_and_signature`
20. `test_oidc_claimed_scope_and_roles_are_ignored`
21. `test_legacy_dev_adapter_is_impossible_in_production_or_railway`
22. `test_rls_bootstrap_child_has_exact_parent_and_becomes_head`
23. `test_bootstrap_functions_require_exact_subject_and_active_scope_membership`
24. `test_revoked_anonymized_expired_or_deletion_pending_subject_never_authenticates`
25. `test_inactive_membership_cannot_create_actor_context`
26. `test_role_capabilities_are_derived_server_side`
27. `test_rls_blocks_cross_organization_and_cross_workspace_read_and_write`
28. `test_connection_pool_reuse_does_not_leak_actor_scope`
29. `test_scoped_repository_requires_actor_and_explicit_scope_predicates`
30. `test_retention_role_has_only_bounded_expiry_execute_and_no_table_or_owner_privilege`
31. `test_audit_expiry_rejects_unknown_nonexpired_held_missing_expired_or_consumed_approval`
32. `test_audit_expiry_purges_only_expired_unheld_partition_and_records_minimized_evidence`
33. `test_backfill_dry_run_is_required_and_apply_is_idempotent`
34. `test_backfill_refuses_missing_or_mismatched_workspace_manifest`
35. `test_backfill_never_copies_excluded_content_or_artifact_tables`
36. `test_backfill_refuses_unexpired_identity_subject_tombstone_match`
37. `test_shadow_reads_canonical_but_never_writes_or_changes_response`
38. `test_canonical_mode_never_reads_or_writes_legacy_on_core_failure`
39. `test_invalid_flag_combinations_fail_application_startup`
40. `test_web_worker_migrator_and_retention_jobs_cannot_receive_each_others_credentials`
41. `test_cutover_requires_reconciliation_and_prepared_record`
42. `test_restore_replays_revocation_anonymization_expiry_and_hold_release_before_startup`

Tests 6–18 are the complete Checkpoint 3A-2 ledger. They provision and verify
the role prerequisite first, then land and freeze `7d2c1a9e4b60` as the exact
dark foundation head. No 3A-3 file exists during that checkpoint.

Tests 19–32 are the Checkpoint 3A-3 ledger. Test 22 first observes the missing
child revision and then creates the minimal `a6150cf0e9d2` lineage. Tests 23,
27, 30, and 31 drive its bootstrap/expiry functions, grants/revocations, and RLS policies
before the 3A-3 commit freezes that revision as the exact head. This in-progress
construction never changes the already-landed `7d2c1a9e4b60` revision. Tests
33–42 belong to the later checkpoints.

Example commands from `backend/`:

```powershell
.\.venv\Scripts\pytest tests/domain/test_identifiers.py::test_uuid7_has_rfc9562_version_variant_and_time_window -q --basetemp=.pytest-tmp-task3a
.\.venv\Scripts\pytest tests/integration/test_core_rls.py::test_rls_blocks_cross_organization_and_cross_workspace_read_and_write -q --basetemp=.pytest-tmp-task3a
```

PostgreSQL integration tests use four distinct credentials against the same
disposable PostgreSQL 16+ database: `TEST_POSTGRES_ADMIN_URL` only for the role
prerequisite fixture, `TEST_POSTGRES_MIGRATION_URL` only for Alembic/adoption,
`TEST_POSTGRES_URL` only as the RLS-subject application role, and
`TEST_POSTGRES_RETENTION_URL` only for the disposable expiry rehearsal. The
admin URL is discarded before migration tests, and no fixture can read another
role's credential. These tests must not skip in CI or release verification. SQLite is
not an acceptable substitute for migration, role, function, trigger,
isolation, or connection-pool tests.

After the individual ledger is complete, run:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_identifiers.py tests/domain/test_authorization.py tests/domain/test_actor_context.py -q --basetemp=.pytest-tmp-task3a-domain
.\.venv\Scripts\pytest tests/test_actor_context_service.py tests/security/test_oidc_authenticator.py tests/test_core_identity_router.py -q --basetemp=.pytest-tmp-task3a-services
.\.venv\Scripts\pytest tests/integration/test_core_roles_prerequisite.py tests/integration/test_core_migration.py tests/integration/test_core_retention_schema.py tests/integration/test_core_schema_adoption.py tests/integration/test_core_rls.py tests/integration/test_core_repository.py tests/integration/test_core_retention.py tests/integration/test_core_tenancy_backfill.py tests/integration/test_core_deployment_contract.py -q --basetemp=.pytest-tmp-task3a-postgres
.\.venv\Scripts\pytest tests/test_decision_workspace_api.py tests/domain/test_decision_workspace.py tests/test_api_schemas.py -q --basetemp=.pytest-tmp-task3a-regression
```

Then run touched-file lint, docs validation, and full repository verification:

```powershell
cd backend
uvx ruff check app/domain/identifiers.py app/domain/authorization.py app/domain/actor_context.py app/application/actor_context_service.py app/application/core_identity_router.py app/infrastructure migrations/versions/7d2c1a9e4b60_core_tenancy_foundation.py migrations/versions/a6150cf0e9d2_core_tenancy_rls_bootstrap.py tools tests/domain/test_identifiers.py tests/domain/test_authorization.py tests/domain/test_actor_context.py tests/test_actor_context_service.py tests/security/test_oidc_authenticator.py tests/integration/test_core_roles_prerequisite.py tests/integration/test_core_migration.py tests/integration/test_core_retention_schema.py tests/integration/test_core_schema_adoption.py tests/integration/test_core_rls.py tests/integration/test_core_repository.py tests/integration/test_core_retention.py tests/integration/test_core_tenancy_backfill.py tests/integration/test_core_deployment_contract.py tests/test_core_identity_router.py
cd ..
python tools/validate_docs.py
npm run verify
```

## 18. Honest gates and stop conditions

### Checkpoint completion

Task 3a implementation may be marked complete only when:

- normative relationship changes are approved and validator-clean;
- the original `384c98f88d53` file is byte-identical to its pre-task hash;
- clean, exact-stamped, and explicit-unversioned-adoption rehearsals pass on
  supported PostgreSQL;
- UUIDv7, public alias immutability, role policy, ActorContext, RLS, bootstrap
  functions, repositories, connection reuse, and cross-tenant matrices pass;
- all twelve foundation tables match the exact retention map, identity
  revocation/anonymization invariants pass, audit expiry remains role-bounded
  and evidence-gated, and restore replay cannot reactivate or reattach deleted
  state;
- OIDC validation is complete and the legacy adapter is impossible in
  production/Railway;
- operator dry-run/apply/reconcile is idempotent and copies only foundation
  identities/relationships;
- shadow comparison performs no writes and canonical mode has no legacy
  fallback;
- backup restore, migration, database roles, revocation, and fail-closed drills
  have attached evidence;
- every required test has recorded individual RED/GREEN evidence, then focused
  and repository verification pass;
- unrelated dirty work is absent from Task 3a commits.

### Claims allowed after Task 3a

If all dark/shadow gates pass, release notes may say:

```text
The canonical organization, workspace, membership, and project-identity foundation is deployed behind disabled or shadow-only controls.
```

After an approved read-only canonical pilot, they may say:

```text
Canonical workspace identity and membership checks are active for the named internal pilot scope. Other product records remain on their stated transition paths.
```

### Claims prohibited after Task 3a

Do not say:

```text
the application is multi-tenant
all routes are tenant isolated
canonical persistence is complete
source ingestion is secure
runs are durable
paths or briefs are canonical
production OIDC is complete for legacy routes
the application can fall back safely to legacy storage
```

Task 3a does not close Gate 3. It establishes a reviewed core dependency for
later per-aggregate migration. Gate 3 remains PARTIAL until source, run, path,
brief/export, job, cache, object, index, deletion, and all route boundaries are
scoped and proven.

### Immediate stop conditions

Stop implementation or rollout on any:

- unresolved normative relationship conflict;
- schema fingerprint mismatch or edited baseline migration;
- duplicate/missing alias or operator mapping ambiguity;
- app role ownership/RLS bypass;
- token claim influencing scope/capabilities;
- cross-tenant result, existence leak, or pool-scope leak;
- shadow write, live dual write, or canonical-to-legacy fallback;
- missing restore evidence or unrevoked backfill credential;
- raw identity/membership data in logs, metrics, traces, or evidence;
- missing/unknown retention metadata, a table/class mismatch, or an unguarded
  deletion transition;
- revoked/anonymized identity authentication, raw-subject retention past
  expiry, tombstone disclosure/reversal, or restore-time reactivation;
- row-by-row audit mutation, expiry of a nonexpired/held partition, missing or
  replayed approval evidence, or standing retention credentials;
- deployment that makes general product records appear canonical.

## 19. Implementation report

Write `.superpowers/sdd/task-3a-tenant-persistence-report.md` with:

- authority approvals and exact doc commit;
- files changed and excluded scope confirmation;
- the pre/post SHA-256 of `384c98f88d53_initial_schema.py`;
- every individual RED/GREEN command and result in order;
- PostgreSQL version, migration starting state, calculated schema fingerprint,
  exact `7d2c1a9e4b60` and `a6150cf0e9d2` lineage/head evidence, role-prerequisite
  and RLS checks, and downgrade/forward-fix evidence;
- dry-run/apply/reconciliation evidence hashes without sensitive contents;
- shadow mismatch totals and proof of zero shadow writes;
- canonical failure/no-fallback evidence;
- backup/restore, credential revocation, cutover/rollback, and release record;
- twelve-table retention/class evidence, identity lifecycle/tombstone negative
  tests, partition expiry/hold/approval evidence, and restore-replay results;
- focused regressions, touched-file lint, docs validator, and `npm run verify`;
- independent spec and quality review verdicts;
- commit SHAs and any remaining honest production blocker.

No passing unit test, created table, or dark deployment is sufficient by itself
to claim the tenant/persistence foundation is production-enabled.

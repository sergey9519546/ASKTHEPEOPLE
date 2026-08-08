# Task 4 revised brief — controlled TXT source ingestion and review

Read this first. It replaces the earlier Task 4 implementation assumptions for
execution purposes. It does not amend the tracked master plan or any normative
document.

## 1. Status and stop-ship decision

**Specification status: PROPOSED / REVISION REQUIRED.**

Task 4 is a stop-ship item as previously scoped. The CURRENT application does
not have a secure source-ingestion boundary, a tenant authorization boundary,
or durable review records. No implementation, screenshot, passing happy-path
test, or disabled domain package may be described as “secure source
ingestion.”

The first eligible release slice is intentionally narrow:

```text
TXT only
direct browser-to-private-object-store upload
strict UTF-8 decoding
quarantine -> scan -> isolated parse -> candidate review -> READY
```

PDF, Markdown, DOCX, HTML, CSV, URL fetch, OCR, images, archives, and every
other input remain **UNAVAILABLE**. PDF is a later opt-in checkpoint, not part
of this task’s first release.

The feature flag is disabled by default:

```text
SOURCE_INGESTION_V1_ENABLED=false
SOURCE_INGESTION_V1_FORMATS=
```

Development may set `SOURCE_INGESTION_V1_FORMATS=txt` only after the relevant
checkpoint gates pass. Production startup must refuse to enable the flag when
any production blocker in section 5 is absent.

## 2. Authority and state legend

The authority order in `AGENTS.md` applies. In particular:

- `docs/product/PRODUCT_TRUTH_CONTRACT.md` controls epistemic claims;
- `docs/product/USE_POLICY.md` controls prohibited and high-risk use;
- `docs/security/SOURCE_INGESTION.md` and
  `docs/security/THREAT_MODEL.md` control the ingestion boundary;
- `docs/privacy/DATA_MAP.md`, `docs/privacy/RETENTION.md`, and
  `docs/privacy/SUBPROCESSORS.md` control data handling;
- `docs/architecture/adr/ADR-0005-zero-trust-source-ingestion.md`,
  ADR-0009, ADR-0012, `docs/architecture/state-machines.md`, and
  `docs/architecture/data-model.md` control architecture;
- `docs/release/ACCEPTANCE.md` and `docs/release/RUNBOOK.md` control release
  claims and evidence.

This brief uses the required terms exactly:

- **CURRENT** — observable in the repository now.
- **PARTIAL** — some required behavior exists, but the product must not imply
  completion.
- **TARGET** — required production behavior.
- **TRANSITION** — a bounded compatibility step with an explicit removal gate.

Where this brief conflicts with a higher-authority document, the higher
authority controls. Section 6 records conflicts that must be resolved rather
than guessed around.

## 3. Deliverable boundary

Build a durable, tenant-scoped source aggregate and one reviewable TXT vertical
slice. A source may shape reviewed starting conditions only. It may not
validate, prove, corroborate, or attach evidence to a possible path or
synthetic conclusion.

The slice includes:

1. typed source, version, segment, candidate, flag, review-event, deletion,
   command, and provenance contracts;
2. organization/workspace authorization and capability checks;
3. canonical PostgreSQL persistence, row-level isolation, transactional
   outbox, audit records, and optimistic concurrency;
4. private quarantine and processed object storage;
5. direct upload intent and completion verification;
6. malware scanning and strict TXT parsing in isolated, no-egress workloads;
7. candidate extraction and explicit human dispositions;
8. source readiness and deletion workflows;
9. new per-resource API routes under `backend/app/api/routes/`;
10. removal or hard disablement of CURRENT legacy bypasses;
11. a frontend ingestion/review experience driven by server capabilities;
12. malicious-corpus, cross-tenant, deletion, recovery, accessibility, and
    release-evidence tests.

This slice does **not** establish behavioral validity, representativeness,
causal validity, reproducibility, calibration, or release readiness for later
simulation stages.

## 4. CURRENT audit ledger

The implementation must begin from these facts, not from the TARGET diagrams.

| Area | CURRENT fact | Consequence |
|---|---|---|
| Upload | `backend/app/api/graph.py:266-376` creates a project, saves uploads, extracts text in the web request, writes `extracted_text.txt`, and sends raw text to Celery. | Source bytes and text cross trust boundaries before quarantine, scanning, or review. |
| Validation | `backend/app/api/graph.py:68-73` and `backend/app/utils/file_security.py:20-78` rely on extensions, filename-derived MIME, and a Latin-1 fallback. | This is not content verification or strict decoding. |
| Parsing | `backend/app/utils/file_parser.py:17-64` parses PDF, Markdown, and text in the application process with permissive decoding. | No parser sandbox, egress denial, or narrow format matrix exists. |
| Downstream bypass | `backend/app/api/routes/prep_routes.py:263-355` reads stored extracted text and includes it in a Celery payload; `backend/app/tasks/simulation_tasks.py:270-280,368-383` forwards it to preparation. | Unreviewed text can influence later work and leak into broker payloads. |
| Provenance bypass | `backend/app/services/simulation_manager.py:719-757` labels the first 12,000 characters of unreviewed text as `SOURCE_EXTRACTED`. | The CURRENT label overstates review and origin. |
| Persistence | `backend/app/models/project.py:36-63` stores an untyped `files` list; `backend/app/db/schema.py:8-62` has no source-version, segment, candidate, review-event, outbox, or deletion aggregate. | Review and deletion cannot be made durable or auditable. |
| Deletion | `backend/app/models/project.py:302-327` records an event and immediately calls `shutil.rmtree`. | Provider, cache, index, object-version, and backup status are not represented. |
| URL path | `backend/app/api/sources.py:20-92` fetches URLs without project/workspace scope; `backend/app/services/url_fetcher.py:46-149,272-318,349-402` can call Firecrawl/Jina and write fetched text. | The route is disconnected from the review aggregate and external responses are not consistently bounded. |
| Frontend URL path | `frontend/src/views/Home.vue:629-693` replaces fetched content with a file containing only the source URL. | The UI reports a source that the upload path did not actually receive. |
| Limits | `backend/app/config.py:203-215`, `backend/app/utils/input_policy.py:19-21`, and `frontend/src/views/Home.vue:449-453` disagree about file size/count and supported formats. | The server and UI do not present one enforceable policy. |
| Auth | `backend/app/__init__.py:88-97` checks one application bearer token. | An application token is not organization identity, membership, or resource authorization. |
| Ontology task | `backend/app/tasks/graph_tasks.py:18-46` calls the ontology generator with a shape that differs from `backend/app/services/ontology_generator.py:22-27`; the latter falls back after registry failure at lines 56-85. | The path is both signature-inconsistent and fail-open. |
| Response contract | `backend/app/api/graph.py:369-384` queues work but omits the created `project_id` from the success response. | The CURRENT route cannot provide a reliable server-owned relationship to the new workspace. |
| Schema authority | `backend/migrations/versions/384c98f88d53_initial_schema.py:20-143` creates integer-keyed legacy tables while `backend/app/db/schema.py:8-62` declares a materially different UUID model. | Alembic autogeneration is unsafe until one canonical mapping is approved. |
| Deployment | `Dockerfile.worker` builds a general Celery worker from the application dependency set; `Procfile` starts that general worker. | There is no credential-minimized, no-egress scanner/parser workload. |
| Workspace identity | `backend/app/application/decision_workspace_service.py` persists the Task 3 workspace manifest in the project directory and truthfully reports `storage_status=TRANSITION`. | That identifier is server-owned, but it is not a tenant/authentication boundary or canonical PostgreSQL workspace record. |

## 5. Production blockers

Every item below is a production blocker, not a follow-up enhancement.

| Blocker | Required evidence before production enablement |
|---|---|
| Organization identity and capabilities | The tenant foundation maps an authenticated actor to canonical UUIDv7 organization/workspace memberships and capabilities; every command resolves physical scope from a server-owned public-ID lookup; tests prove cross-tenant reads and writes return non-enumerating failures. The app-wide bearer token is not accepted as this evidence. |
| PostgreSQL authority | The accepted tenant foundation has one reviewed Alembic head and reconciled metadata; Task 4 records that actual head as its parent, then passes empty, sanitized CURRENT, downgrade/re-upgrade, and restored-backup rehearsals. Constraints/RLS are verified, and production startup refuses SQLite when the feature is enabled. |
| Private object storage | Separate quarantine and processed buckets or access points, encryption at rest, public access blocked, server-generated keys, short-lived constrained upload credentials, object-version deletion handling, and credential rotation evidence exist. |
| Transactional outbox | Source state, review event, audit event, and outbox event commit atomically; relay retry and duplicate-delivery tests pass. Celery enqueue after an unrelated filesystem write is not equivalent. |
| Deletion ledger and worker | Every primary, object version, processed derivative, cache/index, provider record, export, and backup obligation has a durable target status; user copy distinguishes confirmed deletion from scheduled expiry. |
| Isolated scanner/parser | A separate workload runs non-root, read-only, without application/provider/object-store secrets, with network denied and enforced CPU/memory/process/file/time limits; deployment-policy and hostile-corpus evidence pass. `Dockerfile.worker` is not sufficient. |
| Scanner operations | Malware definitions have a signed/update process, freshness SLO, stale-definition fail-closed behavior, and alert/runbook coverage. |
| Provider handling | If candidate extraction sends source-derived text to an external model provider, the approved subprocessor, region, retention mode, deletion/age-out behavior, and request/response bounds are recorded. A manual/deterministic extraction mode may avoid this blocker. |
| Observability without content leakage | Metrics and logs use IDs, hashes, versions, byte counts, durations, and bounded codes only; tests prove raw filenames, object keys, source text, excerpts, and model output are absent from ordinary logs and traces. |
| Reconciled normative packet | The architecture, methodology, security, and docs owners land the accepted source-transition and provenance packet described in section 6, the docs validator passes, and the implementation uses that exact contract version. The accepted reconciliation is not executable authority while it exists only in this proposed brief. |
| Release authority | Security reviewer, persistence owner, orchestration owner, privacy owner, and release operator sign the TXT-only evidence packet. |

The domain kernel and ports may land behind the disabled flag before these
blockers are complete. Their existence must not change
`source_review=UNAVAILABLE`, expose a production route, or support a security
claim.

## 6. Reconciled authority packet and remaining prerequisites

Authority commit `ce132a5` landed the reconciled source state machine,
`epistemic-ledger/v2`, tenancy relationship, and release gates in the normative
documents; `python tools/validate_docs.py` passes on the integration branch.
Domain commit `54ade9c` implements the exact v2 vocabulary and closed triple
matrix. The former normative ambiguity is resolved. Named Architecture,
Security, Privacy, Persistence, and Release approvals and all persistence/
deployment evidence remain open, so domain work remains
`TRANSITION — DOMAIN ONLY` behind the disabled flag and no canonical source
writer or enabled worker is authorized. Do not preserve stale aliases for the
superseded relations or transitions.

### 6.1 Reconciled source state machine

Authority commit `ce132a5` locks this exact closed transition set:

```text
UPLOADING        -> QUARANTINED | FAILED | DELETION_PENDING
QUARANTINED      -> SCANNING | REJECTED | DELETION_PENDING
SCANNING         -> PARSING | REJECTED | FAILED | DELETION_PENDING
PARSING          -> FLAGGED | NEEDS_REVIEW | REJECTED | FAILED | DELETION_PENDING
FLAGGED          -> NEEDS_REVIEW | REJECTED | DELETION_PENDING
NEEDS_REVIEW     -> READY | REJECTED | FLAGGED | DELETION_PENDING
READY            -> DELETION_PENDING
REJECTED         -> DELETION_PENDING
FAILED           -> DELETION_PENDING
DELETION_PENDING -> DELETED
```

There is no other transition. In particular, `FAILED` is an operational
outcome: bounded retries were exhausted or processing could not complete, and
the system makes no source-policy judgment. `REJECTED` is a policy/security or
authorized-review outcome: the system completed enough inspection to reject
the source from use. Error handlers may not interchange the states to make a
test pass.

Every state except `DELETION_PENDING` and `DELETED` may enter
`DELETION_PENDING`. A repeated request using the original idempotency key
replays its receipt. A different deletion command against
`DELETION_PENDING` or `DELETED` does not invent a self-transition.

### 6.2 Reconciled provenance vocabulary

`EXTRACTED_FROM` already exists in the CURRENT TRANSITION domain vocabulary.
Do not add a duplicate or compatibility alias. Once the normative packet
lands, it additionally authorizes:

```text
role: EXTRACTION_CANDIDATE
relation: ACCEPTED_AS
relation: REVISED_AS
relation replacement: SOURCE_SEGMENT INFORMS STARTING_CONDITION
```

The earlier source-to-condition relation is retired for new writes; `INFORMS`
is not a support/evidence claim. The accepted packet must retain the ban on
direct or transitive source-to-possible-path/source-to-consideration support.

The same repository-wide provenance dependency uses the non-validating
direction:

```text
CONSIDERATION PRODUCES_QUESTION VALIDATION_QUESTION
```

Questions are research handoff prompts produced from a consideration; their
existence does not validate a path. Task 4 does not persist path/question
edges, but its closed ledger dependency and regression fixtures must use the
reconciled triple so a path-to-question validation meaning cannot return
through a shared enum.

The v2 pure validator may be consumed by the disabled module. No new canonical
provenance edge may be written until tenant persistence, source review, and the
named approval gates are complete.

### 6.3 Tenant foundation and actual-head migration

The CURRENT ORM and initial migration describe incompatible schemas. Task 4
does not select between them or create organizations/workspaces on its own.
The tenant foundation must first land canonical UUIDv7 organizations,
workspaces, memberships, capabilities, composite tenant foreign keys, forced
RLS, audit/outbox infrastructure, and reconciled metadata.

Immediately before creating the Task 4 migration:

1. run `alembic heads`; require exactly one head;
2. run `alembic current` against disposable production-like PostgreSQL that
   has been upgraded through the accepted tenant foundation;
3. run `alembic check`; require no unowned metadata drift;
4. record the sole head and schema digest in the Task 4 report;
5. create the source-ingestion revision with `down_revision` equal to that
   exact recorded head, never a value copied from this brief;
6. inspect every generated operation and remove unrelated drift;
7. run upgrade, downgrade to the recorded parent, and re-upgrade;
8. repeat against a restored production-like backup fixture.

At audit time the root revision is
`384c98f88d53_initial_schema.py`; it must not be frozen as Task 4's parent.
Multiple heads, an unexpected parent, an absent tenant foundation, or unrelated
autogenerate changes stop the checkpoint.

### 6.4 Task 3 workspace identity is not tenant identity

The TRANSITION filesystem `workspace_manifest.json` is stable identity
metadata. It cannot establish organization membership, actor capabilities,
query scope, or RLS. A canonical workspace record and authenticated membership
mapping are required before production enablement. Do not infer
`organization_id` from a client workspace ID.

## 7. Fixed format and resource matrix

The server owns this matrix and returns it from the capabilities endpoint. The
frontend does not hard-code it.

| Input | First enabled slice | Required behavior |
|---|---:|---|
| `.txt`, declared `text/plain`, canonical UTF-8 without BOM | ENABLED only after all TXT gates pass | Direct upload, byte/hash verification, malware scan, strict decode, deterministic normalization/segmentation, injection-risk screen, review. |
| PDF | UNAVAILABLE | Reject with stable `source_format_unavailable`. A later checkpoint requires signature/MIME verification, encrypted/object/page/decompression limits, isolated parsing, no egress, malformed/encrypted/polyglot corpus evidence, and security approval. |
| Markdown / `.md` | UNAVAILABLE | Reject. It is not treated as plain text because links, embedded HTML, and active-looking instructions require their own policy and corpus. |
| DOCX, HTML, CSV, URL, OCR, images, archives | UNAVAILABLE | Reject or return capability unavailable; do not silently convert or fetch. |
| Executables, scripts, encrypted files, polyglots, NUL-containing/binary text | REJECTED | No parser invocation and no user-facing download route. |

TXT launch limits use the authoritative configurable baseline from
`docs/security/SOURCE_INGESTION.md`:

```text
max_file_bytes                 25 MiB
max_source_versions_per_decision 20
max_decision_source_bytes      100 MiB
max_normalized_tokens_per_version 50,000
parser_cpu_seconds             30
upload_intent_ttl_seconds      600
```

The raw object hash is SHA-256 over uploaded bytes. Strict TXT processing:

1. require the exact server-issued object key and declared byte length;
2. require the provider checksum and independently streamed SHA-256 to match;
3. reject BOM, NUL, invalid UTF-8, disallowed control characters, and bytes
   beyond the limit;
4. retain the raw hash, then normalize CRLF/CR to LF and Unicode to NFC;
5. compute a separate normalized-text hash;
6. tokenize with the versioned production tokenizer and reject over-limit
   input;
7. create deterministic line-aware segments without splitting a Unicode code
   point;
8. store raw and normalized content in different private scopes.

Offsets and line numbers always refer to the normalized UTF-8 text. Review UI
must disclose that normalization without suggesting the source was validated.

## 8. Domain contracts

Extend the landed repository-wide UUIDv7/public-ID contract in
`backend/app/domain/identifiers.py`, then create
`backend/app/domain/source_ingestion.py` for the source aggregate. Models are
Pydantic v2 frozen, strict, and
`extra="forbid"`; commands are immutable dataclasses or equivalent strict
models.

Every relational row has an application-issued RFC 9562 UUIDv7 physical `id`
stored in PostgreSQL `uuid`. Physical IDs never leave the repository adapter.
UUIDv4, truncated UUIDs, integers, provider/model IDs, and client-selected IDs
are forbidden for new canonical rows. Python runtimes without `uuid.uuid7`
must use one small audited RFC 9562 helper or one pinned reviewed dependency;
tests inspect UUID version and RFC variant bits.

Every externally addressable source object also has a separately generated,
stable public ID: a fixed prefix plus 32 lowercase UUIDv7 hexadecimal
characters. The UUIDv7 encoded in a public ID is not the physical row ID.
Requests may reference a public ID but may never choose one during creation:

```text
src_[0-9a-f]{32}     source
srcv_[0-9a-f]{32}    source version
seg_[0-9a-f]{32}     source segment
cand_[0-9a-f]{32}    extraction candidate
cond_[0-9a-f]{32}    accepted starting condition
sflag_[0-9a-f]{32}   review/security flag
srev_[0-9a-f]{32}    review event
del_[0-9a-f]{32}     deletion request
```

Public and physical IDs are generated by separate calls. A public ID is stable
for the logical object; an immutable replacement version receives its own
version public ID. Display labels and source filenames are neither identity.

Use the landed shared `new_uuid7()` and
`new_public_id(kind, physical_id, *, uuid7_factory=None)` factories. Extend
`PublicIdKind` and its closed prefix map with exactly the eight source kinds;
do not create a second identifier factory or a competing UUID helper:

```python
PublicIdKind += Literal[
    "source",
    "source_version",
    "source_segment",
    "source_candidate",
    "starting_condition",
    "source_flag",
    "source_review",
    "deletion_request",
]
```

`new_public_id` receives the physical UUIDv7 only to reject and bounded-retry
an equality collision. It creates a fresh UUIDv7 with the injected factory,
verifies version/variant, removes hyphens, and prepends the kind-owned prefix;
it never formats, derives from, or returns the physical ID. Tests inject
deterministic clock/randomness seams; production randomness is cryptographic.

### 8.1 Enums

```python
class SourceIngestionState(str, Enum):
    UPLOADING = "UPLOADING"
    QUARANTINED = "QUARANTINED"
    SCANNING = "SCANNING"
    PARSING = "PARSING"
    FLAGGED = "FLAGGED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY = "READY"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    DELETION_PENDING = "DELETION_PENDING"
    DELETED = "DELETED"

class CandidateDisposition(str, Enum):
    PENDING = "PENDING"
    ACCEPTED_SOURCE_CONDITION = "ACCEPTED_SOURCE_CONDITION"
    REVISED_USER_CONDITION = "REVISED_USER_CONDITION"
    EXCLUDED = "EXCLUDED"
    REPORTED_SUSPICIOUS = "REPORTED_SUSPICIOUS"

TERMINAL_REVIEW_DISPOSITIONS = frozenset({
    CandidateDisposition.ACCEPTED_SOURCE_CONDITION,
    CandidateDisposition.REVISED_USER_CONDITION,
    CandidateDisposition.EXCLUDED,
})

class ReviewFlagDisposition(str, Enum):
    OPEN = "OPEN"
    RELEASED = "RELEASED"
    REJECTED = "REJECTED"

class SourceProcessingStage(str, Enum):
    SCAN = "SCAN"
    PARSE = "PARSE"
    EXTRACT = "EXTRACT"

class SourceAttemptState(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    CANCELLED = "CANCELLED"

class DeletionTargetKind(str, Enum):
    PRIMARY_DATABASE = "PRIMARY_DATABASE"
    QUARANTINE_OBJECT = "QUARANTINE_OBJECT"
    PROCESSED_OBJECT = "PROCESSED_OBJECT"
    OBJECT_VERSIONS = "OBJECT_VERSIONS"
    DERIVED_INDEX = "DERIVED_INDEX"
    CACHE = "CACHE"
    EXPORT = "EXPORT"
    PROVIDER_RECORD = "PROVIDER_RECORD"
    BACKUP_EXPIRY = "BACKUP_EXPIRY"

class DeletionTargetState(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    SCHEDULED_AGE_OUT = "SCHEDULED_AGE_OUT"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    LEGAL_HOLD = "LEGAL_HOLD"
```

`ReviewFlagDisposition.REJECTED` is written only in the same command
transaction that performs `FLAGGED -> REJECTED`. It is not a substitute for a
source transition and cannot be set while leaving the version `FLAGGED`.

### 8.2 Aggregates and records

```text
Source
  id
  public_id
  organization_id
  workspace_id
  project_id
  display_name
  current_version_id | null
  version
  created_by_actor_id
  created_at
  updated_at

SourceVersion
  id
  public_id
  source_id
  organization_id
  workspace_id
  project_id
  version_number
  state
  original_filename_display
  declared_media_type
  detected_media_type | null
  raw_object_ref | null
  processed_object_ref | null
  raw_byte_length | null
  raw_sha256 | null
  normalized_byte_length | null
  normalized_sha256 | null
  normalized_token_count | null
  scanner_name/version/definitions_version | null
  parser_name/version/policy_version | null
  extraction_prompt_id/version | null
  extraction_schema_id/version | null
  extraction_model_release_id | null
  processing_fence
  deletion_fence
  version
  created_by_actor_id
  created_at
  updated_at

SourceSegment
  id
  public_id
  source_version_id
  organization_id
  workspace_id
  project_id
  ordinal
  normalized_start_byte
  normalized_end_byte
  start_line
  end_line
  segment_sha256
  created_at

CandidateStartingCondition
  id
  public_id
  source_version_id
  source_segment_id
  organization_id
  workspace_id
  project_id
  ordinal
  proposed_statement
  proposed_statement_sha256
  extraction_origin = SYNTHETIC_GENERATED
  disposition
  disposition_reason_code | null
  disposition_reason_note | null
  disposed_by_actor_id | null
  disposed_at | null
  version

StartingCondition
  id
  public_id
  organization_id
  workspace_id
  project_id
  statement
  statement_sha256
  origin = SOURCE_EXTRACTED | USER_STATED
  source_version_id
  source_segment_id | null
  candidate_id
  created_by_actor_id
  created_at

SourceReviewFlag
  id
  public_id
  source_version_id
  candidate_id | null
  organization_id
  workspace_id
  project_id
  flag_code
  severity
  disposition
  detected_by
  disposition_reason_code | null
  disposed_by_actor_id | null
  disposed_at | null
  created_at
  version

SourceReviewEvent
  id
  public_id
  source_version_id
  organization_id
  workspace_id
  project_id
  command_name
  from_state | null
  to_state | null
  actor_type
  actor_id
  capability
  expected_version
  resulting_version
  idempotency_key
  request_body_sha256
  reason_code
  reason_note | null
  request_id
  occurred_at

SourceProcessingAttempt
  id
  source_version_id
  organization_id
  workspace_id
  project_id
  stage
  attempt_number
  state
  lease_owner | null
  lease_expires_at | null
  last_heartbeat_at | null
  fencing_token
  deletion_fence_at_claim
  retry_class | null
  error_code | null
  created_at
  started_at | null
  finished_at | null

DeletionRequest
  id
  public_id
  source_version_id
  organization_id
  workspace_id
  project_id
  requested_by_actor_id
  reason_code
  requested_at
  completed_at | null
  version

DeletionTargetStatus
  deletion_request_id
  target_kind
  target_ref_hash
  state
  provider_receipt_ref | null
  attempt_count
  last_error_code | null
  next_attempt_at | null
  confirmed_at | null
  scheduled_expiry_at | null
  version
```

Raw object references and provider receipts are opaque encrypted references.
They never appear in ordinary API responses, Celery payloads, logs, or audit
notes. Every `id` above is a UUIDv7 physical ID; every `public_id` is the
separately generated prefixed UUIDv7 identifier used by routes and responses.
Foreign keys and RLS predicates use physical IDs only after a scoped public-ID
lookup. `SourceProcessingAttempt` is a non-addressable worker record and has no
public ID. `DeletionTargetStatus` is also non-addressable and may use its
documented composite primary key.

### 8.3 Source transition contract

`transition_source_version(current, target, command)` validates the closed set
in section 6.1. The cartesian complement fails with
`SourceTransitionViolation("source_transition_forbidden")`. No route,
repository, worker, fixture, or admin helper may write `state` directly.

State guards:

| Transition | Required guard |
|---|---|
| `UPLOADING -> QUARANTINED` | exact object key exists; length and SHA-256 match intent; object is private; upload intent not expired; declared format is currently enabled. |
| `UPLOADING -> FAILED` | upload protocol or storage processing did not complete after bounded policy: expired/missing/truncated object, checksum handshake mismatch, or provider completion failure. Store an operational reason code and make no source-content policy judgment. |
| `QUARANTINED -> SCANNING` | worker lease/fencing check succeeds; scanner definitions meet freshness policy. |
| `QUARANTINED -> REJECTED` | verified byte size, declared/detected format, object policy, or pre-scan content-admission policy fails. Request authentication/authorization failure rejects the command without mutating source state. |
| `SCANNING -> PARSING` | malware result clean; scanner receipt/version stored; limits still pass. |
| `SCANNING -> REJECTED` | malware, binary/polyglot, archive, or scanner policy rejection. |
| `SCANNING -> FAILED` | scanner is unavailable, stale, times out, crashes, or returns an invalid receipt after its bounded retry policy; store only an operational reason code and no clean/rejected verdict. |
| `PARSING -> FLAGGED` | normalized artifact and segments are durable; at least one unresolved injection/ambiguity flag exists; untrusted content has not triggered a tool. |
| `PARSING -> NEEDS_REVIEW` | strict parse and bounded candidate extraction succeed; normalized artifact, segments, candidates, prompt/model/schema records, and hashes are durable; no open parsing flag exists. |
| `PARSING -> REJECTED` | strict UTF-8, binary/content, normalization, token, or another allowlisted source-content policy rejects the source; store the exact bounded policy code. |
| `PARSING -> FAILED` | isolated parser or approved extraction dependency is unavailable, times out, crashes, produces an invalid manifest/schema/reference, or exhausts retry without producing a source-policy verdict; no candidate is accepted. |
| `FLAGGED -> NEEDS_REVIEW` | named authorized reviewer released every flag; candidate extraction then passed strict schema and reference checks; release and extraction events are durable. |
| `FLAGGED -> REJECTED` | named authorized reviewer records the source-level security/policy rejection and every open flag receives `REJECTED` in the same transaction. |
| `NEEDS_REVIEW -> READY` | every candidate has a terminal disposition; every flag is released; every accepted/revised record and provenance edge is durable; zero accepted candidates is allowed. |
| `NEEDS_REVIEW -> REJECTED` | authorized rejection reason is recorded; no READY artifact is created. |
| `NEEDS_REVIEW -> FLAGGED` | a suspicious-candidate report creates an `OPEN` flag, invalidates any incomplete finalization receipt, and records the reporting event in the same transaction. |
| Any state other than `DELETION_PENDING` or `DELETED` to `DELETION_PENDING` | deletion request, deletion fence, upload-intent revocation, queued-work cancellation, and complete target inventory commit atomically. Late worker output remains unaccepted/quarantined and cannot advance state. |
| `DELETION_PENDING -> DELETED` | primary content is confirmed absent and every other target is `CONFIRMED`, `NOT_APPLICABLE`, or truthfully `SCHEDULED_AGE_OUT` with disclosed expiry; no target is `FAILED`, `IN_PROGRESS`, `PENDING`, or `LEGAL_HOLD`. |

`READY` means “reviewed for use as starting conditions,” never “source is true,”
“path is validated,” or “claim is verified.”

### 8.4 Candidate disposition semantics

- `ACCEPTED_SOURCE_CONDITION` creates an immutable `StartingCondition` with
  origin `SOURCE_EXTRACTED`. The stored statement must byte-match the
  candidate statement after the same canonical normalization; equality is
  enforced by hash, not a client assertion.
- `REVISED_USER_CONDITION` requires a non-identical bounded statement and
  creates a `StartingCondition` with origin `USER_STATED`. The prior candidate
  and segment remain linked, but the user revision is never relabeled as
  source-extracted.
- `EXCLUDED` creates no starting condition.
- `REPORTED_SUSPICIOUS` creates an open flag, creates no starting condition,
  and atomically transitions `NEEDS_REVIEW -> FLAGGED`. An authorized reviewer
  either releases the flag, reopens the candidate as `PENDING`, and transitions
  `FLAGGED -> NEEDS_REVIEW`, or rejects the whole source with
  `FLAGGED -> REJECTED`.
- Dispositions are immutable events. A changed disposition creates a new
  candidate revision/review event and supersedes the prior current
  disposition; history is never overwritten.
- Zero accepted/revised candidates is a valid completed review. The source can
  be `READY` while contributing no starting conditions; UI copy must state
  that outcome plainly.

### 8.5 Provenance semantics

The landed v2 authority and domain allowlist use these source-review edges.
`EXTRACTED_FROM` predates the packet; its candidate triple is now authorized:

```text
SOURCE_ASSET        CONTAINS       SOURCE_SEGMENT
EXTRACTION_CANDIDATE EXTRACTED_FROM SOURCE_SEGMENT
EXTRACTION_CANDIDATE ACCEPTED_AS    STARTING_CONDITION
EXTRACTION_CANDIDATE REVISED_AS     STARTING_CONDITION
SOURCE_SEGMENT      INFORMS         STARTING_CONDITION  # unchanged acceptance only
```

Required origin rules:

```text
candidate                    SYNTHETIC_GENERATED
unchanged accepted condition SOURCE_EXTRACTED
edited condition             USER_STATED
```

`REVISED_AS` preserves traceability to what the user saw without claiming the
source informs the edited statement. No `SOURCE_SEGMENT INFORMS
STARTING_CONDITION` edge is created for a user revision. Direct or transitive
code that presents a source as support for a possible path remains forbidden.
The shared dependency contract also permits `CONSIDERATION PRODUCES_QUESTION
VALIDATION_QUESTION` and forbids any path-to-question validation relation;
Task 4 regression tests protect that meaning even though this slice does not
write path/question edges.

## 9. Command contract

Every mutation is a command. Routes parse transport input, derive identity and
scope, then call an application service. Workers use a service actor with a
narrow capability. Repositories reject writes without a command context.

```python
class CommandContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    actor_type: Literal["USER", "SERVICE", "SECURITY_REVIEWER", "DELETION_WORKER"]
    actor_id: UUID7
    organization_id: UUID7
    workspace_id: UUID7
    project_id: UUID7
    capabilities: frozenset[str]
    expected_version: int
    idempotency_key: str
    reason_code: str
    reason_note: str | None
    request_id: UUID7
    occurred_at: datetime
```

`actor_type`, `actor_id`, scope, capabilities, `request_id`, and
`occurred_at` are server-derived. The client supplies `expected_version`, an
`Idempotency-Key` header, and an allowlisted reason code/note where the command
requires human intent. Unknown or client-supplied actor/scope/time fields fail
with `422 command_field_forbidden`.

Required commands:

| Command | Capability | State effect |
|---|---|---|
| `create_source_upload_intent` | `sources:write` | Creates Source and SourceVersion in `UPLOADING`. |
| `complete_source_upload` | `sources:write` | `UPLOADING -> QUARANTINED`; emits scan work. |
| `fail_source_upload` | `sources:process` | Operational upload-protocol failure performs `UPLOADING -> FAILED`; it records no source-policy verdict. |
| `begin_source_scan` | `sources:scan` | `QUARANTINED -> SCANNING`. |
| `record_source_quarantine_rejection` | `sources:scan` | Policy/security rejection performs `QUARANTINED -> REJECTED`. |
| `record_source_scan_rejection` | `sources:scan` | `SCANNING -> REJECTED`. |
| `record_source_scan_failure` | `sources:scan` | Operational exhaustion performs `SCANNING -> FAILED`; it records no clean/rejected verdict. |
| `record_source_scan_pass` | `sources:scan` | `SCANNING -> PARSING`; emits parse work. |
| `record_source_parse_flagged` | `sources:parse` | `PARSING -> FLAGGED`. |
| `record_source_parse_reviewable` | `sources:parse` | `PARSING -> NEEDS_REVIEW`. |
| `record_source_parse_rejection` | `sources:parse` | A source-content policy verdict performs `PARSING -> REJECTED`. |
| `record_source_parse_failure` | `sources:parse` | Operational or invalid parser/extractor output exhaustion performs `PARSING -> FAILED`; it records no source-policy verdict. |
| `authorize_source_flag_release` | `sources:security_review` | Records named release and emits bounded extraction work; state remains `FLAGGED`. |
| `complete_source_flag_release` | `sources:parse` | `FLAGGED -> NEEDS_REVIEW`. |
| `reject_flagged_source` | `sources:security_review` | Marks open flags rejected and performs `FLAGGED -> REJECTED` atomically. |
| `accept_source_candidate` | `sources:review` | Candidate disposition and unchanged starting condition; state remains `NEEDS_REVIEW`. |
| `revise_source_candidate` | `sources:review` | Candidate disposition and user-stated starting condition; state remains `NEEDS_REVIEW`. |
| `exclude_source_candidate` | `sources:review` | Candidate disposition only; state remains `NEEDS_REVIEW`. |
| `report_source_candidate_suspicious` | `sources:review` | Opens a flag and performs `NEEDS_REVIEW -> FLAGGED` atomically. |
| `release_review_reported_flag` | `sources:security_review` | Releases the flag, resets its candidate to `PENDING`, and performs `FLAGGED -> NEEDS_REVIEW`. |
| `finalize_source_review` | `sources:review` | `NEEDS_REVIEW -> READY` after guards. |
| `reject_source_review` | `sources:review` | `NEEDS_REVIEW -> REJECTED`. |
| `request_source_deletion` | `sources:delete` | Any state except `DELETION_PENDING`/`DELETED` -> `DELETION_PENDING`; advances the deletion fence, revokes/cancels active work, and creates the complete target inventory atomically. |
| `record_deletion_target_result` | `sources:delete:service` | Updates one target with fencing/version check. |
| `complete_source_deletion` | `sources:delete:service` | `DELETION_PENDING -> DELETED` after guards. |

All command writes use optimistic concurrency:

```sql
UPDATE source_versions
SET state = :target, version = version + 1, updated_at = :now
WHERE id = :id
  AND organization_id = :organization_id
  AND workspace_id = :workspace_id
  AND version = :expected_version;
```

Zero rows yields `409 source_version_conflict`; the response returns no record
from another tenant.

Idempotency is unique on
`(organization_id, workspace_id, command_name, idempotency_key)`. Reuse with the same
canonical request hash returns the stored result. Reuse with another hash
returns `409 idempotency_key_conflict`. Source state, domain/review event,
audit event, idempotency result, and outbox event commit in one PostgreSQL
transaction.

## 10. Persistence and migration contract

### 10.1 Canonical tables

Only after the tenant foundation and the actual-head procedure in section 6.3
pass, add a reviewed manual Alembic migration for:

```text
sources
source_versions
source_segments
candidate_starting_conditions
starting_conditions
source_review_flags
source_review_events
source_processing_attempts
deletion_requests
deletion_target_statuses
```

The tenant foundation already owns `organizations`, `workspaces`,
`workspace_memberships`, `command_idempotency`, `outbox_events`,
`audit_events`, `epistemic_assertions`, and `epistemic_edges`. Task 4 extends
those canonical services/registries; it does not create shadow tenancy,
outbox, audit, or `provenance_edges` tables.

Every Task 4 table except global lookup tables contains immutable
`organization_id`, `workspace_id`, and `project_id` UUIDv7 foreign keys. Every
row physical `id` is UUIDv7. Public IDs are separately generated UUIDv7-based
values and unique within organization/workspace scope. Timestamps are
`TIMESTAMPTZ`; hashes are lowercase 64-character hex with database checks;
state/role/relation/disposition values have database checks; `version` is
positive `BIGINT`. Composite foreign keys carry tenant scope so a child cannot
reference an otherwise valid parent from another organization/workspace.

Required uniqueness and foreign-key rules include:

```text
source_versions(source_id, version_number) UNIQUE
source_segments(source_version_id, ordinal) UNIQUE
candidate_starting_conditions(source_version_id, ordinal) UNIQUE
starting_conditions(candidate_id) UNIQUE
source_review_events(source_version_id, resulting_version) UNIQUE
source_processing_attempts(source_version_id, stage, attempt_number) UNIQUE
command_idempotency(organization_id, workspace_id, command_name, idempotency_key) UNIQUE
outbox_events(event_id) UNIQUE
deletion_target_statuses(deletion_request_id, target_kind, target_ref_hash) UNIQUE
each externally addressable table(organization_id, workspace_id, public_id) UNIQUE
```

No source record is hard-deleted before deletion evidence is retained under the
privacy retention contract. Content columns and object references are cleared
or cryptographically erased as applicable; the minimal non-content deletion
ledger remains.

### 10.2 Row-level isolation

Enable and force PostgreSQL RLS on every scoped table. Each transaction sets
server-derived local settings for organization, workspace, and actor. Policies
require both organization and workspace equality. Application repositories
also include the same predicates; RLS is defense in depth, not the only check.

The outbox relay and deletion worker use dedicated database roles with narrowly
reviewed policies. They may not impersonate arbitrary request identity.
Connection-pool tests must prove local settings do not leak between requests.

### 10.3 Object storage

Use private, non-user-controlled keys:

```text
{environment}/org/{org_public_id}/workspace/{workspace_public_id}/
project/{project_public_id}/source/{source_public_id}/
version/{source_version_public_id}/quarantine/original

{environment}/org/{org_public_id}/workspace/{workspace_public_id}/
project/{project_public_id}/source/{source_public_id}/
version/{source_version_public_id}/processed/normalized.txt
```

The original filename is display metadata only. It is sanitized, bounded, and
never used in a filesystem/object key, response header, log field, or path.

Credential separation:

- API: create one exact-key, short-lived upload form; may `HEAD` that key; no
  list/read/delete.
- Scanner coordinator: read quarantine object and write only an ephemeral
  input volume; no processed write.
- Parser coordinator: read released ephemeral input, write processed object;
  no bucket listing or deletion.
- Review service: range-read processed text in authorized scope only.
- Deletion worker: delete exact ledger targets and object versions; no general
  application access.

Quarantined objects are never served from the product domain. Processed source
text has an authenticated, scope-checked review endpoint only; there is no
generic download URL.

## 11. Application ports and services

Create these ports under `backend/app/application/ports/`:

```python
class RequestIdentityPort(Protocol):
    def current_actor(self) -> AuthenticatedActor: ...

class SourceRepository(Protocol):
    def transact(self, command: SourceCommand) -> CommandResult: ...
    def get_scoped(self, scope: Scope, source_version_id: str) -> SourceVersion: ...

class QuarantineObjectStore(Protocol):
    def create_direct_upload(self, intent: UploadIntent) -> DirectUploadForm: ...
    def stat_exact(self, object_ref: OpaqueObjectRef) -> ObjectStat: ...

class ProcessedObjectStore(Protocol):
    def put_normalized(self, ref: OpaqueObjectRef, stream: BinaryIO) -> ObjectStat: ...
    def read_range(self, ref: OpaqueObjectRef, start: int, end: int) -> bytes: ...

class ScannerPort(Protocol):
    def scan(self, input_ref: EphemeralInputRef, policy: ScanPolicy) -> ScanReceipt: ...

class TxtParserPort(Protocol):
    def parse(self, input_ref: EphemeralInputRef, policy: TxtPolicy) -> ParseManifest: ...

class CandidateExtractorPort(Protocol):
    def extract(self, segments: tuple[BoundedSegmentInput, ...], release: ModelRelease) -> CandidateManifest: ...

class OutboxRepository(Protocol): ...
class AuditRepository(Protocol): ...
class DeletionAdapter(Protocol): ...
```

Create application services under `backend/app/application/source_ingestion/`:

```text
SourceCommandService
SourceQueryService
UploadIntentService
SourceProcessingCoordinator
SourceReviewService
SourceReadinessPolicy
SourceDeletionService
```

Services own authorization, state guards, idempotency, provenance validation,
transactions, and stable errors. Adapters own Flask, SQLAlchemy, object-store,
scanner, parser, model-provider, and Celery details. The domain imports none of
those adapters.

Candidate extraction rules:

- source text is an explicitly delimited untrusted data field, never a system
  or developer message;
- the stage has no tools, URL access, code execution, retrieval, or dynamic
  prompt selection;
- only bounded segment IDs and text enter the stage;
- output uses one strict, versioned JSON Schema with unknown fields rejected;
- every candidate cites an allowed input segment ID;
- no hidden reasoning is requested or stored;
- no confidence/probability/validation score is generated;
- registry, model, schema, or validator failure is terminal for the work
  attempt; there is no direct-prompt fallback;
- broker and outbox messages contain IDs and hashes, never raw source text;
- provider response bodies and source excerpts are absent from normal logs.

## 12. Worker and isolation contract

### 12.1 Event chain

The transactional outbox emits only bounded identifiers:

```text
source.upload.completed.v1
source.scan.requested.v1
source.parse.requested.v1
source.flag.release_authorized.v1
source.deletion.requested.v1
```

An outbox relay publishes after commit. Consumers are at-least-once and call
idempotent commands. Every attempt has attempt ID, lease owner, lease expiry,
fencing token, heartbeat, retry class, bounded error code, and timestamps.
Claiming an attempt atomically increments `SourceVersion.processing_fence` and
copies that value plus the current `deletion_fence` into the attempt. Every
heartbeat, artifact registration, receipt, and state command compares attempt
ID, lease owner, processing fence, and deletion fence. Stale fencing tokens or
a changed deletion fence cannot write a state or accepted artifact.

Retry closes the immutable attempt and creates attempt N+1; it never reuses an
attempt row. Only bounded retry exhaustion may issue a source-version
operational `FAILED` command. A content-policy verdict issues `REJECTED`
without consuming retries intended for dependency failures. Requesting
deletion atomically increments `deletion_fence`, revokes the upload intent,
cancels ready/running attempts, and makes every late output unaccepted.

No Flask route scans, parses, launches a container, calls a model, or waits for
processing. A route returns after the command transaction and outbox row commit.

### 12.2 Deployment units

Add distinct deployment artifacts; do not reuse `Dockerfile.worker`:

```text
backend/Dockerfile.source-coordinator
backend/Dockerfile.source-scanner
backend/Dockerfile.txt-parser
deploy/source-ingestion/compose.test.yml
deploy/source-ingestion/network-policy.yml
```

The production topology is:

```text
web API -> PostgreSQL/outbox/object-control plane
outbox relay -> broker
source coordinator -> ephemeral job creation + exact object transfer
scanner sandbox -> ephemeral read-only input, receipt output
TXT parser sandbox -> ephemeral read-only input, manifest/normalized output
review API -> processed object range reads
deletion worker -> exact ledger targets
```

The coordinator streams one exact quarantine object into an ephemeral volume
before the sandbox starts. The sandbox has no object-store credential and no
network. Output leaves through a separate bounded ephemeral volume and is
validated by the coordinator before persistence.

### 12.3 Minimum sandbox controls

Both scanner and parser workloads require:

```text
runAsNonRoot: true
runAsUser: 10001
readOnlyRootFilesystem: true
allowPrivilegeEscalation: false
capabilities.drop: [ALL]
seccompProfile: RuntimeDefault
network: none / default-deny NetworkPolicy with no egress
pidsLimit: 64
memory: 512 MiB
cpu: 1
nofile: 256
wall clock: 30 seconds
ephemeral input: read-only
ephemeral output: 16 MiB maximum
no app, database, broker, object-store, or model-provider secrets
```

The deployment test must prove network denial with a real connection attempt,
secret absence by enumerating the container environment names, read-only root
behavior, non-root identity, and resource termination. A manifest review alone
is insufficient.

Scanner definition age beyond policy returns a stable unavailable result and
does not advance from `QUARANTINED`; the coordinator retries without claiming
a scan lease, alerts on the freshness SLO, and still permits deletion. Once a
fresh scanner begins work, operational exhaustion is
`SCANNING -> FAILED`, while a source-policy verdict is
`SCANNING -> REJECTED`. Production startup/health admission refuses stale
definitions rather than calling a source rejected.

## 13. Public API

Register a new `backend/app/api/routes/source_review_routes.py` from
`backend/app/api/routes/__init__.py`. Do not add handlers to
`backend/app/api/simulation.py` and do not reuse `backend/app/api/graph.py` for
the new path.

### 13.1 Capabilities

```text
GET /api/simulation/source-ingestion/capabilities
```

Returns the enabled matrix, limits, feature status, policy version, and truth
copy. It does not return storage/provider details.

```json
{
  "success": true,
  "data": {
    "status": "PARTIAL",
    "policy_version": "source-ingestion/txt-v1",
    "enabled_formats": [
      {"extension": ".txt", "media_type": "text/plain", "encoding": "UTF-8"}
    ],
    "unavailable_formats": ["pdf", "markdown", "docx", "html", "csv", "url", "ocr", "image", "archive"],
    "limits": {
      "max_file_bytes": 26214400,
      "max_source_versions_per_decision": 20,
      "max_decision_source_bytes": 104857600,
      "max_normalized_tokens_per_version": 50000
    },
    "source_role": "starting_conditions_only"
  }
}
```

When the flag is off, `status` is `UNAVAILABLE` and `enabled_formats` is empty.

### 13.2 Upload and status

```text
POST /api/simulation/workspaces/{workspace_id}/projects/{project_id}/sources
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/upload-complete
GET  /api/simulation/projects/{project_id}/sources
GET  /api/simulation/sources/{source_id}/versions/{source_version_id}
```

Create-intent body:

```json
{
  "display_name": "Weekend service notes",
  "filename": "notes.txt",
  "media_type": "text/plain",
  "byte_length": 8421,
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "expected_version": 0,
  "reason_code": "SOURCE_ADDED_FOR_STARTING_CONDITIONS"
}
```

Success is `201` with server IDs, state `UPLOADING`, version, expiry, and a
short-lived direct-upload form constrained to one exact private key, byte
range, media type, and checksum. The exact key may exist only inside the
signed upload URL/form required by the storage provider; it is not returned as
reusable application metadata, logged, or treated as authorization. No
reusable storage credential or listable prefix is returned. The browser
uploads directly to object storage.

Upload completion requires an empty body except `expected_version` and
`reason_code`, plus `Idempotency-Key`. The server performs an exact `HEAD` and
streamed checksum verification, then returns `202`, state `QUARANTINED`, row
version, and a `Location` header for status. It does not parse or enqueue
outside the transactional outbox.

### 13.3 Review

```text
GET  /api/simulation/sources/{source_id}/versions/{source_version_id}/review
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/flags/{flag_id}/release
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/flags/{flag_id}/reject
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/candidates/{candidate_id}/accept
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/candidates/{candidate_id}/revise
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/candidates/{candidate_id}/exclude
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/candidates/{candidate_id}/report
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/review/finalize
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/review/reject
```

Every mutation requires `Idempotency-Key`, `expected_version`, and a bounded
reason code. `revise` also requires `statement`; every other endpoint forbids
it. Scope and actor fields are forbidden in all bodies.

The normal review endpoint withholds normalized text and candidate content
before `NEEDS_REVIEW`. In `FLAGGED`, it returns only bounded flag metadata and
plain status. A separate capability-gated controlled review view may render an
escaped, inert excerpt after recording access; it has no links, tools, active
markup, or generic download.

At `NEEDS_REVIEW`, each candidate returns a bounded statement, exact source
segment/line reference, escaped excerpt, disposition, and version. It does
not return model reasoning, confidence, object references, provider payloads,
or unrelated segments.

Finalize returns `200 READY` only after all guards. Unresolved items return
`409 source_review_incomplete` with counts and stable codes, not source text.
Reporting a suspicious candidate returns the new `FLAGGED` state. The
capability-gated flag release returns to `NEEDS_REVIEW`; flag rejection moves
the entire source version to `REJECTED`. Neither action is a local-only
candidate update.

### 13.4 Deletion

```text
POST /api/simulation/sources/{source_id}/versions/{source_version_id}/deletion
GET  /api/simulation/sources/{source_id}/versions/{source_version_id}/deletion
```

From every state other than `DELETION_PENDING`/`DELETED`, the POST returns `202
DELETION_PENDING` only after the request, deletion fence, active upload/work
revocation, and complete target inventory commit. The GET returns target kinds,
truthful states, attempt timestamps, and scheduled expiry dates. It never
returns internal object/provider references. An idempotent replay returns the
stored receipt; a different command against an already deleting/deleted source
does not create a self-transition.

### 13.5 Stable errors

Use bounded RFC 7807-compatible JSON with stable codes:

```text
400 malformed_request
401 authentication_required
403 source_capability_required
404 source_not_found                 # also used for wrong-tenant IDs
409 source_version_conflict
409 idempotency_key_conflict
409 source_review_incomplete
409 source_state_conflict
413 source_too_large
415 source_format_unavailable
422 source_invalid_utf8
422 source_binary_content_rejected
422 source_checksum_mismatch
422 command_field_forbidden
423 source_flagged
500 source_ingestion_internal_error
503 source_ingestion_unavailable
```

No response contains exception text, traceback, raw filename paths, object
keys, source text outside the authorized review shape, or a clue that a
wrong-tenant source exists.

## 14. Frontend contract

The frontend vertical slice must preserve the approved visual direction while
making source state comprehensible. It is not a generic upload card.

Required behavior:

- fetch the capabilities endpoint before presenting an upload control;
- show TXT/UTF-8 and the active server limits exactly;
- remove the URL field, URL fetch action, and fake URL-backed file behavior
  from `frontend/src/views/Home.vue`;
- remove PDF and Markdown from the file picker while unavailable;
- remove the CURRENT source “precision” scoring implication; the presence of a
  file does not make a decision more precise or supported;
- upload directly using the server-issued form, then call completion;
- show plain-language states for upload, quarantine, scanning, parsing,
  security review, condition review, ready, rejected, failed, deletion, and
  reconnection;
- label `FAILED` as an operational processing failure with retry/support
  guidance and `REJECTED` as a source policy/review outcome; never use the
  labels interchangeably;
- let users accept, revise, exclude, or report each candidate with keyboard and
  screen-reader equivalents;
- show exact line references and inert excerpts, not a general document
  renderer;
- keep Finalize disabled until the server reports no unresolved items;
- on `409`, refetch rather than overwriting another review;
- allow zero accepted conditions and explain that the source contributed none;
- announce status changes without moving focus;
- use non-color status labels, visible focus, 44×44 primary targets, 320px
  reflow, reduced motion, and an error summary linked to controls.

Required truth copy near review:

```text
Source material can shape starting conditions. It does not validate a path or outcome.
```

Do not use green “verified/validated” presentation. `READY` is rendered as
`REVIEW COMPLETE`, with the source-role disclosure adjacent.

Task 3 workspace availability becomes:

```text
ABSENT      no source versions
UNAVAILABLE feature disabled or legacy-only sources
PARTIAL     at least one v1 source is processing, flagged, under review, mixed, or deleting
AVAILABLE   the v1 service is enabled and every selected source version is READY
```

The client never infers `AVAILABLE` from local files or checkboxes.

## 15. Legacy cutover

There is no dual executable source path.

### 15.1 Immediate gates

When `SOURCE_INGESTION_V1_ENABLED` is on:

- `/api/sources/fetch` is unregistered or returns `410
  source_url_ingestion_unavailable` with no fetch attempt;
- `/api/graph/ontology/generate` may not accept or parse new files. Before
  cutover it returns `503 source_ingestion_unavailable`; after migration it
  returns `410 legacy_source_route_removed` with the new entry location;
- `ProjectManager.save_source_file`, `FileParser.extract_text`, and
  `ProjectManager.save_extracted_text` are not reachable from a production
  source route;
- ontology generation cannot use the fail-open direct prompt path;
- `prepare_simulation_task` no longer accepts `document_text`;
- outbox/Celery messages contain scoped IDs and hashes only;
- preparation rehydrates only approved starting-condition and segment IDs
  through the scoped repository;
- `SimulationManager` removes the fabricated `unverified_source_excerpt` input
  and never upgrades legacy text to `SOURCE_EXTRACTED`;
- admission runs before state mutation, cleanup, task creation, or dispatch;
- the worker repeats readiness admission so an internal caller cannot bypass
  the HTTP gate.

### 15.2 Existing source data

Existing `project.files` entries and `extracted_text.txt` are labeled:

```text
LEGACY_UNREVIEWED_SOURCE
READ-ONLY
NON-EXECUTABLE
```

They remain readable only through an explicitly authorized legacy view if the
privacy policy allows it. They are never auto-approved. Migration creates a new
Source/SourceVersion, copies bytes into quarantine under a server-generated
key, and sends them through every enabled check and review. If original bytes
are absent, the record cannot be migrated from extracted text alone.

No-source workflows remain allowed. Users may proceed with explicit
`USER_STATED` conditions and declared assumptions. If a run selects sources,
every selected version must be `READY`; one non-ready source blocks admission.

### 15.3 Cutover proof

Repository and runtime tests must prove there is no production call graph from
upload, graph, preparation, or worker entry points to:

```text
FileParser.extract_text
ProjectManager.save_extracted_text
ProjectManager.get_extracted_text
URLFetcher.fetch_urls
raw document_text Celery arguments
OntologyGenerator direct fallback
```

Static grep alone is supporting evidence; request and worker integration tests
are required.

## 16. Staged delivery checkpoints

Build one vertical slice at a time. Each checkpoint gets an independent
security/architecture review and a recorded rollback. Do not begin a later
checkpoint with a failing earlier gate.

### Checkpoint 4A — disabled domain kernel and authority packet

Files:

```text
backend/app/domain/source_ingestion.py
backend/app/domain/identifiers.py
backend/tests/domain/test_source_ingestion.py
backend/tests/domain/test_identifiers.py
normative source packet files owned and landed by the docs steward, not silently edited by the Task 4 implementer
```

Deliver:

- exact reconciled transition set from section 6.1, with operational `FAILED`
  distinct from policy/review `REJECTED`;
- strict UUIDv7 physical/public identity, enums, aggregates, command context,
  guards, candidate semantics, deletion target types, and
  cartesian-complement transition tests;
- reconciled provenance/state packet submitted and landed by the responsible
  owners before any canonical edge write;
- feature remains disabled and Task 3 reports review `UNAVAILABLE`.

Gate: domain tests pass; the accepted packet is either landed or explicitly
recorded as the blocker that keeps the work `TRANSITION — DOMAIN ONLY`. No
public route or security claim.

### Checkpoint 4B — identity, PostgreSQL, RLS, outbox, and object-store foundation

Files:

```text
backend/app/db/schema.py
backend/migrations/versions/  # create one actual-head child; record its exact path in the Task 4 report
backend/app/application/ports/source_ingestion.py
backend/app/infrastructure/persistence/source_repository.py
backend/app/infrastructure/persistence/outbox_repository.py
backend/app/infrastructure/storage/source_object_store.py
backend/tests/integration/test_source_ingestion_postgres.py
backend/tests/integration/test_source_object_store.py
```

Deliver:

- accepted tenant foundation with UUIDv7 organizations/workspaces/memberships,
  capabilities, composite tenant foreign keys, RLS, audit, idempotency, and
  outbox;
- the section 6.3 actual-head procedure and a non-destructive Task 4 migration
  whose parent is the recorded sole head;
- scoped repository with forced RLS and connection-pool reset;
- transactionally coupled state/event/audit/idempotency/outbox writes;
- exact-key private storage and constrained direct-upload form;
- production config validation that refuses SQLite or missing credentials.

Gate: `alembic heads/current/check`, clean migration, sanitized upgrade,
parent downgrade/re-upgrade, restored-backup rehearsal, schema digest,
cross-tenant matrix, object-store policy tests, and duplicate outbox delivery
tests pass. Feature remains disabled.

### Checkpoint 4C — one TXT upload-to-reviewable backend slice

Files:

```text
backend/app/application/source_ingestion/command_service.py
backend/app/application/source_ingestion/processing_coordinator.py
backend/app/tasks/source_ingestion_tasks.py
backend/app/api/routes/source_review_routes.py
backend/app/api/routes/__init__.py
backend/Dockerfile.source-coordinator
backend/Dockerfile.source-scanner
backend/Dockerfile.txt-parser
deploy/source-ingestion/compose.test.yml
deploy/source-ingestion/network-policy.yml
backend/tests/test_source_ingestion_api.py
backend/tests/tasks/test_source_ingestion_tasks.py
backend/tests/security/test_txt_ingestion_corpus.py
```

Deliver only:

```text
create intent -> direct upload -> completion -> quarantine -> scan ->
strict parse/segment -> candidate extraction -> NEEDS_REVIEW or FLAGGED
```

No review mutation or downstream execution yet. The capabilities endpoint may
show `txt` only in development/test after this checkpoint, with status
`PARTIAL`.

Gate: malicious corpus, no-egress/secret/resource tests, retry/fencing tests,
checksum/limit tests, content-leak tests, and operational failure behavior pass.
Section 6.1 must be resolved before production enablement.

### Checkpoint 4D — review, provenance, and readiness

Files:

```text
backend/app/application/source_ingestion/review_service.py
backend/app/application/source_ingestion/readiness_policy.py
backend/tests/test_source_review_api.py
backend/tests/test_source_review_service.py
backend/tests/test_source_provenance.py
frontend/src/components/source-review/*
frontend/src/__tests__/source-ingestion-review.spec.js
```

Deliver candidate/flag review, immutable disposition history, accepted and
revised condition semantics, zero-accepted completion, `READY` guards, and the
accessible review interface.

Gate: authority-approved provenance vocabulary, exhaustive disposition tests,
optimistic concurrency, idempotency, controlled flag review, truth-copy tests,
keyboard/zoom/mobile/assistive-technology review, and source-to-path negative
tests pass.

### Checkpoint 4E — downstream gate and legacy cutover

Files include the existing graph/preparation/task/manager modules named in
sections 4 and 15, plus focused cutover tests. Changes must remove bypasses; do
not add a second implementation to `backend/app/api/simulation.py`.

Deliver:

- URL and legacy upload routes disabled/removed;
- frontend URL and unavailable-format affordances removed;
- raw text absent from broker payloads;
- preparation and worker admission require selected source versions `READY`;
- legacy records read-only and non-executable;
- no-source reviewed flow remains usable.

Gate: route, application-service, worker, and call-graph tests prove bypasses
closed. Rollback disables new work but never re-enables legacy unreviewed
execution.

### Checkpoint 4F — deletion, operations, and TXT production decision

Files:

```text
backend/app/application/source_ingestion/deletion_service.py
backend/app/tasks/source_deletion_tasks.py
backend/tests/test_source_deletion.py
backend/tests/integration/test_source_deletion_targets.py
docs/security and release status updates with actual file:line evidence
```

Deliver target inventory, exact deletion adapters, retries/fencing, legal-hold
behavior, provider receipts, object-version deletion, backup scheduled-expiry
copy, metrics/alerts/runbook, and the evidence packet.

Gate: every production blocker in section 5 is closed and release acceptance
passes. Only then may production enable TXT and describe the format matrix as
“TXT ingestion controls active.” Do not claim complete or universally secure
source ingestion.

### Later checkpoint — PDF, separately approved

PDF remains off until a new brief and evidence packet cover, at minimum:

- binary signature and MIME agreement, polyglot rejection, encrypted-PDF
  policy, object/page/decompressed/token limits;
- isolated parser image with no network/secrets and a pinned parser release;
- malformed, oversized, encrypted, embedded-file, JavaScript/action, font,
  image-bomb, and parser-crash corpus;
- deterministic page/offset provenance and controlled rendering;
- deletion of raw, parsed, preview, OCR, cache, provider, and backup artifacts;
- independent security review and explicit format-matrix enablement.

Markdown and all other formats require their own checkpoint; PDF acceptance
does not authorize them.

## 17. Strict one-test-at-a-time TDD

This task uses literal one-test-at-a-time red/green/refactor. “Write the test
suite, then implement it” is prohibited.

For each numbered behavior:

1. add exactly one new test;
2. run only that test and record RED for the intended missing behavior;
3. if it errors for fixture/import/setup reasons, fix only the test harness and
   rerun until it fails for the intended reason;
4. add the smallest production change that can pass that test;
5. rerun the same test and record GREEN;
6. run the focused module containing all tests accrued so far;
7. refactor only while the focused module remains green;
8. commit the cohesive increment before adding the next test;
9. record command, exit code, failure reason, and result in the Task 4 report.

Do not use one parameterized test to conceal several unobserved red phases. A
cartesian-complement invariant may be one test only after at least one allowed
and one forbidden transition have independently demonstrated red/green.

### 17.1 Required domain sequence

Add and complete these tests in order, one at a time:

1. `test_uploading_may_transition_to_quarantined`
2. `test_scanning_operational_exhaustion_transitions_to_failed`
3. `test_parsing_policy_violation_transitions_to_rejected`
4. `test_parsing_operational_exhaustion_transitions_to_failed`
5. `test_flagged_source_may_be_rejected`
6. `test_suspicious_review_report_transitions_to_flagged`
7. `test_every_non_deleting_state_may_enter_deletion_pending`
8. `test_unlisted_source_transition_fails_closed`
9. `test_all_authorized_source_transitions_match_reconciled_closed_set`
10. `test_cartesian_complement_of_source_transitions_is_forbidden`
11. `test_physical_id_requires_rfc9562_uuid7`
12. `test_public_id_uses_separate_uuid7_from_physical_id`
13. `test_command_context_rejects_client_actor_scope_and_time`
14. `test_ready_requires_every_candidate_dispositioned`
15. `test_ready_allows_zero_accepted_candidates`
16. `test_candidate_is_extracted_from_source_segment`
17. `test_unchanged_acceptance_creates_source_extracted_condition`
18. `test_unchanged_acceptance_creates_source_segment_informs_edge`
19. `test_revision_creates_user_stated_condition`
20. `test_revision_does_not_create_source_segment_informs_edge`
21. `test_consideration_produces_validation_question`
22. `test_path_to_question_validation_relation_is_forbidden`
23. `test_source_segment_to_possible_path_remains_forbidden`
24. `test_deletion_complete_rejects_unresolved_target`

### 17.2 Required persistence and tenancy sequence

1. tenant foundation has UUIDv7 organization/workspace/membership rows,
   composite tenant foreign keys, forced RLS, audit, idempotency, and outbox;
2. `alembic heads` returns exactly one foundation head and `alembic check`
   reports no drift before Task 4 migration creation;
3. every Task 4 physical ID is UUIDv7 and every external object has a distinct
   prefixed UUIDv7 public ID;
4. clean PostgreSQL migration from the recorded foundation head creates the
   reviewed schema;
5. upgrade from a sanitized production-like foundation snapshot preserves
   legacy records and reconciled counts/hashes;
6. downgrade to the recorded parent and re-upgrade is lossless for the fixture;
7. source command writes state, review event, audit, idempotency, and outbox in
   one transaction;
8. injected failure rolls the entire transaction back;
9. same idempotency key/body returns prior result;
10. same key/different body returns conflict;
11. stale expected version returns conflict;
12. organization A cannot read, mutate, enumerate, or infer organization B;
13. workspace A cannot cross into workspace B within the same organization;
14. pooled connection scope does not survive the request transaction;
15. outbox duplicate delivery produces one state effect;
16. public-ID lookup always adds organization/workspace scope and never
    returns a physical ID;
17. user filename cannot alter the object key.

### 17.3 Required API sequence

1. feature-off capabilities return no enabled format;
2. unauthenticated create intent returns 401;
3. membership without `sources:write` returns 403;
4. PDF and Markdown return 415 without object intent;
5. valid TXT intent returns prefixed UUIDv7 public IDs, no physical IDs, and
   constrained direct-upload fields;
6. body actor/scope/time fields return 422;
7. completion checksum mismatch never reaches `QUARANTINED`;
8. valid completion commits `QUARANTINED` and an outbox row before 202;
9. wrong-tenant source ID returns the same 404 as missing;
10. pre-review GET withholds text/candidates;
11. flagged normal-user GET withholds flagged content;
12. review mutation requires idempotency and expected version;
13. finalize with unresolved candidate returns bounded 409;
14. finalize with all excluded returns `READY` and no condition;
15. suspicious candidate report atomically returns `FLAGGED`;
16. deletion can enter `DELETION_PENDING` from each eligible state;
17. unexpected exception returns stable 500/503 without text or traceback.

### 17.4 Required scanner/parser/corpus sequence

Create checked-in, non-sensitive fixtures with expected verdicts and hashes.
At minimum test:

- empty, boundary-size, over-size, valid Unicode, invalid UTF-8, BOM, NUL,
  disallowed controls, mixed line endings, extremely long line, Unicode
  normalization edge, bidirectional-control content, and binary masquerading
  as `.txt`;
- harmless instruction-like prose, direct prompt override, split instruction,
  encoded instruction, tool request, URL exfiltration request, data-URI text,
  and attempts to redefine output schema;
- known harmless scanner fixture and standard antivirus test signature;
- scanner-definition stale, scanner timeout, parser timeout, output overflow,
  malformed manifest, wrong segment hash, unknown segment reference, and model
  schema failure;
- no network, no secret, read-only root, non-root, PID/memory/CPU/time limit;
- retry after worker loss, stale fencing token, and duplicate delivery.

Expected outcomes are explicit: a malware/policy verdict is `REJECTED`;
invalid UTF-8 or forbidden TXT content discovered during parsing is
`REJECTED`; scanner/parser/extraction unavailability or crash after bounded
retry is `FAILED`; suspicious but reviewable content is `FLAGGED`. Tests must
fail if one category is substituted for another.

The hostile corpus proves rejection/flagging behavior; it does not prove files
are safe in general. Record scanner/parser/policy/corpus versions in evidence.

### 17.5 Required review, legacy, deletion, and frontend sequence

Review and provenance:

- unchanged acceptance, revision, exclusion, suspicious report, release,
  rejection, zero accepted, stale review, concurrent reviewers, and complete
  history;
- suspicious report proves `NEEDS_REVIEW -> FLAGGED`; authorized release
  proves `FLAGGED -> NEEDS_REVIEW`; authorized rejection proves
  `FLAGGED -> REJECTED`;
- source-derived prompt injection cannot add tools, schema fields, references,
  or a possible-path edge;
- candidate provenance uses `EXTRACTED_FROM`, unchanged acceptance uses
  `INFORMS`, user revision does not use `INFORMS`, and shared dependency tests
  use `CONSIDERATION PRODUCES_QUESTION VALIDATION_QUESTION`;
- logs/traces/outbox/broker exclude source content.

Legacy/downstream:

- URL route performs no outbound request;
- legacy graph upload performs no parse;
- legacy source is read-only/non-executable;
- missing/processing/flagged/rejected/deleting sources block selected-source
  preparation before mutation or dispatch;
- READY sources pass by scoped IDs only;
- no-source user-stated preparation remains available;
- worker repeats the gate;
- ontology registry failure has no direct fallback.

Deletion:

- target inventory is complete and deterministic;
- every state except `DELETION_PENDING`/`DELETED` can atomically enter
  `DELETION_PENDING`, revoke active upload/work, and fence late output;
- each adapter confirms only its exact target;
- object versions and failed multipart uploads are removed;
- failed target retries without marking deleted;
- legal hold blocks completion and is disclosed;
- provider/backup scheduled expiry is displayed truthfully;
- cross-tenant deletion is impossible;
- deletion events retain no source content.

Frontend:

- URL input and fake URL file are absent;
- PDF/Markdown cannot be selected while unavailable;
- displayed limits come from capabilities;
- direct upload and completion are separate;
- every processing/review/failure/reconnection/deletion state has plain copy
  and an action;
- keyboard accept/revise/exclude/report works;
- focus returns after dialogs, status is announced, errors link to controls;
- 320px, 200%/400% zoom, forced colors, reduced motion, and 44×44 targets pass;
- `READY` is never presented as verified, validated, evidence, or human input.

## 18. Verification commands

Use the repository environment. Do not claim completion from an unexecuted
command or a pre-existing green suite.

Focused domain loop:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_source_ingestion.py::test_name -q
.\.venv\Scripts\pytest tests/domain/test_identifiers.py tests/domain/test_source_ingestion.py -q
```

Focused backend checkpoints:

```powershell
cd backend
.\.venv\Scripts\pytest tests/test_source_ingestion_api.py -q
.\.venv\Scripts\pytest tests/test_source_review_api.py tests/test_source_review_service.py -q
.\.venv\Scripts\pytest tests/tasks/test_source_ingestion_tasks.py -q
.\.venv\Scripts\pytest tests/security/test_txt_ingestion_corpus.py -q
.\.venv\Scripts\pytest tests/test_source_deletion.py tests/integration/test_source_deletion_targets.py -q
```

PostgreSQL and migration evidence, using a dedicated disposable test database:

```powershell
cd backend
.\.venv\Scripts\alembic heads
.\.venv\Scripts\alembic current
.\.venv\Scripts\alembic check
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\alembic downgrade -1
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\pytest tests/integration/test_source_ingestion_postgres.py -q
```

Run `heads/current/check` before creating the revision and record that sole
tenant-foundation head as `down_revision`; run the full block after creation.
Repeat upgrade/downgrade/re-upgrade against the restored production-like
backup fixture and compare the recorded schema/count/hash digest.

Sandbox evidence after its deployment files exist:

```powershell
docker compose -f deploy/source-ingestion/compose.test.yml build
docker compose -f deploy/source-ingestion/compose.test.yml run --rm txt-parser-contract
docker compose -f deploy/source-ingestion/compose.test.yml run --rm scanner-contract
```

Touched backend lint only:

```powershell
cd backend
uvx ruff check app/domain/identifiers.py app/domain/source_ingestion.py app/application/source_ingestion app/api/routes/source_review_routes.py app/tasks/source_ingestion_tasks.py tests/domain/test_identifiers.py tests/domain/test_source_ingestion.py
```

Frontend:

```powershell
cd frontend
npm run test -- source-ingestion-review.spec.js
npm run build
```

Documentation and final repository verification:

```powershell
python tools/validate_docs.py
npm run verify
```

Required manual evidence:

- desktop keyboard-only review;
- NVDA with Firefox or Chrome on Windows;
- VoiceOver with Safari on macOS/iOS;
- 320px viewport, 200% and 400% zoom, reduced motion, forced colors;
- upload interruption, browser refresh, worker loss, broker retry, database
  failover, object-store timeout, scanner stale/timeout, parser timeout, model
  timeout, deletion retry, and reconnection;
- production configuration dry-run proving startup refuses every missing
  blocker independently.

## 19. Rollout, rollback, and claim boundary

Roll out in this order:

1. reconciled normative packet, domain, and ports, flag off;
2. tenant foundation actual-head migration, source schema/RLS/outbox/object
   store, flag off;
3. worker sandboxes and corpus, test environment only;
4. upload-to-reviewable TXT slice, development `PARTIAL`;
5. review UI and readiness, internal environment only;
6. legacy bypass removal and downstream admission;
7. deletion/operations evidence;
8. production dry-run with the flag still off;
9. named approval of the TXT-only evidence packet;
10. enable TXT for one organization cohort with metrics and kill switch;
11. expand only after the observation window and rollback rehearsal.

Rollback may disable new upload, review mutations, processing dispatch, and new
run admission. It must preserve canonical records and history, continue
deletion obligations, and never restore legacy unreviewed execution. In-flight
work is drained or stopped through durable commands; no object or database row
is silently abandoned.

Permitted claim after all TXT gates pass:

```text
TXT ingestion controls are active for the formats shown here. Source material shapes reviewed starting conditions only.
```

Prohibited claims include:

```text
secure source ingestion is complete
all uploaded files are safe
the source validates a scenario
the source proves or corroborates an outcome
source review makes the run factual
PDF/Markdown/URL ingestion is supported while disabled
```

Capabilities, UI, run manifests, exports, logs, release notes, and support copy
must state the same active format matrix. A disabled or untested format is
`UNAVAILABLE`, never “coming through the same secure pipeline.”

## 20. Completion boundary

Task 4’s first production slice is complete only when:

- the reconciled source transition/provenance packet in section 6 is landed in
  the normative docs with zero validator warnings/errors and named approval;
- the tenant foundation is canonical and the Task 4 migration passed the sole
  actual-head, clean/upgrade, parent downgrade/re-upgrade, restored-backup, and
  schema-digest procedure;
- every physical relational ID is UUIDv7, every external source object has a
  separately generated prefixed UUIDv7 public ID, and no physical ID is
  serialized;
- every production blocker in section 5 has evidence and named approval;
- TXT is the only enabled format and all other entry points fail closed;
- state, event, audit, idempotency, and outbox writes are transactional;
- tenant isolation is proven at API, repository, PostgreSQL RLS, job, object,
  cache, index, export, and deletion boundaries;
- scanner/parser isolation is exercised, not merely configured;
- every selected source must be `READY` at HTTP and worker admission;
- zero-accepted review is supported without inventing a condition;
- operational `FAILED` and policy/review `REJECTED` remain distinct in state,
  commands, API, UI, metrics, and tests;
- suspicious candidate reporting performs `NEEDS_REVIEW -> FLAGGED`, and every
  eligible state can enter `DELETION_PENDING` with late work fenced;
- direct source-to-path provenance remains impossible;
- deletion status is truthful across primary and delayed targets;
- strict one-test-at-a-time RED/GREEN evidence is recorded;
- focused tests, touched-file lint, frontend build, docs validation, and full
  repository verification pass;
- the UI is manually checked across the required accessibility and recovery
  matrix;
- legacy data remains readable only as explicitly labeled, non-executable
  history;
- unrelated dirty work is absent from Task 4 commits;
- release language stays inside section 19’s claim boundary.

Passing this boundary authorizes the controlled TXT format only. It does not
authorize PDF, Markdown, URL ingestion, OCR, or a blanket “secure” claim.

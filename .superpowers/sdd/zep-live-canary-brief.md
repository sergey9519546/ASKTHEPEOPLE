# Protected Zep live-canary implementation brief

Status: IMPLEMENTED LOCALLY / LIVE EXECUTION BLOCKED

## Objective

Provide one operator-only canary that executes inside the deployed Celery
worker and proves the complete derived-graph dependency path with a fixed,
fictional fixture:

1. create one isolated graph;
2. register and read back the exact PascalCase ontology `CanarySensor`,
   `CanaryHub`, and `ReportsTo` (`CanarySensor` -> `CanaryHub`);
3. submit exactly one episode without retrying an ambiguous mutation;
4. wait for processing and exact nodes/edge/provenance;
5. verify the exact owner marker, delete once, and confirm provider 404.

This is not an application feature and has no HTTP route. It does not make Zep
canonical. Canonical project/run/report records remain recoverable outside the
derived Zep index.

## Non-negotiable protection boundary

- Default is a non-dispatching dry run. `--execute` is explicit.
- There is no `--api-key` argument and no key in a Celery payload.
- The worker does not read `ZEP_API_KEY` until the execute flag, closed rotation
  evidence, deployment revision, Redis journal, prior-cleanup check, and
  ten-minute distributed lock have all passed.
- The Celery delivery UUID is the required run identity. Journal v2 binds every
  state to that run and revision and retains its closed terminal result. A
  same-run terminal redelivery returns it without credential or provider access.
- Zep SDK calls use a ten-second timeout and request options
  `timeout_in_seconds=10`, `max_retries=0`.
- Only replay-safe reads retry, at most three calls with 0.5/1.0 second delays,
  and only for timeouts, connection failures, HTTP 429, or HTTP 5xx.
  Deterministic 4xx cleanup errors stop immediately; 404 means clean only at an
  explicit absence-confirmation boundary.
- `add_batch` and `delete` are never replayed after an ambiguous result.
- The fixed fixture, provider credential, raw provider body, raw exception, and
  rotation evidence never enter the result, journal, or log surface.
- A provider graph is deletable only when both its graph ID and exact owner
  marker match the internally journaled values.

## Rotation evidence v1

The accepted JSON object is closed: missing and unknown fields fail. It records
the incident and provider IDs; affirmative old-credential revocation,
replacement issuance, web/worker update and restart facts; UTC timestamps;
provider-usage review coverage; different rotator and independent verifier
identities; the exact deployed revision; and a restricted opaque evidence
reference. It contains no credential value, fingerprint, prefix, suffix, or
hash.

Provider-usage review must cover the later web/worker restart, and independent
verification must follow that review.

The worker revision must exactly match the evidence revision through
`ZEP_CANARY_DEPLOYMENT_REVISION` (or Railway's commit revision fallback). The
operator must also set `ZEP_LIVE_CANARY_ENABLED=true` for the bounded window.

## State, time, and exit contract

The sanitized state vocabulary is:

`BLOCKED -> PREFLIGHTED -> CREATE_REQUESTED -> GRAPH_CREATED ->
ONTOLOGY_REQUESTED -> ONTOLOGY_VERIFIED -> EPISODE_REQUESTED ->
EPISODE_ACKNOWLEDGED -> EPISODE_PROCESSED -> GRAPH_VERIFIED ->
DELETE_REQUESTED -> CLEAN`

Any failure after a create could have landed transitions through
`RECONCILING`, then ends `CLEAN` or `CLEANUP_PENDING`. A prior pending/mutated
journal blocks a different run. A same-run `PREFLIGHTED` redelivery reuses its
identity. Any intent/partial-state redelivery reconciles the exact owner and
cleans or fails without replaying the uncertain mutation. Terminal results stay
addressable by run ID after later canaries.

- provider request timeout: 10 seconds;
- episode-processing deadline: 120 seconds;
- total create-to-verification deadline: 180 seconds;
- cleanup deadline: 60 seconds;
- episode and graph-materialization poll interval: 2 seconds;
- Redis lock TTL: 600 seconds.

Exit codes:

- `0`: full pass and deletion confirmed;
- `2`: functional failure, deletion/absence confirmed;
- `3`: cleanup pending or cleanup durability unavailable;
- `4`: rotation evidence blocked, zero Zep calls;
- `5`: execution/config/revision/journal/lock/dispatch blocked, zero Zep calls.

## Live gate

No live execution is authorized by this implementation. It remains blocked
until every historically exposed provider credential is revoked, one fresh
replacement is installed in both deployed web and worker services, both are
restarted, provider usage is reviewed through containment, the exact deployed
revision is recorded, and a different person independently verifies the
restricted evidence. The key itself must never be sent in chat, committed, or
recorded in evidence.

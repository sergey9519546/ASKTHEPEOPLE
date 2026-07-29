# Deployment

The canonical production target is the unified Railway Docker service:

`https://askthepeople-production-8325.up.railway.app`

The frontend and `/api`, `/ws`, and `/health` endpoints are served by the same
container and origin. Production builds must therefore leave
`VITE_API_BASE_URL` empty.

## Critical preflight: exposed provider credentials

Deployment is blocked by the open
[public-history credential incident](SECURITY-INCIDENT-2026-07-29.md). The
historically exposed Zep and Brave values still matched the local and Railway
values at discovery time. Revoke those values, replace them through secure
provider and Railway interfaces, confirm the historical LLM credential is
revoked, and review provider usage before enabling any release workflow.

Rotation must happen before Git-history cleanup. Do not paste replacement
values into this repository, an issue, chat, log, or workflow output.

The hardened workflows and deployment configuration described below are still
uncommitted worktree changes. Preserve them before any history rewrite, review
them through the normal change process, and merge their rewritten equivalents
before enabling deployment. The current `origin/main` does not yet contain this
release path.

## Release path

1. `CI` runs backend tests, frontend tests/build, dependency audits, secret
   scanning, CodeQL, and a real candidate-container health/authentication smoke;
   every result is part of one required gate.
2. `.github/workflows/deploy.yml` runs only after a successful `main` push CI
   run and checks that the tested commit is still the head of `main`.
3. The workflow calls Railway's public API with that exact commit SHA. Railway
   rejects a SHA that does not belong to the service's connected repository.
4. It waits until `/health` is healthy **and** reports the tested commit SHA.
   A healthy response from the previous release cannot pass the deployment.

Before enabling the workflow:

1. Preserve and review the current dirty worktree, then commit and merge the
   hardened configuration—or reapply its verified patch to the rewritten
   history—before treating this document as active deployment behavior.
2. Connect Railway service `8cca1670-faaf-4342-985e-1e33fa9e7cc1` to this
   GitHub repository and its `main` branch. The currently observed live service
   reports `source: null`, so a SHA-pinned API deployment will fail closed until
   that connection exists.
3. Protect `main` with a repository ruleset that requires the CI gate and CodeQL
   before merge, blocks force pushes and deletion, and requires pull-request
   review. Restrict Actions to approved, full-SHA-pinned actions.
4. Create a protected GitHub environment named `railway-production`.
5. Create a fresh Railway **project token** scoped to the production environment
   and store it only in that GitHub environment as
   `RAILWAY_PRODUCTION_TOKEN`. The distinct name prevents the existing broad
   repository-level `RAILWAY_TOKEN` from silently satisfying the workflow.
   The workflow verifies the token's project and environment IDs before using
   the project-token-only `Project-Access-Token` header.
6. Store the same strong runtime application key configured in Railway as the
   environment-only GitHub secret `PRODUCTION_APP_TOKEN`; it is used only for
   the post-deploy authenticated smoke check.
7. Remove and rotate the repository-level `RAILWAY_TOKEN` after checking that
   no other owner-approved workflow uses it.
8. Configure the environment with required reviewers, prevent self-review,
   disable administrator bypass, and set exactly one custom deployment branch
   policy, `main`. The workflow checks these rules before it reads either
   production secret.
9. Disable Railway's direct GitHub autodeploy so failed or pending CI revisions
   cannot bypass this workflow.

The deployment mutation is deliberately not retried: it is non-idempotent and a
lost response could otherwise queue the same release twice. Read-only status
polls may retry.

Before release, the workflow records the currently active deployment. It marks
that revision rollback-eligible only when `/health` succeeds, unauthenticated
settings access is rejected, and authenticated settings access succeeds. A
first deployment, an outage repair, or a migration from the current insecure
legacy build may proceed without automatic rollback; the workflow says so
explicitly. It never rolls back to a revision that failed those checks.

`.github/workflows/docker-image.yml` separately publishes reviewed release
images to GHCR. It is manual-only and must be dispatched from `main` with an
existing stable semantic-version tag that already points to the current main
revision. Before using it, create a reviewer-protected, main-only
`ghcr-production` environment, prevent self-review, and protect version tags
against updates or deletion.

The release workflow builds and persists a per-version candidate tag, attaches
BuildKit provenance and an SBOM, scans that exact registry digest for
high/critical vulnerabilities and embedded secrets, stages the digest under
its immutable commit SHA, then adds a GitHub OIDC build-provenance attestation.
It updates `latest` before publishing the immutable version as the final
operation. Candidate tags are mutable registry pointers, so a retry reuses one
only after `gh attestation verify` proves its immutable digest was produced by
this repository's reviewed release workflow from the same main revision. The
digest is then rescanned and its platform/revision metadata is rechecked. An
unattested or replaced candidate is rebuilt; a conflicting immutable release
version is refused. Failed candidates may remain in the separate
`askthepeople-candidate` package for resumability and audit evidence, but are
never promoted as releases. Establish an operator-owned retention policy for
old candidate tags; deleting one removes the retry anchor and requires a fresh
candidate build.

Railway currently builds the linked repository's Dockerfile; it does not
consume the GHCR image. Do not describe the registry artifact as the running
production image unless Railway's source is explicitly changed to that image.

Railway reads `railway.toml` for the Docker builder, `/health` readiness check,
restart policy, and a 300-second drain window. Gunicorn uses a 240-second
graceful timeout, leaving 60 seconds for the platform to finish container
shutdown after worker draining. Because active task state is still
process-local, operators should avoid deploying during a run; draining reduces
abrupt termination but cannot make unfinished work durable. The service must
define at least:

- `SECRET_KEY` — stable random production secret
- `REQUIRE_APP_AUTH=true`
- `APP_TOKEN` — private access key entered by authorized users at runtime;
  never expose it through a `VITE_*` variable
- `FLASK_DEBUG=false`
- `CORS_ORIGINS=https://askthepeople-production-8325.up.railway.app`
- `TRUSTED_HOSTS=askthepeople-production-8325.up.railway.app`
- `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL_NAME`
- `LLM_ALLOWED_BASE_URLS` — comma-separated exact provider roots
- `ZEP_API_KEY`
- `ALLOW_RUNTIME_SETTINGS=false`
- `ALLOW_PRIVATE_LLM_ENDPOINTS=false`
- Generated run activity stays in the separate observation store. Graph writes
  are unsupported and cannot be enabled by deployment configuration.
- `LOG_LEVEL=INFO`

`SECRET_KEY` and `APP_TOKEN` must each be at least 32 characters, must not be
documented placeholders, and should be generated independently. Railway sets
`RAILWAY_ENVIRONMENT_ID`, so the rate limiter safely uses the edge-provided
`X-Real-IP`. In that runtime the application also appends the exact
`healthcheck.railway.app` readiness-probe host to Flask's host allowlist; do
not replace it with a wildcard. Set `TRUST_X_REAL_IP=true` elsewhere only when
a trusted proxy overwrites that header.

Do not set `VITE_API_BASE_URL` for the unified deployment.
Do not set `VITE_APP_TOKEN`; every Vite environment value is readable in the
downloaded frontend bundle.

## Legacy Vercel URL

The prior Vercel frontend cannot carry the app's WebSocket workflow and its
production environment referenced a deleted Railway backend. Both
`vercel.json` files now define a temporary redirect to the canonical Railway
origin. Deploy that configuration once to preserve old bookmarks, then remove
the stale `VITE_API_BASE_URL` variable from Vercel. Do not run Vercel as a
second application frontend unless the transport and authentication model is
redesigned for split origins.

## Persistence

The application writes projects, uploads, simulations, and reports beneath
`/app/backend/uploads`. Railway currently has no volume, so that data is lost
when a deployment is replaced or restarted. Before treating history as durable,
attach a Railway volume at exactly:

`/app/backend/uploads`

This repository intentionally does not create the volume because it changes
external billing and infrastructure state.

The container starts briefly as root so its entrypoint can repair ownership of
that exact mount, then drops to UID/GID 10001 before starting Gunicorn. Compose
grants only `CHOWN`, `DAC_READ_SEARCH`, `SETUID`, and `SETGID` for mount
inspection, ownership repair, and that transition, and retains
`no-new-privileges`.

## Render alternative

`render.yaml` is a separate, manual Docker alternative. Its secret/provider
variables are mandatory Blueprint inputs and its health check is `/health`.
Add a persistent disk at `/app/backend/uploads` before production use. Do not
enable its autodeploy or run both providers against the same public hostname.

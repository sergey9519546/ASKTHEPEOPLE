---
title: "README"
status: "Reference"
version: "1.1.0"
owner: "Release Operator"
last_reviewed: "2026-10-01"
review_cycle: "Per deployment"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "deployment procedures"
---

# Deployment Documentation

> Consolidated deployment guides for ASKTHEPEOPLE platform

## Quick Start

**New to deployment?** Start with [FREE_DEPLOYMENT_GUIDE.md](FREE_DEPLOYMENT_GUIDE.md)

**Ready to deploy?** Use [../archive/sessions/2026-09-03-intelligent-guidance/READY_TO_DEPLOY.md](../archive/sessions/2026-09-03-intelligent-guidance/READY_TO_DEPLOY.md)

**Need a checklist?** See [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)

---

## Available Guides

### General Deployment

- **[DEPLOYMENT_OPTIONS.md](DEPLOYMENT_OPTIONS.md)** — Overview of all deployment options
- **[../archive/sessions/2026-09-03-intelligent-guidance/READY_TO_DEPLOY.md](../archive/sessions/2026-09-03-intelligent-guidance/READY_TO_DEPLOY.md)** — Complete deployment procedure
- **[DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)** — Pre-deployment checklist
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** — One-page quick reference

### Platform-Specific

#### Railway
- **[RAILWAY_SETUP.md](RAILWAY_SETUP.md)** — Complete Railway setup guide
- **[RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)** — Railway deployment procedure
- **[RAILWAY_FREE_TRIAL_STRATEGY.md](RAILWAY_FREE_TRIAL_STRATEGY.md)** — Using Railway free tier
- **[RAILWAY_QUICK_FIX.md](RAILWAY_QUICK_FIX.md)** — Troubleshooting Railway issues

#### Free Tier Options
- **[FREE_DEPLOYMENT_GUIDE.md](FREE_DEPLOYMENT_GUIDE.md)** — Deploy with $0 budget

### Component Setup

- **[CELERY_WORKER_SETUP.md](CELERY_WORKER_SETUP.md)** — Configure background workers
- **[COMMIT_STAGING_GUIDE.md](COMMIT_STAGING_GUIDE.md)** — Staging environment setup

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer / CDN                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ Frontend│       │ Backend │       │ Backend │
   │ (Static)│       │ (API)   │       │ (API)   │
   └─────────┘       └────┬────┘       └────┬────┘
                          │                  │
        ┌─────────────────┴──────────────────┘
        │
   ┌────▼────────────────────────────────┐
   │     PostgreSQL + Redis + S3         │
   └─────────────────────────────────────┘
```

---

## Environment Variables Required

### Backend
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=...
APP_TOKEN=...
OPENAI_API_KEY=...
CORS_ORIGINS=https://your-frontend.com
```

### Frontend
```bash
VITE_API_URL=https://your-backend.com
```

### Worker
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
OPENAI_API_KEY=...
```

See individual guides for complete environment variable lists.

---

## Deployment Checklist (Quick)

- [ ] Environment variables configured
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Frontend build successful (`npm run build`)
- [ ] Backend tests pass (`pytest`)
- [ ] CORS configured for production domain
- [ ] SECRET_KEY and APP_TOKEN are production values (not defaults)
- [ ] Worker process running (Celery)
- [ ] Health checks passing (`/health`, `/api/health`)

---

## Support Resources

- **Architecture:** [docs/architecture/](../architecture/)
- **Security:** [docs/security/](../security/)
- **Operations:** [../release/RUNBOOK.md](../release/RUNBOOK.md)
- **Monitoring:** [do../release/RUNBOOK.md](../release/RUNBOOK.md)

---

## Troubleshooting

### Common Issues

**500 errors on startup:**
- Check SECRET_KEY is set
- Verify DATABASE_URL is accessible
- Check CORS_ORIGINS includes your frontend domain

**Worker not processing jobs:**
- Verify Celery is running
- Check REDIS_URL connection
- Review worker logs

**Frontend can't reach backend:**
- Verify VITE_API_URL is correct
- Check CORS configuration
- Confirm backend is running

See platform-specific guides for detailed troubleshooting.

---

**Need help?** Check the [main documentation](../README.md) or open an issue.

---

## Deployment readiness (2026-09-03)

Read-only release-engineering audit of the deployment manifests against
`docs/release/RUNBOOK.md`. No manifest file was modified by this audit.

### CI status

Test-suite CI already exists; no additional workflow file was created.

- `.github/workflows/ci.yml` — `backend` job installs with
  `uv sync --frozen --group dev` and runs `pytest -q --ignore=tests/evals`
  plus the eval suite (`ci.yml:73-89`); `frontend` job installs with
  `npm ci` and runs `npm run test` and `npm run build` (`ci.yml:91-140`);
  plus container smoke tests, a gitleaks secret scan, CodeQL, and a
  required-checks `gate` job (`ci.yml:452-470`). Triggers on push to
  `main` and pull requests targeting `main`.
- `.github/workflows/docs.yml` — runs `python tools/validate_docs.py`
  plus wordmark and prohibited-language lints (`docs.yml:55-157`);
  path-filtered to documentation changes.
- Production deployment from CI is intentionally dark:
  `deploy-production` requires the repository variable
  `RAILWAY_PRODUCTION_DEPLOYMENT_ENABLED` to equal `true`
  (`ci.yml:479-482`). Do not set that variable while the blockers below
  stand.

### Deployment blockers

Blockers 2 and 6 below were **closed on 2026-10-01** and are retained for the
audit trail. Blockers 1, 3, 4, 5, and 7 remain open. Gate status is recorded in
[`../architecture/index.md` § Status of record](../architecture/index.md#status-of-record);
nothing here is a work queue.

1. **Every Procfile process type fails closed by design.** `Procfile:1-3`
   runs `backend/scripts/block_legacy_railway_deploy.py:8-11`, which
   always exits 78. Railway, Render (`render.yaml:1-4` declares no
   services), and Vercel paths are disabled until the
   canonical-persistence and revision-atomicity gates close
   (`docs/release/RUNBOOK.md:386-403`). There is no supported PaaS
   deploy of the current code.
2. ~~**`npm run setup:all` / `npm run setup:backend` is broken.**~~
   **RESOLVED 2026-10-01** (commit `47bff7b`). `package.json:7` now uses
   `uv sync --frozen --group dev` rather than `--extra dev`, so the runbook
   baseline command `npm run setup:all`
   (`docs/release/RUNBOOK.md:122-128`) works. The original defect: the dev
   dependencies are a uv dependency group, not an extra
   (`backend/pyproject.toml:112-117`), so `--extra dev` was rejected.
3. **Exposed provider credentials must be revoked and rotated first.**
   The runbook requires revocation, rotation, usage review, and
   independent verification of the exposed ZEP, primary-LLM, boost-LLM,
   and search credentials before any connected run or canary
   (`docs/release/RUNBOOK.md:535-539`).
4. **Required secrets are operator-supplied and cannot ship from the
   repo.** `SECRET_KEY` (refuses startup in production if unset,
   `backend/app/config.py:117-121`; minimum 32 characters,
   `backend/app/config.py:32,48`), `APP_TOKEN` (required when
   `REQUIRE_APP_AUTH=true`, the production default,
   `backend/app/config.py:135-138`, validated at
   `backend/app/config.py:351-360`), `LLM_API_KEY` and `ZEP_API_KEY`
   (`backend/app/config.py:347-350`), and an explicit `CORS_ORIGINS`
   allowlist (the `*` wildcard is refused in production,
   `backend/app/config.py:368-373`).
5. **The only runnable topology is single-host transition Compose, and
   it must not run from a synced filesystem.** `docker-compose.yml:32,36`
   requires `BUILD_REVISION` and a mode-0600 `.env.transition` created
   from `.env.transition.example`; web, worker, beat, and Redis share one
   `uploads` bind mount (`docker-compose.yml:73,121,176`); the runbook
   forbids running from OneDrive, Dropbox, NFS, or SMB
   (`docs/release/RUNBOOK.md:217-222`). The current checkout lives under
   OneDrive, so a deployer must clone to a local disk first.
6. ~~**The runbook's unified verification script does not exist.**~~
   **RESOLVED 2026-10-01** (commit `661f330`, portability fixed the same
   day). `./scripts/release/verify` exists and is the single entry point
   required by `docs/release/RUNBOOK.md:131-135`; `package.json:18` wires
   it as `npm run verify`. **Correction (2026-10-02):** this entry used to
   enumerate five steps and cite `package.json:16`. The script actually runs
   **six** gates - the numbering is in `scripts/release/verify:10-29`, which
   includes a doc truth-gate self-test this list omitted entirely. Gate status
   itself is not restated here; see the single authority at
   `docs/architecture/index.md` (Status of record).
7. **Provider dashboards must have automatic deployments disabled.**
   Railway's GitHub integration can autodeploy independently of Actions;
   the runbook requires the operator to disable autodeploy for every
   connected Railway, Vercel, and Render service and verify no legacy
   public origin remains (`docs/release/RUNBOOK.md:396-401`).

### Recommendations

8. Extend `.env.example` with optional variables the backend reads but
   the example omits: `SUPABASE_S3_ENDPOINT`, `SUPABASE_S3_ACCESS_KEY`,
   `SUPABASE_S3_SECRET_KEY` (`backend/app/config.py:328-331`),
   `SOURCE_INGESTION_V1_ENABLED` / `SOURCE_INGESTION_V1_FORMATS`
   (`backend/app/config.py:232-241`; must stay disabled in production,
   `backend/app/config.py:379-385`), `DEV_ACTOR_CONTEXT_ENABLED`
   (`backend/app/config.py:249-251`), `ENABLE_TRAIT_INFERENCE`,
   `DECISION_LENS_V1_ENABLED`, `RATELIMIT_STORAGE_URI`, and `LOG_FORMAT`.
   All have safe defaults; none block a deploy.
9. `npm run verify` is not a complete cross-platform gate:
   `backend:test` hardcodes the Windows path `.\.venv\Scripts\pytest`
   (`package.json:11`), and the chain omits `tools/validate_docs.py` and
   the backend eval suite that CI runs separately (`ci.yml:83-89`).
10. The local `.env.production` file is stale (untracked and gitignored):
    it names `BRAVE_API_KEY` where the backend reads
    `BRAVE_SEARCH_API_KEY` (`backend/app/api/settings.py:30`), an unused
    `VITE_APP_TOKEN` (the frontend reads only `VITE_API_BASE_URL`,
    `frontend/src/api/index.js:5`), and retired provider endpoints.
    Delete or regenerate it; never copy it into a platform.
11. The legacy guides in this directory predate the runbook: env names
    such as `OPENAI_API_KEY` and `VITE_API_URL` (below) do not match
    `backend/app/config.py` (`LLM_API_KEY`) and the frontend
    (`VITE_API_BASE_URL`), and the architecture diagram above does not
    describe the single-host transition topology. Treat
    `docs/release/RUNBOOK.md` as authoritative.

### Local verification result (2026-10-01)

`npm run verify` passed end to end on Windows: the documentation validator
reported PASS with zero errors and zero warnings, frontend 200 tests in 28
files passed, the production build succeeded, and the backend suite finished
with **9477 passed, 1 skipped, 1 xfailed** (evals excluded). Gate 5, the
gitleaks working-tree scan, is SKIPped because the binary is not installed
locally; CI enforces it.

This run only passed after two portability defects in `scripts/release/verify`
were repaired: gate 1 assumed `python` was on the Git Bash PATH, and gate 4
invoked the extensionless `.venv/Scripts/pytest`, whose CRLF shebang MSYS cannot
execute. Gate 1 now resolves an interpreter across several names and the
conventional Windows install roots; gate 4 prefers `pytest.exe`.

An earlier entry in this section reported 9475 passed / 4 skipped. That figure
came from a pre-fix run and was stale — re-measure rather than quoting it.

## Release verification gate

`./scripts/release/verify` (bash; runs under Git Bash on Windows) is now the
single verification entry point required by `docs/release/RUNBOOK.md:131-135`
and closes deployment blocker 6 above. It runs, in order:

| # | Gate | Skips? |
|---|---|---|
| 1 | Documentation validator (`tools/validate_docs.py`) | no |
| 2 | Doc truth-gate self-test (`scripts/release/check-docs-gates.sh`) | no |
| 3 | Frontend tests (`vitest run`) | no |
| 4 | Frontend production build (`vite build`) | no |
| 5 | Backend tests, evals excluded (mirroring `.github/workflows/ci.yml:81`) | no |
| 6 | gitleaks working-tree scan | yes, with a warning, when the binary is absent; CI still enforces the scan |

Root `npm run verify` invokes this same script; it exits non-zero when any gate
fails.

Gate 2 was added on 2026-10-01. It exists because both grep gates in
`.github/workflows/docs.yml` were silently inert: each used a multi-line
parenthesised ERE that GNU grep cannot compile, and because both pipelines ended
in `|| true` the compile error was swallowed, the hit list came back empty, and
the gates reported PASS on every run. The naked-wordmark gate had never caught a
violation. With the patterns repaired it reports 66 pre-existing violations, so
that gate is armed but currently failing. `check-docs-gates.sh` asserts the
patterns compile and that each gate fires on a planted violation, so a future
regression of this kind cannot pass silently again.

The script resolves a Python interpreter across several names and the
conventional Windows install roots rather than assuming `python` is on the
Git Bash PATH, and it prefers `.venv/Scripts/pytest.exe` over the
extensionless launcher, whose CRLF shebang MSYS cannot execute. Both defects
made the gate fail on Windows before 2026-10-01; see § Local verification
result above.

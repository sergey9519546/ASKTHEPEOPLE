---
title: "README"
status: "Reference"
version: "1.0.0"
owner: "Release Operator"
last_reviewed: "2026-09-03"
review_cycle: "Per deployment"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "deployment procedures"
---

# Deployment Documentation

> Consolidated deployment guides for ASKTHEPEOPLE platform

## Quick Start

**New to deployment?** Start with [FREE_DEPLOYMENT_GUIDE.md](FREE_DEPLOYMENT_GUIDE.md)

**Ready to deploy?** Use [READY_TO_DEPLOY.md](READY_TO_DEPLOY.md)

**Need a checklist?** See [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)

---

## Available Guides

### General Deployment

- **[DEPLOYMENT_OPTIONS.md](DEPLOYMENT_OPTIONS.md)** — Overview of all deployment options
- **[READY_TO_DEPLOY.md](READY_TO_DEPLOY.md)** — Complete deployment procedure
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

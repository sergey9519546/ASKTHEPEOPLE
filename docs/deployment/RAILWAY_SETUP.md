---
title: "RAILWAY SETUP"
status: "Reference"
version: "1.0.0"
owner: "Release Operator"
last_reviewed: "2026-09-03"
review_cycle: "Per deployment"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "deployment procedures"
---

# STATUS: DEPRECATED / DO NOT USE

> This legacy setup guide is retained for audit only. It does not implement the
> approved topology. Follow [`../release/RUNBOOK.md`](../release/RUNBOOK.md).

## Railway Production Setup Guide (Historical)

This guide walks through setting up ASKTHEPEOPLE on Railway with proper Celery worker configuration.

## Prerequisites

- Railway account: https://railway.app/
- GitHub repository connected to Railway
- Zep Cloud API key: https://www.getzep.com/
- OpenAI or compatible LLM API key

## Step 1: Create Railway Project

1. Go to https://railway.app/new
2. Select "Deploy from GitHub repo"
3. Choose your ASKTHEPEOPLE repository
4. Railway will detect the `Procfile` and `railway.toml`

## Step 2: Add Redis Plugin

**Critical:** This must be done before setting other environment variables.

1. In your Railway project dashboard, click "New" → "Database" → "Add Redis"
2. Railway automatically injects `REDIS_URL` into all services in the project
3. Verify: Go to your web service → Variables → you should see `REDIS_URL` (plugin-sourced)

## Step 3: Configure Environment Variables

In your web service settings → Variables tab, add:

### Required Variables

```bash
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
FLASK_DEBUG=false
APP_TOKEN=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
LLM_API_KEY=# YOUR_OPENAI_KEY_HERE (replace with actual key)
ZEP_API_KEY=# YOUR_ZEP_CLOUD_KEY_HERE (replace with actual key)
CORS_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}}
```

### Optional Variables

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_BOOST_MODEL_NAME=gpt-4o
BRAVE_SEARCH_API_KEY=# YOUR_BRAVE_KEY_HERE (replace with actual key)
SENTRY_DSN=# YOUR_SENTRY_DSN_HERE (replace with actual DSN)
ALLOW_RUNTIME_SETTINGS=false
LOG_LEVEL=INFO
```

**Note:** Do NOT set `PORT` or `RAILWAY_*` variables manually — Railway injects these automatically.

## Step 4: Verify Procfile Detected

Railway should automatically detect your `Procfile` and show **2 processes**:

- **web:** Gunicorn serving the Flask app
- **worker:** Celery worker consuming background tasks

If you only see "web", check:
1. `Procfile` exists at repository root
2. Both `web:` and `worker:` lines are present
3. Redeploy the service

## Step 5: Deploy

1. Railway will automatically deploy on push to `main`
2. Or manually trigger: Dashboard → Deployments → "Deploy"
3. Wait for both processes to start (web + worker)

## Step 6: Verify Deployment

### Check Health Endpoint

```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "ok",
  "redis": "ok",
  "services": {
    "llm": "ok",
    "zep": "ok"
  }
}
```

### Check Worker is Running

In Railway dashboard → your service → Deployments → click latest deployment → Logs

Filter by "celery" — you should see:
```
[celery@...] ready
[tasks]
  . tasks.generate_ontology_task
  . tasks.build_graph_task
  . tasks.prepare_simulation_task
  . tasks.run_simulation_task
  . tasks.generate_report_task
```

### Test Background Job

Upload a file via the frontend or API:

```bash
curl -X POST https://your-app.up.railway.app/api/graph/ontology/generate \
  -H "Authorization: Bearer $APP_TOKEN" \
  -F "files=@test.pdf" \
  -F "simulation_requirement=Test scenario" \
  -F "project_name=Test Project"
```

Response: `202 Accepted` with `task_id`

Poll status:
```bash
curl https://your-app.up.railway.app/api/graph/task/{task_id} \
  -H "Authorization: Bearer $APP_TOKEN"
```

Should progress: `pending` → `processing` → `completed`

**If stuck at `pending`:** The worker isn't running or can't reach Redis.

## Troubleshooting

### Worker Not Starting

**Symptom:** Only see "web" process, no "worker" in logs

**Fix:**
1. Verify `Procfile` has both lines
2. Check Railway Settings → "Start Command" is empty (uses Procfile)
3. Redeploy

### Redis Connection Failed

**Symptom:** Worker logs show `Error 111 connecting to redis`

**Fix:**
1. Verify Redis plugin is added to the same project
2. Check that `REDIS_URL` appears in Variables (plugin-sourced)
3. Restart both web and worker processes

### Tasks Queue But Never Execute

**Symptom:** Tasks stay `pending` forever

**Fix:**
1. Check worker logs for crashes
2. Verify `LLM_API_KEY` and `ZEP_API_KEY` are set (worker needs them too)
3. Check worker concurrency — increase if needed:
   ```
   worker: cd backend && exec celery -A app.celery_app worker --concurrency=4 ...
   ```

### Worker Runs Out of Memory

**Symptom:** Worker process crashes with OOM

**Fix:**
1. Lower concurrency: `--concurrency=1`
2. Add `--max-tasks-per-child=50` (already in Procfile)
3. Upgrade Railway plan for more RAM

### CORS Errors

**Symptom:** Frontend can't reach API

**Fix:**
```bash
CORS_ORIGINS=https://your-frontend.vercel.app,https://${{RAILWAY_PUBLIC_DOMAIN}}
```

Use actual domains, comma-separated, no wildcards in production.

## Cost Estimate

**Railway Starter Plan** (~$5/month):
- Web service: Shared CPU, 512MB RAM
- Worker process: Runs on same service (no extra charge)
- Redis: 25MB persistent storage

**Hobby Plan** (~$10/month):
- Dedicated resources
- More reliable for production

**Tips to Minimize Costs:**
- Use `--concurrency=1` on starter plan
- Set `--max-tasks-per-child=100` to prevent memory leaks
- Monitor usage in Railway dashboard

## Multi-Service Alternative (Advanced)

If you need isolated worker scaling:

1. Create a second Railway service from the same repo
2. Set Root Directory: `backend`
3. Set Start Command: `celery -A app.celery_app worker --loglevel=info --concurrency=4`
4. Copy all environment variables from web service
5. Link the same Redis plugin

This allows independent scaling but costs more.

## Monitoring

### Railway Built-in

- Deployments → Logs (filter by "celery" or "gunicorn")
- Metrics → CPU, Memory, Network

### External (Recommended)

**Sentry** for error tracking:
1. Create project at https://sentry.io/
2. Add `SENTRY_DSN` to Railway variables
3. Errors from both web and worker automatically captured

**Celery Monitoring** (optional):
- Flower: https://flower.readthedocs.io/ (adds overhead)
- Or add a `/api/tasks` route to expose TaskManager state

## Updating

**Automatic:**
- Push to `main` branch
- Railway auto-deploys
- Both web and worker restart

**Manual:**
- Railway Dashboard → Deploy

**Zero-downtime:** Railway's default deployment strategy:
1. Starts new web process
2. Waits for health check
3. Drains old process (300s graceful timeout in railway.toml)
4. Worker tasks in-flight complete before shutdown

## Backup Strategy

**What to back up:**
- `backend/uploads/` directory (projects, simulations, reports)
- Railway automatic backups cover Redis
- No database to back up (filesystem storage)

**Railway volumes:** Not configured by default. Data persists across deploys but not service deletions.

**Recommended:** Implement S3/R2 upload storage for production (not included).

## Security Checklist

Before going live:

- [ ] `SECRET_KEY` is 32+ random characters
- [ ] `APP_TOKEN` is set and distributed securely
- [ ] `FLASK_DEBUG=false`
- [ ] `CORS_ORIGINS` is specific domains (no `*`)
- [ ] `ALLOW_RUNTIME_SETTINGS=false` (or secured with APP_TOKEN)
- [ ] `ALLOW_PRIVATE_LLM_ENDPOINTS=false`
- [ ] Sentry configured for error tracking
- [ ] Health check passes
- [ ] Test one full ontology → graph → simulation → report flow

## Support

- Railway docs: https://docs.railway.app/
- Celery docs: https://docs.celeryq.dev/
- Issues: File on GitHub repository

---

**You're done!** All 7 background job endpoints now work:
- Ontology generation
- Graph building  
- Simulation preparation
- Simulation execution
- Report generation

Visit your Railway URL and start creating simulations. 🚀

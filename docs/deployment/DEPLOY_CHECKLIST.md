---
title: "DEPLOY CHECKLIST"
status: "Reference"
version: "1.0.0"
owner: "Release Operator"
last_reviewed: "2026-09-03"
review_cycle: "Per deployment"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "deployment procedures"
---

# Railway Deployment Checklist - Copy & Paste Guide

> **STATUS: DEPRECATED / DO NOT USE**
> This legacy checklist is retained for audit only and does not describe an
> approved deployment topology. Follow [`../release/RUNBOOK.md`](../release/RUNBOOK.md).
> Deployment remains blocked until provider credentials are rotated, canonical
> cross-process persistence exists, and web, worker, beat, and migrations are
> deployed and verified at one revision.

This checklist gives you EXACT values to copy-paste into Railway. No guessing.

## Step 1: Generate Secret Keys (Run These Locally)

Open a terminal and run these commands to generate your secret keys:

```bash
# Generate SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate APP_TOKEN
python -c "import secrets; print('APP_TOKEN=' + secrets.token_urlsafe(32))"
```

**Copy the output** — you'll paste these into Railway in Step 3.

## Step 2: Open Railway Dashboard

1. Go to: https://railway.app/dashboard
2. Find your ASKTHEPEOPLE project (or create new from GitHub repo)
3. Click on the project to open it

## Step 3: Add Redis Plugin

1. In your Railway project, click **"New"** button
2. Select **"Database"**
3. Click **"Add Redis"**
4. Railway automatically creates `REDIS_URL` and shares it with all services

**✅ You should see:** Redis appears in your project with a purple icon

## Step 4: Set Environment Variables

Click on your **web service** → **"Variables"** tab → Add these one by one:

### Required Variables (copy-paste the values you generated in Step 1):

```
SECRET_KEY=<paste the value from Step 1>
```

```
APP_TOKEN=<paste the value from Step 1>
```

### LLM Configuration (you already have these in .env):

From your local `.env` file, copy these values to Railway:

```
LLM_API_KEY=<set-in-provider-secret-store>
```

```
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
```

```
LLM_MODEL_NAME=meta/llama-3.1-8b-instruct
```

```
LLM_BOOST_API_KEY=<set-in-provider-secret-store>
```

```
LLM_BOOST_BASE_URL=https://integrate.api.nvidia.com/v1
```

```
LLM_BOOST_MODEL_NAME=meta/llama-3.1-8b-instruct
```

### Zep (from your .env):

```
ZEP_API_KEY=<set-in-provider-secret-store>
```

### Optional but recommended (from your .env):

```
BRAVE_SEARCH_API_KEY=<set-in-provider-secret-store>
```

### Production Settings:

```
FLASK_DEBUG=false
```

```
REQUIRE_APP_AUTH=true
```

```
ALLOW_RUNTIME_SETTINGS=false
```

```
ALLOW_PRIVATE_LLM_ENDPOINTS=false
```

```
LOG_LEVEL=INFO
```

### CORS (Railway fills in the domain automatically):

```
CORS_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}}
```

## Step 5: Push to Deploy

Railway will auto-deploy when you push to main:

```bash
git push origin main
```

OR manually trigger deploy in Railway:
- Dashboard → Your service → "Deployments" tab → Click "Deploy"

## Step 6: Verify Deployment

### A. Check Logs

In Railway Dashboard → Your service → Latest deployment → **"View Logs"**

**Look for these lines:**

```
# Web process should show:
[INFO] Booting worker with pid: ...
[INFO] Listening at: http://0.0.0.0:5001

# Worker process should show (filter logs by "celery"):
[celery@...] ready
[tasks]
  . tasks.generate_ontology_task
  . tasks.build_graph_task
  . tasks.prepare_simulation_task
  . tasks.run_simulation_task
  . tasks.generate_report_task
```

**If you only see web logs:** The Procfile wasn't detected. Check that `Procfile` exists at repo root.

### B. Check Health Endpoint

Click "Settings" → Note your public domain (e.g., `your-app.up.railway.app`)

Then visit in browser:
```
https://your-app.up.railway.app/health
```

**Expected response:**
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

**If redis shows "not_configured":** Redis plugin isn't linked or REDIS_URL is missing.

### C. Test Background Job

Open browser console at `http://127.0.0.1:5173` (your local frontend) and run:

```javascript
fetch('https://your-app.up.railway.app/api/graph/ontology/generate', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_APP_TOKEN_HERE', // Use the token from Step 1
    'Content-Type': 'multipart/form-data'
  },
  body: formData // Upload a test PDF
})
```

**Expected:** 202 Accepted with task_id
**Then poll:** `/api/graph/task/{task_id}` should go from `pending` → `processing` → `completed`

**If stuck at pending forever:** Worker isn't running or can't reach Redis.

## Troubleshooting

### Worker Not Running

**Check:** Railway Settings → "Start Command" 
- Should be **empty** (uses Procfile)
- If it shows a command, delete it

### Redis Connection Failed

**Check:** Variables tab shows `REDIS_URL` (plugin-sourced)
- Should show: `redis://default:...@redis.railway.internal:6379`
- If missing: Delete and re-add Redis plugin

### 401 Unauthorized on API Calls

**Check:** You're sending the correct `Authorization: Bearer <APP_TOKEN>` header
- Use the APP_TOKEN you generated in Step 1

### CORS Errors

**Check:** Variable `CORS_ORIGINS` 
- Should be: `https://${{RAILWAY_PUBLIC_DOMAIN}}`
- NOT: `https://askthepeople.onrender.com` (that's Render, not Railway)

## Success Criteria

✅ Railway shows 2 processes running (web + worker)
✅ `/health` returns `{"status": "ok", "redis": "ok"}`
✅ Upload file → ontology generates (background job works)
✅ No errors in logs

---

**If you get stuck at any step, send me:**
1. Screenshot of Railway logs (filter by "error")
2. The response from `/health` endpoint
3. Which step number you're stuck on

I'll guide you through it.

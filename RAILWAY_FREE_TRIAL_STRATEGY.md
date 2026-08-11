# STATUS: DEPRECATED / DO NOT USE

> This legacy cost guide is retained for audit only. Its split-service advice
> is unsafe for the current filesystem-backed state. Follow
> [`docs/release/RUNBOOK.md`](docs/release/RUNBOOK.md).

# Railway Free Trial Strategy — Historical

You have $5 free trial credits. Don't waste them.

## 💰 How Railway Charges

Railway charges **per second of usage** based on:
- RAM allocation
- CPU usage (vCPU-seconds)
- Network egress

**Hobby Plan:** $0.000463/GB-RAM/hour + CPU usage
**Pro Plan:** Different pricing model

**Your $5 lasts approximately:**
- Hobby (512MB): ~20-30 days
- Pro (8GB): ~5-7 days

---

## 🎯 Strategy: Use Hobby Tier with Combined Process

### Problem: 
- Hobby = 512MB RAM total
- Your Procfile has 2 processes (web + worker)
- Each needs ~300MB
- **Won't fit in 512MB**

### Solution:
Combine web + worker into ONE process (like Fly.io strategy).

---

## 📋 Step-by-Step: Railway Hobby Deployment

### Step 1: Update Procfile (Combine Processes)

**Current Procfile:**
```
web: cd backend && exec gunicorn ...
worker: cd backend && exec celery ...
```

**New Procfile:**
```
web: cd backend && exec supervisord -c /app/supervisord.conf
```

### Step 2: Create supervisord.conf

Create `supervisord.conf` at repo root:

```ini
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:gunicorn]
command=gunicorn --bind 0.0.0.0:%(ENV_PORT)s --workers 1 --threads 4 --timeout 300 --graceful-timeout 240 wsgi:app
directory=/app/backend
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:celery]
command=celery -A app.celery_app worker --loglevel=info --concurrency=1 --max-tasks-per-child=100
directory=/app/backend
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

### Step 3: Update Dockerfile

Add supervisor installation in Dockerfile (before CMD):

```dockerfile
# Install supervisor
RUN pip install supervisor

# Copy supervisor config
COPY supervisord.conf /app/supervisord.conf

# Create log directory
RUN mkdir -p /var/log/supervisor
```

Change the CMD at the end:

```dockerfile
CMD ["supervisord", "-c", "/app/supervisord.conf"]
```

### Step 4: Deploy to Railway

Railway will:
- Auto-detect Dockerfile
- See only 1 process in Procfile (the "web" process)
- Allocate 512MB to that process
- Both web + worker run inside it

---

## 💰 Credit Usage Estimate

**Hobby Tier (512MB):**
- Web + Worker combined: ~400-450MB actual usage
- $0.000463/GB-hour × 0.45GB × 24h × 30 days = ~$5
- **Your $5 lasts ~30 days**

**If you use Pro by mistake:**
- Minimum resources = 1GB RAM
- Higher per-hour rate
- **Your $5 lasts ~7 days**

**Recommendation:** Stay on Hobby, use combined process.

---

## 🚨 How to Avoid Wasting Credits

### 1. Don't Deploy Multiple Times Unnecessarily
- Each failed deploy = wasted compute
- Test locally first (`docker build` + `docker run`)

### 2. Use Railway's Free Redis
- Railway Redis plugin has free tier (25MB)
- Don't pay for external Redis

### 3. Don't Add a Volume Yet
- Volumes cost extra ($0.25/GB/month)
- For trial, accept ephemeral uploads
- Add volume only after trial (when you migrate to Fly.io or pay)

### 4. Monitor Usage Daily
- Railway Dashboard → Project → Usage
- Check how fast credits burn
- Stop service if not actively testing

### 5. Delete Service When Not Testing
- Only deploy when you're ready to test
- Delete service between test sessions
- Re-deploy when needed

---

## 📊 Trial Lifecycle Plan

### Days 1-3: Initial Setup & Testing
- Deploy to Railway Hobby with combined process
- Test all 7 background job endpoints
- Test full workflow (upload → graph → simulation → report)
- **Burn rate: ~$0.50**

### Days 4-25: Limited Active Use
- Only start service when demoing
- Delete service between demos
- Re-deploy via `git push` when needed
- **Burn rate: ~$3**

### Days 26-30: Migration Planning
- Prepare Fly.io deployment
- Test Fly.io in parallel
- Let Railway trial expire
- **Burn rate: ~$1.50**

### Day 31+: Migrate to Fly.io Free Tier
- Railway credits exhausted
- Fly.io $0/month continues indefinitely

---

## 🎯 Action Plan (Next 30 Minutes)

1. **I'll update your files:**
   - Dockerfile (add supervisor)
   - Create supervisord.conf
   - Update Procfile (1 process)

2. **You deploy to Railway:**
   - Push to GitHub
   - Railway auto-deploys
   - Add Redis plugin (free tier)
   - Set env vars from DEPLOY_CHECKLIST.md

3. **Test immediately:**
   - Health check
   - One background job
   - Verify both web + worker logs appear

4. **Stop service after testing:**
   - Railway Dashboard → Service → Settings → Delete
   - Saves credits for next test

---

## 💡 Summary

**Railway Strategy:**
- ✅ Use Hobby tier ($5 = 30 days)
- ✅ Combine web + worker (1 process = 512MB)
- ✅ Use free Redis plugin
- ✅ Skip volume (accept ephemeral uploads for trial)
- ✅ Delete service between tests

**Migration Strategy:**
- Use Railway for 30 days
- Migrate to Fly.io free tier before credits expire
- Continue indefinitely at $0/month

**Want me to prepare the Dockerfile + supervisord.conf changes now?**

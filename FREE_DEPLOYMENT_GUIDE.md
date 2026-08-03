# Free Deployment Guide ($0/month)

You have $5 Railway trial credits. You need **free long-term hosting**.

## 🎯 Best Free Option: Fly.io Free Tier

**What you get for $0/month:**
- Up to 3 apps free
- 256MB RAM shared across apps
- Free Redis (256MB Upstash tier)
- 3GB persistent storage
- 160GB bandwidth/month
- True 24/7 (no sleep)
- Automatic HTTPS

**The catch:** 256MB RAM is tight for web + worker separately.

**The solution:** Combine web + worker into ONE process using a process manager.

---

## 📋 Step-by-Step Fly.io Setup

### Step 1: Install Flyctl CLI

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**Or download:** https://fly.io/docs/hands-on/install-flyctl/

### Step 2: Sign Up (Free)

```bash
fly auth signup
# Or: fly auth login (if you have account)
```

### Step 3: Launch Your App

```bash
cd C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE
fly launch --no-deploy
```

**Answer the prompts:**
- App name: `askthepeople` (or your choice)
- Region: Choose closest to you
- PostgreSQL: **No**
- Redis: **Yes** (select Development - free tier)

### Step 4: Edit fly.toml

The generated `fly.toml` needs adjustments. Replace it with:

```toml
app = "askthepeople"
primary_region = "sjc"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8080"
  FLASK_DEBUG = "false"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  memory = '256mb'
  cpu_kind = 'shared'
  cpus = 1

[[services]]
  protocol = "tcp"
  internal_port = 8080

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.http_checks]]
    interval = "30s"
    timeout = "5s"
    grace_period = "10s"
    method = "GET"
    path = "/health"
```

### Step 5: Update Dockerfile for Combined Process

Add this to your Dockerfile before the `CMD`:

```dockerfile
# Install supervisor to run multiple processes
RUN pip install supervisor

# Create supervisor config
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
```

### Step 6: Create supervisord.conf

```ini
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:web]
command=gunicorn --bind 0.0.0.0:%(ENV_PORT)s --workers 1 --threads 2 --timeout 300 wsgi:app
directory=/app/backend
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:worker]
command=celery -A app.celery_app worker --loglevel=info --concurrency=1 --max-tasks-per-child=50
directory=/app/backend
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

### Step 7: Update Dockerfile CMD

Change the last line of Dockerfile to:

```dockerfile
CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

### Step 8: Set Environment Variables

```bash
fly secrets set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
fly secrets set APP_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
fly secrets set LLM_API_KEY=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
fly secrets set LLM_BASE_URL=https://integrate.api.nvidia.com/v1
fly secrets set LLM_MODEL_NAME=meta/llama-3.1-8b-instruct
fly secrets set ZEP_API_KEY=z_dev_hy5V2LqnmBLo8X6h5zBXZxHlZw-5Y7JTJ_3pzWmEBPQ
fly secrets set BRAVE_SEARCH_API_KEY=BSA_gkzIc09c0080d7bzGRzz9bHZuci
fly secrets set CORS_ORIGINS=https://askthepeople.fly.dev
```

### Step 9: Create Persistent Volume

```bash
fly volumes create uploads_data --region sjc --size 1
```

### Step 10: Deploy

```bash
fly deploy
```

### Step 11: Verify

```bash
fly status
fly logs
curl https://askthepeople.fly.dev/health
```

---

## 💰 Cost: $0/month

Everything stays within Fly.io's free tier:
- ✅ 1 app (256MB) = free
- ✅ Redis (256MB) = free
- ✅ 1GB volume = free
- ✅ <160GB bandwidth = free

---

## 🚨 If 256MB is Too Tight

**Upgrade to 512MB: $5/month**

```bash
fly scale memory 512
```

Still cheaper than Railway's $25/month Pro tier.

---

## 🔄 Alternative: Oracle Cloud Always Free

If Fly.io doesn't work, Oracle Cloud offers:
- 2x VM instances (1GB RAM each)
- Permanent free tier (no trial, no expiration)
- Full VM control

**But:**
- More complex (3-4 hours setup)
- You manage OS updates, security, SSL
- More responsibility

**Setup guide:** https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm

---

## 📊 Comparison

| Platform | Cost | RAM | Setup | Complexity |
|----------|------|-----|-------|------------|
| **Fly.io Free** | **$0** | **256MB** | **2hr** | **Medium** |
| Fly.io Paid | $5/mo | 512MB | 2hr | Medium |
| Oracle Free | $0 | 1GB | 4hr | High |
| Railway Trial | $5 trial | 512MB | 30min | Low |

---

## 🎯 My Recommendation

**Deploy to Fly.io Free Tier ($0/month)**

1. Follow steps 1-11 above
2. If performance is too slow, upgrade to 512MB ($5/month)
3. Still $20/month cheaper than Railway Pro

**Want me to prepare the exact Dockerfile and supervisord.conf changes for you?**

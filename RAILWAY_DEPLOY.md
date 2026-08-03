# Railway Deployment Guide

## Prerequisites
1. Railway CLI installed: `npm i -g @railway/cli`
2. Railway account connected: `railway login`
3. CI passing (deploys from GHCR image)

## Step 1: Create Railway Project

```bash
# In the project root
railway init
# Select "Empty Project" when prompted
# Name it: askthepeople-production
```

## Step 2: Add GitHub Container Registry Image

```bash
# Link to the GHCR image that CI builds
railway service
# When prompted, select "Add a service"
# Choose "Docker Image"
# Enter: ghcr.io/sergey9519546/askthepeople:latest
```

## Step 3: Set Environment Variables

Run these commands to configure the production environment:

```bash
# Generate strong secrets (run these first to get random values)
railway variables set SECRET_KEY=$(openssl rand -base64 48)
railway variables set APP_TOKEN=$(openssl rand -base64 48)

# LLM Configuration (using your provided a6api key)
railway variables set LLM_API_KEY="sk-aN8EZ7qcGxONUUDO3ltndrsZdvxm1MXQi2wr2iLi8gYXa1hQ"
railway variables set LLM_BASE_URL="https://api.a6api.com/v1"

# Zep Configuration (you'll need to provide your Zep API key)
railway variables set ZEP_API_KEY="z_YOUR_ZEP_KEY_HERE"

# Sentry Error Tracking (sign up at sentry.io for free tier)
railway variables set SENTRY_DSN="https://YOUR_SENTRY_DSN@sentry.io/PROJECT_ID"
railway variables set SENTRY_ENVIRONMENT="production"
railway variables set SENTRY_TRACES_SAMPLE_RATE="0.1"  # 10% of transactions sampled

# Authentication
railway variables set REQUIRE_APP_AUTH="true"

# CORS Origins (update with your actual frontend domain after first deploy)
railway variables set CORS_ORIGINS="https://askthepeople-production.up.railway.app"

# Trusted Hosts (Railway will provide these - update after first deploy)
railway variables set TRUSTED_HOSTS="askthepeople-production.up.railway.app"

# Database (PostgreSQL - Railway will provide this after adding PostgreSQL service)
# railway variables set DATABASE_URL="postgresql+asyncpg://user:password@host:port/dbname"

# Redis (optional - add Redis service first if needed)
# railway variables set REDIS_URL="redis://default:password@host:port"

# Flask environment
railway variables set FLASK_ENV="production"
railway variables set FLASK_DEBUG="false"
```

## Step 4: Deploy

```bash
# Trigger the first deploy
railway up
```

## Step 5: Get Your Public URL

```bash
railway domain
# Railway will show your public URL
```

## Step 6: Update CORS and Trusted Hosts

After getting your public URL (e.g., `askthepeople-production.up.railway.app`), update:

```bash
railway variables set CORS_ORIGINS="https://askthepeople-production.up.railway.app"
railway variables set TRUSTED_HOSTS="askthepeople-production.up.railway.app"
```

## Step 7: Verify Health

```bash
curl https://your-railway-url.railway.app/health
# Should return: {"status":"ok","service":"ASKTHEPEOPLE Backend","revision":"...","storage_writable":true}
```

## Automatic Deploys from CI

Once Railway is set up, the CI workflow automatically deploys to production when:
1. All tests pass on `main` branch
2. Docker image is built and tagged
3. Deploy workflow triggers and updates Railway service

## Monitoring

```bash
# View logs
railway logs

# Check service status
railway status

# View environment variables
railway variables
```

## Adding Redis (Optional but Recommended)

```bash
# Add Redis service to your Railway project
railway add redis
# Railway will automatically set REDIS_URL
```

## Security Notes

1. **Never commit real secrets** - they're already in `.gitignore`
2. **Rotate APP_TOKEN regularly** - it's your API auth token
3. **Use Railway's secret management** - don't expose keys in logs
4. **Monitor health endpoint** - `/health` shows component status
5. **Set up alerts** - Railway can notify on deployment failures

## Monitoring & Observability

### Sentry Error Tracking

1. **Sign up for Sentry** (free tier available):
   - Visit https://sentry.io and create an account
   - Create a new project (select "Flask" as the platform)
   - Copy the DSN (Data Source Name)

2. **Configure Sentry in Railway**:
   ```bash
   railway variables set SENTRY_DSN="https://YOUR_KEY@o123456.ingest.sentry.io/789012"
   railway variables set SENTRY_ENVIRONMENT="production"
   railway variables set SENTRY_TRACES_SAMPLE_RATE="0.1"
   ```

3. **What Sentry Tracks**:
   - All unhandled exceptions with full stack traces
   - Request context (URL, headers, method)
   - User context (if available)
   - PII is automatically scrubbed (emails, API keys, credit cards, SSN)
   - Release tracking via git commit SHA

### Health Check Monitoring

The `/health` endpoint returns component status:

```json
{
  "status": "ok",
  "service": "ASKTHEPEOPLE Backend",
  "revision": "abc123...",
  "components": {
    "storage": "ok",
    "database": "ok",
    "redis": "ok",
    "celery": "ok"
  }
}
```

**Railway Health Check Configuration**:
- Path: `/health`
- Expected status: 200
- Interval: 30 seconds
- Timeout: 10 seconds

**Readiness Probe**:
- Path: `/health/readiness`
- Checks all dependencies before accepting traffic
- Returns 503 if not ready

## Troubleshooting

### Worker fails to boot
- Check `railway logs` for errors
- Verify all required env vars are set: `railway variables`
- Ensure LLM_API_KEY and ZEP_API_KEY are valid

### 503 on /health
- Check if UPLOAD_FOLDER is writable (Railway should auto-create)
- Verify Redis is accessible if configured

### CORS errors
- Update CORS_ORIGINS with your actual frontend URL
- Ensure TRUSTED_HOSTS includes your Railway domain

---

## Quick Reference: Environment Variables Required

| Variable | Required | Example |
|----------|----------|---------|
| SECRET_KEY | Yes | (48-byte random) |
| APP_TOKEN | Yes | (48-byte random) |
| LLM_API_KEY | Yes | sk-aN8EZ7qcGxONUUDO... |
| LLM_BASE_URL | Yes | https://api.a6api.com/v1 |
| ZEP_API_KEY | Yes | z_your_zep_key_here |
| REQUIRE_APP_AUTH | Yes | true |
| CORS_ORIGINS | Yes | https://your-domain.railway.app |
| TRUSTED_HOSTS | Yes | your-domain.railway.app |
| FLASK_ENV | Yes | production |
| FLASK_DEBUG | Yes | false |
| SENTRY_DSN | Recommended | https://key@sentry.io/project |
| SENTRY_ENVIRONMENT | Optional | production |
| SENTRY_TRACES_SAMPLE_RATE | Optional | 0.1 (10% sampling) |
| DATABASE_URL | Optional | postgresql+asyncpg://... |
| REDIS_URL | Optional | redis://... |
| CELERY_BROKER_URL | Optional | (defaults to REDIS_URL) |


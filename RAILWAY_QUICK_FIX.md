# Railway Deployment Quick Fix

## Current Status
- ✅ App deployed at https://askthepeople-production-8325.up.railway.app/
- ✅ Backend running
- ✅ Frontend built into image
- ❌ Missing environment variables

## Fix Steps (5 minutes)

### 1. Add Redis Plugin

In Railway dashboard:
1. Go to your project
2. Click "New" → "Database" → "Add Redis"
3. Choose **Development (free)** plan
4. Railway automatically sets `REDIS_URL` for you

### 2. Set Environment Variables

Click your service → "Variables" tab → Add these:

```
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(32))">
APP_TOKEN=<generate: python -c "import secrets; print(secrets.token_urlsafe(32))">
REQUIRE_APP_AUTH=false
LLM_API_KEY=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
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_MODEL_NAME=meta/llama-3.1-8b-instruct
ZEP_API_KEY=z_dev_hy5V2LqnmBLo8X6h5zBXZxHlZw-5Y7JTJ_3pzWmEBPQ
BRAVE_SEARCH_API_KEY=BSA_gkzIc09c0080d7bzGRzz9bHZuci
CORS_ORIGINS=https://askthepeople-production-8325.up.railway.app
FLASK_DEBUG=false
```

**Critical:** Set `REQUIRE_APP_AUTH=false` for now (or you'll need to send token with every request)

### 3. Railway Will Auto-Redeploy

After setting variables, Railway automatically redeploys. Wait ~2-3 minutes.

### 4. Test

```bash
curl https://askthepeople-production-8325.up.railway.app/health
# Should show: {"status": "ok", "redis": "ok", "services": {"llm": "ok", "zep": "ok"}}

curl https://askthepeople-production-8325.up.railway.app/api/simulation/list
# Should return: {"success": true, "data": [], "count": 0}
```

### 5. Access Frontend

Visit: https://askthepeople-production-8325.up.railway.app/

Should now fully load with UI.

---

## Current Procfile Issue

Your Procfile has 2 processes but Railway **only runs the "web" process**.

The "worker" process is being **ignored**.

**Two options:**

### Option A: Keep Current Setup (Web Only)
- Works for testing
- Background jobs will use synchronous fallback
- No Celery worker running

### Option B: Combine Web + Worker (Recommended for trial)
- Use supervisor to run both
- Fits in Hobby tier (512MB)
- I can prepare this if you want

---

## Immediate Action

1. **Right now:** Add Redis + set env vars (above)
2. **After it works:** Test frontend loads
3. **Optional:** Combine web+worker for background jobs

Ready to test once you set the env vars!

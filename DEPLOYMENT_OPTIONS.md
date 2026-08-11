# STATUS: DEPRECATED / DO NOT USE

This historical cost comparison does not describe the current repository or a
safe release topology. It predates the canonical-persistence, worker
attestation, credential-rotation, and migration gates. Follow
[`docs/release/RUNBOOK.md`](docs/release/RUNBOOK.md) instead. Until those gates
are closed, the only supported zero-cost target is the explicitly labelled
single-host TRANSITION demo topology with fictional, non-sensitive data.

# Deployment Cost Analysis — Railway vs Alternatives (historical)

## Current Setup: Railway

**What you get:**
- Dockerfile deployment (no platform lock-in)
- Redis included
- Auto-scaling (vertical)
- Health checks
- Automatic HTTPS
- GitHub auto-deploy
- Good DX (easy to use)

**Costs:**

| Tier | Price | Specs | Verdict |
|------|-------|-------|---------|
| Hobby | $5/month | 512MB RAM, 0.5 vCPU shared, 100GB bandwidth | ❌ Too small (2 processes need ~1GB) |
| **Pro** | **$20/month** | **8GB RAM, 8 vCPU shared, 100GB bandwidth** | **✅ This is what you need** |
| + Redis | +$0-5 | 25MB free, then $0.10/GB | ✅ Likely free |
| + Volume | +$5 | 10GB persistent | ✅ Needed for uploads |
| **Total** | **~$25/month** | | |

**Why Pro tier required:**
- Hobby = 512MB total, but you have 2 processes (web + worker)
- Each process needs ~300-500MB
- Redis needs ~50MB
- **512MB won't fit both processes**

---

## 💰 Cheaper Alternative: Render

**What you get:**
- Same Dockerfile support
- Managed Redis
- Auto-scaling
- Health checks
- Automatic HTTPS
- GitHub auto-deploy

**Costs:**

| Tier | Price | Specs | Verdict |
|------|-------|-------|---------|
| **Starter** | **$7/month (web)** | **512MB RAM, 0.5 CPU** | **✅ Works** |
| **+ Background Worker** | **+$7/month** | **512MB RAM, 0.5 CPU** | **✅ Separate service** |
| + Redis | $7/month | 25MB persistent | ✅ Managed Redis |
| + Disk | $1/GB/month | Persistent disk | ✅ ~$5 for 5GB |
| **Total** | **~$26/month** | | |

**Advantage:** Smaller units, pay per service
**Disadvantage:** Same cost, more config complexity

**Verdict:** Railway is better DX for same price.

---

## 💰 CHEAPEST Option: Fly.io

**What you get:**
- Dockerfile support
- Redis addon
- Auto-scaling
- Health checks
- Automatic HTTPS
- GitHub Actions deploy

**Costs:**

| Resource | Free Tier | Paid | Your Usage | Cost |
|----------|-----------|------|------------|------|
| Apps | 3 apps free | $0 | 2 apps (web+worker) | **$0** |
| RAM | 256MB/app free | $0.0000022/MB/sec | 512MB web + 256MB worker | **~$12/month** |
| CPU | Shared free | $0.02/GB | ~10GB/month | **$0.20** |
| Redis | 256MB free | $1.79/GB | <256MB | **$0** |
| Persistent Volume | 3GB free | $0.15/GB | 5GB | **$0.30** |
| Bandwidth | 100GB free | | <10GB | **$0** |
| **Total** | | | | **~$12.50/month** |

**Advantages:**
- Cheapest for small projects
- Free Redis (256MB)
- Free apps (just pay for resources)
- Global edge network

**Disadvantages:**
- More complex config (`fly.toml` + scaling rules)
- Less intuitive dashboard
- Requires `flyctl` CLI

**Verdict:** **Best price for your scale, worth the learning curve.**

---

## 💰 ALMOST FREE Option: GitHub Codespaces + Tunnel

**What you get:**
- 60 hours/month free (120 with Pro)
- 2 core, 8GB RAM
- Run everything locally
- Expose via Cloudflare Tunnel or ngrok

**Costs:**

| Tier | Price | Specs | Limits |
|------|-------|-------|--------|
| Free | $0 | 60 hours/month | Must run during demo only |
| Pro | $10/month | 120 hours/month | ~4 hours/day |
| Tunnel | $0 | Cloudflare free tier | |
| **Total** | **$0-10/month** | | Only works for demos |

**Advantages:**
- Essentially free for infrequent demos
- Full dev environment
- No deployment needed

**Disadvantages:**
- ❌ Not 24/7 (hours limited)
- ❌ Loses state when stopped
- ❌ Manual start required
- ❌ Not "production"

**Verdict:** Good for demos, not real deployment.

---

## 💰 SERVERLESS Option: Vercel + Neon + Upstash

**What you get:**
- Frontend on Vercel edge (instant)
- Backend on Vercel serverless functions
- PostgreSQL on Neon (serverless)
- Redis on Upstash (serverless)

**Costs:**

| Service | Free Tier | Your Usage | Cost |
|---------|-----------|------------|------|
| Vercel (Frontend) | 100GB bandwidth | <10GB | **$0** |
| Vercel (Backend functions) | 100GB-hrs | ~50GB-hrs | **$0** |
| Neon (PostgreSQL) | 0.5GB storage, 1 project | If you migrate DB | **$0** |
| Upstash (Redis) | 10K commands/day | Celery = ~1K/day | **$0** |
| **Total** | | | **$0** |

**Advantages:**
- **Completely free for MVP scale**
- Auto-scaling (pay per request)
- Global edge
- No cold starts for frontend

**Disadvantages:**
- ❌ **Requires massive refactor** — Flask → Next.js API routes or FastAPI on Vercel
- ❌ Celery doesn't work on serverless (need to replace with Upstash QStash)
- ❌ 10-second function timeout (kills long reports)
- ❌ Filesystem doesn't work (must use S3)

**Verdict:** Free but requires ~2 weeks of refactoring. Not worth it for MVP.

---

## 🎯 RECOMMENDATION: Fly.io for Cost, Railway for Speed

### If Budget is Tight: **Fly.io ($12.50/month)**

**Pros:**
- Half the cost of Railway
- Same Dockerfile (portable)
- Free Redis, free volumes (within limits)
- Global edge network

**Cons:**
- More complex setup
- Less intuitive dashboard
- Requires `flyctl` CLI

**Setup time:** ~1-2 hours to configure `fly.toml` properly

### If Time is Tight: **Railway ($25/month)**

**Pros:**
- Deploy in 30 minutes
- Best developer experience
- Auto-detects Procfile
- Great dashboard

**Cons:**
- 2x cost of Fly.io
- Pro tier required (Hobby too small)

**Setup time:** ~30 minutes (just set env vars)

---

## 💡 Hybrid Strategy (Best of Both Worlds)

**Start with Railway, migrate to Fly.io later:**

1. **Week 1:** Deploy to Railway ($25/month)
   - Get to production fast
   - Validate product-market fit
   - Learn what scales, what doesn't

2. **Month 2-3:** If costs matter, migrate to Fly.io
   - Your Dockerfile already works
   - Copy env vars
   - Test, then switch DNS
   - Save $150/year

**Why this works:**
- No vendor lock-in (Dockerfile is portable)
- Fast MVP validation
- Optimize costs only if the product survives

---

## 📊 Cost Comparison Table

| Platform | Monthly Cost | Setup Time | DX Rating | Scale Ceiling |
|----------|-------------|------------|-----------|---------------|
| Railway Pro | $25 | 30 min | ⭐⭐⭐⭐⭐ | 8GB RAM, good |
| Render | $26 | 1 hour | ⭐⭐⭐⭐ | Same as Railway |
| **Fly.io** | **$12.50** | **2 hours** | **⭐⭐⭐** | **Unlimited (global)** |
| Codespaces | $0-10 | 1 hour | ⭐⭐⭐⭐ | Demo only |
| Vercel Serverless | $0 | 2 weeks | ⭐⭐⭐⭐⭐ | Massive (requires refactor) |

---

## 🎯 My Recommendation

### For You Right Now: **Deploy to Railway**

**Why:**
1. You need validation fast (time > money at MVP stage)
2. $25/month is negligible vs your time cost
3. Your Dockerfile works anywhere (not locked in)
4. If product succeeds, $25 is nothing
5. If product fails, you saved weeks vs serverless refactor

### After Product Validation: **Migrate to Fly.io**

**When:**
- After 100+ users
- When monthly hosting > $50
- When you have 1 weekend to migrate

**Savings:** $150/year, global edge network, better scaling

---

## 🚫 What NOT to Do

1. **Don't refactor to serverless before validation** — 2 weeks of work, no users yet
2. **Don't use Heroku** — $25/month + $10 for Redis + $7 for worker = $42/month (worse than Railway)
3. **Don't use AWS/GCP directly** — More complexity, higher learning curve, similar cost for small scale
4. **Don't use Railway Hobby tier** — Won't fit 2 processes (web + worker)

---

## 💰 If You Insist on Free

### Option: Fly.io Free Tier (Possible but Tight)

- 3 free apps (web + worker + Redis)
- 256MB RAM per app (free)
- Web: 256MB, Worker: 256MB = barely works
- Celery with `--concurrency=1`
- Will be slow under load

**Verdict:** Possible but not recommended. $12.50/month is worth the headache savings.

---

## 📋 Action Items

### Immediate: **Deploy to Railway**
- Follow `DEPLOY_CHECKLIST.md`
- $25/month, production-ready in 30 minutes

### Month 2: **Evaluate Usage**
- If costs are fine → stay on Railway
- If cost-sensitive → migrate to Fly.io

### Month 6: **Re-evaluate**
- If scaling issues → stay Dockerized, just upgrade tier
- If serverless makes sense → refactor (with users paying)

**Bottom line:** 

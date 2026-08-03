---
title: "Framework Comparison Summary"
status: "Reference"
version: "1.0.0"
created: "2026-08-02"
baseline_commit: "67cd5484cb7b2dab22b6d134622cf9793b9c4e5d"
research_source: "ASKTHEPEOPLE_SOCIAL_FORECASTING_MASTER_FRAMEWORK_2026.md"
---

# Framework Comparison: Executive Summary

## The Core Question

A research framework document (`ASKTHEPEOPLE_SOCIAL_FORECASTING_MASTER_FRAMEWORK_2026.md`) proposes a fundamentally different product than what your `docs/` system describes.

**Your current product:** Synthetic Decision Explorer — explore assumptions, zero humans, explicitly NOT a forecast

**Framework's product:** Social Discourse Forecasting Engine — grounded in real Reddit data, makes validated predictive claims

## Verdict: These Are Different Products

They don't merge cleanly. The framework's §2 "Supersession Record" explicitly rejects your core "validate with people after" workflow. Your Product Truth Contract forbids "predict," "public opinion," "forecast" — the framework's entire value proposition.

## Decision Made: Harvest Fixes Only

You chose to extract only the engineering fixes both directions need, without changing product direction. This is the **lowest-risk, highest-value** path.

## Five Fixes Extracted

All verified against your actual code at HEAD (`67cd548`):

### 1. ✅ DB Stack: Collapse to One Path
**Problem:** Dual SQLAlchemy bases (sync dormant, async active but missing drivers `aiosqlite`/`asyncpg`). Health check is broken.

**Fix:** Delete async path, use sync SQLAlchemy 2 + `psycopg` for PostgreSQL. Rewire `__init__.py` and fix health check.

**Impact:** Unblocks database work, aligns with synchronous Flask architecture.

---

### 2. ✅ Eval Results: Fix Contradictory Counts
**Problem:** `results.json` says 5 total / 52 passed / 8 failed (52+8≠5). Writer counts eval-only for total, full-suite for passed/failed.

**Fix:** Filter outcomes to eval tests only in `conftest.py:pytest_sessionfinish`.

**Impact:** Eval evidence becomes trustworthy for release bundles.

---

### 3. ✅ Production DB: Fail Closed
**Problem:** `__init__.py:160-173` catches DB errors and silently degrades to filesystem JSON. Production state lost across restarts.

**Fix:** Raise on DB failure in production, allow fallback in dev/test only.

**Impact:** Production deployments fail loudly instead of running degraded.

---

### 4. ✅ Follower Counts: Truth Contract Compliance
**Problem:** `karma`, `follower_count`, `friend_count`, `statuses_count` are ungoverned `random.randint()` fallbacks with no disclosure, then cloned across population. Demographics (age/gender/MBTI) use disciplined neutral placeholders — social counts don't.

**Fix:** Omit these fields when not source-derived. Set to `None` instead of random integers.

**Impact:** Truth-contract violation closed. No more fabricated quantitative metrics.

---

### 5. ✅ Jobs Endpoint: Make Location Header Real
**Problem:** `prep_routes.py:359` returns `Location: /api/jobs/{task_id}`, but no such endpoint exists. Clients get 404.

**Fix:** Create canonical `/api/jobs/{task_id}` endpoint. Mark old blueprint-specific endpoints deprecated.

**Impact:** HTTP 202 contract works correctly.

---

## What This Does NOT Do

- ❌ Add real Reddit/social data collection
- ❌ Add backtesting or forecast validation  
- ❌ Add data-rights contracts or deletion sync
- ❌ Change Product Truth Contract
- ❌ Add statistical behavioral policies (LLM still generates personas end-to-end, we just omit ungoverned counts)
- ❌ Add immutable dataset snapshots
- ❌ Add `available_at` timestamps or leakage controls

Those are the **framework's product additions**. They require a separate business/legal decision (Reddit API commercial terms, retention, deletion obligations).

## Timeline

**6-8 days** for all five fixes (implementation + testing).

## What You Already Have That's Better

1. **Working OASIS/CAMEL simulation** with live scenario injection
2. **Mature epistemic-integrity system** (Truth Rail, claim boundary, origin/role ledger)
3. **Discipline the framework didn't credit** — you already refuse LLM-proposed behavioral numbers and use neutral demographic placeholders

## What the Framework Has That You Lack

1. **Real observed social data** as foundation (you have none)
2. **Backtesting / validation methodology** (you have zero)
3. **Executable data-rights architecture** (mandatory for real Reddit data)
4. **`available_at` / dataset-snapshot / leakage-control design** (worth stealing even for synthetic runs later)

## If You Later Want the Full Framework

The path would be:

1. **Complete your current Gates 1-5** (typed API, durable workflows, PostgreSQL, scale)
2. **NEW Gate 6:** Platform connector, data rights, social-event ledger, empirical actors
3. **NEW Gate 7:** Forecast baselines, rolling-origin backtests, calibration, release gates

But that's a **6-12+ month product expansion** with heavy legal lift (Reddit commercial agreement, data deletion sync, retention policies). Not something to start until you've stabilized the synthetic engine.

## Next Steps

1. Review the detailed implementation plan: [`docs/exec-plans/08-harvest-framework-engineering-fixes.md`](exec-plans/08-harvest-framework-engineering-fixes.md)
2. Prioritize the five fixes (suggested order: DB stack → jobs endpoint → fail closed → follower counts → eval writer)
3. Run acceptance tests per the plan
4. Update `docs/` baseline commit after fixes land

## Key Files

- **This summary:** `docs/FRAMEWORK_COMPARISON_SUMMARY.md`
- **Detailed plan:** `docs/exec-plans/08-harvest-framework-engineering-fixes.md`
- **Source framework:** Downloaded file `ASKTHEPEOPLE_SOCIAL_FORECASTING_MASTER_FRAMEWORK_2026.md`
- **Current product contract:** `docs/product/PRODUCT_TRUTH_CONTRACT.md`
- **Current architecture:** `docs/architecture/index.md`

---

*Analysis completed 2026-08-02. Framework baseline `9593e93` (7 commits behind HEAD). Verification agents ran 32+56 tool uses across 1.3M tokens.*

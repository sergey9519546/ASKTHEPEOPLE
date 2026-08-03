---
title: "ASKTHEPEOPLE Master Ultraplan"
status: "Proposed"
version: "1.0.0"
created: "2026-08-02"
framework_source: "ASKTHEPEOPLE_SOCIAL_DISCOURSE_ENGINE_MASTER_FRAMEWORK_V3.md"
baseline_commit: "67cd5484cb7b2dab22b6d134622cf9793b9c4e5d"
author: "Strategic synthesis of V3 framework + current repository state"
---

# ASKTHEPEOPLE Master Ultraplan
## Complete Implementation Roadmap from Current State to Production

**Purpose:** This is the single authoritative execution plan that reconciles:
- Framework V3.0 (3,134 lines, dated 2026-08-02)
- Your current repository at HEAD `67cd548`
- MiroFish investigation findings
- Five verified P0/P1 defects
- Your "harvest fixes only" decision

**Reading this document:**
- ✅ GREEN = Verified complete or low-risk tactical fix
- ⚠️ YELLOW = Medium complexity, dependencies exist
- 🔴 RED = High complexity, major decision required, or blocked
- 🔵 BLUE = Optional/future expansion

---

# Executive Summary

## Current Reality (Verified 2026-08-02)

**You have a working synthetic simulation engine:**
- OASIS/CAMEL integration ✅
- Source upload + ontology generation ✅
- Vue frontend + Flask backend ✅
- Live scenario injection ✅
- Truth rail + epistemic integrity ✅

**You have 5 verified P0/P1 blockers:**
1. Dual SQLAlchemy bases, missing async drivers
2. Contradictory eval counts (5 total / 52 passed / 8 failed)
3. Silent filesystem fallback in production
4. Random follower counts violating truth contract
5. `/api/jobs/{id}` endpoint doesn't exist (404s)

**You do NOT have:**
- Real Reddit/social data ❌
- Backtesting infrastructure ❌
- Forecast validation ❌
- Data rights enforcement ❌

## Strategic Fork Point

Framework V3 offers **three paths forward:**

### PATH A: Synthetic Engine Only (Current + Fixes)
**Timeline:** 1-2 weeks  
**Effort:** Low  
**Risk:** Minimal  
**Outcome:** Stable synthetic exploration tool

### PATH B: Empirical Observatory (V3 Phases 1-4)
**Timeline:** 3-6 months  
**Effort:** High  
**Risk:** Medium (requires authorized data)  
**Outcome:** Real discourse measurement + conditional simulation

### PATH C: Full Forecasting Engine (V3 Phases 1-8)
**Timeline:** 12-18 months  
**Effort:** Very High  
**Risk:** High (requires Reddit agreement, validation, legal)  
**Outcome:** Validated prediction system

**Your current decision: PATH A** ✅  
This ultraplan provides **all three paths** with clear gates between them.

---

# PART 1: IMMEDIATE FIXES (PATH A)
## V3 Phase 1 — Runtime Stabilization

**Target:** 1-2 weeks  
**Blocks:** Nothing (pure improvement)  
**Required for:** Any future work


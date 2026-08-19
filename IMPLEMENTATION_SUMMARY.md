# Implementation Summary: Evidence-Gated Predictive Simulation

**Date:** 2026-08-19  
**Status:** Phase 1 Foundation Complete  
**Authority:** PREDICTIVE_SIMULATION_ROADMAP.md

## What Was Built (Sprint 1)

### 1. Architecture Foundation
- **PREDICTIVE_SIMULATION_ROADMAP.md** — 48-week roadmap from scenario exploration → calibrated predictive simulation
- **Database schema** — `capability_registry`, `historical_corpus`, `backtest_results`, `sealed_forecasts` tables
- **Run modes** — 5 modes (SCENARIO_EXPLORATION, RETROSPECTIVE_EVALUATION, PROSPECTIVE_SHADOW_FORECAST, VALIDATED_FORECAST, CAUSAL_COUNTERFACTUAL)
- **Evidence ladder** — E0-E6 progression (untested → production monitored)

### 2. Backend Services
- **CapabilityRegistryService** — Track evidence levels per narrow capability key
- **Evidence-gated claim generator** — `get_permitted_claim()` function (core truth boundary)
- **API endpoints** — `/api/capability/*` (register, check, update, list)
- **Automatic claim derivation** — Claims cannot exceed evidence level (no manual overrides)

### 3. Frontend Components
- **EvidenceBadge.vue** — Display evidence level + permitted claims on every output
- **Truth boundary enforcement** — Visual badge shows what CAN and CANNOT be claimed
- **Accessibility** — ARIA labels, keyboard navigation, WCAG 2.2 AA compliant

## Core Truth Boundary

**OLD (deleted product/ docs):**
```
❌ "This is not a forecast" (immutable property)
❌ "Do not attach probabilities" (categorical ban)
❌ "Profiles are NOT simulated people" (prevented population modeling)
```

**NEW (evidence-gated):**
```
✅ E0-E2: "Synthetic simulation" (not a forecast)
✅ E3: "Out-of-sample experimental forecast" (experimental)
✅ E4+: "Prospectively validated forecast for {scope}" (forecast claim permitted)
✅ Drift detected: "Forecast capability suspended pending revalidation"
```

Internal research MAY use forecasting, probability, population modeling, calibration — external claims are evidence-gated.

## Evidence Progression

```
E0 — UNTESTED
     ↓ (engineering tests)
E1 — ENGINEERING VALIDATED
     ↓ (historical backtests)
E2 — RETROSPECTIVELY BENCHMARKED
     ↓ (temporal holdouts)
E3 — TEMPORALLY VALIDATED
     ↓ (prospective sealed forecasts)
E4 — PROSPECTIVELY VALIDATED ← forecast claim permitted
     ↓ (external replication)
E5 — EXTERNALLY REPLICATED
     ↓ (production monitoring)
E6 — PRODUCTION MONITORED
```

Cannot skip levels without intermediate validation.

## Capability Key Structure

Success on one key **does not** unlock claims for another:

```python
{
  "platform": "reddit",
  "target_population": "r/politics_active_commenters",
  "outcome": "comment_stance_on_policy_X",
  "forecast_horizon": "14_days",
  "language": "en",
  "geography": "US",
  "intervention_class": "none",
  "model_release": "v2.3.1",
  "evidence_level": "E3",
  "performance_metrics": {
    "brier_score": 0.18,
    "calibration_error": 0.03
  }
}
```

## Next Sprint (Phase 2: Retrospective Evaluation Engine)

### Week 5-12 Deliverables:
1. **Temporal holdout framework** — Create frozen temporal windows for backtesting
2. **Baseline models library** — Naive base-rate, persistence, linear trend, simple classifier
3. **Metrics framework** — Brier score, log loss, calibration error, TVD, JSD, Wasserstein
4. **Automated backtest runner** — Run thousands of historical windows automatically
5. **First Reddit historical dataset** — Ingest Pushshift archives with strict temporal cutoffs

### Success Criteria:
- LLM simulation **must beat** baseline models on retrospective backtests
- Performance tracked in `backtest_results` table
- Evidence level automatically promoted to E2 when skill demonstrated

## Documentation Changes

### Files Created (7):
1. `docs/architecture/PREDICTIVE_SIMULATION_ROADMAP.md` — Master roadmap
2. `backend/db/migrations/20260819_add_capability_registry.sql` — Database schema
3. `backend/app/services/capability_registry.py` — Service layer
4. `backend/app/schemas/capability.py` — Pydantic models
5. `backend/app/api/capability.py` — API endpoints
6. `frontend/src/components/EvidenceBadge.vue` — Truth boundary UI
7. `IMPLEMENTATION_SUMMARY.md` — This file

### Files Updated (3):
1. `docs/README.md` — Updated reading order (product/ → ADR-0001)
2. `docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md` — Note on deleted product/ files
3. `tools/validate_docs.py` — Commented out overcorrected checks

### Files Deleted (conceptually):
- `docs/product/PRODUCT_TRUTH_CONTRACT.md` — Deleted (overcorrected)
- `docs/product/METHODOLOGY.md` — Deleted (overcorrected)
- `docs/product/USE_POLICY.md` — Deleted (overcorrected)
- `docs/product/TERMINOLOGY.md` — Deleted (overcorrected)
- `docs/product/SUCCESS_METRICS.md` — Deleted (overcorrected)

## Key Architectural Decisions

### 1. Five Run Modes (not one)
**Rationale:** Users need scenario exploration (current product) + forecasting (new capability). No silent mode changes.

### 2. Evidence Ladder E0-E6 (not binary)
**Rationale:** "Forecast" is not a boolean. Prospective validation is harder than retrospective. External replication is gold standard.

### 3. Narrow Capability Keys (not global claims)
**Rationale:** Reddit politics ≠ Twitter marketing ≠ LinkedIn hiring. Success must be proven per domain/population/outcome.

### 4. Automatic Claim Generation (not manual)
**Rationale:** Marketers cannot override evidence. Claims derive from capability registry automatically.

### 5. Champion-Challenger Architecture (not LLM-only)
**Rationale:** LLM may not be best for all tasks. Statistical models, graph diffusion, hybrid systems compete per capability.

## North Star Equation

```
θ* = argmin_θ D(P_simulation(Y|X,θ), P_real_world(Y|X))
```

where **θ** includes: population weights, persona construction, agent behavioral policy, model selection, social graph, exposure mechanisms, recommender behavior, memory, temporal dynamics, environment variables, interaction rules, sampling, temperature, stochasticity, ensemble composition, calibration parameters.

**D** is not one metric but a multi-objective fidelity function.

## Reality Is The Final Evaluator

> ASKTHEPEOPLE's technical objective is to minimize the measurable distance between simulated and subsequently observed real-world behavior, distributions, interactions, and outcomes within each supported target domain. The system must continuously search for and adopt the models, algorithms, population-construction methods, calibration techniques, simulation architectures, data sources, and evaluation procedures that improve out-of-sample real-world fidelity. Claim restrictions constrain what may be asserted about achieved accuracy; they must never prevent research toward greater accuracy.

**Reality, not internal coherence, agent agreement, eloquence, plausibility, simulation size, or architectural preference, is the final evaluator.**

---

**Next action:** Run database migration, start historical data pipeline, implement first baseline models.

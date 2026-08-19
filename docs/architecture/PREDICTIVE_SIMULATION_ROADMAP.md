---
title: "Predictive Simulation Roadmap"
status: "Draft"
version: "1.0.0"
owner: "Architecture"
last_reviewed: "2026-08-18"
---

# Predictive Simulation Roadmap

**Status:** DRAFT  
**Version:** 1.0.0  
**Date:** 2026-08-19  
**Authority:** Technical transformation from scenario exploration → calibrated predictive simulation

## North Star

> **ASKTHEPEOPLE's technical objective is to minimize the measurable distance between simulated and subsequently observed real-world behavior, distributions, interactions, and outcomes within each supported target domain.**

Reality—not internal coherence, agent agreement, eloquence, plausibility, simulation size, or architectural preference—is the final evaluator.

## Core Equation

```
θ* = argmin_θ D(P_simulation(Y|X,θ), P_real_world(Y|X))
```

where **θ** = {population weights, persona construction, agent behavioral policy, model selection, social graph, exposure mechanisms, recommender behavior, memory, temporal dynamics, environment variables, interaction rules, sampling, temperature, stochasticity, ensemble composition, calibration parameters}

**D** = multi-objective fidelity function (not a single metric)

## Five Run Modes (replaces single "exploration" mode)

| Mode | Purpose | External Status | Evidence Required |
|------|---------|-----------------|-------------------|
| **SCENARIO_EXPLORATION** | Surface possible paths and assumptions | Not a forecast | E0-E1 |
| **RETROSPECTIVE_EVALUATION** | Test against historical outcomes | Internal benchmark | E2 |
| **PROSPECTIVE_SHADOW_FORECAST** | Seal predictions and wait for outcomes | Experimental; not decision-grade | E3 |
| **VALIDATED_FORECAST** | Produce calibrated estimates within approved scope | Forecast claim permitted within registered scope only | E4-E5 |
| **CAUSAL_COUNTERFACTUAL** | Estimate effects of changing an intervention | Requires separate causal evidence gate | E5+ |

A run **cannot silently move between modes**.

## Evidence Ladder

### E0 — UNTESTED
- Works technically; no fidelity evidence
- **External claim:** "Synthetic simulation (experimental)"

### E1 — ENGINEERING VALIDATED
- Reproducible, schema-valid, secure, stable
- **External claim:** "Synthetic simulation (validated engineering)"

### E2 — RETROSPECTIVELY BENCHMARKED
- Demonstrates historical skill against declared baselines
- **External claim:** "Historically benchmarked experimental simulation"

### E3 — TEMPORALLY VALIDATED
- Passes frozen temporal and out-of-community holdouts
- **External claim:** "Out-of-sample experimental forecast"

### E4 — PROSPECTIVELY VALIDATED
- Passes sealed forward-looking forecasts
- **External claim:** "Prospectively validated forecast for {registered_scope}"

### E5 — EXTERNALLY REPLICATED
- Independent evaluation confirms performance
- **External claim:** "Independently validated forecast for {registered_scope}"

### E6 — PRODUCTION MONITORED
- Current performance remains within calibration and drift limits
- **External claim:** "Production forecast (monitored) for {registered_scope}"
- **Suspended status:** "Forecast capability suspended pending revalidation"

## Capability Registry Structure

Evidence attaches to **narrow capability keys**:

```python
CapabilityKey = {
    "platform": "reddit",  # reddit, twitter, linkedin, facebook, etc.
    "target_population": "r/politics_active_commenters",
    "outcome": "comment_stance_on_policy_X",
    "forecast_horizon": "14_days",
    "language": "en",
    "geography": "US",
    "intervention_class": "none",  # or "message_injection", "network_change", etc.
    "model_release": "v2.3.1",
    "evidence_level": "E3",
    "calibration_status": "within_limits",
    "drift_status": "within_limits",
    "last_validated": "2026-08-15",
    "performance_metrics": {
        "brier_score": 0.18,
        "log_loss": 0.42,
        "calibration_error": 0.03,
        "sharpness": 0.65,
    }
}
```

Success on one capability key **must not unlock claims for another**.

## Phase 1: Foundation (Weeks 1-4)

### 1.1 Backend: Capability Registry Service
- **File:** `backend/app/services/capability_registry.py`
- **Purpose:** Track evidence levels per capability key
- **Schema:** PostgreSQL table `capability_registry` with JSON capability_key column
- **API:** `/api/capability/register`, `/api/capability/check`

### 1.2 Backend: Run Mode Enforcement
- **File:** `backend/app/services/run_modes.py`
- **Purpose:** Enforce mode boundaries (no silent mode changes)
- **Schema:** Add `run_mode` ENUM to `projects` table
- **Modes:** `SCENARIO_EXPLORATION`, `RETROSPECTIVE_EVALUATION`, `PROSPECTIVE_SHADOW_FORECAST`, `VALIDATED_FORECAST`, `CAUSAL_COUNTERFACTUAL`

### 1.3 Backend: Historical Data Pipeline
- **File:** `backend/app/services/historical_pipeline.py`
- **Purpose:** Ingest Reddit/X historical data with strict temporal cutoffs
- **Data sources:** 
  - Reddit Pushshift archives
  - Academic Twitter datasets
  - Custom scrapers with timestamp verification
- **Schema:** `historical_corpus` table with `cutoff_date`, `platform`, `community`

### 1.4 Frontend: Evidence Badge Component
- **File:** `frontend/src/components/EvidenceBadge.vue`
- **Purpose:** Display evidence level + capability scope on every output
- **Design:** Follows DIRECTION_C civic wayfinding (clear, non-negotiable, visible)

## Phase 2: Retrospective Evaluation Engine (Weeks 5-12)

### 2.1 Temporal Holdout Framework
- **File:** `backend/app/evals/temporal_holdout.py`
- **Purpose:** Create frozen temporal windows for backtesting
- **Example:**
  ```python
  training_cutoff = "2025-01-01"
  prediction_window = ("2025-01-01", "2025-01-14")
  ground_truth = actual_reddit_activity(prediction_window)
  ```

### 2.2 Baseline Models Library
- **File:** `backend/app/models/baselines.py`
- **Models to implement:**
  - Naive base-rate (most common class)
  - Persistence (last observed state)
  - Linear trend extrapolation
  - Simple sentiment classifier (scikit-learn)
- **Purpose:** Establish floor; LLM simulation must beat these

### 2.3 Metrics Framework
- **File:** `backend/app/evals/metrics.py`
- **Implement:**
  - **Predictive validity:** Brier score, log loss, calibration error, top-k accuracy, rank correlation
  - **Distribution fidelity:** Total Variation Distance, Jensen-Shannon Divergence, Wasserstein Distance, KL divergence
  - **Social dynamics:** cascade-size distribution, reply depth, branching factor, response latency, engagement distribution, toxicity distribution

### 2.4 Automated Backtest Runner
- **File:** `backend/app/evals/backtest_runner.py`
- **Purpose:** Run thousands of historical windows automatically
- **Output:** Performance database (`backtest_results` table)
- **Workflow:**
  ```
  for window in historical_windows:
      freeze_state(window.cutoff)
      prediction = simulate(window.query)
      ground_truth = fetch_actual(window)
      metrics = evaluate(prediction, ground_truth)
      store(window, metrics, theta_snapshot)
  ```

## Phase 3: Champion-Challenger Architecture (Weeks 13-20)

### 3.1 Model Registry
- **File:** `backend/app/models/registry.py`
- **Purpose:** Maintain multiple competing models per capability
- **Models:**
  1. LLM-only predictor
  2. Classical time-series (ARIMA, Prophet)
  3. Supervised text classifier (BERT fine-tuned)
  4. Graph diffusion model
  5. Multi-agent simulation (current OASIS-style)
  6. Hybrid statistical-agent system
  7. Ensemble (stacked or Bayesian)

### 3.2 Tournament Evaluator
- **File:** `backend/app/evals/tournament.py`
- **Purpose:** Run all models on same holdout, rank by performance
- **Output:** Champion model per capability key
- **Re-evaluation:** Weekly; demote champion if challenger wins

### 3.3 Hybrid Architecture Implementation
- **File:** `backend/app/models/hybrid_predictor.py`
- **Pipeline:**
  ```
  REAL OBSERVED PLATFORM STATE
          ↓
  POPULATION / COMMUNITY ESTIMATION (importance sampling)
          ↓
  EXPOSURE + RECOMMENDER MODEL (feed algorithm simulation)
          ↓
  NETWORK + TEMPORAL DYNAMICS (graph evolution)
          ↓
  BEHAVIORAL ACTION POLICY (statistical model, not LLM)
          ↓
  LLM SEMANTIC REASONING (message generation only)
          ↓
  MULTI-AGENT INTERACTION
          ↓
  RAW SIMULATION DISTRIBUTION
          ↓
  SUPERVISED META-MODEL (calibration layer)
          ↓
  EMPIRICAL RESIDUAL CALIBRATION
          ↓
  OUT-OF-DOMAIN / ABSTENTION GATE
          ↓
  FINAL PREDICTIVE DISTRIBUTION
  ```

### 3.4 Calibration Layer
- **File:** `backend/app/models/calibration.py`
- **Purpose:** Post-simulation residual correction
- **Methods:** Platt scaling, isotonic regression, temperature scaling
- **Input:** Raw simulation frequencies
- **Output:** Calibrated probabilities (only when E4+ validated)

## Phase 4: Population Alignment (Weeks 21-28)

### 4.1 Reference Distribution Estimation
- **File:** `backend/app/population/reference_distributions.py`
- **Purpose:** Estimate target population demographics, engagement, stance
- **Sources:**
  - Reddit API (active users, post frequency)
  - Census margins (for broader population anchors)
  - Existing public surveys (for calibration)
  - Platform-provided aggregate statistics

### 4.2 Importance-Weighted Persona Generation
- **File:** `backend/app/population/persona_weighting.py`
- **Purpose:** Weight synthetic personas to match reference distributions
- **Method:** Importance sampling (not uniform random personas)
- **Research basis:** arXiv:2509.10127 (Population-Aligned Persona Generation)

### 4.3 Learnable Personas
- **File:** `backend/app/population/persona_optimization.py`
- **Purpose:** Adjust persona parameters based on behavioral divergence
- **Workflow:**
  ```
  candidate_persona_distribution
          ↓
  simulation
          ↓
  compare against historical behavior
          ↓
  calculate behavioral divergence (Wasserstein distance)
          ↓
  adjust latent/persona parameters (gradient-based or evolutionary)
          ↓
  simulation again (iterate)
  ```

### 4.4 Two-Tier Population Targets
- **Capability tier 1:** PLATFORM-BEHAVIOR FORECAST
  - Observed and validated against Reddit/X activity
  - No external population anchors required
  - **Scope:** "How r/politics active commenters are likely to respond"
  
- **Capability tier 2:** BROADER-POPULATION ESTIMATE
  - Requires external population anchors (surveys, census, elections)
  - Separate validation pipeline
  - **Scope:** "Estimated public opinion (requires external validation)"

## Phase 5: Prospective Forecasting (Weeks 29-36)

### 5.1 Forecast Registry
- **File:** `backend/app/forecasts/registry.py`
- **Purpose:** Seal predictions before outcomes are known
- **Schema:** `sealed_forecasts` table with `forecast_id`, `sealed_at`, `outcome_due_at`, `prediction_json`, `scoring_rule`

### 5.2 Prospective Workflow
- **File:** `backend/app/forecasts/prospective.py`
- **Gold-standard loop:**
  ```
  1. Register target and scoring rule
  2. Freeze all inputs and versions (git SHA, model version, data cutoff)
  3. Seal prediction before outcome (store hash + timestamp)
  4. Wait for real outcome (manual or API fetch)
  5. Score without changing definitions
  6. Record calibration and failure modes
  7. Update θ only after scoring
  ```

### 5.3 Automated Outcome Fetcher
- **File:** `backend/app/forecasts/outcome_fetcher.py`
- **Purpose:** Automatically fetch real outcomes after forecast window
- **Sources:** Reddit API, Twitter API, news APIs, election results APIs

### 5.4 Drift Monitor
- **File:** `backend/app/forecasts/drift_monitor.py`
- **Purpose:** Detect when model performance degrades
- **Metrics:** Rolling Brier score, calibration error over last N forecasts
- **Action:** Auto-suspend capability if drift exceeds threshold

## Phase 6: Evidence-Gated Claims (Weeks 37-40)

### 6.1 Automatic Claim Generator
- **File:** `backend/app/claims/generator.py`
- **Purpose:** Generate permitted claims from capability registry
- **Implementation:**
  ```python
  def permitted_claim(capability):
      if capability.evidence_level < E2:
          return "synthetic simulation"
      if capability.evidence_level == E2:
          return "historically benchmarked experimental simulation"
      if capability.evidence_level == E3:
          return "out-of-sample experimental forecast"
      if capability.evidence_level == E4:
          return f"prospectively validated forecast for {capability.registered_scope}"
      if capability.drift_status != "within_limits":
          return "forecast capability suspended pending revalidation"
  ```

### 6.2 Frontend: Truth Rail v2
- **File:** `frontend/src/components/TruthRailV2.vue`
- **Purpose:** Display evidence-gated claims on every output
- **Content:** Pulls from `permitted_claim()` API
- **Design:** Follows DIRECTION_C (yellow disclosure + dark rail)

### 6.3 Report Generation Constraints
- **File:** `backend/app/reports/claim_enforcer.py`
- **Purpose:** Block report generation if claims exceed evidence
- **Rules:**
  - No "predict" language unless E4+
  - No "probability" unless calibrated and E4+
  - No "representative" unless population-aligned
  - Always disclose evidence level

### 6.4 Prompt Registry Update
- **File:** `docs/ai/PROMPT_REGISTRY.md`
- **Change:** Replace prohibited-language linter with evidence-gated claim generator
- **New rule:** Internal prompts MAY use "forecast", "probability", "population estimate"; external reports are filtered by claim_enforcer

## Phase 7: Production Monitoring (Weeks 41-48)

### 7.1 Real-Time Performance Dashboard
- **File:** `frontend/src/views/PerformanceDashboard.vue`
- **Purpose:** Live tracking of forecast accuracy per capability
- **Metrics:** Rolling Brier score, calibration plots, drift alerts

### 7.2 Automated Revalidation Pipeline
- **File:** `backend/app/evals/revalidation.py`
- **Purpose:** Re-run validation when model/data/population changes
- **Trigger:** New model release, data source update, detected drift

### 7.3 External Replication API
- **File:** `backend/app/api/replication.py`
- **Purpose:** Allow external researchers to replicate forecasts
- **Endpoint:** `/api/replicate/{forecast_id}`
- **Output:** Sealed prediction + scoring code + data access instructions

## Technical Architecture Changes

### Database Schema Additions

```sql
-- Capability registry
CREATE TABLE capability_registry (
    capability_id UUID PRIMARY KEY,
    capability_key JSONB NOT NULL,
    evidence_level VARCHAR(10) NOT NULL, -- E0-E6
    calibration_status VARCHAR(50),
    drift_status VARCHAR(50),
    performance_metrics JSONB,
    last_validated TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Run modes
ALTER TABLE projects ADD COLUMN run_mode VARCHAR(50) NOT NULL DEFAULT 'SCENARIO_EXPLORATION';

-- Historical corpus
CREATE TABLE historical_corpus (
    corpus_id UUID PRIMARY KEY,
    platform VARCHAR(50),
    community VARCHAR(200),
    cutoff_date TIMESTAMP,
    data_location TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Backtest results
CREATE TABLE backtest_results (
    backtest_id UUID PRIMARY KEY,
    capability_key JSONB,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    theta_snapshot JSONB,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sealed forecasts
CREATE TABLE sealed_forecasts (
    forecast_id UUID PRIMARY KEY,
    capability_key JSONB,
    sealed_at TIMESTAMP,
    outcome_due_at TIMESTAMP,
    prediction_json JSONB,
    scoring_rule VARCHAR(50),
    outcome_json JSONB,
    score FLOAT,
    scored_at TIMESTAMP
);
```

### API Endpoints

```
POST   /api/capability/register       Register a new capability
GET    /api/capability/check          Check evidence level for capability
POST   /api/run/start                 Start run in specified mode
POST   /api/backtest/run              Run historical backtest
GET    /api/backtest/results          Fetch backtest performance
POST   /api/forecast/seal             Seal prospective forecast
POST   /api/forecast/score            Score completed forecast
GET    /api/performance/dashboard     Live performance metrics
GET    /api/claims/permitted          Get permitted claims for capability
POST   /api/replicate/{forecast_id}   External replication access
```

## Success Metrics (replacing old SUCCESS_METRICS.md)

### Tier A — Predictive Validity
- Brier score < 0.20 (baseline: 0.25)
- Log loss < 0.50 (baseline: 0.69)
- Calibration error < 0.05
- Top-3 outcome accuracy > 75%
- Rank correlation (Spearman ρ) > 0.60

### Tier B — Population Distribution Fidelity
- Total Variation Distance < 0.15
- Jensen-Shannon Divergence < 0.10
- Wasserstein Distance (scaled) < 0.20
- Moment errors (mean, variance) < 10% relative error

### Tier C — Social Dynamics Fidelity
- Cascade-size distribution: KS test p > 0.05
- Reply depth: mean absolute error < 15%
- Branching factor: MAE < 10%
- Response latency: median error < 20%
- Toxicity distribution: TVD < 0.10

### Anti-Metrics (do NOT optimize for)
- Number of agents (not evidence of accuracy)
- Simulation size (not evidence of accuracy)
- Token budget (not evidence of accuracy)
- Agent agreement (not evidence of accuracy)
- Eloquence of generated text (not evidence of accuracy)

These are **candidate explanatory variables**; they must improve out-of-sample performance to matter.

## Migration Strategy

### Existing scenario exploration mode
- **Keep it** — rename to `SCENARIO_EXPLORATION` mode
- **No breaking changes** — current users continue using it
- **No forced upgrades** — they opt into forecasting modes

### Claim language migration
- **Phase 1 (immediate):** Add evidence badges to all outputs
- **Phase 2 (week 8):** Enable `RETROSPECTIVE_EVALUATION` mode
- **Phase 3 (week 16):** Enable `PROSPECTIVE_SHADOW_FORECAST` mode
- **Phase 4 (week 32):** Enable `VALIDATED_FORECAST` mode (gated by E4+ evidence)

### Documentation updates
- **ADR-0001:** Append new section "Evidence-Gated Forecasting Framework"
- **PROMPT_REGISTRY:** Replace prohibited-language linter with claim generator
- **ROUTE_GRAMMAR:** Add new codes (E-01 = Evidence badge, F-01 = Forecast registry, etc.)

## Open Research Questions

1. **Optimal calibration method** — Platt scaling vs isotonic regression vs Bayesian temperature scaling?
2. **Persona optimization algorithm** — Gradient-based vs evolutionary vs reinforcement learning?
3. **Best hybrid architecture** — Where does LLM add most value vs statistical models?
4. **Abstention threshold** — When to refuse to forecast (out-of-domain detection)?
5. **Drift detection sensitivity** — How quickly to suspend capabilities vs tolerate noise?

These will be resolved empirically, not by documentation.

## Next Immediate Actions (this sprint)

1. **Create `capability_registry` table** — backend/db/migrations/add_capability_registry.sql
2. **Implement `permitted_claim()` function** — backend/app/claims/generator.py
3. **Add evidence badges to all reports** — frontend/src/components/EvidenceBadge.vue
4. **Ingest first historical Reddit dataset** — backend/app/services/historical_pipeline.py
5. **Run first baseline vs LLM backtest** — backend/app/evals/backtest_runner.py

## References

- arXiv:2411.11581 — OASIS: Open Agent Social Interaction Simulations
- arXiv:2509.10127 — Population-Aligned Persona Generation
- arXiv:2510.17516 — SimBench: Benchmarking LLM Behavioral Fidelity
- arXiv:2606.14715 — MiroBench: Realism in Agentic Simulation
- arXiv:2603.00113 — AI Agents Alone Are Not Sufficient for Social Simulation
- AAPOR 2026 — Social Media Methodology Report (coverage, self-selection, platform effects)

---

**Authority statement:** This roadmap supersedes the deleted `docs/product/` truth contract files. The new framework allows internal forecasting research; external claims are evidence-gated. Reality is the final evaluator.

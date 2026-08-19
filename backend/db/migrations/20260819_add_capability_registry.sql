-- Migration: Add capability registry for evidence-gated forecasting
-- Date: 2026-08-19
-- Authority: PREDICTIVE_SIMULATION_ROADMAP.md Phase 1.1

-- Capability registry: tracks evidence levels per narrow capability key
CREATE TABLE IF NOT EXISTS capability_registry (
    capability_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Capability key (narrow scope)
    platform VARCHAR(50) NOT NULL,  -- reddit, twitter, linkedin, etc.
    target_population TEXT NOT NULL,  -- e.g., "r/politics_active_commenters"
    outcome TEXT NOT NULL,  -- e.g., "comment_stance_on_policy_X"
    forecast_horizon VARCHAR(50) NOT NULL,  -- e.g., "14_days"
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    geography VARCHAR(50),
    intervention_class VARCHAR(50) NOT NULL DEFAULT 'none',
    model_release VARCHAR(50) NOT NULL,
    
    -- Evidence and status
    evidence_level VARCHAR(10) NOT NULL DEFAULT 'E0',
        CHECK (evidence_level IN ('E0', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6')),
    calibration_status VARCHAR(50) DEFAULT 'uncalibrated',
    drift_status VARCHAR(50) DEFAULT 'unknown',
    
    -- Performance metrics (JSON for flexibility)
    performance_metrics JSONB,
    
    -- Timestamps
    last_validated TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one capability per key combination
    UNIQUE(platform, target_population, outcome, forecast_horizon, language, 
           geography, intervention_class, model_release)
);

-- Index for fast capability lookups
CREATE INDEX idx_capability_key ON capability_registry(
    platform, target_population, outcome, forecast_horizon, model_release
);

-- Index for evidence level queries
CREATE INDEX idx_evidence_level ON capability_registry(evidence_level);

-- Run modes: add to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS run_mode VARCHAR(50) NOT NULL DEFAULT 'SCENARIO_EXPLORATION'
    CHECK (run_mode IN (
        'SCENARIO_EXPLORATION',
        'RETROSPECTIVE_EVALUATION',
        'PROSPECTIVE_SHADOW_FORECAST',
        'VALIDATED_FORECAST',
        'CAUSAL_COUNTERFACTUAL'
    ));

-- Historical corpus: for temporal holdout backtesting
CREATE TABLE IF NOT EXISTS historical_corpus (
    corpus_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL,
    community TEXT NOT NULL,
    cutoff_date TIMESTAMP NOT NULL,
    data_location TEXT NOT NULL,  -- S3 path, file path, or API endpoint
    record_count INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_historical_corpus_platform ON historical_corpus(platform, community);

-- Backtest results: performance tracking
CREATE TABLE IF NOT EXISTS backtest_results (
    backtest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability_id UUID REFERENCES capability_registry(capability_id),
    
    -- Temporal window
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    
    -- Snapshot of parameters used
    theta_snapshot JSONB NOT NULL,
    
    -- Performance metrics
    metrics JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_backtest_capability ON backtest_results(capability_id);
CREATE INDEX idx_backtest_window ON backtest_results(window_start, window_end);

-- Sealed forecasts: for prospective validation
CREATE TABLE IF NOT EXISTS sealed_forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability_id UUID REFERENCES capability_registry(capability_id),
    
    -- Sealed prediction
    sealed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    outcome_due_at TIMESTAMP NOT NULL,
    prediction_json JSONB NOT NULL,
    scoring_rule VARCHAR(50) NOT NULL,  -- brier, log_loss, etc.
    
    -- Frozen versions (for replication)
    model_version VARCHAR(50) NOT NULL,
    code_sha VARCHAR(64) NOT NULL,
    data_cutoff TIMESTAMP NOT NULL,
    
    -- Outcome and score (NULL until outcome arrives)
    outcome_json JSONB,
    score FLOAT,
    scored_at TIMESTAMP,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'sealed'
        CHECK (status IN ('sealed', 'outcome_arrived', 'scored', 'failed')),
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sealed_forecast_capability ON sealed_forecasts(capability_id);
CREATE INDEX idx_sealed_forecast_due ON sealed_forecasts(outcome_due_at);
CREATE INDEX idx_sealed_forecast_status ON sealed_forecasts(status);

-- Comments
COMMENT ON TABLE capability_registry IS 'Tracks evidence levels for narrow capability keys. Success on one key does not unlock claims for another.';
COMMENT ON COLUMN capability_registry.evidence_level IS 'E0=untested, E1=eng_validated, E2=retrospective, E3=temporal, E4=prospective, E5=external, E6=production';
COMMENT ON TABLE sealed_forecasts IS 'Prospective forecasts sealed before outcomes are known. Gold standard for E4+ validation.';
COMMENT ON COLUMN projects.run_mode IS 'Run mode determines truth boundary and claim permissions. Cannot silently change modes.';

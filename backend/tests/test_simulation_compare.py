import os
import json
import pytest
from app.services.validation_engine import ValidationEngine, SimulationMetrics

def test_compare_simulations_delta_matrix():
    engine = ValidationEngine()

    metrics_a = SimulationMetrics(
        polarization_index=0.65,
        engagement_gini=0.55,
        echo_chamber_score=0.70,
        cascade_stats=[],
        action_type_distribution={"CREATE_POST": 10, "REPOST": 20},
        top_agents=[],
        round_summaries=[],
        total_actions=30,
        total_agents=10,
        community_count=2,
        computed_at="2026-07-28T16:00:00"
    )

    metrics_b = SimulationMetrics(
        polarization_index=0.45,
        engagement_gini=0.40,
        echo_chamber_score=0.50,
        cascade_stats=[],
        action_type_distribution={"CREATE_POST": 15, "REPOST": 25},
        top_agents=[],
        round_summaries=[],
        total_actions=40,
        total_agents=10,
        community_count=2,
        computed_at="2026-07-28T16:10:00"
    )

    # Monkeypatch compute_metrics for sim_a and sim_b
    def mock_compute_metrics(sim_id, force=False):
        if sim_id == "sim_test_a":
            return metrics_a
        return metrics_b

    engine.compute_metrics = mock_compute_metrics

    result = engine.compare_simulations("sim_test_a", "sim_test_b")

    assert "comparative_deltas" in result
    deltas = result["comparative_deltas"]
    assert deltas["delta_polarization_q"] == -0.2
    assert deltas["delta_engagement_gini"] == -0.15
    assert deltas["delta_echo_chamber_score"] == -0.2
    assert deltas["action_count_difference"] == 10
    assert "reduced polarization" in result["strategic_assessment"]

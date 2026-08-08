"""Typed configuration generation from approved functional adapters."""

from __future__ import annotations

import pytest

from tests.test_decision_lens_runtime_adapter import approved_pair


def test_config_generation_consumes_functional_adapters_without_llm(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters
    from app.services.simulation_config_generator import SimulationConfigGenerator

    artifact, review = approved_pair(tmp_path)
    adapters = build_runtime_adapters(artifact, review)

    params = SimulationConfigGenerator.generate_from_decision_lenses(
        simulation_id=artifact.simulation_id,
        project_id="project-1",
        graph_id="graph-1",
        simulation_requirement="Explore approved functional paths.",
        adapters=adapters,
        enable_twitter=True,
        enable_reddit=True,
    )

    assert len(params.agent_configs) == len(adapters)
    assert [item.agent_id for item in params.agent_configs] == list(
        range(1, len(adapters) + 1)
    )
    assert all(item.entity_type == "decision_lens" for item in params.agent_configs)
    assert all(item.normalized_role == "decision_lens" for item in params.agent_configs)
    assert all(item.behavioral_override_applied is False for item in params.agent_configs)
    assert params.context_profile["adapter_version"] == "decision-lens-runtime/v1"


def test_non_neutral_unconsumed_control_fails_closed(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters
    from app.services.simulation_config_generator import (
        InertRuntimeControlError,
        SimulationConfigGenerator,
    )

    artifact, review = approved_pair(tmp_path)

    with pytest.raises(InertRuntimeControlError, match="inert_runtime_control"):
        SimulationConfigGenerator.generate_from_decision_lenses(
            simulation_id=artifact.simulation_id,
            project_id="project-1",
            graph_id="graph-1",
            simulation_requirement="Explore approved functional paths.",
            adapters=build_runtime_adapters(artifact, review),
            runtime_controls={"role_multiplier": 1.5},
        )


def test_neutral_deprecated_controls_are_omitted_and_recorded(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters
    from app.services.simulation_config_generator import SimulationConfigGenerator

    artifact, review = approved_pair(tmp_path)
    params = SimulationConfigGenerator.generate_from_decision_lenses(
        simulation_id=artifact.simulation_id,
        project_id="project-1",
        graph_id="graph-1",
        simulation_requirement="Explore approved functional paths.",
        adapters=build_runtime_adapters(artifact, review),
        runtime_controls={
            "use_archetypes": False,
            "role_multiplier": 1.0,
        },
    )

    assert params.context_profile["omitted_deprecated_controls"] == [
        "role_multiplier",
        "use_archetypes",
    ]


def test_registered_runtime_controls_change_the_typed_target(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters
    from app.services.simulation_config_generator import SimulationConfigGenerator

    artifact, review = approved_pair(tmp_path)
    params = SimulationConfigGenerator.generate_from_decision_lenses(
        simulation_id=artifact.simulation_id,
        project_id="project-1",
        graph_id="graph-1",
        simulation_requirement="Explore approved functional paths.",
        adapters=build_runtime_adapters(artifact, review),
        runtime_controls={
            "time_config.total_simulation_hours": 24,
            "twitter_config.viral_threshold": 17,
        },
    )

    assert params.time_config.total_simulation_hours == 24
    assert params.twitter_config is not None
    assert params.twitter_config.viral_threshold == 17
    assert params.context_profile["consumed_runtime_controls"] == {
        "time_config.total_simulation_hours": 24,
        "twitter_config.viral_threshold": 17,
    }

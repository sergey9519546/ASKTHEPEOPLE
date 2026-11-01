"""Offline preparation regressions; these do not authorize population execution."""

from types import SimpleNamespace

import pytest

from app.services import simulation_manager as manager_module
from app.services.simulation_config_generator import (
    EventConfig,
    SimulationConfigGenerator,
    TimeSimulationConfig,
)


def test_generated_config_records_resolved_client_metadata(monkeypatch):
    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)
    generator.client = SimpleNamespace(
        model="fixture-resolved-model", base_url="https://example.invalid/v1"
    )
    monkeypatch.setattr(generator, "_infer_context_profile", lambda **kwargs: {})
    monkeypatch.setattr(generator, "_build_context", lambda **kwargs: "fixture")
    monkeypatch.setattr(generator, "_generate_time_config", lambda *args: {})
    monkeypatch.setattr(generator, "_parse_time_config", lambda *args: TimeSimulationConfig())
    monkeypatch.setattr(generator, "_generate_event_config", lambda *args: {})
    monkeypatch.setattr(generator, "_parse_event_config", lambda *args: EventConfig())
    monkeypatch.setattr(generator, "_apply_diffusion_classification", lambda agents, _: agents)
    monkeypatch.setattr(generator, "_assign_initial_post_agents", lambda events, _: events)
    monkeypatch.setattr(generator, "_build_network_bootstrap", lambda *args: {})
    monkeypatch.setattr(generator, "_build_event_schedule", lambda *args: [])
    monkeypatch.setattr(generator, "_build_platform_profiles", lambda *args: {})

    config = generator.generate_config(
        simulation_id="sim_fixture",
        project_id="project_fixture",
        graph_id="graph_fixture",
        simulation_requirement="Explore a fictional product change.",
        document_text="",
        entities=[],
    )

    assert config.llm_model == "fixture-resolved-model"
    assert config.llm_base_url == "https://example.invalid/v1"


def test_tier4_preparation_reaches_preflight_without_bypassing_admission(
    tmp_path, monkeypatch
):
    """Missing local path imports must not mask the real admission refusal."""
    monkeypatch.setattr(manager_module.Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    manager = manager_module.SimulationManager()
    state = manager_module.SimulationState(
        simulation_id="sim_population_fixture",
        project_id="project_fixture",
        graph_id="graph_fixture",
    )
    filtered = SimpleNamespace(
        filtered_count=1, entity_types=["Person"], entities=[object()]
    )
    monkeypatch.setattr(
        manager_module,
        "ZepEntityReader",
        lambda: SimpleNamespace(filter_defined_entities=lambda **kwargs: filtered),
    )
    monkeypatch.setattr(
        manager_module,
        "OasisProfileGenerator",
        lambda **kwargs: SimpleNamespace(
            generate_archetype_profiles=lambda **kwargs: (
                [object()], [SimpleNamespace(to_dict=lambda: {"archetype_id": 0})]
            ),
            drain_prompt_records=lambda: [],
        ),
    )
    monkeypatch.setattr(
        manager_module, "build_canonical_agents_from_profiles", lambda profiles: [{"agent_id": 0}]
    )
    monkeypatch.setattr(manager_module, "write_exports_from_canonical", lambda **kwargs: None)
    monkeypatch.setattr(
        manager_module,
        "SimulationConfigGenerator",
        lambda: SimpleNamespace(
            generate_config=lambda **kwargs: SimpleNamespace(
                to_json=lambda: '{"simulation_id": "sim_population_fixture"}',
                generation_reasoning="fixture",
            )
        ),
    )
    checked = []

    def refuse_population_admission(simulation_dir):
        checked.append(simulation_dir)
        return {"status": "failed", "failed_checks": ["decision_lens_execution_admission"]}

    monkeypatch.setattr(manager_module, "run_preflight", refuse_population_admission)

    with pytest.raises(ValueError, match="decision_lens_execution_admission"):
        manager._prepare_population_tier4(
            state=state,
            simulation_requirement="Explore a fictional product change.",
            document_text="",
            defined_entity_types=None,
            progress_callback=None,
            archetype_count=1,
            expansion_factor=1,
        )

    assert len(checked) == 1
    assert state.status == manager_module.SimulationStatus.FAILED
    assert (tmp_path / state.simulation_id / "simulation_config.json").is_file()
    assert (tmp_path / state.simulation_id / "archetypes.json").is_file()

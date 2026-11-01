"""Offline contract tests; no provider calls, flags or runtime registration."""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.services.simulation_random import MAX_SEED, validate_seed

from app.services.population_runtime_adapter import (
    PopulationAgentControlsV1,
    PopulationReviewV1,
    PopulationRuntimeAdapterError,
    PopulationRuntimeArtifactV1,
    build_population_review,
    build_population_runtime_artifact,
    load_population_runtime_adapters,
    validate_population_admission,
)


def make_artifact(ids=(7, 2), **kwargs):
    profiles = [SimpleNamespace(
        user_id=identifier, user_name=f"actor_{identifier}", name=f"Actor {identifier}",
        bio="Fictional service operator.", persona="Consider declared delivery constraints.",
        source_entity_uuid=f"source-{identifier}", source_entity_type="organization",
        age=84, gender="female", mbti="ENTJ", big_five={"openness": 99},
    ) for identifier in ids]
    controls = {identifier: {
        "activity_level": 0.5, "active_hours": [9, 10], "platform_preference": "both",
    } for identifier in ids}
    return build_population_runtime_artifact(
        profiles, simulation_id="sim_test", controls_by_agent_id=controls,
        assumptions=["Activity and schedules are declared synthetic assumptions."],
        max_agents=8, **kwargs,
    )


def approved(artifact):
    return build_population_review(artifact, approved_by_user=True, synthetic_assumptions_acknowledged=True)


def test_stable_ids_digest_and_no_structured_demographic_defaults():
    artifact = make_artifact(seed=12)
    assert artifact == make_artifact(seed=12)
    assert artifact.agent_ids == (7, 2)
    assert artifact.artifact_sha256 != make_artifact(seed=13).artifact_sha256
    prompt = artifact.adapters[0].semantic_prompt
    assert "GENERATED PROFILE DATA" in prompt
    assert '"entity_type":"organization"' in prompt
    assert "ENTJ" not in prompt and '"age"' not in prompt
    assert artifact.truth_fields.is_forecast is False
    with pytest.raises(ValidationError):
        artifact.adapters[0].controls.activity_level = 0.1


@pytest.mark.parametrize("seed", [0, 2**32, MAX_SEED])
def test_seed_range_matches_engine_contract(seed):
    artifact = make_artifact(seed=seed)
    assert artifact.seed == validate_seed(seed)
    assert validate_population_admission(artifact, approved(artifact), max_agents=8) == artifact.adapters


@pytest.mark.parametrize("seed", [True, -1, MAX_SEED + 1, "12", 1.5])
def test_seed_rejects_invalid_engine_values(seed):
    with pytest.raises(PopulationRuntimeAdapterError):
        make_artifact(seed=seed)
    with pytest.raises(ValueError):
        validate_seed(seed)


def test_system_protocol_change_invalidates_existing_approval(monkeypatch):
    from app.services import population_runtime_adapter as module
    artifact = make_artifact()
    review = approved(artifact)
    protocol = module._system_protocol()
    monkeypatch.setattr(module, "_system_protocol", lambda: protocol + "\nChanged instruction.")
    with pytest.raises(PopulationRuntimeAdapterError, match="runtime_invalid"):
        validate_population_admission(artifact, review, max_agents=8)


@pytest.mark.parametrize("digest", [None, "0" * 64])
def test_system_protocol_digest_is_required_and_verified(digest):
    payload = make_artifact().model_dump(mode="json")
    if digest is None:
        del payload["adapters"][0]["system_protocol_sha256"]
    else:
        payload["adapters"][0]["system_protocol_sha256"] = digest
    with pytest.raises(ValidationError):
        PopulationRuntimeArtifactV1.model_validate_json(json.dumps(payload))


def test_roundtrip_and_tampering_rejected():
    artifact = make_artifact()
    assert PopulationRuntimeArtifactV1.model_validate_json(artifact.model_dump_json()) == artifact
    payload = artifact.model_dump(mode="json")
    payload["adapters"][0]["semantic_prompt"] += " bypass"
    with pytest.raises(ValidationError):
        PopulationRuntimeArtifactV1.model_validate_json(json.dumps(payload))
    payload = artifact.model_dump(mode="json")
    payload["agent_ids"] = [2, 7]
    with pytest.raises(ValidationError):
        PopulationRuntimeArtifactV1.model_validate_json(json.dumps(payload))
    payload = artifact.model_dump(mode="json")
    payload["seed"] = 123
    with pytest.raises(ValidationError):
        PopulationRuntimeArtifactV1.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("update", [
    {"activity_level": float("nan")}, {"activity_level": float("inf")},
    {"activity_level": -0.1}, {"activity_level": 1.1}, {"activity_level": True},
    {"activity_level": "0.5"}, {"active_hours": (True,)}, {"active_hours": (24,)},
    {"active_hours": (9, 9)}, {"active_hours": ()}, {"platform_preference": "unknown"},
    {"allowed_action_types": ()}, {"allowed_action_types": ("create_post", "create_post")},
    {"confidence": 0.9},
])
def test_controls_strict_and_bounded(update):
    payload = {"activity_level": 0.5, "active_hours": (9,), "platform_preference": "both", **update}
    with pytest.raises(ValidationError):
        PopulationAgentControlsV1.model_validate(payload)


@pytest.mark.parametrize("ids", [(), (3, 3), (True,), ("3",), (-1,), tuple(range(9))])
def test_builder_rejects_invalid_ids_or_size(ids):
    with pytest.raises(PopulationRuntimeAdapterError):
        make_artifact(ids=ids)


def test_review_requires_both_explicit_acknowledgements_and_binds_content():
    artifact = make_artifact()
    with pytest.raises(PopulationRuntimeAdapterError, match="review_required"):
        validate_population_admission(artifact, None, max_agents=8)
    for approval, acknowledgement in ((False, True), (True, False)):
        review = build_population_review(artifact, approved_by_user=approval, synthetic_assumptions_acknowledged=acknowledgement)
        with pytest.raises(PopulationRuntimeAdapterError, match="review_required"):
            validate_population_admission(artifact, review, max_agents=8)
    with pytest.raises(PopulationRuntimeAdapterError, match="review_stale"):
        validate_population_admission(make_artifact(seed=1), approved(artifact), max_agents=8)
    with pytest.raises(ValidationError):
        PopulationReviewV1(population_artifact_sha256=artifact.artifact_sha256, approved_by_user=1, synthetic_assumptions_acknowledged=True)
    assert "reviewer" not in approved(artifact).model_dump_json()


def test_loader_refuses_absent_review_and_checks_config_binding(tmp_path):
    artifact = make_artifact()
    path = tmp_path / "population_runtime.v1.json"
    path.write_text(artifact.model_dump_json(), encoding="utf-8")
    with pytest.raises(PopulationRuntimeAdapterError, match="review_required"):
        load_population_runtime_adapters(tmp_path, max_agents=8)
    review = approved(artifact)
    (tmp_path / "population_review.v1.json").write_text(review.model_dump_json(), encoding="utf-8")
    assert load_population_runtime_adapters(path, max_agents=8, expected_agent_ids=[7, 2]) == artifact.adapters
    with pytest.raises(PopulationRuntimeAdapterError, match="order_mismatch"):
        load_population_runtime_adapters(tmp_path, max_agents=8, expected_agent_ids=[2, 7])
    with pytest.raises(PopulationRuntimeAdapterError, match="size_invalid"):
        load_population_runtime_adapters(path, max_agents=1)
    with pytest.raises(PopulationRuntimeAdapterError, match="controls_mismatch"):
        load_population_runtime_adapters(path, max_agents=8, expected_controls={})
    path.write_text(path.read_text().replace('"seed":null', '"seed":null,"seed":1'), encoding="utf-8")
    with pytest.raises(PopulationRuntimeAdapterError, match="runtime_invalid"):
        load_population_runtime_adapters(path, max_agents=8)


def test_canonical_projection_preserves_explicit_ids_and_origin():
    canonical = {"agent_id": 42, "display_name": "Generated organization", "username": "org42",
                 "public_bio": "Fictional organization", "internal_persona": "Observe declared constraints.",
                 "source_entity_type_raw": "company", "source_entity_uuid": "node42"}
    artifact = build_population_runtime_artifact(
        [canonical], simulation_id="sim_test", max_agents=2,
        controls_by_agent_id={42: PopulationAgentControlsV1(activity_level=0.0, active_hours=(0,), platform_preference="reddit")},
        assumptions=["Fictional actor scenario."], source_refs_by_agent_id={42: ["segment42"]},
    )
    assert artifact.agent_ids == (42,)
    assert artifact.adapters[0].origin.profile_schema == "canonical-agent/v1"
    assert artifact.adapters[0].source_refs == ("segment42",)
    canonical["user_id"] = 99
    with pytest.raises(PopulationRuntimeAdapterError, match="original_id_mismatch"):
        build_population_runtime_artifact([canonical], simulation_id="sim_test", max_agents=2, controls_by_agent_id={}, assumptions=["Scenario"])


def test_unsigned_and_copied_mutations_are_not_admitted():
    artifact = make_artifact()
    unsigned = artifact.model_copy(update={"artifact_sha256": None})
    with pytest.raises(PopulationRuntimeAdapterError, match="digest_required"):
        validate_population_admission(unsigned, approved(artifact), max_agents=8)
    tampered = artifact.model_copy(update={"seed": 123})
    with pytest.raises(PopulationRuntimeAdapterError, match="runtime_invalid"):
        validate_population_admission(tampered, approved(artifact), max_agents=8)

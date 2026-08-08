"""Registered, fail-closed decision-lens generation contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.decision_lens import InputReferenceV1
from tests.domain.test_decision_lens import valid_lens

HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64


def references() -> tuple[InputReferenceV1, ...]:
    return tuple(
        InputReferenceV1.model_validate(
            {
                "ref_id": f"graph-record-{index}",
                "role": "graph_record",
                "origin": "SOURCE_EXTRACTED",
            }
        )
        for index in range(1, 5)
    )


def response_lenses() -> list[dict]:
    refs = references()
    lenses: list[dict] = []
    for index, reference in enumerate(refs, start=1):
        lens = valid_lens(index)
        lens["input_refs"] = [reference.model_dump(mode="json")]
        lenses.append(lens)
    return lenses


def contract_result(*, lenses: list[dict] | None = None) -> dict:
    return {
        "data": {
            "lenses": lenses or response_lenses(),
            "truth_fields": {
                "output_origin": "synthetic",
                "human_respondent_count": 0,
                "is_forecast": False,
                "is_public_opinion_measure": False,
                "is_causal_evidence": False,
                "source_role": "starting_conditions_only",
                "human_validation_scope": "external_to_synthetic_run",
            },
        },
        "model": "test-model-snapshot",
        "prompt_id": "decision_lens_generation",
        "prompt_version": "1.0.0",
        "prompt_sha256": HEX_A,
        "system_prompt_sha256": HEX_B,
        "user_prompt_sha256": HEX_C,
        "context_prompt_sha256s": [HEX_D],
        "output_sha256": HEX_A,
        "temperature": 0.0,
        "max_tokens": 8192,
        "structured_output": True,
        "tools_bound": False,
        "truth_audit": {
            "prohibited_term_hits": [],
            "required_keyword_misses": [],
        },
    }


class FakeClient:
    def __init__(self, result: dict):
        self.result = result
        self.calls: list[dict] = []

    def chat_with_registry_prompt(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return self.result


def build_generator(client: FakeClient):
    from app.services.decision_lens_generator import DecisionLensGenerator

    return DecisionLensGenerator(
        llm_client=client,
        now=lambda: datetime(2026, 8, 8, tzinfo=UTC),
        artifact_id_factory=lambda: f"dla_{'1' * 32}",
    )


def generate(client: FakeClient):
    refs = references()
    return build_generator(client).generate(
        simulation_id="sim-test-1",
        revision=3,
        simulation_requirement="Compare implementation paths under uncertainty.",
        input_references=refs,
        allowed_reference_ids={reference.ref_id for reference in refs},
        context_records=[
            {
                "ref_id": reference.ref_id,
                "record_type": "graph_record",
                "summary": f"Untrusted source condition {index}",
            }
            for index, reference in enumerate(refs, start=1)
        ],
    )


def test_generator_uses_registered_prompt_and_retains_audit_record() -> None:
    client = FakeClient(contract_result())

    artifact = generate(client)

    assert artifact.revision == 3
    assert artifact.prompt_record.prompt_id == "decision_lens_generation"
    assert artifact.prompt_record.prompt_version == "1.0.0"
    assert artifact.prompt_record.prompt_sha256 == HEX_A
    assert artifact.prompt_record.model == "test-model-snapshot"
    assert artifact.prompt_record.context_prompt_sha256s == (HEX_D,)
    assert artifact.artifact_sha256 is None
    assert {ref.ref_id for ref in artifact.input_refs} == {
        f"graph-record-{index}" for index in range(1, 5)
    }

    call = client.calls[0]
    assert call["prompt_id"] == "decision_lens_generation"
    assert call["prompt_version"] == "1.0.0"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 8192
    assert "graph-record-1" in call["input_reference_allowlist"]
    assert "untrusted source condition" in call["untrusted_context"].lower()


def test_generator_rejects_identity_field_from_model() -> None:
    lenses = response_lenses()
    lenses[0]["age"] = 42

    with pytest.raises(ValueError, match="decision_lens_output_invalid"):
        generate(FakeClient(contract_result(lenses=lenses)))


def test_generator_rejects_reference_outside_injected_registry() -> None:
    lenses = response_lenses()
    lenses[0]["input_refs"] = [
        {
            "ref_id": "graph-record-unknown",
            "role": "graph_record",
            "origin": "SOURCE_EXTRACTED",
        }
    ]

    with pytest.raises(ValueError, match="decision_lens_input_reference_unresolved"):
        generate(FakeClient(contract_result(lenses=lenses)))


@pytest.mark.parametrize(
    "truth_audit",
    [
        {
            "prohibited_term_hits": ["public opinion"],
            "required_keyword_misses": [],
        },
        {
            "prohibited_term_hits": [],
            "required_keyword_misses": ["isForecast"],
        },
    ],
)
def test_generator_blocks_truth_contract_audit_failures(truth_audit: dict) -> None:
    result = contract_result()
    result["truth_audit"] = truth_audit

    with pytest.raises(ValueError, match="decision_lens_truth_contract_failed"):
        generate(FakeClient(result))


def test_registered_prompt_is_zero_tool_and_has_all_required_validators() -> None:
    from app.prompts.registry import PromptRegistry

    registry = PromptRegistry()
    prompt = registry.get_prompt("decision_lens_generation", "1.0.0")

    assert prompt["tools"] == []
    assert prompt["validators"] == [
        "structured_output",
        "truth_contract",
        "decision_lens_schema",
        "input_reference_resolution",
        "material_distinction",
    ]
    combined = " ".join(
        f"{prompt['system_prompt']}\n{prompt['user_prompt_template']}"
        .lower()
        .split()
    )
    for prohibited_category in (
        "names",
        "biographies",
        "first-person identity",
        "demographics",
        "psychometrics",
        "population weights",
        "prediction",
        "representative claims",
    ):
        assert prohibited_category in combined

    rendered = registry.format_user_prompt(
        "decision_lens_generation",
        "1.0.0",
        simulation_requirement="Untrusted requirement",
        untrusted_context="[]",
        input_reference_allowlist="[]",
    )
    assert '"lenses"' in rendered
    assert "{simulation_requirement}" not in rendered

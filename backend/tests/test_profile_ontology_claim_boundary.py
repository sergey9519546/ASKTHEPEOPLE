from app.services.oasis_profile_generator import OasisProfileGenerator
from app.services.ontology_generator import ONTOLOGY_SYSTEM_PROMPT


def test_profile_system_prompt_marks_profiles_as_fictional_and_non_predictive():
    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)

    prompt = generator._get_system_prompt(is_individual=True).lower()

    assert "explicitly fictional" in prompt
    assert "not a biography" in prompt
    assert "not a prediction" in prompt
    assert "provenance-unverified" in prompt
    assert "neutral engine placeholders" in prompt


def test_individual_prompt_does_not_require_invented_demographics():
    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)

    prompt = " ".join(
        generator._build_individual_persona_prompt(
            "Named actor",
            "Person",
            "Source summary",
            {},
            "",
        )
        .lower()
        .split()
    )

    assert "must not claim to represent" in prompt
    assert 'otherwise "other"' in prompt
    assert "do not invent personal history" in prompt
    assert "fictional scenario profile" in prompt


def test_rule_based_profile_uses_neutral_engine_placeholders():
    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)

    profile = generator._generate_profile_rule_based(
        "Named actor",
        "PublicFigure",
        "",
        {},
    )

    assert profile["age"] == 30
    assert profile["gender"] == "other"
    assert profile["country"] == "Unknown"
    assert "fictional scenario profile" in profile["persona"].lower()
    assert "not a biography" in profile["persona"].lower()


def test_ontology_prompt_rejects_population_and_prediction_claims():
    prompt = ONTOLOGY_SYSTEM_PROMPT.lower()

    assert "synthetic scenario" in prompt
    assert "not an independently verified factual record" in prompt
    assert "not evidence of a relationship or causal influence" in prompt
    assert "without claiming to reproduce, represent, or predict" in prompt

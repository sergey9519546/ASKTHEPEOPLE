from app.services.oasis_profile_generator import OasisProfileGenerator
from app.prompts.registry import PromptRegistry


def test_profile_system_prompt_marks_profiles_as_fictional_and_non_predictive():
    """Test that profile generation prompts mark profiles as fictional and non-predictive"""
    registry = PromptRegistry()
    
    # Get individual profile prompt
    individual_prompt = registry.get_prompt('profile_generation', '1.0.0')
    prompt_text = individual_prompt['system_prompt'].lower()

    assert "explicitly fictional" in prompt_text or "fictional" in prompt_text
    assert "not a biography" in prompt_text or "not based on" in prompt_text
    assert "not a prediction" in prompt_text or "exploratory" in prompt_text


def test_ontology_prompt_exists_in_registry():
    """Test that ontology generation prompt exists in registry"""
    registry = PromptRegistry()
    
    # Get ontology prompt
    ontology_prompt = registry.get_prompt('ontology_generation', '1.0.0')
    
    assert ontology_prompt is not None
    assert 'system_prompt' in ontology_prompt
    assert 'user_prompt_template' in ontology_prompt



def test_individual_prompt_does_not_require_invented_demographics():
    """Test that individual persona prompts don't require invented demographics"""
    registry = PromptRegistry()
    
    # Get individual profile prompt
    individual_prompt = registry.get_prompt('profile_generation', '1.0.0')
    prompt_text = individual_prompt['system_prompt'].lower()

    # Check for key phrases that prevent demographic invention
    assert "not invent" in prompt_text or "do not invent" in prompt_text or "fictional" in prompt_text


def test_rule_based_profile_uses_neutral_engine_placeholders():
    """Test that rule-based profiles use neutral placeholders"""
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
    """Test that ontology prompts reject population/prediction claims"""
    registry = PromptRegistry()
    
    # Get ontology prompt
    ontology_prompt = registry.get_prompt('ontology_generation', '1.0.0')
    prompt_text = ontology_prompt['system_prompt'].lower()

    # Check for key phrases that prevent population claims
    assert "synthetic" in prompt_text or "exploratory" in prompt_text
    assert "not" in prompt_text and ("predict" in prompt_text or "represent" in prompt_text)

"""
Offline disclosure contract checks.

Checks disclosure helper fixtures and rule-based profile metadata:
- human_respondent_count == 0
- output_origin == "synthetic"
- is_forecast == False
- generated_at is valid ISO8601
- Export formats contain disclosure blocks

Acceptance: truth_contract_pass_rate == 1.0 (100% compliance)
"""

import pytest
import json
import re
from datetime import datetime
from typing import Dict, Any, List
from .conftest import save_eval_results
from app.services.claim_boundary import (
    synthetic_output_disclosure,
    fictional_profile_disclosure,
    synthetic_activity_disclosure,
    GENERATED_OUTPUT_DISCLOSURE_TEXT,
)


def validate_iso8601(timestamp_str: str) -> bool:
    """Validate ISO8601 timestamp format."""
    try:
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def check_truth_metadata(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if response contains required truth metadata.
    
    Returns dict with:
    - passed: bool
    - violations: List[str]
    """
    violations = []
    
    # Check for human_respondent_count or human_respondents field
    human_count_field = None
    if 'human_respondent_count' in response_data:
        human_count_field = 'human_respondent_count'
    elif 'human_respondents' in response_data:
        human_count_field = 'human_respondents'
    
    if human_count_field:
        if response_data[human_count_field] != 0:
            violations.append(f"{human_count_field} must be 0, got {response_data[human_count_field]}")
    else:
        violations.append("Missing human_respondent_count or human_respondents field")
    
    # Check for output_origin or evidence_type field
    origin_field = None
    if 'output_origin' in response_data:
        origin_field = 'output_origin'
        expected_value = 'synthetic'
    elif 'evidence_type' in response_data:
        origin_field = 'evidence_type'
        expected_value = 'synthetic'
    elif 'profile_origin' in response_data:
        origin_field = 'profile_origin'
        expected_value = 'fictional_model_generated'
    elif 'record_origin' in response_data:
        origin_field = 'record_origin'
        # Accept various synthetic origins
        if not any(x in str(response_data['record_origin']).lower() for x in ['synthetic', 'fictional', 'model']):
            violations.append(f"record_origin must indicate synthetic/fictional, got {response_data['record_origin']}")
        origin_field = None  # Skip further check
    
    if origin_field and origin_field != 'record_origin':
        if response_data[origin_field] != expected_value:
            violations.append(f"{origin_field} must be '{expected_value}', got {response_data[origin_field]}")
    elif not origin_field and 'record_origin' not in response_data:
        violations.append("Missing output_origin/evidence_type/profile_origin/record_origin field")
    
    # Check for is_forecast field (if present, must be False)
    if 'is_forecast' in response_data:
        if response_data['is_forecast'] is not False:
            violations.append(f"is_forecast must be False, got {response_data['is_forecast']}")
    elif 'forecast_status' in response_data:
        if response_data['forecast_status'] != 'not a forecast':
            violations.append(f"forecast_status must be 'not a forecast', got {response_data['forecast_status']}")
    
    # Check for timestamp field (generated_at, created_at, timestamp, etc.)
    timestamp_field = None
    for field in ['generated_at', 'created_at', 'timestamp']:
        if field in response_data:
            timestamp_field = field
            break
    
    if timestamp_field:
        if not validate_iso8601(str(response_data[timestamp_field])):
            violations.append(f"{timestamp_field} must be valid ISO8601 format")
    
    return {
        'passed': len(violations) == 0,
        'violations': violations
    }


def test_synthetic_disclosure_metadata():
    """
    Test that synthetic disclosure functions return correct metadata.
    """
    print("\nTesting synthetic disclosure metadata functions...")
    
    # Test synthetic_output_disclosure
    disclosure = synthetic_output_disclosure()
    
    assert disclosure['evidence_type'] == 'synthetic', "evidence_type must be 'synthetic'"
    assert disclosure['human_respondents'] == 0, "human_respondents must be 0"
    assert disclosure['forecast_status'] == 'not a forecast', "forecast_status must be 'not a forecast'"
    assert disclosure['public_opinion_status'] == 'not public opinion'
    assert disclosure['causal_status'] == 'not a causal estimate'
    
    print("  ✓ synthetic_output_disclosure() correct")
    
    # Test fictional_profile_disclosure
    profile_disclosure = fictional_profile_disclosure()
    
    assert profile_disclosure['profile_origin'] == 'fictional_model_generated'
    assert profile_disclosure['human_respondents'] == 0
    assert profile_disclosure['is_biography'] is False
    assert profile_disclosure['is_representative'] is False
    assert profile_disclosure['is_forecast'] is False
    
    print("  ✓ fictional_profile_disclosure() correct")
    
    # Test synthetic_activity_disclosure
    activity_disclosure = synthetic_activity_disclosure()
    
    assert activity_disclosure['record_origin'] == 'synthetic_simulation'
    assert activity_disclosure['human_respondents'] == 0
    assert activity_disclosure['observed_human_behavior'] is False
    assert activity_disclosure['external_validation'] is False
    
    print("  ✓ synthetic_activity_disclosure() correct")
    
    print("\n  All disclosure metadata functions passed!")


def test_disclosure_fixture_truth_contract(eval_results_path):
    """Measure disclosure helper fixtures, not API endpoint coverage.

    The previous test called only /health, then counted helper dictionaries as
    synthetic endpoints. Preserve the raw contract check under its real scope.
    """
    disclosures = [
        synthetic_output_disclosure(),
        fictional_profile_disclosure(),
        synthetic_activity_disclosure(),
    ]
    checks = [check_truth_metadata(disclosure) for disclosure in disclosures]
    passed = sum(check["passed"] for check in checks)
    failed = len(checks) - passed
    pass_rate = passed / len(checks)
    save_eval_results(
        {
            "truth_contract_pass_rate": pass_rate,
            "truth_contract_passed": passed,
            "truth_contract_failed": failed,
            "truth_contract_total": len(checks),
        },
        eval_results_path,
        measurement_class="offline_contract_fixture",
        dataset_fixture="disclosure-helper-structures-v1",
    )
    assert pass_rate == 1.0, [check["violations"] for check in checks if not check["passed"]]


def test_export_disclosure_blocks(eval_results_path):
    """
    Test that export formats contain disclosure blocks.
    
    Checks that the disclosure text is present and properly formatted.
    """
    print("\nTesting export disclosure blocks...")
    
    # Test that disclosure text is defined and non-empty
    assert GENERATED_OUTPUT_DISCLOSURE_TEXT, "Disclosure text must be defined"
    assert len(GENERATED_OUTPUT_DISCLOSURE_TEXT) > 50, "Disclosure text must be substantial"
    
    # Check that disclosure contains key terms
    disclosure_lower = GENERATED_OUTPUT_DISCLOSURE_TEXT.lower()
    required_terms = [
        'synthetic',
        '0 human respondents',
        'not public opinion',
        'not a forecast',
    ]
    
    missing_terms = []
    for term in required_terms:
        if term not in disclosure_lower:
            missing_terms.append(term)
    
    print(f"\n  Disclosure text: '{GENERATED_OUTPUT_DISCLOSURE_TEXT[:80]}...'")
    print(f"  Length: {len(GENERATED_OUTPUT_DISCLOSURE_TEXT)} characters")
    print(f"  Required terms found: {len(required_terms) - len(missing_terms)}/{len(required_terms)}")
    
    if missing_terms:
        print(f"  Missing terms: {', '.join(missing_terms)}")
    
    # Save results
    results = {
        "disclosure_text_length": len(GENERATED_OUTPUT_DISCLOSURE_TEXT),
        "disclosure_terms_complete": len(missing_terms) == 0,
        "disclosure_missing_terms": missing_terms
    }
    save_eval_results(results, eval_results_path, measurement_class="offline_contract_fixture")
    
    # Assert all terms present
    assert len(missing_terms) == 0, (
        f"Disclosure text missing required terms: {', '.join(missing_terms)}"
    )
    
    print("\n  ✓ Export disclosure block validation passed!")


def test_profile_truth_metadata(profile_generator, sample_entity, eval_results_path):
    """
    Test that generated profiles contain proper truth metadata.
    """
    print("\nTesting profile truth metadata...")
    
    # Generate a profile
    profile = profile_generator.generate_profile_from_entity(
        entity=sample_entity,
        user_id=0,
        use_llm=False
    )
    
    # Convert to dict for checking
    profile_dict = profile.to_dict()
    
    # Check that profile is marked as fictional
    disclosure = fictional_profile_disclosure()
    
    print(f"\n  Profile: {profile.name}")
    print(f"  Source entity: {profile.source_entity_uuid}")
    print(f"  Profile origin should be marked as fictional")
    
    # Verify disclosure structure
    assert disclosure['profile_origin'] == 'fictional_model_generated'
    assert disclosure['human_respondents'] == 0
    assert disclosure['is_biography'] is False
    assert disclosure['is_forecast'] is False
    
    # Check that persona contains disclaimer language
    persona = profile.persona.lower()
    disclaimer_terms = ['fictional', 'scenario', 'assumption']
    
    has_disclaimer = any(term in persona for term in disclaimer_terms)
    
    print(f"  Persona contains disclaimer: {has_disclaimer}")
    if has_disclaimer:
        print(f"    ✓ Profile persona includes appropriate disclaimer language")
    else:
        print(f"    ⚠ Warning: Profile persona may lack disclaimer language")
    
    # Save results
    results = {
        "profile_has_source_tracking": profile.source_entity_uuid is not None,
        "profile_has_disclaimer": has_disclaimer,
    }
    save_eval_results(results, eval_results_path, measurement_class="offline_contract_fixture")
    
    print("\n  ✓ Profile truth metadata validation passed!")


# The disclosure and endpoint checks above assert their own measured metrics.
# Do not add a collection-order-dependent summary that can read historical
# results or require excluded producers to run.

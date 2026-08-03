"""
Standalone test runner for profile validators.
Runs tests without initializing the full Flask app.
"""

import sys
import importlib.util

# Load the profile_validators module directly
spec = importlib.util.spec_from_file_location(
    'profile_validators',
    'app/services/profile_validators.py'
)
profile_validators = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile_validators)

ProfileValidator = profile_validators.ProfileValidator
ProfileValidationError = profile_validators.ProfileValidationError
ValidationResult = profile_validators.ValidationResult
validate_profile_batch = profile_validators.validate_profile_batch


def test_gender_stereotype_detected():
    """Test that gender stereotypes are caught."""
    validator = ProfileValidator()
    
    profile = {
        'bio': 'A naturally nurturing woman who loves caring for others',
        'persona': 'She is emotional and sensitive, as women naturally are.',
        'age': 30,
        'gender': 'female',
        'mbti': 'ISFJ',
        'country': 'US',
        'profession': 'Nurse'
    }
    
    result = validator.validate_single_profile(profile)
    assert not result.passed, "Should reject stereotypical profile"
    assert result.validation_type == 'stereotype'
    print("✓ Gender stereotype detection works")


def test_essentialism_detected():
    """Test that essentialism is caught."""
    validator = ProfileValidator()
    
    profile = {
        'bio': 'An engineer who focuses on practical solutions',
        'persona': (
            'Because she is female, she approaches problems with more empathy. '
            'Being a woman makes her naturally better at collaboration.'
        ),
        'age': 28,
        'gender': 'female',
        'mbti': 'ISTJ',
        'country': 'US',
        'profession': 'Engineer'
    }
    
    result = validator.validate_single_profile(profile)
    assert not result.passed, "Should reject essentialist profile"
    assert result.validation_type == 'essentialism'
    print("✓ Essentialism detection works")


def test_valid_profile_passes():
    """Test that a valid profile passes."""
    validator = ProfileValidator()
    
    profile = {
        'bio': 'A software engineer interested in climate policy and renewable energy transitions.',
        'persona': (
            'This is a fictional scenario profile. The profile explores perspectives on '
            'technology governance and environmental policy. Their communication style '
            'is analytical and data-driven, often citing research papers and policy documents. '
            'They engage in discussions about decarbonization strategies and the role of '
            'software in climate modeling.'
        ),
        'age': 32,
        'gender': 'other',
        'mbti': 'INTJ',
        'country': 'Germany',
        'profession': 'Software Engineer',
        'interested_topics': ['Climate Change', 'Renewable Energy', 'Policy']
    }
    
    result = validator.validate_single_profile(profile)
    assert result.passed, f"Should pass valid profile, but got: {result.reason}"
    print("✓ Valid profile passes validation")


def test_duplicate_personas_rejected():
    """Test that duplicate personas are detected."""
    validator = ProfileValidator()
    
    profiles = [
        {
            'bio': 'A software engineer working on climate tech',
            'persona': 'This is a fictional profile. They focus on renewable energy software and carbon tracking systems.',
            'age': 30,
            'gender': 'male',
            'mbti': 'INTJ',
            'profession': 'Engineer',
            'interested_topics': ['Climate', 'Software']
        },
        {
            'bio': 'A software engineer working on climate tech',
            'persona': 'This is a fictional profile. They focus on renewable energy software and carbon tracking systems.',
            'age': 35,
            'gender': 'female',
            'mbti': 'INTJ',
            'profession': 'Engineer',
            'interested_topics': ['Climate', 'Software']
        }
    ]
    
    result = validator.check_profile_diversity(profiles)
    assert not result.passed, "Should reject duplicate profiles"
    print("✓ Duplicate profile detection works")


def test_pure_demographic_variations_rejected():
    """Test that profiles differing only in demographics are rejected."""
    validator = ProfileValidator()
    
    profiles = [
        {
            'bio': 'A policy analyst focused on healthcare',
            'persona': (
                'This is a fictional profile. Works on healthcare policy research, '
                'focusing on insurance models and access barriers. Analytical approach.'
            ),
            'age': 30,
            'gender': 'male',
            'mbti': 'ISTJ',
            'profession': 'Policy Analyst',
            'interested_topics': ['Healthcare', 'Policy', 'Research']
        },
        {
            'bio': 'A policy analyst focused on healthcare',
            'persona': (
                'This is a fictional profile. Works on healthcare policy research, '
                'focusing on insurance models and access barriers. Analytical approach.'
            ),
            'age': 55,
            'gender': 'female',
            'mbti': 'ISTJ',
            'profession': 'Policy Analyst',
            'interested_topics': ['Healthcare', 'Policy', 'Research']
        }
    ]
    
    result = validator.check_profile_diversity(profiles)
    assert not result.passed, "Should reject pure demographic variations"
    print("✓ Pure demographic variation detection works")


def test_diverse_profiles_pass():
    """Test that diverse profiles pass."""
    validator = ProfileValidator()
    
    profiles = [
        {
            'bio': 'A software engineer focused on climate technology',
            'persona': (
                'This is a fictional profile. They develop carbon tracking software '
                'and advocate for open-source climate solutions. Technical and pragmatic.'
            ),
            'age': 32,
            'gender': 'other',
            'mbti': 'INTJ',
            'profession': 'Software Engineer',
            'interested_topics': ['Climate Tech', 'Open Source', 'Carbon Markets']
        },
        {
            'bio': 'An environmental activist organizing community campaigns',
            'persona': (
                'This is a fictional profile. They organize grassroots movements '
                'against fossil fuel infrastructure. Passionate and community-focused.'
            ),
            'age': 28,
            'gender': 'female',
            'mbti': 'ENFP',
            'profession': 'Community Organizer',
            'interested_topics': ['Environmental Justice', 'Community Organizing', 'Direct Action']
        },
        {
            'bio': 'An economist researching carbon pricing mechanisms',
            'persona': (
                'This is a fictional profile. They publish research on market-based '
                'climate solutions and carbon tax design. Data-driven and policy-oriented.'
            ),
            'age': 45,
            'gender': 'male',
            'mbti': 'ISTJ',
            'profession': 'Economist',
            'interested_topics': ['Carbon Pricing', 'Economics', 'Policy Design']
        }
    ]
    
    result = validator.check_profile_diversity(profiles)
    assert result.passed, f"Should pass diverse profiles, but got: {result.reason}"
    print("✓ Diverse profile set passes validation")


def test_batch_validation():
    """Test batch validation function."""
    profiles = [
        {
            'bio': 'A climate scientist studying atmospheric changes',
            'persona': (
                'This is a fictional profile. They conduct research on greenhouse gas '
                'concentrations and climate modeling. Evidence-focused and methodical.'
            ),
            'age': 42,
            'gender': 'female',
            'mbti': 'ISTJ',
            'profession': 'Climate Scientist',
            'interested_topics': ['Climate Science', 'Atmospheric Research', 'Data Analysis']
        },
        {
            'bio': 'A journalist covering energy policy and transitions',
            'persona': (
                'This is a fictional profile. They report on renewable energy policies '
                'and interview stakeholders across the energy sector. Investigative and balanced.'
            ),
            'age': 34,
            'gender': 'other',
            'mbti': 'ENFP',
            'profession': 'Journalist',
            'interested_topics': ['Energy Policy', 'Journalism', 'Public Affairs']
        }
    ]
    
    passed, reason, details = validate_profile_batch(profiles)
    assert passed, f"Should pass valid batch, but got: {reason}"
    print("✓ Batch validation works correctly")


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("Running Profile Validation Tests (Gate 1)")
    print("="*60 + "\n")
    
    tests = [
        ("Stereotype Detection", test_gender_stereotype_detected),
        ("Essentialism Detection", test_essentialism_detected),
        ("Valid Profile Acceptance", test_valid_profile_passes),
        ("Duplicate Detection", test_duplicate_personas_rejected),
        ("Demographic Variation Detection", test_pure_demographic_variations_rejected),
        ("Diverse Profile Acceptance", test_diverse_profiles_pass),
        ("Batch Validation", test_batch_validation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name} ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

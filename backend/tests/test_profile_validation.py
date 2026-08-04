"""
Tests for profile validation (Gate 1 requirement).

Tests stereotype detection, essentialism checks, diversity validation,
and integration with profile generation.
"""

import sys
import os
import pytest

# Add backend directory to path to allow direct import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import directly from module to avoid Flask app initialization
from app.services.profile_validators import (
    ProfileValidator,
    ProfileValidationError,
    ValidationResult,
    validate_profile_batch
)


class TestStereotypeDetection:
    """Test stereotype detection in profiles."""
    
    def test_gender_stereotype_detected(self):
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
        assert not result.passed
        assert result.validation_type == 'stereotype'
        assert 'stereotypical' in result.reason.lower()
    
    def test_age_stereotype_detected(self):
        """Test that age stereotypes are caught."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A young person who understands technology',
            'persona': 'As a millennial, they are lazy and entitled. Old people cannot understand social media.',
            'age': 25,
            'gender': 'other',
            'mbti': 'ENTP',
            'country': 'US',
            'profession': 'Developer'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'stereotype'
    
    def test_professional_stereotype_detected(self):
        """Test that professional stereotypes are caught."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A typical lawyer who is aggressive and argumentative',
            'persona': 'As you would expect from a lawyer, they are confrontational and always looking for conflicts.',
            'age': 40,
            'gender': 'male',
            'mbti': 'ENTJ',
            'country': 'US',
            'profession': 'Lawyer'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'stereotype'
    
    def test_valid_profile_passes(self):
        """Test that a valid, non-stereotypical profile passes."""
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
        assert result.passed


class TestEssentialismDetection:
    """Test essentialism (demographic determinism) detection."""
    
    def test_gender_essentialism_detected(self):
        """Test that gender-based essentialism is caught."""
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
        assert not result.passed
        assert result.validation_type == 'essentialism'
    
    def test_age_essentialism_detected(self):
        """Test that age-based essentialism is caught."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A young activist passionate about social change',
            'persona': (
                'Being 22-year-old means they are idealistic and lack practical experience. '
                'Due to their age, they cannot understand complex policy issues.'
            ),
            'age': 22,
            'gender': 'other',
            'mbti': 'ENFP',
            'country': 'UK',
            'profession': 'Activist'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'essentialism'
    
    def test_valid_contextual_description_passes(self):
        """Test that valid contextual descriptions pass (not essentialism)."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A policy analyst focused on healthcare reform',
            'persona': (
                'This is a fictional scenario profile. They work as a healthcare policy analyst, '
                'researching insurance models and access barriers. Their professional experience '
                'includes working with community health centers. They tend to cite empirical '
                'studies and focus on evidence-based interventions.'
            ),
            'age': 35,
            'gender': 'female',
            'mbti': 'ISTJ',
            'country': 'Canada',
            'profession': 'Policy Analyst',
            'interested_topics': ['Healthcare', 'Public Policy', 'Social Services']
        }
        
        result = validator.validate_single_profile(profile)
        assert result.passed


class TestDemographicOnlyDetection:
    """Test detection of demographic-only profiles."""
    
    def test_demographic_only_bio_rejected(self):
        """Test that bios with only demographics are rejected."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A 30-year-old male from Japan.',
            'persona': 'This is a fictional profile representing various perspectives.',
            'age': 30,
            'gender': 'male',
            'mbti': 'ISTJ',
            'country': 'Japan',
            'profession': 'Unknown'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'demographic_only'
    
    def test_insufficient_persona_rejected(self):
        """Test that very short personas are rejected."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A software engineer interested in AI',
            'persona': 'Works in tech.',  # Too short
            'age': 28,
            'gender': 'other',
            'mbti': 'INTP',
            'country': 'US',
            'profession': 'Engineer'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'insufficient_content'


class TestRequiredFieldsValidation:
    """Test validation of required fields."""
    
    def test_missing_bio_rejected(self):
        """Test that profiles missing bio are rejected."""
        validator = ProfileValidator()
        
        profile = {
            'persona': 'A fictional profile for scenario testing purposes.',
            'age': 30,
            'gender': 'other',
            'mbti': 'ISTJ'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'missing_field'
    
    def test_invalid_gender_rejected(self):
        """Test that invalid gender values are rejected."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A researcher focused on social dynamics',
            'persona': 'This is a fictional scenario profile exploring various perspectives on community organizing.',
            'age': 35,
            'gender': 'invalid',  # Invalid gender
            'mbti': 'ENFJ'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'invalid_field_value'
        assert 'gender' in result.reason.lower()
    
    def test_invalid_age_rejected(self):
        """Test that invalid ages are rejected."""
        validator = ProfileValidator()
        
        profile = {
            'bio': 'A student interested in climate science',
            'persona': 'This is a fictional scenario profile exploring perspectives on environmental policy and activism.',
            'age': 5,  # Too young
            'gender': 'other',
            'mbti': 'INFP'
        }
        
        result = validator.validate_single_profile(profile)
        assert not result.passed
        assert result.validation_type == 'invalid_field_value'
        assert 'age' in result.reason.lower()


class TestDiversityChecks:
    """Test diversity validation across profile sets."""
    
    def test_duplicate_personas_rejected(self):
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
                'age': 35,  # Different age, but same persona
                'gender': 'female',
                'mbti': 'INTJ',
                'profession': 'Engineer',
                'interested_topics': ['Climate', 'Software']
            }
        ]
        
        result = validator.check_profile_diversity(profiles)
        assert not result.passed
        assert result.validation_type in ['duplicate_profile', 'near_duplicate_profile']
    
    def test_pure_demographic_variations_rejected(self):
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
                # Reworded persona: not a byte-identical duplicate, but the same
                # functional profile (profession, topics, decision criteria).
                'persona': (
                    'This is a fictional profile. Their healthcare policy research '
                    'examines insurance models and access barriers using an '
                    'analytical approach.'
                ),
                'age': 55,  # Only age differs
                'gender': 'female',  # Only gender differs
                'mbti': 'ISTJ',
                'profession': 'Policy Analyst',
                'interested_topics': ['Healthcare', 'Policy', 'Research']
            }
        ]
        
        result = validator.check_profile_diversity(profiles)
        assert not result.passed
        assert result.validation_type == 'pure_demographic_variation'
    
    def test_diverse_profiles_pass(self):
        """Test that genuinely diverse profiles pass validation."""
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
        assert result.passed


class TestBatchValidation:
    """Test batch validation function."""
    
    def test_batch_validation_catches_individual_failures(self):
        """Test that batch validation catches individual profile failures."""
        profiles = [
            {
                'bio': 'A valid profile with sufficient content',
                'persona': (
                    'This is a fictional scenario profile. They work in renewable energy '
                    'consulting, advising businesses on decarbonization strategies.'
                ),
                'age': 35,
                'gender': 'other',
                'mbti': 'ENTJ',
                'profession': 'Consultant',
                'interested_topics': ['Renewable Energy', 'Business Strategy']
            },
            {
                'bio': 'A naturally emotional woman who cares deeply',  # Stereotype
                'persona': 'She is nurturing and sensitive, as women are.',
                'age': 30,
                'gender': 'female',
                'mbti': 'ISFJ',
                'profession': 'Teacher',
                'interested_topics': ['Education']
            }
        ]
        
        passed, reason, details = validate_profile_batch(profiles)
        assert not passed
        assert 'stereotypical' in reason.lower()
    
    def test_batch_validation_catches_diversity_failures(self):
        """Test that batch validation catches diversity failures."""
        profiles = [
            {
                'bio': 'An engineer working on sustainable transportation',
                'persona': (
                    'This is a fictional profile. They design electric vehicle systems '
                    'and battery technology for urban transit applications.'
                ),
                'age': 30,
                'gender': 'male',
                'mbti': 'ISTP',
                'profession': 'Engineer',
                'interested_topics': ['Electric Vehicles', 'Battery Tech']
            },
            {
                'bio': 'An engineer working on sustainable transportation',
                'persona': (
                    'This is a fictional profile. They design electric vehicle systems '
                    'and battery technology for urban transit applications.'
                ),
                'age': 50,  # Only age differs
                'gender': 'female',  # Only gender differs
                'mbti': 'ISTP',
                'profession': 'Engineer',
                'interested_topics': ['Electric Vehicles', 'Battery Tech']
            }
        ]
        
        passed, reason, details = validate_profile_batch(profiles)
        assert not passed
        assert 'demographic' in reason.lower() or 'duplicate' in reason.lower()
    
    def test_batch_validation_passes_valid_set(self):
        """Test that batch validation passes valid diverse profiles."""
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
            },
            {
                'bio': 'A renewable energy investor evaluating projects',
                'persona': (
                    'This is a fictional profile. They assess financial viability of clean '
                    'energy ventures and advise on market opportunities. Pragmatic and risk-aware.'
                ),
                'age': 51,
                'gender': 'male',
                'mbti': 'ENTJ',
                'profession': 'Investor',
                'interested_topics': ['Clean Energy', 'Finance', 'Market Analysis']
            }
        ]
        
        passed, reason, details = validate_profile_batch(profiles)
        assert passed
        assert reason is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

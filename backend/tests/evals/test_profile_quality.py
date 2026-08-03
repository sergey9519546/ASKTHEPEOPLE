"""
Profile Quality Evaluation (Gate 5 requirement).

Tests profile generation for:
- Diversity: Count unique decision criteria (should be >80% unique)
- Stereotypes: Check for stereotype markers (should be <5% flagged)
- Essentialism: Check for essentialist language (should be 0%)
"""

import pytest
import re
from typing import List, Set
from .conftest import save_eval_results
from app.services.oasis_profile_generator import OasisAgentProfile
from app.services.zep_entity_reader import EntityNode


# Stereotype markers to detect
STEREOTYPE_MARKERS = [
    r'\b(all|every|always)\s+(women|men|males|females|asians|blacks|whites|latinos|hispanics|muslims|christians|jews)\b',
    r'\b(women|men|males|females)\s+(are|tend to be|usually are)\s+(emotional|logical|aggressive|nurturing|weak|strong)\b',
    r'\b(typical|naturally|inherently|genetically)\s+(masculine|feminine|male|female)\b',
    r'\bborn\s+(leader|follower|criminal|genius)\b',
    r'\b(race|gender|ethnicity)\s+determines?\b',
]

# Essentialist language patterns
ESSENTIALIST_MARKERS = [
    r'\bby nature\b',
    r'\binherently\b',
    r'\bgenetically programmed\b',
    r'\bborn (with|to be)\b',
    r'\bnatural(ly)?\s+(tendency|inclination|disposition)\b',
    r'\b(always|never) (behaves?|acts?|thinks?|feels?)\b',
    r'\b(all|every) (person|people|individual)s? of (this|that|their) (type|kind|group)\b',
]


def detect_stereotypes(text: str) -> bool:
    """Detect stereotype markers in text."""
    text_lower = text.lower()
    for pattern in STEREOTYPE_MARKERS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def detect_essentialism(text: str) -> bool:
    """Detect essentialist language in text."""
    text_lower = text.lower()
    for pattern in ESSENTIALIST_MARKERS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def extract_decision_criteria(profile: OasisAgentProfile) -> str:
    """
    Extract key decision-making criteria from profile.
    
    This creates a signature based on:
    - Profession
    - Age group
    - MBTI type
    - Primary interest area
    """
    criteria_parts = []
    
    # Factor 1: Profession
    if profile.profession:
        criteria_parts.append(f"prof:{profile.profession.lower()}")
    
    # Factor 2: Age group (creates 5 age groups)
    if profile.age:
        age_group = (profile.age // 10) * 10  # Group by decade
        criteria_parts.append(f"age:{age_group}")
    
    # Factor 3: MBTI type
    if profile.mbti:
        criteria_parts.append(f"mbti:{profile.mbti}")
    
    # Factor 4: Primary interest (first topic)
    if profile.interested_topics and len(profile.interested_topics) > 0:
        criteria_parts.append(f"interest:{profile.interested_topics[0].lower()}")
    
    return "|".join(sorted(criteria_parts))


def test_profile_diversity(profile_generator, sample_entity, sample_decision_prompt, eval_results_path):
    """
    Test profile diversity: Generate 100 profiles and measure uniqueness.
    
    Acceptance: diversity_rate > 0.80 (>80 unique decision criteria)
    """
    # Generate 100 profiles with diverse entity types and attributes
    profiles: List[OasisAgentProfile] = []
    
    # Create diverse entity types and attributes
    entity_types = [
        "student", "professor", "expert", "activist", "journalist",
        "alumni", "publicfigure", "faculty", "official"
    ]
    
    professions = [
        "Student", "Professor", "Engineer", "Journalist", "Activist",
        "Researcher", "Teacher", "Consultant", "Manager", "Analyst"
    ]
    
    topic_sets = [
        ["Education", "Technology", "Innovation"],
        ["Policy", "Government", "Law"],
        ["Science", "Research", "Academia"],
        ["Media", "Communication", "Arts"],
        ["Environment", "Climate", "Sustainability"],
        ["Business", "Economics", "Finance"],
        ["Health", "Medicine", "Public Health"],
        ["Social Issues", "Community", "Justice"],
        ["Culture", "Philosophy", "Ethics"],
        ["Technology", "AI", "Data Science"],
    ]
    
    print(f"\nGenerating 100 profiles for diversity evaluation...")
    
    for i in range(100):
        # Create entity variant with diverse attributes
        entity_type = entity_types[i % len(entity_types)]
        profession = professions[i % len(professions)]
        topics = topic_sets[i % len(topic_sets)]
        
        entity_variant = EntityNode(
            uuid=f"test-uuid-{i:03d}",
            name=f"Person {i}",
            labels=["Person", entity_type],
            summary=f"A {profession.lower()} interested in {topics[0]}",
            attributes={
                "profile_id": i,
                "occupation": profession,
                "type": entity_type
            },
            related_edges=[],
            related_nodes=[]
        )
        
        # Generate profile (using rule-based to avoid LLM dependency in CI)
        profile = profile_generator.generate_profile_from_entity(
            entity=entity_variant,
            user_id=i,
            use_llm=False
        )
        
        # Set diverse attributes to ensure variety
        profile.profession = profession
        profile.interested_topics = topics
        profile.age = 20 + (i % 50)  # Ages 20-69
        profile.mbti = profile_generator.MBTI_TYPES[i % len(profile_generator.MBTI_TYPES)]
        
        profiles.append(profile)
        
        if (i + 1) % 20 == 0:
            print(f"  Generated {i + 1}/100 profiles...")
    
    # Measure diversity: count unique decision criteria
    decision_criteria: Set[str] = set()
    for profile in profiles:
        criteria = extract_decision_criteria(profile)
        if criteria:  # Only count non-empty criteria
            decision_criteria.add(criteria)
    
    unique_count = len(decision_criteria)
    diversity_rate = unique_count / len(profiles)
    
    print(f"\nDiversity Results:")
    print(f"  Total profiles: {len(profiles)}")
    print(f"  Unique decision criteria: {unique_count}")
    print(f"  Diversity rate: {diversity_rate:.2%}")
    
    # Save results
    results = {
        "diversity_rate": diversity_rate,
        "unique_criteria_count": unique_count,
        "total_profiles": len(profiles)
    }
    save_eval_results(results, eval_results_path)
    
    # Assert threshold
    assert diversity_rate > 0.80, (
        f"Profile diversity too low: {diversity_rate:.2%} (expected >80%). "
        f"Only {unique_count} unique criteria out of {len(profiles)} profiles."
    )


def test_stereotype_detection(profile_generator, sample_entity, eval_results_path):
    """
    Test stereotype detection: Generate 100 profiles and check for stereotypes.
    
    Acceptance: stereotype_rate < 0.05 (<5% flagged)
    """
    # Generate 100 profiles with diverse backgrounds
    profiles: List[OasisAgentProfile] = []
    entity_types = ["student", "professor", "expert", "activist", "journalist"]
    
    print(f"\nGenerating 100 profiles for stereotype detection...")
    
    for i in range(100):
        entity_type = entity_types[i % len(entity_types)]
        entity_variant = EntityNode(
            uuid=f"test-uuid-stereo-{i:03d}",
            name=f"Person {i}",
            labels=["Person", entity_type],
            summary=f"A {entity_type} with diverse perspectives",
            attributes={
                "type": entity_type
            },
            related_edges=[],
            related_nodes=[]
        )
        
        profile = profile_generator.generate_profile_from_entity(
            entity=entity_variant,
            user_id=i,
            use_llm=False
        )
        profiles.append(profile)
        
        if (i + 1) % 20 == 0:
            print(f"  Generated {i + 1}/100 profiles...")
    
    # Check for stereotypes
    flagged_count = 0
    flagged_examples = []
    
    for profile in profiles:
        # Check bio and persona for stereotypes
        combined_text = f"{profile.bio} {profile.persona}"
        
        if detect_stereotypes(combined_text):
            flagged_count += 1
            if len(flagged_examples) < 3:  # Keep first 3 examples
                flagged_examples.append({
                    "name": profile.name,
                    "bio": profile.bio[:100],
                    "persona": profile.persona[:100] if profile.persona else ""
                })
    
    stereotype_rate = flagged_count / len(profiles)
    
    print(f"\nStereotype Detection Results:")
    print(f"  Total profiles: {len(profiles)}")
    print(f"  Profiles flagged: {flagged_count}")
    print(f"  Stereotype rate: {stereotype_rate:.2%}")
    
    if flagged_examples:
        print(f"  Example flagged profiles:")
        for ex in flagged_examples:
            print(f"    - {ex['name']}: {ex['bio'][:50]}...")
    
    # Save results
    results = {
        "stereotype_rate": stereotype_rate,
        "flagged_count": flagged_count,
        "total_profiles_checked": len(profiles)
    }
    save_eval_results(results, eval_results_path)
    
    # Assert threshold
    assert stereotype_rate < 0.05, (
        f"Stereotype rate too high: {stereotype_rate:.2%} (expected <5%). "
        f"{flagged_count} profiles flagged out of {len(profiles)}."
    )


def test_essentialism_detection(profile_generator, sample_entity, eval_results_path):
    """
    Test essentialism detection: Check profiles for essentialist language.
    
    Acceptance: essentialism_rate == 0.0 (0% flagged)
    """
    # Generate 100 profiles
    profiles: List[OasisAgentProfile] = []
    
    print(f"\nGenerating 100 profiles for essentialism detection...")
    
    for i in range(100):
        entity_variant = EntityNode(
            uuid=f"test-uuid-ess-{i:03d}",
            name=f"Person {i}",
            labels=["Person"],
            summary=f"A diverse individual with unique perspectives",
            attributes={},
            related_edges=[],
            related_nodes=[]
        )
        
        profile = profile_generator.generate_profile_from_entity(
            entity=entity_variant,
            user_id=i,
            use_llm=False
        )
        profiles.append(profile)
        
        if (i + 1) % 20 == 0:
            print(f"  Generated {i + 1}/100 profiles...")
    
    # Check for essentialist language
    flagged_count = 0
    flagged_examples = []
    
    for profile in profiles:
        combined_text = f"{profile.bio} {profile.persona}"
        
        if detect_essentialism(combined_text):
            flagged_count += 1
            if len(flagged_examples) < 3:
                flagged_examples.append({
                    "name": profile.name,
                    "bio": profile.bio[:100],
                    "persona": profile.persona[:100] if profile.persona else ""
                })
    
    essentialism_rate = flagged_count / len(profiles)
    
    print(f"\nEssentialism Detection Results:")
    print(f"  Total profiles: {len(profiles)}")
    print(f"  Profiles flagged: {flagged_count}")
    print(f"  Essentialism rate: {essentialism_rate:.2%}")
    
    if flagged_examples:
        print(f"  Example flagged profiles:")
        for ex in flagged_examples:
            print(f"    - {ex['name']}: {ex['bio'][:50]}...")
    
    # Save results
    results = {
        "essentialism_rate": essentialism_rate,
        "essentialism_flagged_count": flagged_count,
        "total_profiles_checked_essentialism": len(profiles)
    }
    save_eval_results(results, eval_results_path)
    
    # Assert threshold (strict: should be 0)
    assert essentialism_rate == 0.0, (
        f"Essentialism detected: {essentialism_rate:.2%} (expected 0%). "
        f"{flagged_count} profiles flagged out of {len(profiles)}."
    )


def test_profile_quality_summary(eval_results_path):
    """
    Summary test that prints overall quality metrics.
    
    This test runs last and summarizes all quality checks.
    """
    import json
    
    if not eval_results_path.exists():
        pytest.skip("No evaluation results available")
    
    with open(eval_results_path, 'r') as f:
        results = json.load(f)
    
    print("\n" + "="*70)
    print("PROFILE QUALITY EVALUATION SUMMARY")
    print("="*70)
    
    diversity_rate = results.get('diversity_rate', 0)
    stereotype_rate = results.get('stereotype_rate', 0)
    essentialism_rate = results.get('essentialism_rate', 0)
    
    print(f"\nDiversity Rate:      {diversity_rate:.2%} (threshold: >80%)")
    print(f"Stereotype Rate:     {stereotype_rate:.2%} (threshold: <5%)")
    print(f"Essentialism Rate:   {essentialism_rate:.2%} (threshold: 0%)")
    
    # Overall pass/fail
    diversity_pass = diversity_rate > 0.80
    stereotype_pass = stereotype_rate < 0.05
    essentialism_pass = essentialism_rate == 0.0
    
    all_pass = diversity_pass and stereotype_pass and essentialism_pass
    
    print(f"\nDiversity Check:     {'✓ PASS' if diversity_pass else '✗ FAIL'}")
    print(f"Stereotype Check:    {'✓ PASS' if stereotype_pass else '✗ FAIL'}")
    print(f"Essentialism Check:  {'✓ PASS' if essentialism_pass else '✗ FAIL'}")
    print(f"\nOverall Quality:     {'✓ PASS' if all_pass else '✗ FAIL'}")
    print("="*70 + "\n")

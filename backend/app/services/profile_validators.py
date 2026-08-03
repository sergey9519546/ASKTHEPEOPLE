"""
Profile Validators — Gate 1 requirement enforcement.

Validates generated profiles to prevent stereotypes, essentialism, and ensure diversity
before profiles are returned to users. Profiles that fail validation trigger retry
or rejection.

Key validation rules:
1. No stereotypical personas (ethnic/gender/age stereotypes)
2. No essentialist reasoning (demographic determinism)
3. Profiles must differ on decision criteria, not just demographics
4. No duplicate functional profiles
"""

from typing import Dict, List, Any, Optional, Tuple
import re
from dataclasses import dataclass
import logging

# Try relative import first, fall back to absolute for standalone usage
try:
    from ..utils.logger import get_logger
    logger = get_logger('askthepeople.profile_validators')
except (ImportError, ValueError):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('askthepeople.profile_validators')


class ProfileValidationError(Exception):
    """Raised when a profile or profile set fails validation."""
    def __init__(self, message: str, validation_type: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.validation_type = validation_type
        self.details = details or {}


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    reason: Optional[str] = None
    validation_type: Optional[str] = None
    details: Optional[Dict] = None
    
    @staticmethod
    def success():
        return ValidationResult(passed=True)
    
    @staticmethod
    def failure(reason: str, validation_type: str, details: Optional[Dict] = None):
        return ValidationResult(
            passed=False,
            reason=reason,
            validation_type=validation_type,
            details=details
        )


class ProfileValidator:
    """
    Validates synthetic profiles for stereotypes, essentialism, and diversity.
    
    All validations enforce the principle that profiles are scenario inputs,
    not representations of real people or groups.
    """
    
    # Stereotypical phrases that should not appear in profiles
    STEREOTYPE_PATTERNS = [
        # Gender stereotypes
        r'\b(naturally\s+)?(nurturing|emotional|sensitive)\s+(woman|female|girl)',
        r'\b(naturally\s+)?(aggressive|logical|assertive)\s+(man|male|boy)',
        r'\bwomen\s+are\s+(better|worse|naturally)',
        r'\bmen\s+are\s+(better|worse|naturally)',
        
        # Ethnic/racial stereotypes
        r'\b(naturally\s+)?(good|bad)\s+at\s+math\s+(because|as\s+a)',
        r'\basian\s+(naturally|typically|always)\s+',
        r'\bblack\s+(naturally|typically|always)\s+',
        r'\bwhite\s+(naturally|typically|always)\s+',
        r'\blatino\s+(naturally|typically|always)\s+',
        
        # Age stereotypes
        r'\b(young|old)\s+people\s+(can\'?t|cannot|always|never)',
        r'\b(too\s+old|too\s+young)\s+to\s+(understand|learn|change)',
        r'\bmillennials?\s+(are\s+lazy|can\'?t|always)',
        r'\bboomer\s+(doesn\'?t|can\'?t|refuses)',
        
        # Professional stereotypes
        r'\b(typical|stereotypical)\s+(lawyer|engineer|teacher|nurse)',
        r'\bas\s+you\'?d\s+expect\s+from\s+a\s+',
        
        # Cultural essentialism
        r'\b(in\s+their|my)\s+culture,?\s+(we|they)\s+(always|never|must)',
        r'\bcultural\s+background\s+(makes|means|causes)\s+(them|him|her)',
    ]
    
    # Essentialist reasoning patterns (demographic determinism)
    ESSENTIALISM_PATTERNS = [
        r'\bbecause\s+(he|she|they)\s+(is|are)\s+(male|female|asian|black|white|young|old)',
        r'\bas\s+a\s+(man|woman|person\s+of\s+color)',
        r'\bdue\s+to\s+(his|her|their)\s+(gender|race|ethnicity|age)',
        r'\bbeing\s+(male|female|[0-9]+-year-old)\s+(makes|means|causes)',
        r'\b(naturally|inherently)\s+(inclined|predisposed|suited)',
    ]
    
    # Forbidden demographic-only descriptions
    DEMOGRAPHIC_ONLY_PATTERNS = [
        r'^(A|An)\s+[0-9]+-year-old\s+(male|female|man|woman)\s+from\s+\w+\.$',
        r'^(Male|Female|Man|Woman),\s+age\s+[0-9]+,\s+from\s+\w+\.$',
    ]
    
    def __init__(self):
        self.stereotype_regexes = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.STEREOTYPE_PATTERNS
        ]
        self.essentialism_regexes = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.ESSENTIALISM_PATTERNS
        ]
        self.demographic_only_regexes = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.DEMOGRAPHIC_ONLY_PATTERNS
        ]
    
    def validate_single_profile(self, profile: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single profile for stereotypes and essentialism.
        
        Args:
            profile: Profile dictionary with 'bio', 'persona', etc.
            
        Returns:
            ValidationResult indicating pass/fail with reason
        """
        # Check stereotype patterns
        stereotype_check = self._check_stereotypes(profile)
        if not stereotype_check.passed:
            return stereotype_check
        
        # Check essentialism patterns
        essentialism_check = self._check_essentialism(profile)
        if not essentialism_check.passed:
            return essentialism_check
        
        # Check required fields first (more specific errors)
        required_check = self._check_required_fields(profile)
        if not required_check.passed:
            return required_check
        
        # Check for demographic-only content (generic, after specific checks)
        demographic_check = self._check_demographic_only(profile)
        if not demographic_check.passed:
            return demographic_check
        
        return ValidationResult.success()
    
    def _check_stereotypes(self, profile: Dict[str, Any]) -> ValidationResult:
        """Check for stereotypical content in profile."""
        bio = profile.get('bio', '')
        persona = profile.get('persona', '')
        combined_text = f"{bio} {persona}"
        
        for regex in self.stereotype_regexes:
            match = regex.search(combined_text)
            if match:
                return ValidationResult.failure(
                    reason=f"Profile contains stereotypical content: '{match.group()}'",
                    validation_type="stereotype",
                    details={"matched_text": match.group(), "field": "bio/persona"}
                )
        
        return ValidationResult.success()
    
    def _check_essentialism(self, profile: Dict[str, Any]) -> ValidationResult:
        """Check for essentialist reasoning (demographic determinism)."""
        bio = profile.get('bio', '')
        persona = profile.get('persona', '')
        combined_text = f"{bio} {persona}"
        
        for regex in self.essentialism_regexes:
            match = regex.search(combined_text)
            if match:
                return ValidationResult.failure(
                    reason=f"Profile contains essentialist reasoning: '{match.group()}'",
                    validation_type="essentialism",
                    details={"matched_text": match.group(), "field": "bio/persona"}
                )
        
        return ValidationResult.success()
    
    def _check_demographic_only(self, profile: Dict[str, Any]) -> ValidationResult:
        """Check if profile is only demographic description without functional content."""
        bio = profile.get('bio', '').strip()
        persona = profile.get('persona', '').strip()
        
        # Check if bio is just demographics
        for regex in self.demographic_only_regexes:
            if regex.match(bio):
                return ValidationResult.failure(
                    reason="Profile bio contains only demographic information without functional context",
                    validation_type="demographic_only",
                    details={"field": "bio", "content": bio[:100]}
                )
        
        # Check if persona is too short (likely just demographics)
        if len(persona) < 100:
            return ValidationResult.failure(
                reason="Profile persona is too brief (< 100 chars) to establish functional context",
                validation_type="insufficient_content",
                details={"field": "persona", "length": len(persona)}
            )
        
        return ValidationResult.success()
    
    def _check_required_fields(self, profile: Dict[str, Any]) -> ValidationResult:
        """Check that all required fields are present and valid."""
        required_fields = ['bio', 'persona', 'age', 'gender', 'mbti']
        
        for field in required_fields:
            if field not in profile or not profile[field]:
                return ValidationResult.failure(
                    reason=f"Required field '{field}' is missing or empty",
                    validation_type="missing_field",
                    details={"field": field}
                )
        
        # Validate gender values
        valid_genders = ['male', 'female', 'other']
        if profile.get('gender', '').lower() not in valid_genders:
            return ValidationResult.failure(
                reason=f"Invalid gender value: {profile.get('gender')}. Must be 'male', 'female', or 'other'",
                validation_type="invalid_field_value",
                details={"field": "gender", "value": profile.get('gender')}
            )
        
        # Validate age range
        age = profile.get('age')
        if not isinstance(age, int) or age < 13 or age > 100:
            return ValidationResult.failure(
                reason=f"Invalid age value: {age}. Must be integer between 13 and 100",
                validation_type="invalid_field_value",
                details={"field": "age", "value": age}
            )
        
        return ValidationResult.success()
    
    def check_profile_diversity(
        self,
        profiles: List[Dict[str, Any]],
        min_functional_difference: float = 0.3
    ) -> ValidationResult:
        """
        Check that profiles differ on functional/decision criteria, not just demographics.
        
        Args:
            profiles: List of profile dictionaries
            min_functional_difference: Minimum required functional difference (0-1)
            
        Returns:
            ValidationResult indicating pass/fail
        """
        if len(profiles) < 2:
            return ValidationResult.success()
        
        # Check for duplicate personas (exact or near-exact matches)
        duplicate_check = self._check_duplicate_personas(profiles)
        if not duplicate_check.passed:
            return duplicate_check
        
        # Check for pure demographic variations
        demographic_variation_check = self._check_pure_demographic_variations(profiles)
        if not demographic_variation_check.passed:
            return demographic_variation_check
        
        return ValidationResult.success()
    
    def _check_duplicate_personas(self, profiles: List[Dict[str, Any]]) -> ValidationResult:
        """Check for duplicate or nearly identical personas."""
        persona_map = {}
        
        for i, profile in enumerate(profiles):
            persona = profile.get('persona', '').strip().lower()
            # Normalize whitespace
            persona_normalized = ' '.join(persona.split())
            
            # Check for exact duplicates
            if persona_normalized in persona_map:
                return ValidationResult.failure(
                    reason=f"Duplicate persona detected (profiles {persona_map[persona_normalized]} and {i})",
                    validation_type="duplicate_profile",
                    details={
                        "profile_indices": [persona_map[persona_normalized], i],
                        "persona_preview": persona_normalized[:200]
                    }
                )
            
            persona_map[persona_normalized] = i
        
        # Check for near-duplicates (simple similarity check)
        personas_list = list(persona_map.keys())
        for i in range(len(personas_list)):
            for j in range(i + 1, len(personas_list)):
                similarity = self._simple_similarity(personas_list[i], personas_list[j])
                if similarity > 0.9:  # 90% similar
                    return ValidationResult.failure(
                        reason=f"Nearly identical personas detected (profiles {i} and {j}): {similarity:.2%} similar",
                        validation_type="near_duplicate_profile",
                        details={
                            "profile_indices": [i, j],
                            "similarity": similarity
                        }
                    )
        
        return ValidationResult.success()
    
    def _check_pure_demographic_variations(self, profiles: List[Dict[str, Any]]) -> ValidationResult:
        """
        Check that profiles don't differ only on demographics.
        
        Example of what to catch:
        - Profile A: "35-year-old software engineer interested in climate change"
        - Profile B: "55-year-old software engineer interested in climate change"
        (Same functional profile, different age only)
        """
        # Extract functional components (profession, interests, stance indicators)
        functional_profiles = []
        
        for i, profile in enumerate(profiles):
            functional = self._extract_functional_components(profile)
            
            # Check if this functional profile already exists
            for j, existing in enumerate(functional_profiles):
                if self._functional_profiles_match(functional, existing):
                    return ValidationResult.failure(
                        reason=f"Profiles {j} and {i} differ only in demographics, not decision criteria",
                        validation_type="pure_demographic_variation",
                        details={
                            "profile_indices": [j, i],
                            "functional_profile": functional
                        }
                    )
            
            functional_profiles.append(functional)
        
        return ValidationResult.success()
    
    def _extract_functional_components(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract functional components that affect decision-making."""
        return {
            'profession': profile.get('profession', '').lower().strip(),
            'interested_topics': sorted([t.lower().strip() for t in profile.get('interested_topics', [])]),
            'mbti': profile.get('mbti', '').upper().strip(),
            # Extract key phrases from persona (interests, values, concerns)
            'persona_keywords': self._extract_keywords(profile.get('persona', ''))
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from persona text."""
        # Simple keyword extraction (could be enhanced with NLP)
        text = text.lower()
        # Remove age/gender/demographic mentions
        text = re.sub(r'\b\d+-year-old\b', '', text)
        text = re.sub(r'\b(male|female|man|woman|boy|girl)\b', '', text)
        
        # Extract words > 5 chars (excluding common words)
        common_words = {'about', 'would', 'could', 'should', 'their', 'which', 'there', 
                       'these', 'those', 'where', 'while', 'because', 'through'}
        words = re.findall(r'\b\w{6,}\b', text)
        keywords = [w for w in words if w not in common_words]
        
        return sorted(set(keywords))[:20]  # Top 20 unique keywords
    
    def _functional_profiles_match(self, fp1: Dict, fp2: Dict, threshold: float = 0.8) -> bool:
        """Check if two functional profiles are too similar."""
        # Check profession
        if fp1['profession'] and fp2['profession']:
            if fp1['profession'] == fp2['profession']:
                # Same profession - check other factors
                
                # Check interested topics overlap
                topics1 = set(fp1['interested_topics'])
                topics2 = set(fp2['interested_topics'])
                if topics1 and topics2:
                    overlap = len(topics1 & topics2) / max(len(topics1), len(topics2))
                    if overlap > 0.7:  # 70% topic overlap
                        # Check keyword similarity
                        keywords1 = set(fp1['persona_keywords'])
                        keywords2 = set(fp2['persona_keywords'])
                        if keywords1 and keywords2:
                            keyword_overlap = len(keywords1 & keywords2) / max(len(keywords1), len(keywords2))
                            if keyword_overlap > threshold:
                                return True
        
        return False
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple word-based similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


def validate_profile_batch(
    profiles: List[Dict[str, Any]],
    validator: Optional[ProfileValidator] = None
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Validate a batch of profiles.
    
    Args:
        profiles: List of profile dictionaries
        validator: ProfileValidator instance (creates new if None)
        
    Returns:
        Tuple of (passed, reason, details)
    """
    if validator is None:
        validator = ProfileValidator()
    
    # Validate each profile individually
    for i, profile in enumerate(profiles):
        result = validator.validate_single_profile(profile)
        if not result.passed:
            logger.warning(
                f"Profile {i} failed validation: {result.reason}",
                extra={"validation_type": result.validation_type, "details": result.details}
            )
            return False, f"Profile {i}: {result.reason}", result.details
    
    # Check diversity across profiles
    diversity_result = validator.check_profile_diversity(profiles)
    if not diversity_result.passed:
        logger.warning(
            f"Profile set failed diversity check: {diversity_result.reason}",
            extra={"validation_type": diversity_result.validation_type, "details": diversity_result.details}
        )
        return False, diversity_result.reason, diversity_result.details
    
    return True, None, None

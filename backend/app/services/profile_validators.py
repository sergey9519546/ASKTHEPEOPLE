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

# Similarity above which two personas are treated as clones.
#
# The batch gate runs POPULATION-WIDE (every profile against every other), so
# its threshold is a collapse detector, not a pairwise-distinctness
# requirement. Measured on a real 5,000-variant tier-4 population:
#
#   legitimate pairs   p99 0.351   p99.9 0.478   TRUE MAX 0.634
#   (the true max is the nearest pair found by an inverted-index top-k search,
#   not a random sample, which under-reported it as 0.618)
#
#   deliberately cloned pairs, by share of words substituted:
#     2% / 5%   -> 0.911
#     10%       -> 0.814
#     15%       -> 0.698
#
# 0.75 sits between the two populations: 0.12 above every legitimate pair and
# 0.06 below a 10%-substituted clone. The previous value of 0.90 caught only
# substitutions of 5% or less, because 0.911 was the first clone score below
# it. 0.70 was rejected: the 15% clone scores 0.698, so a 0.70 gate has no
# usable margin on the clone side.
#
# The *within-archetype* distinctness requirement — the "these are 20
# distinct characters" bar — is 0.60 and lives in
# `tests/evals/test_variant_persona_distinctness.py`, which measures one
# archetype at a time (measured worst there: 0.253).
#
# Named because `_check_duplicate_personas` derives its candidate-prefix
# length from this value; changing it changes the index geometry, not just
# the cut.
_NEAR_DUPLICATE_THRESHOLD = 0.75
_PERSONA_SHINGLE_SIZE = 3

# Population above which the pairwise near-duplicate stage is skipped. 750 is
# where ~280k comparisons still finish in well under a second, which is the
# entity-generation batch size this stage actually serves. Above it the exact
# -duplicate stage still runs over every profile, so total collapse is still
# caught — see `_check_duplicate_personas`.
_MAX_NEAR_DUPLICATE_PROFILES = 750

# Sentence prefixes that are identical in every variant BY DESIGN and must not
# count toward similarity: the mandated disclosure, the role framing, and the
# centroid scenario context. Kept in step with
# `tests/evals/test_variant_persona_distinctness.py`, which strips the same
# prefixes and explains why.
_PERSONA_BOILERPLATE_PREFIXES = (
    "fictional scenario character",
    "fictional scenario profile",
    "scenario context:",
)


def persona_discriminating_text(persona: str) -> str:
    """The part of a persona that is supposed to differ between characters.

    Drops the sentences every variant carries by construction: the mandatory
    fictional-scenario disclosure, the role framing, and the centroid's
    scenario context. Returns whitespace-normalised text.
    """
    kept: List[str] = []
    for sentence in str(persona).split(". "):
        if sentence.lower().strip().rstrip(".").startswith(
            _PERSONA_BOILERPLATE_PREFIXES
        ):
            continue
        kept.append(sentence)
    return " ".join(" ".join(kept).lower().split())


def _shingles(text: str, size: int = _PERSONA_SHINGLE_SIZE) -> set:
    words = persona_discriminating_text(text).split()
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def persona_similarity(
    left: str,
    right: str,
    *,
    size: int = _PERSONA_SHINGLE_SIZE,
) -> float:
    """Shingle Jaccard over the discriminating part of two personas."""
    a = _shingles(left, size)
    b = _shingles(right, size)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

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
    def success(details: Optional[Dict] = None):
        return ValidationResult(passed=True, details=details)
    
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
        """Reject exact duplicates always; near-duplicates when affordable.

        Two stages with different costs and different scopes.

        **Exact duplicates** are an O(n) dict lookup and always run, at any
        population size. This is the stage that catches real collapse, and it
        catches the failure this gate was written for: a generation run that
        emits the same paragraph thousands of times.

        **Near-duplicates** need every pair compared, which is O(n^2). They
        run only when the population is small enough for that to be cheap
        (`_MAX_NEAR_DUPLICATE_PROFILES`). Above the cap the stage is skipped
        and says so in `details` and in the log, rather than silently
        reporting an exhaustive result it did not compute.

        Why a cap and not a smarter index: an inverted index over a
        document-frequency-ordered prefix was implemented and removed. It is
        exact, but compositional personas draw from a vocabulary of a few
        hundred words (measured: 252 across 1,000 variants), so even the
        rarest words have document frequency in the dozens and posting lists
        run hundreds long. Measured candidate count was 364 per profile
        against ~500 for the plain double loop — a 27% saving for an index
        whose soundness then has to be argued and tested. Plain O(n^2) inside
        a documented budget is the better trade.

        Similarity is measured on the discriminating text only
        (`persona_similarity`). The raw persona is dominated by boilerplate
        every profile is REQUIRED to carry, which put legitimate variants at
        0.93-0.95 similarity and made the gate unsatisfiable.
        """
        exact: Dict[str, int] = {}
        normalized: List[str] = []

        for position, profile in enumerate(profiles):
            persona = ' '.join(str(profile.get('persona', '')).lower().split())
            if persona in exact:
                return ValidationResult.failure(
                    reason=(
                        f"Duplicate persona detected "
                        f"(profiles {exact[persona]} and {position})"
                    ),
                    validation_type="duplicate_profile",
                    details={
                        "profile_indices": [exact[persona], position],
                        "persona_preview": persona[:200],
                    },
                )
            exact[persona] = position
            normalized.append(persona)

        if len(normalized) < 2:
            return ValidationResult.success()

        if len(normalized) > _MAX_NEAR_DUPLICATE_PROFILES:
            logger.warning(
                "Skipping pairwise near-duplicate scan: "
                f"{len(normalized)} profiles exceeds the "
                f"{_MAX_NEAR_DUPLICATE_PROFILES} budget. Exact-duplicate "
                "detection still ran over the whole population; "
                "near-duplicate detection did not.",
                extra={
                    "profile_count": len(normalized),
                    "budget": _MAX_NEAR_DUPLICATE_PROFILES,
                },
            )
            return ValidationResult.success(
                details={
                    "exact_duplicates_checked": True,
                    "near_duplicate_checked": False,
                    "profile_count": len(normalized),
                }
            )

        shingles = [_shingles(text) for text in normalized]
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                union = shingles[i] | shingles[j]
                if not union:
                    continue
                similarity = len(shingles[i] & shingles[j]) / len(union)
                if similarity > _NEAR_DUPLICATE_THRESHOLD:
                    return ValidationResult.failure(
                        reason=(
                            "Nearly identical personas detected "
                            f"(profiles {i} and {j}): "
                            f"{similarity:.2%} similar"
                        ),
                        validation_type="near_duplicate_profile",
                        details={
                            "profile_indices": [i, j],
                            "similarity": similarity,
                        },
                    )

        return ValidationResult.success(
            details={
                "exact_duplicates_checked": True,
                "near_duplicate_checked": True,
                "profile_count": len(normalized),
            }
        )

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

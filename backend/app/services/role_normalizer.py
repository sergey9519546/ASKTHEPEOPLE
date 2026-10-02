"""
Entity role normalization helpers.

This module turns raw graph labels into a stable downstream role contract so
profile generation, config generation, bootstrap logic, and reporting all work
from the same semantics.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .zep_entity_reader import EntityNode


_NEUTRAL_PLATFORM_PRESENCE = {"twitter": 0.7, "reddit": 0.7}
_STRUCTURAL_REASONING = (
    "Structural source-label normalization only. The mapping does not infer "
    "behavior, platform preference, public opinion, representativeness, or a forecast."
)


def _role_definition(
    normalized_role: str,
    role_family: str,
    *,
    is_individual: bool = False,
    is_institution: bool = False,
    is_media: bool = False,
    is_official: bool = False,
    confidence: float,
) -> Dict[str, Any]:
    """Build structural role metadata without behavioral defaults."""
    return {
        "normalized_role": normalized_role,
        "role_family": role_family,
        "is_individual": is_individual,
        "is_institution": is_institution,
        "is_media": is_media,
        "is_official": is_official,
        "confidence": confidence,
    }


_ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "student": _role_definition("student", "person", is_individual=True, confidence=0.96),
    "alumni": _role_definition("alumni", "person", is_individual=True, confidence=0.94),
    "professor": _role_definition("academic", "person", is_individual=True, confidence=0.95),
    "faculty": _role_definition("academic", "person", is_individual=True, confidence=0.92),
    "teacher": _role_definition(
        "educator",
        "person",
        is_individual=True,
        confidence=0.92,
    ),
    "expert": _role_definition("expert", "person", is_individual=True, confidence=0.92),
    "researcher": _role_definition(
        "researcher",
        "person",
        is_individual=True,
        confidence=0.93,
    ),
    "scientist": _role_definition(
        "researcher",
        "person",
        is_individual=True,
        confidence=0.92,
    ),
    "analyst": _role_definition(
        "analyst",
        "person",
        is_individual=True,
        confidence=0.9,
    ),
    "official": _role_definition(
        "official",
        "person",
        is_individual=True,
        is_official=True,
        confidence=0.93,
    ),
    "councilmember": _role_definition(
        "official",
        "person",
        is_individual=True,
        is_official=True,
        confidence=0.92,
    ),
    "mayor": _role_definition(
        "official",
        "person",
        is_individual=True,
        is_official=True,
        confidence=0.94,
    ),
    "journalist": _role_definition(
        "journalist",
        "media",
        is_individual=True,
        is_media=True,
        confidence=0.93,
    ),
    "mediaoutlet": _role_definition(
        "media",
        "media",
        is_institution=True,
        is_media=True,
        confidence=0.97,
    ),
    "university": _role_definition(
        "institution",
        "institution",
        is_institution=True,
        is_official=True,
        confidence=0.95,
    ),
    "institution": _role_definition(
        "institution",
        "institution",
        is_institution=True,
        confidence=0.85,
    ),
    "school": _role_definition(
        "institution",
        "institution",
        is_institution=True,
        is_official=True,
        confidence=0.92,
    ),
    "library": _role_definition(
        "civic_service",
        "institution",
        is_institution=True,
        confidence=0.9,
    ),
    "hospital": _role_definition(
        "healthcare",
        "institution",
        is_institution=True,
        is_official=True,
        confidence=0.93,
    ),
    "governmentagency": _role_definition(
        "government",
        "institution",
        is_institution=True,
        is_official=True,
        confidence=0.97,
    ),
    "council": _role_definition(
        "government",
        "institution",
        is_institution=True,
        is_official=True,
        confidence=0.92,
    ),
    "agency": _role_definition(
        "government",
        "institution",
        is_institution=True,
        is_official=True,
        confidence=0.88,
    ),
    "organization": _role_definition(
        "organization",
        "institution",
        is_institution=True,
        confidence=0.9,
    ),
    "ngo": _role_definition(
        "organization",
        "institution",
        is_institution=True,
        confidence=0.93,
    ),
    "charity": _role_definition(
        "organization",
        "institution",
        is_institution=True,
        confidence=0.92,
    ),
    "association": _role_definition(
        "organization",
        "institution",
        is_institution=True,
        confidence=0.89,
    ),
    "union": _role_definition(
        "organization",
        "institution",
        is_institution=True,
        confidence=0.9,
    ),
    "cooperative": _role_definition(
        "organization",
        "institution",
        is_institution=True,
        confidence=0.88,
    ),
    "club": _role_definition(
        "community",
        "community",
        is_institution=True,
        confidence=0.85,
    ),
    "company": _role_definition(
        "company",
        "institution",
        is_institution=True,
        confidence=0.92,
    ),
    "business": _role_definition(
        "company",
        "institution",
        is_institution=True,
        confidence=0.89,
    ),
    "community": _role_definition(
        "community",
        "community",
        is_institution=True,
        confidence=0.91,
    ),
    "neighborhood": _role_definition(
        "community",
        "community",
        is_institution=True,
        confidence=0.88,
    ),
    "group": _role_definition(
        "community",
        "community",
        is_institution=True,
        confidence=0.86,
    ),
    "person": _role_definition(
        "individual",
        "person",
        is_individual=True,
        confidence=0.8,
    ),
    "resident": _role_definition(
        "individual",
        "person",
        is_individual=True,
        confidence=0.88,
    ),
    "citizen": _role_definition(
        "individual",
        "person",
        is_individual=True,
        confidence=0.86,
    ),
    "worker": _role_definition(
        "worker",
        "person",
        is_individual=True,
        confidence=0.87,
    ),
    "parent": _role_definition(
        "individual",
        "person",
        is_individual=True,
        confidence=0.85,
    ),
    "nurse": _role_definition(
        "healthcare_worker",
        "person",
        is_individual=True,
        confidence=0.92,
    ),
    "doctor": _role_definition(
        "healthcare_worker",
        "person",
        is_individual=True,
        confidence=0.92,
    ),
    "engineer": _role_definition(
        "worker",
        "person",
        is_individual=True,
        confidence=0.9,
    ),
    "businessowner": _role_definition(
        "business_owner",
        "person",
        is_individual=True,
        confidence=0.9,
    ),
    "artist": _role_definition(
        "creator",
        "person",
        is_individual=True,
        confidence=0.87,
    ),
    "volunteer": _role_definition(
        "volunteer",
        "person",
        is_individual=True,
        confidence=0.86,
    ),
    "publicfigure": _role_definition(
        "public_figure",
        "person",
        is_individual=True,
        confidence=0.94,
    ),
    "activist": _role_definition(
        "activist",
        "person",
        is_individual=True,
        confidence=0.93,
    ),
}

_ROLE_ALIASES = {
    "public_figure": "publicfigure",
    "media": "mediaoutlet",
    "socialmediaplatform": "mediaoutlet",
    "nonprofit": "ngo",
    "charitableorganization": "charity",
    "tradeunion": "union",
    "citycouncil": "council",
}

_DEFAULT_ROLE = {
    "normalized_role": "entity",
    "role_family": "unknown",
    "is_individual": False,
    "is_institution": False,
    "is_media": False,
    "is_official": False,
    "confidence": 0.5,
}


def normalize_entity_type(raw_type: str | None) -> Dict[str, Any]:
    raw_value = (raw_type or "unknown").strip()
    key = raw_value.lower().replace(" ", "")
    key = _ROLE_ALIASES.get(key, key)
    role = dict(_DEFAULT_ROLE)
    role.update(_ROLE_DEFINITIONS.get(key, {}))
    role["raw_type"] = raw_value
    role["default_platform_presence"] = dict(_NEUTRAL_PLATFORM_PRESENCE)
    role["platform_presence_basis"] = "neutral_fictional_default"
    role["human_respondents"] = 0
    role["reasoning"] = _STRUCTURAL_REASONING
    return role


def build_entity_type_registry(entities: Iterable[EntityNode]) -> List[Dict[str, Any]]:
    registry: List[Dict[str, Any]] = []
    seen = set()
    for entity in entities:
        raw_type = entity.get_entity_type() or "Unknown"
        if raw_type in seen:
            continue
        seen.add(raw_type)
        registry.append(normalize_entity_type(raw_type))
    registry.sort(key=lambda item: item["raw_type"].lower())
    return registry

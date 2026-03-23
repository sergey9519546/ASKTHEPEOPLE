"""
Entity role normalization helpers.

This module turns raw graph labels into a stable downstream role contract so
profile generation, config generation, bootstrap logic, and reporting all work
from the same semantics.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .zep_entity_reader import EntityNode


_ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "student": {
        "normalized_role": "student",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.7, "reddit": 0.95},
        "confidence": 0.96,
        "reasoning": "Student-like entities are treated as individual participants.",
    },
    "alumni": {
        "normalized_role": "alumni",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.7, "reddit": 0.85},
        "confidence": 0.94,
        "reasoning": "Alumni behave like individual participants with slightly broader reach.",
    },
    "professor": {
        "normalized_role": "academic",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.8, "reddit": 0.55},
        "confidence": 0.95,
        "reasoning": "Professors map to academically oriented individual actors.",
    },
    "faculty": {
        "normalized_role": "academic",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.75, "reddit": 0.5},
        "confidence": 0.92,
        "reasoning": "Faculty roles are normalized as academic actors.",
    },
    "expert": {
        "normalized_role": "expert",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.8, "reddit": 0.55},
        "confidence": 0.92,
        "reasoning": "Experts are treated as individual subject matter actors.",
    },
    "official": {
        "normalized_role": "official",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": True,
        "default_platform_presence": {"twitter": 0.82, "reddit": 0.4},
        "confidence": 0.93,
        "reasoning": "Officials are individual actors with authority-sensitive behavior.",
    },
    "journalist": {
        "normalized_role": "journalist",
        "role_family": "media",
        "is_individual": True,
        "is_institution": False,
        "is_media": True,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.92, "reddit": 0.45},
        "confidence": 0.93,
        "reasoning": "Journalists are individual media actors.",
    },
    "mediaoutlet": {
        "normalized_role": "media",
        "role_family": "media",
        "is_individual": False,
        "is_institution": True,
        "is_media": True,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.96, "reddit": 0.55},
        "confidence": 0.97,
        "reasoning": "Media outlets are institutional media actors.",
    },
    "university": {
        "normalized_role": "institution",
        "role_family": "institution",
        "is_individual": False,
        "is_institution": True,
        "is_media": False,
        "is_official": True,
        "default_platform_presence": {"twitter": 0.88, "reddit": 0.3},
        "confidence": 0.95,
        "reasoning": "Universities are institutional actors with semi-official communication patterns.",
    },
    "governmentagency": {
        "normalized_role": "government",
        "role_family": "institution",
        "is_individual": False,
        "is_institution": True,
        "is_media": False,
        "is_official": True,
        "default_platform_presence": {"twitter": 0.9, "reddit": 0.22},
        "confidence": 0.97,
        "reasoning": "Government agencies are official institutional actors.",
    },
    "organization": {
        "normalized_role": "organization",
        "role_family": "institution",
        "is_individual": False,
        "is_institution": True,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.78, "reddit": 0.5},
        "confidence": 0.9,
        "reasoning": "Organizations are institutional non-state actors.",
    },
    "ngo": {
        "normalized_role": "organization",
        "role_family": "institution",
        "is_individual": False,
        "is_institution": True,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.82, "reddit": 0.58},
        "confidence": 0.93,
        "reasoning": "NGOs are institutional advocacy actors.",
    },
    "company": {
        "normalized_role": "company",
        "role_family": "institution",
        "is_individual": False,
        "is_institution": True,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.86, "reddit": 0.38},
        "confidence": 0.92,
        "reasoning": "Companies are corporate institutional actors.",
    },
    "community": {
        "normalized_role": "community",
        "role_family": "community",
        "is_individual": False,
        "is_institution": True,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.65, "reddit": 0.9},
        "confidence": 0.91,
        "reasoning": "Communities map to group actors with stronger discussion-platform presence.",
    },
    "group": {
        "normalized_role": "community",
        "role_family": "community",
        "is_individual": False,
        "is_institution": True,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.62, "reddit": 0.88},
        "confidence": 0.86,
        "reasoning": "Generic groups default to community actors.",
    },
    "person": {
        "normalized_role": "individual",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.75, "reddit": 0.78},
        "confidence": 0.8,
        "reasoning": "Unqualified people are generic individual actors.",
    },
    "publicfigure": {
        "normalized_role": "public_figure",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.92, "reddit": 0.4},
        "confidence": 0.94,
        "reasoning": "Public figures are high-visibility individual actors.",
    },
    "activist": {
        "normalized_role": "activist",
        "role_family": "person",
        "is_individual": True,
        "is_institution": False,
        "is_media": False,
        "is_official": False,
        "default_platform_presence": {"twitter": 0.88, "reddit": 0.82},
        "confidence": 0.93,
        "reasoning": "Activists are individual advocacy actors.",
    },
}

_ROLE_ALIASES = {
    "teacher": "professor",
    "government": "governmentagency",
    "agency": "governmentagency",
    "institution": "university",
    "public_figure": "publicfigure",
    "media": "mediaoutlet",
    "socialmediaplatform": "mediaoutlet",
}

_DEFAULT_ROLE = {
    "normalized_role": "entity",
    "role_family": "unknown",
    "is_individual": False,
    "is_institution": False,
    "is_media": False,
    "is_official": False,
    "default_platform_presence": {"twitter": 0.7, "reddit": 0.7},
    "confidence": 0.5,
    "reasoning": "Fallback role used because the raw label has no specialized mapping yet.",
}


def normalize_entity_type(raw_type: str | None) -> Dict[str, Any]:
    raw_value = (raw_type or "unknown").strip()
    key = raw_value.lower().replace(" ", "")
    key = _ROLE_ALIASES.get(key, key)
    role = dict(_DEFAULT_ROLE)
    role.update(_ROLE_DEFINITIONS.get(key, {}))
    role["raw_type"] = raw_value
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

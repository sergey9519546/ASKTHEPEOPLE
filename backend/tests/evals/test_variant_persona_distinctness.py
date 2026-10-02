"""Variant Persona Distinctness Evaluation (Gate 5 requirement).

The 50,000-character tier's binding property: archetype variants are
**distinct characters**, not clones. The unit tests in
`tests/test_persona_composition.py` assert exact string distinctness on a
small population; this eval measures *similarity* — two variants can differ
in a single word yet read as the same character, which exact-string checks
cannot catch.

Acceptance: for every archetype, the maximum shingle Jaccard similarity
between any two variant personas is <= 0.60.
"""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.archetype_engine import AgentArchetype, ArchetypeEngine
from app.services.oasis_profile_generator import OasisAgentProfile
from tests.evals.conftest import save_eval_results  # noqa: F401

MAX_SIMILARITY = 0.60
SHINGLE_SIZE = 3


def _shingles(text: str, size: int = SHINGLE_SIZE) -> set:
    """Word-level shingle set for Jaccard similarity, computed on the
    VARIANT-SPECIFIC portion of the persona.

    The persona carries shared boilerplate by design: the role framing and
    the mandatory disclosure are identical in every variant (the disclosure
    is a legal requirement, not a character trait). Measuring similarity on
    the whole string would read two honest variants as clones whenever the
    boilerplate outweighs the axes — which it does at a 1-2 sentence
    disclosure. The boilerplate lines are stripped first, so the score
    measures what SHOULD differ: posture, voice, concerns, disposition.
    """
    boilerplate_prefixes = (
        "fictional scenario character",
        "fictional scenario profile",
        "scenario context:",
    )
    kept: list = []
    for sentence in text.split(". "):
        normalized = sentence.lower().strip().rstrip(".")
        if normalized.startswith(boilerplate_prefixes):
            continue
        kept.append(sentence)
    words = " ".join(kept).lower().split()
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _expand(archetype_id: int, count: int, topics: list) -> list:
    archetype = AgentArchetype(
        archetype_id=archetype_id,
        label="resident",
        member_indices=[0],
        centroid_index=0,
        source_entity_uuids=[],
    )
    centroid = OasisAgentProfile(
        user_id=0,
        user_name="centroid_resident",
        name="Centroid Resident",
        bio="Fictional scenario account for the resident role.",
        persona="Centroid persona paragraph for the resident archetype.",
        profession="Resident",
        interested_topics=list(topics),
    )
    return ArchetypeEngine().expand_archetype(
        archetype, centroid, count, base_agent_id=100,
    )


def _max_similarity(personas: list) -> float:
    worst = 0.0
    for i in range(len(personas)):
        shingles_i = _shingles(personas[i])
        for j in range(i + 1, len(personas)):
            similarity = _jaccard(shingles_i, _shingles(personas[j]))
            if similarity > worst:
                worst = similarity
    return worst


def test_variant_personas_do_not_collapse(eval_results_path):
    """For every archetype, the most-similar pair of variant personas must
    stay below the collapse threshold."""
    topic_sets = [
        ["Recycling", "Local Events", "Public Services", "Community"],
        ["Housing", "Transport", "Budget"],
        ["Education", "Safety"],
    ]
    results = {}
    for archetype_id, topics in enumerate(topic_sets, start=1):
        variants = _expand(archetype_id=archetype_id, count=20, topics=topics)
        personas = [v.persona for v in variants]
        worst = _max_similarity(personas)
        results[f"archetype_{archetype_id}_max_similarity"] = round(worst, 4)
        assert worst <= MAX_SIMILARITY, (
            f"archetype {archetype_id}: most-similar variant pair scored "
            f"{worst:.3f} (threshold {MAX_SIMILARITY}) — the crowd is "
            "collapsing into clones"
        )

    save_eval_results(
        {
            "variant_persona_distinctness_passed": True,
            "variant_persona_max_similarity_threshold": MAX_SIMILARITY,
            "variant_persona_shingle_size": SHINGLE_SIZE,
            **results,
        },
        eval_results_path,
    )


def test_short_topic_lists_stay_distinct():
    """A 2-topic centroid is the realistic worst case: the rotation has only
    2 orderings, so the voice/posture axes must carry the distinctness."""
    variants = _expand(
        archetype_id=11, count=20, topics=["Housing", "Transport"],
    )
    personas = [v.persona for v in variants]
    assert len(set(personas)) == 20
    worst = _max_similarity(personas)
    assert worst <= MAX_SIMILARITY, worst

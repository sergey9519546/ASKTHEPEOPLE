"""Compositional persona distinctness (the 50k-tier property).

The binding constraint on the 50,000-character tier: variants must be
**distinct characters**, not clones of one persona paragraph. Verbatim
copying produced variants differing only in username, age, and jittered Big
Five scores — 50,000 copies of one paragraph is one character repeated.

The tests here assert three directions: variants are textually distinct,
every variant carries the mandatory disclosure, and generation is
deterministic (a rerun reproduces the same population).
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.archetype_engine import AgentArchetype, ArchetypeEngine
from app.services.oasis_profile_generator import OasisAgentProfile
from app.services.persona_composition import (
    DISCLOSURE_SUFFIX,
    compose_variant_persona,
)
from app.services.role_normalizer import normalize_entity_type


_ROLE = normalize_entity_type("resident")
_TOPICS = ["Recycling", "Local Events", "Public Services", "Community"]
_CONSTRAINT = "Operates as an individual with limited discretionary resources."


def _centroid(big_five: dict | None = None) -> OasisAgentProfile:
    return OasisAgentProfile(
        user_id=0,
        user_name="centroid_resident",
        name="Centroid Resident",
        bio="Fictional scenario account for the resident role.",
        persona="Centroid persona paragraph for the resident archetype.",
        big_five=big_five,
        profession="Resident",
        interested_topics=list(_TOPICS),
    )


def _expand(archetype_id: int, count: int, big_five: dict | None = None):
    archetype = AgentArchetype(
        archetype_id=archetype_id,
        label="resident",
        member_indices=[0],
        centroid_index=0,
        source_entity_uuids=[],
    )
    return ArchetypeEngine().expand_archetype(
        archetype,
        _centroid(big_five),
        count,
        base_agent_id=100,
    )


# --- distinctness --------------------------------------------------------- #


def test_no_two_variants_share_a_persona():
    """The collision test: 20 variants produce 20 distinct persona strings."""
    variants = _expand(archetype_id=7, count=20)
    personas = [v.persona for v in variants]
    assert len(set(personas)) == 20


def test_no_two_variants_share_a_bio():
    variants = _expand(archetype_id=7, count=20)
    bios = [v.bio for v in variants]
    assert len(set(bios)) == 20


def test_no_two_variants_share_a_username():
    variants = _expand(archetype_id=7, count=20)
    usernames = [v.user_name for v in variants]
    assert len(set(usernames)) == 20


def test_usernames_are_globally_unique_across_archetypes():
    """The old f'{label}_{n:02d}' form collided across archetypes; the
    archetype stem makes usernames unique across the whole population."""
    all_usernames = set()
    for archetype_id in range(250):
        variants = _expand(archetype_id=archetype_id, count=20)
        for v in variants:
            all_usernames.add(v.user_name)
    # 250 archetypes x 20 variants = 5,000 unique usernames.
    assert len(all_usernames) == 5_000


def test_personas_differ_across_archetypes():
    """Variants of DIFFERENT archetypes must not share a persona either."""
    p_a = _expand(archetype_id=1, count=3)[0].persona
    p_b = _expand(archetype_id=2, count=3)[0].persona
    assert p_a != p_b


# --- disclosure ----------------------------------------------------------- #


def test_disclosure_suffix_in_every_variant():
    """A variant that dropped the fictional-scenario disclosure would
    present synthetic text as human evidence."""
    variants = _expand(archetype_id=7, count=20)
    for v in variants:
        assert DISCLOSURE_SUFFIX in v.persona
        # Case-insensitive: the bio opens with "Fictional", the same word the
        # old verbatim bio carried.
        assert "fictional" in v.bio.lower()


def test_persona_mentions_the_scenario_role():
    variants = _expand(archetype_id=7, count=5)
    for v in variants:
        assert "Fictional scenario character" in v.persona


# --- determinism ------------------------------------------------------------ #


def test_generation_is_deterministic():
    """Same seed -> the same population. A rerun must reproduce the same
    50,000 characters, not a fresh random draw."""
    run_1 = _expand(archetype_id=7, count=10)
    run_2 = _expand(archetype_id=7, count=10)
    for v1, v2 in zip(run_1, run_2):
        assert v1.user_name == v2.user_name
        assert v1.persona == v2.persona
        assert v1.bio == v2.bio
        assert v1.age == v2.age


# --- no verbatim copies ----------------------------------------------------- #


def test_variant_persona_is_not_the_centroid_paragraph():
    """The centroid's paragraph anchors the archetype as scenario context;
    a variant repeating it verbatim is the old clone behavior."""
    centroid = _centroid()
    variants = _expand(archetype_id=7, count=10)
    for v in variants:
        assert v.persona != centroid.persona


def test_scenario_context_is_anchored_from_the_centroid():
    """The centroid's persona context appears (truncated) in the variant —
    the archetype linkage survives without a verbatim copy."""
    variants = _expand(archetype_id=7, count=5)
    for v in variants:
        assert "Scenario context:" in v.persona


# --- the composer is pure ---------------------------------------------------- #


def test_composer_is_a_pure_function():
    """No client, no Config, no network: the composer is a function of its
    inputs only, so the distinctness tests are deterministic."""
    import inspect

    from app.services import persona_composition

    signature = inspect.signature(persona_composition.compose_variant_persona)
    params = set(signature.parameters)
    assert "client" not in params
    assert "config" not in params

    source = inspect.getsource(persona_composition)
    assert "OpenAI(" not in source
    assert "requests.get" not in source
    assert "urlopen" not in source


def test_disposition_from_jittered_big_five():
    """The disposition axis is selected by the jittered Big Five dominant
    trait, so variants with different dominant traits differ there too."""
    variants = _expand(
        archetype_id=7,
        count=20,
        big_five={
            "openness": 50, "conscientiousness": 50, "extraversion": 50,
            "agreeableness": 50, "neuroticism": 50,
        },
    )
    # With a real base score the jitter produces differing dominant traits
    # across variants; assert the disposition section exists in every one.
    for v in variants:
        assert "Disposition:" in v.persona

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
    _ATTENTION_FOCI,
    _DISPOSITION_ROTATIONS,
    _ENGAGEMENT_POSTURES,
    _EXPANSION_STRIDE,
    _VOICE_TEXTURES,
    _axis_space,
    _axis_values,
    _dominant_trait,
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


# --- population-wide distinctness -------------------------------------------- #
#
# Everything above measures ONE archetype. That was a blind spot: a
# per-archetype guarantee says nothing about two variants of DIFFERENT
# archetypes, and a composition scheme that was injective inside an archetype
# still produced exact duplicate personas across archetypes.


def test_axis_tuple_is_injective_across_the_whole_population():
    """No two variants anywhere share a (posture, voice, disposition, focus).

    The property the per-archetype tests cannot see. A per-archetype shuffle
    was injective within an archetype and still collided across them.
    """
    triples = {
        _axis_values(archetype_id, variant_index)
        for archetype_id in range(1, 251)
        for variant_index in range(20)
    }
    assert len(triples) == 250 * 20


def test_axis_space_covers_the_declared_population():
    """The radix decomposition must not wrap at the declared population size."""
    from app.utils.input_policy import ARCHETYPE_COUNT_MAX, ARCHETYPE_EXPANSION_MAX

    assert _axis_space() >= ARCHETYPE_COUNT_MAX * ARCHETYPE_EXPANSION_MAX


def test_no_axis_length_divides_the_composition_stride():
    """An axis whose length divides the stride is constant within an archetype.

    With 20-entry axes and a stride of 20, `slot // 20` never changes inside
    one archetype, so every variant shared a single voice texture — 20
    variants produced 4 distinct bios. `_validate_axes` raises on this; the
    test pins the invariant rather than relying on the import guard alone.
    """
    import math

    from app.services.persona_composition import _EXPANSION_STRIDE

    for axis in (
        _ENGAGEMENT_POSTURES, _VOICE_TEXTURES,
        _DISPOSITION_ROTATIONS, _ATTENTION_FOCI,
    ):
        assert math.gcd(len(axis), _EXPANSION_STRIDE) == 1, len(axis)


def test_personas_are_distinct_across_different_archetypes():
    """Cross-archetype exact duplicates: the case one-archetype tests miss."""
    seen = {}
    for archetype_id in range(1, 41):
        for variant in _expand(archetype_id=archetype_id, count=20):
            assert variant.persona not in seen, (
                f"archetypes {seen.get(variant.persona)} and {archetype_id} "
                "produced the same persona"
            )
            seen[variant.persona] = archetype_id
    assert len(seen) == 800


# --- the Big Five tie ------------------------------------------------------ #


def test_uniform_traits_yield_no_dominant_trait():
    """A tie is not a dominant trait.

    `ENABLE_TRAIT_INFERENCE` is off by default, so every profile carries the
    neutral population midpoint: all five scores equal. `max()` on that
    returns whichever key iterates first, so every variant was handed the
    same trait-derived disposition and the whole axis collapsed while still
    looking trait-driven.
    """
    neutral = dict.fromkeys(
        ("openness", "conscientiousness", "extraversion",
         "agreeableness", "neuroticism"),
        50.0,
    )
    assert _dominant_trait(neutral) is None
    assert _dominant_trait({"openness": 80.0, "conscientiousness": 20.0}) == "openness"
    assert _dominant_trait(None) is None


def test_uniform_traits_produce_distinct_dispositions():
    """Tied traits must not pin every variant to one disposition.

    Exercised on the composer directly: `expand_archetype` jitters the
    centroid's traits, so it cannot produce the tied input that this guards.
    """
    neutral = dict.fromkeys(
        ("openness", "conscientiousness", "extraversion",
         "agreeableness", "neuroticism"),
        50.0,
    )
    dispositions = set()
    for variant_index in range(20):
        persona = compose_variant_persona(
            archetype_id=7,
            variant_index=variant_index,
            role_info={"normalized_role": "resident", "role_family": "person"},
            concern_topics=list(_TOPICS),
            disposition_traits=neutral,
            constraint_text=None,
        )
        dispositions.add(persona.split("Disposition: ")[1].split(".")[0])
    # Not 20: mixed radix advances only the low digit within one archetype,
    # so individual axes are not guaranteed to differ there. What must not
    # happen is collapse onto ONE disposition — the defect this fixes. The
    # per-variant distinctness guarantee is on the triple, asserted
    # separately by test_axis_tuple_is_injective_across_the_whole_population
    # and test_no_two_variants_share_a_persona.
    assert len(dispositions) >= 15


def test_a_real_dominant_trait_is_still_honoured():
    """Tie-detection must not discard a genuine winner."""
    winner = {
        "openness": 80.0, "conscientiousness": 20.0, "extraversion": 30.0,
        "agreeableness": 40.0, "neuroticism": 25.0,
    }
    dispositions = {
        compose_variant_persona(
            archetype_id=7,
            variant_index=variant_index,
            role_info={"normalized_role": "resident", "role_family": "person"},
            concern_topics=list(_TOPICS),
            disposition_traits=winner,
            constraint_text=None,
        ).split("Disposition: ")[1].split(".")[0]
        for variant_index in range(20)
    }
    assert dispositions == {
        "drawn to new angles and alternatives in the discussion"
    }


# --- the global RNG must not be touched ------------------------------------ #


def test_expansion_does_not_mutate_the_global_rng():
    """`expand_archetype` must not reseed the interpreter-global stream.

    It called `random.seed()` inside the per-variant loop, so anything later
    in the same worker that read the global stream — FollowerEngine runs in
    the same call — inherited a stream advanced by an unrelated loop.
    """
    import random as stdlib_random

    stdlib_random.seed(1234)
    expected = [stdlib_random.random() for _ in range(5)]
    stdlib_random.seed(1234)
    _expand(archetype_id=7, count=20)
    assert [stdlib_random.random() for _ in range(5)] == expected

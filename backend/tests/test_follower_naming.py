"""Follower naming distinctness (the 50k-tier crowd property).

A 45,000-follower crowd of "Follower 42" names reads as a counter, not
characters. The compositional matrix gives every follower a role/topic-varied
display name while staying deterministic and collision-free. The agent_name
remains the unique identifier either way.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.follower_engine import FollowerEngine


def test_45k_followers_all_have_display_names():
    engine = FollowerEngine(id_base=1000)
    followers = engine.generate_followers(45_000)
    assert len(followers) == 45_000
    assert all(f.display_name for f in followers)


def test_45k_followers_unique_agent_names():
    engine = FollowerEngine(id_base=1000)
    followers = engine.generate_followers(45_000)
    agent_names = [f.agent_name for f in followers]
    assert len(set(agent_names)) == 45_000


def test_crowd_names_are_not_uniform():
    """A crowd of identical display names is a counter, not characters."""
    engine = FollowerEngine(id_base=1000)
    followers = engine.generate_followers(45_000)
    display_names = [f.display_name for f in followers]
    distinct = len(set(display_names))
    # With 8 roles x rotated topics the crowd must not collapse to a
    # handful of names; assert a broad spread rather than exact uniqueness.
    assert distinct >= 100, f"only {distinct} distinct display names in 45,000"


def test_naming_is_deterministic():
    """Display names are a pure function of the index (role rotation), so
    two runs produce the same names. agent_name embeds the behavior, which
    is stochastic by design and not part of the naming contract."""
    engine = FollowerEngine(id_base=1000)
    run_1 = engine.generate_followers(50)
    run_2 = engine.generate_followers(50)
    for f1, f2 in zip(run_1, run_2):
        assert f1.display_name == f2.display_name
        # The unique identifier carries the index regardless of behavior.
        assert f1.agent_name.split("_")[-1] == f2.agent_name.split("_")[-1]


def test_follower_contract_unchanged():
    """The action schema and behavior assignment did not change."""
    engine = FollowerEngine(id_base=1000)
    followers = engine.generate_followers(100)
    for f in followers:
        assert f.behavior_type.value in {"AMPLIFIER", "CONTRARIAN", "NEUTRAL", "LURKER"}
        assert -1.0 <= f.opinion_bias <= 1.0
        assert 0.0 <= f.activity_probability <= 1.0


def test_no_follower_display_name_falls_back_to_the_generic_label():
    """Every rotation entry must normalize to a real role.

    The rotation listed "individual", which is absent from the role table, so
    it normalized to the generic "entity" fallback and one follower in eight
    was named "Entity 5" in a 45,000-follower crowd.
    """
    from app.services.follower_engine import FollowerEngine

    names = [
        agent.display_name
        for agent in FollowerEngine().generate_followers(2000)
    ]
    assert all(names)
    generic = [n for n in names if n.startswith("Entity ")]
    assert not generic, f"{len(generic)} followers got the generic label"


def test_follower_display_names_are_unique_across_the_full_crowd():
    from app.services.follower_engine import FollowerEngine

    agents = FollowerEngine().generate_followers(5000)
    assert len({a.display_name for a in agents}) == 5000
    assert len({a.agent_name for a in agents}) == 5000

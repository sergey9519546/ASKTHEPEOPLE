"""Seeded follower observations stay local to each follower and round."""

import random

import pytest

from app.services.follower_engine import FollowerEngine


def _observations(actions):
    return [{k: v for k, v in action.items() if k != "timestamp"} for action in actions]


def _leaders():
    return [
        {"action_type": "CREATE_POST", "action_args": {"tweet_id": f"p{i}", "content": f"Fiction {i}"}}
        for i in range(10)
    ]


def test_seeded_follower_generation_replays_without_global_rng_changes():
    engine = FollowerEngine(seed=0)
    before = random.getstate()
    first = engine.generate_followers(100)
    assert random.getstate() == before
    try:
        for _ in range(100):
            random.random()
        assert FollowerEngine(seed=0).generate_followers(100) == first
        assert engine.generate_followers(100) == first
    finally:
        random.setstate(before)
    assert FollowerEngine(seed=1).generate_followers(100) != first
    assert engine.generate_followers(10) == first[:10]


@pytest.mark.parametrize("platform", ["twitter", "reddit"])
def test_seeded_reactions_replay_despite_other_platforms_rounds_and_global_draws(platform):
    engine = FollowerEngine(seed=17)
    followers = engine.generate_followers(200)
    leaders = _leaders()
    before = random.getstate()
    first = _observations(engine.compute_round_actions(followers, leaders, 3, platform, max_actions=20))
    assert random.getstate() == before
    try:
        for _ in range(100):
            random.random()
        engine.compute_round_actions(followers, leaders, 4, "reddit", max_actions=20)
        replay = engine.compute_round_actions(followers, leaders, 3, platform, max_actions=20)
    finally:
        random.setstate(before)
    assert _observations(replay) == first
    assert len(first) == 20
    assert all(row["is_follower"] for row in first)
    assert _observations(FollowerEngine(seed=18).compute_round_actions(
        followers, leaders, 3, platform, max_actions=20
    )) != first


def test_seeded_reactions_are_independent_of_follower_order_and_other_followers():
    engine = FollowerEngine(seed=17)
    followers = engine.generate_followers(200)
    expected = _observations(engine.compute_round_actions(followers, _leaders(), 3, "twitter"))
    reordered = _observations(engine.compute_round_actions(list(reversed(followers)), _leaders(), 3, "twitter"))
    assert reordered == expected
    subset = _observations(engine.compute_round_actions(followers[:20], _leaders(), 3, "twitter"))
    assert subset == [row for row in expected if row["agent_id"] < 1020]


def test_local_rng_injection_preserves_global_rng():
    before = random.getstate()
    engine = FollowerEngine(rng=random.Random(7))
    other = FollowerEngine(rng=random.Random(7))
    followers = engine.generate_followers(100)
    assert other.generate_followers(100) == followers
    assert _observations(engine.compute_round_actions(followers, _leaders(), 1, "twitter")) == _observations(
        other.compute_round_actions(followers, _leaders(), 1, "twitter")
    )
    assert random.getstate() == before


@pytest.mark.parametrize("seed", [True, False, -1, 2**63, "7", 7.0])
def test_invalid_follower_seeds_are_rejected(seed):
    with pytest.raises(ValueError, match="seed"):
        FollowerEngine(seed=seed)


def test_follower_seed_and_injected_rng_are_mutually_exclusive():
    with pytest.raises(ValueError, match="seed.*rng|rng.*seed"):
        FollowerEngine(seed=7, rng=random.Random(7))

"""Tier-4 crowd throughput: 45,000 followers must stay inside the round budget.

The tier-4 composition is 5,000 LLM agents + 45,000 rule-based followers.
Follower actions are computed in the monitor thread after every OASIS round,
so the per-round compute is on the critical path of round advancement — a
slow round here stalls the whole run. These tests pin:

1. Per-round compute for the full 45k crowd stays well under one round's
   monitoring interval (the monitor sleeps 2s between polls; the budget here
   is 5s/round to leave headroom for I/O on the same thread).
2. The configured action ceiling is actually a ceiling — an uncapped crowd
   produces ~18k writes/round/platform of pure volume.
3. The down-sample is deterministic: the same round keeps the same subset.
"""

from __future__ import annotations

import random
import time

import pytest

from app.config import Config
from app.services.follower_engine import FollowerEngine


FOLLOWER_COUNT = 45_000
ROUNDS = 10
PER_ROUND_BUDGET_S = 5.0
CAP = Config.TIER4_CROWD_ACTIONS_PER_ROUND_MAX


@pytest.fixture(scope="module")
def crowd():
    engine = FollowerEngine()
    return engine, engine.generate_followers(FOLLOWER_COUNT)


@pytest.fixture(scope="module")
def leader_actions():
    rng = random.Random(20261001)
    # A representative leader round: ~200 posts/comments to react to.
    return [
        {
            "action_type": rng.choice(
                ["CREATE_POST", "QUOTE_POST", "CREATE_COMMENT"]
            ),
            "action_args": {
                "tweet_id": f"t{i}",
                "post_id": f"p{i}",
                "content": f"Leader content {i}",
            },
        }
        for i in range(200)
    ]


def test_full_crowd_stays_in_round_budget(crowd, leader_actions):
    engine, followers = crowd
    timings = []
    for round_num in range(1, ROUNDS + 1):
        start = time.perf_counter()
        engine.compute_round_actions(
            followers,
            leader_actions,
            round_num,
            "twitter",
            max_actions=CAP,
        )
        timings.append(time.perf_counter() - start)
    slowest = max(timings)
    assert slowest < PER_ROUND_BUDGET_S, (
        f"slowest round took {slowest:.2f}s (budget {PER_ROUND_BUDGET_S}s); "
        f"round compute is on the monitor thread's critical path"
    )


def test_capped_round_never_exceeds_ceiling(crowd, leader_actions):
    engine, followers = crowd
    for round_num in range(1, ROUNDS + 1):
        for platform in ("twitter", "reddit"):
            actions = engine.compute_round_actions(
                followers, leader_actions, round_num, platform, max_actions=CAP
            )
            assert len(actions) <= CAP


def test_downsample_is_deterministic_per_round(crowd, leader_actions, monkeypatch):
    # The pre-cap computation uses the module-global RNG, so "the same round
    # keeps the same subset" is only well-defined when that RNG is seeded.
    # Seed the module two ways and confirm the kept subsets match.
    import app.services.follower_engine as fe

    engine, followers = crowd
    monkeypatch.setattr(fe, "_rng", random.Random(7))
    first = engine.compute_round_actions(
        followers, leader_actions, 3, "twitter", max_actions=CAP
    )
    monkeypatch.setattr(fe, "_rng", random.Random(7))
    second = engine.compute_round_actions(
        followers, leader_actions, 3, "twitter", max_actions=CAP
    )
    assert len(first) == CAP
    assert [a["agent_id"] for a in first] == [a["agent_id"] for a in second]
    # And a different seed keeps a different subset (the set isn't "first N")
    monkeypatch.setattr(fe, "_rng", random.Random(8))
    other = engine.compute_round_actions(
        followers, leader_actions, 3, "twitter", max_actions=CAP
    )
    assert [a["agent_id"] for a in first] != [a["agent_id"] for a in other]


def test_different_rounds_keep_different_subsets(crowd, leader_actions):
    engine, followers = crowd
    kept = [
        {a["agent_id"] for a in engine.compute_round_actions(
            followers, leader_actions, r, "twitter", max_actions=CAP
        )}
        for r in range(1, 5)
    ]
    # Not all rounds keep the identical subset
    assert len({frozenset(s) for s in kept}) > 1


def test_uncapped_small_crowd_is_untouched(monkeypatch):
    """The default 100-follower run must not be affected by the cap."""
    import app.services.follower_engine as fe

    engine = FollowerEngine()
    monkeypatch.setattr(fe, "_rng", random.Random(11))
    followers = engine.generate_followers(100)
    leaders = [
        {"action_type": "CREATE_POST", "action_args": {"tweet_id": "t1", "content": "x"}}
    ]
    monkeypatch.setattr(fe, "_rng", random.Random(11))
    capped = engine.compute_round_actions(followers, leaders, 1, "twitter", max_actions=CAP)
    monkeypatch.setattr(fe, "_rng", random.Random(11))
    uncapped = engine.compute_round_actions(followers, leaders, 1, "twitter")
    # 100 followers cannot exceed a 2000 ceiling; both paths compute the full set
    assert len(capped) == len(uncapped) <= 200

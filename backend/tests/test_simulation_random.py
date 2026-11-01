"""Offline checks for independently addressable local random streams."""

import random

import pytest

from app.services.simulation_random import (
    derive_seed,
    make_rng,
    seed_from_config,
    validate_seed,
)


@pytest.mark.parametrize("seed", [0, 1, 2**63 - 1])
def test_valid_root_seed_boundaries(seed):
    assert validate_seed(seed) == seed
    assert seed_from_config({"seed": seed}) == seed


@pytest.mark.parametrize("seed", [True, False, -1, 2**63, 1.0, "1", None, [], {}])
def test_invalid_root_seeds_are_rejected(seed):
    with pytest.raises(ValueError, match="seed"):
        validate_seed(seed)
    with pytest.raises(ValueError, match="seed"):
        seed_from_config({"seed": seed})
    with pytest.raises(ValueError, match="seed"):
        make_rng(seed, "scheduler:twitter")


def test_only_missing_config_seed_preserves_legacy_mode():
    assert seed_from_config({}) is None


def test_stream_replay_does_not_consume_or_depend_on_global_randomness():
    before = random.getstate()
    first = make_rng(17, "scheduler:twitter", round_num=4, agent_id=9)
    expected = [first.random() for _ in range(12)]
    assert random.getstate() == before
    try:
        for _ in range(100):
            random.random()
        replay = make_rng(17, "scheduler:twitter", round_num=4, agent_id=9)
        assert [replay.random() for _ in range(12)] == expected
    finally:
        random.setstate(before)


def test_namespaces_rounds_agents_and_root_seeds_are_isolated():
    keys = [
        (17, "scheduler:twitter", 4, 9),
        (18, "scheduler:twitter", 4, 9),
        (17, "scheduler:reddit", 4, 9),
        (17, "scheduler:twitter", 5, 9),
        (17, "scheduler:twitter", 4, 10),
        (17, "scheduler:twitter", None, 9),
        (17, "scheduler:twitter", 4, None),
    ]
    seeds = [derive_seed(s, ns, round_num=r, agent_id=a) for s, ns, r, a in keys]
    assert len(set(seeds)) == len(keys)
    untouched = make_rng(17, "scheduler:twitter", round_num=4, agent_id=9)
    noisy = make_rng(17, "followers:twitter", round_num=4, agent_id=9)
    for _ in range(100):
        noisy.random()
    replay = make_rng(17, "scheduler:twitter", round_num=4, agent_id=9)
    assert untouched.getstate() == replay.getstate()


def test_rng_can_be_passed_to_existing_big_five_seams():
    from app.services.big_five import BigFive, sample_population

    assert sample_population(make_rng(8, "profiles", agent_id=2)) == sample_population(
        make_rng(8, "profiles", agent_id=2)
    )
    assert BigFive().jitter(rng=make_rng(8, "jitter", agent_id=2)) == BigFive().jitter(
        rng=make_rng(8, "jitter", agent_id=2)
    )

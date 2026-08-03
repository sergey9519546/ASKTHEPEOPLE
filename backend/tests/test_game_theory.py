"""Acceptance tests for app.services.game_theory.

Every assertion below is anchored to a game whose solution is known from the
literature, not to whatever the implementation happens to produce. If a test
fails, the implementation is wrong.

Reference games used:

* Prisoner's Dilemma -- unique pure equilibrium at mutual defection; the
  cooperative action is strictly dominated.
* Stag Hunt -- coordination game with exactly two pure equilibria.
* Matching Pennies -- zero pure equilibria; unique equilibrium is (1/2, 1/2).
* Battle of the Sexes -- two pure equilibria plus the mixed equilibrium
  (3/5, 2/5).
* Unanimity game -- Shapley value is 1/n each by symmetry.
"""

import itertools
import random

import pytest

from app.services.game_theory import (
    DEFAULT_TOLERANCE,
    GameTheoryError,
    GameTooLargeError,
    NormalFormGame,
    UnsupportedGameShapeError,
    best_response,
    is_in_core,
    iterated_strict_dominance,
    mixed_nash_2x2,
    pure_nash_equilibria,
    shapley_value,
    stable_coalitions,
)

# ---------------------------------------------------------------------------
# Textbook game fixtures
# ---------------------------------------------------------------------------


def prisoners_dilemma() -> NormalFormGame:
    """Standard PD with years-in-prison rendered as negative utility.

    (C, C) = (-1, -1)   (C, D) = (-3,  0)
    (D, C) = ( 0, -3)   (D, D) = (-2, -2)

    Defect strictly dominates Cooperate for both players, so the unique pure
    equilibrium is (D, D) -- the classic result that individually rational play
    lands on the jointly worse outcome.
    """
    return NormalFormGame.from_bimatrix(
        row_payoffs=[[-1.0, -3.0], [0.0, -2.0]],
        col_payoffs=[[-1.0, 0.0], [-3.0, -2.0]],
        players=("suspect_a", "suspect_b"),
        row_actions=["cooperate", "defect"],
        col_actions=["cooperate", "defect"],
    )


def stag_hunt() -> NormalFormGame:
    """Stag Hunt: (Stag, Stag) and (Hare, Hare) are both equilibria.

    (S, S) = (4, 4)   (S, H) = (1, 3)
    (H, S) = (3, 1)   (H, H) = (3, 3)

    Stag is the better joint outcome but is risky; Hare is safe. Exactly two
    pure equilibria, which is the defining feature of a coordination game.
    """
    return NormalFormGame.from_bimatrix(
        row_payoffs=[[4.0, 1.0], [3.0, 3.0]],
        col_payoffs=[[4.0, 3.0], [1.0, 3.0]],
        players=("hunter_1", "hunter_2"),
        row_actions=["stag", "hare"],
        col_actions=["stag", "hare"],
    )


def matching_pennies() -> NormalFormGame:
    """Strictly competitive zero-sum game with NO pure equilibrium.

    (H, H) = ( 1, -1)   (H, T) = (-1,  1)
    (T, H) = (-1,  1)   (T, T) = ( 1, -1)

    The unique Nash equilibrium is fully mixed at (1/2, 1/2) for both players.
    """
    return NormalFormGame.from_bimatrix(
        row_payoffs=[[1.0, -1.0], [-1.0, 1.0]],
        col_payoffs=[[-1.0, 1.0], [1.0, -1.0]],
        players=("matcher", "mismatcher"),
        row_actions=["heads", "tails"],
        col_actions=["heads", "tails"],
    )


def battle_of_the_sexes() -> NormalFormGame:
    """Battle of the Sexes: two pure equilibria plus a known mixed one.

    (O, O) = (3, 2)   (O, F) = (0, 0)
    (F, O) = (0, 0)   (F, F) = (2, 3)

    Both players prefer to be together but disagree on the venue. Pure
    equilibria are (O, O) and (F, F). The mixed equilibrium has each player
    choosing its own preferred venue with probability 3/5.
    """
    return NormalFormGame.from_bimatrix(
        row_payoffs=[[3.0, 0.0], [0.0, 2.0]],
        col_payoffs=[[2.0, 0.0], [0.0, 3.0]],
        players=("alex", "blair"),
        row_actions=["opera", "football"],
        col_actions=["opera", "football"],
    )


# ---------------------------------------------------------------------------
# 1. Prisoner's Dilemma
# ---------------------------------------------------------------------------


def test_prisoners_dilemma_has_unique_pure_nash_at_mutual_defection():
    game = prisoners_dilemma()

    assert pure_nash_equilibria(game) == [("defect", "defect")]


def test_prisoners_dilemma_cooperate_is_strictly_dominated_for_both_players():
    game = prisoners_dilemma()
    reduced = iterated_strict_dominance(game)

    assert reduced.actions["suspect_a"] == ("defect",)
    assert reduced.actions["suspect_b"] == ("defect",)


def test_prisoners_dilemma_iterated_dominance_collapses_to_the_single_profile():
    game = prisoners_dilemma()
    reduced = iterated_strict_dominance(game)

    assert reduced.profile_count() == 1
    assert list(reduced.profiles()) == [("defect", "defect")]
    # The survivor of iterated strict dominance is exactly the pure equilibrium.
    assert list(reduced.profiles()) == pure_nash_equilibria(game)


def test_prisoners_dilemma_reduced_game_preserves_payoffs():
    reduced = iterated_strict_dominance(prisoners_dilemma())

    assert reduced.payoff_vector(("defect", "defect")) == (-2.0, -2.0)


def test_prisoners_dilemma_defect_is_the_best_response_to_either_opponent_action():
    game = prisoners_dilemma()

    assert best_response(game, "suspect_a", {"suspect_b": "cooperate"}) == ["defect"]
    assert best_response(game, "suspect_a", {"suspect_b": "defect"}) == ["defect"]


def test_prisoners_dilemma_has_no_interior_mixed_equilibrium():
    # With a strictly dominant action there is nothing to be indifferent about,
    # so the closed form must report no interior mixed equilibrium.
    assert mixed_nash_2x2(prisoners_dilemma()) is None


# ---------------------------------------------------------------------------
# 2. Stag Hunt
# ---------------------------------------------------------------------------


def test_stag_hunt_has_exactly_two_pure_nash_equilibria():
    equilibria = pure_nash_equilibria(stag_hunt())

    assert len(equilibria) == 2
    assert set(equilibria) == {("stag", "stag"), ("hare", "hare")}


def test_stag_hunt_has_no_strictly_dominated_actions():
    game = stag_hunt()
    reduced = iterated_strict_dominance(game)

    # Neither action is dominated: stag is better against stag, hare against hare.
    assert reduced.actions["hunter_1"] == ("stag", "hare")
    assert reduced.actions["hunter_2"] == ("stag", "hare")


def test_stag_hunt_best_responses_mirror_the_opponent():
    game = stag_hunt()

    assert best_response(game, "hunter_1", {"hunter_2": "stag"}) == ["stag"]
    assert best_response(game, "hunter_1", {"hunter_2": "hare"}) == ["hare"]


def test_stag_hunt_mixed_equilibrium_matches_the_indifference_condition():
    mixed = mixed_nash_2x2(stag_hunt())

    # Row is indifferent when 4q + 1(1-q) == 3q + 3(1-q), i.e. q = 2/3.
    assert mixed is not None
    assert mixed["hunter_1"]["stag"] == pytest.approx(2.0 / 3.0)
    assert mixed["hunter_2"]["stag"] == pytest.approx(2.0 / 3.0)


# ---------------------------------------------------------------------------
# 3. Matching Pennies
# ---------------------------------------------------------------------------


def test_matching_pennies_has_zero_pure_nash_equilibria():
    assert pure_nash_equilibria(matching_pennies()) == []


def test_matching_pennies_mixed_equilibrium_is_one_half_for_both_players():
    mixed = mixed_nash_2x2(matching_pennies())

    assert mixed is not None
    assert mixed["matcher"]["heads"] == pytest.approx(0.5)
    assert mixed["matcher"]["tails"] == pytest.approx(0.5)
    assert mixed["mismatcher"]["heads"] == pytest.approx(0.5)
    assert mixed["mismatcher"]["tails"] == pytest.approx(0.5)


def test_matching_pennies_mixed_probabilities_sum_to_one():
    mixed = mixed_nash_2x2(matching_pennies())

    assert mixed is not None
    for distribution in mixed.values():
        assert sum(distribution.values()) == pytest.approx(1.0)


def test_matching_pennies_has_no_strictly_dominated_actions():
    game = matching_pennies()
    reduced = iterated_strict_dominance(game)

    assert reduced.action_counts == (2, 2)


def test_matching_pennies_is_zero_sum_at_every_profile():
    game = matching_pennies()

    for profile in game.profiles():
        assert sum(game.payoff_vector(profile)) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 4. Battle of the Sexes
# ---------------------------------------------------------------------------


def test_battle_of_the_sexes_has_two_pure_nash_equilibria():
    equilibria = pure_nash_equilibria(battle_of_the_sexes())

    assert len(equilibria) == 2
    assert set(equilibria) == {("opera", "opera"), ("football", "football")}


def test_battle_of_the_sexes_mixed_equilibrium_is_three_fifths_two_fifths():
    mixed = mixed_nash_2x2(battle_of_the_sexes())

    assert mixed is not None
    # Each player plays its own preferred venue with probability 3/5.
    assert mixed["alex"]["opera"] == pytest.approx(0.6)
    assert mixed["alex"]["football"] == pytest.approx(0.4)
    assert mixed["blair"]["football"] == pytest.approx(0.6)
    assert mixed["blair"]["opera"] == pytest.approx(0.4)


def test_battle_of_the_sexes_mixed_equilibrium_makes_each_player_indifferent():
    game = battle_of_the_sexes()
    mixed = mixed_nash_2x2(game)
    assert mixed is not None

    q_opera = mixed["blair"]["opera"]
    p_opera = mixed["alex"]["opera"]

    alex_opera = q_opera * 3.0 + (1.0 - q_opera) * 0.0
    alex_football = q_opera * 0.0 + (1.0 - q_opera) * 2.0
    assert alex_opera == pytest.approx(alex_football)

    blair_opera = p_opera * 2.0 + (1.0 - p_opera) * 0.0
    blair_football = p_opera * 0.0 + (1.0 - p_opera) * 3.0
    assert blair_opera == pytest.approx(blair_football)


# ---------------------------------------------------------------------------
# 5. Shapley value
# ---------------------------------------------------------------------------


def test_shapley_value_of_three_player_unanimity_game_is_one_third_each():
    players = ("a", "b", "c")

    def unanimity(coalition):
        # Value 1 only if everybody joins; nothing otherwise.
        return 1.0 if coalition == frozenset(players) else 0.0

    shares = shapley_value(players, unanimity)

    assert shares["a"] == pytest.approx(1.0 / 3.0)
    assert shares["b"] == pytest.approx(1.0 / 3.0)
    assert shares["c"] == pytest.approx(1.0 / 3.0)


def test_shapley_value_is_efficient_on_a_non_symmetric_game():
    # Deliberately asymmetric: pairwise synergies all differ.
    values = {
        frozenset(): 0.0,
        frozenset({"incumbent"}): 10.0,
        frozenset({"challenger"}): 4.0,
        frozenset({"regulator"}): 0.0,
        frozenset({"incumbent", "challenger"}): 90.0,
        frozenset({"incumbent", "regulator"}): 80.0,
        frozenset({"challenger", "regulator"}): 70.0,
        frozenset({"incumbent", "challenger", "regulator"}): 120.0,
    }
    players = ("incumbent", "challenger", "regulator")

    shares = shapley_value(players, lambda coalition: values[frozenset(coalition)])

    # Efficiency axiom: shares exhaust the grand-coalition value.
    assert sum(shares.values()) == pytest.approx(120.0)
    # Asymmetric game must produce asymmetric shares.
    assert len({round(v, 9) for v in shares.values()}) == 3
    # The incumbent is worth strictly more than the regulator here.
    assert shares["incumbent"] > shares["regulator"]


def test_shapley_value_matches_brute_force_permutation_average():
    values = {
        frozenset(): 0.0,
        frozenset({1}): 2.0,
        frozenset({2}): 5.0,
        frozenset({3}): 1.0,
        frozenset({1, 2}): 12.0,
        frozenset({1, 3}): 7.0,
        frozenset({2, 3}): 9.0,
        frozenset({1, 2, 3}): 20.0,
    }
    players = (1, 2, 3)

    def characteristic(coalition):
        return values[frozenset(coalition)]

    # Independent reference implementation: average marginal contribution over
    # all orderings, computed the slow, literal way.
    totals = {p: 0.0 for p in players}
    orderings = list(itertools.permutations(players))
    for ordering in orderings:
        predecessors: set = set()
        for player in ordering:
            before = frozenset(predecessors)
            totals[player] += characteristic(before | {player}) - characteristic(before)
            predecessors.add(player)
    expected = {p: totals[p] / len(orderings) for p in players}

    shares = shapley_value(players, characteristic)

    for player in players:
        assert shares[player] == pytest.approx(expected[player])


def test_shapley_value_gives_a_null_player_zero():
    players = ("worker", "worker_2", "bystander")

    def characteristic(coalition):
        # The bystander adds nothing anywhere.
        productive = coalition - {"bystander"}
        return float(len(productive))

    shares = shapley_value(players, characteristic)

    assert shares["bystander"] == pytest.approx(0.0)
    assert sum(shares.values()) == pytest.approx(2.0)


def test_shapley_value_rejects_nonzero_empty_coalition_value():
    with pytest.raises(GameTheoryError, match="empty coalition"):
        shapley_value(("a", "b"), lambda coalition: 5.0)


# ---------------------------------------------------------------------------
# 6. best_response returns ALL ties
# ---------------------------------------------------------------------------


def test_best_response_returns_every_tied_maximiser():
    # Row is exactly indifferent between "hold" and "match" against "low",
    # and both beat "exit". All tied maximisers must come back.
    game = NormalFormGame.from_bimatrix(
        row_payoffs=[[5.0, 1.0], [5.0, 0.0], [2.0, 9.0]],
        col_payoffs=[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
        players=("us", "rival"),
        row_actions=["hold", "match", "exit"],
        col_actions=["low", "high"],
    )

    responses = best_response(game, "us", {"rival": "low"})

    assert responses == ["hold", "match"]


def test_best_response_returns_all_actions_when_player_is_wholly_indifferent():
    game = NormalFormGame.from_bimatrix(
        row_payoffs=[[3.0, 3.0], [3.0, 3.0]],
        col_payoffs=[[1.0, 2.0], [2.0, 1.0]],
        players=("flat", "other"),
        row_actions=["x", "y"],
        col_actions=["p", "q"],
    )

    assert best_response(game, "flat", {"other": "p"}) == ["x", "y"]
    assert best_response(game, "flat", {"other": "q"}) == ["x", "y"]


def test_best_response_accepts_sequence_form_for_multiple_opponents():
    players = ("a", "b", "c")
    actions = {p: ("up", "down") for p in players}

    def payoffs(profile):
        # Player "a" is rewarded for matching the majority of b and c.
        majority = "up" if [profile[1], profile[2]].count("up") >= 2 else "down"
        return (1.0 if profile[0] == majority else 0.0, 0.0, 0.0)

    game = NormalFormGame(players=players, actions=actions, payoffs=payoffs)

    assert best_response(game, "a", ("up", "up")) == ["up"]
    assert best_response(game, "a", {"b": "down", "c": "down"}) == ["down"]
    # Split opponents: no majority "up", so "down" wins under this payoff rule.
    assert best_response(game, "a", ("up", "down")) == ["down"]


def test_best_response_honours_tolerance_for_near_ties():
    game = NormalFormGame.from_bimatrix(
        row_payoffs=[[1.0, 0.0], [1.0 + DEFAULT_TOLERANCE / 10.0, 0.0]],
        col_payoffs=[[0.0, 0.0], [0.0, 0.0]],
        players=("us", "them"),
        row_actions=["a", "b"],
        col_actions=["l", "r"],
    )

    # A difference below tolerance counts as a tie, not a strict preference.
    assert best_response(game, "us", {"them": "l"}) == ["a", "b"]


def test_best_response_rejects_incomplete_opponent_assignment():
    players = ("a", "b", "c")
    game = NormalFormGame(
        players=players,
        actions={p: ("x", "y") for p in players},
        payoffs=lambda profile: (0.0, 0.0, 0.0),
    )

    with pytest.raises(GameTheoryError, match="missing an action"):
        best_response(game, "a", {"b": "x"})


# ---------------------------------------------------------------------------
# 7. Size guards raise clearly instead of hanging
# ---------------------------------------------------------------------------


def test_pure_nash_guard_raises_instead_of_enumerating():
    # 12 players x 3 actions = 531441 profiles. Must refuse, not grind.
    players = tuple(f"actor_{i}" for i in range(12))
    game = NormalFormGame(
        players=players,
        actions={p: ("low", "mid", "high") for p in players},
        payoffs=lambda profile: tuple(0.0 for _ in profile),
    )

    with pytest.raises(GameTooLargeError) as excinfo:
        pure_nash_equilibria(game)

    message = str(excinfo.value)
    assert "531441" in message
    assert "max_profiles" in message


def test_profiles_guard_reports_the_actual_and_allowed_counts():
    players = ("a", "b", "c")
    game = NormalFormGame(
        players=players,
        actions={p: (0, 1, 2, 3) for p in players},
        payoffs=lambda profile: (0.0, 0.0, 0.0),
    )

    with pytest.raises(GameTooLargeError, match="64 pure action profiles"):
        list(game.profiles(max_profiles=10))


def test_iterated_strict_dominance_guard_raises_instead_of_hanging():
    players = tuple(f"actor_{i}" for i in range(14))
    game = NormalFormGame(
        players=players,
        actions={p: ("in", "out") for p in players},
        payoffs=lambda profile: tuple(0.0 for _ in profile),
    )

    with pytest.raises(GameTooLargeError, match="max_profiles"):
        iterated_strict_dominance(game, max_profiles=1000)


def test_shapley_value_guard_raises_on_too_many_players():
    players = tuple(range(40))

    with pytest.raises(GameTooLargeError) as excinfo:
        shapley_value(players, lambda coalition: float(len(coalition)))

    message = str(excinfo.value)
    assert "40 players" in message
    assert "max_players" in message


def test_stable_coalitions_guard_raises_on_too_many_players():
    players = tuple(range(25))

    with pytest.raises(GameTooLargeError, match="max_players"):
        stable_coalitions(players, lambda coalition: float(len(coalition)))


def test_mixed_nash_2x2_refuses_games_outside_its_special_case():
    three_by_three = NormalFormGame.from_bimatrix(
        row_payoffs=[[0.0, -1.0, 1.0], [1.0, 0.0, -1.0], [-1.0, 1.0, 0.0]],
        col_payoffs=[[0.0, 1.0, -1.0], [-1.0, 0.0, 1.0], [1.0, -1.0, 0.0]],
        row_actions=["rock", "paper", "scissors"],
        col_actions=["rock", "paper", "scissors"],
    )

    with pytest.raises(UnsupportedGameShapeError, match="2 actions per player"):
        mixed_nash_2x2(three_by_three)

    three_players = NormalFormGame(
        players=("a", "b", "c"),
        actions={"a": (0, 1), "b": (0, 1), "c": (0, 1)},
        payoffs=lambda profile: (0.0, 0.0, 0.0),
    )
    with pytest.raises(UnsupportedGameShapeError, match="2-player games only"):
        mixed_nash_2x2(three_players)


# ---------------------------------------------------------------------------
# Coalition stability and the core
# ---------------------------------------------------------------------------


def test_stable_coalitions_includes_grand_coalition_for_a_convex_game():
    # Superadditive with increasing returns: the grand coalition's Shapley
    # split is core-stable, so it must appear.
    values = {
        frozenset(): 0.0,
        frozenset({"a"}): 1.0,
        frozenset({"b"}): 1.0,
        frozenset({"c"}): 1.0,
        frozenset({"a", "b"}): 4.0,
        frozenset({"a", "c"}): 4.0,
        frozenset({"b", "c"}): 4.0,
        frozenset({"a", "b", "c"}): 9.0,
    }
    players = ("a", "b", "c")

    stable = stable_coalitions(players, lambda coalition: values[frozenset(coalition)])
    members = [entry.members for entry in stable]

    assert frozenset(players) in members
    # Singletons are trivially stable by the documented definition.
    assert frozenset({"a"}) in members
    for entry in stable:
        assert sum(entry.allocation.values()) == pytest.approx(entry.value)


def test_stable_coalitions_excludes_grand_coalition_of_simple_majority_game():
    # 3-player simple majority: any two players get 1, the trio gets 1.
    # Its core is empty, so the grand coalition cannot be stable.
    players = ("a", "b", "c")

    def majority(coalition):
        return 1.0 if len(coalition) >= 2 else 0.0

    stable = stable_coalitions(players, majority)
    members = [entry.members for entry in stable]

    assert frozenset(players) not in members
    # The two-player coalitions still split 1 evenly against zero-value singles.
    assert frozenset({"a", "b"}) in members


def test_is_in_core_agrees_with_hand_computed_allocations():
    players = ("a", "b", "c")

    def values(coalition):
        return 1.0 if len(coalition) >= 2 else 0.0

    # Empty core: every efficient split leaves some pair able to do better.
    assert is_in_core(players, values, {"a": 1 / 3, "b": 1 / 3, "c": 1 / 3}) is False
    assert is_in_core(players, values, {"a": 0.5, "b": 0.5, "c": 0.0}) is False

    def additive(coalition):
        return float(len(coalition))

    # Additive game: the equal-marginal split is in the core.
    assert is_in_core(players, additive, {"a": 1.0, "b": 1.0, "c": 1.0}) is True
    # Inefficient allocations are outside the core by definition.
    assert is_in_core(players, additive, {"a": 1.0, "b": 1.0, "c": 0.5}) is False
    # Efficient but not coalitionally rational.
    assert is_in_core(players, additive, {"a": 3.0, "b": 0.0, "c": 0.0}) is False


def test_shapley_allocation_of_a_convex_game_is_in_its_core():
    values = {
        frozenset(): 0.0,
        frozenset({"a"}): 0.0,
        frozenset({"b"}): 0.0,
        frozenset({"c"}): 0.0,
        frozenset({"a", "b"}): 3.0,
        frozenset({"a", "c"}): 3.0,
        frozenset({"b", "c"}): 3.0,
        frozenset({"a", "b", "c"}): 9.0,
    }
    players = ("a", "b", "c")

    def characteristic(coalition):
        return values[frozenset(coalition)]

    allocation = shapley_value(players, characteristic)

    assert is_in_core(players, characteristic, allocation) is True


# ---------------------------------------------------------------------------
# Competitive-scenario smoke tests (the module's stated purpose)
# ---------------------------------------------------------------------------


def test_undercutting_rival_is_predicted_when_price_cutting_strictly_dominates():
    # Both firms gain by cutting price regardless of the other's choice: a
    # price war is the unique pure equilibrium. Structurally a PD.
    game = NormalFormGame.from_bimatrix(
        row_payoffs=[[10.0, 2.0], [14.0, 5.0]],
        col_payoffs=[[10.0, 14.0], [2.0, 5.0]],
        players=("us", "rival"),
        row_actions=["hold_price", "undercut"],
        col_actions=["hold_price", "undercut"],
    )

    assert pure_nash_equilibria(game) == [("undercut", "undercut")]
    reduced = iterated_strict_dominance(game)
    assert reduced.actions["rival"] == ("undercut",)


def test_three_player_entry_game_pure_equilibria_are_found_exhaustively():
    # Two of three entrants can profit; a third makes the market unprofitable.
    players = ("firm_a", "firm_b", "firm_c")
    actions = {p: ("enter", "stay_out") for p in players}

    def payoffs(profile):
        entrants = profile.count("enter")
        if entrants == 0:
            per_entrant = 0.0
        elif entrants <= 2:
            per_entrant = 6.0 / entrants
        else:
            per_entrant = -1.0
        return tuple(per_entrant if action == "enter" else 0.0 for action in profile)

    game = NormalFormGame(players=players, actions=actions, payoffs=payoffs)
    equilibria = pure_nash_equilibria(game)

    # Exactly the three profiles with two entrants: a single entrant would be
    # undercut by a profitable third-party entry, and three entrants all lose.
    assert set(equilibria) == {
        ("enter", "enter", "stay_out"),
        ("enter", "stay_out", "enter"),
        ("stay_out", "enter", "enter"),
    }


def test_coalition_attribution_and_stability_on_an_asymmetric_alliance():
    players = ("major", "minor", "swing")

    def values(coalition):
        members = frozenset(coalition)
        if not members:
            return 0.0
        table = {
            frozenset({"major"}): 20.0,
            frozenset({"minor"}): 5.0,
            frozenset({"swing"}): 5.0,
            frozenset({"major", "minor"}): 40.0,
            frozenset({"major", "swing"}): 40.0,
            frozenset({"minor", "swing"}): 12.0,
            frozenset({"major", "minor", "swing"}): 60.0,
        }
        return table[members]

    shares = shapley_value(players, values)

    assert sum(shares.values()) == pytest.approx(60.0)
    assert shares["major"] > shares["minor"]
    assert shares["minor"] == pytest.approx(shares["swing"])

    stable = stable_coalitions(players, values)
    for entry in stable:
        assert sum(entry.allocation.values()) == pytest.approx(entry.value)


# ---------------------------------------------------------------------------
# Property-based cross-validation against independent definitions
# ---------------------------------------------------------------------------


def _is_degenerate_2x2(a, b):
    """True if either player is exactly indifferent against a pure opponent action.

    The textbook structural law relating pure- and mixed-equilibrium counts is
    stated for non-degenerate games only, so degenerate draws are excluded.
    """
    return (
        a[0][0] == a[1][0]
        or a[0][1] == a[1][1]
        or b[0][0] == b[0][1]
        or b[1][0] == b[1][1]
    )


def test_mixed_nash_2x2_output_always_satisfies_both_indifference_conditions():
    """Verify the closed form against the *definition*, not against itself.

    Whenever an interior mixed equilibrium is reported, each player must be
    exactly indifferent between its two pure actions given the opponent's mix.
    This catches transposed indices, which a symmetric game like Matching
    Pennies would silently hide.
    """
    rng = random.Random(7)
    verified = 0

    for _ in range(1500):
        a = [[rng.randint(-6, 6) for _ in range(2)] for _ in range(2)]
        b = [[rng.randint(-6, 6) for _ in range(2)] for _ in range(2)]
        game = NormalFormGame.from_bimatrix(
            a, b, row_actions=[0, 1], col_actions=[0, 1]
        )

        result = mixed_nash_2x2(game)
        if result is None:
            continue

        p = result["row"][0]
        q = result["col"][0]
        assert 0.0 < p < 1.0
        assert 0.0 < q < 1.0

        row_plays_0 = q * a[0][0] + (1 - q) * a[0][1]
        row_plays_1 = q * a[1][0] + (1 - q) * a[1][1]
        col_plays_0 = p * b[0][0] + (1 - p) * b[1][0]
        col_plays_1 = p * b[0][1] + (1 - p) * b[1][1]

        assert row_plays_0 == pytest.approx(row_plays_1), (a, b, p, q)
        assert col_plays_0 == pytest.approx(col_plays_1), (a, b, p, q)
        verified += 1

    assert verified > 100, f"too few interior equilibria exercised ({verified})"


def test_nondegenerate_2x2_games_obey_the_pure_versus_mixed_structural_law():
    """In a non-degenerate 2x2 game, an interior mixed equilibrium exists
    exactly when the number of pure equilibria is 0 or 2.

    A game with a single pure equilibrium (e.g. one with a dominant action,
    like Prisoner's Dilemma) has no interior mixed equilibrium; a game with
    none (Matching Pennies) or two (Stag Hunt, Battle of the Sexes) does.
    """
    rng = random.Random(3)
    tested = 0

    while tested < 600:
        a = [[rng.randint(-40, 40) for _ in range(2)] for _ in range(2)]
        b = [[rng.randint(-40, 40) for _ in range(2)] for _ in range(2)]
        if _is_degenerate_2x2(a, b):
            continue
        tested += 1

        game = NormalFormGame.from_bimatrix(
            a, b, row_actions=[0, 1], col_actions=[0, 1]
        )
        n_pure = len(pure_nash_equilibria(game))
        has_mixed = mixed_nash_2x2(game) is not None

        assert has_mixed == (n_pure in (0, 2)), (a, b, n_pure, has_mixed)


def test_iterated_strict_dominance_is_order_independent():
    """The order-independence theorem asserted in the docstring, checked.

    Eliminating strictly dominated actions in any order must yield the same
    surviving game, so shuffling the player order must not change the result.
    """
    rng = random.Random(19)

    for _ in range(200):
        a = [[rng.randint(-5, 5) for _ in range(3)] for _ in range(3)]
        b = [[rng.randint(-5, 5) for _ in range(3)] for _ in range(3)]

        forward = NormalFormGame.from_bimatrix(
            a, b, players=("p", "q"), row_actions=[0, 1, 2], col_actions=[0, 1, 2]
        )
        # Same game, players declared in the opposite order.
        transposed = NormalFormGame(
            players=("q", "p"),
            actions={"q": (0, 1, 2), "p": (0, 1, 2)},
            payoffs={
                (cj, ri): (b[ri][cj], a[ri][cj])
                for ri in range(3)
                for cj in range(3)
            },
        )

        reduced_forward = iterated_strict_dominance(forward)
        reduced_reversed = iterated_strict_dominance(transposed)

        assert set(reduced_forward.actions["p"]) == set(reduced_reversed.actions["p"])
        assert set(reduced_forward.actions["q"]) == set(reduced_reversed.actions["q"])


def test_iterated_strict_dominance_never_discards_a_pure_equilibrium():
    """Removing strictly dominated actions cannot destroy a Nash equilibrium.

    This is the soundness property that makes the reduction safe to apply
    before equilibrium search.
    """
    rng = random.Random(23)

    for _ in range(200):
        a = [[rng.randint(-5, 5) for _ in range(3)] for _ in range(3)]
        b = [[rng.randint(-5, 5) for _ in range(3)] for _ in range(3)]
        game = NormalFormGame.from_bimatrix(
            a, b, row_actions=[0, 1, 2], col_actions=[0, 1, 2]
        )

        original = set(pure_nash_equilibria(game))
        reduced = iterated_strict_dominance(game)
        survivors = set(pure_nash_equilibria(reduced))

        assert original == survivors, (a, b, original, survivors)


def test_shapley_efficiency_holds_on_random_games():
    """Efficiency axiom on arbitrary characteristic functions, not just tidy ones."""
    rng = random.Random(31)
    players = ("a", "b", "c", "d")

    for _ in range(200):
        table = {
            frozenset(subset): float(rng.randint(-20, 40))
            for size in range(1, len(players) + 1)
            for subset in itertools.combinations(players, size)
        }
        table[frozenset()] = 0.0

        shares = shapley_value(players, lambda coalition: table[frozenset(coalition)])

        assert sum(shares.values()) == pytest.approx(table[frozenset(players)])


# ---------------------------------------------------------------------------
# Construction-time validation
# ---------------------------------------------------------------------------


def test_game_construction_rejects_malformed_input():
    with pytest.raises(GameTheoryError, match="at least one player"):
        NormalFormGame(players=(), actions={}, payoffs={})

    with pytest.raises(GameTheoryError, match="distinct"):
        NormalFormGame(
            players=("a", "a"), actions={"a": (0, 1)}, payoffs=lambda profile: (0.0, 0.0)
        )

    with pytest.raises(GameTheoryError, match="No action list"):
        NormalFormGame(
            players=("a", "b"), actions={"a": (0, 1)}, payoffs=lambda profile: (0.0, 0.0)
        )

    with pytest.raises(GameTheoryError, match="empty action list"):
        NormalFormGame(
            players=("a",), actions={"a": ()}, payoffs=lambda profile: (0.0,)
        )


def test_payoff_lookup_errors_are_explicit():
    game = NormalFormGame(
        players=("a", "b"),
        actions={"a": (0, 1), "b": (0, 1)},
        payoffs={(0, 0): (1.0, 1.0)},
    )

    with pytest.raises(GameTheoryError, match="No payoff defined"):
        game.payoff_vector((1, 1))

    with pytest.raises(GameTheoryError, match="expected 2"):
        game.payoff_vector((0,))

    bad = NormalFormGame(
        players=("a", "b"),
        actions={"a": (0,), "b": (0,)},
        payoffs={(0, 0): (1.0,)},
    )
    with pytest.raises(GameTheoryError, match="expected 2"):
        bad.payoff_vector((0, 0))


def test_module_declares_only_standard_library_imports():
    """The isolation claim in the module docstring must actually hold.

    Parsed from source rather than trusted from prose: no ``app.*``, no Flask,
    no third-party numeric or network packages anywhere in the module.
    """
    import ast
    import pathlib
    import sys

    module = sys.modules["app.services.game_theory"]
    source_path = pathlib.Path(module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # a relative import would pull in the app package
                imported_roots.add(f".{node.module or ''}")
            elif node.module:
                imported_roots.add(node.module.split(".")[0])

    allowed = {"__future__", "dataclasses", "itertools", "math", "typing"}
    assert imported_roots <= allowed, (
        f"game_theory.py imports outside the standard-library allowlist: "
        f"{sorted(imported_roots - allowed)}"
    )
    for forbidden in ("app", "flask", "numpy", "scipy", "nashpy", "requests", "networkx"):
        assert forbidden not in imported_roots


def test_module_docstring_states_the_scope_limitation():
    import sys

    # The honest-scope statement is part of the contract; normalise whitespace
    # so that reflowing the paragraph does not break the check.
    doc = " ".join((sys.modules["app.services.game_theory"].__doc__ or "").split())

    assert "not a general Nash solver" in doc
    assert "PPAD-complete" in doc

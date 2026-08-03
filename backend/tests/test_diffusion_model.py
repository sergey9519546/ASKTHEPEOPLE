"""Acceptance tests for app.services.diffusion_model.

These are written as genuine acceptance criteria: each test states a property
that the Rogers / Bass / linear-threshold implementation must satisfy, and
checks it against an independently computed expectation (analytic formulas,
hand-computed cascades) rather than against whatever the code happens to emit.
"""

from __future__ import annotations

import math

import pytest

from app.services.diffusion_model import (
    CATEGORY_ORDER,
    CATEGORY_SHARES,
    CATEGORY_THRESHOLDS,
    DEFAULT_THRESHOLD,
    P_EMPIRICAL_RANGE,
    Q_EMPIRICAL_RANGE,
    TYPICAL_P,
    TYPICAL_Q,
    AdopterCategory,
    adjacency_from_edges,
    bass_adoption_curve,
    bass_incremental_adopters,
    bass_peak_time,
    category_counts,
    classify_population,
    innovativeness_score,
    propagate,
    simulate_contagion,
    thresholds_from_categories,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_persona(identifier, openness, **extra):
    """A persona in the plain-dict shape the module promises to accept."""
    payload = {
        "persona_id": identifier,
        "big_five": {
            "openness": openness,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        },
    }
    payload.update(extra)
    return payload


def spread_population(count, seed_offset=0.0):
    """``count`` personas with distinct, evenly spread Openness values."""
    if count == 1:
        return [make_persona("p0", 0.5)]
    return [
        make_persona(f"p{index}", (index / (count - 1)) * 0.999 + seed_offset)
        for index in range(count)
    ]


def complete_graph(size):
    nodes = list(range(size))
    return {node: {other for other in nodes if other != node} for node in nodes}


# ---------------------------------------------------------------------------
# Module invariants
# ---------------------------------------------------------------------------


def test_canonical_shares_sum_to_one_and_match_rogers():
    assert math.isclose(sum(CATEGORY_SHARES.values()), 1.0, abs_tol=1e-12)
    assert CATEGORY_SHARES[AdopterCategory.INNOVATOR] == pytest.approx(0.025)
    assert CATEGORY_SHARES[AdopterCategory.EARLY_ADOPTER] == pytest.approx(0.135)
    assert CATEGORY_SHARES[AdopterCategory.EARLY_MAJORITY] == pytest.approx(0.34)
    assert CATEGORY_SHARES[AdopterCategory.LATE_MAJORITY] == pytest.approx(0.34)
    assert CATEGORY_SHARES[AdopterCategory.LAGGARD] == pytest.approx(0.16)


def test_category_order_is_earliest_to_latest():
    assert [category.value for category in CATEGORY_ORDER] == [0, 1, 2, 3, 4]


def test_documented_typical_parameters_sit_inside_documented_ranges():
    assert P_EMPIRICAL_RANGE[0] <= TYPICAL_P <= P_EMPIRICAL_RANGE[1]
    assert Q_EMPIRICAL_RANGE[0] <= TYPICAL_Q <= Q_EMPIRICAL_RANGE[1]
    # Diffusion is imitation-dominated: q is an order of magnitude above p.
    assert TYPICAL_Q > 10 * TYPICAL_P


# ---------------------------------------------------------------------------
# AC1: category shares reproduce the canonical percentages
# ---------------------------------------------------------------------------


def test_ac1_thousand_personas_match_canonical_shares_within_one():
    personas = spread_population(1000)
    counts = category_counts(classify_population(personas))

    assert sum(counts.values()) == 1000
    for category, share in CATEGORY_SHARES.items():
        expected = share * 1000
        assert abs(counts[category] - expected) <= 1, (
            f"{category.name}: got {counts[category]}, expected ~{expected}"
        )

    # At n=1000 the canonical shares land on exact integers, so demand exactness.
    assert counts == {
        AdopterCategory.INNOVATOR: 25,
        AdopterCategory.EARLY_ADOPTER: 135,
        AdopterCategory.EARLY_MAJORITY: 340,
        AdopterCategory.LATE_MAJORITY: 340,
        AdopterCategory.LAGGARD: 160,
    }


@pytest.mark.parametrize("size", [7, 33, 100, 250, 999, 1000, 4321])
def test_ac1_shares_hold_within_one_across_population_sizes(size):
    counts = category_counts(classify_population(spread_population(size)))
    assert sum(counts.values()) == size
    for category, share in CATEGORY_SHARES.items():
        assert abs(counts[category] - share * size) <= 1, (
            f"n={size} {category.name}: {counts[category]} vs {share * size}"
        )


def test_ac1_classification_is_not_independent_sampling():
    """Rank-and-slice must be deterministic and exactly reproducible."""
    personas = spread_population(400)
    first = classify_population(personas)
    second = classify_population(personas)
    assert first == second


def test_ac1_accepts_mapping_input_and_custom_key():
    personas = {f"id{index}": {"score": index} for index in range(200)}
    assignments = classify_population(personas, key=lambda persona: persona["score"])
    counts = category_counts(assignments)
    assert sum(counts.values()) == 200
    # Highest score must be an innovator; lowest must be a laggard.
    assert assignments["id199"] is AdopterCategory.INNOVATOR
    assert assignments["id0"] is AdopterCategory.LAGGARD


def test_ac1_rejects_duplicate_identifiers():
    personas = [make_persona("dup", 0.1), make_persona("dup", 0.9)]
    with pytest.raises(ValueError):
        classify_population(personas)


# ---------------------------------------------------------------------------
# AC2: Bass curve properties
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "p,q",
    [
        (TYPICAL_P, TYPICAL_Q),
        (0.0002, 0.30),
        (0.03, 0.50),
        (0.01, 0.40),
        (0.02, 0.35),
    ],
)
def test_ac2_curve_is_monotonically_non_decreasing(p, q):
    curve = bass_adoption_curve(p, q, m=10_000.0, periods=60)
    for earlier, later in zip(curve, curve[1:]):
        assert later >= earlier, f"curve decreased: {earlier} -> {later}"


@pytest.mark.parametrize(
    "p,q",
    [(TYPICAL_P, TYPICAL_Q), (0.0002, 0.30), (0.03, 0.50), (0.01, 0.40)],
)
def test_ac2_curve_never_exceeds_market_potential(p, q):
    market = 10_000.0
    curve = bass_adoption_curve(p, q, m=market, periods=400)
    assert all(0.0 <= value <= market for value in curve)
    assert max(curve) <= market


@pytest.mark.parametrize("p,q", [(TYPICAL_P, TYPICAL_Q), (0.01, 0.40)])
def test_ac2_curve_approaches_market_potential_asymptotically(p, q):
    market = 10_000.0
    curve = bass_adoption_curve(p, q, m=market, periods=400)
    # Converges to m ...
    assert curve[-1] == pytest.approx(market, rel=1e-9)
    # ... but is still strictly below m while the process is under way.
    early = bass_adoption_curve(p, q, m=market, periods=10)
    assert all(value < market for value in early)


@pytest.mark.parametrize(
    "p,q",
    [
        (TYPICAL_P, TYPICAL_Q),  # t* ~= 6.19
        (0.03, 0.50),  # t* ~= 5.30
        (0.01, 0.40),  # t* ~= 8.99
        (0.0002, 0.30),  # t* ~= 24.4
        (0.005, 0.45),  # t* ~= 9.89
    ],
)
def test_ac2_peak_adoption_timing_matches_analytic_t_star(p, q):
    analytic = bass_peak_time(p, q)
    assert analytic is not None

    periods = 200
    increments = bass_incremental_adopters(p, q, m=10_000.0, periods=periods)
    peak_index = max(range(periods), key=lambda index: increments[index])

    # increments[i] covers the interval (i, i+1], so its midpoint is i + 0.5.
    observed = peak_index + 0.5
    assert abs(observed - analytic) <= 1.0, (
        f"p={p} q={q}: observed peak at t={observed}, analytic t*={analytic}"
    )


def test_ac2_analytic_peak_time_formula_is_exact_for_known_values():
    # ln(0.38 / 0.03) / (0.03 + 0.38)
    assert bass_peak_time(0.03, 0.38) == pytest.approx(math.log(0.38 / 0.03) / 0.41)
    # Reference value computed independently at 40-digit precision with
    # decimal.Decimal: ln(0.38/0.03)/0.41 = 6.19261919770311238544...
    assert bass_peak_time(0.03, 0.38) == pytest.approx(6.1926191977, abs=1e-9)


def test_ac2_incremental_adopters_sum_to_cumulative():
    cumulative = bass_adoption_curve(TYPICAL_P, TYPICAL_Q, m=5_000.0, periods=50)
    increments = bass_incremental_adopters(TYPICAL_P, TYPICAL_Q, m=5_000.0, periods=50)
    assert sum(increments) == pytest.approx(cumulative[-1])
    assert all(value >= 0.0 for value in increments)


def test_ac2_higher_q_diffuses_faster():
    slow = bass_adoption_curve(TYPICAL_P, 0.30, m=1_000.0, periods=20)
    fast = bass_adoption_curve(TYPICAL_P, 0.50, m=1_000.0, periods=20)
    assert fast[9] > slow[9]
    assert bass_peak_time(TYPICAL_P, 0.50) < bass_peak_time(TYPICAL_P, 0.30)


# ---------------------------------------------------------------------------
# AC3: contagion fixpoint, cascade, isolation
# ---------------------------------------------------------------------------


def test_ac3_thresholds_span_innovator_zero_to_laggard_high():
    assert CATEGORY_THRESHOLDS[AdopterCategory.INNOVATOR] == pytest.approx(0.0)
    assert CATEGORY_THRESHOLDS[AdopterCategory.LAGGARD] == pytest.approx(0.75)
    values = [CATEGORY_THRESHOLDS[category] for category in CATEGORY_ORDER]
    assert values == sorted(values), "thresholds must rise from innovator to laggard"


def test_ac3_fully_connected_low_threshold_graph_cascades_to_everyone():
    adjacency = complete_graph(12)
    thresholds = {node: 0.05 for node in adjacency}
    history = simulate_contagion(adjacency, seeds={0}, thresholds=thresholds, max_steps=50)
    assert history[-1] == set(adjacency)


def test_ac3_isolated_node_with_high_threshold_never_adopts():
    adjacency = adjacency_from_edges([(0, 1), (1, 2), (0, 2)], nodes=[99])
    thresholds = {node: 0.1 for node in adjacency}
    thresholds[99] = 0.75  # laggard, and has no neighbours at all
    history = simulate_contagion(adjacency, seeds={0}, thresholds=thresholds, max_steps=50)
    assert 99 not in history[-1]
    assert {0, 1, 2}.issubset(history[-1])


def test_ac3_isolated_innovator_adopts_spontaneously():
    """Threshold 0.0 means no social proof required -- even with zero neighbours."""
    adjacency = {"lonely": set()}
    thresholds = {"lonely": CATEGORY_THRESHOLDS[AdopterCategory.INNOVATOR]}
    assert propagate(adjacency, adopted=set(), thresholds=thresholds) == {"lonely"}


def test_ac3_simulation_reaches_fixpoint_and_terminates():
    adjacency = complete_graph(10)
    thresholds = {node: 0.05 for node in adjacency}
    history = simulate_contagion(adjacency, seeds={0}, thresholds=thresholds, max_steps=1000)
    # Only changed states are recorded, so the run is far shorter than max_steps.
    assert len(history) < 1000
    # The final state is a genuine fixpoint of propagate().
    final = history[-1]
    assert propagate(adjacency, final, thresholds) == final
    # Each recorded step strictly grew the adopted set (monotone, no cycling).
    for earlier, later in zip(history, history[1:]):
        assert earlier < later


def test_ac3_stalled_cascade_terminates_without_converting_everyone():
    # A path a-b-c-d where 'd' is a laggard (threshold 0.75) with four
    # neighbours, only one of which ('c') ever adopts. Its adopted fraction
    # tops out at 1/4 = 0.25 < 0.75, so the cascade genuinely stalls at 'd'.
    # The dangling x/y/z each have only 'd' as a neighbour and a 0.99
    # threshold, so they cannot adopt either.
    adjacency = adjacency_from_edges(
        [("a", "b"), ("b", "c"), ("c", "d"), ("d", "x"), ("d", "y"), ("d", "z")]
    )
    assert len(adjacency["d"]) == 4  # the stall is structural, not incidental
    thresholds = {
        "a": 0.0,
        "b": 0.4,
        "c": 0.4,
        "d": 0.75,
        "x": 0.99,
        "y": 0.99,
        "z": 0.99,
    }
    history = simulate_contagion(adjacency, seeds={"a"}, thresholds=thresholds, max_steps=100)
    final = history[-1]
    assert propagate(adjacency, final, thresholds) == final  # genuine fixpoint
    assert final == {"a", "b", "c"}
    assert "d" not in final


def test_ac3_propagate_is_synchronous_and_order_independent():
    adjacency = adjacency_from_edges([(0, 1), (1, 2), (2, 3)])
    thresholds = {0: 0.0, 1: 0.5, 2: 0.5, 3: 0.5}
    # Starting from {0}: node 1 sees 1/2 adopted neighbours -> adopts.
    # Node 2 sees 0/2 at the START of the step -> must NOT adopt this step.
    after_one = propagate(adjacency, {0}, thresholds)
    assert after_one == {0, 1}


def test_ac3_max_steps_zero_returns_seeds_only():
    adjacency = complete_graph(5)
    thresholds = {node: 0.0 for node in adjacency}
    history = simulate_contagion(adjacency, seeds={0}, thresholds=thresholds, max_steps=0)
    assert history == [{0}]


def test_ac3_missing_threshold_falls_back_to_default():
    adjacency = complete_graph(4)
    # No thresholds supplied at all -> DEFAULT_THRESHOLD (0.5) for everyone.
    assert DEFAULT_THRESHOLD == pytest.approx(0.5)
    # Seeding 2 of 4: each unadopted node sees 2/3 adopted neighbours >= 0.5.
    assert propagate(adjacency, {0, 1}, thresholds={}) == {0, 1, 2, 3}
    # Seeding 1 of 4: each unadopted node sees 1/3 < 0.5 -> no adoption.
    assert propagate(adjacency, {0}, thresholds={}) == {0}


def test_ac3_thresholds_from_categories_uses_rogers_table():
    assignments = {
        "i": AdopterCategory.INNOVATOR,
        "l": AdopterCategory.LAGGARD,
    }
    thresholds = thresholds_from_categories(assignments)
    assert thresholds == {"i": 0.0, "l": 0.75}
    overridden = thresholds_from_categories(
        assignments, overrides={AdopterCategory.LAGGARD: 0.9}
    )
    assert overridden["l"] == pytest.approx(0.9)


def test_ac3_end_to_end_rogers_categories_drive_the_cascade():
    """Classified population -> thresholds -> cascade, with no manual wiring."""
    personas = spread_population(100)
    assignments = classify_population(personas)
    adjacency = complete_graph(0)
    adjacency = {persona["persona_id"]: set() for persona in personas}
    ids = list(adjacency)
    for node in ids:
        adjacency[node] = {other for other in ids if other != node}

    thresholds = thresholds_from_categories(assignments)
    history = simulate_contagion(adjacency, seeds=set(), thresholds=thresholds, max_steps=200)

    # Innovators (threshold 0.0) self-start, then the cascade proceeds.
    innovators = {
        node for node, category in assignments.items() if category is AdopterCategory.INNOVATOR
    }
    assert innovators
    assert innovators.issubset(history[-1])
    assert propagate(adjacency, history[-1], thresholds) == history[-1]


# ---------------------------------------------------------------------------
# AC4: Openness ordering
# ---------------------------------------------------------------------------


def test_ac4_higher_openness_classifies_into_earlier_categories():
    personas = [make_persona(f"p{index}", index / 199.0) for index in range(200)]
    assignments = classify_population(personas)

    # Walk from most to least open; the category rank must never decrease.
    ranks = [assignments[f"p{index}"].value for index in reversed(range(200))]
    assert ranks == sorted(ranks), "category rank must be monotone in Openness"

    assert assignments["p199"] is AdopterCategory.INNOVATOR
    assert assignments["p0"] is AdopterCategory.LAGGARD


def test_ac4_openness_dominates_the_score_when_other_traits_are_equal():
    low = make_persona("low", 0.1)
    high = make_persona("high", 0.9)
    assert innovativeness_score(high, scale=1.0) > innovativeness_score(low, scale=1.0)


def test_ac4_openness_outweighs_the_other_traits_combined():
    """A very open, otherwise-unfavourable persona still beats the reverse."""
    open_but_introverted = {
        "persona_id": "a",
        "big_five": {"openness": 1.0, "extraversion": 0.0, "neuroticism": 1.0},
    }
    closed_but_extraverted = {
        "persona_id": "b",
        "big_five": {"openness": 0.0, "extraversion": 1.0, "neuroticism": 0.0},
    }
    assert innovativeness_score(open_but_introverted, scale=1.0) > innovativeness_score(
        closed_but_extraverted, scale=1.0
    )


@pytest.mark.parametrize("scale", [1.0, 5.0, 10.0, 100.0])
def test_ac4_openness_ordering_survives_different_trait_scales(scale):
    personas = [
        {"persona_id": f"p{index}", "big_five": {"openness": (index / 49.0) * scale}}
        for index in range(50)
    ]
    assignments = classify_population(personas)
    ranks = [assignments[f"p{index}"].value for index in reversed(range(50))]
    assert ranks == sorted(ranks)


def test_ac4_graceful_fallback_when_big_five_absent():
    """No Big Five: proxies still order personas, and nothing raises."""
    personas = [
        {"persona_id": f"p{index}", "tech_savviness": index / 99.0} for index in range(100)
    ]
    assignments = classify_population(personas)
    assert len(assignments) == 100
    ranks = [assignments[f"p{index}"].value for index in reversed(range(100))]
    assert ranks == sorted(ranks)


def test_ac4_no_signal_at_all_still_classifies_everyone_deterministically():
    personas = [{"persona_id": f"p{index}"} for index in range(100)]
    first = classify_population(personas)
    second = classify_population(personas)
    assert first == second
    counts = category_counts(first)
    assert sum(counts.values()) == 100
    for category, share in CATEGORY_SHARES.items():
        assert abs(counts[category] - share * 100) <= 1


def test_ac4_flat_alias_keys_are_recognised():
    persona = {"persona_id": "x", "openness_to_experience": 0.9}
    assert innovativeness_score(persona, scale=1.0) > 0.5


# ---------------------------------------------------------------------------
# AC5: edge cases
# ---------------------------------------------------------------------------


def test_ac5_empty_population():
    assert classify_population([]) == {}
    assert classify_population({}) == {}
    assert category_counts({}) == {category: 0 for category in CATEGORY_ORDER}


def test_ac5_single_persona():
    assignments = classify_population([make_persona("solo", 0.5)])
    assert len(assignments) == 1
    # Largest remainder with n=1: the single slot goes to the largest share.
    category = assignments["solo"]
    assert isinstance(category, AdopterCategory)
    assert category in (AdopterCategory.EARLY_MAJORITY, AdopterCategory.LATE_MAJORITY)


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5])
def test_ac5_tiny_populations_are_fully_assigned(size):
    personas = spread_population(size)
    assignments = classify_population(personas)
    assert len(assignments) == size
    assert all(isinstance(value, AdopterCategory) for value in assignments.values())


def test_ac5_bass_with_p_zero_never_starts():
    """No external impulse means F(0)=0 is a fixpoint: nothing ever adopts."""
    curve = bass_adoption_curve(0.0, TYPICAL_Q, m=1_000.0, periods=25)
    assert curve == [0.0] * 25
    assert bass_peak_time(0.0, TYPICAL_Q) is None


def test_ac5_bass_with_q_zero_is_pure_exponential():
    market = 1_000.0
    curve = bass_adoption_curve(TYPICAL_P, 0.0, m=market, periods=30)
    for index, value in enumerate(curve, start=1):
        expected = market * (1.0 - math.exp(-TYPICAL_P * index))
        assert value == pytest.approx(expected, rel=1e-12)
    # Adoption rate decays from t=0, so there is no interior peak.
    assert bass_peak_time(TYPICAL_P, 0.0) is None
    increments = bass_incremental_adopters(TYPICAL_P, 0.0, m=market, periods=30)
    assert increments[0] == max(increments)


def test_ac5_bass_with_both_p_and_q_zero():
    assert bass_adoption_curve(0.0, 0.0, m=1_000.0, periods=10) == [0.0] * 10
    assert bass_peak_time(0.0, 0.0) is None


def test_ac5_bass_with_zero_periods_or_zero_market():
    assert bass_adoption_curve(TYPICAL_P, TYPICAL_Q, m=1_000.0, periods=0) == []
    assert bass_adoption_curve(TYPICAL_P, TYPICAL_Q, m=0.0, periods=5) == [0.0] * 5


def test_ac5_bass_rejects_negative_parameters():
    with pytest.raises(ValueError):
        bass_adoption_curve(-0.1, TYPICAL_Q, m=100.0, periods=5)
    with pytest.raises(ValueError):
        bass_adoption_curve(TYPICAL_P, -0.1, m=100.0, periods=5)
    with pytest.raises(ValueError):
        bass_adoption_curve(TYPICAL_P, TYPICAL_Q, m=-1.0, periods=5)
    with pytest.raises(ValueError):
        bass_adoption_curve(TYPICAL_P, TYPICAL_Q, m=100.0, periods=-1)


def test_ac5_bass_peak_time_when_q_below_p():
    """q <= p: the peak precedes launch, so t* is non-positive, not None."""
    peak = bass_peak_time(0.4, 0.2)
    assert peak is not None and peak < 0.0
    assert bass_peak_time(0.3, 0.3) == pytest.approx(0.0)


def test_ac5_contagion_on_empty_graph():
    assert propagate({}, adopted=set(), thresholds={}) == set()
    assert simulate_contagion({}, seeds=set(), thresholds={}, max_steps=10) == [set()]


def test_ac5_contagion_with_no_seeds_and_positive_thresholds_does_nothing():
    adjacency = complete_graph(6)
    thresholds = {node: 0.5 for node in adjacency}
    history = simulate_contagion(adjacency, seeds=set(), thresholds=thresholds, max_steps=20)
    assert history == [set()]


def test_ac5_single_node_graph():
    adjacency = {"only": set()}
    high = simulate_contagion(adjacency, seeds=set(), thresholds={"only": 0.5}, max_steps=10)
    assert high[-1] == set()
    zero = simulate_contagion(adjacency, seeds=set(), thresholds={"only": 0.0}, max_steps=10)
    assert zero[-1] == {"only"}


def test_ac5_self_loops_are_ignored():
    adjacency = {"a": {"a", "b"}, "b": {"a"}}
    # 'a' must not count itself as an adopted neighbour.
    assert propagate(adjacency, adopted=set(), thresholds={"a": 0.5, "b": 0.5}) == set()


def test_ac5_nodes_appearing_only_as_neighbours_are_included():
    adjacency = {"a": {"b"}}  # 'b' has no key of its own
    result = propagate(adjacency, adopted=set(), thresholds={"a": 0.9, "b": 0.0})
    assert result == {"b"}


def test_ac5_seeds_outside_the_graph_are_retained():
    adjacency = {"a": {"b"}, "b": {"a"}}
    result = propagate(adjacency, adopted={"ghost"}, thresholds={"a": 0.9, "b": 0.9})
    assert "ghost" in result


def test_ac5_non_mapping_persona_raises_typeerror():
    with pytest.raises(TypeError):
        classify_population([("not", "a", "mapping")])
    with pytest.raises(TypeError):
        innovativeness_score(["not a mapping"])


def test_ac5_module_has_no_app_or_flask_coupling():
    """The module must stay standalone: stdlib only, no app.* / Flask imports."""
    import ast
    import pathlib

    import app.services.diffusion_model as module

    source = pathlib.Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    forbidden = {"app", "flask", "sqlalchemy", "requests", "httpx", "celery"}
    assert not (imported & forbidden), f"forbidden imports found: {imported & forbidden}"

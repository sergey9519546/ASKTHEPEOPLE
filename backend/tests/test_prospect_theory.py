"""
Tests for the cumulative prospect theory module.

These tests are written as *empirical acceptance criteria*: each one encodes a
classic, replicated finding from the prospect theory literature and asserts
that the implementation reproduces it with the canonical TK92 parameters. They
are deliberately not tuned to the implementation -- if a test fails, the right
response is to question the parameters or the maths, not to loosen the test.

The module under test is standalone (stdlib only), so this file imports it
directly by file path rather than through ``app.services``. That package's
``__init__`` eagerly imports torch, camel-oasis and Flask-bound modules, which
would defeat the point of having an isolated, dependency-free module.
"""

import importlib.util
import math
import pathlib
import sys

import pytest


def _load_prospect_theory():
    """Import prospect_theory.py directly, bypassing app.services.__init__."""
    module_path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "app"
        / "services"
        / "prospect_theory.py"
    )
    spec = importlib.util.spec_from_file_location(
        "prospect_theory_isolated", module_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pt = _load_prospect_theory()

Prospect = pt.Prospect
PTParams = pt.PTParams


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


def test_module_has_no_heavy_dependencies():
    """The module must be pure stdlib: no app.*, flask, torch, requests."""
    source = (
        pathlib.Path(__file__).resolve().parent.parent
        / "app"
        / "services"
        / "prospect_theory.py"
    ).read_text(encoding="utf-8")

    forbidden = ("import flask", "from flask", "from app.", "import app.",
                 "import torch", "import requests", "import openai")
    for token in forbidden:
        assert token not in source.lower(), f"unexpected dependency: {token}"


def test_loads_without_flask_app():
    """Loading the module must not have pulled in Flask or the app package."""
    module = _load_prospect_theory()
    assert module.PTParams().alpha == pytest.approx(0.88)


# ---------------------------------------------------------------------------
# Value function basics
# ---------------------------------------------------------------------------


def test_value_function_canonical_shape():
    params = PTParams()

    assert pt.value(0.0, params) == pytest.approx(0.0)
    # Gains: v(x) = x ** alpha
    assert pt.value(100.0, params) == pytest.approx(100.0 ** 0.88)
    # Losses: v(x) = -lambda * (-x) ** beta
    assert pt.value(-100.0, params) == pytest.approx(-2.25 * (100.0 ** 0.88))


def test_value_function_is_concave_for_gains():
    """Diminishing sensitivity: doubling a gain less than doubles its value."""
    params = PTParams()
    assert pt.value(200.0, params) < 2.0 * pt.value(100.0, params)


def test_value_function_is_convex_for_losses():
    """Doubling a loss less than doubles the (absolute) pain."""
    params = PTParams()
    assert pt.value(-200.0, params) > 2.0 * pt.value(-100.0, params)


def test_losses_loom_larger_than_gains():
    """The defining kink: |v(-x)| > v(x) for x > 0."""
    params = PTParams()
    for x in (1.0, 10.0, 100.0, 1000.0):
        assert abs(pt.value(-x, params)) > pt.value(x, params)
    # And the ratio at equal magnitudes is exactly lambda_ when alpha == beta.
    assert abs(pt.value(-50.0, params)) / pt.value(50.0, params) == pytest.approx(
        2.25
    )


# ---------------------------------------------------------------------------
# Probability weighting
# ---------------------------------------------------------------------------


def test_weight_endpoints_are_exact():
    assert pt.weight(0.0, 0.61) == 0.0
    assert pt.weight(1.0, 0.61) == 1.0
    assert pt.weight(0.0, 0.69) == 0.0
    assert pt.weight(1.0, 0.69) == 1.0


def test_weight_is_monotonically_increasing():
    prev = -1.0
    for i in range(0, 101):
        p = i / 100.0
        w = pt.weight(p, 0.61)
        assert w > prev, f"w not increasing at p={p}"
        prev = w


def test_weight_overweights_small_probabilities():
    """w(p) > p for small p -- the source of lottery and insurance appeal."""
    for p in (0.001, 0.01, 0.05):
        assert pt.weight(p, 0.61) > p
        assert pt.weight(p, 0.69) > p


def test_weight_underweights_moderate_and_large_probabilities():
    """w(p) < p in the upper-middle range."""
    for p in (0.5, 0.7, 0.9, 0.99):
        assert pt.weight(p, 0.61) < p
        assert pt.weight(p, 0.69) < p


def test_weight_gamma_one_is_identity():
    """With no curvature the weighting function must be the identity."""
    for p in (0.1, 0.25, 0.5, 0.75, 0.9):
        assert pt.weight(p, 1.0) == pytest.approx(p)


# ---------------------------------------------------------------------------
# Classic finding 1: risk aversion for gains
# ---------------------------------------------------------------------------


def test_risk_aversion_in_gains():
    """A certain +50 is preferred to a 50% shot at +100."""
    certain = Prospect(outcomes=[50.0], probabilities=[1.0], label="certain_50")
    gamble = Prospect(
        outcomes=[100.0, 0.0], probabilities=[0.5, 0.5], label="gamble_100"
    )

    v_certain = pt.evaluate_prospect(certain, reference_point=0.0)
    v_gamble = pt.evaluate_prospect(gamble, reference_point=0.0)

    assert v_certain > v_gamble, (
        f"expected risk aversion in gains, got certain={v_certain:.4f} "
        f"gamble={v_gamble:.4f}"
    )

    # And the softmax choice should favour the sure thing.
    probs = pt.choose([certain, gamble], reference_point=0.0, temperature=5.0)
    assert probs["certain_50"] > probs["gamble_100"]


# ---------------------------------------------------------------------------
# Classic finding 2: risk seeking for losses (the reflection effect)
# ---------------------------------------------------------------------------


def test_risk_seeking_in_losses():
    """A 50% shot at -100 is preferred to a certain -50."""
    certain = Prospect(
        outcomes=[-50.0], probabilities=[1.0], label="certain_loss_50"
    )
    gamble = Prospect(
        outcomes=[-100.0, 0.0], probabilities=[0.5, 0.5], label="gamble_loss_100"
    )

    v_certain = pt.evaluate_prospect(certain, reference_point=0.0)
    v_gamble = pt.evaluate_prospect(gamble, reference_point=0.0)

    assert v_gamble > v_certain, (
        f"expected risk seeking in losses, got certain={v_certain:.4f} "
        f"gamble={v_gamble:.4f}"
    )
    # Both branches are of course still bad.
    assert v_certain < 0 and v_gamble < 0

    probs = pt.choose([certain, gamble], reference_point=0.0, temperature=5.0)
    assert probs["gamble_loss_100"] > probs["certain_loss_50"]


def test_reflection_effect_is_a_genuine_preference_reversal():
    """
    The same 50/50 structure flips preference between the gain and loss domain.
    Mirroring the outcomes must mirror the ranking.
    """
    gain_certain = Prospect([50.0], [1.0], "sure")
    gain_gamble = Prospect([100.0, 0.0], [0.5, 0.5], "risky")
    loss_certain = Prospect([-50.0], [1.0], "sure")
    loss_gamble = Prospect([-100.0, 0.0], [0.5, 0.5], "risky")

    gains_prefer_sure = pt.evaluate_prospect(gain_certain) > pt.evaluate_prospect(
        gain_gamble
    )
    losses_prefer_risky = pt.evaluate_prospect(
        loss_gamble
    ) > pt.evaluate_prospect(loss_certain)

    assert gains_prefer_sure and losses_prefer_risky


# ---------------------------------------------------------------------------
# Classic finding 3: loss aversion
# ---------------------------------------------------------------------------


def test_symmetric_coin_flip_has_negative_subjective_value():
    """A 50/50 win-100/lose-100 bet is unattractive despite zero EV."""
    bet = Prospect(
        outcomes=[100.0, -100.0], probabilities=[0.5, 0.5], label="fair_coin"
    )
    v = pt.evaluate_prospect(bet, reference_point=0.0)

    # Expected value is exactly zero...
    assert math.fsum(
        x * p for x, p in zip(bet.outcomes, bet.probabilities)
    ) == pytest.approx(0.0)
    # ...but subjective value is clearly negative.
    assert v < 0, f"expected loss aversion to make v < 0, got {v:.4f}"


def test_loss_aversion_requires_a_premium_to_accept_a_coin_flip():
    """
    A 50/50 bet needs a substantial upside premium before it becomes
    acceptable -- the standard experimental result.

    NOTE ON THE ACTUAL THRESHOLD. It is tempting to expect the indifference
    multiplier to equal lambda_ (2.25), but under *cumulative* PT it does not,
    and the gap is a real prediction of the model rather than a defect:

      * The loss branch is weighted with delta=0.69 and the gain branch with
        gamma=0.61, so at p=0.5 the loss gets decision weight 0.4540 while the
        gain gets only 0.4206. That asymmetry alone multiplies the effective
        loss aversion by 1.079, giving 2.25 * 1.079 = 2.43.
      * Concavity in gains (alpha=0.88) then means the winning side has to grow
        by more than 2.43x in raw money to close a 2.43x gap in value.

    The two effects compose to an indifference multiplier of ~2.74, which sits
    inside the ~1.5-3x band reported across lab studies, so the band is what we
    assert. Asserting ~2.25 exactly would be asserting a misreading of CPT.
    """
    rejected = Prospect([150.0, -100.0], [0.5, 0.5], "win150_lose100")
    assert pt.evaluate_prospect(rejected) < 0

    accepted = Prospect([320.0, -100.0], [0.5, 0.5], "win320_lose100")
    assert pt.evaluate_prospect(accepted) > 0

    # Locate the indifference multiplier and check it lands in the ~1.5-3 band
    # reported across lab studies.
    lo, hi = 1.0, 5.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if pt.evaluate_prospect(Prospect([100.0 * mid, -100.0], [0.5, 0.5])) < 0:
            lo = mid
        else:
            hi = mid
    ratio = (lo + hi) / 2.0
    assert 1.5 < ratio < 3.0, f"loss aversion ratio out of band: {ratio:.3f}"
    # Pin the exact model prediction so a parameter change is a visible diff.
    assert ratio == pytest.approx(2.74, abs=0.02)


def test_higher_loss_aversion_makes_mixed_gambles_less_attractive():
    bet = Prospect([100.0, -100.0], [0.5, 0.5], "coin")
    mild = pt.evaluate_prospect(bet, params=PTParams(lambda_=1.5))
    severe = pt.evaluate_prospect(bet, params=PTParams(lambda_=3.0))
    assert mild > severe


# ---------------------------------------------------------------------------
# Classic finding 4: reference dependence / framing
# ---------------------------------------------------------------------------


def test_same_outcome_flips_sign_when_reference_moves_across_it():
    """
    The core insight. An absolute outcome of 100 is a gain when the reference
    is 50 and a loss when the reference is 150 -- same world, opposite value.
    """
    outcome = Prospect([100.0], [1.0], "flat_100")

    as_gain = pt.evaluate_prospect(outcome, reference_point=50.0)
    as_loss = pt.evaluate_prospect(outcome, reference_point=150.0)
    at_reference = pt.evaluate_prospect(outcome, reference_point=100.0)

    assert as_gain > 0, f"expected a gain, got {as_gain:.4f}"
    assert as_loss < 0, f"expected a loss, got {as_loss:.4f}"
    assert at_reference == pytest.approx(0.0)


def test_framing_reverses_preference_between_identical_prospects():
    """
    Asian-disease style framing. Two prospects with identical absolute
    outcomes are ranked one way from a pessimistic reference (everything is a
    gain -> risk averse) and the other way from an optimistic reference
    (everything is a loss -> risk seeking).
    """
    sure = Prospect([200.0], [1.0], "sure_200")
    risky = Prospect([600.0, 0.0], [1.0 / 3.0, 2.0 / 3.0], "risky_600")

    # "Lives saved" frame: reference = 0 saved, so outcomes are gains.
    gain_frame = pt.choose([sure, risky], reference_point=0.0, temperature=5.0)

    # "Lives lost" frame: reference = 600 saved, so outcomes are losses.
    loss_frame = pt.choose([sure, risky], reference_point=600.0, temperature=5.0)

    assert gain_frame["sure_200"] > gain_frame["risky_600"], (
        f"gain frame should be risk averse: {gain_frame}"
    )
    assert loss_frame["risky_600"] > loss_frame["sure_200"], (
        f"loss frame should be risk seeking: {loss_frame}"
    )


def test_reference_point_shift_is_not_a_mere_constant_offset():
    """
    Under expected utility, shifting the reference would just relabel things
    monotonically. Under CPT it genuinely reorders prospects, which is what
    makes the theory non-consequentialist.
    """
    a = Prospect([100.0, 0.0], [0.5, 0.5], "a")
    b = Prospect([60.0, 40.0], [0.5, 0.5], "b")

    diff_low_ref = pt.evaluate_prospect(a, 0.0) - pt.evaluate_prospect(b, 0.0)
    diff_high_ref = pt.evaluate_prospect(a, 100.0) - pt.evaluate_prospect(
        b, 100.0
    )
    assert diff_low_ref * diff_high_ref < 0, (
        "expected the reference shift to reverse the ranking, got "
        f"{diff_low_ref:.4f} and {diff_high_ref:.4f}"
    )


# ---------------------------------------------------------------------------
# Classic finding 5: the fourfold pattern
# ---------------------------------------------------------------------------


def test_fourfold_low_probability_gain_is_risk_seeking_lottery_appeal():
    """
    A 1% chance of +100 beats a certain +1 of equal expected value: people
    overpay for lottery tickets.
    """
    lottery = Prospect([100.0, 0.0], [0.01, 0.99], "lottery")
    premium = Prospect([1.0], [1.0], "certain_1")

    v_lottery = pt.evaluate_prospect(lottery)
    v_certain = pt.evaluate_prospect(premium)

    assert v_lottery > v_certain, (
        f"expected lottery appeal, got lottery={v_lottery:.4f} "
        f"certain={v_certain:.4f}"
    )


def test_fourfold_low_probability_loss_is_risk_averse_insurance_appeal():
    """
    A certain -1 premium beats a 1% chance of -100 of equal expected value:
    people overpay for insurance.
    """
    uninsured = Prospect([-100.0, 0.0], [0.01, 0.99], "uninsured")
    premium = Prospect([-1.0], [1.0], "pay_premium")

    v_uninsured = pt.evaluate_prospect(uninsured)
    v_premium = pt.evaluate_prospect(premium)

    assert v_premium > v_uninsured, (
        f"expected insurance appeal, got premium={v_premium:.4f} "
        f"uninsured={v_uninsured:.4f}"
    )


def test_fourfold_pattern_all_four_cells():
    """
    The full 2x2: {gain, loss} x {low probability, high probability}.
      low-p gain   -> risk seeking
      high-p gain  -> risk aversion
      low-p loss   -> risk aversion
      high-p loss  -> risk seeking
    Each cell compares a gamble against its exact expected value as a sure
    thing, so any deviation is pure risk attitude.
    """
    def is_risk_seeking(outcome, probability):
        ev = outcome * probability
        gamble = Prospect([outcome, 0.0], [probability, 1.0 - probability], "g")
        sure = Prospect([ev], [1.0], "s")
        return pt.evaluate_prospect(gamble) > pt.evaluate_prospect(sure)

    assert is_risk_seeking(100.0, 0.01) is True, "low-p gain: expect seeking"
    assert is_risk_seeking(100.0, 0.90) is False, "high-p gain: expect aversion"
    assert is_risk_seeking(-100.0, 0.01) is False, "low-p loss: expect aversion"
    assert is_risk_seeking(-100.0, 0.90) is True, "high-p loss: expect seeking"


def test_low_probability_outcomes_are_overweighted_relative_to_expectation():
    """Direct check on decision weights rather than on preferences."""
    # Gain side: subjective value of a 1% shot at 100 exceeds w=p linear value.
    p = 0.01
    assert pt.weight(p, 0.61) / p > 4.0
    assert pt.weight(p, 0.69) / p > 3.0


# ---------------------------------------------------------------------------
# Cumulative representation sanity
# ---------------------------------------------------------------------------


def test_certain_outcome_equals_value_function():
    """With p=1 the weighting drops out entirely."""
    params = PTParams()
    for x in (-250.0, -1.0, 0.0, 1.0, 250.0):
        p = Prospect([x], [1.0], "sure")
        assert pt.evaluate_prospect(p, 0.0, params) == pytest.approx(
            pt.value(x, params)
        )


def test_evaluation_respects_stochastic_dominance():
    """Improving every outcome must not reduce subjective value."""
    worse = Prospect([10.0, 50.0, 90.0], [0.3, 0.4, 0.3], "worse")
    better = Prospect([20.0, 60.0, 100.0], [0.3, 0.4, 0.3], "better")
    assert pt.evaluate_prospect(better) > pt.evaluate_prospect(worse)


def test_outcome_order_does_not_matter():
    """The rank-dependent construction must sort internally."""
    a = Prospect([10.0, -20.0, 70.0], [0.2, 0.5, 0.3], "a")
    b = Prospect([70.0, 10.0, -20.0], [0.3, 0.2, 0.5], "b")
    assert pt.evaluate_prospect(a) == pytest.approx(pt.evaluate_prospect(b))


def test_duplicate_outcomes_are_handled():
    """Splitting one outcome into two identical halves must be a no-op."""
    single = Prospect([100.0, 0.0], [0.5, 0.5], "single")
    split = Prospect([100.0, 100.0, 0.0], [0.25, 0.25, 0.5], "split")
    assert pt.evaluate_prospect(single) == pytest.approx(
        pt.evaluate_prospect(split)
    )


def test_zero_probability_outcomes_do_not_contribute():
    base = Prospect([100.0, 0.0], [0.5, 0.5], "base")
    padded = Prospect([100.0, 0.0, 9999.0], [0.5, 0.5, 0.0], "padded")
    assert pt.evaluate_prospect(base) == pytest.approx(
        pt.evaluate_prospect(padded)
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_probabilities_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        Prospect(outcomes=[10.0, 20.0], probabilities=[0.5, 0.2], label="bad")
    with pytest.raises(ValueError, match="sum to 1"):
        Prospect(outcomes=[10.0, 20.0], probabilities=[0.7, 0.7], label="bad")


def test_probability_sum_tolerance_is_respected():
    # Just inside the 1e-6 tolerance: accepted.
    Prospect(outcomes=[10.0, 20.0], probabilities=[0.5, 0.5 + 9e-7], label="ok")
    # Just outside: rejected.
    with pytest.raises(ValueError, match="sum to 1"):
        Prospect(
            outcomes=[10.0, 20.0], probabilities=[0.5, 0.5 + 1e-5], label="bad"
        )


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError, match="same length"):
        Prospect(outcomes=[10.0, 20.0, 30.0], probabilities=[0.5, 0.5], label="x")
    with pytest.raises(ValueError, match="same length"):
        Prospect(outcomes=[10.0], probabilities=[0.5, 0.5], label="x")


def test_out_of_range_probabilities_are_rejected():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        Prospect(outcomes=[10.0, 20.0], probabilities=[-0.5, 1.5], label="x")


def test_empty_prospect_is_rejected():
    with pytest.raises(ValueError, match="at least one outcome"):
        Prospect(outcomes=[], probabilities=[], label="x")


def test_non_finite_values_are_rejected():
    with pytest.raises(ValueError):
        Prospect(outcomes=[float("inf")], probabilities=[1.0], label="x")
    with pytest.raises(ValueError):
        Prospect(outcomes=[1.0], probabilities=[float("nan")], label="x")


def test_weight_rejects_bad_probability():
    with pytest.raises(ValueError):
        pt.weight(1.5, 0.61)
    with pytest.raises(ValueError):
        pt.weight(-0.1, 0.61)


def test_weight_rejects_non_monotonic_curvature():
    """gamma below ~0.28 makes w(p) non-monotonic; refuse rather than lie."""
    with pytest.raises(ValueError, match="monotonic"):
        pt.weight(0.5, 0.1)


def test_params_reject_invalid_values():
    with pytest.raises(ValueError):
        PTParams(alpha=0.0)
    with pytest.raises(ValueError):
        PTParams(lambda_=-1.0)
    with pytest.raises(ValueError, match="monotonic"):
        PTParams(gamma=0.05)


def test_choose_rejects_bad_input():
    with pytest.raises(ValueError, match="must not be empty"):
        pt.choose([])
    with pytest.raises(ValueError, match="temperature"):
        pt.choose([Prospect([1.0], [1.0], "a")], temperature=0.0)
    with pytest.raises(ValueError, match="unique"):
        pt.choose(
            [Prospect([1.0], [1.0], "dup"), Prospect([2.0], [1.0], "dup")]
        )


# ---------------------------------------------------------------------------
# Choice probabilities
# ---------------------------------------------------------------------------


def test_choice_probabilities_sum_to_one():
    prospects = [
        Prospect([50.0], [1.0], "sure"),
        Prospect([100.0, 0.0], [0.5, 0.5], "coin"),
        Prospect([1000.0, 0.0], [0.01, 0.99], "lottery"),
        Prospect([-20.0, 80.0], [0.5, 0.5], "mixed"),
    ]
    for temperature in (0.1, 1.0, 10.0, 100.0):
        probs = pt.choose(prospects, reference_point=0.0, temperature=temperature)
        assert set(probs) == {"sure", "coin", "lottery", "mixed"}
        assert math.fsum(probs.values()) == pytest.approx(1.0)
        assert all(0.0 <= v <= 1.0 for v in probs.values())


def test_choice_is_stable_for_extreme_temperatures():
    """No overflow at tiny temperature, no NaN at huge temperature."""
    prospects = [
        Prospect([1000.0], [1.0], "big"),
        Prospect([-1000.0], [1.0], "small"),
    ]
    hot = pt.choose(prospects, temperature=1e6)
    cold = pt.choose(prospects, temperature=1e-3)

    assert math.fsum(hot.values()) == pytest.approx(1.0)
    assert math.fsum(cold.values()) == pytest.approx(1.0)
    # Near-uniform when hot, near-deterministic when cold.
    assert hot["big"] == pytest.approx(0.5, abs=0.01)
    assert cold["big"] > 0.999


def test_lower_temperature_sharpens_choice():
    prospects = [
        Prospect([50.0], [1.0], "sure"),
        Prospect([100.0, 0.0], [0.5, 0.5], "coin"),
    ]
    sharp = pt.choose(prospects, temperature=1.0)["sure"]
    soft = pt.choose(prospects, temperature=50.0)["sure"]
    assert sharp > soft


def test_single_prospect_gets_probability_one():
    probs = pt.choose([Prospect([42.0], [1.0], "only")])
    assert probs == {"only": pytest.approx(1.0)}


# ---------------------------------------------------------------------------
# Big Five mapping
# ---------------------------------------------------------------------------


def test_neutral_big_five_returns_canonical_parameters():
    """All traits at 0.5 must reproduce TK92 exactly."""
    params = pt.params_from_big_five(0.5, 0.5, 0.5, 0.5, 0.5)
    canonical = PTParams()
    assert params.alpha == pytest.approx(canonical.alpha)
    assert params.beta == pytest.approx(canonical.beta)
    assert params.lambda_ == pytest.approx(canonical.lambda_)
    assert params.gamma == pytest.approx(canonical.gamma)
    assert params.delta == pytest.approx(canonical.delta)


def test_higher_neuroticism_increases_loss_aversion():
    """The best-supported personality link in the module."""
    calm = pt.params_from_big_five(neuroticism=0.0)
    average = pt.params_from_big_five(neuroticism=0.5)
    anxious = pt.params_from_big_five(neuroticism=1.0)

    assert calm.lambda_ < average.lambda_ < anxious.lambda_


def test_loss_aversion_stays_in_documented_modest_range():
    """Modulations must stay modest: lambda_ in [1.8, 2.8]."""
    for i in range(0, 101):
        n = i / 100.0
        params = pt.params_from_big_five(neuroticism=n)
        assert 1.8 <= params.lambda_ <= 2.8


def test_all_modulated_parameters_stay_in_documented_ranges():
    extremes = (0.0, 0.5, 1.0)
    for o in extremes:
        for c in extremes:
            for e in extremes:
                for a in extremes:
                    for n in extremes:
                        p = pt.params_from_big_five(o, c, e, a, n)
                        assert 1.8 <= p.lambda_ <= 2.8
                        assert 0.82 <= p.alpha <= 0.94
                        assert 0.55 <= p.gamma <= 0.70
                        assert 0.60 <= p.delta <= 0.78
                        assert p.beta == pytest.approx(0.88)


def test_agreeableness_is_deliberately_unmapped():
    """
    Documented as an intentional non-mapping: we found no defensible link, so
    agreeableness must not silently affect anything.
    """
    low = pt.params_from_big_five(agreeableness=0.0)
    high = pt.params_from_big_five(agreeableness=1.0)
    assert low == high


def test_big_five_rejects_out_of_range_scores():
    with pytest.raises(ValueError, match="normalised score"):
        pt.params_from_big_five(neuroticism=1.5)
    with pytest.raises(ValueError, match="normalised score"):
        pt.params_from_big_five(openness=-0.2)


def test_neurotic_agent_rejects_gambles_a_calm_agent_accepts():
    """
    The personality modulation must produce a behavioural difference.

    The gamble has to be chosen to sit *between* the two agents' indifference
    thresholds, which for this module are ~2.13x (neuroticism 0.0, lambda_ 1.8)
    and ~3.51x (neuroticism 1.0, lambda_ 2.8). A win of 250 against a loss of
    100 is a 2.5x multiplier, so it falls in the window where the calm agent
    accepts and the anxious agent declines.
    """
    bet = Prospect([250.0, -100.0], [0.5, 0.5], "coin")

    calm = pt.params_from_big_five(neuroticism=0.0)
    anxious = pt.params_from_big_five(neuroticism=1.0)

    v_calm = pt.evaluate_prospect(bet, params=calm)
    v_anxious = pt.evaluate_prospect(bet, params=anxious)

    assert v_calm > v_anxious
    assert v_calm > 0 > v_anxious, (
        f"expected a preference reversal, got calm={v_calm:.4f} "
        f"anxious={v_anxious:.4f}"
    )


def test_classic_findings_survive_personality_variation():
    """
    Risk aversion in gains and risk seeking in losses are robust properties of
    CPT, not artefacts of the median parameters. They must hold across the
    whole modulated personality space.
    """
    gain_sure = Prospect([50.0], [1.0], "s")
    gain_risky = Prospect([100.0, 0.0], [0.5, 0.5], "r")
    loss_sure = Prospect([-50.0], [1.0], "s")
    loss_risky = Prospect([-100.0, 0.0], [0.5, 0.5], "r")

    for i in range(0, 11):
        t = i / 10.0
        params = pt.params_from_big_five(t, t, t, t, t)
        assert pt.evaluate_prospect(gain_sure, params=params) > (
            pt.evaluate_prospect(gain_risky, params=params)
        ), f"risk aversion in gains failed at trait level {t}"
        assert pt.evaluate_prospect(loss_risky, params=params) > (
            pt.evaluate_prospect(loss_sure, params=params)
        ), f"risk seeking in losses failed at trait level {t}"

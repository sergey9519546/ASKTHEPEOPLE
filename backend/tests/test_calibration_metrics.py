"""Acceptance tests for :mod:`app.services.calibration_metrics`.

These tests are the specification. Each one encodes a property that must
hold for the scores to be trustworthy when quoted:

* known-answer anchors (perfect / inverted / always-0.5 forecasters),
* the Murphy decomposition identity to 1e-9 on multiple datasets,
* the calibration-is-not-discrimination distinction,
* correct handling of tied forecasts in AUC,
* and hard failure on invalid input.

The module under test is imported directly rather than through the Flask
application factory, which is the point of keeping it dependency-free.
"""

import math
import random

import pytest

from app.services.calibration_metrics import (
    Bin,
    auc_roc,
    brier_score,
    brier_skill_score,
    calibration_curve,
    expected_calibration_error,
    log_score,
    murphy_decomposition,
)

TOLERANCE = 1e-9


# --------------------------------------------------------------------------
# fixtures / dataset builders
# --------------------------------------------------------------------------


def perfect_pairs():
    """1.0 on everything that happened, 0.0 on everything that did not."""
    return [(1.0, 1), (1.0, 1), (0.0, 0), (0.0, 0), (1.0, 1), (0.0, 0)]


def inverted_pairs():
    """Confidently backwards: high forecasts on non-events."""
    return [(0.0, 1), (0.0, 1), (1.0, 0), (1.0, 0), (0.0, 1), (1.0, 0)]


def balanced_half_pairs():
    """Always 0.5, on a set with three events and three non-events."""
    return [(0.5, 1), (0.5, 0), (0.5, 1), (0.5, 0), (0.5, 1), (0.5, 0)]


def continuous_pairs(seed=7, n=500, base_rate=0.6):
    """Uniform forecasts, outcomes independent of them (uninformative).

    Deliberately spreads forecasts *within* each bin, which is the case
    that breaks a naive Murphy decomposition.
    """
    rng = random.Random(seed)
    return [
        (rng.random(), 1 if rng.random() < base_rate else 0) for _ in range(n)
    ]


def informative_pairs(seed=11, n=400):
    """Forecasts that genuinely carry signal, with realistic noise."""
    rng = random.Random(seed)
    pairs = []
    for _ in range(n):
        latent = rng.random()
        probability = min(max(latent + rng.gauss(0.0, 0.08), 0.0), 1.0)
        pairs.append((probability, 1 if rng.random() < latent else 0))
    return pairs


# --------------------------------------------------------------------------
# 1. perfect forecaster
# --------------------------------------------------------------------------


def test_perfect_forecaster_scores_zero_brier():
    assert brier_score(perfect_pairs()) == pytest.approx(0.0, abs=TOLERANCE)


def test_perfect_forecaster_scores_auc_one():
    assert auc_roc(perfect_pairs()) == pytest.approx(1.0, abs=TOLERANCE)


def test_perfect_forecaster_has_zero_log_score():
    # Clamping means this is not exactly 0.0, but it must be negligible.
    assert log_score(perfect_pairs()) < 1e-12


# --------------------------------------------------------------------------
# 2. always-0.5 baseline
# --------------------------------------------------------------------------


def test_always_half_on_balanced_set_scores_exactly_quarter():
    assert brier_score(balanced_half_pairs()) == pytest.approx(
        0.25, abs=TOLERANCE
    )


def test_always_half_scores_quarter_regardless_of_base_rate():
    # (0.5 - o)^2 == 0.25 for o in {0, 1}, so this holds for any mix.
    skewed = [(0.5, 1)] * 9 + [(0.5, 0)]
    assert brier_score(skewed) == pytest.approx(0.25, abs=TOLERANCE)


def test_maximally_wrong_forecaster_scores_brier_one():
    assert brier_score(inverted_pairs()) == pytest.approx(1.0, abs=TOLERANCE)


# --------------------------------------------------------------------------
# 3. inverted forecaster
# --------------------------------------------------------------------------


def test_perfectly_inverted_forecaster_scores_auc_zero():
    assert auc_roc(inverted_pairs()) == pytest.approx(0.0, abs=TOLERANCE)


def test_inverting_forecasts_reflects_auc_about_half():
    pairs = informative_pairs()
    flipped = [(1.0 - p, o) for p, o in pairs]
    assert auc_roc(pairs) + auc_roc(flipped) == pytest.approx(
        1.0, abs=TOLERANCE
    )


# --------------------------------------------------------------------------
# 4. uninformative forecaster
# --------------------------------------------------------------------------


def test_random_forecaster_has_auc_near_half():
    assert auc_roc(continuous_pairs(seed=3, n=4000)) == pytest.approx(
        0.5, abs=0.05
    )


def test_informative_forecaster_beats_random_on_auc():
    assert auc_roc(informative_pairs()) > 0.8


# --------------------------------------------------------------------------
# 5. Murphy identity
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pairs, label",
    [
        (perfect_pairs(), "perfect"),
        (balanced_half_pairs(), "always-0.5"),
        (inverted_pairs(), "inverted"),
        (continuous_pairs(seed=7), "continuous-uninformative"),
        (continuous_pairs(seed=21, n=137, base_rate=0.2), "low-base-rate"),
        (informative_pairs(), "informative"),
    ],
)
def test_murphy_identity_holds_to_1e9(pairs, label):
    """Brier == reliability - resolution + uncertainty + within_bin_error.

    The within-bin term is a genuine part of the identity once continuous
    forecasts are binned; see the module docstring. It is exactly 0.0 when
    binning is lossless.
    """
    result = murphy_decomposition(pairs)
    reconstructed = (
        result["reliability"]
        - result["resolution"]
        + result["uncertainty"]
        + result["within_bin_error"]
    )
    assert reconstructed == pytest.approx(result["brier"], abs=TOLERANCE), label
    assert abs(result["identity_residual"]) < TOLERANCE, label


@pytest.mark.parametrize("n_bins", [1, 2, 5, 10, 20, 50])
def test_murphy_identity_holds_across_bin_counts(n_bins):
    result = murphy_decomposition(continuous_pairs(seed=5, n=300), n_bins=n_bins)
    reconstructed = (
        result["reliability"]
        - result["resolution"]
        + result["uncertainty"]
        + result["within_bin_error"]
    )
    assert reconstructed == pytest.approx(result["brier"], abs=TOLERANCE)


def test_three_term_identity_is_exact_when_bins_are_lossless():
    """With forecasts on bin-interior constants, within_bin_error is 0.0.

    This is Murphy's original discrete setting, and it pins down that the
    fourth term is a discretization artifact rather than a fudge factor.
    """
    pairs = (
        [(0.05, 1)] * 2
        + [(0.05, 0)] * 18
        + [(0.45, 1)] * 9
        + [(0.45, 0)] * 11
        + [(0.95, 1)] * 19
        + [(0.95, 0)] * 1
    )
    result = murphy_decomposition(pairs, n_bins=10)
    assert result["within_bin_error"] == pytest.approx(0.0, abs=1e-15)
    three_term = (
        result["reliability"] - result["resolution"] + result["uncertainty"]
    )
    assert three_term == pytest.approx(result["brier"], abs=TOLERANCE)


def test_within_bin_error_is_material_for_continuous_forecasts():
    """Guard against a future 'simplification' back to the naive formula.

    If someone drops the within-bin term, the three-term sum misses the
    Brier score by far more than 1e-9. This test documents that gap so the
    omission fails loudly instead of quietly.
    """
    result = murphy_decomposition(continuous_pairs(seed=7), n_bins=10)
    three_term = (
        result["reliability"] - result["resolution"] + result["uncertainty"]
    )
    gap = abs(three_term - result["brier"])
    assert gap > 1e-9
    assert result["within_bin_error"] == pytest.approx(
        result["brier"] - three_term, abs=TOLERANCE
    )


def test_uncertainty_is_base_rate_variance():
    pairs = [(0.5, 1)] * 3 + [(0.5, 0)] * 7
    result = murphy_decomposition(pairs)
    assert result["base_rate"] == pytest.approx(0.3, abs=TOLERANCE)
    assert result["uncertainty"] == pytest.approx(0.21, abs=TOLERANCE)


def test_perfect_forecaster_has_zero_reliability_and_max_resolution():
    result = murphy_decomposition(perfect_pairs())
    assert result["reliability"] == pytest.approx(0.0, abs=TOLERANCE)
    # A perfect forecaster's resolution absorbs all the uncertainty.
    assert result["resolution"] == pytest.approx(
        result["uncertainty"], abs=TOLERANCE
    )


# --------------------------------------------------------------------------
# 6. calibration is NOT discrimination (the key conceptual case)
# --------------------------------------------------------------------------


def test_calibrated_but_uninformative_has_low_reliability_and_zero_resolution():
    """Always predicting the true base rate: perfectly calibrated, useless.

    30 of 100 events occur and the forecaster says 0.30 every single time.
    It is flawlessly calibrated -- reliability error ~0, ECE ~0 -- and yet
    it has *no* ability to tell which events will occur: resolution is
    exactly 0 and AUC is exactly 0.5. Both assertions together are the
    whole reason this module reports calibration and discrimination
    separately.
    """
    pairs = [(0.30, 1)] * 30 + [(0.30, 0)] * 70
    result = murphy_decomposition(pairs)

    # Calibration: essentially perfect.
    assert result["reliability"] == pytest.approx(0.0, abs=TOLERANCE)
    assert expected_calibration_error(pairs) == pytest.approx(
        0.0, abs=TOLERANCE
    )

    # Discrimination: nonexistent.
    assert result["resolution"] == pytest.approx(0.0, abs=TOLERANCE)
    assert auc_roc(pairs) == pytest.approx(0.5, abs=TOLERANCE)

    # And its Brier score is exactly the irreducible uncertainty.
    assert result["brier"] == pytest.approx(
        result["uncertainty"], abs=TOLERANCE
    )
    # It cannot beat the base-rate baseline, by construction.
    assert brier_skill_score(pairs) == pytest.approx(0.0, abs=TOLERANCE)


def test_discriminating_but_miscalibrated_forecaster_is_the_mirror_case():
    """Perfect ranking, badly calibrated: AUC 1.0 but large reliability error.

    The complement of the test above. Together they establish that neither
    metric family implies the other.
    """
    pairs = [(0.55, 1)] * 50 + [(0.45, 0)] * 50
    result = murphy_decomposition(pairs)

    assert auc_roc(pairs) == pytest.approx(1.0, abs=TOLERANCE)
    assert result["resolution"] > 0.2
    # Says ~50/50 while being certain in practice: miscalibrated.
    assert result["reliability"] > 0.15
    assert expected_calibration_error(pairs) == pytest.approx(
        0.45, abs=TOLERANCE
    )


# --------------------------------------------------------------------------
# 7. tie handling in AUC
# --------------------------------------------------------------------------


def test_all_identical_predictions_give_auc_exactly_half():
    """Every forecast tied => every pair is a tie => AUC is exactly 0.5.

    A naive implementation that counts only strict ``>`` returns 0.0 here,
    and one that counts ``>=`` returns 1.0. Both are wrong.
    """
    pairs = [(0.42, 1)] * 5 + [(0.42, 0)] * 5
    assert auc_roc(pairs) == 0.5


@pytest.mark.parametrize("value", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_constant_forecast_at_any_value_gives_auc_half(value):
    pairs = [(value, 1)] * 3 + [(value, 0)] * 7
    assert auc_roc(pairs) == pytest.approx(0.5, abs=TOLERANCE)


def test_partial_ties_count_as_one_half():
    """Hand-computed mixed case: one clean pair, two tied pairs.

    Positives {0.8, 0.5}, negatives {0.5, 0.2}. Pairwise:
    0.8>0.5 -> 1, 0.8>0.2 -> 1, 0.5==0.5 -> 0.5, 0.5>0.2 -> 1.
    Total 3.5 over 4 pairs = 0.875.
    """
    pairs = [(0.8, 1), (0.5, 1), (0.5, 0), (0.2, 0)]
    assert auc_roc(pairs) == pytest.approx(0.875, abs=TOLERANCE)


def test_auc_matches_bruteforce_pairwise_definition_with_heavy_ties():
    """Cross-check the O(n log n) midrank result against the definition.

    Forecasts are rounded to one decimal to force many ties, which is
    where an efficient implementation is most likely to diverge.
    """
    rng = random.Random(99)
    pairs = [
        (round(rng.random(), 1), 1 if rng.random() < 0.5 else 0)
        for _ in range(200)
    ]
    positives = [p for p, o in pairs if o == 1]
    negatives = [p for p, o in pairs if o == 0]
    wins = math.fsum(
        1.0 if hi > lo else 0.5 if hi == lo else 0.0
        for hi in positives
        for lo in negatives
    )
    expected = wins / (len(positives) * len(negatives))
    assert auc_roc(pairs) == pytest.approx(expected, abs=TOLERANCE)


def test_auc_requires_both_classes():
    with pytest.raises(ValueError, match="positive and .* negative"):
        auc_roc([(0.6, 1), (0.7, 1)])
    with pytest.raises(ValueError, match="positive and .* negative"):
        auc_roc([(0.6, 0), (0.7, 0)])


# --------------------------------------------------------------------------
# 8. ECE and the calibration curve
# --------------------------------------------------------------------------


def test_ece_is_zero_for_perfectly_calibrated_set():
    """Each bucket's realized frequency equals its forecast exactly."""
    pairs = (
        [(0.1, 1)] * 1
        + [(0.1, 0)] * 9
        + [(0.5, 1)] * 5
        + [(0.5, 0)] * 5
        + [(0.9, 1)] * 9
        + [(0.9, 0)] * 1
    )
    assert expected_calibration_error(pairs) == pytest.approx(
        0.0, abs=TOLERANCE
    )


def test_ece_is_zero_for_the_perfect_forecaster():
    assert expected_calibration_error(perfect_pairs()) == pytest.approx(
        0.0, abs=TOLERANCE
    )


def test_ece_is_one_for_the_maximally_wrong_forecaster():
    assert expected_calibration_error(inverted_pairs()) == pytest.approx(
        1.0, abs=TOLERANCE
    )


def test_ece_is_count_weighted_not_bin_weighted():
    """A large well-calibrated bin must dominate a tiny broken one.

    100 forecasts at 0.5 with a 50/50 split are exactly calibrated (zero
    gap); a single 0.95 forecast on a non-event is wrong by 0.95. The
    count-weighted ECE is 0.95 / 101 = 0.0094. An unweighted mean over
    occupied bins would report (0 + 0.95) / 2 = 0.475 -- fifty times
    worse, and thoroughly misleading about a mostly-calibrated set.
    """
    pairs = [(0.5, 1)] * 50 + [(0.5, 0)] * 50 + [(0.95, 0)]
    assert expected_calibration_error(pairs, n_bins=10) == pytest.approx(
        0.95 / 101, abs=1e-9
    )


def test_calibration_curve_answers_the_seventy_percent_question():
    """70% forecasts that occur 70% of the time show zero gap."""
    pairs = [(0.7, 1)] * 70 + [(0.7, 0)] * 30
    bucket = next(
        b for b in calibration_curve(pairs, n_bins=10) if b.count > 0
    )
    assert bucket.bin_lower == pytest.approx(0.7)
    assert bucket.bin_upper == pytest.approx(0.8)
    assert bucket.count == 100
    assert bucket.mean_predicted == pytest.approx(0.7, abs=TOLERANCE)
    assert bucket.observed_frequency == pytest.approx(0.7, abs=TOLERANCE)


def test_calibration_curve_returns_all_bins_with_empty_marked_none():
    curve = calibration_curve([(0.05, 1), (0.05, 0)], n_bins=10)
    assert len(curve) == 10
    assert all(isinstance(b, Bin) for b in curve)
    assert curve[0].count == 2
    # Empty bins must be None, never a misleading 0.0.
    for bucket in curve[1:]:
        assert bucket.count == 0
        assert bucket.mean_predicted is None
        assert bucket.observed_frequency is None


def test_calibration_curve_counts_sum_to_input_size():
    pairs = continuous_pairs(seed=13, n=250)
    curve = calibration_curve(pairs, n_bins=7)
    assert sum(b.count for b in curve) == len(pairs)


def test_probability_one_lands_in_final_bin_not_dropped():
    """p == 1.0 must fall in the top bin; a naive int(p*n) overflows."""
    curve = calibration_curve([(1.0, 1), (1.0, 0)], n_bins=10)
    assert curve[-1].count == 2
    assert curve[-1].bin_upper == pytest.approx(1.0)
    assert sum(b.count for b in curve) == 2


def test_bin_edges_are_robust_to_float_representation():
    """0.3 and 0.7 are not exact in binary; they must still bin correctly."""
    curve = calibration_curve([(0.3, 1), (0.7, 0)], n_bins=10)
    assert curve[3].count == 1  # [0.3, 0.4)
    assert curve[7].count == 1  # [0.7, 0.8)


# --------------------------------------------------------------------------
# brier skill score
# --------------------------------------------------------------------------


def test_perfect_forecaster_has_skill_one():
    assert brier_skill_score(perfect_pairs()) == pytest.approx(
        1.0, abs=TOLERANCE
    )


def test_informative_forecaster_has_positive_skill():
    assert brier_skill_score(informative_pairs()) > 0.0


def test_uninformative_forecaster_has_negative_skill():
    """Uniform noise on a 0.6 base rate is worse than quoting 0.6."""
    assert brier_skill_score(continuous_pairs(seed=7)) < 0.0


def test_skill_against_explicit_baseline_rate():
    pairs = [(0.5, 1), (0.5, 0), (0.5, 1), (0.5, 0)]
    # Baseline 0.5 is the same forecast, so skill is exactly 0.
    assert brier_skill_score(pairs, baseline_rate=0.5) == pytest.approx(
        0.0, abs=TOLERANCE
    )


def test_skill_raises_when_baseline_is_degenerate():
    # Every outcome is 1 and the base rate is 1.0: baseline Brier is 0.
    with pytest.raises(ValueError, match="undefined"):
        brier_skill_score([(0.9, 1), (0.8, 1)])


# --------------------------------------------------------------------------
# log score
# --------------------------------------------------------------------------


def test_log_score_of_always_half_is_ln_two():
    assert log_score(balanced_half_pairs()) == pytest.approx(
        math.log(2.0), abs=TOLERANCE
    )


def test_log_score_is_finite_when_confidently_wrong():
    """The whole point of epsilon: a large penalty, not inf."""
    score = log_score([(1.0, 0), (0.0, 1)])
    assert math.isfinite(score)
    assert score > 30.0


def test_log_score_penalizes_overconfidence_more_than_brier():
    timid = [(0.6, 1), (0.4, 0)]
    reckless = [(0.999, 1), (0.999, 0)]
    assert log_score(reckless) > log_score(timid)


# --------------------------------------------------------------------------
# 9. validation
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "func",
    [
        brier_score,
        brier_skill_score,
        murphy_decomposition,
        calibration_curve,
        expected_calibration_error,
        auc_roc,
        log_score,
    ],
)
def test_every_metric_rejects_empty_input(func):
    with pytest.raises(ValueError, match="at least one"):
        func([])


@pytest.mark.parametrize(
    "func",
    [
        brier_score,
        brier_skill_score,
        murphy_decomposition,
        calibration_curve,
        expected_calibration_error,
        auc_roc,
        log_score,
    ],
)
@pytest.mark.parametrize("bad_probability", [-0.01, 1.01, 2.0, -1.0, 100.0])
def test_every_metric_rejects_out_of_range_probability(func, bad_probability):
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        func([(0.5, 1), (bad_probability, 0)])


@pytest.mark.parametrize(
    "func",
    [
        brier_score,
        brier_skill_score,
        murphy_decomposition,
        calibration_curve,
        expected_calibration_error,
        auc_roc,
        log_score,
    ],
)
@pytest.mark.parametrize("bad_outcome", [2, -1, 0.5, "1", None, 1.5])
def test_every_metric_rejects_non_binary_outcome(func, bad_outcome):
    with pytest.raises(ValueError, match="0 or 1"):
        func([(0.5, 1), (0.5, bad_outcome)])


@pytest.mark.parametrize("bad_probability", [float("nan"), float("inf"), float("-inf")])
def test_nan_and_inf_probabilities_are_rejected(bad_probability):
    """NaN compares False against everything, so it must be caught by name."""
    with pytest.raises(ValueError, match="finite"):
        brier_score([(0.5, 1), (bad_probability, 0)])


def test_non_numeric_probability_is_rejected():
    with pytest.raises(ValueError, match="real number"):
        brier_score([("0.5", 1)])


@pytest.mark.parametrize(
    "malformed", [[(0.5,)], [(0.5, 1, 0)], [0.5], ["ab"], [None]]
)
def test_malformed_pairs_are_rejected(malformed):
    with pytest.raises(ValueError):
        brier_score(malformed)


def test_none_input_is_rejected():
    with pytest.raises(ValueError, match="None"):
        brier_score(None)


@pytest.mark.parametrize("bad_bins", [0, -1, -10, 2.5, "10", None])
def test_binned_metrics_reject_invalid_bin_counts(bad_bins):
    pairs = [(0.5, 1), (0.5, 0)]
    for func in (
        calibration_curve,
        expected_calibration_error,
        murphy_decomposition,
    ):
        with pytest.raises(ValueError, match="n_bins"):
            func(pairs, n_bins=bad_bins)


@pytest.mark.parametrize("bad_epsilon", [0.0, -1e-9, 0.5, 0.9, 1.0, float("nan")])
def test_log_score_rejects_invalid_epsilon(bad_epsilon):
    with pytest.raises(ValueError, match="epsilon"):
        log_score([(0.5, 1)], epsilon=bad_epsilon)


@pytest.mark.parametrize("bad_rate", [-0.1, 1.1, float("inf")])
def test_brier_skill_score_rejects_invalid_baseline(bad_rate):
    with pytest.raises(ValueError, match="baseline_rate"):
        brier_skill_score([(0.5, 1), (0.5, 0)], baseline_rate=bad_rate)


def test_boolean_outcomes_are_accepted_as_zero_and_one():
    """True/False are unambiguous binary outcomes; accept them."""
    assert brier_score([(1.0, True), (0.0, False)]) == pytest.approx(
        0.0, abs=TOLERANCE
    )


def test_integer_probabilities_zero_and_one_are_accepted():
    assert brier_score([(1, 1), (0, 0)]) == pytest.approx(0.0, abs=TOLERANCE)


def test_generators_are_consumed_safely():
    """A one-shot iterable must not be silently exhausted mid-computation."""
    assert murphy_decomposition((p for p in [(0.5, 1), (0.5, 0)]))["n"] == 2


# --------------------------------------------------------------------------
# invariants / ranges
# --------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_all_metrics_stay_within_documented_ranges(seed):
    pairs = informative_pairs(seed=seed, n=200)
    assert 0.0 <= brier_score(pairs) <= 1.0
    assert 0.0 <= auc_roc(pairs) <= 1.0
    assert 0.0 <= expected_calibration_error(pairs) <= 1.0
    assert log_score(pairs) >= 0.0

    result = murphy_decomposition(pairs)
    assert result["reliability"] >= 0.0
    assert result["resolution"] >= 0.0
    assert 0.0 <= result["uncertainty"] <= 0.25


def test_metrics_are_invariant_to_input_order():
    pairs = informative_pairs(seed=17, n=150)
    shuffled = list(pairs)
    random.Random(4).shuffle(shuffled)
    assert brier_score(shuffled) == pytest.approx(
        brier_score(pairs), abs=TOLERANCE
    )
    assert auc_roc(shuffled) == pytest.approx(auc_roc(pairs), abs=TOLERANCE)
    assert expected_calibration_error(shuffled) == pytest.approx(
        expected_calibration_error(pairs), abs=TOLERANCE
    )


def test_module_has_no_heavyweight_dependencies():
    """The module must stay importable in isolation.

    No numpy/pandas/Flask and no ``app.*`` imports, so the math can be
    audited and reused without an application context.
    """
    import app.services.calibration_metrics as module

    source = open(module.__file__, encoding="utf-8").read()
    for forbidden in ("import numpy", "import pandas", "import flask", "from flask"):
        assert forbidden not in source.lower()
    assert "from app." not in source
    assert "import requests" not in source

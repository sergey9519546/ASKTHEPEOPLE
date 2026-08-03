"""Forecast-scoring and calibration metrics (pure math, zero dependencies).

This module answers two *different* questions that are frequently and
incorrectly conflated:

1. **Calibration / reliability** -- "when I say 70%, does it happen 70% of
   the time?" Measured by :func:`calibration_curve`,
   :func:`expected_calibration_error`, and the ``reliability`` term of
   :func:`murphy_decomposition`. Lower is better.

2. **Discrimination / resolution** -- "do my forecasts separate the events
   that happened from the ones that did not?" Measured by :func:`auc_roc`
   and the ``resolution`` term of :func:`murphy_decomposition`. Higher is
   better.

A forecaster that always predicts the true base rate is *perfectly
calibrated and completely useless*: reliability error ~0, resolution ~0.
That case is the reason both families of metric exist, and it is asserted
in the test suite.

Design constraints (deliberate):
    * Standard library only -- ``math``, ``bisect``, ``typing``. No numpy,
      no pandas, no Flask, no ``app.*`` imports, no network. The module is
      importable in complete isolation, which keeps the math auditable and
      unit-testable without application context.
    * Every function validates its input and raises :class:`ValueError`
      rather than returning a misleading number. A silently-wrong score is
      worse than no score, because it will be quoted.

Input format throughout: an iterable of ``(predicted_probability,
observed_binary_outcome)`` pairs, where the probability is in ``[0, 1]``
and the outcome is exactly ``0`` or ``1``.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from typing import Any, Iterable, NamedTuple

__all__ = [
    "Bin",
    "brier_score",
    "brier_skill_score",
    "murphy_decomposition",
    "calibration_curve",
    "expected_calibration_error",
    "auc_roc",
    "log_score",
]


class Bin(NamedTuple):
    """One bucket of a reliability diagram.

    Attributes:
        bin_lower: Inclusive lower edge of the probability bucket.
        bin_upper: Upper edge. Exclusive, except for the final bin whose
            upper edge is ``1.0`` inclusive.
        count: Number of forecasts that landed in this bucket.
        mean_predicted: Mean forecast probability in the bucket, or
            ``None`` when the bucket is empty. ``None`` rather than ``0.0``
            so an empty bucket can never be mistaken for a confident one.
        observed_frequency: Fraction of bucket events that actually
            occurred, or ``None`` when the bucket is empty.
    """

    bin_lower: float
    bin_upper: float
    count: int
    mean_predicted: float | None
    observed_frequency: float | None


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------


def _validate_pairs(pairs: Iterable[Any]) -> list[tuple[float, int]]:
    """Normalize and hard-validate the ``(probability, outcome)`` input.

    Raises:
        ValueError: On empty input, malformed pairs, non-numeric or NaN
            probabilities, probabilities outside ``[0, 1]``, or outcomes
            that are not exactly 0 or 1.
    """
    if pairs is None:
        raise ValueError("pairs must not be None")

    cleaned: list[tuple[float, int]] = []
    for index, pair in enumerate(pairs):
        if isinstance(pair, (str, bytes)):
            raise ValueError(
                f"pair at index {index} must be a (probability, outcome) "
                f"sequence, got {type(pair).__name__}"
            )
        try:
            probability, outcome = pair
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"pair at index {index} must unpack to exactly "
                f"(probability, outcome): {pair!r}"
            ) from exc

        if isinstance(probability, bool) or not isinstance(
            probability, (int, float)
        ):
            raise ValueError(
                f"probability at index {index} must be a real number, got "
                f"{probability!r}"
            )
        probability = float(probability)
        # NaN must be rejected explicitly: every comparison against NaN is
        # False, so a plain range check would let it through and poison the
        # arithmetic downstream.
        if math.isnan(probability) or math.isinf(probability):
            raise ValueError(
                f"probability at index {index} must be finite, got "
                f"{probability!r}"
            )
        if probability < 0.0 or probability > 1.0:
            raise ValueError(
                f"probability at index {index} must be in [0, 1], got "
                f"{probability!r}"
            )

        if isinstance(outcome, bool):
            outcome_int = int(outcome)
        elif isinstance(outcome, int):
            outcome_int = outcome
        elif isinstance(outcome, float):
            if not outcome.is_integer():
                raise ValueError(
                    f"outcome at index {index} must be exactly 0 or 1, got "
                    f"{outcome!r}"
                )
            outcome_int = int(outcome)
        else:
            raise ValueError(
                f"outcome at index {index} must be 0 or 1, got {outcome!r}"
            )
        if outcome_int not in (0, 1):
            raise ValueError(
                f"outcome at index {index} must be exactly 0 or 1, got "
                f"{outcome!r}"
            )

        cleaned.append((probability, outcome_int))

    if not cleaned:
        raise ValueError("pairs must contain at least one forecast")
    return cleaned


def _validate_n_bins(n_bins: int) -> int:
    if isinstance(n_bins, bool) or not isinstance(n_bins, int):
        raise ValueError(f"n_bins must be an integer, got {n_bins!r}")
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins}")
    return n_bins


def _bin_index(probability: float, edges: list[float]) -> int:
    """Return the bucket index for ``probability``.

    Buckets are equal width over ``[0, 1]``, lower edge inclusive, upper
    edge exclusive, with the final bucket closed so that ``p == 1.0``
    lands in the top bucket instead of overflowing.

    ``bisect_right`` on the interior edges is used rather than
    ``int(p * n_bins)``, because the latter misbins values whose binary
    float representation sits a hair below an edge.
    """
    return bisect_right(edges, probability)


def _interior_edges(n_bins: int) -> list[float]:
    return [i / n_bins for i in range(1, n_bins)]


def _group_by_bin(
    cleaned: list[tuple[float, int]], n_bins: int
) -> dict[int, list[tuple[float, int]]]:
    edges = _interior_edges(n_bins)
    groups: dict[int, list[tuple[float, int]]] = {}
    for probability, outcome in cleaned:
        groups.setdefault(_bin_index(probability, edges), []).append(
            (probability, outcome)
        )
    return groups


# --------------------------------------------------------------------------
# proper scoring rules
# --------------------------------------------------------------------------


def brier_score(pairs: Iterable[Any]) -> float:
    """Mean squared error of probabilistic forecasts. Lower is better.

    Reference points: ``0.0`` is a perfect forecaster, ``0.25`` is the
    always-0.5 baseline on any dataset, and ``1.0`` is maximally,
    confidently wrong on every event.

    Args:
        pairs: Iterable of ``(probability, outcome)``.

    Returns:
        The Brier score in ``[0, 1]``.

    Raises:
        ValueError: If the input is empty or malformed.
    """
    cleaned = _validate_pairs(pairs)
    total = math.fsum((p - o) ** 2 for p, o in cleaned)
    return total / len(cleaned)


def brier_skill_score(
    pairs: Iterable[Any], baseline_rate: float | None = None
) -> float:
    """Brier skill relative to a constant baseline forecast.

    ``BSS = 1 - Brier / Brier_baseline``. Positive means the forecaster
    beat the naive constant baseline, ``0.0`` means it matched it, and
    negative means it did worse than simply quoting the base rate every
    time. Unbounded below.

    Args:
        pairs: Iterable of ``(probability, outcome)``.
        baseline_rate: Constant probability the baseline always predicts.
            Defaults to the observed base rate of ``pairs``, which is the
            standard (and hardest to beat) reference.

    Returns:
        The Brier skill score.

    Raises:
        ValueError: On malformed input, a ``baseline_rate`` outside
            ``[0, 1]``, or a degenerate baseline whose own Brier score is
            ``0.0`` (which makes skill mathematically undefined rather
            than infinite -- e.g. every outcome is 1 and the baseline
            predicts 1.0).
    """
    cleaned = _validate_pairs(pairs)
    n = len(cleaned)

    if baseline_rate is None:
        rate = math.fsum(o for _, o in cleaned) / n
    else:
        if isinstance(baseline_rate, bool) or not isinstance(
            baseline_rate, (int, float)
        ):
            raise ValueError(
                f"baseline_rate must be a real number, got {baseline_rate!r}"
            )
        rate = float(baseline_rate)
        if math.isnan(rate) or math.isinf(rate):
            raise ValueError("baseline_rate must be finite")
        if rate < 0.0 or rate > 1.0:
            raise ValueError(
                f"baseline_rate must be in [0, 1], got {baseline_rate!r}"
            )

    baseline_brier = math.fsum((rate - o) ** 2 for _, o in cleaned) / n
    if baseline_brier == 0.0:
        raise ValueError(
            "baseline Brier score is 0.0, so skill is undefined; the "
            "baseline forecast is already perfect for this dataset"
        )
    return 1.0 - (brier_score(cleaned) / baseline_brier)


def log_score(pairs: Iterable[Any], epsilon: float = 1e-15) -> float:
    """Mean logarithmic loss (cross-entropy). Lower is better.

    Probabilities are clamped into ``[epsilon, 1 - epsilon]`` before the
    logarithm, so a confident-and-wrong forecast yields a large finite
    penalty (about 34.5 at the default epsilon) instead of ``inf``, which
    would make the mean useless.

    Args:
        pairs: Iterable of ``(probability, outcome)``.
        epsilon: Clamping bound, must satisfy ``0 < epsilon < 0.5``.

    Returns:
        Mean negative log-likelihood in nats. ``0.0`` only for a perfect,
        fully confident forecaster.

    Raises:
        ValueError: On malformed input or an out-of-range ``epsilon``.
    """
    cleaned = _validate_pairs(pairs)
    if isinstance(epsilon, bool) or not isinstance(epsilon, (int, float)):
        raise ValueError(f"epsilon must be a real number, got {epsilon!r}")
    epsilon = float(epsilon)
    if math.isnan(epsilon) or not (0.0 < epsilon < 0.5):
        raise ValueError(f"epsilon must satisfy 0 < epsilon < 0.5, got {epsilon!r}")

    def term(probability: float, outcome: int) -> float:
        clamped = min(max(probability, epsilon), 1.0 - epsilon)
        return -math.log(clamped) if outcome == 1 else -math.log(1.0 - clamped)

    return math.fsum(term(p, o) for p, o in cleaned) / len(cleaned)


# --------------------------------------------------------------------------
# calibration
# --------------------------------------------------------------------------


def calibration_curve(pairs: Iterable[Any], n_bins: int = 10) -> list[Bin]:
    """Build a reliability diagram: predicted vs. actually observed.

    This is the direct answer to "are my 70% predictions right 70% of the
    time?" -- find the bin covering 0.70 and compare ``mean_predicted``
    against ``observed_frequency``.

    All ``n_bins`` buckets are returned, including empty ones (``count ==
    0``, ``mean_predicted is None``, ``observed_frequency is None``), so
    the curve has a stable shape across datasets and gaps in coverage are
    visible rather than silently dropped.

    Args:
        pairs: Iterable of ``(probability, outcome)``.
        n_bins: Number of equal-width buckets over ``[0, 1]``.

    Returns:
        List of :class:`Bin`, ordered from lowest to highest probability.

    Raises:
        ValueError: On malformed input or ``n_bins < 1``.
    """
    cleaned = _validate_pairs(pairs)
    n_bins = _validate_n_bins(n_bins)
    groups = _group_by_bin(cleaned, n_bins)

    curve: list[Bin] = []
    for index in range(n_bins):
        members = groups.get(index, [])
        lower = index / n_bins
        upper = (index + 1) / n_bins
        if members:
            count = len(members)
            mean_predicted = math.fsum(p for p, _ in members) / count
            observed = math.fsum(o for _, o in members) / count
            curve.append(Bin(lower, upper, count, mean_predicted, observed))
        else:
            curve.append(Bin(lower, upper, 0, None, None))
    return curve


def expected_calibration_error(
    pairs: Iterable[Any], n_bins: int = 10
) -> float:
    """Count-weighted mean calibration gap across non-empty bins.

    ``ECE = sum_k (n_k / N) * |mean_predicted_k - observed_frequency_k|``.
    ``0.0`` means every bucket's forecasts matched their realized
    frequency exactly. Lower is better.

    Note that ECE measures calibration *only*. A forecaster that always
    predicts the true base rate scores a near-perfect ECE while carrying
    no information at all, so ECE must never be read as accuracy.

    Args:
        pairs: Iterable of ``(probability, outcome)``.
        n_bins: Number of equal-width buckets over ``[0, 1]``.

    Returns:
        The expected calibration error in ``[0, 1]``.

    Raises:
        ValueError: On malformed input or ``n_bins < 1``.
    """
    cleaned = _validate_pairs(pairs)
    n_bins = _validate_n_bins(n_bins)
    n = len(cleaned)
    total = math.fsum(
        b.count * abs(b.mean_predicted - b.observed_frequency)
        for b in calibration_curve(cleaned, n_bins)
        if b.count > 0
    )
    return total / n


def murphy_decomposition(
    pairs: Iterable[Any], n_bins: int = 10
) -> dict[str, Any]:
    """Decompose the Brier score into reliability, resolution, uncertainty.

    The classic Murphy (1973) identity is::

        Brier = reliability - resolution + uncertainty

    where, over bins ``k`` with ``n_k`` members, bin mean forecast
    ``p_k``, bin observed frequency ``o_k``, and overall base rate ``o``:

    * ``reliability  = (1/N) * sum_k n_k * (p_k - o_k)^2`` -- calibration
      error. **Lower is better**; 0 means each bucket's forecasts matched
      reality.
    * ``resolution   = (1/N) * sum_k n_k * (o_k - o)^2`` -- discrimination.
      **Higher is better**; 0 means the buckets are indistinguishable from
      the base rate, i.e. the forecasts carry no information.
    * ``uncertainty  = o * (1 - o)`` -- irreducible base-rate variance. A
      property of the events, not of the forecaster. Not improvable.

    **The subtlety that makes or breaks this function:** that three-term
    identity is exact only when every forecast inside a bin is identical
    (Murphy's original setting of finitely many forecast values). With
    continuous forecasts collapsed into fixed-width bins, replacing each
    forecast by its bin mean introduces a discretization residual, and the
    three terms miss the true Brier score by a small but very real amount
    -- empirically ~6e-4 on 500 uniform forecasts in 10 bins, which is
    six orders of magnitude larger than a 1e-9 tolerance. Rather than
    hide that, the exact residual is returned as ``within_bin_error``::

        Brier = reliability - resolution + uncertainty + within_bin_error

    which closes to floating-point precision *always*, and
    ``within_bin_error`` is exactly ``0.0`` whenever binning is lossless.
    Derivation, writing ``d_i = p_i - p_k`` within bin ``k`` (so
    ``sum_i d_i = 0``)::

        within_bin_error = (1/N) * sum_k sum_i [ d_i^2 - 2*d_i*(o_i - o_k) ]

    It is a signed residual, not a variance, and may be negative.

    Args:
        pairs: Iterable of ``(probability, outcome)``.
        n_bins: Number of equal-width buckets over ``[0, 1]``.

    Returns:
        Dict with keys ``brier``, ``reliability``, ``resolution``,
        ``uncertainty``, ``within_bin_error``, ``identity_residual``
        (Brier minus the reconstructed four-term sum, ~1e-16),
        ``base_rate``, ``n``, ``n_bins`` and ``n_bins_occupied``.

    Raises:
        ValueError: On malformed input or ``n_bins < 1``.
    """
    cleaned = _validate_pairs(pairs)
    n_bins = _validate_n_bins(n_bins)
    n = len(cleaned)

    base_rate = math.fsum(o for _, o in cleaned) / n
    groups = _group_by_bin(cleaned, n_bins)

    reliability_terms: list[float] = []
    resolution_terms: list[float] = []
    within_terms: list[float] = []

    for members in groups.values():
        count = len(members)
        mean_predicted = math.fsum(p for p, _ in members) / count
        observed = math.fsum(o for _, o in members) / count

        reliability_terms.append(count * (mean_predicted - observed) ** 2)
        resolution_terms.append(count * (observed - base_rate) ** 2)

        for probability, outcome in members:
            deviation = probability - mean_predicted
            within_terms.append(
                deviation * deviation - 2.0 * deviation * (outcome - observed)
            )

    reliability = math.fsum(reliability_terms) / n
    resolution = math.fsum(resolution_terms) / n
    uncertainty = base_rate * (1.0 - base_rate)
    within_bin_error = math.fsum(within_terms) / n

    brier = brier_score(cleaned)
    reconstructed = reliability - resolution + uncertainty + within_bin_error

    return {
        "brier": brier,
        "reliability": reliability,
        "resolution": resolution,
        "uncertainty": uncertainty,
        "within_bin_error": within_bin_error,
        "identity_residual": brier - reconstructed,
        "base_rate": base_rate,
        "n": n,
        "n_bins": n_bins,
        "n_bins_occupied": len(groups),
    }


# --------------------------------------------------------------------------
# discrimination
# --------------------------------------------------------------------------


def auc_roc(pairs: Iterable[Any]) -> float:
    """Area under the ROC curve, via the Mann-Whitney U equivalence.

    AUC is the probability that a randomly chosen event that *did* occur
    received a higher forecast than a randomly chosen event that did not,
    counting **tied forecasts as one half**. ``1.0`` is perfect ranking,
    ``0.5`` is no discriminating ability, and ``0.0`` is perfectly
    inverted (which is just as informative as 1.0, but sign-flipped).

    Computed with midranks::

        AUC = (R_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)

    where ``R_pos`` is the sum of the *average* ranks of the positive
    class. Assigning tied forecasts their mean rank is what makes ties
    contribute exactly 0.5 each; the common shortcut of using ordinal
    ranks, or of counting only strict ``>`` comparisons, silently scores a
    block of identical predictions as 0.0 or 1.0 instead of 0.5. Runs in
    O(n log n) rather than the O(n^2) pairwise double loop.

    Args:
        pairs: Iterable of ``(probability, outcome)``.

    Returns:
        The AUC in ``[0, 1]``.

    Raises:
        ValueError: On malformed input, or if the outcomes are all 0 or
            all 1. AUC is genuinely undefined with only one class present
            -- there are no pairs to rank -- so this raises instead of
            returning a plausible-looking 0.5.
    """
    cleaned = _validate_pairs(pairs)

    n_pos = sum(1 for _, o in cleaned if o == 1)
    n_neg = len(cleaned) - n_pos
    if n_pos == 0 or n_neg == 0:
        raise ValueError(
            "auc_roc requires at least one positive and one negative "
            f"outcome, got {n_pos} positive and {n_neg} negative"
        )

    ordered = sorted(cleaned, key=lambda item: item[0])

    # Midranks: every member of a tied block receives the mean of the
    # ordinal ranks that block spans.
    rank_sum_positive = 0.0
    index = 0
    total = len(ordered)
    while index < total:
        end = index + 1
        while end < total and ordered[end][0] == ordered[index][0]:
            end += 1
        # Ranks are 1-based: this block occupies ranks index+1 .. end.
        average_rank = (index + 1 + end) / 2.0
        positives_in_block = sum(1 for _, o in ordered[index:end] if o == 1)
        rank_sum_positive += average_rank * positives_in_block
        index = end

    u_statistic = rank_sum_positive - n_pos * (n_pos + 1) / 2.0
    return u_statistic / (n_pos * n_neg)

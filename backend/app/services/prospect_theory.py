"""
Cumulative Prospect Theory (CPT) -- Tversky & Kahneman (1992).

A standalone, dependency-free implementation of the canonical CPT decision
model. This module deliberately imports NOTHING from ``app.*``, no Flask, no
LLM clients and performs no I/O or network access. It depends only on the
Python standard library (``math``, ``dataclasses``, ``typing``) so that it can
be imported, unit-tested and reasoned about in complete isolation.

Reference
---------
Tversky, A., & Kahneman, D. (1992). "Advances in Prospect Theory: Cumulative
Representation of Uncertainty." Journal of Risk and Uncertainty, 5(4), 297-323.

The model has three moving parts:

1. A *reference point*. Outcomes are not evaluated in absolute terms but as
   deviations from a reference point. This is the core insight of the theory:
   the very same absolute outcome is a gain or a loss depending only on where
   the reference sits. Moving the reference across an outcome flips the sign of
   its subjective value (framing).

2. A *value function* that is concave for gains, convex for losses, and
   steeper for losses than for gains (loss aversion)::

       v(x) =  x ** alpha                for x >= 0
       v(x) = -lambda_ * (-x) ** beta    for x <  0

   Median estimates from TK92: alpha = beta = 0.88, lambda_ = 2.25.

3. A *probability weighting function* that overweights small probabilities and
   underweights moderate-to-large ones::

       w(p) = p**g / (p**g + (1 - p)**g) ** (1 / g)

   Median estimates from TK92: g = 0.61 on the gain side, g = 0.69 on the loss
   side (here named ``gamma`` and ``delta``).

Weighting is applied in the *cumulative* (rank-dependent) form, which is what
makes this CPT rather than the 1979 "original prospect theory". Gains are
ranked from best to worst and losses from worst to best; each outcome's
decision weight is the increment of the weighting function over the cumulative
probability up to that outcome. This construction is what keeps the model from
violating stochastic dominance.

Public API
----------
- ``Prospect``                -- dataclass: outcomes, probabilities, label
- ``PTParams``                -- dataclass: alpha, beta, lambda_, gamma, delta
- ``value(x, params)``        -- the value function v(x)
- ``weight(p, gamma)``        -- the probability weighting function w(p)
- ``evaluate_prospect(prospect, reference_point, params)`` -> subjective value
- ``choose(prospects, reference_point, params, temperature)`` -> choice probs
- ``params_from_big_five(...)`` -> PTParams modulated by personality
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence

__all__ = [
    "PROBABILITY_TOLERANCE",
    "PTParams",
    "Prospect",
    "value",
    "weight",
    "evaluate_prospect",
    "choose",
    "params_from_big_five",
]


# Probabilities must sum to 1 within this absolute tolerance.
PROBABILITY_TOLERANCE = 1e-6

# Below roughly this value the one-parameter TK92 weighting function stops
# being monotonically increasing in p, which makes it a nonsensical weighting
# function. Ingersoll (2008) puts the threshold at ~0.279. We reject smaller
# curvature parameters rather than silently returning garbage.
_MIN_WEIGHTING_CURVATURE = 0.28


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PTParams:
    """
    Cumulative prospect theory parameters.

    Defaults are the median estimates reported by Tversky & Kahneman (1992).

    Attributes
    ----------
    alpha:
        Curvature of the value function for gains. ``alpha < 1`` produces
        diminishing sensitivity (concavity) and therefore risk aversion for
        moderate-to-high probability gains.
    beta:
        Curvature of the value function for losses. ``beta < 1`` produces
        convexity and therefore risk seeking for moderate-to-high probability
        losses.
    lambda_:
        Loss aversion coefficient. ``lambda_ > 1`` makes losses loom larger
        than commensurate gains.
    gamma:
        Curvature of the probability weighting function on the gain side.
    delta:
        Curvature of the probability weighting function on the loss side.
    """

    alpha: float = 0.88
    beta: float = 0.88
    lambda_: float = 2.25
    gamma: float = 0.61
    delta: float = 0.69

    def __post_init__(self) -> None:
        for name in ("alpha", "beta"):
            val = getattr(self, name)
            if not (val > 0.0):
                raise ValueError(f"{name} must be > 0, got {val!r}")
        if not (self.lambda_ > 0.0):
            raise ValueError(f"lambda_ must be > 0, got {self.lambda_!r}")
        for name in ("gamma", "delta"):
            val = getattr(self, name)
            if not (val >= _MIN_WEIGHTING_CURVATURE):
                raise ValueError(
                    f"{name} must be >= {_MIN_WEIGHTING_CURVATURE} to keep the "
                    f"weighting function monotonic, got {val!r}"
                )
            if val > 1.0:
                # Values above 1 invert the characteristic inverse-S shape.
                # Permitted but unusual, so no error -- documented instead.
                pass


# ---------------------------------------------------------------------------
# Prospects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Prospect:
    """
    A lottery over absolute outcomes.

    ``outcomes`` are stated in *absolute* terms (e.g. final wealth, final
    headcount, final poll share). They are converted into gains and losses at
    evaluation time by subtracting the reference point, which is what lets the
    same prospect be evaluated from different frames.

    Raises
    ------
    ValueError
        If the lengths disagree, if any probability is outside [0, 1], or if
        the probabilities do not sum to 1 within ``PROBABILITY_TOLERANCE``.
    """

    outcomes: List[float]
    probabilities: List[float]
    label: str = "prospect"

    def __post_init__(self) -> None:
        if len(self.outcomes) != len(self.probabilities):
            raise ValueError(
                "outcomes and probabilities must have the same length: "
                f"got {len(self.outcomes)} outcomes and "
                f"{len(self.probabilities)} probabilities"
            )
        if not self.outcomes:
            raise ValueError("a prospect must have at least one outcome")

        for p in self.probabilities:
            if not math.isfinite(p):
                raise ValueError(f"probabilities must be finite, got {p!r}")
            if p < 0.0 or p > 1.0:
                raise ValueError(f"probabilities must lie in [0, 1], got {p!r}")

        for x in self.outcomes:
            if not math.isfinite(x):
                raise ValueError(f"outcomes must be finite, got {x!r}")

        total = math.fsum(self.probabilities)
        if abs(total - 1.0) > PROBABILITY_TOLERANCE:
            raise ValueError(
                f"probabilities must sum to 1.0 (tolerance "
                f"{PROBABILITY_TOLERANCE}), got {total!r}"
            )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def value(x: float, params: PTParams | None = None) -> float:
    """
    The CPT value function evaluated at a *reference-relative* outcome.

    ``x`` is already a deviation from the reference point: positive means gain,
    negative means loss.

        v(x) =  x ** alpha                for x >= 0
        v(x) = -lambda_ * (-x) ** beta    for x <  0

    The kink at zero (slope ratio ``lambda_``) is loss aversion.
    """
    if params is None:
        params = PTParams()
    if not math.isfinite(x):
        raise ValueError(f"x must be finite, got {x!r}")

    if x >= 0.0:
        return float(x ** params.alpha)
    return float(-params.lambda_ * ((-x) ** params.beta))


def weight(p: float, gamma: float = 0.61) -> float:
    """
    The one-parameter Tversky-Kahneman (1992) probability weighting function.

        w(p) = p**gamma / (p**gamma + (1 - p)**gamma) ** (1 / gamma)

    With ``gamma < 1`` this is inverse-S shaped: small probabilities are
    overweighted (w(p) > p) and moderate-to-large probabilities underweighted.
    ``w(0) = 0`` and ``w(1) = 1`` exactly.

    Pass ``params.gamma`` for gain-side weighting and ``params.delta`` for
    loss-side weighting.
    """
    if not math.isfinite(p):
        raise ValueError(f"p must be finite, got {p!r}")
    if p < 0.0 or p > 1.0:
        raise ValueError(f"p must lie in [0, 1], got {p!r}")
    if not (gamma >= _MIN_WEIGHTING_CURVATURE):
        raise ValueError(
            f"gamma must be >= {_MIN_WEIGHTING_CURVATURE} to keep the "
            f"weighting function monotonic, got {gamma!r}"
        )

    # Endpoints are pinned analytically; this also avoids 0**gamma edge cases.
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0

    num = p ** gamma
    den = (num + (1.0 - p) ** gamma) ** (1.0 / gamma)
    return float(num / den)


def evaluate_prospect(
    prospect: Prospect,
    reference_point: float = 0.0,
    params: PTParams | None = None,
) -> float:
    """
    Subjective value of ``prospect`` seen from ``reference_point``.

    Uses the cumulative (rank-dependent) representation:

    * Outcomes are shifted to reference-relative terms, then split into a gain
      branch (>= 0) and a loss branch (< 0).
    * Gains are ranked best -> worst. The decision weight of the i-th ranked
      gain is ``w+(P_i) - w+(P_{i-1})`` where ``P_i`` is the cumulative
      probability of outcomes at least as good as the i-th.
    * Losses are ranked worst -> best, with the mirror-image construction
      using ``w-``.
    * The two branches are summed.

    Duplicate probabilities and duplicate outcomes are handled correctly
    because the construction telescopes over the sorted cumulative sums.

    A note on interpreting the output: ``lambda_`` is *not* the behavioural
    loss-aversion ratio. Because the loss branch is weighted with ``delta`` and
    the gain branch with ``gamma``, and because ``delta > gamma`` in the TK92
    estimates, a 50/50 mixed gamble gives the loss more decision weight than
    the gain (0.4540 vs 0.4206). Combined with concavity in gains, the
    canonical parameters imply an indifference point around 2.74x rather than
    2.25x for "win X vs lose 100". That is a genuine prediction of cumulative
    PT, not a bug.
    """
    if params is None:
        params = PTParams()
    if not math.isfinite(reference_point):
        raise ValueError(
            f"reference_point must be finite, got {reference_point!r}"
        )

    relative = [
        (float(x) - float(reference_point), float(p))
        for x, p in zip(prospect.outcomes, prospect.probabilities)
    ]

    gains = [(x, p) for x, p in relative if x >= 0.0 and p > 0.0]
    losses = [(x, p) for x, p in relative if x < 0.0 and p > 0.0]

    total = 0.0

    # Gain branch: rank from the best outcome downwards.
    gains.sort(key=lambda item: item[0], reverse=True)
    cumulative = 0.0
    prev_w = 0.0
    for x, p in gains:
        cumulative += p
        # Guard against tiny floating point overshoot past 1.0.
        cum = min(cumulative, 1.0)
        cur_w = weight(cum, params.gamma)
        total += (cur_w - prev_w) * value(x, params)
        prev_w = cur_w

    # Loss branch: rank from the worst outcome upwards.
    losses.sort(key=lambda item: item[0])
    cumulative = 0.0
    prev_w = 0.0
    for x, p in losses:
        cumulative += p
        cum = min(cumulative, 1.0)
        cur_w = weight(cum, params.delta)
        total += (cur_w - prev_w) * value(x, params)
        prev_w = cur_w

    return float(total)


def choose(
    prospects: Sequence[Prospect],
    reference_point: float = 0.0,
    params: PTParams | None = None,
    temperature: float = 1.0,
) -> Dict[str, float]:
    """
    Softmax choice probabilities over ``prospects``.

    Returns a mapping ``label -> probability``; the values sum to 1.0.

    ``temperature`` controls determinism: as it approaches 0 the choice becomes
    the argmax of subjective value, and as it grows the choice approaches
    uniform. Note that CPT subjective values inherit the *units* of the
    outcomes, so a sensible temperature scales with the size of the payoffs --
    a temperature of 1.0 against payoffs in the hundreds is effectively
    deterministic.

    Raises
    ------
    ValueError
        If ``prospects`` is empty, labels are duplicated, or temperature <= 0.
    """
    if params is None:
        params = PTParams()
    if not prospects:
        raise ValueError("prospects must not be empty")
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError(f"temperature must be > 0, got {temperature!r}")

    labels = [p.label for p in prospects]
    if len(set(labels)) != len(labels):
        raise ValueError(f"prospect labels must be unique, got {labels!r}")

    values = [
        evaluate_prospect(p, reference_point=reference_point, params=params)
        for p in prospects
    ]

    # Numerically stable softmax: subtract the max before exponentiating.
    scaled = [v / temperature for v in values]
    top = max(scaled)
    exps = [math.exp(s - top) for s in scaled]
    denominator = math.fsum(exps)

    return {
        label: float(e / denominator) for label, e in zip(labels, exps)
    }


# ---------------------------------------------------------------------------
# Personality -> parameters
# ---------------------------------------------------------------------------


def _clamp(x: float, low: float, high: float) -> float:
    return low if x < low else (high if x > high else x)


def params_from_big_five(
    openness: float = 0.5,
    conscientiousness: float = 0.5,
    extraversion: float = 0.5,
    agreeableness: float = 0.5,
    neuroticism: float = 0.5,
) -> PTParams:
    """
    Derive CPT parameters from Big Five trait scores.

    All five inputs are normalised trait scores in ``[0, 1]``, where 0.5 is the
    population-average trait level. At the neutral input (all traits 0.5) this
    function returns exactly the canonical TK92 defaults, so personality acts
    purely as a perturbation of the published parameters.

    EPISTEMIC STATUS OF EACH MAPPING
    ================================
    Be careful here. Only the first mapping has meaningful empirical support;
    the rest are explicitly labelled design assumptions. None of these should
    be presented to a user as an established psychometric result.

    1. neuroticism -> lambda_ (loss aversion).  *BEST SUPPORTED.*
       Neuroticism is the trait most consistently tied to heightened
       sensitivity to negative outcomes, threat and punishment. There is a
       reasonable literature linking trait negative affectivity / neuroticism
       to stronger loss aversion and greater risk avoidance. Caveats that
       matter: reported effect sizes are small, several studies fail to
       replicate, and behavioural loss-aversion estimates are themselves
       noisy at the individual level. So the *direction* here is
       defensible; the exact slope is not.

    2. extraversion -> alpha (gain-side curvature).  *DESIGN ASSUMPTION.*
       Motivated by the reward-sensitivity / BAS account of extraversion:
       more extraverted agents are modelled as showing slightly less
       diminishing sensitivity to larger gains (alpha nearer 1). This is a
       plausible reading of reward-sensitivity work, not a measured
       alpha-extraversion coefficient. Treat as invented.

    3. openness -> gamma (gain-side probability weighting). *DESIGN ASSUMPTION.*
       Modelled so that higher openness means less distortion of gain
       probabilities (gamma nearer 1), on the loose rationale that openness
       correlates with cognitive reflection and deliberate probability use.
       We are not aware of a direct empirical estimate. Treat as invented.

    4. conscientiousness -> delta (loss-side probability weighting).
       *DESIGN ASSUMPTION.* Modelled so that higher conscientiousness means
       *more* overweighting of low-probability losses, i.e. the
       planning/insurance-buying tendency. Directionally intuitive,
       empirically unestablished. Treat as invented.

    5. agreeableness -> nothing.  *DELIBERATELY UNMAPPED.*
       We found no defensible link between agreeableness and any CPT
       parameter in an individual (non-social) risky-choice task. Rather than
       invent one for symmetry, agreeableness is accepted and ignored. The
       parameter is kept in the signature so callers can pass a full Big Five
       vector without special-casing.

    All perturbations are intentionally MODEST -- the resulting agent is still
    recognisably a TK92 decision maker, not a caricature. Ranges after
    clamping:

        lambda_ in [1.80, 2.80]   (canonical 2.25)
        alpha   in [0.82, 0.94]   (canonical 0.88)
        gamma   in [0.55, 0.70]   (canonical 0.61)
        delta   in [0.60, 0.78]   (canonical 0.69)

    ``beta`` (loss-side curvature) is left at the canonical value: we have no
    even-plausible trait story for it, and TK92 could not distinguish it from
    ``alpha`` empirically anyway.
    """
    traits = {
        "openness": openness,
        "conscientiousness": conscientiousness,
        "extraversion": extraversion,
        "agreeableness": agreeableness,
        "neuroticism": neuroticism,
    }
    for name, val in traits.items():
        if not math.isfinite(val):
            raise ValueError(f"{name} must be finite, got {val!r}")
        if val < 0.0 or val > 1.0:
            raise ValueError(
                f"{name} must be a normalised score in [0, 1], got {val!r}"
            )

    base = PTParams()

    # (1) Loss aversion rises with neuroticism. Slope 1.1 over the unit trait
    #     range, centred on the canonical 2.25, then clamped to [1.8, 2.8].
    lambda_ = _clamp(base.lambda_ + (neuroticism - 0.5) * 1.1, 1.8, 2.8)

    # (2) Gain-side curvature rises (less diminishing sensitivity) with
    #     extraversion. DESIGN ASSUMPTION.
    alpha = _clamp(base.alpha + (extraversion - 0.5) * 0.12, 0.82, 0.94)

    # (3) Gain-side probability distortion shrinks with openness (gamma -> 1
    #     means no distortion). DESIGN ASSUMPTION.
    gamma = _clamp(base.gamma + (openness - 0.5) * 0.15, 0.55, 0.70)

    # (4) Loss-side probability distortion grows with conscientiousness, i.e.
    #     lower delta = more overweighting of rare losses. DESIGN ASSUMPTION.
    delta = _clamp(base.delta - (conscientiousness - 0.5) * 0.18, 0.60, 0.78)

    return PTParams(
        alpha=alpha,
        beta=base.beta,
        lambda_=lambda_,
        gamma=gamma,
        delta=delta,
    )

"""Rogers' Diffusion of Innovations + Bass diffusion, as a standalone module.

This module is deliberately dependency-free: standard library + ``math`` only.
It performs no I/O, imports nothing from ``app.*``, touches no Flask context,
and makes no network calls. Everything is a pure function over plain data, so it
can be unit-tested in isolation and reused from any layer.

Three families of behaviour live here:

1. **Rogers' adopter categorisation** (:func:`classify_population`) --
   assigns each persona to one of five adopter categories whose *population
   shares* reproduce Rogers' canonical normal-curve partition.
2. **Bass diffusion** (:func:`bass_adoption_curve`) -- the aggregate
   macro-level S-curve driven by a coefficient of innovation ``p`` (external /
   mass-media influence) and a coefficient of imitation ``q`` (internal /
   word-of-mouth influence).
3. **Linear-threshold network contagion** (:func:`propagate`,
   :func:`simulate_contagion`) -- the micro-level counterpart, where an
   individual adopts once a sufficient fraction of its neighbours have adopted.
   Thresholds are derived from the Rogers category, which is what ties (1) and
   (3) together.

References
----------
* Rogers, E. M. (2003). *Diffusion of Innovations* (5th ed.). Free Press.
  Chapter 7 defines the five adopter categories and the canonical shares used
  in :data:`CATEGORY_SHARES` (partition of a normal curve at the mean and at
  1 and 2 standard deviations below/above it).
* Bass, F. M. (1969). "A New Product Growth for Model Consumer Durables."
  *Management Science*, 15(5), 215-227.
* Bass, F. M. (2004). "Comments on 'A New Product Growth for Model Consumer
  Durables'." *Management Science*, 50(12), 1833-1840.
* Sultan, F., Farley, J. U., & Lehmann, D. R. (1990). "A Meta-Analysis of
  Applications of Diffusion Models." *Journal of Marketing Research*, 27(1),
  70-77.
* Granovetter, M. (1978). "Threshold Models of Collective Behavior."
  *American Journal of Sociology*, 83(6), 1420-1443.
* Kempe, D., Kleinberg, J., & Tardos, E. (2003). "Maximizing the Spread of
  Influence through a Social Network." *KDD '03*.
"""

from __future__ import annotations

import hashlib
import math
from enum import Enum
from fractions import Fraction
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

__all__ = [
    "AdopterCategory",
    "CATEGORY_SHARES",
    "CATEGORY_ORDER",
    "CATEGORY_THRESHOLDS",
    "DEFAULT_THRESHOLD",
    "TYPICAL_P",
    "TYPICAL_Q",
    "P_EMPIRICAL_RANGE",
    "Q_EMPIRICAL_RANGE",
    "innovativeness_score",
    "classify_population",
    "category_counts",
    "bass_adoption_curve",
    "bass_incremental_adopters",
    "bass_peak_time",
    "thresholds_from_categories",
    "propagate",
    "simulate_contagion",
    "adjacency_from_edges",
    "adjacency_from_networkx",
]


# ---------------------------------------------------------------------------
# 1. Rogers' adopter categories
# ---------------------------------------------------------------------------


class AdopterCategory(Enum):
    """Rogers' five adopter categories, ordered earliest -> latest.

    The ``value`` is the adoption *rank* (0 = adopts earliest), so categories
    compare naturally: ``AdopterCategory.INNOVATOR.value < AdopterCategory.LAGGARD.value``.
    """

    INNOVATOR = 0
    EARLY_ADOPTER = 1
    EARLY_MAJORITY = 2
    LATE_MAJORITY = 3
    LAGGARD = 4

    @property
    def share(self) -> float:
        """Canonical share of the population in this category."""
        return CATEGORY_SHARES[self]

    def threshold(self) -> float:
        """Canonical linear-threshold value for this category."""
        return CATEGORY_THRESHOLDS[self]


#: Earliest -> latest adoption order.
CATEGORY_ORDER: Tuple[AdopterCategory, ...] = (
    AdopterCategory.INNOVATOR,
    AdopterCategory.EARLY_ADOPTER,
    AdopterCategory.EARLY_MAJORITY,
    AdopterCategory.LATE_MAJORITY,
    AdopterCategory.LAGGARD,
)

# Exact rational shares. Rogers partitions the normal curve of innovativeness
# at mean - 2sd (2.5%), mean - 1sd (13.5%), mean (34%), mean + 1sd (34%) and
# the remaining tail (16%). Kept as Fractions so the integer allocation in
# classify_population() is exact rather than floating-point-approximate.
_CATEGORY_SHARES_EXACT: Dict[AdopterCategory, Fraction] = {
    AdopterCategory.INNOVATOR: Fraction(25, 1000),  # 2.5%
    AdopterCategory.EARLY_ADOPTER: Fraction(135, 1000),  # 13.5%
    AdopterCategory.EARLY_MAJORITY: Fraction(340, 1000),  # 34.0%
    AdopterCategory.LATE_MAJORITY: Fraction(340, 1000),  # 34.0%
    AdopterCategory.LAGGARD: Fraction(160, 1000),  # 16.0%
}

#: Canonical population shares as floats (what callers normally want).
CATEGORY_SHARES: Dict[AdopterCategory, float] = {
    category: float(share) for category, share in _CATEGORY_SHARES_EXACT.items()
}

# The shares must partition the population exactly. Asserted on the exact
# rational representation (a true equality), and on the float representation
# with a tolerance, because 0.025 + 0.135 + 0.34 + 0.34 + 0.16 is not
# necessarily exactly 1.0 in binary floating point.
assert sum(_CATEGORY_SHARES_EXACT.values()) == Fraction(1), (
    "Rogers adopter category shares must sum to exactly 1"
)
assert math.isclose(sum(CATEGORY_SHARES.values()), 1.0, rel_tol=0.0, abs_tol=1e-12), (
    "Rogers adopter category shares must sum to 1.0"
)
assert set(CATEGORY_ORDER) == set(AdopterCategory), "CATEGORY_ORDER must cover every category"


#: Linear-threshold values per category: the fraction of a node's neighbours
#: that must have adopted before the node adopts. Innovators are
#: *venturesome* and adopt with no social proof at all (0.0 -> spontaneous);
#: laggards are *traditional* and need most of their network on board first.
CATEGORY_THRESHOLDS: Dict[AdopterCategory, float] = {
    AdopterCategory.INNOVATOR: 0.00,
    AdopterCategory.EARLY_ADOPTER: 0.10,
    AdopterCategory.EARLY_MAJORITY: 0.25,
    AdopterCategory.LATE_MAJORITY: 0.50,
    AdopterCategory.LAGGARD: 0.75,
}

#: Threshold used for a node with no entry in the thresholds mapping.
DEFAULT_THRESHOLD: float = 0.5


# ---------------------------------------------------------------------------
# 1a. Innovativeness scoring
# ---------------------------------------------------------------------------

# Personas arrive as plain mappings on purpose: this module must not import
# OasisAgentProfile (or any other app schema), so it discovers Big Five traits
# by probing a set of conventional key spellings instead.
_TRAIT_CONTAINER_KEYS: Tuple[str, ...] = (
    "big_five",
    "bigfive",
    "big5",
    "ocean",
    "personality",
    "personality_traits",
    "traits",
    "psychographics",
)

_TRAIT_ALIASES: Dict[str, Tuple[str, ...]] = {
    "openness": ("openness", "openness_to_experience", "open", "o"),
    "conscientiousness": ("conscientiousness", "conscientious", "c"),
    "extraversion": ("extraversion", "extroversion", "extravert", "e"),
    "agreeableness": ("agreeableness", "agreeable", "a"),
    "neuroticism": ("neuroticism", "neurotic", "n"),
}

# Explicit innovativeness overrides, checked before the Big Five fallback chain.
_INNOVATIVENESS_ALIASES: Tuple[str, ...] = (
    "innovativeness",
    "innovativeness_score",
    "innovation_score",
    "novelty_seeking",
)

# Weak proxies used only when no Big Five data is present at all. Each maps to
# (aliases, weight, invert) -- ``invert`` flips the normalised value so that
# "higher raw value means later adoption" proxies still point the right way.
_PROXY_SPECS: Tuple[Tuple[Tuple[str, ...], float, bool], ...] = (
    (("tech_savviness", "tech_savvy", "technology_affinity", "digital_literacy"), 0.5, False),
    (("education_level", "education"), 0.2, False),
    (("risk_tolerance", "risk_appetite"), 0.2, False),
    (("age",), 0.1, True),
)

# Big Five weighting. Rogers characterises innovativeness as venturesomeness
# and cosmopoliteness, both of which load onto Openness -- hence the dominant
# weight. Extraversion contributes because social participation and
# interconnectedness predict earlier adoption, and Neuroticism subtracts
# because risk aversion delays it. The weights are chosen so that Openness
# alone determines the ordering whenever the other traits are equal.
_OPENNESS_WEIGHT = 0.70
_EXTRAVERSION_WEIGHT = 0.20
_NEUROTICISM_WEIGHT = 0.10  # applied to (1 - neuroticism)

# Age is normalised against this span when used as a weak proxy.
_MAX_PLAUSIBLE_AGE = 100.0

# Candidate upper bounds for trait scales seen in the wild (0-1, 1-5 Likert,
# 0-10, 0-100 percentile).
_SCALE_CANDIDATES: Tuple[float, ...] = (1.0, 5.0, 10.0, 100.0)


def _coerce_float(value: Any) -> Optional[float]:
    """Best-effort numeric coercion. Returns ``None`` for non-numeric input."""
    if isinstance(value, bool):
        # bool is an int subclass; treat it as a 0/1 numeric value.
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        result = float(value)
        return result if math.isfinite(result) else None
    if isinstance(value, str):
        try:
            result = float(value.strip())
        except ValueError:
            return None
        return result if math.isfinite(result) else None
    return None


def _lookup(mapping: Mapping[str, Any], aliases: Iterable[str]) -> Optional[float]:
    """Find the first numeric value among ``aliases`` (case-insensitive)."""
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for alias in aliases:
        if alias in lowered:
            coerced = _coerce_float(lowered[alias])
            if coerced is not None:
                return coerced
    return None


def _candidate_scopes(persona: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    """Return the persona itself plus any nested trait containers."""
    scopes: List[Mapping[str, Any]] = [persona]
    for key, value in persona.items():
        if str(key).lower() in _TRAIT_CONTAINER_KEYS and isinstance(value, Mapping):
            scopes.append(value)
    return scopes


def _raw_traits(persona: Mapping[str, Any]) -> Dict[str, float]:
    """Extract whatever Big Five traits are present, un-normalised."""
    traits: Dict[str, float] = {}
    # Nested containers are probed first so an explicit big_five block wins
    # over a same-named top-level key.
    for scope in reversed(_candidate_scopes(persona)):
        for trait, aliases in _TRAIT_ALIASES.items():
            found = _lookup(scope, aliases)
            if found is not None:
                traits[trait] = found
    return traits


def _infer_scale(values: Sequence[float]) -> float:
    """Infer the upper bound of the trait scale from observed values.

    Inferring once for the whole population (rather than per value) matters:
    a per-value heuristic would map ``4`` on a 1-5 Likert scale to 0.8 and
    ``7`` on a 0-10 scale to 0.7, silently inverting the ordering of two
    personas. A single shared divisor cannot do that.
    """
    if not values:
        return 1.0
    observed_max = max(abs(value) for value in values)
    for candidate in _SCALE_CANDIDATES:
        if observed_max <= candidate:
            return candidate
    return observed_max if observed_max > 0 else 1.0


def _clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else (1.0 if value > 1.0 else value)


def _stable_pseudo_score(persona: Mapping[str, Any], identifier: Hashable) -> float:
    """Deterministic tie-breaker in [0, 1) for personas with no usable signal.

    Uses SHA-256 rather than :func:`hash` so results are stable across
    processes regardless of ``PYTHONHASHSEED``.
    """
    del persona  # identity is the only stable thing we can rely on
    digest = hashlib.sha256(repr(identifier).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def innovativeness_score(
    persona: Mapping[str, Any],
    scale: Optional[float] = None,
    identifier: Hashable = None,
) -> float:
    """Score a persona's innovativeness in ``[0, 1]`` (higher = adopts earlier).

    Driven primarily by **Openness** when Big Five data is present. Degrades
    gracefully otherwise:

    1. Big Five present -> weighted Openness / Extraversion / (1 - Neuroticism).
    2. Explicit ``innovativeness``-style key -> used directly.
    3. Weak proxies (tech savviness, education, risk tolerance, age).
    4. Nothing usable -> deterministic pseudo-score from ``identifier``, so the
       ranking is stable across runs instead of arbitrary.

    ``scale`` is the upper bound of the trait scale (e.g. ``5.0`` for a 1-5
    Likert scale). When ``None`` it is inferred from this persona's own values,
    which is why :func:`classify_population` infers it population-wide and
    passes it in explicitly.
    """
    if not isinstance(persona, Mapping):
        raise TypeError(f"persona must be a Mapping, got {type(persona).__name__}")

    traits = _raw_traits(persona)
    if traits:
        divisor = scale if scale is not None else _infer_scale(list(traits.values()))
        divisor = divisor or 1.0
        normalised = {name: _clamp01(value / divisor) for name, value in traits.items()}

        if "openness" in normalised:
            openness = normalised["openness"]
            extraversion = normalised.get("extraversion", 0.5)
            neuroticism = normalised.get("neuroticism", 0.5)
            score = (
                _OPENNESS_WEIGHT * openness
                + _EXTRAVERSION_WEIGHT * extraversion
                + _NEUROTICISM_WEIGHT * (1.0 - neuroticism)
            )
            return _clamp01(score)

        # Big Five present but Openness missing: average the usable signals.
        signals = [normalised.get("extraversion"), normalised.get("agreeableness")]
        if "neuroticism" in normalised:
            signals.append(1.0 - normalised["neuroticism"])
        usable = [value for value in signals if value is not None]
        if usable:
            return _clamp01(sum(usable) / len(usable))

    for scope in _candidate_scopes(persona):
        explicit = _lookup(scope, _INNOVATIVENESS_ALIASES)
        if explicit is not None:
            divisor = scale if scale is not None else _infer_scale([explicit])
            return _clamp01(explicit / (divisor or 1.0))

    weighted_sum = 0.0
    total_weight = 0.0
    for scope in _candidate_scopes(persona):
        for aliases, weight, invert in _PROXY_SPECS:
            raw = _lookup(scope, aliases)
            if raw is None:
                continue
            divisor = _MAX_PLAUSIBLE_AGE if aliases == ("age",) else _infer_scale([raw])
            value = _clamp01(raw / (divisor or 1.0))
            if invert:
                value = 1.0 - value
            weighted_sum += weight * value
            total_weight += weight
    if total_weight > 0.0:
        return _clamp01(weighted_sum / total_weight)

    return _stable_pseudo_score(persona, identifier)


def _allocate_counts(total: int) -> Dict[AdopterCategory, int]:
    """Split ``total`` personas across categories by canonical share.

    Uses the largest-remainder (Hare) method on exact rationals, so the counts
    always sum to ``total`` and each count is within 1 of ``share * total``.
    """
    if total <= 0:
        return {category: 0 for category in CATEGORY_ORDER}

    exact = {category: _CATEGORY_SHARES_EXACT[category] * total for category in CATEGORY_ORDER}
    counts = {category: int(value) for category, value in exact.items()}  # floor
    shortfall = total - sum(counts.values())

    if shortfall:
        remainders = sorted(
            range(len(CATEGORY_ORDER)),
            key=lambda index: (
                -(exact[CATEGORY_ORDER[index]] - counts[CATEGORY_ORDER[index]]),
                index,
            ),
        )
        for index in remainders[:shortfall]:
            counts[CATEGORY_ORDER[index]] += 1

    assert sum(counts.values()) == total
    return counts


def _persona_items(
    personas: Any,
    id_key: Optional[Callable[[Mapping[str, Any]], Hashable]],
) -> List[Tuple[Hashable, Mapping[str, Any]]]:
    """Normalise the accepted input shapes into ``[(persona_id, persona), ...]``."""
    items: List[Tuple[Hashable, Mapping[str, Any]]] = []

    if isinstance(personas, Mapping):
        # Mapping of persona_id -> persona payload.
        for identifier, persona in personas.items():
            if not isinstance(persona, Mapping):
                raise TypeError(
                    f"persona {identifier!r} must be a Mapping, got {type(persona).__name__}"
                )
            items.append((identifier, persona))
        return items

    for position, persona in enumerate(personas):
        if not isinstance(persona, Mapping):
            raise TypeError(
                f"persona at index {position} must be a Mapping, "
                f"got {type(persona).__name__}"
            )
        if id_key is not None:
            identifier = id_key(persona)
        else:
            identifier = _lookup_identifier(persona, position)
        items.append((identifier, persona))
    return items


_ID_ALIASES: Tuple[str, ...] = ("persona_id", "id", "agent_id", "uid", "uuid", "name")


def _lookup_identifier(persona: Mapping[str, Any], position: int) -> Hashable:
    lowered = {str(key).lower(): value for key, value in persona.items()}
    for alias in _ID_ALIASES:
        if alias in lowered:
            value = lowered[alias]
            if isinstance(value, Hashable) and value is not None:
                return value
    return position


def classify_population(
    personas: Any,
    key: Optional[Callable[[Mapping[str, Any]], float]] = None,
    id_key: Optional[Callable[[Mapping[str, Any]], Hashable]] = None,
) -> Dict[Hashable, AdopterCategory]:
    """Assign each persona a Rogers adopter category matching canonical shares.

    The categorisation is a **rank-and-slice**, not per-persona sampling:
    personas are ranked by innovativeness (descending) and the sorted list is
    cut at the canonical share boundaries. Sampling each persona independently
    from the share distribution would only reproduce the shares in expectation
    and would be off by several percent on realistic population sizes; slicing
    reproduces them exactly (up to integer rounding).

    Parameters
    ----------
    personas:
        Either an iterable of persona mappings, or a mapping of
        ``persona_id -> persona mapping``. Plain dicts are accepted on purpose
        so this module does not have to import any profile schema.
    key:
        Optional scoring callable, used like :func:`sorted`'s ``key``: it
        receives a persona and returns its innovativeness score (higher =
        earlier adopter). Defaults to :func:`innovativeness_score`.
    id_key:
        Optional callable extracting the persona id. Only consulted when
        ``personas`` is an iterable; defaults to probing ``persona_id`` / ``id``
        / ``agent_id`` / ``uid`` / ``uuid`` / ``name``, then falling back to the
        positional index.

    Returns
    -------
    dict
        ``{persona_id: AdopterCategory}``.

    Notes
    -----
    Ties are broken deterministically by the string form of the persona id, so
    repeated calls on the same input always produce the same assignment.
    """
    items = _persona_items(personas, id_key)
    if not items:
        return {}

    identifiers = [identifier for identifier, _ in items]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("persona identifiers must be unique")

    if key is None:
        # Infer the trait scale across the whole population before scoring, so
        # every persona is normalised by the same divisor.
        pooled: List[float] = []
        for _, persona in items:
            pooled.extend(_raw_traits(persona).values())
        scale = _infer_scale(pooled) if pooled else None
        scored = [
            (identifier, innovativeness_score(persona, scale=scale, identifier=identifier))
            for identifier, persona in items
        ]
    else:
        scored = []
        for identifier, persona in items:
            raw = _coerce_float(key(persona))
            if raw is None:
                raise ValueError(
                    f"key(...) must return a finite number for persona {identifier!r}"
                )
            scored.append((identifier, raw))

    # Descending score; deterministic tie-break on the id's string form.
    scored.sort(key=lambda pair: (-pair[1], str(pair[0])))

    counts = _allocate_counts(len(scored))
    assignments: Dict[Hashable, AdopterCategory] = {}
    cursor = 0
    for category in CATEGORY_ORDER:
        for identifier, _ in scored[cursor : cursor + counts[category]]:
            assignments[identifier] = category
        cursor += counts[category]

    assert len(assignments) == len(scored)
    return assignments


def category_counts(
    assignments: Mapping[Hashable, AdopterCategory],
) -> Dict[AdopterCategory, int]:
    """Tally an assignment mapping, including zero-count categories."""
    counts = {category: 0 for category in CATEGORY_ORDER}
    for category in assignments.values():
        counts[category] += 1
    return counts


# ---------------------------------------------------------------------------
# 2. Bass diffusion model
# ---------------------------------------------------------------------------

# Empirical parameter ranges, from Bass's own work and the meta-analyses built
# on it:
#
#   p -- coefficient of innovation (external influence: advertising, mass
#        media, independent decision-making). Typically ~0.03, with a
#        plausible range of 0.0002-0.03. Bass (2004) reports that the average
#        value of p across studies is "about 0.03" and notes that estimates
#        are rarely larger; Sultan, Farley & Lehmann (1990), meta-analysing
#        213 applications, report a mean p of roughly 0.03. Values at the
#        0.0002 end come from slow-starting durables where essentially nobody
#        adopts without word of mouth.
#
#   q -- coefficient of imitation (internal influence: word of mouth, social
#        contagion). Typically ~0.38, with a plausible range of 0.3-0.5.
#        Sultan, Farley & Lehmann (1990) report a mean q of about 0.38, and
#        Bass's retrospective commentary uses the same central value.
#
# Because q is roughly an order of magnitude larger than p, diffusion is
# imitation-dominated: the S-curve has a slow start, then an inflection.
#
# Peak adoption (maximum of the *incremental* adoption rate) occurs at
#
#     t* = ln(q / p) / (p + q)
#
# which for p = 0.03, q = 0.38 gives t* = ln(12.667) / 0.41 ~= 6.19 periods.
# See :func:`bass_peak_time`.

TYPICAL_P: float = 0.03
TYPICAL_Q: float = 0.38
P_EMPIRICAL_RANGE: Tuple[float, float] = (0.0002, 0.03)
Q_EMPIRICAL_RANGE: Tuple[float, float] = (0.30, 0.50)


def _validate_bass_params(p: float, q: float, m: float, periods: int) -> None:
    for name, value in (("p", p), ("q", q), ("m", m)):
        coerced = _coerce_float(value)
        if coerced is None:
            raise TypeError(f"{name} must be a finite number, got {value!r}")
        if coerced < 0.0:
            raise ValueError(f"{name} must be non-negative, got {coerced}")
    if not isinstance(periods, int) or isinstance(periods, bool):
        raise TypeError(f"periods must be an int, got {type(periods).__name__}")
    if periods < 0:
        raise ValueError(f"periods must be non-negative, got {periods}")


def bass_adoption_curve(p: float, q: float, m: float, periods: int) -> List[float]:
    """Cumulative adopters at the end of periods ``1 .. periods``.

    Evaluates the closed-form solution of the Bass differential equation

        f(t) / (1 - F(t)) = p + q * F(t)

    which is

        F(t) = (1 - exp(-(p + q) t)) / (1 + (q / p) exp(-(p + q) t))

    and returns ``m * F(t)``. Using the closed form rather than a discrete
    recurrence keeps the curve consistent with the analytic peak time
    :func:`bass_peak_time`, and guarantees the two invariants callers rely on:
    the sequence is monotonically non-decreasing, and it approaches ``m``
    asymptotically without ever reaching or exceeding it.

    Parameters
    ----------
    p:
        Coefficient of innovation (external influence). See
        :data:`P_EMPIRICAL_RANGE`.
    q:
        Coefficient of imitation (internal influence). See
        :data:`Q_EMPIRICAL_RANGE`.
    m:
        Market potential (total eventual adopters).
    periods:
        Number of periods to evaluate. The returned list has exactly this
        length; element ``i`` is cumulative adoption at ``t = i + 1``.

    Returns
    -------
    list of float
        Cumulative adopters, length ``periods``.

    Notes
    -----
    With ``p == 0`` there is no external impulse, so an adoption process
    starting from ``F(0) = 0`` never leaves zero -- the imitation term has
    nothing to imitate. This is the true fixpoint of the model, not a
    numerical dodge, and the function returns all zeros. With ``q == 0`` the
    closed form degenerates to the exponential ``1 - exp(-p t)``.
    """
    _validate_bass_params(p, q, m, periods)
    p, q, m = float(p), float(q), float(m)

    if periods == 0:
        return []
    if p == 0.0 or m == 0.0:
        return [0.0] * periods

    rate = p + q
    ratio = q / p
    curve: List[float] = []
    for step in range(1, periods + 1):
        decay = math.exp(-rate * step)
        fraction = (1.0 - decay) / (1.0 + ratio * decay)
        # Guard against float noise pushing the fraction outside [0, 1).
        curve.append(m * _clamp01(fraction))
    return curve


def bass_incremental_adopters(p: float, q: float, m: float, periods: int) -> List[float]:
    """Per-period new adopters, ``N(t) - N(t - 1)`` with ``N(0) = 0``.

    Element ``i`` covers the interval ``(i, i + 1]``, so its effective midpoint
    is ``i + 0.5`` -- which is the right thing to compare against
    :func:`bass_peak_time`.
    """
    cumulative = bass_adoption_curve(p, q, m, periods)
    increments: List[float] = []
    previous = 0.0
    for value in cumulative:
        increments.append(value - previous)
        previous = value
    return increments


def bass_peak_time(p: float, q: float) -> Optional[float]:
    """Analytic time of peak adoption rate: ``t* = ln(q / p) / (p + q)``.

    Returns ``None`` when no interior peak exists: with ``p <= 0`` nothing ever
    adopts, and with ``q <= 0`` the adoption rate decays monotonically from
    ``t = 0``. When ``0 < q <= p`` the formula legitimately yields a value
    ``<= 0``, meaning the peak precedes launch and the observed rate only ever
    declines; that raw value is returned rather than being clipped.
    """
    coerced_p, coerced_q = _coerce_float(p), _coerce_float(q)
    if coerced_p is None or coerced_q is None:
        raise TypeError("p and q must be finite numbers")
    if coerced_p <= 0.0 or coerced_q <= 0.0:
        return None
    return math.log(coerced_q / coerced_p) / (coerced_p + coerced_q)


# ---------------------------------------------------------------------------
# 3. Linear-threshold network contagion
# ---------------------------------------------------------------------------

Adjacency = Mapping[Hashable, Iterable[Hashable]]


def thresholds_from_categories(
    assignments: Mapping[Hashable, AdopterCategory],
    overrides: Optional[Mapping[AdopterCategory, float]] = None,
) -> Dict[Hashable, float]:
    """Map ``{node: AdopterCategory}`` to ``{node: threshold}``.

    Uses :data:`CATEGORY_THRESHOLDS` unless ``overrides`` supplies a different
    value for a category.
    """
    table = dict(CATEGORY_THRESHOLDS)
    if overrides:
        for category, value in overrides.items():
            if not isinstance(category, AdopterCategory):
                raise TypeError(f"override keys must be AdopterCategory, got {category!r}")
            coerced = _coerce_float(value)
            if coerced is None:
                raise TypeError(f"threshold for {category} must be a finite number")
            table[category] = coerced

    result: Dict[Hashable, float] = {}
    for node, category in assignments.items():
        if not isinstance(category, AdopterCategory):
            raise TypeError(
                f"assignment for node {node!r} must be an AdopterCategory, got {category!r}"
            )
        result[node] = table[category]
    return result


def _all_nodes(adjacency: Adjacency) -> Set[Hashable]:
    if not isinstance(adjacency, Mapping):
        raise TypeError(f"adjacency must be a Mapping, got {type(adjacency).__name__}")
    nodes: Set[Hashable] = set(adjacency.keys())
    for neighbours in adjacency.values():
        if isinstance(neighbours, (str, bytes)):
            raise TypeError("neighbour lists must be iterables of nodes, not strings")
        nodes.update(neighbours)
    return nodes


def propagate(
    adjacency: Adjacency,
    adopted: Iterable[Hashable],
    thresholds: Mapping[Hashable, float],
) -> Set[Hashable]:
    """Run one synchronous timestep of linear-threshold contagion.

    A node adopts when the fraction of its neighbours that have already
    adopted is **greater than or equal to** its threshold. Updates are
    synchronous: every node is evaluated against the state at the *start* of
    the step, so the result does not depend on iteration order.

    A node with no neighbours has an adopted-neighbour fraction of ``0.0``. It
    therefore adopts only if its threshold is ``<= 0`` -- which is exactly the
    innovator case (:data:`CATEGORY_THRESHOLDS` puts innovators at ``0.0``,
    modelling Rogers' venturesome adopters who need no social proof). An
    isolated node with a high threshold can never adopt.

    Parameters
    ----------
    adjacency:
        ``{node: iterable of neighbour nodes}``. Nodes appearing only as
        neighbours are included in the simulation with an empty neighbour set.
        Interpreted as-is, so passing a symmetric mapping gives undirected
        behaviour and an asymmetric one gives directed influence.
    adopted:
        Nodes that have already adopted.
    thresholds:
        ``{node: threshold}``; missing nodes fall back to
        :data:`DEFAULT_THRESHOLD`.

    Returns
    -------
    set
        The full adopted set *after* the step (adoption is monotone, so this is
        a superset of ``adopted``).
    """
    if not isinstance(thresholds, Mapping):
        raise TypeError(f"thresholds must be a Mapping, got {type(thresholds).__name__}")

    nodes = _all_nodes(adjacency)
    current: Set[Hashable] = set(adopted)
    nodes.update(current)

    next_state = set(current)
    for node in nodes:
        if node in current:
            continue
        neighbours = [neighbour for neighbour in adjacency.get(node, ()) if neighbour != node]
        threshold = thresholds.get(node, DEFAULT_THRESHOLD)
        if neighbours:
            adopted_fraction = sum(1 for n in neighbours if n in current) / len(neighbours)
        else:
            adopted_fraction = 0.0
        if adopted_fraction >= threshold:
            next_state.add(node)
    return next_state


def simulate_contagion(
    adjacency: Adjacency,
    seeds: Iterable[Hashable],
    thresholds: Mapping[Hashable, float],
    max_steps: int = 100,
) -> List[Set[Hashable]]:
    """Iterate :func:`propagate` to the cascade fixpoint.

    Returns
    -------
    list of set
        ``[state_0, state_1, ...]`` where ``state_0`` is the seed set and each
        subsequent entry is the adopted set after that step. Only *changed*
        states are appended, so the last element is the fixpoint.

    Termination is guaranteed: adoption is monotone and the node set is finite,
    so each recorded step strictly grows the adopted set and there can be at
    most ``len(nodes)`` of them. ``max_steps`` is an additional explicit cap.
    """
    if not isinstance(max_steps, int) or isinstance(max_steps, bool):
        raise TypeError(f"max_steps must be an int, got {type(max_steps).__name__}")
    if max_steps < 0:
        raise ValueError(f"max_steps must be non-negative, got {max_steps}")

    current: Set[Hashable] = set(seeds)
    history: List[Set[Hashable]] = [set(current)]

    for _ in range(max_steps):
        nxt = propagate(adjacency, current, thresholds)
        if nxt == current:
            break  # fixpoint reached
        history.append(set(nxt))
        current = nxt
    return history


# ---------------------------------------------------------------------------
# Adjacency helpers
# ---------------------------------------------------------------------------


def adjacency_from_edges(
    edges: Iterable[Tuple[Hashable, Hashable]],
    nodes: Optional[Iterable[Hashable]] = None,
    directed: bool = False,
) -> Dict[Hashable, Set[Hashable]]:
    """Build an adjacency mapping from an edge list.

    ``nodes`` lets callers include isolated nodes that appear in no edge.
    """
    adjacency: Dict[Hashable, Set[Hashable]] = {}
    for node in nodes or ():
        adjacency.setdefault(node, set())
    for edge in edges:
        source, target = edge
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set())
        if not directed:
            adjacency[target].add(source)
    return adjacency


def adjacency_from_networkx(graph: Any) -> Dict[Hashable, Set[Hashable]]:
    """Convert a ``networkx`` graph to a plain adjacency mapping.

    ``networkx`` is imported lazily *inside* this function so that importing
    this module never requires it; the core model stays standard-library only.
    """
    return {node: set(graph.neighbors(node)) for node in graph.nodes()}

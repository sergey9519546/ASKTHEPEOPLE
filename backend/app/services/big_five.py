"""
Big Five (OCEAN) personality traits for agent profiles.

Why this module exists
----------------------
The profile schema historically carried an MBTI type. MBTI has poor test-retest
reliability and weak predictive validity for behaviour; the Five Factor Model is
the standard in personality psychology and is what the behavioural literature
(including the trait-behaviour correlations we rely on elsewhere) is built on.

Why MBTI is NOT removed
-----------------------
The installed OASIS package indexes the key unconditionally:

    oasis/social_agent/agents_generator.py:461
        profile["other_info"]["mbti"] = agent_info[i]["mbti"]

    oasis/social_platform/config/user.py:97
        f"...personality type of {self.profile['other_info']['mbti']} from "

A missing "mbti" key raises KeyError and aborts the run, so the field must keep
existing for interop. This module therefore ADDS Big Five as the substantive
representation and DERIVES an MBTI-shaped string from it purely to satisfy
OASIS. The derived code is an interop artifact, not a personality claim.

Honesty about what is and is not empirical
------------------------------------------
- Trait definitions and the 0-100 scaling are standard.
- The population mean/SD defaults are approximations of published normative
  data, not a specific citable sample. Treated as reasonable priors.
- The Big-Five-to-MBTI mapping below is a well-documented *approximate*
  correspondence for four of the five traits (Openness~N/S, Conscientiousness~J/P,
  Extraversion~E/I, Agreeableness~F/T). Neuroticism has NO MBTI counterpart and
  is simply dropped in that direction. The mapping is lossy and one-way.
- Any function whose mapping is a design assumption rather than a finding is
  marked ASSUMPTION in its docstring.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

# Trait keys, in the conventional OCEAN order.
TRAITS = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

# Approximate adult normative centre and spread on a 0-100 scale.
# ASSUMPTION: these are reasonable priors, not a specific published sample.
_POP_MEAN = 50.0
_POP_SD = 18.0

_SCALE_MIN = 0.0
_SCALE_MAX = 100.0


def clamp(value: float) -> float:
    """Clamp a trait score into the valid 0-100 range."""
    return max(_SCALE_MIN, min(_SCALE_MAX, float(value)))


@dataclass(frozen=True)
class BigFive:
    """
    Five Factor personality scores, each on a 0-100 percentile-style scale.

    Frozen because a persona's traits should not drift silently once assigned;
    callers that want a variant should construct a new instance (see `jitter`).
    """

    openness: float = _POP_MEAN
    conscientiousness: float = _POP_MEAN
    extraversion: float = _POP_MEAN
    agreeableness: float = _POP_MEAN
    neuroticism: float = _POP_MEAN

    def __post_init__(self) -> None:
        for trait in TRAITS:
            value = getattr(self, trait)
            if not isinstance(value, (int, float)):
                raise TypeError(f"{trait} must be numeric, got {type(value).__name__}")
            if not _SCALE_MIN <= float(value) <= _SCALE_MAX:
                raise ValueError(
                    f"{trait}={value} out of range; expected {_SCALE_MIN}-{_SCALE_MAX}"
                )

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["BigFive"]:
        """Rebuild from a dict, tolerating absent keys. Returns None for empty input."""
        if not data:
            return None
        present = {t: data[t] for t in TRAITS if data.get(t) is not None}
        if not present:
            return None
        return cls(**present)

    def jitter(self, spread: float = 8.0, rng: Optional[random.Random] = None) -> "BigFive":
        """
        Return a nearby variant, for expanding one archetype into similar individuals.

        Clamped, so repeated jittering of an extreme trait will not walk out of range.
        """
        r = rng or random
        return BigFive(
            **{t: clamp(getattr(self, t) + r.gauss(0.0, spread)) for t in TRAITS}
        )


def sample_population(rng: Optional[random.Random] = None) -> BigFive:
    """
    Draw a trait profile from an approximate population distribution.

    Uses independent normals per trait. Real Big Five factors are close to
    orthogonal by construction (that is the point of factor analysis), so
    independence is a defensible simplification here — unlike demographics,
    where independent sampling produces incoherent people.
    """
    r = rng or random
    return BigFive(**{t: clamp(r.gauss(_POP_MEAN, _POP_SD)) for t in TRAITS})


# --- OASIS interop -------------------------------------------------------

# Threshold for assigning a letter. Scores near the midpoint are genuinely
# ambiguous; we break toward the first letter rather than pretending precision.
_MID = 50.0


def to_mbti_code(traits: BigFive) -> str:
    """
    Derive a 4-letter MBTI-shaped code from Big Five scores, for OASIS interop only.

    ASSUMPTION / LOSSY: this encodes the commonly cited approximate correspondence
    (Extraversion->E/I, Openness->N/S, Agreeableness->F/T, Conscientiousness->J/P).
    Neuroticism has no MBTI dimension and is discarded. Do not treat the output as
    a personality assessment; it exists because OASIS interpolates this key into
    the agent system prompt and raises KeyError without it.
    """
    e_i = "E" if traits.extraversion >= _MID else "I"
    n_s = "N" if traits.openness >= _MID else "S"
    f_t = "F" if traits.agreeableness >= _MID else "T"
    j_p = "J" if traits.conscientiousness >= _MID else "P"
    return f"{e_i}{n_s}{f_t}{j_p}"


# --- Behavioural couplings ----------------------------------------------


def innovativeness(traits: BigFive) -> float:
    """
    Score 0-100 for how readily this persona adopts something new.

    Openness is the best-supported trait link to innovation adoption, so it
    dominates. Extraversion contributes a smaller share via social exposure.
    ASSUMPTION: the specific 0.7/0.3 weighting is a design choice, not a
    measured effect size.
    """
    return clamp(0.7 * traits.openness + 0.3 * traits.extraversion)


def loss_aversion_lambda(traits: BigFive) -> float:
    """
    Prospect-theory loss-aversion coefficient modulated by Neuroticism.

    Tversky & Kahneman's median estimate is ~2.25. Higher Neuroticism is
    associated with stronger sensitivity to negative outcomes, so it shifts
    lambda upward. Deliberately kept in a narrow band around the canonical
    value: the direction is defensible, a large magnitude would not be.
    ASSUMPTION: the +/-0.45 band is a design choice.
    """
    centred = (traits.neuroticism - _POP_MEAN) / _POP_MEAN  # -1.0 .. +1.0
    return round(2.25 + 0.45 * centred, 4)


def adoption_threshold(traits: BigFive) -> float:
    """
    Fraction of peers who must adopt before this persona does (0.0-1.0).

    Inverse of innovativeness: an innovator needs almost no social proof, a
    laggard needs most of their network. Used by linear-threshold contagion.
    ASSUMPTION: linear inversion is a simplification.
    """
    return round(1.0 - (innovativeness(traits) / 100.0), 4)

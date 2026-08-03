"""
Derive engine behavioural controls from Big Five personality traits.

Why this module exists
----------------------
`simulation_config_generator._generate_agent_config_by_rule` returns the same
neutral constants for every agent (activity 0.5, novelty_seeking 0.45,
conflict_tolerance 0.45, authority_sensitivity 0.4, reaction "measured"). That
is a deliberate safety decision, not an oversight: LLM-proposed behavioural
values have no verifiable provenance, so the runtime hard-clamps them
(see simulation_config_generator.py:1138-1147).

The consequence is that every synthetic agent behaves identically. A population
of 50 agents explores exactly one behavioural configuration, which is the single
biggest limit on how much a run can actually tell you.

What changed and why it is allowed
----------------------------------
Big Five traits are a *different provenance class* from an LLM's free-text
guess at "how active is this person". A trait vector is either:

  - derived from supplied source material (verifiable provenance), or
  - explicitly absent (None)

This module maps traits -> controls through fixed, inspectable, unit-tested
arithmetic. There is no model call in this path. Given the same traits it always
returns the same controls, so the result is reproducible and auditable — which
is exactly the property the clamp existed to protect.

When traits are absent this module returns nothing and the caller keeps the
neutral defaults. Absence of personality never becomes invented personality.

Epistemic status of the mappings
--------------------------------
The DIRECTIONS below are supported by the trait literature: Extraversion
predicts social activity and expressiveness; Openness predicts novelty seeking;
Agreeableness predicts conflict avoidance; Conscientiousness predicts
deliberateness and rule/authority orientation; Neuroticism predicts negative
affect.

The SLOPES AND INTERCEPTS ARE NOT EMPIRICAL. They are chosen to keep every
control inside a modest band around the existing neutral default, so that
personality perturbs behaviour without manufacturing extremes. Each is marked
ASSUMPTION. A neutral trait vector (all 50) reproduces the existing neutral
defaults to within rounding, which is asserted by a test — so this change is a
strict generalisation of current behaviour, not a replacement for it.

Nothing here is a prediction about a real person.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .big_five import BigFive

# Provenance tag written onto configs whose controls came from traits.
# Distinct from "neutral_fictional_default" so the two are never confused in
# artifacts, and from anything implying measurement of real humans.
CONTROL_BASIS_TRAIT_DERIVED = "source_derived_trait_projection"

# Neutral baselines, mirroring _generate_agent_config_by_rule. Kept here so a
# test can assert the neutral trait vector reproduces them exactly.
NEUTRAL_ACTIVITY_LEVEL = 0.5
NEUTRAL_POSTS_PER_HOUR = 0.5
NEUTRAL_COMMENTS_PER_HOUR = 1.0
NEUTRAL_CONFLICT_TOLERANCE = 0.45
NEUTRAL_AUTHORITY_SENSITIVITY = 0.4
NEUTRAL_NOVELTY_SEEKING = 0.45
NEUTRAL_RESPONSE_DELAY_MIN = 5
NEUTRAL_RESPONSE_DELAY_MAX = 60

# Half-width of the band each control may move within. ASSUMPTION: these are
# deliberately narrow. Widening them makes runs more dramatic and less
# defensible; do not widen without a reason recorded here.
_ACTIVITY_SPAN = 0.30
_POSTS_SPAN = 0.30
_COMMENTS_SPAN = 0.50
_CONFLICT_SPAN = 0.30
_AUTHORITY_SPAN = 0.30
_NOVELTY_SPAN = 0.35


def _centred(score: float) -> float:
    """Map a 0-100 trait score to -1.0 .. +1.0 around the population midpoint."""
    return (score - 50.0) / 50.0


def _project(baseline: float, span: float, centred: float, lo: float, hi: float) -> float:
    """Shift `baseline` by up to +/-span according to a centred trait, then clamp."""
    return round(max(lo, min(hi, baseline + span * centred)), 4)


def derive_controls(traits: BigFive) -> Dict[str, Any]:
    """
    Project a trait vector onto engine behavioural controls.

    Pure and deterministic: same traits in, same controls out, no model call.
    A neutral vector (all 50) returns the existing neutral defaults.
    """
    o = _centred(traits.openness)
    c = _centred(traits.conscientiousness)
    e = _centred(traits.extraversion)
    a = _centred(traits.agreeableness)
    n = _centred(traits.neuroticism)

    # Extraversion -> volume of social action. Direction supported; slope ASSUMPTION.
    activity_level = _project(NEUTRAL_ACTIVITY_LEVEL, _ACTIVITY_SPAN, e, 0.05, 0.95)
    posts_per_hour = _project(NEUTRAL_POSTS_PER_HOUR, _POSTS_SPAN, e, 0.05, 0.95)
    comments_per_hour = _project(NEUTRAL_COMMENTS_PER_HOUR, _COMMENTS_SPAN, e, 0.1, 2.0)

    # Agreeableness -> conflict avoidance, so the sign is INVERTED: agreeable
    # agents tolerate less conflict. Direction supported; slope ASSUMPTION.
    conflict_tolerance = _project(
        NEUTRAL_CONFLICT_TOLERANCE, _CONFLICT_SPAN, -a, 0.05, 0.95
    )

    # Conscientiousness -> deference to rules/authority. ASSUMPTION on slope.
    authority_sensitivity = _project(
        NEUTRAL_AUTHORITY_SENSITIVITY, _AUTHORITY_SPAN, c, 0.05, 0.95
    )

    # Openness -> appetite for the unfamiliar. Best-supported of these links.
    novelty_seeking = _project(NEUTRAL_NOVELTY_SEEKING, _NOVELTY_SPAN, o, 0.05, 0.95)

    # Extraverts respond sooner; conscientious agents deliberate longer. The
    # window must stay ordered and positive.
    delay_shift = -12.0 * e + 8.0 * c
    delay_min = int(max(1, round(NEUTRAL_RESPONSE_DELAY_MIN + delay_shift * 0.4)))
    delay_max = int(max(delay_min + 1, round(NEUTRAL_RESPONSE_DELAY_MAX + delay_shift)))

    return {
        "activity_level": activity_level,
        "posts_per_hour": posts_per_hour,
        "comments_per_hour": comments_per_hour,
        "conflict_tolerance": conflict_tolerance,
        "authority_sensitivity": authority_sensitivity,
        "novelty_seeking": novelty_seeking,
        "response_delay_min": delay_min,
        "response_delay_max": delay_max,
        "reaction_style": reaction_style(traits),
        # Provenance. Deliberately does NOT claim measurement of real humans:
        # the remaining truth flags are set by the caller and stay false.
        "control_assumption_basis": CONTROL_BASIS_TRAIT_DERIVED,
    }


def reaction_style(traits: BigFive) -> str:
    """
    Pick one of the engine's four reaction styles from traits.

    The engine accepts exactly: measured, reactive, amplifying, cautious.
    Order matters — the first matching rule wins, so the most behaviourally
    distinctive condition is checked first. ASSUMPTION: thresholds are design
    choices; only the orderings they encode are defensible.
    """
    high_neuroticism = traits.neuroticism >= 65.0
    low_agreeableness = traits.agreeableness <= 35.0
    high_extraversion = traits.extraversion >= 65.0
    high_conscientiousness = traits.conscientiousness >= 65.0

    if high_neuroticism and low_agreeableness:
        return "reactive"
    if high_extraversion and traits.openness >= 60.0:
        return "amplifying"
    if high_conscientiousness or (high_neuroticism and traits.extraversion <= 40.0):
        return "cautious"
    return "measured"


def controls_from_canonical_agent(agent: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Read `big_five` off a canonical agent dict and project it, or return None.

    Returns None — meaning "keep the neutral defaults" — when the agent is
    missing, carries no traits, or carries traits that fail validation. Malformed
    trait data must never silently become a behavioural claim, so a ValueError
    or TypeError from BigFive is treated as absence rather than propagated.
    """
    if not agent:
        return None
    try:
        traits = BigFive.from_dict(agent.get("big_five"))
    except (ValueError, TypeError):
        return None
    if traits is None:
        return None
    return derive_controls(traits)


# ---------------------------------------------------------------------------
# Prospect-theory persona framing
# ---------------------------------------------------------------------------
# This section produces a short, deterministic text fragment that describes
# how an agent frames decisions under uncertainty, based on their trait-derived
# Prospect Theory parameters. The fragment is appended to the persona string
# before writing reddit_profiles.json so it reaches the OASIS system prompt.
#
# Why text, not a config field
# ----------------------------
# `stance` and `sentiment_bias` in AgentActivityConfig are not consumed by the
# subprocess scripts — verified by grepping every reference in all three
# run_*.py files. The agent system prompt (built by OASIS user.py:97 from
# `profile["other_info"]["user_profile"]`) IS live. Enriching the persona text
# is the correct integration point.
#
# Why deterministic
# -----------------
# A deterministic projection keeps this on the right side of the provenance
# clamp. The same traits always produce the same text. No model call.
#
# Epistemic status
# ----------------
# The DIRECTIONS in the framing (neuroticism → loss sensitivity,
# conscientiousness → deliberation, openness → probability calibration) are
# supported by the trait literature. The specific THRESHOLDS and PHRASING are
# ASSUMPTION and are clearly labelled as scenario assumptions in the output text.


# Threshold above/below which a trait "moves" the framing
_HIGH = 65.0
_LOW  = 35.0

# Canonical TK92 loss-aversion coefficient for reference
_CANONICAL_LAMBDA = 2.25


def prospect_framing_text(traits: BigFive) -> str:
    """
    Return a 1-3 sentence scenario-assumption fragment for the OASIS system prompt.

    Describes how this agent frames decisions under uncertainty. The output is
    deterministic: same traits → same text. Returns empty string for a neutral
    trait vector so the persona is unchanged for unspecialised agents.

    ASSUMPTION: thresholds (_HIGH/_LOW) and phrasing are design choices.
    Only the directional links are literature-supported.
    """
    from .prospect_theory import params_from_big_five
    from .big_five import TRAITS

    # prospect_theory expects normalized [0,1] scores; BigFive uses [0,100]
    params = params_from_big_five(
        openness=traits.openness / 100.0,
        conscientiousness=traits.conscientiousness / 100.0,
        extraversion=traits.extraversion / 100.0,
        agreeableness=traits.agreeableness / 100.0,
        neuroticism=traits.neuroticism / 100.0,
    )

    fragments = []

    # Loss aversion: driven by neuroticism. Only mention when clearly above/below neutral.
    if traits.neuroticism >= _HIGH:
        fragments.append(
            f"In this scenario, losses weigh approximately "
            f"{params.lambda_:.1f}× more heavily than equivalent gains; "
            "decision-making tends to anchor on downside risk and status-quo preservation."
        )
    elif traits.neuroticism <= _LOW:
        fragments.append(
            f"In this scenario, potential gains are weighted roughly on par with losses "
            f"(loss-aversion coefficient ≈ {params.lambda_:.1f}); "
            "willing to accept symmetric risk for symmetric expected value."
        )

    # Probability calibration: openness affects gamma (weighting function curvature).
    # High openness → gamma closer to 1 → less distortion of probabilities.
    if traits.openness >= _HIGH:
        fragments.append(
            "Evaluates scenario likelihoods with relatively calibrated probability assessment; "
            "less prone to overweighting rare catastrophes or underweighting likely outcomes."
        )
    elif traits.openness <= _LOW:
        fragments.append(
            "Tends to overweight small-probability scenarios (both opportunities and threats); "
            "low-likelihood outcomes may receive disproportionate attention."
        )

    # Deliberation: conscientiousness affects decision speed and systematicity.
    if traits.conscientiousness >= _HIGH:
        fragments.append(
            "Approaches decisions methodically; "
            "evaluates trade-offs sequentially before committing to a position."
        )
    elif traits.conscientiousness <= _LOW:
        fragments.append(
            "Reaches positions quickly with limited sequential evaluation; "
            "acts on initial framing rather than exhaustive trade-off analysis."
        )

    if not fragments:
        return ""  # Neutral vector → no framing appended

    # Prepend a single disclosure marker so the text is clearly labelled in
    # any artifact or export rather than being mistaken for source fact.
    return (
        "[Scenario assumption — risk framing derived from personality projection] "
        + " ".join(fragments)
    )


def persona_with_framing(internal_persona: str, agent: Optional[Dict[str, Any]]) -> str:
    """
    Return `internal_persona` augmented with a prospect-theory framing sentence,
    or the original persona unchanged if no traits are available.

    Safe to call on every agent: absent traits return the input unmodified.
    """
    if not agent:
        return internal_persona
    try:
        traits = BigFive.from_dict(agent.get("big_five"))
    except (ValueError, TypeError):
        return internal_persona
    if traits is None:
        return internal_persona

    framing = prospect_framing_text(traits)
    if not framing:
        return internal_persona

    separator = "\n\n" if internal_persona and not internal_persona.endswith("\n") else ""
    return f"{internal_persona}{separator}{framing}"

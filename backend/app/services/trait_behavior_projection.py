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


# ---------------------------------------------------------------------------
# Constraint-based influence weight + persona framing
# ---------------------------------------------------------------------------
# The constraint_engine models what actors CAN do, not just what they want.
# Here it drives two things:
#
#   1. influence_weight in AgentActivityConfig — institutional actors have
#      more amplification capacity than isolated individuals.
#
#   2. A persona text fragment — describes what structural limits apply, so
#      the OASIS system prompt captures resource and authority constraints.
#
# Both are derived deterministically from the entity role (no model call)
# and fail open if the role is unknown or the constraint module is absent.
#
# ASSUMPTION: the influence_weight values by role are design choices. The
# DIRECTION is defensible (institutions have more reach); the specific
# multipliers are not empirical.


# Influence weight by role family. 1.0 is the baseline for individuals.
# ASSUMPTION: all multipliers are design choices, not measured values.
# Keys cover BOTH normalized_role and role_family values produced by
# role_normalizer.normalize_entity_type (verified empirically: individual,
# academic, alumni, expert, official, student -> person family; organization,
# institution, government -> institution family; journalist, media -> media;
# community; entity).
_INFLUENCE_BY_ROLE_FAMILY = {
    # institutions / officials / media amplify more
    "institution":    1.40,
    "organization":   1.40,
    "government":     1.40,
    "official":       1.25,
    "media":          1.35,
    "journalist":     1.35,
    "expert":         1.15,
    "academic":       1.10,
    "community":      1.10,
    # individuals: baseline
    "individual":     1.00,
    "person":         1.00,
    "alumni":         1.00,
    "entity":         1.00,
    "unknown":        1.00,
    # constrained individual
    "student":        0.90,
}

# Text fragments by role family for the persona constraint section.
_CONSTRAINT_TEXT_BY_ROLE = {
    "institution": (
        "Operates with institutional resources (budget, staff, communications channels) "
        "but is subject to formal accountability constraints — regulatory compliance, "
        "public scrutiny, and board or governance approval for major positions."
    ),
    "organization": (
        "Operates with organizational resources but is subject to formal accountability "
        "constraints — regulatory compliance, public scrutiny, and governance approval "
        "for major positions."
    ),
    "government": (
        "Holds formal public authority with broad reach, but is bound by legal and "
        "procedural constraints: actions require due process, are matters of public "
        "record, and may be subject to challenge or appeal."
    ),
    "official": (
        "Holds formal authority within its jurisdiction, which amplifies reach, "
        "but is bound by legal and procedural constraints: actions require due process, "
        "public record, and may be subject to challenge or appeal."
    ),
    "media": (
        "Has broad distribution reach but operates under editorial constraints — "
        "verification requirements, reputational risk from inaccuracy, and platform "
        "or publication standards that shape what and how it can publish."
    ),
    "journalist": (
        "Has publication reach but operates under editorial constraints — "
        "verification requirements, reputational risk from inaccuracy, and "
        "publication standards that shape what and how it can publish."
    ),
    "expert": (
        "Carries credibility in a domain, which amplifies perceived authority, "
        "but is constrained by professional norms: positions outside the domain "
        "of expertise carry less weight and risk reputational cost."
    ),
    "academic": (
        "Carries scholarly credibility that amplifies perceived authority, but is "
        "constrained by academic norms — evidentiary standards and the reputational "
        "cost of claims beyond established findings."
    ),
    "community": (
        "Speaks with collective legitimacy but typically lacks formal authority or "
        "large budgets; coordinated action requires voluntary participation and "
        "consensus-building, and resource limits constrain what it can deliver."
    ),
    "student": (
        "Operates with limited discretionary resources and institutional standing; "
        "influence is largely informal and contingent on others' willingness to listen."
    ),
    "individual": (
        "Operates as an individual with limited discretionary time, budget, "
        "and information access. Actions that require significant resources, "
        "coordination, or formal authority are likely out of reach."
    ),
    "person": (
        "Operates as an individual with limited discretionary time, budget, "
        "and information access. Actions that require significant resources, "
        "coordination, or formal authority are likely out of reach."
    ),
}


def influence_weight_from_role(role_info: Optional[Dict[str, Any]]) -> float:
    """
    Return an influence_weight multiplier based on role.

    1.0 is the baseline. Institutional and media actors exceed it; individuals
    stay at 1.0. Returns 1.0 (neutral) for absent or unknown roles.

    Accepts either a raw normalize_entity_type() result (with normalized_role /
    role_family keys) or a bare normalized_role string. ASSUMPTION: multipliers
    are design choices; direction defensible.
    """
    normalized = _normalized_role_of(role_info)
    if normalized in _INFLUENCE_BY_ROLE_FAMILY:
        return _INFLUENCE_BY_ROLE_FAMILY[normalized]
    family = _role_family_of(role_info)
    return _INFLUENCE_BY_ROLE_FAMILY.get(family, 1.0)


def constraint_framing_text(role_info: Optional[Dict[str, Any]]) -> str:
    """
    Return a 1-2 sentence scenario-assumption fragment describing structural
    constraints for this entity type.

    Returns empty string for unknown/missing roles so personas are unchanged.
    Deterministic: same role_info → same text. No model call.

    Accepts either a raw normalize_entity_type() result or a bare
    normalized_role string (e.g. "individual", "organization", "government").
    """
    normalized = _normalized_role_of(role_info)
    text = _CONSTRAINT_TEXT_BY_ROLE.get(normalized)
    if text is None:
        text = _CONSTRAINT_TEXT_BY_ROLE.get(_role_family_of(role_info), "")
    if not text:
        return ""
    return f"[Scenario assumption — structural constraints for role type] {text}"


def _normalized_role_of(role_info: Optional[Any]) -> str:
    """Resolve the normalized role key, whether given a dict or a bare string."""
    if isinstance(role_info, str):
        return role_info
    if not role_info:
        return ""
    return str(role_info.get("normalized_role", "") or "")


def _role_family_of(role_info: Optional[Any]) -> str:
    if isinstance(role_info, str):
        # A bare string is already a normalized role; family lookup not needed.
        return ""
    if not role_info:
        return "unknown"
    return str(role_info.get("role_family", "unknown") or "unknown")


def persona_with_constraint_framing(
    internal_persona: str,
    role_info: Optional[Dict[str, Any]],
) -> str:
    """
    Return `internal_persona` augmented with a structural-constraint fragment.

    Absent or unknown roles leave the persona unchanged.
    """
    framing = constraint_framing_text(role_info)
    if not framing:
        return internal_persona
    separator = "\n\n" if internal_persona and not internal_persona.endswith("\n") else ""
    return f"{internal_persona}{separator}{framing}"

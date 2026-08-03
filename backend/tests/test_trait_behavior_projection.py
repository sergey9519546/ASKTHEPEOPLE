"""
Tests for trait -> behavioural control projection.

The critical property is the neutrality guarantee: a neutral trait vector must
reproduce the existing hard-clamped defaults exactly, and absent traits must
leave the defaults untouched. That is what makes this a strict generalisation of
current behaviour rather than a behavioural change smuggled in behind a refactor.
"""

import pytest

from app.services.big_five import BigFive
from app.services.trait_behavior_projection import (
    CONTROL_BASIS_TRAIT_DERIVED,
    NEUTRAL_ACTIVITY_LEVEL,
    NEUTRAL_AUTHORITY_SENSITIVITY,
    NEUTRAL_COMMENTS_PER_HOUR,
    NEUTRAL_CONFLICT_TOLERANCE,
    NEUTRAL_NOVELTY_SEEKING,
    NEUTRAL_POSTS_PER_HOUR,
    NEUTRAL_RESPONSE_DELAY_MAX,
    NEUTRAL_RESPONSE_DELAY_MIN,
    controls_from_canonical_agent,
    derive_controls,
    reaction_style,
)

# Engine-accepted reaction styles, per the config generator prompt contract.
VALID_REACTION_STYLES = {"measured", "reactive", "amplifying", "cautious"}

# Bounded controls and their permitted ranges.
BOUNDED = {
    "activity_level": (0.05, 0.95),
    "posts_per_hour": (0.05, 0.95),
    "comments_per_hour": (0.1, 2.0),
    "conflict_tolerance": (0.05, 0.95),
    "authority_sensitivity": (0.05, 0.95),
    "novelty_seeking": (0.05, 0.95),
}

EXTREMES = [0.0, 25.0, 50.0, 75.0, 100.0]


def _grid():
    """A coarse but exhaustive sweep of the trait space corners."""
    for o in EXTREMES:
        for c in EXTREMES:
            for e in EXTREMES:
                for a in EXTREMES:
                    for n in EXTREMES:
                        yield BigFive(
                            openness=o,
                            conscientiousness=c,
                            extraversion=e,
                            agreeableness=a,
                            neuroticism=n,
                        )


class TestNeutralityGuarantee:
    """A neutral vector must reproduce today's clamped defaults."""

    def test_neutral_traits_reproduce_neutral_defaults(self):
        controls = derive_controls(BigFive())
        assert controls["activity_level"] == pytest.approx(NEUTRAL_ACTIVITY_LEVEL)
        assert controls["posts_per_hour"] == pytest.approx(NEUTRAL_POSTS_PER_HOUR)
        assert controls["comments_per_hour"] == pytest.approx(NEUTRAL_COMMENTS_PER_HOUR)
        assert controls["conflict_tolerance"] == pytest.approx(NEUTRAL_CONFLICT_TOLERANCE)
        assert controls["authority_sensitivity"] == pytest.approx(
            NEUTRAL_AUTHORITY_SENSITIVITY
        )
        assert controls["novelty_seeking"] == pytest.approx(NEUTRAL_NOVELTY_SEEKING)

    def test_neutral_traits_reproduce_neutral_delays(self):
        controls = derive_controls(BigFive())
        assert controls["response_delay_min"] == NEUTRAL_RESPONSE_DELAY_MIN
        assert controls["response_delay_max"] == NEUTRAL_RESPONSE_DELAY_MAX

    def test_neutral_traits_give_measured_reaction(self):
        assert reaction_style(BigFive()) == "measured"


class TestAbsentTraitsKeepDefaults:
    """Absence of personality must never become invented personality."""

    def test_no_agent_returns_none(self):
        assert controls_from_canonical_agent(None) is None

    def test_empty_agent_returns_none(self):
        assert controls_from_canonical_agent({}) is None

    def test_agent_without_big_five_returns_none(self):
        assert controls_from_canonical_agent({"agent_id": 3, "mbti": "INTJ"}) is None

    def test_explicit_none_big_five_returns_none(self):
        assert controls_from_canonical_agent({"big_five": None}) is None

    def test_all_none_trait_values_returns_none(self):
        agent = {"big_five": {t: None for t in
                              ("openness", "conscientiousness", "extraversion",
                               "agreeableness", "neuroticism")}}
        assert controls_from_canonical_agent(agent) is None

    def test_out_of_range_traits_return_none_not_exception(self):
        """Malformed data must degrade to defaults, not crash a run or become a claim."""
        assert controls_from_canonical_agent({"big_five": {"openness": 900.0}}) is None

    def test_non_numeric_traits_return_none_not_exception(self):
        assert controls_from_canonical_agent({"big_five": {"openness": "very"}}) is None

    def test_valid_traits_do_produce_controls(self):
        agent = {"big_five": BigFive(extraversion=90.0).to_dict()}
        controls = controls_from_canonical_agent(agent)
        assert controls is not None
        assert controls["control_assumption_basis"] == CONTROL_BASIS_TRAIT_DERIVED


class TestDirectionalMappings:
    """Only the directions are defensible, so only directions are asserted."""

    def test_extraversion_raises_activity(self):
        quiet = derive_controls(BigFive(extraversion=10.0))
        loud = derive_controls(BigFive(extraversion=90.0))
        assert loud["activity_level"] > quiet["activity_level"]
        assert loud["posts_per_hour"] > quiet["posts_per_hour"]
        assert loud["comments_per_hour"] > quiet["comments_per_hour"]

    def test_agreeableness_lowers_conflict_tolerance(self):
        """Inverted mapping: agreeable agents tolerate LESS conflict."""
        agreeable = derive_controls(BigFive(agreeableness=90.0))
        hostile = derive_controls(BigFive(agreeableness=10.0))
        assert agreeable["conflict_tolerance"] < hostile["conflict_tolerance"]

    def test_conscientiousness_raises_authority_sensitivity(self):
        lax = derive_controls(BigFive(conscientiousness=10.0))
        dutiful = derive_controls(BigFive(conscientiousness=90.0))
        assert dutiful["authority_sensitivity"] > lax["authority_sensitivity"]

    def test_openness_raises_novelty_seeking(self):
        closed = derive_controls(BigFive(openness=10.0))
        curious = derive_controls(BigFive(openness=90.0))
        assert curious["novelty_seeking"] > closed["novelty_seeking"]

    def test_extraversion_shortens_response_delay(self):
        introvert = derive_controls(BigFive(extraversion=10.0))
        extravert = derive_controls(BigFive(extraversion=90.0))
        assert extravert["response_delay_max"] < introvert["response_delay_max"]

    def test_conscientiousness_lengthens_response_delay(self):
        impulsive = derive_controls(BigFive(conscientiousness=10.0))
        deliberate = derive_controls(BigFive(conscientiousness=90.0))
        assert deliberate["response_delay_max"] > impulsive["response_delay_max"]

    def test_openness_does_not_drive_activity(self):
        """Guards against accidentally coupling unrelated trait/control pairs."""
        a = derive_controls(BigFive(openness=5.0))
        b = derive_controls(BigFive(openness=95.0))
        assert a["activity_level"] == b["activity_level"]


class TestInvariantsAcrossWholeTraitSpace:
    def test_all_bounded_controls_stay_in_range(self):
        for traits in _grid():
            controls = derive_controls(traits)
            for key, (lo, hi) in BOUNDED.items():
                assert lo <= controls[key] <= hi, f"{key} escaped range for {traits}"

    def test_delay_window_always_ordered_and_positive(self):
        for traits in _grid():
            controls = derive_controls(traits)
            assert controls["response_delay_min"] >= 1
            assert controls["response_delay_max"] > controls["response_delay_min"]

    def test_reaction_style_always_engine_valid(self):
        for traits in _grid():
            assert reaction_style(traits) in VALID_REACTION_STYLES

    def test_provenance_tag_always_present(self):
        for traits in _grid():
            assert derive_controls(traits)["control_assumption_basis"] == (
                CONTROL_BASIS_TRAIT_DERIVED
            )

    def test_provenance_never_claims_measurement(self):
        """The basis string must not imply real human data."""
        basis = CONTROL_BASIS_TRAIT_DERIVED.lower()
        for forbidden in ("measured", "human", "observed", "representative",
                          "forecast", "predict"):
            assert forbidden not in basis


class TestDeterminism:
    def test_same_traits_give_identical_controls(self):
        traits = BigFive(openness=63.0, conscientiousness=41.0, extraversion=77.0,
                         agreeableness=22.0, neuroticism=58.0)
        assert derive_controls(traits) == derive_controls(traits)

    def test_no_model_call_in_this_path(self):
        """Determinism is the property the provenance clamp protects."""
        import app.services.trait_behavior_projection as mod
        source = open(mod.__file__, encoding="utf-8").read()
        for banned in ("LLMClient", "openai", "requests.", "_call_llm"):
            assert banned not in source


class TestReactionStyleRules:
    def test_anxious_and_hostile_is_reactive(self):
        assert reaction_style(BigFive(neuroticism=80.0, agreeableness=20.0)) == "reactive"

    def test_outgoing_and_curious_is_amplifying(self):
        assert reaction_style(
            BigFive(extraversion=80.0, openness=75.0, neuroticism=30.0)
        ) == "amplifying"

    def test_dutiful_is_cautious(self):
        assert reaction_style(
            BigFive(conscientiousness=85.0, extraversion=40.0, neuroticism=40.0)
        ) == "cautious"

    def test_withdrawn_and_anxious_is_cautious(self):
        assert reaction_style(
            BigFive(neuroticism=80.0, extraversion=20.0, agreeableness=60.0)
        ) == "cautious"

    def test_reactive_takes_precedence_over_cautious(self):
        """Rule order is load-bearing; this pins it."""
        traits = BigFive(neuroticism=90.0, agreeableness=10.0,
                         conscientiousness=90.0, extraversion=20.0)
        assert reaction_style(traits) == "reactive"


class TestPopulationDiversity:
    """The whole point of the change: agents must stop being identical."""

    def test_distinct_personalities_yield_distinct_controls(self):
        import random

        from app.services.big_five import sample_population

        rng = random.Random(4242)
        signatures = set()
        for _ in range(60):
            controls = derive_controls(sample_population(rng=rng))
            signatures.add((
                controls["activity_level"],
                controls["conflict_tolerance"],
                controls["novelty_seeking"],
                controls["reaction_style"],
            ))
        # Before this module every agent shared one signature.
        assert len(signatures) > 40, f"only {len(signatures)} distinct configurations"

    def test_more_than_one_reaction_style_appears_in_a_population(self):
        import random

        from app.services.big_five import sample_population

        rng = random.Random(99)
        styles = {reaction_style(sample_population(rng=rng)) for _ in range(200)}
        assert len(styles) >= 3

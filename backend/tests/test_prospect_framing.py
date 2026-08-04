"""
Tests for prospect-theory persona framing.

Critical properties:
  1. Deterministic: same traits → same text, always
  2. Fail-open: absent/malformed traits → original persona unchanged
  3. Correct channel: framing reaches reddit_profiles.json on disk
  4. Clearly labelled: output includes "[Scenario assumption" disclosure
  5. Trait-direction correct: neuroticism ↑ → loss aversion ↑ (literature-supported)
  6. Threshold-conditional: neutral traits → empty framing (no change)
  7. Platform-symmetric: twitter and reddit writers apply the same framing
"""

import json
import os
import tempfile
import types
from unittest.mock import patch

import pytest

from app.services.big_five import BigFive
from app.services.trait_behavior_projection import (
    persona_with_framing,
    prospect_framing_text,
)


class TestProspectFramingDeterminism:
    def test_same_traits_produce_identical_text(self):
        traits = BigFive(neuroticism=85.0, conscientiousness=20.0, openness=75.0)
        result1 = prospect_framing_text(traits)
        result2 = prospect_framing_text(traits)
        assert result1 == result2
        assert result1  # not empty

    def test_neutral_traits_produce_empty_framing(self):
        """Neutral vector → no change to persona."""
        neutral = BigFive()  # all 50.0
        assert prospect_framing_text(neutral) == ""

    def test_slightly_off_neutral_still_produces_empty(self):
        """Only strong deviations trigger framing; narrow band around midpoint is silent."""
        near_neutral = BigFive(neuroticism=55.0, openness=48.0, conscientiousness=52.0)
        assert prospect_framing_text(near_neutral) == ""


class TestProspectFramingDirection:
    def test_high_neuroticism_increases_loss_aversion(self):
        """Literature: neuroticism correlates with loss aversion."""
        high_n = BigFive(neuroticism=85.0)
        framing = prospect_framing_text(high_n)
        assert "losses weigh approximately" in framing
        assert "more heavily than equivalent gains" in framing
        assert "2." in framing  # lambda > 2.0

    def test_low_neuroticism_reduces_loss_aversion(self):
        low_n = BigFive(neuroticism=20.0)
        framing = prospect_framing_text(low_n)
        assert "on par with losses" in framing or "roughly" in framing

    def test_high_openness_improves_probability_calibration(self):
        """Openness → lower gamma → less probability distortion."""
        high_o = BigFive(openness=90.0)
        framing = prospect_framing_text(high_o)
        assert "calibrated probability" in framing or "less prone" in framing

    def test_low_openness_distorts_probabilities(self):
        low_o = BigFive(openness=20.0)
        framing = prospect_framing_text(low_o)
        assert "overweight" in framing and "small-probability" in framing

    def test_high_conscientiousness_increases_deliberation(self):
        high_c = BigFive(conscientiousness=85.0)
        framing = prospect_framing_text(high_c)
        assert "methodically" in framing or "evaluates trade-offs" in framing

    def test_low_conscientiousness_speeds_decisions(self):
        low_c = BigFive(conscientiousness=20.0)
        framing = prospect_framing_text(low_c)
        assert "quickly" in framing or "initial framing" in framing


class TestProspectFramingFailsOpen:
    def test_absent_agent_returns_original_persona(self):
        original = "An engineer."
        assert persona_with_framing(original, None) == original

    def test_agent_without_big_five_returns_original(self):
        original = "An engineer."
        assert persona_with_framing(original, {}) == original
        assert persona_with_framing(original, {"agent_id": 1}) == original

    def test_agent_with_none_big_five_returns_original(self):
        original = "An engineer."
        assert persona_with_framing(original, {"big_five": None}) == original

    def test_malformed_big_five_returns_original_not_exception(self):
        original = "An engineer."
        malformed = {"big_five": {"openness": "not_a_number"}}
        result = persona_with_framing(original, malformed)
        assert result == original  # didn't crash


class TestProspectFramingLabelling:
    def test_framing_text_includes_disclosure_label(self):
        """Must be clearly labelled as scenario assumption, not source fact."""
        traits = BigFive(neuroticism=85.0)
        framing = prospect_framing_text(traits)
        assert "[Scenario assumption" in framing
        assert "personality projection" in framing

    def test_framing_never_claims_to_be_measured_or_observed(self):
        """Epistemic honesty: this is a projection, not data."""
        traits = BigFive(neuroticism=85.0, openness=90.0, conscientiousness=20.0)
        framing = prospect_framing_text(traits).lower()
        forbidden = ["measured", "observed", "diagnosed", "assessed", "tested", "validated"]
        for word in forbidden:
            assert word not in framing, f"framing must not claim '{word}'"


class TestEndToEndIntegration:
    def test_framing_reaches_reddit_profiles_json_on_disk(self):
        """The real integration test: prove the text reaches the file OASIS loads."""
        from app.services.oasis_profile_generator import OasisAgentProfile
        from app.services.simulation_artifacts import (
            build_canonical_agents,
            write_exports_from_canonical,
        )

        traits = BigFive(neuroticism=85.0, conscientiousness=20.0)
        profile = OasisAgentProfile(
            user_id=0,
            user_name="u0",
            name="Test Person",
            bio="bio",
            persona="An engineer who values community.",
            big_five=traits.to_dict(),
        )
        entity = types.SimpleNamespace(
            uuid="u0",
            name="Test Person",
            summary="summary",
            attributes={},
            get_entity_type=lambda: "Person",
            related_edges=[],
            related_nodes=[],
        )
        canonical = build_canonical_agents([entity], [profile])
        tmpdir = tempfile.mkdtemp()
        write_exports_from_canonical(tmpdir, canonical)

        reddit_path = os.path.join(tmpdir, "reddit_profiles.json")
        assert os.path.exists(reddit_path), "reddit_profiles.json must exist"
        on_disk = json.load(open(reddit_path, encoding="utf-8"))
        persona_on_disk = on_disk[0]["persona"]

        assert "An engineer who values community." in persona_on_disk
        assert "[Scenario assumption" in persona_on_disk
        assert "losses weigh approximately" in persona_on_disk
        assert "2." in persona_on_disk  # lambda coefficient

    def test_neutral_traits_leave_prospect_framing_empty(self):
        """Neutral vector → no PROSPECT framing (constraint framing may still apply)."""
        from app.services.oasis_profile_generator import OasisAgentProfile
        from app.services.simulation_artifacts import (
            build_canonical_agents,
            write_exports_from_canonical,
        )

        neutral = BigFive()  # all 50.0
        original_persona = "A neutral engineer."
        profile = OasisAgentProfile(
            user_id=0,
            user_name="u0",
            name="Neutral",
            bio="bio",
            persona=original_persona,
            big_five=neutral.to_dict(),
        )
        entity = types.SimpleNamespace(
            uuid="u0", name="Neutral", summary="s", attributes={},
            get_entity_type=lambda: "Person",
            related_edges=[], related_nodes=[],
        )
        canonical = build_canonical_agents([entity], [profile])
        tmpdir = tempfile.mkdtemp()
        write_exports_from_canonical(tmpdir, canonical)

        on_disk = json.load(open(os.path.join(tmpdir, "reddit_profiles.json"), encoding="utf-8"))
        persona = on_disk[0]["persona"]
        # Neutral traits → no prospect framing (loss aversion, probability weighting)
        assert "losses weigh" not in persona
        assert "probability" not in persona
        # But constraint framing still applies based on entity type
        assert "individual with limited discretionary" in persona or original_persona in persona

    def test_export_exception_does_not_crash_pipeline(self):
        """If framing fails, the pipeline must succeed with original persona."""
        from app.services.simulation_artifacts import canonical_to_reddit_profiles

        canonical = [
            {
                "display_name": "Test",
                "username": "test",
                "public_bio": "bio",
                "internal_persona": "original",
                "age": 30,
                "mbti": "INTJ",
                "country": "US",
                "big_five": {"openness": "INVALID"},  # malformed
            }
        ]
        result = canonical_to_reddit_profiles(canonical)
        assert result[0]["persona"] == "original"  # didn't crash, used original


class TestProspectFramingProvenance:
    def test_framing_does_not_claim_human_measurement(self):
        """The framing is a scenario assumption, not human data."""
        traits = BigFive(neuroticism=85.0, openness=90.0, conscientiousness=20.0)
        framing = prospect_framing_text(traits).lower()
        # Must not include any phrasing that suggests real measurement
        forbidden_phrases = [
            "this person",
            "this individual",
            "subject",
            "participant",
            "respondent",
            "measured",
            "observed behavior",
            "clinical",
            "diagnosis",
        ]
        for phrase in forbidden_phrases:
            assert phrase not in framing, f"must not claim '{phrase}'"

    def test_framing_explicitly_says_scenario_assumption(self):
        traits = BigFive(neuroticism=85.0)
        framing = prospect_framing_text(traits)
        assert "scenario" in framing.lower()
        assert "assumption" in framing.lower()


class TestFramingReachesBothPlatforms:
    """The default platform is "parallel", so both writers run in one job.

    If only one of them applies the framing, a cross-platform comparison in a
    report measures which writer produced the profile rather than anything
    about the scenario.
    """

    @staticmethod
    def _agent():
        return {
            "agent_id": 0,
            "display_name": "Alice",
            "username": "alice",
            "public_bio": "bio",
            "internal_persona": "Base persona.",
            "age": 40,
            "gender": "female",
            "mbti": "INTJ",
            "country": "US",
            "source_entity_type_normalized": "organization",
            "big_five": BigFive(
                openness=90.0,
                conscientiousness=80.0,
                extraversion=20.0,
                agreeableness=50.0,
                neuroticism=80.0,
            ).to_dict(),
        }

    def test_twitter_rows_carry_the_same_framing_as_reddit(self):
        from app.services.simulation_artifacts import (
            canonical_to_reddit_profiles,
            canonical_to_twitter_rows,
        )

        agent = self._agent()
        user_char = canonical_to_twitter_rows([agent])[0]["user_char"]
        persona = canonical_to_reddit_profiles([agent])[0]["persona"]

        for marker in ("losses weigh", "structural constraints for role type"):
            assert marker in persona, f"reddit persona lost {marker!r}"
            assert marker in user_char, f"twitter user_char is missing {marker!r}"

    def test_twitter_user_char_stays_single_line(self):
        """twitter_profiles.csv is a one-line-per-field format."""
        from app.services.simulation_artifacts import canonical_to_twitter_rows

        user_char = canonical_to_twitter_rows([self._agent()])[0]["user_char"]
        assert "\n" not in user_char and "\r" not in user_char

    def test_untraited_agent_is_unchanged_on_both_platforms(self):
        from app.services.simulation_artifacts import (
            canonical_to_reddit_profiles,
            canonical_to_twitter_rows,
        )

        agent = self._agent()
        agent["big_five"] = None
        agent["source_entity_type_normalized"] = ""

        assert canonical_to_twitter_rows([agent])[0]["user_char"] == "Base persona."
        assert canonical_to_reddit_profiles([agent])[0]["persona"] == "Base persona."

    def test_framing_failure_is_logged_not_silent(self, caplog):
        """A dead framing path must be visible in the logs, not indistinguishable
        from the feature having nothing to add."""
        import logging

        from app.services import simulation_artifacts

        def boom(*_args, **_kwargs):
            raise RuntimeError("projection unavailable")

        agent = self._agent()
        with caplog.at_level(logging.WARNING):
            with patch(
                "app.services.trait_behavior_projection.persona_with_framing",
                boom,
            ):
                assert simulation_artifacts.framed_persona(agent) == "Base persona."

        assert any(
            "Persona framing skipped" in record.getMessage()
            for record in caplog.records
        ), "fallback to the raw persona was not logged"

"""
Tests for constraint-engine wiring: influence_weight by role + persona framing.

Critical properties:
  1. Deterministic: same role → same weight and text
  2. Fail-open: absent/unknown roles → neutral weight (1.0), unchanged persona
  3. Direction: institutions/media amplify more than individuals; students less
  4. Correct channel: constraint framing reaches reddit_profiles.json on disk
  5. Clearly labelled: "[Scenario assumption — structural constraints"
  6. Composes with prospect framing (both layers present when applicable)
"""

import json
import os
import tempfile
import types

import pytest

from app.services.role_normalizer import normalize_entity_type
from app.services.trait_behavior_projection import (
    constraint_framing_text,
    influence_weight_from_role,
    persona_with_constraint_framing,
)


class TestInfluenceWeight:
    def test_institution_amplifies_more_than_individual(self):
        org = influence_weight_from_role(normalize_entity_type("Organization"))
        person = influence_weight_from_role(normalize_entity_type("Person"))
        assert org > person
        assert org > 1.0
        assert person == 1.0

    def test_media_amplifies(self):
        media = influence_weight_from_role(normalize_entity_type("mediaoutlet"))
        assert media > 1.0

    def test_journalist_amplifies(self):
        j = influence_weight_from_role(normalize_entity_type("journalist"))
        assert j > 1.0

    def test_official_amplifies_via_normalized_role(self):
        """Official normalizes to family=person but carries authority weight."""
        official = influence_weight_from_role(normalize_entity_type("official"))
        person = influence_weight_from_role(normalize_entity_type("Person"))
        assert official > person

    def test_expert_amplifies_slightly(self):
        expert = influence_weight_from_role(normalize_entity_type("expert"))
        person = influence_weight_from_role(normalize_entity_type("Person"))
        assert expert > person

    def test_student_is_constrained_below_baseline(self):
        student = influence_weight_from_role(normalize_entity_type("student"))
        assert student < 1.0

    def test_unknown_role_gets_neutral_weight(self):
        assert influence_weight_from_role(normalize_entity_type("trend")) == 1.0

    def test_absent_role_info_gets_neutral_weight(self):
        assert influence_weight_from_role(None) == 1.0
        assert influence_weight_from_role({}) == 1.0

    def test_deterministic(self):
        role = normalize_entity_type("Organization")
        assert influence_weight_from_role(role) == influence_weight_from_role(role)


class TestConstraintFraming:
    def test_institution_framing_mentions_resources_and_accountability(self):
        text = constraint_framing_text(normalize_entity_type("Organization"))
        assert "institutional resources" in text or "organizational resources" in text
        assert "accountability" in text or "compliance" in text

    def test_media_framing_mentions_editorial_constraints(self):
        text = constraint_framing_text(normalize_entity_type("mediaoutlet"))
        assert "editorial constraints" in text or "verification" in text

    def test_individual_framing_mentions_limited_resources(self):
        text = constraint_framing_text(normalize_entity_type("Person"))
        assert "limited" in text
        assert "out of reach" in text

    def test_unknown_role_gets_empty_framing(self):
        assert constraint_framing_text(normalize_entity_type("trend")) == ""

    def test_absent_role_info_gets_empty_framing(self):
        assert constraint_framing_text(None) == ""
        assert constraint_framing_text({}) == ""

    def test_framing_is_labelled_scenario_assumption(self):
        text = constraint_framing_text(normalize_entity_type("Organization"))
        assert "[Scenario assumption" in text
        assert "structural constraints" in text

    def test_framing_does_not_claim_measurement(self):
        text = constraint_framing_text(normalize_entity_type("Organization")).lower()
        for forbidden in ("measured", "observed", "respondent", "real person",
                          "survey", "sample", "representative"):
            assert forbidden not in text

    def test_deterministic(self):
        role = normalize_entity_type("Organization")
        assert constraint_framing_text(role) == constraint_framing_text(role)


class TestPersonaConstraintFraming:
    def test_appends_when_role_known(self):
        original = "A community organizer."
        result = persona_with_constraint_framing(original, normalize_entity_type("group"))
        assert result.startswith(original)
        assert "[Scenario assumption" in result

    def test_leaves_unchanged_for_unknown_role(self):
        original = "A trend."
        assert persona_with_constraint_framing(original, normalize_entity_type("trend")) == original

    def test_leaves_unchanged_for_absent_role(self):
        original = "A person."
        assert persona_with_constraint_framing(original, None) == original
        assert persona_with_constraint_framing(original, {}) == original


class TestEndToEndConstraintIntegration:
    def test_constraint_framing_reaches_reddit_profiles_on_disk(self):
        """The real integration test: prove it reaches the file OASIS loads."""
        from app.services.oasis_profile_generator import OasisAgentProfile
        from app.services.simulation_artifacts import (
            build_canonical_agents,
            write_exports_from_canonical,
        )

        profile = OasisAgentProfile(
            user_id=0,
            user_name="ngo",
            name="NGO",
            bio="bio",
            persona="An NGO activist.",
        )
        entity = types.SimpleNamespace(
            uuid="u0", name="NGO", summary="s", attributes={},
            get_entity_type=lambda: "Organization",
            related_edges=[], related_nodes=[],
        )
        canonical = build_canonical_agents([entity], [profile])
        tmpdir = tempfile.mkdtemp()
        write_exports_from_canonical(tmpdir, canonical)

        on_disk = json.load(open(os.path.join(tmpdir, "reddit_profiles.json"), encoding="utf-8"))
        persona = on_disk[0]["persona"]
        assert "An NGO activist." in persona
        assert "[Scenario assumption — structural constraints" in persona
        assert "organizational resources" in persona

    def test_individual_entity_gets_individual_constraints(self):
        from app.services.oasis_profile_generator import OasisAgentProfile
        from app.services.simulation_artifacts import (
            build_canonical_agents,
            write_exports_from_canonical,
        )

        profile = OasisAgentProfile(
            user_id=0, user_name="p0", name="Person", bio="bio",
            persona="A concerned resident.",
        )
        entity = types.SimpleNamespace(
            uuid="u0", name="Person", summary="s", attributes={},
            get_entity_type=lambda: "Person",
            related_edges=[], related_nodes=[],
        )
        canonical = build_canonical_agents([entity], [profile])
        tmpdir = tempfile.mkdtemp()
        write_exports_from_canonical(tmpdir, canonical)

        on_disk = json.load(open(os.path.join(tmpdir, "reddit_profiles.json"), encoding="utf-8"))
        persona = on_disk[0]["persona"]
        assert "individual with limited discretionary time" in persona

    def test_unknown_entity_leaves_persona_unchanged(self):
        from app.services.oasis_profile_generator import OasisAgentProfile
        from app.services.simulation_artifacts import (
            build_canonical_agents,
            write_exports_from_canonical,
        )

        original = "A trend that matters."
        profile = OasisAgentProfile(
            user_id=0, user_name="t0", name="Trend", bio="bio", persona=original,
        )
        entity = types.SimpleNamespace(
            uuid="u0", name="Trend", summary="s", attributes={},
            get_entity_type=lambda: "trend",
            related_edges=[], related_nodes=[],
        )
        canonical = build_canonical_agents([entity], [profile])
        tmpdir = tempfile.mkdtemp()
        write_exports_from_canonical(tmpdir, canonical)

        on_disk = json.load(open(os.path.join(tmpdir, "reddit_profiles.json"), encoding="utf-8"))
        assert on_disk[0]["persona"] == original

    def test_constraint_and_prospect_framing_compose(self):
        """Both layers present when traits AND role are known."""
        from app.services.big_five import BigFive
        from app.services.oasis_profile_generator import OasisAgentProfile
        from app.services.simulation_artifacts import (
            build_canonical_agents,
            write_exports_from_canonical,
        )

        traits = BigFive(neuroticism=85.0)
        profile = OasisAgentProfile(
            user_id=0, user_name="ngo", name="NGO", bio="bio",
            persona="An NGO activist.",
            big_five=traits.to_dict(),
        )
        entity = types.SimpleNamespace(
            uuid="u0", name="NGO", summary="s", attributes={},
            get_entity_type=lambda: "Organization",
            related_edges=[], related_nodes=[],
        )
        canonical = build_canonical_agents([entity], [profile])
        tmpdir = tempfile.mkdtemp()
        write_exports_from_canonical(tmpdir, canonical)

        on_disk = json.load(open(os.path.join(tmpdir, "reddit_profiles.json"), encoding="utf-8"))
        persona = on_disk[0]["persona"]
        # Both disclosure labels present
        assert persona.count("[Scenario assumption") >= 2
        # Both layers present
        assert "losses weigh approximately" in persona       # prospect
        assert "organizational resources" in persona          # constraint

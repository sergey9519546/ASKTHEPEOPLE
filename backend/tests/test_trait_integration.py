"""
Integration test: do source-derived traits actually reach the engine config?

The unit tests for trait_behavior_projection prove the arithmetic. These prove
the wiring — that a trait vector on a canonical agent survives the trip through
_generate_agent_configs_batch into AgentActivityConfig, and that agents without
traits are left on the neutral defaults.

Regression target: `simulation_artifacts` previously read the raw `profile.mbti`
field, so a persona carrying Big Five reached OASIS as the "ISTJ" placeholder and
its personality was silently discarded.
"""

import types

import pytest

from app.services.big_five import BigFive, to_mbti_code
from app.services.oasis_profile_generator import OasisAgentProfile
from app.services.simulation_config_generator import SimulationConfigGenerator
from app.services.trait_behavior_projection import CONTROL_BASIS_TRAIT_DERIVED


def _entity(uuid: str, name: str, etype: str = "Person"):
    """Minimal EntityNode stand-in: the batch builder only needs these members."""
    return types.SimpleNamespace(
        uuid=uuid,
        name=name,
        summary=f"{name} summary",
        get_entity_type=lambda: etype,
    )


def _generator():
    """A generator with the LLM path disabled, so only the clamp logic runs."""
    gen = SimulationConfigGenerator.__new__(SimulationConfigGenerator)
    gen.AGENT_SUMMARY_LENGTH = 200
    # Force the LLM batch call to fail so we exercise the rule-based path.
    gen._call_llm_with_retry = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("LLM disabled in test")
    )
    return gen


def _configs_for(canonical_agents, n=None):
    gen = _generator()
    count = n if n is not None else len(canonical_agents)
    entities = [_entity(f"u{i}", f"Entity {i}") for i in range(count)]
    return gen._generate_agent_configs_batch(
        context="ctx",
        entities=entities,
        start_idx=0,
        simulation_requirement="a decision",
        canonical_agents=canonical_agents,
        context_profile=None,
    )


class TestTraitsReachEngineConfig:
    def test_extravert_gets_higher_activity_than_introvert(self):
        agents = [
            {"agent_id": 0, "big_five": BigFive(extraversion=95.0).to_dict()},
            {"agent_id": 1, "big_five": BigFive(extraversion=5.0).to_dict()},
        ]
        configs = _configs_for(agents)
        assert configs[0].activity_level > configs[1].activity_level

    def test_provenance_basis_records_trait_derivation(self):
        agents = [{"agent_id": 0, "big_five": BigFive(openness=80.0).to_dict()}]
        configs = _configs_for(agents)
        assert configs[0].control_assumption_basis == CONTROL_BASIS_TRAIT_DERIVED

    def test_truth_flags_stay_false_even_with_traits(self):
        """A trait projection is a scenario assumption, never evidence."""
        agents = [{"agent_id": 0, "big_five": BigFive(extraversion=95.0).to_dict()}]
        cfg = _configs_for(agents)[0]
        assert cfg.measured_human_behavior is False
        assert cfg.human_respondents == 0
        assert cfg.causal_evidence is False
        assert cfg.behavioral_override_applied is False

    def test_population_is_no_longer_uniform(self):
        """The core regression: distinct personalities must not collapse to one config."""
        import random

        from app.services.big_five import sample_population

        rng = random.Random(31337)
        agents = [
            {"agent_id": i, "big_five": sample_population(rng=rng).to_dict()}
            for i in range(25)
        ]
        configs = _configs_for(agents)
        signatures = {
            (c.activity_level, c.conflict_tolerance, c.novelty_seeking, c.reaction_style)
            for c in configs
        }
        assert len(signatures) > 15, f"only {len(signatures)} distinct configs of 25"

    def test_reaction_style_varies_across_population(self):
        agents = [
            {"agent_id": 0, "big_five": BigFive(neuroticism=85.0, agreeableness=15.0).to_dict()},
            {"agent_id": 1, "big_five": BigFive(extraversion=85.0, openness=80.0, neuroticism=30.0).to_dict()},
            {"agent_id": 2, "big_five": BigFive(conscientiousness=90.0, extraversion=30.0, neuroticism=40.0).to_dict()},
        ]
        styles = {c.reaction_style for c in _configs_for(agents)}
        assert len(styles) >= 2

    def test_delay_window_remains_valid(self):
        agents = [{"agent_id": 0, "big_five": BigFive(extraversion=95.0, conscientiousness=5.0).to_dict()}]
        cfg = _configs_for(agents)[0]
        assert cfg.response_delay_min >= 1
        assert cfg.response_delay_max > cfg.response_delay_min


class TestAgentsWithoutTraitsUnchanged:
    """Absent traits must leave today's neutral behaviour exactly as it was."""

    def test_no_canonical_agents_keeps_neutral_defaults(self):
        cfg = _configs_for(None, n=1)[0]
        assert cfg.activity_level == 0.5
        assert cfg.conflict_tolerance == 0.45
        assert cfg.authority_sensitivity == 0.4
        assert cfg.novelty_seeking == 0.45
        assert cfg.reaction_style == "measured"
        assert cfg.control_assumption_basis == "neutral_fictional_default"

    def test_canonical_agents_without_traits_keep_neutral_defaults(self):
        agents = [{"agent_id": 0, "mbti": "INTJ", "big_five": None}]
        cfg = _configs_for(agents)[0]
        assert cfg.activity_level == 0.5
        assert cfg.control_assumption_basis == "neutral_fictional_default"

    def test_malformed_traits_degrade_to_neutral_not_crash(self):
        agents = [{"agent_id": 0, "big_five": {"openness": 5000.0}}]
        cfg = _configs_for(agents)[0]
        assert cfg.activity_level == 0.5
        assert cfg.control_assumption_basis == "neutral_fictional_default"

    def test_mixed_population_applies_traits_only_where_present(self):
        agents = [
            {"agent_id": 0, "big_five": BigFive(extraversion=95.0).to_dict()},
            {"agent_id": 1},
        ]
        configs = _configs_for(agents)
        assert configs[0].control_assumption_basis == CONTROL_BASIS_TRAIT_DERIVED
        assert configs[1].control_assumption_basis == "neutral_fictional_default"
        assert configs[1].activity_level == 0.5

    def test_fewer_canonical_agents_than_entities_is_safe(self):
        agents = [{"agent_id": 0, "big_five": BigFive(extraversion=90.0).to_dict()}]
        configs = _configs_for(agents, n=3)
        assert len(configs) == 3
        assert configs[1].control_assumption_basis == "neutral_fictional_default"


class TestMbtiInteropRegression:
    """OASIS indexes profile["other_info"]["mbti"] unconditionally."""

    def test_effective_mbti_derives_from_traits_not_placeholder(self):
        traits = BigFive(openness=88.0, conscientiousness=20.0, extraversion=85.0,
                         agreeableness=80.0, neuroticism=30.0)
        profile = OasisAgentProfile(
            user_id=1, user_name="u", name="N", bio="b", persona="p",
            big_five=traits.to_dict(),
        )
        assert profile.mbti is None          # nothing stored on the raw field
        assert profile.effective_mbti() == to_mbti_code(traits)
        assert profile.effective_mbti() != "ISTJ"

    def test_canonical_agent_carries_derived_code_and_traits(self):
        from app.services.simulation_artifacts import build_canonical_agents

        traits = BigFive(openness=88.0, conscientiousness=20.0, extraversion=85.0,
                         agreeableness=80.0, neuroticism=30.0)
        profile = OasisAgentProfile(
            user_id=0, user_name="u0", name="Zero", bio="bio", persona="persona",
            big_five=traits.to_dict(),
        )
        entity = _entity("uuid-0", "Zero")
        entity.attributes = {}
        entity.labels = []
        entity.created_at = None
        # _build_graph_records reads both relation collections.
        entity.related_edges = []
        entity.related_nodes = []

        canonical = build_canonical_agents([entity], [profile])
        assert canonical[0]["mbti"] == to_mbti_code(traits)
        assert canonical[0]["mbti"] != "ISTJ"
        assert canonical[0]["big_five"] == traits.to_dict()

    def test_profile_without_traits_still_gets_valid_code(self):
        """Never None: a missing key raises KeyError inside OASIS."""
        profile = OasisAgentProfile(
            user_id=1, user_name="u", name="N", bio="b", persona="p",
        )
        assert profile.effective_mbti() == "ISTJ"

    def test_stored_mbti_used_when_no_traits(self):
        profile = OasisAgentProfile(
            user_id=1, user_name="u", name="N", bio="b", persona="p", mbti="ENTP",
        )
        assert profile.effective_mbti() == "ENTP"

    def test_traits_take_precedence_over_stored_code(self):
        traits = BigFive(openness=90.0, conscientiousness=90.0,
                         extraversion=90.0, agreeableness=90.0)
        profile = OasisAgentProfile(
            user_id=1, user_name="u", name="N", bio="b", persona="p",
            mbti="ISTJ", big_five=traits.to_dict(),
        )
        assert profile.effective_mbti() == "ENFJ"

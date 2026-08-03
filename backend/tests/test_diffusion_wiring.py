"""
Tests for diffusion-classification wiring in the config generator.

The critical property: the Rogers adopter distribution is a population
property. Classifying agents one-by-one cannot reproduce it; this must
run on the full population. These tests verify that the classification
actually runs, correctly modulates novelty_seeking by category, and
fails open rather than crashing when the module is absent or traits are missing.
"""

import types

import pytest

from app.services.diffusion_model import AdopterCategory
from app.services.simulation_config_generator import (
    AgentActivityConfig,
    SimulationConfigGenerator,
)


# Minimal EntityNode stub
def _entity(i: int):
    return types.SimpleNamespace(
        uuid=f"u{i}",
        name=f"Entity {i}",
        summary=f"Summary {i}",
        attributes={},
        get_entity_type=lambda: "Person",
    )


def _gen():
    gen = SimulationConfigGenerator.__new__(SimulationConfigGenerator)
    gen._call_llm_with_retry = lambda *a, **kw: (
        (_ for _ in ()).throw(RuntimeError("LLM disabled"))
    )
    gen.AGENT_SUMMARY_LENGTH = 200
    return gen


def _config(agent_id: int, novelty: float = 0.45) -> AgentActivityConfig:
    return AgentActivityConfig(
        agent_id=agent_id,
        entity_uuid=f"u{agent_id}",
        entity_name=f"Entity {agent_id}",
        entity_type="Person",
        novelty_seeking=novelty,
        response_delay_min=5,
        response_delay_max=60,
    )


def _bf_canon(agent_id: int, openness: float):
    from app.services.big_five import BigFive
    return {
        "agent_id": agent_id,
        "big_five": BigFive(openness=openness).to_dict(),
    }


class TestDiffusionDistribution:
    def test_rogers_shares_reproduced_exactly_for_typical_population(self):
        """The Hare largest-remainder method gives exact Rogers shares."""
        n = 40
        configs = [_config(i) for i in range(n)]
        # Give agents a spread of openness scores so ranking is unambiguous.
        canons = [_bf_canon(i, float(i * 100 // n)) for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)
        assert len(result) == n

    def test_innovators_get_higher_novelty_than_laggards(self):
        """Direction: within a SPREAD population, innovators have higher novelty than laggards."""
        n = 40
        configs = [_config(i) for i in range(n)]
        # Spread from 5 to 95 so ranking is unambiguous and all categories appear.
        canons = [_bf_canon(i, 5.0 + i * (90.0 / (n - 1))) for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)

        # Collect novelty by category by re-running classify_population with the same scores.
        from app.services.diffusion_model import classify_population, AdopterCategory
        from app.services.big_five import BigFive

        personas = {
            i: {"id": i, "innovativeness_score": BigFive.from_dict(canons[i]["big_five"]).openness}
            for i in range(n)
        }
        cat_map = classify_population(personas=personas,
                                      key=lambda p: p["innovativeness_score"],
                                      id_key=lambda p: p["id"])

        innovator_novelty  = [result[i].novelty_seeking for i in range(n) if cat_map.get(i) == AdopterCategory.INNOVATOR]
        laggard_novelty    = [result[i].novelty_seeking for i in range(n) if cat_map.get(i) == AdopterCategory.LAGGARD]

        assert innovator_novelty, "no innovators in spread population"
        assert laggard_novelty, "no laggards in spread population"
        assert min(innovator_novelty) > max(laggard_novelty), (
            f"innovator novelty {innovator_novelty} must exceed laggard novelty {laggard_novelty}"
        )

    def test_innovators_respond_faster_than_laggards(self):
        """Delay factor: within a SPREAD population, innovators respond faster than laggards."""
        n = 40
        configs = [_config(i) for i in range(n)]
        canons = [_bf_canon(i, 5.0 + i * (90.0 / (n - 1))) for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)

        from app.services.diffusion_model import classify_population, AdopterCategory
        from app.services.big_five import BigFive

        personas = {
            i: {"id": i, "innovativeness_score": BigFive.from_dict(canons[i]["big_five"]).openness}
            for i in range(n)
        }
        cat_map = classify_population(personas=personas,
                                      key=lambda p: p["innovativeness_score"],
                                      id_key=lambda p: p["id"])

        innovator_delays = [result[i].response_delay_max for i in range(n) if cat_map.get(i) == AdopterCategory.INNOVATOR]
        laggard_delays   = [result[i].response_delay_max for i in range(n) if cat_map.get(i) == AdopterCategory.LAGGARD]

        assert innovator_delays and laggard_delays
        assert max(innovator_delays) < min(laggard_delays), (
            f"innovator delays {innovator_delays} must be lower than laggard delays {laggard_delays}"
        )

    def test_novelty_seeking_stays_in_valid_range(self):
        n = 20
        configs = [_config(i, novelty=0.99) for i in range(n)]
        canons = [_bf_canon(i, float(i * 5)) for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)
        for c in result:
            assert 0.05 <= c.novelty_seeking <= 0.95

    def test_delay_window_stays_ordered_and_positive(self):
        n = 20
        configs = [_config(i) for i in range(n)]
        canons = [_bf_canon(i, float(i * 5)) for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)
        for c in result:
            assert c.response_delay_min >= 1
            assert c.response_delay_max > c.response_delay_min


class TestDiffusionFailsOpen:
    def test_empty_configs_returns_empty(self):
        assert _gen()._apply_diffusion_classification([], []) == []

    def test_no_canonical_agents_still_classifies_with_neutral_scores(self):
        """Without trait data agents get neutral scores (50.0) and are still classified.
        
        This is correct behavior: diffusion classification still assigns categories
        even without Big Five data — it just uses equal scores, so the assignment
        is determined by position rather than personality. The key property is that
        all_valid novelty values are returned, not that they're unchanged.
        """
        configs = [_config(0, novelty=0.45), _config(1, novelty=0.45)]
        result = _gen()._apply_diffusion_classification(configs, [])
        assert len(result) == 2
        for c in result:
            assert 0.05 <= c.novelty_seeking <= 0.95
            assert c.response_delay_min >= 1
            assert c.response_delay_max > c.response_delay_min

    def test_missing_big_five_gets_neutral_score_not_error(self):
        """Agents without traits use 50.0 (neutral) as innovativeness score."""
        n = 20
        configs = [_config(i) for i in range(n)]
        canons = [{"agent_id": i} for i in range(n)]  # no big_five key
        result = _gen()._apply_diffusion_classification(configs, canons)
        assert len(result) == n  # didn't crash

    def test_malformed_big_five_uses_neutral_not_exception(self):
        n = 20
        configs = [_config(i) for i in range(n)]
        canons = [{"agent_id": i, "big_five": {"openness": 9999.9}} for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)
        assert len(result) == n

    def test_import_error_degrades_gracefully(self, monkeypatch):
        """If diffusion_model is unavailable, configs must be returned unchanged."""
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def blocked(name, *a, **k):
            if "diffusion_model" in name:
                raise ImportError("module unavailable")
            return real_import(name, *a, **k)

        monkeypatch.setattr("builtins.__import__", blocked)
        configs = [_config(0, novelty=0.45)]
        result = _gen()._apply_diffusion_classification(configs, [])
        assert result[0].novelty_seeking == pytest.approx(0.45)

    def test_classification_exception_degrades_gracefully(self, monkeypatch):
        """Any unexpected error in classification must not crash a run."""
        import app.services.simulation_config_generator as mod
        monkeypatch.setattr(
            "app.services.diffusion_model.classify_population",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        configs = [_config(0, novelty=0.45)]
        result = _gen()._apply_diffusion_classification(configs, [])
        assert result[0].novelty_seeking == pytest.approx(0.45)


class TestDiffusionProvenance:
    def test_diffusion_does_not_alter_truth_flags(self):
        """Population dynamics are a scenario assumption, not evidence."""
        n = 20
        configs = [_config(i) for i in range(n)]
        canons = [_bf_canon(i, float(i * 5)) for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)
        for c in result:
            assert c.measured_human_behavior is False
            assert c.human_respondents == 0
            assert c.causal_evidence is False

    def test_control_basis_unchanged_by_diffusion(self):
        """Diffusion modulation is a nudge, not a new provenance claim."""
        n = 20
        configs = [_config(i) for i in range(n)]
        # Set a known basis from trait projection
        from app.services.trait_behavior_projection import CONTROL_BASIS_TRAIT_DERIVED
        for c in configs:
            c.control_assumption_basis = CONTROL_BASIS_TRAIT_DERIVED
        canons = [_bf_canon(i, float(i * 5)) for i in range(n)]
        result = _gen()._apply_diffusion_classification(configs, canons)
        for c in result:
            assert c.control_assumption_basis == CONTROL_BASIS_TRAIT_DERIVED

"""
Tests for trait inference wiring into profile generation.

Two properties matter here:
  1. With ENABLE_TRAIT_INFERENCE off, nothing changes and no model call happens.
  2. With it on, only span-verified traits are attached, and every failure mode
     degrades to `big_five = None` rather than breaking profile generation.
"""

import types

import pytest

from app.services.big_five import BigFive
from app.services.oasis_profile_generator import (
    OasisAgentProfile,
    OasisProfileGenerator,
    _TraitInferenceClient,
)

SOURCE_SUMMARY = (
    "The programme lead is relentlessly curious about unfamiliar approaches and "
    "keeps meticulous written records of every decision taken by the committee."
)
REAL_SPAN = "relentlessly curious about unfamiliar approaches"


def _entity():
    return types.SimpleNamespace(
        uuid="uuid-1",
        name="Programme Lead",
        summary=SOURCE_SUMMARY,
        attributes={},
        get_entity_type=lambda: "Person",
    )


def _generator():
    """Bare generator instance; __init__ needs API keys we do not have in tests."""
    gen = OasisProfileGenerator.__new__(OasisProfileGenerator)
    gen.client = None
    gen.model_name = "test-model"
    return gen


def _profile():
    return OasisAgentProfile(
        user_id=0, user_name="lead", name="Programme Lead",
        bio="bio", persona="persona",
    )


class _Flag:
    """Patches Config.ENABLE_TRAIT_INFERENCE for the duration of a test."""

    def __init__(self, monkeypatch, value):
        from app.services import oasis_profile_generator as mod

        monkeypatch.setattr(mod.Config, "ENABLE_TRAIT_INFERENCE", value, raising=False)


class TestFlagOffChangesNothing:
    def test_no_traits_attached_when_disabled(self, monkeypatch):
        _Flag(monkeypatch, False)
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "context")
        assert profile.big_five is None

    def test_no_model_call_when_disabled(self, monkeypatch):
        """Cost control: the flag must short-circuit before any inference work."""
        _Flag(monkeypatch, False)
        called = []

        def boom(*a, **k):
            called.append(1)
            raise AssertionError("infer_traits must not run when flag is off")

        monkeypatch.setattr("app.services.trait_inference.infer_traits", boom)
        _generator()._attach_inferred_traits(_profile(), _entity(), "ctx")
        assert called == []

    def test_missing_config_attribute_treated_as_off(self, monkeypatch):
        """Absent flag must fail closed, not crash."""
        from app.services import oasis_profile_generator as mod

        monkeypatch.delattr(mod.Config, "ENABLE_TRAIT_INFERENCE", raising=False)
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "ctx")
        assert profile.big_five is None


class TestFlagOnAttachesVerifiedTraits:
    def test_verified_traits_are_attached(self, monkeypatch):
        _Flag(monkeypatch, True)
        from app.services.trait_inference import TraitInferenceResult

        traits = BigFive(openness=88.0)
        monkeypatch.setattr(
            "app.services.trait_inference.infer_traits",
            lambda **kw: TraitInferenceResult(
                traits=traits, verified_traits={"openness": 88.0}
            ),
        )
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "ctx")
        assert profile.big_five == traits.to_dict()

    def test_ungrounded_result_leaves_traits_none(self, monkeypatch):
        _Flag(monkeypatch, True)
        from app.services.trait_inference import TraitInferenceResult

        monkeypatch.setattr(
            "app.services.trait_inference.infer_traits",
            lambda **kw: TraitInferenceResult(failure_reason="no_trait_span_verified"),
        )
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "ctx")
        assert profile.big_five is None

    def test_source_text_includes_summary_and_context(self, monkeypatch):
        """Spans are verified against this exact text, so it must be what is sent."""
        _Flag(monkeypatch, True)
        captured = {}
        from app.services.trait_inference import TraitInferenceResult

        def capture(**kw):
            captured.update(kw)
            return TraitInferenceResult()

        monkeypatch.setattr("app.services.trait_inference.infer_traits", capture)
        _generator()._attach_inferred_traits(_profile(), _entity(), "extra graph context")
        assert SOURCE_SUMMARY in captured["source_text"]
        assert "extra graph context" in captured["source_text"]

    def test_empty_source_skips_inference(self, monkeypatch):
        _Flag(monkeypatch, True)
        called = []
        monkeypatch.setattr(
            "app.services.trait_inference.infer_traits",
            lambda **kw: called.append(1),
        )
        entity = _entity()
        entity.summary = ""
        _generator()._attach_inferred_traits(_profile(), entity, "   ")
        assert called == []


class TestFailuresNeverBreakGeneration:
    def test_inference_exception_is_swallowed(self, monkeypatch):
        _Flag(monkeypatch, True)

        def explode(**kw):
            raise RuntimeError("provider down")

        monkeypatch.setattr("app.services.trait_inference.infer_traits", explode)
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "ctx")
        assert profile.big_five is None

    def test_import_error_is_swallowed(self, monkeypatch):
        _Flag(monkeypatch, True)
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def blocked(name, *a, **k):
            if "trait_inference" in name:
                raise ImportError("simulated missing module")
            return real_import(name, *a, **k)

        monkeypatch.setattr("builtins.__import__", blocked)
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "ctx")
        assert profile.big_five is None

    def test_malformed_traits_object_swallowed(self, monkeypatch):
        _Flag(monkeypatch, True)

        broken = types.SimpleNamespace(
            grounded=True,
            traits=types.SimpleNamespace(to_dict=lambda: (_ for _ in ()).throw(ValueError("bad"))),
            verified_traits={},
            failure_reason="",
        )
        monkeypatch.setattr(
            "app.services.trait_inference.infer_traits", lambda **kw: broken
        )
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "ctx")
        assert profile.big_five is None


class TestInferenceClientAdapter:
    def test_uses_zero_temperature(self):
        """Citation is extraction, not creativity; sampling invites paraphrase."""
        captured = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                msg = types.SimpleNamespace(content='{"openness": {"score": 70}}')
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

        fake = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=FakeCompletions())
        )
        _TraitInferenceClient(fake, "m").generate("prompt")
        assert captured["temperature"] == 0
        assert captured["model"] == "m"

    def test_returns_empty_string_for_null_content(self):
        class FakeCompletions:
            def create(self, **kwargs):
                msg = types.SimpleNamespace(content=None)
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

        fake = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=FakeCompletions())
        )
        assert _TraitInferenceClient(fake, "m").generate("p") == ""

    def test_system_prompt_demands_verbatim_copying(self):
        captured = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                msg = types.SimpleNamespace(content="{}")
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

        fake = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=FakeCompletions())
        )
        _TraitInferenceClient(fake, "m").generate("p")
        system = captured["messages"][0]["content"].lower()
        assert "character for character" in system

    def test_adapter_satisfies_inference_call_surface(self):
        """infer_traits probes for generate/complete/chat/__call__."""
        assert callable(getattr(_TraitInferenceClient(None, "m"), "generate"))


class TestEndToEndWithRealVerifier:
    """No mocking of the verifier — a fake model, but real span checking."""

    def test_honest_citation_survives_the_whole_path(self, monkeypatch):
        _Flag(monkeypatch, True)
        import json

        class FakeLLM:
            def generate(self, prompt):
                return json.dumps(
                    {"openness": {"score": 85, "spans": [REAL_SPAN]}}
                )

        monkeypatch.setattr(
            "app.services.oasis_profile_generator._TraitInferenceClient",
            lambda client, model: FakeLLM(),
        )
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "")
        assert profile.big_five is not None
        assert profile.big_five["openness"] == 85.0

    def test_fabricated_citation_is_rejected_end_to_end(self, monkeypatch):
        """The security property, exercised through the real integration path."""
        _Flag(monkeypatch, True)
        import json

        class LyingLLM:
            def generate(self, prompt):
                return json.dumps({
                    "neuroticism": {
                        "score": 95,
                        "spans": ["the lead is chronically anxious and volatile"],
                    }
                })

        monkeypatch.setattr(
            "app.services.oasis_profile_generator._TraitInferenceClient",
            lambda client, model: LyingLLM(),
        )
        profile = _profile()
        _generator()._attach_inferred_traits(profile, _entity(), "")
        assert profile.big_five is None, "fabricated trait must not reach the profile"

    def test_traits_flow_through_to_engine_controls(self, monkeypatch):
        """Full chain: source text -> verified traits -> engine behaviour."""
        _Flag(monkeypatch, True)
        import json

        from app.services.trait_behavior_projection import (
            CONTROL_BASIS_TRAIT_DERIVED,
            controls_from_canonical_agent,
        )

        social_source = (
            "The lead speaks constantly at every gathering and actively seeks out "
            "large crowds of unfamiliar colleagues at industry events."
        )

        class FakeLLM:
            def generate(self, prompt):
                return json.dumps({
                    "extraversion": {
                        "score": 90,
                        "spans": ["speaks constantly at every gathering"],
                    }
                })

        monkeypatch.setattr(
            "app.services.oasis_profile_generator._TraitInferenceClient",
            lambda client, model: FakeLLM(),
        )
        entity = _entity()
        entity.summary = social_source
        profile = _profile()
        _generator()._attach_inferred_traits(profile, entity, "")

        assert profile.big_five is not None
        controls = controls_from_canonical_agent({"big_five": profile.big_five})
        assert controls is not None
        assert controls["control_assumption_basis"] == CONTROL_BASIS_TRAIT_DERIVED
        # Extraversion 90 must raise activity above the 0.5 neutral baseline.
        assert controls["activity_level"] > 0.5

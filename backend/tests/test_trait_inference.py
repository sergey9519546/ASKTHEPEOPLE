"""
Tests for span-verified trait inference.

The security property under test: a model CANNOT get a trait accepted without
quoting the source correctly. Most of these tests are adversarial — they try to
sneak a fabricated trait past the verifier. If any succeeds, the module's whole
justification for bypassing the behavioural clamp collapses.
"""

import pytest

from app.services.big_five import TRAITS, BigFive
from app.services.trait_inference import (
    EVIDENCE_CLASS,
    MIN_SPAN_CHARS,
    TraitInferenceResult,
    build_inference_prompt,
    infer_traits,
    verify_span,
    verify_trait_claims,
    _normalise,
)

SOURCE = (
    "The committee chair is relentlessly curious about unfamiliar approaches and "
    "frequently proposes experimental pilots that colleagues consider premature. "
    "She keeps meticulous written records of every decision and never misses a "
    "deadline. In contested meetings she avoids open disagreement and defers to "
    "the most senior voice in the room."
)

# Long enough to clear MIN_SPAN_CHARS and present verbatim in SOURCE.
REAL_SPAN = "relentlessly curious about unfamiliar approaches"
REAL_SPAN_2 = "keeps meticulous written records of every decision"


def _claim(score, spans):
    return {"score": score, "spans": spans}


class FakeLLM:
    """Returns a canned response; records the prompt it was given."""

    def __init__(self, response):
        self.response = response
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.response


class ExplodingLLM:
    def generate(self, prompt):
        raise RuntimeError("upstream 503")


class TestSpanVerificationAcceptsHonestQuotes:
    def test_exact_quote_verifies(self):
        assert verify_span(REAL_SPAN, _normalise(SOURCE)).verified

    def test_whitespace_reformatting_tolerated(self):
        messy = REAL_SPAN.replace(" ", "   \n ")
        assert verify_span(messy, _normalise(SOURCE)).verified

    def test_case_change_tolerated(self):
        assert verify_span(REAL_SPAN.upper(), _normalise(SOURCE)).verified

    def test_curly_quote_substitution_tolerated(self):
        src = 'She said "the pilot programme is premature" in the review meeting.'
        quoted = 'She said \u201cthe pilot programme is premature\u201d in the review'
        assert verify_span(quoted, _normalise(src)).verified

    def test_unicode_dash_variants_tolerated(self):
        src = "The chair - always curious - proposed another unfamiliar pilot."
        quoted = "The chair \u2014 always curious \u2014 proposed another unfamiliar pilot."
        assert verify_span(quoted, _normalise(src)).verified


class TestSpanVerificationRejectsFabrication:
    """Adversarial. Each of these must FAIL to verify."""

    def test_pure_invention_rejected(self):
        check = verify_span(
            "The chair is a thrill-seeking skydiver with three doctorates",
            _normalise(SOURCE),
        )
        assert not check.verified
        assert check.reason == "not_found_in_source"

    def test_paraphrase_rejected(self):
        """Semantically faithful but not verbatim — must still be rejected."""
        check = verify_span(
            "The chairperson is extremely inquisitive about new methods",
            _normalise(SOURCE),
        )
        assert not check.verified

    def test_single_inserted_word_rejected(self):
        check = verify_span(
            "relentlessly curious about very unfamiliar approaches", _normalise(SOURCE)
        )
        assert not check.verified

    def test_single_removed_word_rejected(self):
        check = verify_span(
            "relentlessly curious unfamiliar approaches", _normalise(SOURCE)
        )
        assert not check.verified

    def test_negation_flip_rejected(self):
        """The most dangerous fabrication: inverting meaning while looking similar."""
        check = verify_span(
            "relentlessly incurious about unfamiliar approaches", _normalise(SOURCE)
        )
        assert not check.verified

    def test_span_below_minimum_length_rejected(self):
        check = verify_span("curious", _normalise(SOURCE))
        assert not check.verified
        assert "shorter_than" in check.reason

    def test_common_short_word_cannot_verify(self):
        """Without a length floor, 'the' would match almost any document."""
        assert not verify_span("the", _normalise(SOURCE)).verified

    def test_non_string_span_rejected(self):
        for bad in (None, 42, [], {}, True):
            assert not verify_span(bad, _normalise(SOURCE)).verified

    def test_whitespace_only_span_rejected(self):
        assert not verify_span(" " * 60, _normalise(SOURCE)).verified

    def test_padded_short_claim_still_rejected(self):
        """Padding a real short word to clear the length floor must not work."""
        assert not verify_span("curious " * 6, _normalise(SOURCE)).verified


class TestTraitClaimVerification:
    def test_supported_trait_accepted(self):
        verified, rejected, _ = verify_trait_claims(
            {"openness": _claim(82, [REAL_SPAN])}, SOURCE
        )
        assert verified == {"openness": 82.0}
        assert "openness" not in rejected

    def test_unsupported_trait_dropped(self):
        verified, rejected, _ = verify_trait_claims(
            {"neuroticism": _claim(90, ["he panics constantly under mild pressure"])},
            SOURCE,
        )
        assert verified == {}
        assert "no_span_verified" in rejected["neuroticism"]

    def test_mixed_claims_partially_accepted(self):
        verified, rejected, _ = verify_trait_claims(
            {
                "openness": _claim(80, [REAL_SPAN]),
                "conscientiousness": _claim(85, [REAL_SPAN_2]),
                "neuroticism": _claim(95, ["invented volatility not in the text"]),
            },
            SOURCE,
        )
        assert set(verified) == {"openness", "conscientiousness"}
        assert "neuroticism" in rejected

    def test_one_good_span_among_bad_suffices(self):
        verified, _, _ = verify_trait_claims(
            {"openness": _claim(70, ["fabricated quote here padded out", REAL_SPAN])},
            SOURCE,
        )
        assert "openness" in verified

    def test_score_out_of_range_rejected(self):
        for bad in (-5, 101, 1000):
            verified, rejected, _ = verify_trait_claims(
                {"openness": _claim(bad, [REAL_SPAN])}, SOURCE
            )
            assert verified == {}
            assert rejected["openness"] == "score_missing_or_out_of_range"

    def test_non_numeric_score_rejected(self):
        for bad in ("high", None, [], {}):
            verified, _, _ = verify_trait_claims(
                {"openness": _claim(bad, [REAL_SPAN])}, SOURCE
            )
            assert verified == {}

    def test_boolean_score_rejected(self):
        """True == 1 in Python; a bool must not be read as a score."""
        verified, _, _ = verify_trait_claims(
            {"openness": _claim(True, [REAL_SPAN])}, SOURCE
        )
        assert verified == {}

    def test_nan_score_rejected(self):
        verified, _, _ = verify_trait_claims(
            {"openness": _claim(float("nan"), [REAL_SPAN])}, SOURCE
        )
        assert verified == {}

    def test_missing_spans_rejected(self):
        verified, rejected, _ = verify_trait_claims({"openness": {"score": 80}}, SOURCE)
        assert verified == {}
        assert rejected["openness"] == "no_spans_supplied"

    def test_empty_span_list_rejected(self):
        verified, rejected, _ = verify_trait_claims(
            {"openness": _claim(80, [])}, SOURCE
        )
        assert rejected["openness"] == "no_spans_supplied"

    def test_bare_string_span_accepted_as_single(self):
        verified, _, _ = verify_trait_claims(
            {"openness": {"score": 80, "spans": REAL_SPAN}}, SOURCE
        )
        assert "openness" in verified

    def test_empty_source_rejects_everything(self):
        verified, rejected, _ = verify_trait_claims(
            {"openness": _claim(80, [REAL_SPAN])}, ""
        )
        assert verified == {}
        assert all(r == "empty_source_text" for r in rejected.values())

    def test_non_dict_claims_rejected(self):
        for bad in ([], "openness=80", 42, None):
            verified, rejected, _ = verify_trait_claims(bad, SOURCE)
            assert verified == {}
            assert rejected

    def test_empty_claims_yields_nothing(self):
        verified, _, _ = verify_trait_claims({}, SOURCE)
        assert verified == {}


class TestInferTraitsEndToEnd:
    def test_grounded_inference_returns_traits(self):
        llm = FakeLLM(f'{{"openness": {{"score": 85, "spans": ["{REAL_SPAN}"]}}}}')
        result = infer_traits("Chair", SOURCE, llm)
        assert result.grounded
        assert result.traits.openness == 85.0

    def test_unverified_trait_yields_no_traits(self):
        llm = FakeLLM('{"openness": {"score": 85, "spans": ["nothing like the source"]}}')
        result = infer_traits("Chair", SOURCE, llm)
        assert not result.grounded
        assert result.traits is None
        assert result.failure_reason == "no_trait_span_verified"

    def test_unverified_traits_stay_at_midpoint(self):
        """Partial grounding: evidenced traits move, the rest remain neutral."""
        llm = FakeLLM(f'{{"openness": {{"score": 90, "spans": ["{REAL_SPAN}"]}}}}')
        result = infer_traits("Chair", SOURCE, llm)
        assert result.traits.openness == 90.0
        assert result.traits.neuroticism == 50.0
        assert result.traits.extraversion == 50.0

    def test_empty_object_response_is_valid_and_ungrounded(self):
        """Returning {} is the correct answer for unsupportive text."""
        result = infer_traits("Chair", SOURCE, FakeLLM("{}"))
        assert not result.grounded

    def test_code_fenced_json_parsed(self):
        llm = FakeLLM(
            f'```json\n{{"openness": {{"score": 75, "spans": ["{REAL_SPAN}"]}}}}\n```'
        )
        assert infer_traits("Chair", SOURCE, llm).grounded

    def test_json_embedded_in_prose_parsed(self):
        llm = FakeLLM(
            f'Here is my analysis: {{"openness": {{"score": 75, '
            f'"spans": ["{REAL_SPAN}"]}}}} Hope that helps!'
        )
        assert infer_traits("Chair", SOURCE, llm).grounded

    def test_model_exception_degrades_not_raises(self):
        result = infer_traits("Chair", SOURCE, ExplodingLLM())
        assert not result.grounded
        assert "model_call_failed" in result.failure_reason

    def test_unparseable_output_degrades(self):
        result = infer_traits("Chair", SOURCE, FakeLLM("I cannot help with that."))
        assert not result.grounded
        assert result.failure_reason == "unparseable_model_output"

    def test_json_array_response_rejected(self):
        result = infer_traits("Chair", SOURCE, FakeLLM('["openness", 80]'))
        assert not result.grounded

    def test_no_source_text_short_circuits(self):
        llm = FakeLLM("should never be called")
        result = infer_traits("Chair", "", llm)
        assert not result.grounded
        assert result.failure_reason == "no_source_text"
        assert llm.prompts == []

    def test_no_llm_client_degrades(self):
        result = infer_traits("Chair", SOURCE, None)
        assert not result.grounded
        assert result.failure_reason == "no_llm_client"

    def test_client_without_known_method_degrades(self):
        class Useless:
            pass

        result = infer_traits("Chair", SOURCE, Useless())
        assert not result.grounded
        assert "model_call_failed" in result.failure_reason

    def test_all_five_traits_can_be_grounded(self):
        rich = (
            "She is relentlessly curious about unfamiliar approaches to the problem. "
            "She keeps meticulous written records of every single decision made. "
            "She speaks constantly at every gathering and seeks out large crowds. "
            "She avoids open disagreement and defers to the most senior voice. "
            "She becomes visibly anxious whenever a deadline is threatened at all."
        )
        claims = {
            "openness": _claim(85, ["relentlessly curious about unfamiliar approaches"]),
            "conscientiousness": _claim(90, ["meticulous written records of every single decision"]),
            "extraversion": _claim(80, ["speaks constantly at every gathering"]),
            "agreeableness": _claim(75, ["avoids open disagreement and defers to the most senior"]),
            "neuroticism": _claim(70, ["visibly anxious whenever a deadline is threatened"]),
        }
        import json

        result = infer_traits("Chair", rich, FakeLLM(json.dumps(claims)))
        assert result.grounded
        assert len(result.verified_traits) == 5


class TestProvenanceRecord:
    def test_provenance_lists_verified_and_rejected(self):
        llm = FakeLLM(
            f'{{"openness": {{"score": 80, "spans": ["{REAL_SPAN}"]}},'
            f' "neuroticism": {{"score": 90, "spans": ["fabricated padding text here"]}}}}'
        )
        prov = infer_traits("Chair", SOURCE, llm).provenance()
        assert prov["verified_traits"] == ["openness"]
        assert "neuroticism" in prov["rejected_traits"]
        assert prov["grounded"] is True

    def test_provenance_records_verified_spans(self):
        llm = FakeLLM(f'{{"openness": {{"score": 80, "spans": ["{REAL_SPAN}"]}}}}')
        prov = infer_traits("Chair", SOURCE, llm).provenance()
        assert REAL_SPAN in prov["verified_spans"]["openness"]

    def test_provenance_never_claims_human_measurement(self):
        """Verified provenance is not evidence about a real person."""
        llm = FakeLLM(f'{{"openness": {{"score": 80, "spans": ["{REAL_SPAN}"]}}}}')
        prov = infer_traits("Chair", SOURCE, llm).provenance()
        assert prov["measured_human_behavior"] is False
        assert prov["human_respondents"] == 0
        assert prov["causal_evidence"] is False

    def test_evidence_class_avoids_overclaiming_words(self):
        cls = EVIDENCE_CLASS.lower()
        for forbidden in ("measured", "observed", "representative", "forecast", "predicted"):
            assert forbidden not in cls

    def test_provenance_available_even_on_total_failure(self):
        prov = infer_traits("Chair", SOURCE, ExplodingLLM()).provenance()
        assert prov["grounded"] is False
        assert prov["verified_traits"] == []
        assert prov["measured_human_behavior"] is False


class TestPromptContract:
    def test_prompt_demands_exact_copying(self):
        prompt = build_inference_prompt("Chair", SOURCE)
        lowered = prompt.lower()
        assert "exactly" in lowered or "character for character" in lowered
        assert "do not paraphrase" in lowered

    def test_prompt_states_spans_are_checked(self):
        assert "substring match" in build_inference_prompt("Chair", SOURCE).lower()

    def test_prompt_permits_and_encourages_omission(self):
        lowered = build_inference_prompt("Chair", SOURCE).lower()
        assert "omit" in lowered
        assert "do not guess" in lowered

    def test_prompt_declines_psychological_assessment_framing(self):
        assert "not a psychological" in build_inference_prompt("Chair", SOURCE).lower()

    def test_prompt_includes_the_source(self):
        assert REAL_SPAN in build_inference_prompt("Chair", SOURCE)

    def test_prompt_truncates_very_long_source(self):
        huge = "word " * 200_000
        assert len(build_inference_prompt("Chair", huge)) < 20_000

    def test_prompt_states_minimum_span_length(self):
        assert str(MIN_SPAN_CHARS) in build_inference_prompt("Chair", SOURCE)


class TestDeterminism:
    def test_verification_is_deterministic(self):
        claims = {"openness": _claim(80, [REAL_SPAN])}
        first = verify_trait_claims(claims, SOURCE)[0]
        for _ in range(20):
            assert verify_trait_claims(claims, SOURCE)[0] == first

    def test_verifier_makes_no_model_call(self):
        """Verification must stand alone; that is what makes it mechanical."""
        import app.services.trait_inference as mod

        source = open(mod.__file__, encoding="utf-8").read()
        verifier_region = source[
            source.index("def verify_trait_claims") : source.index("def build_inference_prompt")
        ]
        for banned in ("LLMClient", "openai", "requests.", "_call_model"):
            assert banned not in verifier_region

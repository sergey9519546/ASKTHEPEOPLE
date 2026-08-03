"""
Infer Big Five traits from supplied source material, with mechanical verification.

Why this is not just "ask the LLM for trait scores"
---------------------------------------------------
`simulation_config_generator` hard-clamps behavioural controls to neutral
defaults "until source-constraint provenance can be verified **mechanically**"
(simulation_config_generator.py:1090-1093). An LLM returning
`{"openness": 82}` satisfies nothing: there is no way to check the number
against anything, so it is exactly the unverifiable proposal the clamp rejects.

This module therefore requires the model to produce, for every trait it scores,
one or more **verbatim spans** from the supplied text. Each span is then checked
by literal substring match against the real source. A trait survives only if at
least one of its spans is found. Everything else is dropped.

That check is mechanical in the sense the clamp requires: it is deterministic,
runs without a model, and fails closed. The model proposes; arithmetic and
string matching decide.

What this does and does not establish
-------------------------------------
A verified span proves the quoted text EXISTS IN THE SUPPLIED MATERIAL. It does
not prove the text is true, that it describes a real person, that the trait
inference from it is correct, or that any real individual holds these traits.
It establishes provenance, not accuracy.

A span can be verified and the inference from it still be wrong. This is a
grounding mechanism, not a measurement instrument. Nothing here is a claim about
a real person's personality.

Failure posture
---------------
Every failure path returns fewer traits, never invented ones:
  - no source text          -> None
  - model call fails        -> None
  - malformed JSON          -> None
  - span not found in source-> that trait dropped
  - no trait survives       -> None
`None` means the caller keeps neutral defaults. Absence of evidence never
becomes evidence.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger
from .big_five import TRAITS, BigFive, clamp

logger = get_logger(__name__)

# A span shorter than this matches too easily by chance ("the", "a person") and
# would make verification meaningless. ASSUMPTION: 24 chars is a judgement call,
# chosen to be long enough that an incidental match is unlikely in prose.
MIN_SPAN_CHARS = 24

# Cap spans considered per trait, to bound cost of verification.
MAX_SPANS_PER_TRAIT = 4

# Truncate the material shown to the model. Long inputs raise cost and dilute
# attention without improving grounding.
MAX_SOURCE_CHARS = 12_000

# Provenance tag. Matches the evidence_class vocabulary in report_evidence.py
# and deliberately avoids implying measurement of a real human.
EVIDENCE_CLASS = "source_grounded_trait_inference"


def _normalise(text: str) -> str:
    """
    Fold text for tolerant-but-honest substring matching.

    Models routinely alter whitespace and convert straight quotes to curly ones
    when quoting. Matching raw would reject correct citations for cosmetic
    reasons. Unicode is NFKC-normalised, quote/dash variants are unified,
    whitespace is collapsed, and case is folded.

    This tolerates reformatting. It does NOT tolerate changed wording: any
    inserted, removed, or substituted word still fails the match.
    """
    text = unicodedata.normalize("NFKC", text)
    for variants, canonical in (
        ("\u2018\u2019\u201b\u2032\u00b4`", "'"),
        ("\u201c\u201d\u201e\u2033", '"'),
        ("\u2010\u2011\u2012\u2013\u2014\u2015\u2212", "-"),
        ("\u00a0\u2007\u202f\u200b", " "),
    ):
        for ch in variants:
            text = text.replace(ch, canonical)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


@dataclass
class SpanCheck:
    """Result of verifying one quoted span against the source."""

    span: str
    verified: bool
    reason: str = ""


@dataclass
class TraitInferenceResult:
    """
    Outcome of an inference attempt.

    `traits` is None unless at least one trait was span-verified. `provenance`
    is always populated so a caller can record what was attempted, including
    total failure.
    """

    traits: Optional[BigFive] = None
    verified_traits: Dict[str, float] = field(default_factory=dict)
    rejected_traits: Dict[str, str] = field(default_factory=dict)
    span_checks: Dict[str, List[SpanCheck]] = field(default_factory=dict)
    evidence_class: str = EVIDENCE_CLASS
    failure_reason: str = ""

    @property
    def grounded(self) -> bool:
        return self.traits is not None

    def provenance(self) -> Dict[str, Any]:
        """Auditable record of what was verified and what was thrown away."""
        return {
            "evidence_class": self.evidence_class,
            "grounded": self.grounded,
            "verified_traits": sorted(self.verified_traits),
            "rejected_traits": self.rejected_traits,
            "verified_spans": {
                trait: [c.span for c in checks if c.verified]
                for trait, checks in self.span_checks.items()
                if any(c.verified for c in checks)
            },
            "failure_reason": self.failure_reason,
            # These stay false regardless of how well grounded the inference is.
            # A verified quotation is not a measurement of a human being.
            "measured_human_behavior": False,
            "human_respondents": 0,
            "causal_evidence": False,
        }


def verify_span(span: Any, haystack_normalised: str) -> SpanCheck:
    """Check one candidate span against the normalised source text."""
    if not isinstance(span, str):
        return SpanCheck(span=str(span), verified=False, reason="not_a_string")
    stripped = span.strip()
    if len(stripped) < MIN_SPAN_CHARS:
        return SpanCheck(
            span=stripped,
            verified=False,
            reason=f"shorter_than_{MIN_SPAN_CHARS}_chars",
        )
    needle = _normalise(stripped)
    if not needle:
        return SpanCheck(span=stripped, verified=False, reason="empty_after_normalisation")
    if needle in haystack_normalised:
        return SpanCheck(span=stripped, verified=True)
    return SpanCheck(span=stripped, verified=False, reason="not_found_in_source")


def _coerce_score(raw: Any) -> Optional[float]:
    """Accept a 0-100 number; reject anything else. Booleans are not scores."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
        return None
    if not 0.0 <= value <= 100.0:
        return None
    return clamp(value)


def verify_trait_claims(
    claims: Any,
    source_text: str,
) -> Tuple[Dict[str, float], Dict[str, str], Dict[str, List[SpanCheck]]]:
    """
    Verify model-proposed trait claims against source text.

    Expects `claims` shaped as:
        {"openness": {"score": 0-100, "spans": ["verbatim quote", ...]}, ...}

    Returns (verified, rejected, span_checks). A trait is verified only when its
    score is well-formed AND at least one span is found literally in the source.
    """
    verified: Dict[str, float] = {}
    rejected: Dict[str, str] = {}
    span_checks: Dict[str, List[SpanCheck]] = {}

    if not isinstance(claims, dict):
        return {}, {t: "claims_not_a_mapping" for t in TRAITS}, {}

    haystack = _normalise(source_text or "")
    if not haystack:
        return {}, {t: "empty_source_text" for t in TRAITS}, {}

    for trait in TRAITS:
        claim = claims.get(trait)
        if not isinstance(claim, dict):
            rejected[trait] = "absent_or_malformed_claim"
            continue

        score = _coerce_score(claim.get("score"))
        if score is None:
            rejected[trait] = "score_missing_or_out_of_range"
            continue

        raw_spans = claim.get("spans")
        if isinstance(raw_spans, str):
            raw_spans = [raw_spans]
        if not isinstance(raw_spans, list) or not raw_spans:
            rejected[trait] = "no_spans_supplied"
            continue

        checks = [
            verify_span(s, haystack) for s in raw_spans[:MAX_SPANS_PER_TRAIT]
        ]
        span_checks[trait] = checks

        if any(c.verified for c in checks):
            verified[trait] = score
        else:
            reasons = sorted({c.reason for c in checks if c.reason})
            rejected[trait] = "no_span_verified:" + ",".join(reasons)

    return verified, rejected, span_checks


def build_inference_prompt(entity_name: str, source_text: str) -> str:
    """
    Prompt requiring verbatim citation for every trait scored.

    The instruction to omit unsupported traits is load-bearing: a model that
    scores all five without support produces five rejections and a null result,
    which is correct but wasteful.
    """
    excerpt = (source_text or "")[:MAX_SOURCE_CHARS]
    return f"""Assess which Big Five personality dimensions are *explicitly supported by
the text below* for the scenario entity "{entity_name}".

This is a reading-comprehension task about a document, not a psychological
assessment of a real person. You are identifying what the text states, not
diagnosing anyone.

Rules:
- Score a dimension ONLY if the text contains wording that directly supports it.
- For each dimension you score, quote at least one span COPIED EXACTLY from the
  text, at least {MIN_SPAN_CHARS} characters long. Copy character for character.
  Do not paraphrase, summarise, translate, or fix typos in a quoted span.
- OMIT any dimension the text does not support. Omission is the correct and
  expected answer for most dimensions. Do not guess to fill the object.
- Every quoted span is checked by literal substring match against the source.
  An inexact quote causes that dimension to be discarded.

Scale, 0-100, where 50 is unremarkable:
- openness: curiosity, appetite for novelty and abstraction
- conscientiousness: orderliness, planning, follow-through
- extraversion: sociability, assertiveness, outward energy
- agreeableness: cooperation, deference, conflict avoidance
- neuroticism: negative affect, volatility, threat sensitivity

Return only JSON, no prose or markdown:
{{"openness": {{"score": 70, "spans": ["exact quote from the text"]}}}}

Return {{}} if the text supports no dimension.

TEXT:
{excerpt}
"""


def infer_traits(
    entity_name: str,
    source_text: str,
    llm_client: Any,
) -> TraitInferenceResult:
    """
    Attempt span-verified trait inference. Fails closed to an ungrounded result.

    `llm_client` must expose a callable returning the model's raw text. Any
    exception is caught: a failed inference must degrade to neutral defaults,
    never break a run.
    """
    if not source_text or not source_text.strip():
        return TraitInferenceResult(failure_reason="no_source_text")
    if llm_client is None:
        return TraitInferenceResult(failure_reason="no_llm_client")

    prompt = build_inference_prompt(entity_name, source_text)

    try:
        raw = _call_model(llm_client, prompt)
    except Exception as exc:  # noqa: BLE001 - degrade, never propagate
        logger.warning("Trait inference model call failed for %s: %s", entity_name, exc)
        return TraitInferenceResult(failure_reason=f"model_call_failed:{type(exc).__name__}")

    claims = _parse_json_object(raw)
    if claims is None:
        return TraitInferenceResult(failure_reason="unparseable_model_output")

    verified, rejected, checks = verify_trait_claims(claims, source_text)

    if not verified:
        logger.info(
            "No trait survived span verification for %s; neutral defaults retained",
            entity_name,
        )
        return TraitInferenceResult(
            verified_traits={},
            rejected_traits=rejected,
            span_checks=checks,
            failure_reason="no_trait_span_verified",
        )

    # Unverified dimensions fall back to the population midpoint rather than
    # being invented. A partially grounded vector is honest: the traits that
    # carry evidence move, the rest stay neutral.
    traits = BigFive(**verified)

    logger.info(
        "Span-verified %d/%d traits for %s (%s)",
        len(verified),
        len(TRAITS),
        entity_name,
        ", ".join(sorted(verified)),
    )
    return TraitInferenceResult(
        traits=traits,
        verified_traits=verified,
        rejected_traits=rejected,
        span_checks=checks,
    )


def _call_model(llm_client: Any, prompt: str) -> str:
    """Adapt to whichever call surface the client exposes."""
    for attr in ("generate", "complete", "chat", "__call__"):
        fn = getattr(llm_client, attr, None)
        if callable(fn):
            return str(fn(prompt))
    raise AttributeError("llm_client exposes no known call method")


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object, tolerating code fences and surrounding prose."""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None

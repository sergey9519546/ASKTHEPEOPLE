---
title: "Span-Verified Trait Inference"
status: "Implemented"
version: "1.0.0"
owner: "askthepeople-architect"
last_reviewed: "2026-08-03"
created: "2026-08-03"
---

# Span-Verified Trait Inference

**Status:** Implemented, feature-flagged off by default  
**Created:** 2026-08-03  
**Module:** `backend/app/services/trait_inference.py`  
**Tests:** 56 unit + 17 integration, all passing  
**Config:** `ENABLE_TRAIT_INFERENCE` (default `False`)

## What This Solves

Before this module, `big_five` was `None` for every LLM-generated profile because there was no defensible way to derive traits from source text. The consequence was that the entire personality layer did nothing in production — every agent used identical neutral defaults for all behavioural controls.

## Why "Just Ask the LLM for Trait Scores" Was Not Acceptable

The simulation config generator hard-clamps all behavioural controls to neutral defaults *"until source-constraint provenance can be verified **mechanically**"* (`simulation_config_generator.py:1090`). An LLM returning `{"openness": 82}` has no verifiable provenance: there is nothing to check the number against, so it is exactly the unverifiable proposal the clamp rejects.

Trait projection bypasses that clamp because traits are either source-derived or absent, and the arithmetic is deterministic. But that exception only holds if traits themselves are mechanically verifiable. Ungrounded trait scores would make the whole behavioural layer inadmissible.

## How Mechanical Verification Works

The model must cite, for every trait it scores, one or more **verbatim spans** from the supplied source text. Each span is checked by **literal substring match** against the real source. A trait survives only if at least one of its spans is found. Everything else is dropped.

```python
claims = {
    "openness": {
        "score": 85,
        "spans": ["relentlessly curious about unfamiliar approaches"]
    }
}
verified, rejected, checks = verify_trait_claims(claims, source_text)
```

The check is:
- deterministic (same input, same output, no model)
- runs without a model call
- fails closed (uncertain → reject)

The model proposes; arithmetic and string matching decide.

### Tolerances

The verifier normalises both the span and the source for:
- Unicode (NFKC)
- quote/dash variant unification (`"` → `"`, `–` → `-`)
- whitespace collapse
- case folding

This tolerates cosmetic reformatting but does NOT tolerate changed wording. Any inserted, removed, or substituted word still fails the match.

### Adversarial Testing

The test suite includes deliberate attacks that must fail:
- **Paraphrase** — semantically faithful but not verbatim: *"extremely inquisitive about new methods"* for *"relentlessly curious about unfamiliar approaches"*
- **Negation flip** — the most dangerous fabrication: *"relentlessly **incurious** about unfamiliar approaches"*
- **Single word insertion** — *"relentlessly curious about **very** unfamiliar approaches"*
- **Single word removal** — *"relentlessly curious ~~about~~ unfamiliar approaches"*
- **Padded short claims** — repeating a common word to clear the length floor

All correctly rejected.

## What This Establishes and What It Does Not

A verified span proves **the quoted text exists in the supplied material**. It does not prove:
- the text is true
- the text describes a real person
- the trait inference from it is correct
- any real individual holds these traits

This is a **grounding mechanism**, not a measurement instrument. Nothing here is a claim about a real person's personality.

## Failure Posture

Every failure path returns fewer traits, never invented ones:

| Condition | Result |
|---|---|
| No source text | `None` |
| Model call fails | `None` |
| Unparseable output | `None` |
| Span not found in source | That trait dropped |
| No trait survives | `None` |

`None` means the caller keeps neutral defaults. Absence of evidence never becomes evidence.

## Integration with Profile Generation

`OasisProfileGenerator._attach_inferred_traits` runs **after** validation passes, so a rejected profile never incurs the extra model call. The method:
- is gated by `ENABLE_TRAIT_INFERENCE` (default off)
- concatenates `entity.summary` and graph context as the source text
- calls `infer_traits` with a zero-temperature client adapter
- mutates `profile.big_five` in place when grounded
- swallows all exceptions (enhancement must never break a run)

With the flag **off**, behaviour is byte-identical to before this module existed.

With it **on**, a trait is attached only if it passes the independent mechanical span check — which is why it can move behavioural controls past the clamp.

## Epistemic Honesty

The prompt explicitly declines psychological-assessment framing:

> This is a reading-comprehension task about a document, not a psychological assessment of a real person. You are identifying what the text states, not diagnosing anyone.

The evidence class is `source_grounded_trait_inference`, deliberately avoiding *measured/observed/representative/forecast/predicted*. Provenance records always set:
```python
"measured_human_behavior": False
"human_respondents": 0
"causal_evidence": False
```

## Prompt Contract (Enforced)

- **Exact copying required**: *"Copy character for character. Do not paraphrase, summarise, translate, or fix typos."*
- **Spans are checked**: *"Every quoted span is checked by literal substring match against the source. An inexact quote causes that dimension to be discarded."*
- **Omission is correct**: *"OMIT any dimension the text does not support. Omission is the correct and expected answer for most dimensions. Do not guess to fill the object."*
- **Minimum span length stated**: The prompt includes `MIN_SPAN_CHARS` so the model knows the constraint.

## Example

**Source:**
> The committee chair is relentlessly curious about unfamiliar approaches and frequently proposes experimental pilots that colleagues consider premature. She keeps meticulous written records of every decision.

**Model response:**
```json
{
  "openness": {
    "score": 85,
    "spans": ["relentlessly curious about unfamiliar approaches"]
  },
  "conscientiousness": {
    "score": 90,
    "spans": ["keeps meticulous written records of every decision"]
  }
}
```

**Verification outcome:**
- Both spans found in source → both traits verified
- Extraversion, Agreeableness, Neuroticism unsupported → fall back to 50.0 (neutral)
- Final trait vector: `(85, 90, 50, 50, 50)`

## Cost and Default

Each inference costs **one additional model call per generated profile**. That is why the flag defaults off. In production, enable it only when:
1. The cost is acceptable for the run size
2. You want behavioural diversity (distinct personalities → distinct controls)
3. The source material is rich enough to support grounding

With it off, every agent uses the same neutral behavioural defaults, and the trait layer is inactive — which is exactly the behaviour before this module existed.

## Files

| Path | Lines | Purpose |
|---|---|---|
| `backend/app/services/trait_inference.py` | 327 | Span verification + inference orchestration |
| `backend/tests/test_trait_inference.py` | 315 | 56 tests, including adversarial |
| `backend/tests/test_trait_inference_wiring.py` | 229 | 17 integration tests |
| `backend/app/services/oasis_profile_generator.py` | +63 | Wiring + adapter |
| `backend/app/config.py` | +14 | Feature flag |

**Total:** 948 lines, 73 tests, all passing.

## Security Property

A model **cannot** get a trait accepted without quoting the source correctly. The test `test_fabricated_citation_is_rejected_end_to_end` exercises this through the real integration path with no mocking of the verifier.

## Next Steps (Not Implemented)

- Multi-document citation (currently concatenates summary + context)
- Confidence scores per trait (currently binary: verified or absent)
- Trait drift detection across multiple source texts for the same entity
- Active learning: flag low-confidence inferences for human review

None of these are necessary for the current integration to be correct and useful.

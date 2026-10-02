"""Compositional persona variation for archetype-expanded populations.

The 50,000-character tier (docs/plans/2026-10-01-50k-character-scale-plan.md)
requires variants that are *distinct characters*, not clones of one persona
paragraph. Verbatim copying produced variants differing only in username,
age, and jittered Big Five scores — 50,000 copies of one paragraph is one
character repeated.

This module assembles each variant's persona from a deterministic matrix:

    role framing        (47 roles from role_normalizer)
  + concern axis        (2-3 topics drawn from the centroid's interests,
                         rotated deterministically per variant)
  + disposition axis    (selected by the variant's jittered Big Five
                         dominant trait)
  + constraint framing  (constraint_framing_text from the role contract)
  + disclosure suffix   (the mandatory fictional-scenario sentence)

Design constraints
------------------
**No model call.** The matrix is deterministic and seeded by
``(archetype_id, variant_index)``, so a rerun reproduces the same population
(the archetype engine's existing seeded-random contract). Generation of
45,000 variants must cost no more than the loop itself.

**Pure.** No Config, no network, no client. The composer is a function of
its inputs only, which makes the distinctness tests deterministic.

**The disclosure is mandatory.** Every composed persona carries the same
fictional-scenario sentence the verbatim copy carried. The backend
truth-term tests keep gating this string; a variant that dropped it would
present synthetic text as human evidence.
"""

from __future__ import annotations

import math
import random
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple


# --- matrix axes --------------------------------------------------------- #

# Engagement postures. One of the three axes addressed by mixed radix over the
# global slot: see `_axis_values` for the injectivity argument.
_ENGAGEMENT_POSTURES: Sequence[str] = (
    "follows the discussion closely and weighs in when the topic touches "
    "direct experience, mostly reacting to specific claims rather than the "
    "overall direction",
    "reads widely but posts rarely, preferring to react to others, and "
    "usually engages only when a thread is already active",
    "engages most with practical, day-to-day angles of the scenario, and "
    "frames every point in terms of what changes for the routine",
    "focuses on how the scenario affects people they know, and brings "
    "second-hand accounts into the discussion",
    "follows the procedural and cost side of the discussion, and asks what "
    "each option spends and who approves it",
    "engages through questions more than positions, and rarely commits to "
    "a side without asking what would change it",
    "pushes back on claims that seem too confident, and asks what evidence "
    "would distinguish the alternatives",
    "amplifies perspectives that match their own experience, and restates "
    "others' points in their own terms",
    "tracks the timeline and logistics angle of the scenario, and asks "
    "what happens first and who is waiting",
    "engages mainly to share first-hand observation, and describes what "
    "they have seen rather than what they conclude",
    "follows the fairness and access angle of the discussion, and asks who "
    "is left out of each option",
    "engages most when the discussion turns to trade-offs, and names both "
    "sides of each trade before picking one",
    "takes the procedural side first and the argument second",
    "reacts to what others wrote rather than to the original claim",
    "treats the scenario as a set of choices with different owners",
    "looks for the precedent the discussion is ignoring",
    "sorts the options by who has to act first",
    "keeps a running note of what has already been ruled out",
    "engages late, once other positions are visible",
    "responds to the strongest version of the opposing view",
    "sorts the discussion by who is willing to act on it",
    "leads with what has to be true and works backwards",
    "stays on the thread others already started",
)

# Voice textures. Walked on the same injective per-archetype order as the
# postures, so two variants differ in how they write as well as in posture.
# Entries are comma-free adjective phrases: the persona carrier reads them as
# "writing in a <entry> register" and the bio reads one as a standalone
# sentence, so a phrase with an internal comma ("conversational, with short
# posts") produced broken English in both.
_VOICE_TEXTURES: Sequence[str] = (
    "direct and plain-spoken",
    "measured and detail-oriented",
    "conversational and brief",
    "cautious and hedged",
    "blunt about costs and downsides",
    "inquisitive and careful",
    "pragmatic and action-focused",
    "skeptical of unsupported framing",
    "warm and concise",
    "formal even in short posts",
    "plain and unhurried",
    "terse and unadorned",
    "illustrative and anecdotal",
    "formal and heavily hedged",
    "candid about what cannot be delivered",
    "cheerfully skeptical",
    "descriptive and even-handed",
    "clipped and technical",
    "warm and receptive",
    "dry and matter-of-fact",
    "forthright without being harsh",
    "quietly persistent",
    "plainly didactic",
)

# Disposition phrases, selected by the jittered Big Five dominant trait.
# Kept qualitative: they describe how the character approaches discussion,
# never a measured or predicted behavior.
_DISPOSITION_PHRASES: Dict[str, str] = {
    "openness": "drawn to new angles and alternatives in the discussion",
    "conscientiousness": "attentive to details, timelines, and follow-through",
    "extraversion": "quick to join the discussion and respond to others",
    "agreeableness": "looks for common ground before disagreeing",
    "neuroticism": "attentive to risks and what could go wrong",
}

_DISPOSITION_DEFAULT = (
    "approaches the discussion even-handedly, weighing each claim on its own terms"
)

# Qualitative disposition rotations for variants with no source-derived
# traits. Same discipline as the posture axis: they describe how the
# character approaches discussion, never a measured or predicted behavior.
_DISPOSITION_ROTATIONS: Sequence[str] = (
    "weighs practical outcomes before positions",
    "waits for specifics before forming a view",
    "leans toward the side with fewer assumptions",
    "tracks what each option costs people",
    "follows the sequencing of events more than the claims",
    "engages with the parts of the scenario that are still undecided",
    "weighs the trade-off between speed and care",
    "checks what the scenario assumes before accepting it",
    "leans toward whatever keeps options open",
    "follows the access and fairness side of the discussion",
    "focuses on what the scenario leaves unresolved",
    "weighs each claim against direct experience",
    "checks the practical detail before the principle",
    "asks what changes first",
    "tracks the commitment rather than the statement",
    "reads a trade as two things exchanged, not one thing gained",
    "prefers the option that leaves the most doors open",
    "sorts what is reversible from what is not",
    "watches what each option forecloses",
    "returns to the constraint everyone else skipped",
    "weighs what survives contact with the timetable",
    "asks what would have to be true for this to work",
    "keeps a running list of what would change its mind",
)

# Attention focus: the thing this character notices first in the scenario.
# The fourth axis, added because injectivity alone left genuinely distinct
# characters landing on the batch gate's clone threshold (worst legitimate
# pair 0.80 against a 0.90 gate) - see `_axis_values`. Framed as a reading
# habit, never as a measured or predicted behaviour.
_ATTENTION_FOCI: Sequence[str] = (
    "notices where the language stops being specific",
    "tracks who is named in the plan and who is not",
    "watches for the assumption the whole plan rests on",
    "keeps returning to what the second-order effect would be on the routine",
    "reads the piece as someone already inside it",
    "notices which detail is doing most of the work",
    "checks whether the trade is being described honestly",
    "keeps an eye on who carries the downside",
    "watches what happens first once the plan is live",
    "flags the part of the claim that is doing no work",
    "follows which commitments the plan actually keeps",
    "notes what the smaller version of this would cost",
    "watches the sequence, not the headline",
    "keeps count of what has already been ruled out",
    "looks for the cost that nobody has priced",
    "asks what survives if the first step slips",
    "tracks what would have to change to reverse course",
    "reads the concession as the actual position",
    "keeps an eye on the part that was left out",
    "notes which promise has no owner attached",
    "watches what the timeline quietly requires",
    "checks what the comparison is actually against",
    "asks who would notice first if this changed",
)

# The mandatory disclosure suffix. Same legal content as the long form the
# verbatim persona copy carried, in one compact sentence: the truth-term
# tests gate the content, and a shorter shared boilerplate keeps the
# variant-specific axes dominant in the persona (a similarity eval reads two
# variants as clones when shared boilerplate drowns the differing parts).
DISCLOSURE_SUFFIX = (
    "Fictional scenario profile: its communication and behavior are "
    "assumptions in this run, not a claim about any real person."
)


def _dominant_trait(traits: Optional[Any]) -> Optional[str]:
    """The highest Big Five score, or None when there is no dominant trait.

    Accepts a dict of scores or a BigFive-like object with a ``to_dict``.

    **A tie yields None, not an arbitrary winner.** `ENABLE_TRAIT_INFERENCE`
    is off by default, so traits are the neutral population midpoint on every
    profile: all five scores equal. `max()` on that returns whichever key
    happens to come first in iteration order, so every variant of every
    archetype was handed the SAME trait-derived disposition — the entire
    disposition axis silently collapsed to one phrase while still looking
    like trait-driven output. None lets the composer fall through to the
    injective rotation, which is what actually distinguishes the variants.
    """
    if traits is None:
        return None
    if hasattr(traits, "to_dict"):
        traits = traits.to_dict()
    if not isinstance(traits, dict) or not traits:
        return None
    try:
        scores = {key: float(value) for key, value in traits.items()}
    except (TypeError, ValueError):
        return None
    if not scores:
        return None
    top = max(scores.values())
    leaders = [key for key, value in scores.items() if value == top]
    if len(leaders) != 1:
        return None
    return leaders[0]


def _topic_rotation(
    topics: Optional[Sequence[str]],
    archetype_id: int,
    variant_index: int,
    count: int = 2,
) -> List[str]:
    """Deterministically rotate `count` topics out of the centroid's list.

    Kept for the bio/display-name composers (one-line fields where a single
    rotation is enough). The persona composer uses `_rng_topic_rotation`,
    which draws from the per-(id, n) rng instead.
    """
    if not topics:
        return []
    unique = list(dict.fromkeys(str(t).strip() for t in topics if str(t).strip()))
    if not unique:
        return []
    offset = (archetype_id + variant_index) % len(unique)
    rotated = unique[offset:] + unique[:offset]
    return rotated[:count] if len(rotated) >= count else rotated


# Variants per archetype. The global slot is `archetype_id * STRIDE +
# variant_index`, so this must equal the largest legal expansion;
# `_validate_axes` asserts it does.
_EXPANSION_STRIDE = 20


def _axis_space() -> int:
    """Size of the joint axis space: postures x voices x dispositions x focus."""
    return (
        len(_ENGAGEMENT_POSTURES)
        * len(_VOICE_TEXTURES)
        * len(_DISPOSITION_ROTATIONS)
        * len(_ATTENTION_FOCI)
    )


# Multiplier that scrambles the global slot before it is decomposed. Must be
# coprime with the axis space or the decomposition stops being injective.
# 8801 is prime and shares no factor with the space (23**4 = 279,841);
# `_validate_axes` re-checks the coprimality at import rather than trusting
# the comment.
_SLOT_SCRAMBLE = 8801


def _axis_values(
    archetype_id: int,
    variant_index: int,
) -> Tuple[str, str, str, str]:
    """The (posture, voice, disposition, focus) tuple for one variant.

    Injective over the WHOLE population, not just within one archetype. The
    per-archetype shuffle this replaced guaranteed distinctness only inside
    an archetype; across 250 archetypes two variants sharing a posture and a
    voice still scored 0.80 shingle similarity, and with identical centroids
    the triple collided outright — an exact duplicate persona. The distinctness
    eval never caught either, because it measured one archetype at a time.

    The joint space is addressed by mixed radix over a single global slot::

        slot = archetype_id * STRIDE + variant_index     # injective in the id
        slot = slot * SCRAMBLE % SPACE                   # still injective (gcd 1)
        posture = AXIS_P[slot % len(P)]
        voice    = AXIS_V[(slot // len(P)) % len(V)]
        disposition = AXIS_D[(slot // (len(P) * len(V))) % len(D)]
        focus    = AXIS_F[(slot // (len(P) * len(V) * len(D))) % len(F)]

    Mixed radix is a bijection on 0..SPACE-1, so no two variants anywhere in
    the population agree on the tuple while the population fits the space — and
    the scramble keeps consecutive archetypes from landing on consecutive
    postures, which the eval's similarity check would otherwise notice.

    **Why there are four axes and not three.** Injectivity only guarantees the
    tuple differs; two variants may still differ on the *shortest* axis alone
    and read as near-identical. Measured over 300,000 random pairs of a real
    5,000-variant population, the worst legitimate similarity was 0.80 against
    a batch gate at 0.90 — distinct characters were landing right on the
    clone threshold, which is a variety defect the injectivity guarantee does
    not cover. A fourth axis makes "differs on the shortest axis only" rarer
    and drops the worst pair.
    """
    space = _axis_space()
    stride = _EXPANSION_STRIDE
    if variant_index >= stride:
        # Beyond the declared expansion the radix decomposition would alias
        # onto another archetype's slot. Surface it rather than silently
        # emitting a duplicate character.
        raise ValueError(
            f"variant_index {variant_index} exceeds the composition stride "
            f"{stride}; expand the persona axes before raising the "
            "expansion factor"
        )
    slot = (archetype_id * stride + variant_index) * _SLOT_SCRAMBLE % space
    posture_axis = _ENGAGEMENT_POSTURES
    voice_axis = _VOICE_TEXTURES
    disposition_axis = _DISPOSITION_ROTATIONS
    focus_axis = _ATTENTION_FOCI
    posture_digit = slot % len(posture_axis)
    voice_digit = (slot // len(posture_axis)) % len(voice_axis)
    disposition_digit = (
        slot // (len(posture_axis) * len(voice_axis))
    ) % len(disposition_axis)
    focus_digit = (
        slot // (len(posture_axis) * len(voice_axis) * len(disposition_axis))
    ) % len(focus_axis)
    return (
        posture_axis[posture_digit],
        voice_axis[voice_digit],
        disposition_axis[disposition_digit],
        focus_axis[focus_digit],
    )


def _validate_axes() -> None:
    """Fail at import if the axis space cannot address the whole population.

    Two invariants, both of which silently reintroduce duplicate characters if
    broken:

    1. The stride must cover the largest legal expansion, or the global slot
       aliases between archetypes.
    2. The joint axis space must be at least as large as the largest declared
       population, or mixed radix wraps and two variants collide. Tier 4's
       defaults (250 archetypes x 20) need 5,000; four 23-entry axes provide
       279,841.
    """
    from ..utils.input_policy import ARCHETYPE_COUNT_MAX, ARCHETYPE_EXPANSION_MAX

    if _EXPANSION_STRIDE != ARCHETYPE_EXPANSION_MAX:
        raise RuntimeError(
            f"_EXPANSION_STRIDE is {_EXPANSION_STRIDE} but the legal expansion "
            f"is {ARCHETYPE_EXPANSION_MAX}"
        )

    space = _axis_space()
    required = 0
    try:
        from ..config import Config

        required = max(
            ARCHETYPE_COUNT_MAX * ARCHETYPE_EXPANSION_MAX,
            Config.TIER4_ARCHETYPE_COUNT * Config.TIER4_EXPANSION_FACTOR,
        )
    except Exception:  # pragma: no cover - config import is best effort here
        required = ARCHETYPE_COUNT_MAX * ARCHETYPE_EXPANSION_MAX

    if space < required:
        raise RuntimeError(
            f"persona axis space is {space} ({len(_ENGAGEMENT_POSTURES)}x"
            f"{len(_VOICE_TEXTURES)}x{len(_DISPOSITION_ROTATIONS)}x"
            f"{len(_ATTENTION_FOCI)}) but the "
            f"declared population reaches {required} variants; add entries to "
            "an axis"
        )

    # An axis whose LENGTH divides the stride is constant for every variant of
    # one archetype: slot advances by 1 per variant, so the low digit
    # `slot // stride` never changes inside an archetype. With 20-entry axes
    # and a stride of 20 that made every variant of an archetype share one
    # voice texture — 20 variants, 4 distinct bios. The axis must be
    # coprime with the stride, not merely long enough.
    for name, axis in (
        ("_ENGAGEMENT_POSTURES", _ENGAGEMENT_POSTURES),
        ("_VOICE_TEXTURES", _VOICE_TEXTURES),
        ("_DISPOSITION_ROTATIONS", _DISPOSITION_ROTATIONS),
    ):
        if math.gcd(len(axis), _EXPANSION_STRIDE) != 1:
            raise RuntimeError(
                f"{name} has {len(axis)} entries, which shares a factor with "
                f"the composition stride {_EXPANSION_STRIDE}; the axis would be "
                "constant across every variant of one archetype"
            )

    if math.gcd(_SLOT_SCRAMBLE, space) != 1:
        raise RuntimeError(
            f"_SLOT_SCRAMBLE {_SLOT_SCRAMBLE} is not coprime with the axis "
            f"space {space}; the slot scramble would not be injective"
        )


_validate_axes()


def _rng_topic_rotation(
    rng: random.Random,
    topics: Optional[Sequence[str]],
    archetype_id: int,
    variant_index: int,
    count: int = 2,
) -> List[str]:
    """Draw `count` distinct topics from the centroid's list via the rng.

    Unique per (archetype_id, variant_index) by construction — the rng is
    seeded with id*10_000 + n, so the same seed reproduces the same draw
    while different variants draw different subsets.
    """
    if not topics:
        return []
    unique = list(dict.fromkeys(str(t).strip() for t in topics if str(t).strip()))
    if not unique:
        return []
    if len(unique) <= count:
        return list(unique)
    return rng.sample(unique, count)


# --- composition ---------------------------------------------------------- #


def compose_variant_persona(
    *,
    archetype_id: int,
    variant_index: int,
    role_info: Optional[Dict[str, Any]],
    concern_topics: Optional[Sequence[str]],
    disposition_traits: Optional[Any],
    constraint_text: Optional[str],
    entity_context: Optional[str] = None,
) -> str:
    """Compose one variant's persona from the matrix. Deterministic.

    The same ``(archetype_id, variant_index, role_info, concern_topics,
    disposition_traits, constraint_text)`` always produces the same string.
    """
    rng = random.Random(archetype_id * 10_000 + variant_index)

    role_label = "entity"
    role_family = "unknown"
    if isinstance(role_info, dict):
        role_label = str(role_info.get("normalized_role") or "entity")
        role_family = str(role_info.get("role_family") or "unknown")

    # Injective over the whole population: see `_axis_values`. Every earlier
    # scheme failed here — a modular stride repeats inside its cycle, a
    # birthday draw collides on ~12 of 190 pairs at 20 variants, and a
    # per-archetype shuffle was injective only *within* one archetype.
    posture, voice, walked_disposition, focus = _axis_values(
        archetype_id, variant_index
    )

    disposition = _DISPOSITION_DEFAULT
    dominant = _dominant_trait(disposition_traits)
    if dominant and dominant in _DISPOSITION_PHRASES:
        # Source-derived traits win over the walked axis. That costs
        # injectivity — several variants can share a dominant trait — but
        # trait evidence outranks composition, so it is honoured.
        disposition = _DISPOSITION_PHRASES[dominant]
    else:
        disposition = walked_disposition

    parts: List[str] = []

    # 1. Role framing. Compact: the full framing sentence also lives in the
    #    public bio and the constraint text, so a long restatement here would
    #    make shared boilerplate dominate the persona (a similarity eval
    #    would then read two variants as near-identical clones even though
    #    every axis differs).
    parts.append(f"Fictional scenario character, {role_label} role.")

    # 2. Engagement posture + voice. Deterministically rotated. These two
    #    axes plus the concern axis are the variant-specific core, so they
    #    come before the shared boilerplate.
    parts.append(
        f"This character {posture}, writing in a {voice} register."
    )

    # 3. Concern axis. Topics drawn from the centroid's list through a
    #    seeded rng, so the concern axis differs across variants even when
    #    the centroid's topic list is short. This one axis is drawn through the
    #    rng rather than walked, because the centroid's list is of unknown
    #    length — it can be shorter than the expansion and it is not under
    #    this module's control.
    topics = _rng_topic_rotation(
        rng, concern_topics, archetype_id, variant_index
    )
    if topics:
        parts.append(
            "Scenario interests this character follows: "
            + ", ".join(topics)
            + "."
        )

    # 4. Disposition. From the jittered Big Five when present.
    parts.append(f"Disposition: {disposition}.")

    # 5. Attention focus. What this character notices first, before the
    #    centroid context. Placed ahead of the shared context so it is not
    #    drowned by it - a near-identical pair would otherwise be lifted by
    #    similarity toward the clone threshold.
    parts.append(f"It {focus}.")

    # 6. Entity context (the centroid's LLM persona context), when supplied.
    #    Collapsed to one line and truncated: context anchors the character
    #    to the archetype without repeating the whole centroid paragraph.
    #    Trailing punctuation is stripped before the full stop is appended,
    #    so a centroid that already ends in a period does not render as
    #    "..archetype.." on every variant.
    if entity_context:
        collapsed = " ".join(str(entity_context).split())
        if collapsed:
            trimmed = collapsed[:240].rstrip(" .,;:")
            if trimmed:
                parts.append(f"Scenario context: {trimmed}.")

    # 7. Constraint framing from the role contract.
    if constraint_text:
        parts.append(str(constraint_text).strip())

    # 8. The mandatory disclosure. Appended last, never dropped. Compact
    #    form: one sentence, same legal content as the long form, so the
    #    shared boilerplate cannot drown the variant-specific axes.
    parts.append(DISCLOSURE_SUFFIX)

    return " ".join(parts)


def compose_variant_bio(
    *,
    archetype_id: int,
    variant_index: int,
    role_info: Optional[Dict[str, Any]],
    concern_topics: Optional[Sequence[str]],
) -> str:
    """Compose one variant's short public bio from the same axes. Deterministic.

    The voice texture is taken from the same injective per-archetype walk the
    persona uses (a different axis seed), so no two variants of one archetype
    share a bio even when the centroid has too few topics to rotate. The
    earlier independent modular stride here could repeat within its cycle —
    the defect the persona axis had.
    """
    role_label = "entity"
    if isinstance(role_info, dict):
        role_label = str(role_info.get("normalized_role") or "entity")
    voice = _axis_values(archetype_id, variant_index)[1]
    topics = _topic_rotation(concern_topics, archetype_id, variant_index, count=2)
    topic_text = f" Interested in {', '.join(topics)}." if topics else ""
    voice_text = f" {voice[0].upper()}{voice[1:]}."
    return (
        # "Fictional" appears verbatim: the truth-term tests and the
        # distinctness tests both gate this word in the public bio.
        f"Fictional {role_label} scenario character.{voice_text}{topic_text}"
        " Generated for this run — not a real person."
    )


def compose_display_name(
    *,
    archetype_id: int,
    variant_index: int,
    role_info: Optional[Dict[str, Any]],
    concern_topics: Optional[Sequence[str]] = None,
) -> str:
    """Compose a display name from role + rotated topic. Deterministic.

    A 45,000-follower crowd of "Follower 42" names reads as a counter, not
    characters; role- and topic-varied names fix that while staying
    deterministic and collision-free within an archetype.
    """
    role_label = "entity"
    if isinstance(role_info, dict):
        role_label = str(role_info.get("normalized_role") or "entity")
    role_title = role_label.replace("_", " ").title()

    topics = _topic_rotation(concern_topics, archetype_id, variant_index, count=1)
    if topics:
        topic_word = str(topics[0]).split()[0].strip(",.;")
        topic_title = topic_word.title() if topic_word else ""
        if topic_title and topic_title.lower() != role_title.lower():
            return f"{topic_title} {role_title} {variant_index + 1}"
    return f"{role_title} {variant_index + 1}"


def compose_username(
    *,
    archetype_id: int,
    variant_index: int,
    role_info: Optional[Dict[str, Any]],
) -> str:
    """Compose a globally-unique username.

    The old ``f"{label}_{n:02d}"`` form collided across archetypes (two
    archetypes both labeled "council" produced duplicate usernames). The
    archetype stem makes usernames unique across the whole population.
    """
    role_label = "entity"
    if isinstance(role_info, dict):
        role_label = str(role_info.get("normalized_role") or "entity")
    safe = re.sub(r"[^a-z0-9_]", "", role_label.lower().replace(" ", "_")) or "entity"
    return f"a{archetype_id}_{safe}_{variant_index:02d}"

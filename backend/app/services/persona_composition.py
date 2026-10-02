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

import random
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple


# --- matrix axes --------------------------------------------------------- #

# Engagement postures. Walked injectively per archetype: see `_axis_at` for
# why the axis length is a hard floor, not a style choice.
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
    """The highest Big Five score, or None when traits are absent.

    Accepts a dict of scores or a BigFive-like object with a ``to_dict``.
    """
    if traits is None:
        return None
    if hasattr(traits, "to_dict"):
        traits = traits.to_dict()
    if not isinstance(traits, dict) or not traits:
        return None
    try:
        return max(traits, key=lambda key: float(traits[key]))
    except (TypeError, ValueError):
        return None


def _rotation(values: Sequence[str], index: int) -> str:
    return values[index % len(values)]


@lru_cache(maxsize=4096)
def _axis_order(
    axis: Tuple[str, ...],
    archetype_id: int,
    axis_seed: int,
) -> Tuple[str, ...]:
    """Per-archetype shuffled order for one axis.

    Seeded by ``(archetype_id, axis_seed)``: deterministic for a given
    archetype and distinct per axis, so the three axes do not walk in step.
    Cached because tier 4 walks 45,000 variants and re-shuffling per call
    would be pure waste.
    """
    shuffled = list(axis)
    random.Random(archetype_id * 100 + axis_seed).shuffle(shuffled)
    return tuple(shuffled)


def _axis_at(
    axis: Sequence[str],
    archetype_id: int,
    variant_index: int,
    *,
    axis_seed: int,
) -> str:
    """Take position `variant_index` from a per-archetype shuffled axis.

    Two variants of one archetype therefore **cannot** share an axis value
    while ``variant_index < len(axis)``: a permutation's distinct positions
    hold distinct entries. That is the property the distinctness eval
    measures, and it is why the axis length is a hard floor rather than a
    style choice — see `_validate_axes`.

    Sampling was tried first and failed the same way every time. A modular
    stride repeats with a period that divides the axis length, so variants one
    cycle apart collided on every axis simultaneously. A seeded
    ``random.choice`` is better but not better enough: with 12 postures and
    20 variants roughly 12 of the 190 pairs collide by birthday argument, and
    a pair sharing posture plus disposition scores 0.65-0.76 shingle
    similarity — the "crowd is collapsing into clones" failure this avoids.
    """
    order = _axis_order(tuple(axis), archetype_id, axis_seed)
    return order[variant_index % len(order)]


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


def _validate_axes() -> None:
    """Fail at import if any axis is shorter than the largest expansion.

    `_axis_at` only guarantees distinctness while ``variant_index`` stays
    below the axis length. The largest expansion this module must survive is
    `ARCHETYPE_EXPANSION_MAX`; an axis shorter than that reintroduces the
    collision silently, so the invariant is asserted rather than left to a
    comment.
    """
    from ..utils.input_policy import ARCHETYPE_EXPANSION_MAX

    for name, axis in (
        ("_ENGAGEMENT_POSTURES", _ENGAGEMENT_POSTURES),
        ("_VOICE_TEXTURES", _VOICE_TEXTURES),
        ("_DISPOSITION_ROTATIONS", _DISPOSITION_ROTATIONS),
    ):
        if len(axis) < ARCHETYPE_EXPANSION_MAX:
            raise RuntimeError(
                f"{name} has {len(axis)} entries but expansion can reach "
                f"{ARCHETYPE_EXPANSION_MAX}; two variants of one archetype "
                "would share an axis value and read as the same character"
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

    # Axes are drawn by INDEX into per-archetype shuffled orders. Drawing
    # from the rng (a birthday-collision draw) left ~78% of 20-variant
    # archetypes with a shared posture pair, and pairs sharing posture +
    # disposition scored 0.65 in the distinctness eval. Instead: each axis
    # is shuffled deterministically per archetype with a DISTINCT seed per
    # axis, and variant n takes position n from each shuffled list — so no
    # two variants in an archetype repeat a full axis triple by
    # construction, while the same archetype id always produces the same
    # shuffles (deterministic).
    posture = _axis_at(
        _ENGAGEMENT_POSTURES, archetype_id, variant_index, axis_seed=1
    )
    voice = _axis_at(
        _VOICE_TEXTURES, archetype_id, variant_index, axis_seed=2
    )

    disposition = _DISPOSITION_DEFAULT
    dominant = _dominant_trait(disposition_traits)
    if dominant and dominant in _DISPOSITION_PHRASES:
        disposition = _DISPOSITION_PHRASES[dominant]
    else:
        # No source-derived traits: take the disposition from the same
        # per-archetype shuffled-axis mechanism (distinct axis seed).
        disposition = _axis_at(
            _DISPOSITION_ROTATIONS, archetype_id, variant_index, axis_seed=3
        )

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
    #    the centroid's topic list is short. This one axis is sampled rather
    #    than walked because the centroid's list is of unknown length — it
    #    can be shorter than the expansion, and it is not under this
    #    module's control.
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

    # 5. Entity context (the centroid's LLM persona context), when supplied.
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

    # 6. Constraint framing from the role contract.
    if constraint_text:
        parts.append(str(constraint_text).strip())

    # 7. The mandatory disclosure. Appended last, never dropped. Compact
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
    voice = _axis_at(
        _VOICE_TEXTURES, archetype_id, variant_index, axis_seed=4
    )
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

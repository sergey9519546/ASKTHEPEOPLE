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
from typing import Any, Dict, List, Optional, Sequence


# --- matrix axes --------------------------------------------------------- #

# Engagement postures. Rotated per variant so the crowd reads as characters
# with different relationships to the scenario, not one posture repeated.
_ENGAGEMENT_POSTURES: Sequence[str] = (
    "follows the discussion closely and weighs in when the topic touches "
    "direct experience",
    "reads widely but posts rarely, preferring to react to others",
    "engages most with practical, day-to-day angles of the scenario",
    "focuses on how the scenario affects people they know",
    "follows the procedural and cost side of the discussion",
    "engages through questions more than positions",
    "pushes back on claims that seem too confident",
    "amplifies perspectives that match their own experience",
    "tracks the timeline and logistics angle of the scenario",
    "engages mainly to share first-hand observation",
    "follows the fairness and access angle of the discussion",
    "engages most when the discussion turns to trade-offs",
)

# Voice textures. Rotated independently of posture so two variants sharing a
# posture still differ in how they write.
_VOICE_TEXTURES: Sequence[str] = (
    "direct and plain-spoken",
    "measured and detail-oriented",
    "conversational, with short posts",
    "cautious, hedging most claims",
    "blunt about costs and downsides",
    "curious, asking before asserting",
    "pragmatic, focused on what is actionable",
    "skeptical of unsupported framing",
    "warm but concise",
    "formal in tone even in short posts",
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

# The mandatory disclosure suffix. Identical to the sentence the verbatim
# persona copy carries; the truth-term tests gate this string.
DISCLOSURE_SUFFIX = (
    "This is a fictional scenario profile. Its communication and behavior "
    "are assumptions within this run, not a claim about a real person, "
    "observation of real people, or a prediction of any real actor."
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


def _topic_rotation(
    topics: Optional[Sequence[str]],
    archetype_id: int,
    variant_index: int,
    count: int = 2,
) -> List[str]:
    """Deterministically rotate `count` topics out of the centroid's list.

    Every variant in an archetype draws a different rotation, so the concern
    axis differs across variants even when the centroid's topic list is short
    (a 2-topic list with count=2 still rotates the *order*).
    """
    if not topics:
        return []
    unique = list(dict.fromkeys(str(t).strip() for t in topics if str(t).strip()))
    if not unique:
        return []
    offset = (archetype_id + variant_index) % len(unique)
    rotated = unique[offset:] + unique[:offset]
    return rotated[:count] if len(rotated) >= count else rotated


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

    posture = _rotation(_ENGAGEMENT_POSTURES, archetype_id + variant_index)
    voice = _VOICE_TEXTURES[
        (archetype_id * 7 + variant_index * 3) % len(_VOICE_TEXTURES)
    ]

    disposition = _DISPOSITION_DEFAULT
    dominant = _dominant_trait(disposition_traits)
    if dominant and dominant in _DISPOSITION_PHRASES:
        disposition = _DISPOSITION_PHRASES[dominant]

    parts: List[str] = []

    # 1. Role framing. The scenario role the character stands in — never a
    #    biography of a real actor.
    parts.append(
        f"Fictional scenario character in the {role_label} role "
        f"({role_family} family)."
    )

    # 2. Engagement posture + voice. Deterministically rotated.
    parts.append(f"This character {posture}, and writes in a {voice} way.")

    # 3. Concern axis. The rotated topics, framed as scenario interests.
    topics = _topic_rotation(concern_topics, archetype_id, variant_index)
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
    if entity_context:
        collapsed = " ".join(str(entity_context).split())
        if collapsed:
            parts.append(f"Scenario context: {collapsed[:240]}.")

    # 6. Constraint framing from the role contract.
    if constraint_text:
        parts.append(str(constraint_text).strip())

    # 7. The mandatory disclosure. Appended last, never dropped.
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

    Bios are one line, so the topic rotation alone cannot make 20 of them
    distinct (a 4-topic list rotates only 4 orderings). The voice texture
    breaks the tie: it rotates on an INDEPENDENT stride (id*7 + n*3, the
    same stride the persona's voice uses), so voice x topic-rotation stays
    decorrelated across variants.
    """
    role_label = "entity"
    if isinstance(role_info, dict):
        role_label = str(role_info.get("normalized_role") or "entity")
    voice = _VOICE_TEXTURES[
        (archetype_id * 7 + variant_index * 3) % len(_VOICE_TEXTURES)
    ]
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

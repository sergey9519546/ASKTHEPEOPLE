"""Resource-constraint and feasibility engine.

This module models what an actor can actually *do*, which is a different
question from what an actor would *prefer*. Preference engines rank options.
This engine removes options: a budget runs out, a deadline passes, a permit is
missing, an actor never learned the fact that the action depends on, or another
actor has to sign off first.

Design constraints (deliberate, do not "improve" them away):

- **Standard library only.** No Flask, no ``app.*`` imports, no network, no
  database. The engine is a pure function library so it can be unit-tested and
  reasoned about in isolation, and so it can be called from a worker process,
  a request handler, or a notebook without dragging in application state.
- **Actors are plain dicts.** The engine never imports a profile dataclass.
  An actor is any mapping with an id, a set of constraints, and optionally a
  set of known facts. This keeps the engine decoupled from whatever shape the
  profile layer happens to have today.

Semantics that matter
---------------------

``Enforcement`` is the load-bearing concept:

- ``HARD``   — exceeding capacity blocks the action absolutely. ``feasible``
  becomes ``False`` and the violated constraint is listed in ``blocking``.
- ``SOFT``   — exceeding capacity is *permitted* but recorded as a penalty.
  ``feasible`` stays ``True``. The overage is reported in ``penalties``.
- ``PROBABILISTIC`` — exceeding capacity does not block and is not a penalty;
  it degrades the chance of success. Each probabilistic constraint contributes
  a factor to ``success_probability``, and the factors multiply.

``FeasibilityResult.feasible`` answers exactly one question: "is this action
free of HARD violations?" It deliberately does **not** fold in
``success_probability``, because a 5%-likely action is a different situation
from a forbidden one and collapsing the two loses information. Callers that
want the combined judgement should use
:attr:`FeasibilityResult.expected_to_succeed`.

Truth boundary
--------------

Every number produced here is arithmetic over caller-supplied assumptions.
Capacities, costs and probabilities are inputs, not measurements. A
``success_probability`` returned by this module is not calibrated, is not a
forecast, and is not evidence about any real actor's behavior.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

__all__ = [
    "ConstraintType",
    "Enforcement",
    "Constraint",
    "Action",
    "Penalty",
    "FeasibilityResult",
    "CircularDependencyError",
    "check_feasibility",
    "resolve_dependencies",
    "visible_facts",
    "can_act_on_information",
    "degrade_action",
    "normalize_constraints",
    "actor_capacities",
    "PUBLIC_KNOWLEDGE_KEY",
]

# Key in a knowledge graph whose facts are visible to every actor.
PUBLIC_KNOWLEDGE_KEY = "*"

# Scale factors are floored to this many decimals so that a scaled action can
# never overshoot the available capacity through float representation error.
_SCALE_DECIMALS = 6
_EPSILON = 1e-9


class ConstraintType(str, Enum):
    """The kind of scarcity a constraint represents.

    Values are lowercase strings so constraints survive a JSON round-trip and
    can be authored in configuration without importing this module.
    """

    BUDGET = "budget"
    TIME = "time"
    INFORMATION = "information"
    LEGAL = "legal"
    SOCIAL = "social"
    CAPACITY = "capacity"


class Enforcement(str, Enum):
    """How a constraint behaves when demand exceeds capacity."""

    HARD = "hard"
    """Blocks absolutely. The action cannot happen."""

    SOFT = "soft"
    """Permitted, but at a recorded cost or penalty."""

    PROBABILISTIC = "probabilistic"
    """Permitted, but succeeds only with some probability."""


@dataclass(frozen=True)
class Constraint:
    """A single ceiling on what an actor can spend, spare, or get away with.

    Args:
        type: Which resource or gate this limits.
        capacity: How much of that resource is available. Must be finite and
            non-negative, or ``math.inf`` for "no ceiling".
        enforcement: What happens when a cost exceeds ``capacity``.
        label: Human-readable name used in explanations, e.g.
            ``"quarterly campaign budget"``.
    """

    type: ConstraintType
    capacity: float
    enforcement: Enforcement = Enforcement.HARD
    label: str = ""

    def __post_init__(self) -> None:
        if self.capacity < 0:
            raise ValueError(
                f"Constraint capacity must be non-negative, got {self.capacity!r} "
                f"for {self.describe()}"
            )
        if isinstance(self.capacity, float) and math.isnan(self.capacity):
            raise ValueError(f"Constraint capacity must not be NaN for {self.describe()}")

    def describe(self) -> str:
        """Return a short label suitable for embedding in a sentence."""
        return self.label or self.type.value

    def is_exceeded_by(self, cost: float) -> bool:
        """Return ``True`` if ``cost`` demands more than this constraint allows."""
        return cost > self.capacity + _EPSILON

    def success_factor(self, cost: float) -> float:
        """Return this constraint's multiplicative contribution to success.

        Only meaningful for :attr:`Enforcement.PROBABILISTIC`. A cost within
        capacity contributes ``1.0``. A cost above capacity contributes
        ``capacity / cost``, so asking for twice what is available halves the
        chance of success. Zero capacity against a positive cost contributes
        ``0.0``: not forbidden, but not going to happen either.
        """
        if not self.is_exceeded_by(cost):
            return 1.0
        if cost <= 0:
            return 1.0
        if math.isinf(self.capacity):
            return 1.0
        return max(0.0, min(1.0, self.capacity / cost))


@dataclass(frozen=True)
class Action:
    """Something an actor might attempt, priced in constrained resources.

    Args:
        label: Human-readable name of the action.
        costs: What the action consumes, keyed by :class:`ConstraintType`.
            A resource absent from this mapping is not consumed.
        requires_approval_from: Ids of actors that must act before this one.
            Used by :func:`resolve_dependencies`, not by
            :func:`check_feasibility` — an unapproved action is *sequenced*
            later, it is not inherently infeasible.
        requires_knowledge: Facts the actor must already hold. Missing
            knowledge is a HARD information block: you cannot act on what you
            do not know.
        min_scale: The smallest fraction of this action that is still worth
            doing. :func:`degrade_action` refuses to scale below it.
        divisible: If ``False`` the action is all-or-nothing and cannot be
            scaled down at all.
        scale: The fraction of the original action this instance represents.
            ``1.0`` for an author-defined action; set by :func:`degrade_action`.
    """

    label: str
    costs: dict[ConstraintType, float] = field(default_factory=dict)
    requires_approval_from: list[str] = field(default_factory=list)
    requires_knowledge: set[str] = field(default_factory=set)
    min_scale: float = 0.1
    divisible: bool = True
    scale: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 < self.min_scale <= 1.0:
            raise ValueError(
                f"min_scale must be in (0, 1], got {self.min_scale!r} for {self.label!r}"
            )
        for constraint_type, cost in self.costs.items():
            if not isinstance(constraint_type, ConstraintType):
                raise TypeError(
                    f"Action.costs keys must be ConstraintType, got "
                    f"{constraint_type!r} for {self.label!r}"
                )
            if cost < 0:
                raise ValueError(
                    f"Action costs must be non-negative, got {cost!r} for "
                    f"{constraint_type.value} in {self.label!r}"
                )

    def cost_of(self, constraint_type: ConstraintType) -> float:
        """Return the cost in one resource, or ``0.0`` if it is not consumed."""
        return float(self.costs.get(constraint_type, 0.0))

    def total_cost(self) -> float:
        """Return the sum of all costs. Only useful for coarse comparisons."""
        return float(sum(self.costs.values()))


@dataclass(frozen=True)
class Penalty:
    """A SOFT constraint that was exceeded but did not block the action."""

    constraint: Constraint
    required: float
    capacity: float

    @property
    def overage(self) -> float:
        """Return how far past capacity the action reached."""
        return max(0.0, self.required - self.capacity)

    def describe(self) -> str:
        """Return a one-line explanation of the overage."""
        return (
            f"{self.constraint.describe()} exceeded by {self.overage:g} "
            f"(needed {self.required:g}, had {self.capacity:g})"
        )


@dataclass(frozen=True)
class FeasibilityResult:
    """The verdict on whether an actor can attempt an action.

    Attributes:
        feasible: ``True`` when no HARD constraint was violated. Note that a
            feasible action can still have ``success_probability == 0.0``; see
            :attr:`expected_to_succeed`.
        blocking: The HARD constraints that were violated.
        penalties: The SOFT constraints that were exceeded. Never affects
            :attr:`feasible`.
        success_probability: Product of every PROBABILISTIC constraint's
            factor. ``1.0`` when there are none.
        reason: Human-readable explanation of the verdict.
        action_label: The action this verdict is about.
        actor_id: The actor this verdict is about.
        missing_knowledge: Facts the action required that the actor lacked.
    """

    feasible: bool
    blocking: list[Constraint] = field(default_factory=list)
    penalties: list[Penalty] = field(default_factory=list)
    success_probability: float = 1.0
    reason: str = ""
    action_label: str = ""
    actor_id: str = ""
    missing_knowledge: set[str] = field(default_factory=set)

    @property
    def expected_to_succeed(self) -> bool:
        """Return ``True`` only if the action is unblocked *and* can succeed."""
        return self.feasible and self.success_probability > 0.0

    @property
    def penalty_cost(self) -> float:
        """Return the summed overage across all SOFT violations."""
        return float(sum(penalty.overage for penalty in self.penalties))

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable view for logging or API responses."""
        return {
            "actor_id": self.actor_id,
            "action_label": self.action_label,
            "feasible": self.feasible,
            "expected_to_succeed": self.expected_to_succeed,
            "success_probability": self.success_probability,
            "blocking": [
                {
                    "type": constraint.type.value,
                    "label": constraint.describe(),
                    "capacity": constraint.capacity,
                }
                for constraint in self.blocking
            ],
            "penalties": [
                {
                    "type": penalty.constraint.type.value,
                    "label": penalty.constraint.describe(),
                    "required": penalty.required,
                    "capacity": penalty.capacity,
                    "overage": penalty.overage,
                }
                for penalty in self.penalties
            ],
            "penalty_cost": self.penalty_cost,
            "missing_knowledge": sorted(self.missing_knowledge),
            "reason": self.reason,
        }


class CircularDependencyError(Exception):
    """Raised when approval requirements form a cycle.

    A deadlocked approval chain is a substantive finding about a scenario, not
    an internal error, so the involved actors are both named in the message and
    exposed on :attr:`actors` for programmatic inspection.
    """

    def __init__(self, cycle: Sequence[str]) -> None:
        self.actors: tuple[str, ...] = tuple(cycle)
        if self.actors:
            path = " -> ".join([*self.actors, self.actors[0]])
        else:  # pragma: no cover - defensive, callers always pass a cycle
            path = "<unknown>"
        super().__init__(
            "Circular approval dependency detected; no actor can act first. "
            f"Cycle: {path}. Actors involved: {', '.join(self.actors)}."
        )


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _coerce_enum(value: Any, enum_cls: type[Enum], field_name: str) -> Any:
    """Coerce a string or enum member into ``enum_cls``."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value.strip().lower())
        except ValueError:
            pass
        try:
            return enum_cls[value.strip().upper()]
        except KeyError:
            pass
    valid = ", ".join(member.value for member in enum_cls)
    raise ValueError(f"Unknown {field_name}: {value!r}. Expected one of: {valid}")


def _coerce_constraint_type(value: Any) -> ConstraintType:
    return _coerce_enum(value, ConstraintType, "constraint type")


def _coerce_enforcement(value: Any) -> Enforcement:
    return _coerce_enum(value, Enforcement, "enforcement")


def _normalize_constraint(raw: Any, fallback_type: Any = None) -> Constraint:
    """Build a :class:`Constraint` from a Constraint, mapping, or bare number."""
    if isinstance(raw, Constraint):
        return raw

    if isinstance(raw, Mapping):
        constraint_type = raw.get("type", raw.get("constraint_type", fallback_type))
        if constraint_type is None:
            raise ValueError(f"Constraint mapping is missing a 'type': {raw!r}")
        capacity = raw.get("capacity", raw.get("limit", raw.get("available")))
        if capacity is None:
            raise ValueError(f"Constraint mapping is missing a 'capacity': {raw!r}")
        return Constraint(
            type=_coerce_constraint_type(constraint_type),
            capacity=float(capacity),
            enforcement=_coerce_enforcement(raw.get("enforcement", Enforcement.HARD)),
            label=str(raw.get("label", "") or ""),
        )

    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        if fallback_type is None:
            raise ValueError(
                f"Bare capacity {raw!r} given without a constraint type to attach it to"
            )
        return Constraint(
            type=_coerce_constraint_type(fallback_type),
            capacity=float(raw),
            enforcement=Enforcement.HARD,
        )

    raise TypeError(
        f"Cannot interpret {raw!r} as a Constraint. Provide a Constraint, a "
        "mapping with 'type' and 'capacity', or a number keyed by constraint type."
    )


def normalize_constraints(actor: Mapping[str, Any]) -> list[Constraint]:
    """Return an actor's constraints as :class:`Constraint` objects.

    Accepts several authoring shapes so that callers are not forced to import
    this module to describe an actor:

    - ``{"constraints": [Constraint(...), ...]}``
    - ``{"constraints": [{"type": "budget", "capacity": 100, ...}, ...]}``
    - ``{"constraints": {ConstraintType.BUDGET: 100, "time": 8}}``

    An actor with no ``constraints`` key is unconstrained, which is a valid and
    meaningful state (nothing stops it).

    Args:
        actor: A mapping describing the actor.

    Returns:
        A list of constraints, possibly empty.
    """
    if not isinstance(actor, Mapping):
        raise TypeError(f"Actor must be a mapping, got {type(actor).__name__}")

    raw_constraints = actor.get("constraints")
    if raw_constraints is None:
        return []

    if isinstance(raw_constraints, Mapping):
        return [
            _normalize_constraint(value, fallback_type=key)
            for key, value in raw_constraints.items()
        ]

    if isinstance(raw_constraints, Iterable) and not isinstance(raw_constraints, (str, bytes)):
        return [_normalize_constraint(item) for item in raw_constraints]

    raise TypeError(
        f"actor['constraints'] must be a mapping or an iterable, got "
        f"{type(raw_constraints).__name__}"
    )


def _actor_id(actor: Mapping[str, Any]) -> str:
    """Return an actor's id, tolerating the common key spellings."""
    for key in ("id", "actor_id", "agent_id", "name"):
        value = actor.get(key)
        if value:
            return str(value)
    return ""


def _actor_knowledge(actor: Mapping[str, Any]) -> set[str]:
    """Return the facts an actor holds, from ``knowledge`` or ``knows``."""
    for key in ("knowledge", "knows", "known_facts", "facts"):
        raw = actor.get(key)
        if raw is None:
            continue
        if isinstance(raw, (str, bytes)):
            return {str(raw)}
        if isinstance(raw, Mapping):
            return {str(fact) for fact in raw}
        if isinstance(raw, Iterable):
            return {str(fact) for fact in raw}
    return set()


def actor_capacities(actor: Mapping[str, Any]) -> dict[ConstraintType, float]:
    """Return the tightest capacity per resource for an actor.

    Useful for feeding :func:`degrade_action`. When an actor holds several
    constraints on the same resource the smallest capacity wins, because that
    is the one that actually binds. Resources the actor has no constraint on
    are absent from the result, meaning unconstrained.

    Args:
        actor: A mapping describing the actor.

    Returns:
        A mapping of constraint type to the binding capacity.
    """
    capacities: dict[ConstraintType, float] = {}
    for constraint in normalize_constraints(actor):
        existing = capacities.get(constraint.type)
        if existing is None or constraint.capacity < existing:
            capacities[constraint.type] = float(constraint.capacity)
    return capacities


# ---------------------------------------------------------------------------
# Feasibility
# ---------------------------------------------------------------------------


def check_feasibility(actor: Mapping[str, Any], action: Action) -> FeasibilityResult:
    """Decide whether ``actor`` can attempt ``action``.

    Every constraint the actor holds is tested against the corresponding cost
    in the action. Resources the actor has no constraint on are unlimited.
    Costs the action does not incur are zero, so a constraint on an unused
    resource is never violated.

    Enforcement determines the consequence, and the three cases are kept
    strictly separate:

    - HARD over capacity -> appended to ``blocking``, ``feasible`` is ``False``.
    - SOFT over capacity -> appended to ``penalties``, ``feasible`` unchanged.
    - PROBABILISTIC over capacity -> multiplied into ``success_probability``,
      neither blocking nor penalised.

    Missing knowledge is treated as a HARD information block: an actor cannot
    act on a fact it does not hold. The block is reported as a synthesised
    ``INFORMATION`` constraint so callers can handle ``blocking`` uniformly.

    ``requires_approval_from`` is intentionally *not* evaluated here. Waiting
    on a co-actor is a sequencing question, answered by
    :func:`resolve_dependencies`; it does not make an action infeasible.

    Args:
        actor: Mapping with an id, optional ``constraints``, optional
            ``knowledge``.
        action: The action under consideration.

    Returns:
        A :class:`FeasibilityResult` describing the verdict and its reasons.
    """
    if not isinstance(action, Action):
        raise TypeError(f"action must be an Action, got {type(action).__name__}")

    constraints = normalize_constraints(actor)
    actor_id = _actor_id(actor)

    blocking: list[Constraint] = []
    penalties: list[Penalty] = []
    success_probability = 1.0
    probabilistic_notes: list[str] = []

    for constraint in constraints:
        cost = action.cost_of(constraint.type)

        if constraint.enforcement is Enforcement.PROBABILISTIC:
            factor = constraint.success_factor(cost)
            if factor < 1.0:
                probabilistic_notes.append(
                    f"{constraint.describe()} reduces success to {factor:g}x "
                    f"(needed {cost:g}, had {constraint.capacity:g})"
                )
            success_probability *= factor
            continue

        if not constraint.is_exceeded_by(cost):
            continue

        if constraint.enforcement is Enforcement.HARD:
            blocking.append(constraint)
        else:
            penalties.append(
                Penalty(
                    constraint=constraint,
                    required=cost,
                    capacity=float(constraint.capacity),
                )
            )

    known = _actor_knowledge(actor)
    missing_knowledge = {str(fact) for fact in action.requires_knowledge} - known
    if missing_knowledge:
        blocking.append(
            Constraint(
                type=ConstraintType.INFORMATION,
                capacity=0.0,
                enforcement=Enforcement.HARD,
                label="missing knowledge: " + ", ".join(sorted(missing_knowledge)),
            )
        )

    success_probability = max(0.0, min(1.0, success_probability))
    feasible = not blocking

    reason = _build_reason(
        actor_id=actor_id,
        action=action,
        feasible=feasible,
        blocking=blocking,
        penalties=penalties,
        success_probability=success_probability,
        probabilistic_notes=probabilistic_notes,
    )

    return FeasibilityResult(
        feasible=feasible,
        blocking=blocking,
        penalties=penalties,
        success_probability=success_probability,
        reason=reason,
        action_label=action.label,
        actor_id=actor_id,
        missing_knowledge=missing_knowledge,
    )


def _build_reason(
    *,
    actor_id: str,
    action: Action,
    feasible: bool,
    blocking: Sequence[Constraint],
    penalties: Sequence[Penalty],
    success_probability: float,
    probabilistic_notes: Sequence[str],
) -> str:
    """Compose the human-readable explanation attached to a result."""
    who = actor_id or "actor"
    what = action.label or "action"
    parts: list[str] = []

    if blocking:
        details = "; ".join(
            f"{constraint.describe()} ({constraint.type.value}, hard limit "
            f"{constraint.capacity:g}, needed {action.cost_of(constraint.type):g})"
            if constraint.label and "missing knowledge" not in constraint.label
            else constraint.describe()
            for constraint in blocking
        )
        parts.append(f"BLOCKED: {who} cannot perform {what}. Hard violations: {details}")
    else:
        parts.append(f"FEASIBLE: {who} can attempt {what}")

    if penalties:
        details = "; ".join(penalty.describe() for penalty in penalties)
        parts.append(f"allowed at a cost ({len(penalties)} soft violation(s)): {details}")

    if probabilistic_notes:
        parts.append("; ".join(probabilistic_notes))

    if feasible or probabilistic_notes:
        parts.append(f"success probability {success_probability:g}")

    return ". ".join(parts) + "."


# ---------------------------------------------------------------------------
# Approval dependencies
# ---------------------------------------------------------------------------


def _actions_for(value: Any) -> list[Action]:
    """Normalize a per-actor value into a list of actions."""
    if value is None:
        return []
    if isinstance(value, Action):
        return [value]
    if isinstance(value, Mapping):
        raise TypeError(
            "actions_by_actor values must be an Action or a sequence of Actions, "
            f"got a mapping: {value!r}"
        )
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        actions = list(value)
        for item in actions:
            if not isinstance(item, Action):
                raise TypeError(
                    f"actions_by_actor contained a non-Action item: {item!r}"
                )
        return actions
    raise TypeError(
        f"Cannot interpret {value!r} as an Action or sequence of Actions"
    )


def resolve_dependencies(
    actions_by_actor: Mapping[str, Any],
) -> list[list[str]]:
    """Sort actors into execution waves based on approval requirements.

    An actor that requires approval from another actor cannot act until that
    approver has acted. Each returned wave contains actors whose approvals are
    all satisfied by earlier waves, so every actor in a wave may act
    concurrently. Actor ids within a wave are sorted for determinism.

    Approvers that are named but have no entry in ``actions_by_actor`` are
    treated as external parties that are already in place, and appear in the
    first wave. They are surfaced rather than silently dropped, because a
    dependency on an actor nobody modelled is worth seeing.

    Args:
        actions_by_actor: Mapping of actor id to an :class:`Action` or a
            sequence of actions. Approval edges are read from every action's
            ``requires_approval_from``.

    Returns:
        A list of waves, each a sorted list of actor ids. An empty input
        returns an empty list.

    Raises:
        CircularDependencyError: If approvals form a cycle, including an actor
            that requires its own approval. The message names the actors in the
            cycle.
    """
    if not isinstance(actions_by_actor, Mapping):
        raise TypeError(
            f"actions_by_actor must be a mapping, got {type(actions_by_actor).__name__}"
        )
    if not actions_by_actor:
        return []

    # approvers[actor] = actors that must act before `actor`.
    approvers: dict[str, set[str]] = {}
    for actor_id, value in actions_by_actor.items():
        actor_key = str(actor_id)
        approvers.setdefault(actor_key, set())
        for action in _actions_for(value):
            for approver in action.requires_approval_from:
                approver_key = str(approver)
                approvers[actor_key].add(approver_key)
                approvers.setdefault(approver_key, set())

    for actor_key, needed in approvers.items():
        if actor_key in needed:
            raise CircularDependencyError([actor_key])

    waves: list[list[str]] = []
    remaining = {actor: set(needed) for actor, needed in approvers.items()}
    settled: set[str] = set()

    while remaining:
        ready = sorted(
            actor for actor, needed in remaining.items() if not (needed - settled)
        )
        if not ready:
            raise CircularDependencyError(_find_cycle(remaining))
        waves.append(ready)
        settled.update(ready)
        for actor in ready:
            del remaining[actor]

    return waves


def _find_cycle(graph: Mapping[str, set[str]]) -> list[str]:
    """Return one concrete cycle from ``graph`` as an ordered actor list.

    ``graph`` maps an actor to the actors that must act before it, so the walk
    follows unsatisfied prerequisites backwards. The returned list is rotated
    to start at its alphabetically smallest member for stable messages.
    """
    nodes = set(graph)
    visiting: list[str] = []
    on_path: set[str] = set()
    done: set[str] = set()

    def walk(node: str) -> list[str] | None:
        visiting.append(node)
        on_path.add(node)
        for prerequisite in sorted(graph.get(node, ())):
            if prerequisite not in nodes:
                continue
            if prerequisite in on_path:
                start = visiting.index(prerequisite)
                return list(reversed(visiting[start:]))
            if prerequisite in done:
                continue
            found = walk(prerequisite)
            if found is not None:
                return found
        visiting.pop()
        on_path.discard(node)
        done.add(node)
        return None

    for node in sorted(nodes):
        if node in done:
            continue
        cycle = walk(node)
        if cycle:
            pivot = cycle.index(min(cycle))
            return cycle[pivot:] + cycle[:pivot]

    # Unreachable in practice: the caller only calls this when progress stalled.
    return sorted(nodes)  # pragma: no cover


# ---------------------------------------------------------------------------
# Information asymmetry
# ---------------------------------------------------------------------------


def visible_facts(actor_id: str, knowledge_graph: Mapping[str, Any]) -> set[str]:
    """Return the set of facts an actor can see.

    Two authoring shapes are supported per entry:

    - ``{"alice": {"merger_date", "price"}}`` — facts held privately by alice.
    - ``{"alice": {"facts": {...}, "shares_with": ["bob"]}}`` — facts held by
      alice and also visible to bob.

    Facts under the :data:`PUBLIC_KNOWLEDGE_KEY` (``"*"``) key are visible to
    everyone. An actor absent from the graph simply knows nothing beyond the
    public facts, which is the correct default for an outsider.

    Args:
        actor_id: The actor whose viewpoint to compute.
        knowledge_graph: Mapping of actor id to held facts.

    Returns:
        A new set of facts. The graph is never mutated.
    """
    if knowledge_graph is None:
        return set()
    if not isinstance(knowledge_graph, Mapping):
        raise TypeError(
            f"knowledge_graph must be a mapping, got {type(knowledge_graph).__name__}"
        )

    target = str(actor_id)
    visible: set[str] = set()

    for owner, entry in knowledge_graph.items():
        owner_key = str(owner)
        facts, shared_with = _unpack_knowledge_entry(entry)

        if owner_key == PUBLIC_KNOWLEDGE_KEY:
            visible |= facts
            continue
        if owner_key == target:
            visible |= facts
            continue
        if target in shared_with or PUBLIC_KNOWLEDGE_KEY in shared_with:
            visible |= facts

    return visible


def _unpack_knowledge_entry(entry: Any) -> tuple[set[str], set[str]]:
    """Split a knowledge-graph entry into (facts, shared_with)."""
    if entry is None:
        return set(), set()
    if isinstance(entry, (str, bytes)):
        return {str(entry)}, set()
    if isinstance(entry, Mapping):
        if "facts" in entry or "shares_with" in entry or "shared_with" in entry:
            raw_facts = entry.get("facts") or ()
            raw_shared = entry.get("shares_with", entry.get("shared_with")) or ()
            facts = (
                {str(raw_facts)}
                if isinstance(raw_facts, (str, bytes))
                else {str(fact) for fact in raw_facts}
            )
            shared = (
                {str(raw_shared)}
                if isinstance(raw_shared, (str, bytes))
                else {str(who) for who in raw_shared}
            )
            return facts, shared
        # A plain mapping is treated as a set of fact keys.
        return {str(fact) for fact in entry}, set()
    if isinstance(entry, Iterable):
        return {str(fact) for fact in entry}, set()
    return {str(entry)}, set()


def can_act_on_information(
    actor: Mapping[str, Any],
    action: Action,
    knowledge: Any = None,
) -> bool:
    """Return ``True`` if the actor knows everything the action requires.

    Information is the constraint most often modelled wrongly, because it is
    tempting to let every actor read the same world state. Here an actor can
    only act on facts it actually holds.

    Args:
        actor: Mapping describing the actor. Facts on the actor itself (under
            ``knowledge``/``knows``) always count.
        action: The action whose ``requires_knowledge`` must be satisfied.
        knowledge: Optional extra source of facts. Either a flat collection of
            facts available to this actor, or a knowledge graph keyed by actor
            id, in which case the actor's visible facts are resolved with
            :func:`visible_facts`.

    Returns:
        ``True`` when no required fact is missing.
    """
    required = {str(fact) for fact in action.requires_knowledge}
    if not required:
        return True

    known = _actor_knowledge(actor)

    if isinstance(knowledge, Mapping):
        known |= visible_facts(_actor_id(actor), knowledge)
    elif isinstance(knowledge, (str, bytes)):
        known.add(str(knowledge))
    elif isinstance(knowledge, Iterable):
        known |= {str(fact) for fact in knowledge}

    return required <= known


# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------


def _normalize_available(available: Any) -> dict[ConstraintType, float]:
    """Coerce an availability mapping into typed capacities."""
    if available is None:
        return {}
    if isinstance(available, Mapping):
        normalized: dict[ConstraintType, float] = {}
        for key, value in available.items():
            if isinstance(value, Constraint):
                capacity = float(value.capacity)
            elif isinstance(value, Mapping):
                capacity = float(_normalize_constraint(value, fallback_type=key).capacity)
            else:
                capacity = float(value)
            constraint_type = _coerce_constraint_type(key)
            existing = normalized.get(constraint_type)
            normalized[constraint_type] = (
                capacity if existing is None else min(existing, capacity)
            )
        return normalized
    raise TypeError(
        f"available must be a mapping of constraint type to capacity, got "
        f"{type(available).__name__}"
    )


def degrade_action(action: Action, available: Any) -> Action | None:
    """Return the largest affordable version of ``action``, or ``None``.

    Real actors compromise. Faced with a campaign it cannot fund, an actor runs
    a smaller campaign rather than doing nothing, and modelling that as a flat
    failure overstates how often constrained actors go quiet.

    The scale factor is the tightest ratio of available capacity to required
    cost across every resource, capped at ``1.0`` and floored to six decimals so
    that the scaled costs can never exceed what is available. Resources absent
    from ``available`` are treated as unconstrained, matching
    :func:`check_feasibility`, where a resource with no constraint cannot be
    violated.

    Args:
        action: The full-strength action.
        available: Mapping of constraint type to available capacity. Accepts
            :class:`ConstraintType` or string keys and numeric,
            :class:`Constraint`, or mapping values. Pass
            :func:`actor_capacities` output directly.

    Returns:
        ``action`` itself when it is fully affordable, a new scaled
        :class:`Action` when a smaller version fits, or ``None`` when even
        ``action.min_scale`` is unaffordable or the action is indivisible and
        unaffordable.
    """
    if not isinstance(action, Action):
        raise TypeError(f"action must be an Action, got {type(action).__name__}")

    capacities = _normalize_available(available)

    scale = 1.0
    for constraint_type, cost in action.costs.items():
        cost = float(cost)
        if cost <= 0:
            continue
        capacity = capacities.get(constraint_type)
        if capacity is None or math.isinf(capacity):
            continue
        scale = min(scale, max(0.0, capacity) / cost)

    if scale >= 1.0 - _EPSILON:
        return action

    if not action.divisible:
        return None

    factor = 10**_SCALE_DECIMALS
    scale = math.floor(scale * factor) / factor

    if scale < action.min_scale - _EPSILON or scale <= 0.0:
        return None

    return replace(
        action,
        label=f"{action.label} (scaled to {scale:g})",
        costs={
            constraint_type: float(cost) * scale
            for constraint_type, cost in action.costs.items()
        },
        requires_approval_from=list(action.requires_approval_from),
        requires_knowledge=set(action.requires_knowledge),
        scale=action.scale * scale,
    )

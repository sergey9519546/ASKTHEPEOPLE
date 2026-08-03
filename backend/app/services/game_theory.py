"""Game-theoretic reasoning primitives for strategic/competitive scenarios.

Purpose
-------
This module supports questions of the form "will a competitor undercut us?",
"which actors have an incentive to form a coalition?", and "what does an actor
do if it correctly anticipates the others' moves?".

Honest scope statement (read this before using the module)
----------------------------------------------------------
Computing a Nash equilibrium of a general n-player finite game is hard:
2-player equilibrium computation is PPAD-complete, and many natural decision
questions about n-player games (e.g. existence of an equilibrium with given
support properties) are NP-hard or worse. **This module is deliberately not a
general Nash solver.** It implements a small set of pieces that are either
exact-but-exponential (and therefore explicitly size-guarded) or exact-but-
restricted to a special case.

Per-function classification:

===========================  ============================================
Function                     Status
===========================  ============================================
``pure_nash_equilibria``     Exact, but exponential in the number of
                             players. Size-guarded. Finds only *pure*
                             equilibria; a game may have none (Matching
                             Pennies) while still having mixed equilibria.
``best_response``            Exact. Returns every tied maximiser.
``iterated_strict_dominance``Exact for domination by *pure* strategies
                             only. Does not detect actions dominated only
                             by a mixed strategy (that needs an LP).
``mixed_nash_2x2``           Exact closed form, restricted to 2 players
                             with 2 actions each. Interior equilibria only.
``shapley_value``            Exact. Size-guarded.
``stable_coalitions``        Exact for the specific stability notion
                             defined in its docstring, which is *stricter*
                             than "the core is non-empty". Read it.
``is_in_core``               Exact core-membership test for one allocation.
===========================  ============================================

Dependencies: standard library only (``dataclasses``, ``itertools``, ``math``,
``typing``). No Flask, no ``app.*`` imports, no numeric third-party packages,
no I/O. The module is importable in isolation.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any, Callable, Hashable, Iterable, Iterator, Mapping, Sequence

__all__ = [
    "GameTheoryError",
    "GameTooLargeError",
    "UnsupportedGameShapeError",
    "NormalFormGame",
    "StableCoalition",
    "best_response",
    "pure_nash_equilibria",
    "iterated_strict_dominance",
    "mixed_nash_2x2",
    "shapley_value",
    "stable_coalitions",
    "is_in_core",
    "DEFAULT_TOLERANCE",
    "MAX_PURE_PROFILES",
    "MAX_SHAPLEY_PLAYERS",
    "MAX_COALITION_PLAYERS",
]


# --------------------------------------------------------------------------
# Tolerances and hard size guards
# --------------------------------------------------------------------------

#: Absolute tolerance used when comparing payoffs. Payoffs within this
#: distance of each other are treated as tied, and "strictly greater" means
#: greater by more than this amount.
DEFAULT_TOLERANCE = 1e-9

#: Maximum number of pure action profiles this module will enumerate. The
#: number of profiles is the product of the per-player action counts, i.e.
#: exponential in the player count. Exceeding this raises
#: :class:`GameTooLargeError` rather than hanging.
MAX_PURE_PROFILES = 200_000

#: Maximum player count for :func:`shapley_value`. The exact computation
#: touches every subset of players (2**n), so this stays small on purpose.
MAX_SHAPLEY_PLAYERS = 12

#: Maximum player count for :func:`stable_coalitions`. That routine inspects
#: every subcoalition of every coalition, which is Theta(3**n) work.
MAX_COALITION_PLAYERS = 10


class GameTheoryError(ValueError):
    """Base class for all errors raised by this module."""


class GameTooLargeError(GameTheoryError):
    """Raised when a request would require an intractable enumeration.

    This exists so that callers get an immediate, explicit, actionable error
    instead of a process that appears to hang.
    """


class UnsupportedGameShapeError(GameTheoryError):
    """Raised when a game does not match a routine's restricted domain.

    For example, :func:`mixed_nash_2x2` only accepts 2-player games with
    exactly 2 actions per player.
    """


# --------------------------------------------------------------------------
# Game representation
# --------------------------------------------------------------------------

PayoffVector = tuple[float, ...]
Profile = tuple[Any, ...]
PayoffSource = Mapping[Profile, Sequence[float]] | Callable[[Profile], Sequence[float]]


@dataclass(frozen=True, eq=True)
class NormalFormGame:
    """A finite normal-form (simultaneous-move) game.

    Parameters
    ----------
    players:
        Ordered, distinct, hashable player identifiers. The order is
        load-bearing: an action profile is a tuple aligned with this order,
        and a payoff vector is a tuple aligned with this order.
    actions:
        Mapping of player -> ordered, distinct actions available to that
        player. Every player in ``players`` must appear.
    payoffs:
        Either

        * a mapping from action profile (tuple aligned with ``players``) to a
          payoff vector (sequence of floats aligned with ``players``), which
          must cover every profile that is queried; or
        * a callable taking an action profile and returning a payoff vector.

        A callable is the right choice for large games, because it avoids
        materialising an exponentially large table. Note that the size guards
        in this module apply regardless of representation.

    Notes
    -----
    Payoffs are interpreted as utilities to be **maximised**. If you are
    modelling costs, negate them before constructing the game.

    No equilibrium property is validated at construction time. Construction is
    cheap; the analysis functions do the work.
    """

    players: tuple[Hashable, ...]
    actions: Mapping[Hashable, tuple[Any, ...]]
    payoffs: PayoffSource

    def __post_init__(self) -> None:
        players = tuple(self.players)
        if not players:
            raise GameTheoryError("A game needs at least one player.")
        if len(set(players)) != len(players):
            raise GameTheoryError(f"Player identifiers must be distinct, got {players!r}.")

        missing = [p for p in players if p not in self.actions]
        if missing:
            raise GameTheoryError(f"No action list supplied for player(s) {missing!r}.")

        normalised_actions: dict[Hashable, tuple[Any, ...]] = {}
        for player in players:
            acts = tuple(self.actions[player])
            if not acts:
                raise GameTheoryError(f"Player {player!r} has an empty action list.")
            if len(set(acts)) != len(acts):
                raise GameTheoryError(
                    f"Actions for player {player!r} must be distinct, got {acts!r}."
                )
            normalised_actions[player] = acts

        if not callable(self.payoffs) and not isinstance(self.payoffs, Mapping):
            raise GameTheoryError(
                "payoffs must be a Mapping from profile to payoff vector, or a callable."
            )

        object.__setattr__(self, "players", players)
        object.__setattr__(self, "actions", normalised_actions)

    # -- basic shape -------------------------------------------------------

    @property
    def n_players(self) -> int:
        """Number of players."""
        return len(self.players)

    @property
    def action_counts(self) -> tuple[int, ...]:
        """Number of actions per player, aligned with :attr:`players`."""
        return tuple(len(self.actions[p]) for p in self.players)

    def player_index(self, player: Hashable) -> int:
        """Index of ``player`` within :attr:`players`."""
        try:
            return self.players.index(player)
        except ValueError:
            raise GameTheoryError(
                f"Unknown player {player!r}; game players are {self.players!r}."
            ) from None

    def profile_count(self) -> int:
        """Total number of pure action profiles (product of action counts).

        This grows exponentially with the number of players. Callers use it to
        decide whether an exhaustive routine is affordable.
        """
        total = 1
        for count in self.action_counts:
            total *= count
        return total

    def profiles(self, *, max_profiles: int = MAX_PURE_PROFILES) -> Iterator[Profile]:
        """Iterate over every pure action profile.

        Raises
        ------
        GameTooLargeError
            If the profile count exceeds ``max_profiles``. The check happens
            *before* any enumeration, so this fails fast rather than hanging.
        """
        total = self.profile_count()
        if total > max_profiles:
            raise GameTooLargeError(
                f"This game has {total} pure action profiles, which exceeds the "
                f"max_profiles guard of {max_profiles}. Enumerating pure profiles is "
                f"exponential in the number of players ({self.n_players} here, with "
                f"action counts {self.action_counts}). Reduce the game, or raise "
                f"max_profiles deliberately if you accept the cost."
            )
        return itertools.product(*(self.actions[p] for p in self.players))

    # -- payoff access -----------------------------------------------------

    def payoff_vector(self, profile: Profile) -> PayoffVector:
        """Payoff vector for ``profile``, aligned with :attr:`players`."""
        profile = tuple(profile)
        if len(profile) != self.n_players:
            raise GameTheoryError(
                f"Profile {profile!r} has length {len(profile)}, expected "
                f"{self.n_players} (one action per player)."
            )

        source = self.payoffs
        if callable(source):
            raw = source(profile)
        else:
            try:
                raw = source[profile]
            except KeyError:
                raise GameTheoryError(
                    f"No payoff defined for profile {profile!r}. A payoff mapping must "
                    f"cover every profile that gets queried."
                ) from None

        try:
            vector = tuple(float(value) for value in raw)
        except (TypeError, ValueError):
            raise GameTheoryError(
                f"Payoff for profile {profile!r} must be a sequence of numbers, got {raw!r}."
            ) from None

        if len(vector) != self.n_players:
            raise GameTheoryError(
                f"Payoff for profile {profile!r} has {len(vector)} entries, expected "
                f"{self.n_players} (one per player)."
            )
        return vector

    def payoff(self, player: Hashable, profile: Profile) -> float:
        """Payoff to ``player`` under ``profile``."""
        return self.payoff_vector(profile)[self.player_index(player)]

    # -- derived games -----------------------------------------------------

    def with_actions(
        self, actions: Mapping[Hashable, Iterable[Any]]
    ) -> "NormalFormGame":
        """Return a copy restricted to the given (sub)sets of actions.

        Each restricted action list must be a non-empty subset of the original
        list for that player. If this game stores payoffs in a mapping, the
        mapping is filtered to the surviving profiles; if payoffs come from a
        callable, the callable is reused as-is.
        """
        restricted: dict[Hashable, tuple[Any, ...]] = {}
        for player in self.players:
            if player not in actions:
                raise GameTheoryError(f"No restricted action list for player {player!r}.")
            acts = tuple(actions[player])
            if not acts:
                raise GameTheoryError(
                    f"Restricted action list for player {player!r} is empty."
                )
            original = self.actions[player]
            unknown = [a for a in acts if a not in original]
            if unknown:
                raise GameTheoryError(
                    f"Actions {unknown!r} are not available to player {player!r} "
                    f"(available: {original!r})."
                )
            # Preserve the original ordering for stable, comparable output.
            restricted[player] = tuple(a for a in original if a in acts)

        payoffs: PayoffSource
        if callable(self.payoffs):
            payoffs = self.payoffs
        else:
            surviving = set(itertools.product(*(restricted[p] for p in self.players)))
            payoffs = {
                profile: tuple(values)
                for profile, values in self.payoffs.items()
                if profile in surviving
            }

        return NormalFormGame(players=self.players, actions=restricted, payoffs=payoffs)

    # -- constructors ------------------------------------------------------

    @classmethod
    def from_bimatrix(
        cls,
        row_payoffs: Sequence[Sequence[float]],
        col_payoffs: Sequence[Sequence[float]],
        *,
        players: tuple[Hashable, Hashable] = ("row", "col"),
        row_actions: Sequence[Any] | None = None,
        col_actions: Sequence[Any] | None = None,
    ) -> "NormalFormGame":
        """Build a 2-player game from two payoff matrices.

        ``row_payoffs[i][j]`` is the row player's payoff when the row player
        plays its action ``i`` and the column player plays its action ``j``;
        ``col_payoffs[i][j]`` is the column player's payoff for the same cell.
        """
        n_rows = len(row_payoffs)
        if n_rows == 0:
            raise GameTheoryError("row_payoffs must be non-empty.")
        n_cols = len(row_payoffs[0])
        if n_cols == 0:
            raise GameTheoryError("row_payoffs rows must be non-empty.")
        if any(len(row) != n_cols for row in row_payoffs):
            raise GameTheoryError("row_payoffs must be rectangular.")
        if len(col_payoffs) != n_rows or any(len(row) != n_cols for row in col_payoffs):
            raise GameTheoryError("col_payoffs must have the same shape as row_payoffs.")

        row_player, col_player = players
        r_actions = (
            tuple(row_actions) if row_actions is not None else tuple(range(n_rows))
        )
        c_actions = (
            tuple(col_actions) if col_actions is not None else tuple(range(n_cols))
        )
        if len(r_actions) != n_rows or len(c_actions) != n_cols:
            raise GameTheoryError("Action label counts must match the matrix shape.")

        table = {
            (r_actions[i], c_actions[j]): (
                float(row_payoffs[i][j]),
                float(col_payoffs[i][j]),
            )
            for i in range(n_rows)
            for j in range(n_cols)
        }
        return cls(
            players=(row_player, col_player),
            actions={row_player: r_actions, col_player: c_actions},
            payoffs=table,
        )


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------


def _other_players(game: NormalFormGame, player: Hashable) -> tuple[Hashable, ...]:
    return tuple(p for p in game.players if p != player)


def _normalise_others(
    game: NormalFormGame,
    player: Hashable,
    others_actions: Mapping[Hashable, Any] | Sequence[Any],
) -> dict[Hashable, Any]:
    """Coerce an "others' actions" argument into a player -> action mapping.

    Accepts either a mapping keyed by player, or a sequence aligned with the
    other players in :attr:`NormalFormGame.players` order.
    """
    others = _other_players(game, player)

    if isinstance(others_actions, Mapping):
        assignment = {p: others_actions[p] for p in others if p in others_actions}
        missing = [p for p in others if p not in assignment]
        if missing:
            raise GameTheoryError(
                f"others_actions is missing an action for player(s) {missing!r}."
            )
        extra = [k for k in others_actions if k not in others]
        if extra:
            raise GameTheoryError(
                f"others_actions contains entries for {extra!r}, which are not the "
                f"opponents of {player!r} (opponents: {others!r})."
            )
    else:
        values = tuple(others_actions)
        if len(values) != len(others):
            raise GameTheoryError(
                f"others_actions has {len(values)} entries but {player!r} has "
                f"{len(others)} opponent(s) {others!r}. When passing a sequence it "
                f"must be aligned with the game's player order, excluding {player!r}."
            )
        assignment = dict(zip(others, values))

    for opponent, action in assignment.items():
        if action not in game.actions[opponent]:
            raise GameTheoryError(
                f"Action {action!r} is not available to player {opponent!r} "
                f"(available: {game.actions[opponent]!r})."
            )
    return assignment


def _assemble_profile(
    game: NormalFormGame,
    player: Hashable,
    own_action: Any,
    others: Mapping[Hashable, Any],
) -> Profile:
    return tuple(
        own_action if p == player else others[p] for p in game.players
    )


def _argmax_all(
    scored: Sequence[tuple[Any, float]], tolerance: float
) -> list[Any]:
    """Return every item whose score is within ``tolerance`` of the maximum."""
    best = max(score for _, score in scored)
    return [item for item, score in scored if score >= best - tolerance]


# --------------------------------------------------------------------------
# Best response
# --------------------------------------------------------------------------


def best_response(
    game: NormalFormGame,
    player: Hashable,
    others_actions: Mapping[Hashable, Any] | Sequence[Any],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[Any]:
    """All payoff-maximising actions for ``player`` given the others' actions.

    Exactness: **exact**. This is a direct maximisation over one player's
    finite action list, with no approximation.

    Every tied maximiser is returned, in the player's declared action order.
    Ties are common and meaningful in strategic modelling (an actor that is
    indifferent is exactly the actor whose behaviour you cannot predict from
    payoffs alone), so this function deliberately never picks one arbitrarily.

    Parameters
    ----------
    others_actions:
        Either a mapping of opponent -> action covering every opponent, or a
        sequence aligned with the game's player order excluding ``player``.
    tolerance:
        Absolute tolerance for treating payoffs as tied.

    Returns
    -------
    list
        One or more actions. Never empty, because action lists are non-empty.
    """
    assignment = _normalise_others(game, player, others_actions)
    scored = [
        (action, game.payoff(player, _assemble_profile(game, player, action, assignment)))
        for action in game.actions[player]
    ]
    return _argmax_all(scored, tolerance)


# --------------------------------------------------------------------------
# Pure Nash equilibria
# --------------------------------------------------------------------------


def pure_nash_equilibria(
    game: NormalFormGame,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    max_profiles: int = MAX_PURE_PROFILES,
) -> list[Profile]:
    """Every **pure-strategy** Nash equilibrium, by exhaustive search.

    A profile is returned when no player can strictly improve its own payoff by
    unilaterally changing its own action ("no unilateral improvement").

    Exactness and cost
    ------------------
    * **Exact** for pure equilibria: the search is exhaustive, so the result is
      the complete set, not a sample or a heuristic.
    * **Exponential**: the number of profiles is the product of the per-player
      action counts. This is intended for SMALL games (a handful of actors with
      a handful of options each). ``max_profiles`` is enforced *before*
      enumeration and raises :class:`GameTooLargeError`, so an oversized
      request fails immediately with a clear message instead of hanging.

    Important limitation
    --------------------
    Many games have **no** pure equilibrium (Matching Pennies is the standard
    example). An empty result means "no pure equilibrium exists", **not** "no
    equilibrium exists": by Nash's theorem a finite game always has at least
    one equilibrium once mixed strategies are allowed. This module can compute
    mixed equilibria only for the 2x2 case (see :func:`mixed_nash_2x2`).

    Returns
    -------
    list of tuple
        Equilibrium profiles, each aligned with ``game.players``, in
        lexicographic order of the declared action lists.
    """
    equilibria: list[Profile] = []
    for profile in game.profiles(max_profiles=max_profiles):
        vector = game.payoff_vector(profile)
        stable = True
        for index, player in enumerate(game.players):
            current = vector[index]
            for alternative in game.actions[player]:
                if alternative == profile[index]:
                    continue
                deviated = list(profile)
                deviated[index] = alternative
                if game.payoff_vector(tuple(deviated))[index] > current + tolerance:
                    stable = False
                    break
            if not stable:
                break
        if stable:
            equilibria.append(profile)
    return equilibria


# --------------------------------------------------------------------------
# Iterated strict dominance
# --------------------------------------------------------------------------


def iterated_strict_dominance(
    game: NormalFormGame,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    max_profiles: int = MAX_PURE_PROFILES,
) -> NormalFormGame:
    """Iteratively remove strictly dominated actions; return the reduced game.

    An action ``a`` of player ``i`` is strictly dominated (by a pure strategy)
    when some other available action ``b`` of player ``i`` yields a strictly
    higher payoff against *every* combination of the opponents' currently
    surviving actions. Such an action is never played by a payoff-maximiser,
    and removing it cannot remove any Nash equilibrium.

    Why only strict dominance
    -------------------------
    Iterated elimination of **strictly** dominated strategies is
    order-independent: the surviving set does not depend on the order in which
    actions are removed. This is a theorem, not an implementation detail, and
    it is what makes the reduced game a well-defined object.

    Iterated elimination of **weakly** dominated strategies is *not*
    order-independent: different elimination orders can yield different
    surviving sets, and it can destroy Nash equilibria. This module therefore
    does **not** provide weak elimination, so that no caller can mistake it for
    an equally safe operation.

    Exactness
    ---------
    Exact with respect to domination by **pure** strategies. An action can be
    strictly dominated by a *mixed* strategy while not being dominated by any
    single pure action; detecting that requires solving a linear program, which
    is out of scope here. Consequently the returned game may still contain
    actions that a fuller procedure would eliminate. The reduction is therefore
    sound (nothing wrongly removed) but not complete (something may remain).

    Raises
    ------
    GameTooLargeError
        If the opponent-profile enumeration needed for a dominance check
        exceeds ``max_profiles``.
    """
    surviving: dict[Hashable, tuple[Any, ...]] = {
        player: tuple(game.actions[player]) for player in game.players
    }

    changed = True
    while changed:
        changed = False
        for player in game.players:
            available = surviving[player]
            if len(available) < 2:
                continue

            others = _other_players(game, player)
            opponent_lists = [surviving[o] for o in others]
            opponent_count = 1
            for lst in opponent_lists:
                opponent_count *= len(lst)
            if opponent_count > max_profiles:
                raise GameTooLargeError(
                    f"Checking strict dominance for player {player!r} requires "
                    f"evaluating {opponent_count} opponent action combinations, which "
                    f"exceeds the max_profiles guard of {max_profiles}. Dominance "
                    f"checking is exponential in the number of opponents "
                    f"({len(others)} here)."
                )

            opponent_profiles = [
                dict(zip(others, combo)) for combo in itertools.product(*opponent_lists)
            ]

            dominated_action = None
            for candidate in available:
                for dominator in available:
                    if dominator == candidate:
                        continue
                    if all(
                        game.payoff(
                            player,
                            _assemble_profile(game, player, dominator, opponents),
                        )
                        > game.payoff(
                            player,
                            _assemble_profile(game, player, candidate, opponents),
                        )
                        + tolerance
                        for opponents in opponent_profiles
                    ):
                        dominated_action = candidate
                        break
                if dominated_action is not None:
                    break

            if dominated_action is not None:
                surviving[player] = tuple(
                    a for a in available if a != dominated_action
                )
                changed = True

    return game.with_actions(surviving)


# --------------------------------------------------------------------------
# Mixed equilibrium, 2x2 only
# --------------------------------------------------------------------------


def mixed_nash_2x2(
    game: NormalFormGame, *, tolerance: float = DEFAULT_TOLERANCE
) -> dict[Hashable, dict[Any, float]] | None:
    """Closed-form fully-mixed Nash equilibrium of a 2-player 2-action game.

    **Restricted special case.** This function handles exactly two players with
    exactly two actions each, and nothing else. It does not generalise: there
    is no closed form for larger games, and this module makes no attempt to
    pretend otherwise. Larger games raise
    :class:`UnsupportedGameShapeError`.

    Method
    ------
    In a fully-mixed (interior) equilibrium each player must be indifferent
    between its two actions, because otherwise it would put all weight on the
    better one. Writing ``p`` for the probability that the row player plays its
    first action and ``q`` for the probability that the column player plays its
    first action, the two indifference conditions are linear and give

        p = (b11 - b10) / (b00 - b10 - b01 + b11)
        q = (a11 - a01) / (a00 - a01 - a10 + a11)

    where ``a`` is the row player's payoff matrix and ``b`` the column
    player's. Note the cross-over: ``p`` is pinned down by the *column*
    player's indifference, and ``q`` by the *row* player's.

    Returns
    -------
    dict or None
        On success, ``{player: {action: probability}}`` for both players, with
        each inner dict summing to 1. Returns ``None`` when no interior mixed
        equilibrium exists, which happens when a denominator vanishes
        (degenerate payoffs) or when the solved probability falls outside the
        open interval ``(0, 1)``. Coordination-free games such as Prisoner's
        Dilemma correctly return ``None``.

        ``None`` says nothing about pure equilibria; use
        :func:`pure_nash_equilibria` for those.
    """
    if game.n_players != 2:
        raise UnsupportedGameShapeError(
            f"mixed_nash_2x2 handles 2-player games only, got {game.n_players} "
            f"players. There is no closed-form solution for larger games and this "
            f"module does not attempt one."
        )
    if game.action_counts != (2, 2):
        raise UnsupportedGameShapeError(
            f"mixed_nash_2x2 handles 2 actions per player only, got action counts "
            f"{game.action_counts}."
        )

    row_player, col_player = game.players
    row_actions = game.actions[row_player]
    col_actions = game.actions[col_player]

    a: list[list[float]] = [[0.0, 0.0], [0.0, 0.0]]
    b: list[list[float]] = [[0.0, 0.0], [0.0, 0.0]]
    for i, row_action in enumerate(row_actions):
        for j, col_action in enumerate(col_actions):
            row_value, col_value = game.payoff_vector((row_action, col_action))
            a[i][j] = row_value
            b[i][j] = col_value

    # Column player's indifference pins down the row player's mix p.
    p_denominator = b[0][0] - b[1][0] - b[0][1] + b[1][1]
    # Row player's indifference pins down the column player's mix q.
    q_denominator = a[0][0] - a[0][1] - a[1][0] + a[1][1]

    if abs(p_denominator) <= tolerance or abs(q_denominator) <= tolerance:
        # Degenerate: at least one player's payoff difference does not depend on
        # the opponent's mix, so no interior indifference point is pinned down.
        return None

    p = (b[1][1] - b[1][0]) / p_denominator
    q = (a[1][1] - a[0][1]) / q_denominator

    if not (tolerance < p < 1.0 - tolerance):
        return None
    if not (tolerance < q < 1.0 - tolerance):
        return None

    return {
        row_player: {row_actions[0]: p, row_actions[1]: 1.0 - p},
        col_player: {col_actions[0]: q, col_actions[1]: 1.0 - q},
    }


# --------------------------------------------------------------------------
# Cooperative game theory: Shapley value
# --------------------------------------------------------------------------

CharacteristicFunction = Callable[[frozenset], float]


def _validate_coalition_inputs(
    players: Sequence[Hashable],
    characteristic_function: CharacteristicFunction,
    *,
    max_players: int,
    routine: str,
    tolerance: float,
) -> tuple[Hashable, ...]:
    ordered = tuple(players)
    if not ordered:
        raise GameTheoryError(f"{routine} needs at least one player.")
    if len(set(ordered)) != len(ordered):
        raise GameTheoryError(f"Player identifiers must be distinct, got {ordered!r}.")
    if len(ordered) > max_players:
        raise GameTooLargeError(
            f"{routine} was called with {len(ordered)} players, which exceeds the "
            f"max_players guard of {max_players}. The exact computation enumerates "
            f"coalitions and so grows exponentially in the player count; refusing "
            f"rather than hanging. Aggregate actors into blocs, or raise the limit "
            f"deliberately if you accept the cost."
        )
    if not callable(characteristic_function):
        raise GameTheoryError("characteristic_function must be callable.")

    empty_value = float(characteristic_function(frozenset()))
    if abs(empty_value) > tolerance:
        raise GameTheoryError(
            f"characteristic_function(frozenset()) returned {empty_value!r}, but the "
            f"value of the empty coalition must be 0 for the Shapley value's "
            f"efficiency property to hold."
        )
    return ordered


def shapley_value(
    players: Sequence[Hashable],
    characteristic_function: CharacteristicFunction,
    *,
    max_players: int = MAX_SHAPLEY_PLAYERS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict[Hashable, float]:
    """Exact Shapley value: attribute a coalition's value to its members.

    Exactness: **exact**, not sampled. The Shapley value of player ``i`` is its
    average marginal contribution over all ``n!`` orderings of the players.
    This implementation evaluates the algebraically identical closed form

        phi_i = sum over S subset of N\\{i} of
                    |S|! * (n - |S| - 1)! / n! * ( v(S + i) - v(S) )

    which groups the orderings that share the same predecessor set ``S``. It
    therefore touches ``2**(n-1)`` subsets per player rather than ``n!``
    orderings, and returns the same numbers a full permutation average would.

    Parameters
    ----------
    players:
        Distinct, hashable actor identifiers.
    characteristic_function:
        ``v``, called with a :class:`frozenset` of players and returning the
        value that coalition can secure on its own. ``v(empty set)`` must be 0.
    max_players:
        Guard. Exceeding it raises :class:`GameTooLargeError` with an explicit
        message rather than hanging.

    Returns
    -------
    dict
        Player -> value share. The shares sum to ``v(N)`` (efficiency), up to
        floating-point error.
    """
    ordered = _validate_coalition_inputs(
        players,
        characteristic_function,
        max_players=max_players,
        routine="shapley_value",
        tolerance=tolerance,
    )
    n = len(ordered)
    n_factorial = math.factorial(n)

    # Cache v so each coalition is evaluated at most once.
    cache: dict[frozenset, float] = {}

    def value(coalition: frozenset) -> float:
        if coalition not in cache:
            cache[coalition] = float(characteristic_function(coalition))
        return cache[coalition]

    shares: dict[Hashable, float] = {}
    for player in ordered:
        rest = [p for p in ordered if p != player]
        total = 0.0
        for size in range(len(rest) + 1):
            weight = math.factorial(size) * math.factorial(n - size - 1) / n_factorial
            for subset in itertools.combinations(rest, size):
                without = frozenset(subset)
                with_player = without | {player}
                total += weight * (value(with_player) - value(without))
        shares[player] = total
    return shares


# --------------------------------------------------------------------------
# Cooperative game theory: core membership and coalition stability
# --------------------------------------------------------------------------


def is_in_core(
    players: Sequence[Hashable],
    characteristic_function: CharacteristicFunction,
    allocation: Mapping[Hashable, float],
    *,
    max_players: int = MAX_COALITION_PLAYERS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> bool:
    """Whether ``allocation`` lies in the core of the cooperative game.

    Exactness: **exact**. Every one of the ``2**n`` coalitions is checked.

    An allocation ``x`` is in the core when it is

    * efficient: ``sum(x) == v(N)``, and
    * coalitionally rational: ``sum(x_i for i in S) >= v(S)`` for every
      coalition ``S``, so no group of actors can strictly gain by walking away
      and operating on its own.

    Note that the core can be empty (the 3-player simple majority game is the
    standard example), in which case this returns ``False`` for every
    allocation. Emptiness of the core is a fact about the game, not a failure
    of this function.
    """
    ordered = _validate_coalition_inputs(
        players,
        characteristic_function,
        max_players=max_players,
        routine="is_in_core",
        tolerance=tolerance,
    )

    missing = [p for p in ordered if p not in allocation]
    if missing:
        raise GameTheoryError(f"allocation is missing player(s) {missing!r}.")

    grand_value = float(characteristic_function(frozenset(ordered)))
    if abs(sum(float(allocation[p]) for p in ordered) - grand_value) > 1e-6:
        return False

    for size in range(1, len(ordered) + 1):
        for subset in itertools.combinations(ordered, size):
            coalition_payout = sum(float(allocation[p]) for p in subset)
            if coalition_payout < float(characteristic_function(frozenset(subset))) - 1e-9:
                return False
    return True


@dataclass(frozen=True)
class StableCoalition:
    """A coalition together with the allocation that makes it stable.

    Attributes
    ----------
    members:
        The coalition, as a frozenset of player identifiers.
    value:
        ``v(members)``, the value the coalition secures on its own.
    allocation:
        The Shapley allocation of the subgame restricted to ``members``. It
        sums to ``value``.
    """

    members: frozenset
    value: float
    allocation: Mapping[Hashable, float]


def stable_coalitions(
    players: Sequence[Hashable],
    characteristic_function: CharacteristicFunction,
    *,
    max_players: int = MAX_COALITION_PLAYERS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[StableCoalition]:
    """Coalitions whose Shapley split leaves nobody wanting to defect.

    Precisely what is computed
    --------------------------
    For each non-empty coalition ``S``:

    1. Build the *subgame* on ``S``: the same characteristic function, its
       domain restricted to subsets of ``S``.
    2. Compute the Shapley value ``x`` of that subgame. By efficiency,
       ``sum(x) == v(S)``, so ``S``'s own value is fully distributed.
    3. Keep ``S`` when ``x`` is **in the core of the subgame**, i.e. when for
       every non-empty ``T`` strictly inside ``S``,
       ``sum(x_i for i in T) >= v(T)``. No member and no sub-bloc can strictly
       gain by defecting from the Shapley split.

    So the stability notion is: *"the Shapley allocation of this coalition's
    own subgame is core-stable within that subgame."* This is checked exactly.

    How this relates to the core -- read carefully
    ----------------------------------------------
    This is **not** the same as "the coalition's core is non-empty", and it is
    **not** the core of the grand coalition.

    * The test is **stricter** than core non-emptiness. It examines one
      specific allocation (the Shapley one). A coalition can have a non-empty
      core while its Shapley allocation sits outside that core, and such a
      coalition is *excluded* here. So the returned list is a subset of the
      coalitions with non-empty cores: inclusion implies a non-empty core, but
      exclusion does not imply an empty one.
    * Consequently, absence from this list is evidence that the Shapley split
      is contestable, not proof that no stable split exists.

    To test the core directly for an allocation you already have, use
    :func:`is_in_core`.

    Singleton coalitions have no non-empty strict subcoalitions, so they are
    trivially stable and are always returned. That is a property of the
    definition, not a claim that a lone actor is strategically well placed.

    Cost
    ----
    Exact and exponential: the work is ``Theta(3**n)`` because every
    subcoalition of every coalition is inspected. ``max_players`` guards this
    and raises :class:`GameTooLargeError` rather than hanging.

    Returns
    -------
    list of StableCoalition
        Ordered by coalition size ascending, then by player order.
    """
    ordered = _validate_coalition_inputs(
        players,
        characteristic_function,
        max_players=max_players,
        routine="stable_coalitions",
        tolerance=tolerance,
    )

    cache: dict[frozenset, float] = {}

    def value(coalition: frozenset) -> float:
        if coalition not in cache:
            cache[coalition] = float(characteristic_function(coalition))
        return cache[coalition]

    results: list[StableCoalition] = []
    for size in range(1, len(ordered) + 1):
        for subset in itertools.combinations(ordered, size):
            members = frozenset(subset)
            allocation = shapley_value(
                subset,
                lambda coalition: value(frozenset(coalition)),
                max_players=max_players,
                tolerance=tolerance,
            )

            stable = True
            for inner_size in range(1, size):
                for inner in itertools.combinations(subset, inner_size):
                    payout = sum(allocation[p] for p in inner)
                    if payout < value(frozenset(inner)) - 1e-9:
                        stable = False
                        break
                if not stable:
                    break

            if stable:
                results.append(
                    StableCoalition(
                        members=members,
                        value=value(members),
                        allocation=allocation,
                    )
                )
    return results

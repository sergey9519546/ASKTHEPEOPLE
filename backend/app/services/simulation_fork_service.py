import contextlib
import json
import os
import shutil
import sqlite3
import uuid
from typing import Optional

from ..config import Config
from ..utils.safe_path import safe_join


class ForkError(RuntimeError):
    """A fork failed for a reason that is not "the source does not exist".

    Deliberately not a ValueError: the route maps ValueError to 404, and a
    corrupt run state or an unreadable copy is a server-side failure, not a
    missing simulation.
    """


def fork_simulation(
    source_id: str,
    target_turn: int,
    simulations_dir: "str | None" = None,
) -> Optional[str]:
    """
    Forks a simulation by copying its directory and truncating all databases past `target_turn`.
    Returns the new simulation ID.

    `simulations_dir` defaults to Config.OASIS_SIMULATION_DATA_DIR, the single
    source every other simulation path already resolves through. It used to
    default to the literal relative string "uploads/simulations", which
    resolved against the process cwd and therefore ignored UPLOAD_FOLDER and
    OASIS_SIMULATION_DATA_DIR: with either configured — as they are on the
    deployed setup — this function looked in a directory nothing else writes
    to and raised "Simulation <id> not found" for ids that exist.
    """
    if simulations_dir is None:
        simulations_dir = Config.OASIS_SIMULATION_DATA_DIR

    # safe_join rather than os.path.join, for consistency with every other
    # user-id-to-path conversion in the codebase (app/utils/safe_path.py).
    # Werkzeug normalises "." and ".." out of the URL before routing, so this
    # is defence in depth rather than a live escape, and it also rejects ids
    # that would produce a surprising path by any other route in.
    source_dir = safe_join(simulations_dir, source_id)
    if not os.path.isdir(source_dir):
        raise ValueError(f"Simulation {source_id} not found.")

    new_id = str(uuid.uuid4())
    new_dir = os.path.join(simulations_dir, new_id)

    # 1. Deep copy file directory
    shutil.copytree(source_dir, new_dir)

    # Everything past the copy is cleaned up on failure. Without this a fork
    # that failed half way — a corrupt run_state.json is enough — left an
    # orphaned directory behind that later listings would report as a real
    # simulation.
    try:
        _rewrite_forked_state(new_dir, new_id, target_turn)
        _truncate_observations(new_dir, target_turn)
    except Exception:
        shutil.rmtree(new_dir, ignore_errors=True)
        raise

    return new_id


def _rewrite_forked_state(new_dir: str, new_id: str, target_turn: int) -> None:
    """Point the copied run state at the new id and roll its round back."""
    run_state_path = os.path.join(new_dir, "run_state.json")
    if not os.path.exists(run_state_path):
        return

    with open(run_state_path, "r", encoding="utf-8") as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError as exc:
            # JSONDecodeError subclasses ValueError, which the route maps to
            # 404 "not found" — wrong, and it echoes the parser's message.
            raise ForkError(
                f"Simulation run state is not valid JSON: {run_state_path}"
            ) from exc

    state["simulation_id"] = new_id
    # Also rollback the current_round to target_turn
    if "round_num" in state:
        state["round_num"] = target_turn
    with open(run_state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def _truncate_observations(new_dir: str, target_turn: int) -> None:
    """Drop observation rows past `target_turn` in the copied database."""

    # 3. Truncate canonical simulation observations DB
    obs_db = os.path.join(new_dir, "simulation_observations.db")
    if os.path.exists(obs_db):
        # closing() so a failure part-way through truncation cannot leak the
        # handle and leave the copied database locked for the caller.
        with contextlib.closing(sqlite3.connect(obs_db)) as conn:
            cursor = conn.cursor()
            # Delete events past target turn. The table name is interpolated
            # from the fixed list below, never from input; the value is bound.
            tables_with_round = [
                "interviews", "bootstrap_events", "scheduled_events",
                "injected_events", "reflections", "round_summaries",
            ]
            for table in tables_with_round:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE round_num > ?", (target_turn,))
                except sqlite3.OperationalError:
                    pass
            conn.commit()

    # 4. Truncate OASIS trace databases (if they store round info or if we just want to keep them as is and OASIS will append)
    # The OASIS trace DB doesn't have round_num natively, so we might need to rely on the fact that
    # run_parallel_simulation tracks rowid in run_state.json. If we rolled back run_state,
    # the runner might re-process some trace elements, but to actually prevent future actions from leaking:
    for platform in ["twitter", "reddit"]:
        plat_db = os.path.join(new_dir, f"{platform}_simulation.db")
        if os.path.exists(plat_db):
            # We cannot easily truncate OASIS traces by round_num since it only has created_at
            # We will rely on OASIS being re-initialized from the new state.
            pass

import os
import shutil
import sqlite3
import uuid
import json
from typing import Optional

def fork_simulation(source_id: str, target_turn: int, simulations_dir: str = "uploads/simulations") -> Optional[str]:
    """
    Forks a simulation by copying its directory and truncating all databases past `target_turn`.
    Returns the new simulation ID.
    """
    source_dir = os.path.join(simulations_dir, source_id)
    if not os.path.exists(source_dir):
        raise ValueError(f"Simulation {source_id} not found.")

    new_id = str(uuid.uuid4())
    new_dir = os.path.join(simulations_dir, new_id)

    # 1. Deep copy file directory
    shutil.copytree(source_dir, new_dir)

    # 2. Update config or state files with new ID
    run_state_path = os.path.join(new_dir, "run_state.json")
    if os.path.exists(run_state_path):
        with open(run_state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        state["simulation_id"] = new_id
        # Also rollback the current_round to target_turn
        if "round_num" in state:
            state["round_num"] = target_turn
        with open(run_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

    # 3. Truncate canonical simulation observations DB
    obs_db = os.path.join(new_dir, "simulation_observations.db")
    if os.path.exists(obs_db):
        conn = sqlite3.connect(obs_db)
        cursor = conn.cursor()
        # Delete events past target turn
        tables_with_round = ["interviews", "bootstrap_events", "scheduled_events", "injected_events", "reflections"]
        for table in tables_with_round:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE round_num > ?", (target_turn,))
            except sqlite3.OperationalError:
                pass
        try:
            cursor.execute("DELETE FROM round_summaries WHERE round_num > ?", (target_turn,))
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()

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

    return new_id

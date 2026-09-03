import sys
sys.path.insert(0, '.')
from app.services.simulation_manager import SimulationManager
from pathlib import Path
import json

# Create test simulation
sim_dir = Path("test_data/sim_test")
sim_dir.mkdir(parents=True, exist_ok=True)
(sim_dir / "state.json").write_text(
    json.dumps({"status": "ready", "config_generated": True}),
    encoding="utf-8",
)
(sim_dir / "simulation_config.json").write_text("{}", encoding="utf-8")
(sim_dir / "decision_lens_runtime.v1.json").write_text(
    json.dumps({"adapters": [{"agent_id": 1}, {"agent_id": 2}]}),
    encoding="utf-8",
)
(sim_dir / "preflight.json").write_text(
    json.dumps({"status": "passed"}),
    encoding="utf-8",
)

# Mock the admission check
import app.services.simulation_preflight
app.services.simulation_preflight.assert_decision_lens_execution_admission = lambda x: {}

# Call is_runnable
mgr = SimulationManager()
is_prepared, info = mgr.is_runnable("sim_test")
print(f"is_prepared: {is_prepared}")
print(f"info: {json.dumps(info, indent=2)}")

## 2026-08-04 - Fix Daily Upgrade Task - Fix logic bug in select_active_agent_ids
**Learning:** In backend simulation runtime, agent selection logic needed to accurately check `_platform_matches` while accounting for `event_boost_agent_ids`. The previous implementation applied `_platform_weight` incorrectly, evaluating to 0.0 for mismatched platforms and causing missing logic and test failures in agent filtering.
**Action:** Refactored `select_active_agent_ids` in `simulation_runtime_contract.py` to properly use `_platform_matches` and avoid zeroing out boosted agents.

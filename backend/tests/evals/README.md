# Offline evaluations for ASKTHEPEOPLE / Synthetic Decision Explorer

This directory contains offline, fixture-backed quality checks for the
ASKTHEPEOPLE Synthetic Decision Explorer. These checks exercise deterministic
profile, path-signature, disclosure, and truth-contract helpers. They do not
call a paid model, recruit human respondents, establish population fidelity, or
validate a forecast.

Version: 2.0.0. Last reviewed: 2026-10-31.

## Scope

- `test_profile_quality.py` checks rule-based profile fixture diversity and
  scans generated fixture text for stereotype and essentialist markers.
- `test_path_distinctness.py` checks deterministic decision signatures and
  assumption-isolation behavior in the local test helper.
- `test_truth_contract.py` checks disclosure structures and local API/test
  fixtures; it does not measure API endpoint coverage.
- `test_variant_persona_distinctness.py` checks fixture persona similarity
  using word shingles (offline text similarity, not behavioral fidelity).
- `test_results_artifact.py` checks artifact freshness, provenance, output-path
  handling, and outcome/error accounting.

The numeric thresholds in the test files are acceptance thresholds for these
offline heuristics only. A passing result is not a fidelity or accuracy claim.

## Running

From `backend/`:

```bash
# Fresh artifact is written to backend/.pytest_eval_results/results.json.
pytest tests/evals/ -v --tb=short

# Choose any output path; parent directories are created automatically.
pytest tests/evals/ -v --eval-results C:/tmp/askthepeople-evals/results.json
```

The `--eval-results` path is used by both the `eval_results_path` fixture and
the pytest result plugin. Each run writes a complete fresh snapshot and does
not merge from an existing output file.

The tracked `tests/evals/results.json` is historical evidence. It is never
used as a fallback for current-session assertions and is never rewritten by the
suite. Historical-byte checks may read it explicitly to verify its integrity.

## Artifact contract

A fresh artifact contains:

- `artifact_schema_version` and `scope: "current_session"`;
- `freshness: "session_only"`, a session id, and start/finish timestamps;
- `status`: `complete`, `partial`, or `failed`. A selected subset with missing
  required metrics remains `partial`; selected-test success is recorded separately.
  Setup, call, teardown, or eval collection failures produce `failed`;
- `selected_tests` and `_test_summary`, including `not_run`, setup/teardown
  error counts, and error entries containing test identifiers and phases only;
- `metrics` plus top-level metric compatibility keys;
- `metric_provenance`, including producer test id, offline measurement class,
  dataset-fixture identity, `dataset_fixture_id_sha256` (hash of that ID,
  not dataset contents), and test-file SHA-256 of the inline fixture recipe;
- `producers`, one record for each metric-producing test.

`offline_heuristic` is the expected measurement class for these tests. It
labels how a metric was produced; it does not claim synthetic output matches
real people or real-world outcomes.

## Adding an evaluation

1. Add the test under `tests/evals/`.
2. Use `eval_results_path` and call `save_eval_results(...)` for produced
   metrics.
3. Keep threshold assertions in the producer test so selecting a subset does
   not depend on another test's execution order.
4. Provide a stable `dataset_fixture` identity when the metric is tied to a
   fixture population.
5. Do not read or overwrite `tests/evals/results.json` from a normal test run.

## Impact and rollback

Current-session evidence no longer carries historical metrics. Consumers should
use the configured output path, inspect status and producer outcomes, and treat
metrics from failed or unfinished producers as diagnostic observations only.
The suite retains top-level metric names alongside the explicit `metrics` map.
No threshold was lowered. Production code, prompts, and stored user data are
unaffected. Rolling back this harness change needs no data migration; preserve
the tracked historical artifact and do not restore it as fresh run evidence.

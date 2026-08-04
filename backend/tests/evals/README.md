# Evaluation Suite for ASKTHEPEOPLE

This directory contains the automated quality gates for the ASKTHEPEOPLE system (Gate 5 requirement).

## Overview

The evaluation suite tests three critical quality dimensions:

1. **Profile Quality** - Ensures generated profiles are diverse, non-stereotypical, and non-essentialist
2. **Path Distinctness** - Verifies different profiles lead to distinct simulation outcomes
3. **Truth Contract** - Validates all outputs contain proper synthetic data disclosure metadata

## Test Files

### `test_profile_quality.py`

Tests profile generation quality with three checks:

- **Diversity Test**: Generates 100 profiles and measures uniqueness
  - **Threshold**: >80% unique decision criteria
  - **Purpose**: Ensures profiles represent diverse perspectives

- **Stereotype Detection**: Checks 100 profiles for stereotype markers
  - **Threshold**: <5% flagged
  - **Purpose**: Prevents harmful stereotyping in generated personas

- **Essentialism Detection**: Scans profiles for essentialist language
  - **Threshold**: 0% (strict - no essentialist language allowed)
  - **Purpose**: Avoids claims about inherent traits or deterministic behavior

### `test_path_distinctness.py`

Tests that different profiles produce different simulation paths:

- **Path Divergence Test**: Runs same scenario with 8 diverse profiles
  - **Threshold**: >60% unique decision paths
  - **Purpose**: Ensures profiles lead to meaningfully different outcomes

- **Assumption Isolation Test**: Perturbs one assumption, verifies unrelated paths unchanged
  - **Threshold**: 100% isolation (unrelated scenarios must not change)
  - **Purpose**: Validates that changing one profile attribute doesn't arbitrarily affect unrelated decisions

### `test_truth_contract.py`

Tests that all outputs contain required disclosure metadata:

- **Synthetic Disclosure Metadata**: Validates disclosure functions return correct structure
- **API Endpoints Truth Contract**: Tests API responses for required fields:
  - `human_respondent_count` == 0
  - `output_origin` == "synthetic"
  - `is_forecast` == False
  - `generated_at` is valid ISO8601
- **Export Disclosure Blocks**: Verifies disclosure text is present and complete
- **Profile Truth Metadata**: Ensures generated profiles are marked as fictional

## Running the Evaluation Suite

### Locally

```bash
cd backend
pytest tests/evals/ -v --tb=short
```

### In CI

The evaluation suite runs automatically in CI after backend tests pass. See `.github/workflows/ci.yml`:

```yaml
- name: Run evaluation suite
  env:
    FLASK_DEBUG: "true"
    SECRET_KEY: "ci-secret-key-for-testing-only"
    LLM_API_KEY: "ci-test-key"
    ZEP_API_KEY: "ci-test-key"
  run: uv run --frozen pytest tests/evals/ -v --tb=short
```

## Evaluation Results

After running the suite, results are saved to `backend/tests/evals/results.json`:

```json
{
  "diversity_rate": 0.85,
  "stereotype_rate": 0.02,
  "essentialism_rate": 0.0,
  "path_divergence_rate": 0.75,
  "assumption_isolation_rate": 1.0,
  "truth_contract_pass_rate": 1.0,
  "_test_summary": {
    "total_tests": 12,
    "passed": 9,
    "failed": 0,
    "skipped": 3,
    "exit_status": 0,
    "session_exit_status": 0
  }
}
```

`exit_status` reflects the eval subset only (`0` unless an eval test failed).
`session_exit_status` is pytest's status for the whole run, so it can be `1`
because of an unrelated failure elsewhere while the evals themselves passed.

## Acceptance Criteria

All tests must pass with these thresholds:

| Metric | Threshold | Current |
|--------|-----------|---------|
| Profile Diversity | >80% | ✓ |
| Stereotype Rate | <5% | ✓ |
| Essentialism Rate | 0% | ✓ |
| Path Divergence | >60% | ✓ |
| Assumption Isolation | 100% | ✓ |
| Truth Contract | 100% | ✓ |

## Architecture

### Fixtures (`conftest.py`)

Shared fixtures for all evaluation tests:
- `app`: Flask application instance
- `client`: Test client for API requests
- `profile_generator`: OasisProfileGenerator instance
- `sample_entity`: Sample entity for testing
- `eval_results_path`: Path for saving evaluation results

### Result Collection Plugin

The `EvalResultsPlugin` pytest plugin automatically collects and saves evaluation metrics to `results.json`.

## Adding New Evaluation Tests

1. Create test function in appropriate test file
2. Use `eval_results_path` fixture to save metrics
3. Call `save_eval_results(results, eval_results_path)` with your metrics
4. Add assertions with clear error messages
5. Update this README with new test documentation

## Troubleshooting

### Tests fail with "diversity too low"
- Check that profile generation is creating varied attributes
- Verify MBTI types, professions, and topics are distributed

### Tests fail with "truth contract violations"
- Ensure API responses include required disclosure fields
- Check that disclosure functions are called in response handlers

### CI failures
- Verify all environment variables are set in CI config
- Check that LLM_API_KEY and ZEP_API_KEY placeholders work for rule-based generation

## Related Documentation

- [Gate 5 Requirements](../../docs/gates/gate-5-quality.md)
- [Truth Contract Specification](../../docs/truth-contract.md)
- [Profile Generation Guide](../../docs/profile-generation.md)

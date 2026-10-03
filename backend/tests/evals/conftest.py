"""Shared fixtures and pytest plugin for evaluation suite."""

import pytest
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for app imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app
from app.services.oasis_profile_generator import (
    OasisProfileGenerator,
    OasisAgentProfile,
)
from app.services.zep_entity_reader import EntityNode


# In-process record of everything the suite measured during THIS session.
#
# The obvious channel -- reading each test's own `tmp_path` file back out of
# `item.funcargs` at session-finish time -- does not work. pytest populates
# `funcargs` during setup and empties it again during teardown, so by the time
# `pytest_sessionfinish` runs it is `None` (measured against the pinned pytest
# in this repo). That is why the artifact used to end up carrying only
# `_test_summary` no matter how the file was read: there was nothing to read.
# `save_eval_results` is therefore also recorded here, and this accumulator is
# the primary source the session-finish hook merges.
_SESSION_RESULTS: dict = {}


def recorded_eval_results() -> dict:
    """Metrics available to an in-session assertion.

    Prefers what this session has measured so far, then falls back to the
    committed artifact, which is the previous run's recorded evidence.

    The per-test ``eval_results_path`` cannot be used for this. It is a fresh
    pytest tmp file per test, so a test asking whether it exists is asking
    whether a file written *later* has been written yet — which is why the
    three summary tests skipped unconditionally and their thresholds never ran.

    Returns an empty dict only when neither source has anything, which callers
    must treat as a failure rather than a skip: a missing metric means the thing
    that produces it did not run.
    """
    if _SESSION_RESULTS:
        return dict(_SESSION_RESULTS)
    committed = Path(__file__).parent / "results.json"
    return _read_json_dict(committed) or {}


@pytest.fixture()
def recorded_results():
    """Metrics available to an in-session assertion.

    Prefer this over importing the helper. Importing conftest from a test body
    re-enters pytest's plugin machinery and hangs the run.
    """
    return recorded_eval_results()


def _read_json_dict(path: Path):
    """Read ``path`` as a JSON object, or return ``None``.

    A missing file is the ordinary case (a test that measured nothing, or a
    first run with no artifact committed yet), and an unparseable one must
    not take the session down: this artifact is evidence, not a gate. Every
    failure mode collapses to ``None`` so the caller decides whether to warn
    or stay quiet. ``json.JSONDecodeError`` and ``UnicodeDecodeError`` are
    both ``ValueError``, and the ``OSError`` branch covers a missing,
    unreadable, or directory-shaped path.
    """
    try:
        with open(path, 'r') as f:
            loaded = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def profile_generator(monkeypatch):
    """Create profile generator instance with mock test configuration."""
    monkeypatch.setenv("LLM_API_KEY", "test-eval-mock-key-32characterslong!")
    return OasisProfileGenerator(api_key="test-eval-mock-key-32characterslong!")


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    return EntityNode(
        uuid="test-uuid-001",
        name="Alex Chen",
        labels=["Person", "Student"],
        summary="A computer science student interested in AI and ethics",
        attributes={
            "occupation": "Student",
            "institution": "Test University"
        },
        related_edges=[
            {
                "fact": "Alex Chen studies at Test University",
                "edge_name": "studies_at",
                "direction": "outgoing"
            }
        ],
        related_nodes=[
            {
                "name": "Test University",
                "labels": ["University"],
                "summary": "A research university"
            }
        ]
    )


@pytest.fixture
def sample_decision_prompt():
    """Sample decision prompt for profile generation."""
    return "Should universities implement stricter AI ethics guidelines for student research projects?"


@pytest.fixture
def eval_results_path(tmp_path):
    """Path for saving evaluation results."""
    results_path = tmp_path / "results.json"
    yield results_path

    # Merge this test's results into the tracked artifact.
    #
    # `shutil.copy` used to sit here, and it was a second, independent way for
    # a measured result to be thrown away: it replaced the artifact with one
    # test's file, so the bytes on disk were always whichever eval test
    # happened to finish last. Merging keeps every earlier contribution, which
    # also means the artifact stays truthful if the process dies mid-run.
    if results_path.exists():
        actual_path = Path(__file__).parent / "results.json"
        merged = _read_json_dict(actual_path) or {}
        merged.update(_read_json_dict(results_path) or {})
        with open(actual_path, 'w') as f:
            json.dump(merged, f, indent=2)


def save_eval_results(results: dict, results_path: Path):
    """Save evaluation results to JSON file."""
    # Load existing results if available
    existing = {}
    if results_path.exists():
        try:
            with open(results_path, 'r') as f:
                existing = json.load(f)
        except:
            pass
    
    # Merge results
    existing.update(results)

    # Save
    with open(results_path, 'w') as f:
        json.dump(existing, f, indent=2)

    # Record into the session accumulator too, so the result reaches the
    # tracked artifact even though the per-test file is unreachable once
    # pytest has torn the fixtures down.
    _SESSION_RESULTS.update(results)


# ============================================================================
# Pytest Plugin for Result Collection
# ============================================================================

class EvalResultsPlugin:
    """Plugin to collect and save evaluation results."""
    
    def __init__(self, results_path=None, session_results=None):
        self.results = {}
        self.test_outcomes = {}
        # Testability seams. Production leaves both None: it writes the tracked
        # artifact beside this module and reads the live session accumulator.
        # A test that exercises the merge passes a tmp artifact and an explicit
        # accumulator, so it can assert the merge without mutating committed
        # evidence or observing the running session's own measurements. There
        # is no second production call site. `session_results={}` is therefore
        # meaningful and distinct from the `None` default.
        self.results_path = (
            Path(results_path) if results_path is not None else None
        )
        self.session_results = session_results
    
    def pytest_runtest_logreport(self, report):
        """Collect test outcomes.

        Records the definitive outcome per test. A test skipped during setup
        never reaches ``when == "call"``, so we must capture the setup-phase
        skip too — otherwise it lands in ``total`` (counted from session
        items) but not in ``passed/failed/skipped`` (counted from call
        outcomes), producing the contradictory ``passed + failed + skipped
        != total`` the exec-plan 08 Fix 2 audit flagged. The rule: the last
        non-passing setup/teardown outcome wins for that nodeid; a real
        ``call`` outcome always supersedes a setup report.
        """
        if report.when == "call":
            self.test_outcomes[report.nodeid] = {
                "outcome": report.outcome,
                "duration": report.duration,
            }
        elif report.skipped and report.nodeid not in self.test_outcomes:
            # A skip in setup (e.g. a missing fixture) — record it so it is
            # counted as skipped rather than dropped on the floor.
            self.test_outcomes[report.nodeid] = {
                "outcome": "skipped",
                "duration": getattr(report, "duration", 0.0),
            }
    
    def pytest_sessionfinish(self, session, exitstatus):
        """Save results at the end of the test session."""
        # Only save if we're in the evals directory
        if not any('evals' in str(item.fspath) for item in session.items):
            return
        
        # Determine output path
        evals_dir = Path(__file__).parent
        results_path = self.results_path or (evals_dir / "results.json")

        # Start from what the artifact already carries instead of from empty.
        # The per-test `eval_results_path` fixture copies each test's own
        # results into this same file, so the bytes already on disk are real
        # contributions from this session. Overwriting them is what made this
        # artifact write-only: the only thing that survived was the single
        # per-test file read below plus `_test_summary`, so the committed
        # evidence recorded that tests ran and never what they measured.
        # Unreadable or absent is tolerated -- a corrupt artifact must not
        # fail a passing eval session.
        self.results = _read_json_dict(results_path) or {}
        if self.results:
            print(
                f"\n\nEvaluation artifact carried "
                f"{len(self.results)} existing key(s) into the merge"
            )

        # Merge EVERY eval test's result, accumulating across the session.
        # Three sources, merged in this order; later writes win, and the key
        # sets are complementary in practice.
        #
        # 1. The session accumulator: every `save_eval_results` call made
        #    during this session, so this is the channel that actually
        #    carries every test's measurement. It is read HERE rather than in
        #    the constructor, because the constructor runs at
        #    `pytest_configure` time -- before any test has measured anything.
        session_results = (
            _SESSION_RESULTS if self.session_results is None
            else self.session_results
        )
        merged_from = len(session_results)
        self.results.update(session_results)

        # 2. Any test's own `tmp_path` file still reachable through
        #    `funcargs`. Under the pinned pytest this is empty by now --
        #    `funcargs` is cleared during teardown -- so this contributes
        #    nothing today and is kept only as the fallback for a pytest that
        #    retains it. Crucially there is no `break`: the old `break` read
        #    one test's file and then discarded everything else on disk.
        for item in session.items:
            funcargs = getattr(item, 'funcargs', None) or {}
            per_test_path = funcargs.get('eval_results_path')
            if per_test_path is None:
                continue
            per_test = _read_json_dict(Path(per_test_path))
            if per_test is None:
                continue
            self.results.update(per_test)
            merged_from += 1

        # 3. Nothing to do for a test that measured nothing: it contributes no
        #    keys and must not hide the tests that did.

        # Add test execution metadata
        eval_tests = [
            item for item in session.items
            if 'evals' in str(item.fspath)
        ]
        
        # Filter outcomes to eval tests only
        eval_test_ids = {item.nodeid for item in eval_tests}
        eval_outcomes = {
            nodeid: outcome
            for nodeid, outcome in self.test_outcomes.items()
            if nodeid in eval_test_ids
        }
        
        passed = sum(
            1 for outcome in eval_outcomes.values()
            if outcome['outcome'] == 'passed'
        )
        failed = sum(
            1 for outcome in eval_outcomes.values()
            if outcome['outcome'] == 'failed'
        )
        skipped = sum(
            1 for outcome in eval_outcomes.values()
            if outcome['outcome'] == 'skipped'
        )
        
        total = len(eval_test_ids)
        
        # Sanity check
        if passed + failed + skipped != total:
            print(f"\n\nWARNING: Eval count mismatch: {passed}+{failed}+{skipped} != {total}")
        
        # `exit_status` describes the EVAL subset, so it stays consistent with
        # the counts beside it. pytest's `exitstatus` covers the whole session:
        # in a full-suite run an unrelated failure anywhere would record
        # "failed: 0, exit_status: 1" here, which reads as a broken eval suite.
        # The session status is still recorded, under its own name.
        self.results['_test_summary'] = {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'exit_status': 0 if failed == 0 else 1,
            'session_exit_status': int(exitstatus),
        }
        
        # Save results
        try:
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(
                f"\n\nEvaluation results saved to: {results_path} "
                f"({len(self.results)} top-level key(s), "
                f"per-test results merged from {merged_from} test(s))"
            )
        except Exception as e:
            print(f"\n\nWarning: Failed to save evaluation results: {e}")


def pytest_configure(config):
    """Register custom markers and plugin."""
    config.addinivalue_line(
        "markers", "eval: mark test as an evaluation suite test"
    )
    
    if config.pluginmanager.hasplugin('eval_results'):
        return

    # One reset per session, here, before any test can call
    # `save_eval_results`. Resetting inside the plugin constructor instead
    # would let a plugin built inside a test erase the running session's
    # measurements.
    _SESSION_RESULTS.clear()

    plugin = EvalResultsPlugin()
    config.pluginmanager.register(plugin, 'eval_results')

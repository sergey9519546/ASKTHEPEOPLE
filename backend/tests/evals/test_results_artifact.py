"""The committed eval artifact must carry metrics, not only a summary.

`tests/evals/results.json` is this suite's evidence artifact and is tracked
by git. It was write-only: the only top-level key it carried was
`_test_summary`, so it recorded that tests ran and never what they measured.
`docs/exec-plans/08-harvest-framework-engineering-fixes.md` names the same
defect as its Fix 2.2 "CURRENT PROBLEM": "`results.json` contains only
`_test_summary`, no actual eval metrics".

Two independent guards live here because they fail for different reasons:

* the merge itself, exercised against a `tmp_path` artifact so the
  assertion never depends on session state -- this file runs INSIDE the suite
  whose own `eval_results_path` teardown rewrites the tracked artifact;
* the tracked artifact's committed bytes, snapshotted at collection time,
  before any test in this session can run, so the guard cannot be fooled by
  a file this very session rewrote.

Neither guard reads the tracked artifact during a test body on purpose: by
then the last-executed eval test's teardown has already copied its own
single-test results over the top, which is transient state, not evidence.
"""

import json
from pathlib import Path

from . import conftest
from .conftest import EvalResultsPlugin, save_eval_results, _read_json_dict

ARTIFACT = Path(__file__).resolve().parent / "results.json"

#: The rates the suite measures. Each one has its own threshold, asserted by
#: the test that measures it. None of them may be absent from the artifact:
#: their absence is exactly what made the artifact write-only.
REQUIRED_METRICS = (
    "diversity_rate",
    "stereotype_rate",
    "essentialism_rate",
    "path_divergence_rate",
    "assumption_isolation_rate",
    "truth_contract_pass_rate",
)

# Read during collection, before any test in this session executes.
_COMMITTED_AT_IMPORT = _read_json_dict(ARTIFACT)


class _StubItem:
    """The two attributes `pytest_sessionfinish` reads off an item."""

    def __init__(self, nodeid, fspath, funcargs=None):
        self.nodeid = nodeid
        self.fspath = fspath
        self.funcargs = funcargs or {}


class _StubSession:
    def __init__(self, items):
        self.items = items


class _StubReport:
    """Minimal stand-in for pytest's `TestReport`."""

    def __init__(self, nodeid, when="call", outcome="passed"):
        self.nodeid = nodeid
        self.when = when
        self.outcome = outcome
        self.duration = 0.0
        self.skipped = outcome == "skipped"


def _eval_session(tmp_path, artifacts):
    """Build a stub eval session.

    `artifacts` maps a test name to the JSON object that test wrote to its
    own `tmp_path`, or to `None` for a test that measured nothing.
    """
    fspath = str(tmp_path / "evals" / "test_example.py")
    items = []
    for name, payload in artifacts.items():
        funcargs = {}
        if payload is not None:
            per_test = tmp_path / f"tmp-{name}" / "results.json"
            per_test.parent.mkdir(parents=True, exist_ok=True)
            per_test.write_text(json.dumps(payload), encoding="utf-8")
            funcargs["eval_results_path"] = per_test
        items.append(
            _StubItem(f"evals/test_example.py::test_{name}", fspath, funcargs)
        )
    return _StubSession(items)


def _finish(artifact, session, exitstatus=0, session_results=None, feed=True):
    # `session_results={}` pins the primary merge source to empty so these
    # tests observe only what they staged, never the running session's own
    # measurements.
    plugin = EvalResultsPlugin(
        results_path=artifact,
        session_results={} if session_results is None else session_results,
    )
    if feed:
        # A stub session reports no outcomes unless asked, which makes the
        # hook print its own count-mismatch warning. Feed one passing report
        # per item so the staged session looks like a real one.
        for item in session.items:
            plugin.pytest_runtest_logreport(_StubReport(item.nodeid))
    plugin.pytest_sessionfinish(session, exitstatus)
    return json.loads(artifact.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Guard 1: the merge the session-finish hook performs.
# ---------------------------------------------------------------------------

def test_sessionfinish_merges_every_tests_results(tmp_path):
    """Accumulate across every eval test, not just the first one.

    pytest's `tmp_path` is unique per test, so each file holds one test's
    metrics and the key sets are complementary. Breaking after the first
    kept a single test's contribution and discarded the rest.
    """
    artifact = tmp_path / "results.json"
    session = _eval_session(
        tmp_path,
        {
            "alpha": {"alpha_rate": 0.1},
            "beta": {"beta_rate": 0.2},
            "gamma": {"gamma_rate": 0.3},
            "silent": None,
        },
    )

    written = _finish(artifact, session)

    missing = {"alpha_rate", "beta_rate", "gamma_rate"} - written.keys()
    assert not missing, (
        f"per-test eval results missing from the artifact: {sorted(missing)}. "
        "Only one test's results reached the file."
    )


def test_sessionfinish_preserves_keys_already_on_disk(tmp_path):
    """Merge with the artifact, never replace it.

    The bytes already on disk are real contributions -- the per-test
    `eval_results_path` teardown copies each test's results into this same
    file -- plus any legitimately maintained key. Replacing the file
    destroyed all of them, which is why the committed artifact recorded
    that tests ran and nothing about what they measured.
    """
    artifact = tmp_path / "results.json"
    artifact.write_text(
        json.dumps({"alpha_rate": "stale", "maintained_by_hand": True}),
        encoding="utf-8",
    )
    session = _eval_session(
        tmp_path,
        {
            "alpha": {"alpha_rate": 0.1},
            "beta": {"beta_rate": 0.2},
        },
    )

    written = _finish(artifact, session)

    assert written["maintained_by_hand"] is True, (
        "a top-level key the artifact legitimately carried was destroyed by "
        "the session-finish write"
    )
    assert written["beta_rate"] == 0.2
    assert written["alpha_rate"] == 0.1, (
        "this session's measurement must supersede the previous run's value"
    )


def test_sessionfinish_merges_the_session_accumulator(tmp_path):
    """The accumulator is the channel that actually carries every measurement.

    pytest empties `item.funcargs` during teardown, so a session-finish hook
    cannot read a test's own results file back out of it. `save_eval_results`
    therefore also records in-process, and that record must reach the artifact
    even when no per-test file is reachable.
    """
    artifact = tmp_path / "results.json"
    session = _eval_session(tmp_path, {"measured_nothing": None})

    written = _finish(
        artifact,
        session,
        session_results={
            "diversity_rate": 0.8,
            "truth_contract_pass_rate": 1.0,
        },
    )

    assert written["diversity_rate"] == 0.8
    assert written["truth_contract_pass_rate"] == 1.0


def test_save_eval_results_records_into_the_session_accumulator(tmp_path, monkeypatch):
    """`save_eval_results` writes the file AND records in-process.

    Round-tripped through a fresh plugin, so the assertion covers the real
    wiring rather than a hand-staged accumulator.

    `monkeypatch` rebinds the module-level accumulator for the duration of this
    test, and `save_eval_results` plus the session-finish hook both resolve it
    as a module global at call time. Without that, this test's staged key
    would be merged into the tracked artifact by the real session-finish hook
    and would ship as fabricated evidence.
    """
    monkeypatch.setattr(conftest, "_SESSION_RESULTS", {})

    staged = tmp_path / "results.json"
    save_eval_results({"staged_metric": 0.25}, staged)

    assert json.loads(staged.read_text(encoding="utf-8"))["staged_metric"] == 0.25
    assert conftest._SESSION_RESULTS["staged_metric"] == 0.25

    artifact = tmp_path / "artifact.json"
    written = _finish(
        artifact,
        _eval_session(tmp_path, {"measured_nothing": None}),
        session_results=dict(conftest._SESSION_RESULTS),
    )
    assert written["staged_metric"] == 0.25
    assert "staged_metric" not in _COMMITTED_AT_IMPORT, (
        "a test-only key leaked into the committed artifact"
    )


def test_sessionfinish_tolerates_a_missing_artifact(tmp_path):
    """No committed artifact yet is normal, not an error."""
    artifact = tmp_path / "results.json"
    assert not artifact.exists()
    session = _eval_session(tmp_path, {"alpha": {"alpha_rate": 0.1}})

    written = _finish(artifact, session)

    assert written["alpha_rate"] == 0.1


def test_sessionfinish_tolerates_an_unreadable_artifact(tmp_path):
    """A corrupt artifact is evidence gone wrong, not a reason to fail the run."""
    artifact = tmp_path / "results.json"
    artifact.write_text("{ this is not json", encoding="utf-8")
    session = _eval_session(tmp_path, {"alpha": {"alpha_rate": 0.1}})

    written = _finish(artifact, session)

    assert written["alpha_rate"] == 0.1
    assert "_test_summary" in written


def test_sessionfinish_tolerates_a_non_object_artifact(tmp_path):
    """A JSON array or scalar where an object was expected is likewise survivable."""
    artifact = tmp_path / "results.json"
    artifact.write_text("[1, 2, 3]", encoding="utf-8")
    session = _eval_session(tmp_path, {"alpha": {"alpha_rate": 0.1}})

    written = _finish(artifact, session)

    assert written["alpha_rate"] == 0.1


def test_sessionfinish_keeps_eval_subset_exit_status_semantics(tmp_path):
    """`exit_status` describes the EVAL subset; the session's own status is
    recorded separately.

    pytest's `exitstatus` covers the whole session, so in a full-suite run
    an unrelated failure anywhere would otherwise record "failed: 0,
    exit_status: 1" here, which reads as a broken eval suite. The careful
    comment above the assignment in `conftest.py` must not regress.
    """
    artifact = tmp_path / "results.json"
    session = _eval_session(
        tmp_path,
        {"alpha": {"alpha_rate": 0.1}, "beta": {"beta_rate": 0.2}},
    )
    plugin = EvalResultsPlugin(results_path=artifact, session_results={})
    for item in session.items:
        plugin.pytest_runtest_logreport(_StubReport(item.nodeid))

    plugin.pytest_sessionfinish(session, 1)

    summary = json.loads(artifact.read_text(encoding="utf-8"))["_test_summary"]
    assert summary["failed"] == 0
    assert summary["exit_status"] == 0, (
        "exit_status must describe the eval subset, not the whole session"
    )
    assert summary["session_exit_status"] == 1, (
        "the whole-session status must still be recorded, under its own name"
    )
    assert summary["total_tests"] == 2
    assert (
        summary["passed"] + summary["failed"] + summary["skipped"]
        == summary["total_tests"]
    )


# ---------------------------------------------------------------------------
# Guard 2: the tracked artifact's committed bytes.
# ---------------------------------------------------------------------------

def test_committed_artifact_carries_every_metric():
    """The committed evidence records what was measured, not just that tests ran."""
    assert _COMMITTED_AT_IMPORT is not None, (
        f"{ARTIFACT} is missing or is not a JSON object. The eval suite is "
        "required to leave a parseable artifact; re-run "
        "`pytest tests/evals/` and commit the result."
    )

    missing = [key for key in REQUIRED_METRICS if key not in _COMMITTED_AT_IMPORT]
    assert not missing, (
        f"{ARTIFACT.name} is write-only: it records that tests ran and never "
        f"what they measured. Missing metrics: {missing}. Present keys: "
        f"{sorted(_COMMITTED_AT_IMPORT)}."
    )


def test_committed_artifact_metrics_are_plausible_rates():
    """Every required metric is a rate in [0, 1]."""
    assert _COMMITTED_AT_IMPORT is not None, f"{ARTIFACT} is missing or unreadable"

    for key in REQUIRED_METRICS:
        value = _COMMITTED_AT_IMPORT[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"{key} should be a measured number, got {type(value).__name__}"
        )
        assert 0.0 <= value <= 1.0, f"{key} = {value} is outside [0, 1]"


def test_committed_artifact_summary_is_internally_consistent():
    """`passed + failed + skipped == total_tests`.

    This is the same contradiction exec-plan 08's Fix 2 audit flagged in the
    writer; the guard belongs next to the artifact it describes.
    """
    assert _COMMITTED_AT_IMPORT is not None, f"{ARTIFACT} is missing or unreadable"

    summary = _COMMITTED_AT_IMPORT.get("_test_summary")
    assert summary is not None, f"{ARTIFACT.name} carries no _test_summary"

    counted = summary["passed"] + summary["failed"] + summary["skipped"]
    assert counted == summary["total_tests"], (
        f"{counted} != {summary['total_tests']}: the committed counts contradict "
        "each other"
    )
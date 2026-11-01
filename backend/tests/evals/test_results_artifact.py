"""Focused integrity tests for current-session evaluation artifacts.

The tracked ``results.json`` is historical evidence.  These tests exercise the
fresh output contract without writing it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import conftest
from .conftest import EvalResultsPlugin, _artifact_payload, save_eval_results


HISTORICAL_ARTIFACT = Path(__file__).resolve().parent / "results.json"


class _StubItem:
    def __init__(self, nodeid, fspath):
        self.nodeid = nodeid
        self.fspath = fspath


class _StubSession:
    def __init__(self, items):
        self.items = items


class _StubReport:
    def __init__(self, nodeid, when="call", outcome="passed", message=""):
        self.nodeid = nodeid
        self.when = when
        self.outcome = outcome
        self.duration = 0.0
        self.skipped = outcome == "skipped"
        self.longrepr = message


def _eval_session(tmp_path, names=("alpha", "beta")):
    fspath = tmp_path / "evals" / "test_example.py"
    fspath.parent.mkdir()
    fspath.write_text("def test_example(): pass\n", encoding="utf-8")
    items = [_StubItem(f"evals/test_example.py::test_{name}", str(fspath)) for name in names]
    return _StubSession(items)


def _finish(artifact, session, reports, *, session_results=None):
    plugin = EvalResultsPlugin(
        results_path=artifact,
        session_results={} if session_results is None else session_results,
    )
    plugin.pytest_collection_finish(session)
    for report in reports:
        if report.when == "call":
            plugin.pytest_runtest_logreport(_StubReport(report.nodeid, "setup"))
        plugin.pytest_runtest_logreport(report)
        if report.when == "call" and report.outcome == "passed":
            plugin.pytest_runtest_logreport(_StubReport(report.nodeid, "teardown"))
    plugin.pytest_sessionfinish(session, 0)
    return json.loads(artifact.read_text(encoding="utf-8"))


def test_current_session_does_not_fallback_to_historical_metrics(tmp_path, monkeypatch):
    """Missing producers stay missing, even when historical bytes are present."""
    historical = {"old_metric": 0.99, "_test_summary": {"passed": 99}}
    monkeypatch.setattr(conftest, "_SESSION_RESULTS", {})
    monkeypatch.setattr(conftest, "_SESSION_PROVENANCE", {})
    monkeypatch.setattr(conftest, "_SESSION_PRODUCERS", {})
    monkeypatch.setattr(conftest, "_SESSION_ID", "current-session")
    historical_path = tmp_path / "historical.json"
    historical_path.write_text(json.dumps(historical), encoding="utf-8")

    artifact = tmp_path / "fresh" / "results.json"
    written = _finish(
        artifact,
        _eval_session(tmp_path, ("only",)),
        [_StubReport("evals/test_example.py::test_only")],
    )

    assert "old_metric" not in written
    assert written["scope"] == "current_session"
    assert written["freshness"] == "session_only"
    assert written["session_id"] == "current-session"
    assert written["status"] == "partial"
    assert written["_test_summary"]["selected_tests_status"] == "complete"
    assert conftest.recorded_eval_results() == {}


def test_save_results_never_merges_existing_output(tmp_path, monkeypatch):
    """A stale output file cannot inject metrics into the new session."""
    monkeypatch.setattr(conftest, "_SESSION_RESULTS", {})
    monkeypatch.setattr(conftest, "_SESSION_PROVENANCE", {})
    monkeypatch.setattr(conftest, "_SESSION_PRODUCERS", {})
    output = tmp_path / "results.json"
    output.write_text(json.dumps({"stale_metric": 0.75}), encoding="utf-8")

    save_eval_results({"fresh_metric": 0.25}, output, producer_id="test_fresh")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["fresh_metric"] == 0.25
    assert "stale_metric" not in payload
    assert payload["metric_provenance"]["fresh_metric"]["producer_test_id"] == "test_fresh"


def test_arbitrary_output_directory_is_supported(tmp_path, monkeypatch):
    """The explicit output option works outside the eval source directory."""
    monkeypatch.setattr(conftest, "_SESSION_RESULTS", {})
    monkeypatch.setattr(conftest, "_SESSION_PROVENANCE", {})
    monkeypatch.setattr(conftest, "_SESSION_PRODUCERS", {})
    output = tmp_path / "arbitrary" / "nested" / "artifact.json"
    save_eval_results(
        {"offline_metric": 1.0},
        output,
        measurement_class="offline_heuristic",
        dataset_fixture="fixture:small-v1",
        producer_id="evals/test_example.py::test_offline",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["metrics"] == {"offline_metric": 1.0}
    assert payload["producers"][0]["dataset_fixture"] == "fixture:small-v1"
    assert payload["producers"][0]["measurement_class"] == "offline_heuristic"
    assert payload["producers"][0]["test_file_sha256"] is None


def test_tracked_historical_artifact_is_read_only(tmp_path):
    """No test helper can overwrite the committed historical artifact."""
    before = HISTORICAL_ARTIFACT.read_bytes()
    with pytest.raises(ValueError, match="historical and read-only"):
        conftest._write_json(HISTORICAL_ARTIFACT, _artifact_payload({"x": 1}))
    assert HISTORICAL_ARTIFACT.read_bytes() == before


def test_setup_and_teardown_errors_are_accounted(tmp_path):
    session = _eval_session(tmp_path, ("setup_error", "teardown_error", "skipped"))
    reports = [
        _StubReport(session.items[0].nodeid, "setup", "failed", "fixture failed"),
        _StubReport(session.items[1].nodeid, "setup", "passed"),
        _StubReport(session.items[1].nodeid, "call", "passed"),
        _StubReport(session.items[1].nodeid, "teardown", "failed", "cleanup failed"),
        _StubReport(session.items[2].nodeid, "setup", "skipped", "not selected"),
    ]
    payload = _finish(tmp_path / "out.json", session, reports)
    summary = payload["_test_summary"]

    assert payload["status"] == "failed"
    assert summary["failed"] == 2
    assert summary["skipped"] == 1
    assert summary["setup_errors"] == 1
    assert summary["teardown_errors"] == 1
    assert summary["errors"] == 2
    assert len(payload["errors"]) == 2


def test_producer_scoped_artifact_has_no_unrun_metric(tmp_path):
    session = _eval_session(tmp_path, ("producer", "excluded"))
    payload = _finish(
        tmp_path / "scoped.json",
        session,
        [_StubReport(session.items[0].nodeid)],
        session_results={"producer_metric": 0.5},
    )
    assert payload["metrics"] == {"producer_metric": 0.5}
    assert "excluded_metric" not in payload
    assert payload["_test_summary"]["not_run"] == 1
    assert payload["status"] == "partial"


def test_sessionfinish_discards_old_output_and_funcargs(tmp_path):
    output = tmp_path / "stale.json"
    output.write_text('{"old_metric": 0.99}', encoding="utf-8")
    session = _eval_session(tmp_path, ("only",))
    session.items[0].funcargs = {"eval_results_path": output}
    written = _finish(output, session, [_StubReport(session.items[0].nodeid)])
    assert written["metrics"] == {}
    assert "old_metric" not in written


def test_recorded_results_never_reads_a_disk_fallback(monkeypatch):
    monkeypatch.setattr(conftest, "_SESSION_RESULTS", {})
    def forbidden_read(*args, **kwargs):
        pytest.fail("Current-session results must not read historical files")
    monkeypatch.setattr(conftest, "_read_json_dict", forbidden_read)
    assert conftest.recorded_eval_results() == {}


def test_failed_or_unfinished_producer_cannot_satisfy_consumers(tmp_path, monkeypatch):
    monkeypatch.setattr(conftest, "_SESSION_RESULTS", {"metric": 0.75})
    monkeypatch.setattr(conftest, "_SESSION_PROVENANCE", {"metric": {"producer_test_id": "producer"}})
    monkeypatch.setattr(conftest, "_SESSION_OUTCOMES", {})
    plugin = EvalResultsPlugin(tmp_path / "out.json")
    plugin.pytest_runtest_logreport(_StubReport("producer", "setup"))
    plugin.pytest_runtest_logreport(_StubReport("producer"))
    assert conftest.recorded_eval_results() == {}
    plugin.pytest_runtest_logreport(_StubReport("producer", "teardown", "failed"))
    assert conftest.recorded_eval_results() == {}
    plugin.pytest_runtest_logreport(_StubReport("successful", "setup"))
    plugin.pytest_runtest_logreport(_StubReport("successful"))
    plugin.pytest_runtest_logreport(_StubReport("successful", "teardown"))
    conftest._SESSION_PROVENANCE["metric"]["producer_test_id"] = "successful"
    assert conftest.recorded_eval_results() == {"metric": 0.75}


def test_option_and_direct_save_refuse_historical_output(monkeypatch):
    from types import SimpleNamespace
    before = HISTORICAL_ARTIFACT.read_bytes()
    config = SimpleNamespace(getoption=lambda name: str(HISTORICAL_ARTIFACT))
    with pytest.raises(ValueError, match="historical and read-only"):
        conftest.results_path_for_config(config)
    with pytest.raises(ValueError, match="historical and read-only"):
        save_eval_results({"test_only": 1}, HISTORICAL_ARTIFACT, producer_id="test_only")
    assert HISTORICAL_ARTIFACT.read_bytes() == before


def test_fixture_and_plugin_share_configured_output(request, eval_results_path):
    plugin = request.config.pluginmanager.getplugin("eval_results")
    assert eval_results_path == plugin.results_path
    assert eval_results_path == conftest.results_path_for_config(request.config)
    assert eval_results_path != HISTORICAL_ARTIFACT


def test_collection_error_without_items_writes_failed_artifact(tmp_path):
    from types import SimpleNamespace
    output = tmp_path / "out.json"
    plugin = EvalResultsPlugin(output, session_results={})
    plugin.pytest_collectreport(SimpleNamespace(
        nodeid="tests/evals/test_broken.py", failed=True,
    ))
    plugin.pytest_sessionfinish(_StubSession([]), 2)
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["status"] == "failed"
    assert written["metrics"] == {}
    assert written["_test_summary"]["collection_errors"] == 1


def test_incomplete_phase_reports_remain_partial(tmp_path):
    session = _eval_session(tmp_path, ("interrupted",))
    plugin = EvalResultsPlugin(tmp_path / "out.json", session_results={})
    plugin.pytest_runtest_logreport(_StubReport(session.items[0].nodeid))
    plugin.pytest_sessionfinish(session, 2)
    assert plugin.results["status"] == "partial"
    assert plugin.results["_test_summary"]["not_run"] == 1


def test_historical_artifact_rates_are_valid_historical_bytes_only():
    historical = json.loads(HISTORICAL_ARTIFACT.read_text(encoding="utf-8"))
    for key in conftest.REQUIRED_METRICS:
        value = historical[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert 0 <= value <= 1
    summary = historical["_test_summary"]
    assert summary["total_tests"] == summary["passed"] + summary["failed"] + summary["skipped"]

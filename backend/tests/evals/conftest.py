"""Offline eval fixtures and current-session artifact collection.

The tracked results.json is historical only. No writer reads or merges it.
Application imports are lazy so artifact regressions need only pytest.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ARTIFACT_SCHEMA_VERSION = 2
HISTORICAL_ARTIFACT = Path(__file__).resolve().with_name("results.json")
# .pytest*/ is already ignored. The old .pytest_cache can be inaccessible locally.
DEFAULT_RESULTS_PATH = Path(__file__).resolve().parents[2] / ".pytest_eval_results" / "results.json"
REQUIRED_METRICS = (
    "diversity_rate", "stereotype_rate", "essentialism_rate",
    "path_divergence_rate", "assumption_isolation_rate", "truth_contract_pass_rate",
)
_SESSION_RESULTS: dict = {}
_SESSION_PROVENANCE: dict = {}
_SESSION_PRODUCERS: dict = {}
_SESSION_OUTCOMES: dict = {}
_SESSION_SELECTED_TESTS: list = []
_SESSION_ID = None
_SESSION_STARTED_AT = None
_SESSION_OUTPUT_PATH = None
_CURRENT_TEST_ID = None
_CURRENT_TEST_FILE_HASH = None


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _reset_session_state():
    global _SESSION_ID, _SESSION_STARTED_AT, _SESSION_OUTPUT_PATH
    global _CURRENT_TEST_ID, _CURRENT_TEST_FILE_HASH
    for state in (_SESSION_RESULTS, _SESSION_PROVENANCE, _SESSION_PRODUCERS, _SESSION_OUTCOMES):
        state.clear()
    _SESSION_SELECTED_TESTS.clear()
    _SESSION_ID = uuid.uuid4().hex
    _SESSION_STARTED_AT = _utc_now()
    _SESSION_OUTPUT_PATH = None
    _CURRENT_TEST_ID = None
    _CURRENT_TEST_FILE_HASH = None


def _is_eval_path(path):
    return "evals" in str(path).replace("\\", "/").split("/")


def _check_output_path(path):
    path = Path(path).expanduser().resolve()
    if path == HISTORICAL_ARTIFACT or (
        path.exists() and HISTORICAL_ARTIFACT.exists()
        and os.path.samefile(path, HISTORICAL_ARTIFACT)
    ):
        raise ValueError("The tracked eval results.json is historical and read-only")
    return path


def results_path_for_config(config=None):
    configured = config.getoption("--eval-results") if config is not None else None
    return _check_output_path(configured or DEFAULT_RESULTS_PATH)


def _read_json_dict(path):
    """Only for explicit historical-file inspection, never current metrics."""
    try:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def recorded_eval_results():
    """Only current metrics whose producer passed setup, call AND teardown.

    Producers assert their local measurements directly. An unfinished or failed
    producer cannot satisfy a later consumer; missing metrics remain absent.
    """
    return deepcopy({
        key: value for key, value in _SESSION_RESULTS.items()
        if _SESSION_OUTCOMES.get(
            _SESSION_PROVENANCE.get(key, {}).get("producer_test_id")
        ) == "passed"
    })


@pytest.fixture
def recorded_results():
    return recorded_eval_results()


def _artifact_payload(metrics, *, selected_tests=None, summary=None, status="partial",
                      finished_at=None, provenance=None, producers=None, errors=None):
    global _SESSION_ID, _SESSION_STARTED_AT
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        _SESSION_STARTED_AT = _utc_now()
    return {
        **deepcopy(metrics),
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "scope": "current_session",
        "freshness": "session_only",
        "session_id": _SESSION_ID,
        "started_at": _SESSION_STARTED_AT,
        "finished_at": finished_at,
        "status": status,
        "selected_tests": list(selected_tests or []),
        "metrics": deepcopy(metrics),
        "metric_provenance": deepcopy(provenance or {}),
        "producers": deepcopy(producers or []),
        "errors": deepcopy(errors or []),
        "_test_summary": summary,
    }


def _write_json(path, payload):
    path = _check_output_path(path)
    # Serialize before touching the output. Never persist non-JSON/NaN metrics.
    contents = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_eval_results(results, results_path=None, *, measurement_class="offline_heuristic",
                      dataset_fixture=None, producer_id=None):
    """Save only in-memory session measurements, never read output as input.

    The fixture identifier digest hashes the ID, not dataset contents. The
    separate test-file SHA-256 fingerprints the inline fixture recipe.
    """
    if not isinstance(results, dict):
        raise TypeError("evaluation results must be a JSON object")
    if any(not isinstance(key, str) for key in results):
        raise ValueError("metric keys must be strings")
    reserved = set(_artifact_payload({}))
    if reserved.intersection(results):
        raise ValueError("metrics must not overwrite artifact metadata")
    json.dumps(results, allow_nan=False)
    output = _check_output_path(results_path or _SESSION_OUTPUT_PATH or DEFAULT_RESULTS_PATH)
    test_id = producer_id or _CURRENT_TEST_ID
    if not test_id:
        raise ValueError("metrics require a producer test identifier")
    fixture_id = dataset_fixture or f"inline-fixtures:{test_id}"
    file_hash = _CURRENT_TEST_FILE_HASH if test_id == _CURRENT_TEST_ID else _sha256_file(
        test_id.split("::", 1)[0]
    )
    details = {
        "producer_test_id": test_id,
        "measurement_class": measurement_class,
        "dataset_fixture": fixture_id,
        "dataset_fixture_id_sha256": hashlib.sha256(fixture_id.encode("utf-8")).hexdigest(),
        "test_file_sha256": file_hash,
    }
    for key in results:
        previous = _SESSION_PROVENANCE.get(key)
        if previous and previous["producer_test_id"] != test_id:
            raise ValueError(f"metric {key} already belongs to another producer")
    _SESSION_RESULTS.update(deepcopy(results))
    for key in results:
        _SESSION_PROVENANCE[key] = dict(details)
    keys = set(_SESSION_PRODUCERS.get(test_id, {}).get("metric_keys", [])) | set(results)
    _SESSION_PRODUCERS[test_id] = {**details, "test_id": test_id, "metric_keys": sorted(keys)}
    _write_json(output, _artifact_payload(
        _SESSION_RESULTS, selected_tests=_SESSION_SELECTED_TESTS,
        provenance=_SESSION_PROVENANCE, producers=list(_SESSION_PRODUCERS.values()),
    ))


@pytest.fixture
def app():
    from app import create_app

    application = create_app()
    application.config.update({"TESTING": True})
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def profile_generator(monkeypatch):
    from app.services.oasis_profile_generator import OasisProfileGenerator

    monkeypatch.setenv("LLM_API_KEY", "test-eval-mock-key-32characterslong!")
    return OasisProfileGenerator(api_key="test-eval-mock-key-32characterslong!")


@pytest.fixture
def sample_entity():
    from app.services.zep_entity_reader import EntityNode

    return EntityNode(
        uuid="test-uuid-001", name="Alex Chen", labels=["Person", "Student"],
        summary="A computer science student interested in AI and ethics",
        attributes={"occupation": "Student", "institution": "Test University"},
        related_edges=[{
            "fact": "Alex Chen studies at Test University",
            "edge_name": "studies_at", "direction": "outgoing",
        }],
        related_nodes=[{
            "name": "Test University", "labels": ["University"],
            "summary": "A research university",
        }],
    )


@pytest.fixture
def sample_decision_prompt():
    return "Should universities implement stricter AI ethics guidelines for student research projects?"


@pytest.fixture
def eval_results_path(request):
    """Exactly the path used by the registered session plugin; no teardown I/O."""
    return request.config.pluginmanager.getplugin("eval_results").results_path


class EvalResultsPlugin:
    def __init__(self, results_path=None, session_results=None):
        self.results_path = _check_output_path(results_path or DEFAULT_RESULTS_PATH)
        # Explicit dictionaries isolate harness tests from real session evidence.
        self.session_results = session_results
        self.results = {}
        self.test_phases = {}
        self.selected_tests = []
        self.test_file_hashes = {}
        self.collection_errors = []

    def pytest_collection_finish(self, session):
        # Runs after deselection/reordering plugins. Only actual selection is recorded.
        selected = [item for item in session.items if _is_eval_path(item.fspath)]
        self.selected_tests = [item.nodeid for item in selected]
        self.test_file_hashes = {item.nodeid: _sha256_file(item.fspath) for item in selected}
        if self.session_results is None:
            _SESSION_SELECTED_TESTS[:] = self.selected_tests

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item):
        global _CURRENT_TEST_ID, _CURRENT_TEST_FILE_HASH
        if self.session_results is None:
            _CURRENT_TEST_ID = item.nodeid
            _CURRENT_TEST_FILE_HASH = self.test_file_hashes.get(item.nodeid)

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_runtest_teardown(self, item, nextitem):
        global _CURRENT_TEST_ID, _CURRENT_TEST_FILE_HASH
        yield
        if self.session_results is None:
            _CURRENT_TEST_ID = None
            _CURRENT_TEST_FILE_HASH = None

    def pytest_collectreport(self, report):
        if report.failed and _is_eval_path(report.nodeid.split("::", 1)[0]):
            # Do not retain raw exception messages, locals, credentials or source data.
            self.collection_errors.append({"test_id": report.nodeid, "phase": "collection"})

    @staticmethod
    def _outcome(phases):
        outcomes = {phase: data["outcome"] for phase, data in phases.items()}
        if "failed" in outcomes.values():
            return "failed"
        if "skipped" in outcomes.values():
            return "skipped"
        if all(outcomes.get(phase) == "passed" for phase in ("setup", "call", "teardown")):
            return "passed"
        return "not_run"

    def pytest_runtest_logreport(self, report):
        phases = self.test_phases.setdefault(report.nodeid, {})
        phases[report.when] = {
            "outcome": report.outcome, "duration": getattr(report, "duration", 0.0),
        }
        if self.session_results is None:
            _SESSION_OUTCOMES[report.nodeid] = self._outcome(phases)

    def pytest_sessionfinish(self, session, exitstatus):
        selected = [item for item in session.items if _is_eval_path(item.fspath)]
        outcomes = {item.nodeid: self._outcome(self.test_phases.get(item.nodeid, {}))
                    for item in selected}
        errors = list(self.collection_errors)
        for test_id in outcomes:
            errors.extend({"test_id": test_id, "phase": phase}
                          for phase, data in self.test_phases.get(test_id, {}).items()
                          if data["outcome"] == "failed")
        summary = {
            "total_tests": len(outcomes),
            **{name: list(outcomes.values()).count(name)
               for name in ("passed", "failed", "skipped", "not_run")},
            "setup_errors": sum(error["phase"] == "setup" for error in errors),
            "teardown_errors": sum(error["phase"] == "teardown" for error in errors),
            "collection_errors": len(self.collection_errors),
            "errors": len(errors),
            "exit_status": 1 if errors else 0,
            "session_exit_status": int(exitstatus),
        }
        selected_status = (
            "failed" if errors else "partial"
            if not selected or summary["not_run"] or summary["skipped"]
            or int(exitstatus) in (2, 3, 4, 5) else "complete"
        )
        live = self.session_results is None
        metrics = deepcopy(_SESSION_RESULTS if live else self.session_results)
        provenance = {key: {**value, "producer_outcome": outcomes.get(value["producer_test_id"], "not_run")}
                      for key, value in _SESSION_PROVENANCE.items()} if live else {}
        producers = [{**value, "outcome": outcomes.get(value["test_id"], "not_run")}
                     for value in _SESSION_PRODUCERS.values()] if live else []
        verified = {key for key, value in provenance.items() if value["producer_outcome"] == "passed"}
        # Explicit session_results is a unit-test seam, never a production source.
        if not live:
            verified = set(metrics)
        missing = sorted(set(REQUIRED_METRICS) - verified)
        summary.update(selected_tests_status=selected_status, missing_required_metrics=missing)
        status = "partial" if selected_status == "complete" and missing else selected_status
        self.results = _artifact_payload(
            metrics, selected_tests=list(outcomes), summary=summary, status=status,
            finished_at=_utc_now(), provenance=provenance, producers=producers, errors=errors,
        )
        try:
            _write_json(self.results_path, self.results)
        except OSError as exc:
            session.exitstatus = pytest.ExitCode.INTERNAL_ERROR
            raise pytest.UsageError(f"Could not write eval artifact: {exc}") from exc
        print(f"\nEvaluation results saved to: {self.results_path} (status={status})")


def pytest_addoption(parser):
    parser.addoption("--eval-results", action="store", default=None, metavar="PATH",
                     help=f"Current-session eval output (default: {DEFAULT_RESULTS_PATH})")


def pytest_configure(config):
    config.addinivalue_line("markers", "eval: mark test as an evaluation suite test")
    if config.pluginmanager.hasplugin("eval_results"):
        return
    _reset_session_state()
    global _SESSION_OUTPUT_PATH
    try:
        _SESSION_OUTPUT_PATH = results_path_for_config(config)
        # Invalidate old output even if collection fails or selects no tests.
        _write_json(_SESSION_OUTPUT_PATH, _artifact_payload({}))
    except (ValueError, OSError) as exc:
        raise pytest.UsageError(str(exc)) from exc
    config.pluginmanager.register(EvalResultsPlugin(_SESSION_OUTPUT_PATH), "eval_results")

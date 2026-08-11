import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from app.services.runtime_control_store import RuntimeControlStore
from app.services.simulation_manager import SimulationStatus
from app.services.simulation_runner import RunnerStatus


def _store(tmp_path, attempt_id="attempt-current", fencing_token=7):
    return RuntimeControlStore(
        str(tmp_path),
        attempt_id=attempt_id,
        fencing_token=fencing_token,
    )


def test_read_only_store_does_not_create_runtime_control_artifacts(tmp_path):
    simulation_dir = tmp_path / "sim-read-only"
    control_root = simulation_dir / "runtime_controls"

    store = RuntimeControlStore(str(simulation_dir))
    assert store.get_status("00000000-0000-4000-8000-000000000001") is None
    assert store.get_platform_states() == {}
    assert store.list_receipts() == []
    assert (
        store.find_completed_control(
            "stop",
            attempt_id="attempt-current",
            fencing_token=7,
        )
        is None
    )

    assert not control_root.exists()


def test_store_reopens_and_aggregates_independent_platform_receipts(tmp_path):
    args = {"content": "A durable intervention", "nested": {"weight": 1}}
    queued = _store(tmp_path).enqueue(
        "inject_post",
        args,
        ["twitter", "reddit", "twitter"],
    )
    args["nested"]["weight"] = 99

    reopened = _store(tmp_path)
    status = reopened.get_status(queued["control_id"])
    assert status["status"] == "queued"
    assert status["platforms"] == ["twitter", "reddit"]
    assert status["platform_statuses"] == {
        "twitter": {"status": "queued"},
        "reddit": {"status": "queued"},
    }

    twitter = reopened.claim_next("twitter")
    reddit = reopened.claim_next("reddit")
    assert twitter["args"]["nested"]["weight"] == 1
    assert reddit["control_id"] == twitter["control_id"]
    assert reopened.claim_next("twitter") is None

    reopened.complete("twitter", twitter, {"applied_count": 1})
    partial = _store(tmp_path).get_status(queued["control_id"])
    assert partial["status"] == "processing"
    assert partial["platform_statuses"]["twitter"]["status"] == "completed"
    assert partial["platform_statuses"]["reddit"]["status"] == "processing"

    reopened.complete("reddit", reddit, {"applied_count": 1})
    completed = _store(tmp_path).get_status(queued["control_id"])
    assert completed["status"] == "completed"
    assert completed["result"] == {
        "twitter": {"applied_count": 1},
        "reddit": {"applied_count": 1},
    }


def test_processing_command_is_not_replayed_after_owner_failure(tmp_path):
    store = _store(tmp_path)
    control = store.enqueue("stop", {}, ["twitter"])
    claimed = store.claim_next("twitter")

    assert claimed["control_id"] == control["control_id"]
    assert _store(tmp_path).claim_next("twitter") is None
    assert (
        tmp_path
        / "runtime_controls"
        / "processing"
        / "twitter"
        / f"{control['control_id']}.json"
    ).exists()


def test_claim_is_atomic_across_store_instances(tmp_path):
    store = _store(tmp_path)
    control = store.enqueue("pause_after_round", {}, ["twitter"])

    def claim_once():
        claimed = _store(tmp_path).claim_next("twitter")
        return claimed and claimed["control_id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed_ids = list(pool.map(lambda _: claim_once(), range(2)))

    assert sorted(value for value in claimed_ids if value) == [control["control_id"]]


def test_claim_is_atomic_across_processes(tmp_path):
    store = _store(tmp_path)
    control = store.enqueue("resume", {}, ["reddit"])
    script = (
        "import sys; "
        "from app.services.runtime_control_store import RuntimeControlStore; "
        "item=RuntimeControlStore(sys.argv[1], attempt_id='attempt-current', fencing_token=7).claim_next('reddit'); "
        "print(item['control_id'] if item else '')"
    )
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(tmp_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    outputs = []
    for worker in workers:
        stdout, stderr = worker.communicate(timeout=20)
        assert worker.returncode == 0, stderr
        outputs.append(stdout.strip())

    assert sorted(value for value in outputs if value) == [control["control_id"]]


def test_failed_receipt_and_platform_state_survive_reopen(tmp_path):
    store = _store(tmp_path)
    control = store.enqueue("inject_event", {"event_type": "topic_spike"}, ["reddit"])
    command = store.claim_next("reddit")
    store.write_platform_state("reddit", {"status": "paused", "round_num": 4})
    store.fail("reddit", command, "invalid target")

    reopened = _store(tmp_path)
    status = reopened.get_status(control["control_id"])
    assert status["status"] == "failed"
    assert status["errors"] == {"reddit": "invalid target"}
    assert reopened.get_platform_states()["reddit"]["status"] == "paused"


@pytest.mark.parametrize(
    ("command_type", "platforms"),
    [("unknown", ["twitter"]), ("stop", []), ("stop", ["mastodon"])],
)
def test_store_rejects_unsupported_contract_values(tmp_path, command_type, platforms):
    with pytest.raises(ValueError):
        _store(tmp_path).enqueue(command_type, {}, platforms)


def test_manifest_is_commit_point_and_partial_copy_is_never_claimed(tmp_path):
    pending = tmp_path / "runtime_controls" / "pending" / "twitter"
    pending.mkdir(parents=True)
    control_id = "00000000-0000-4000-8000-000000000001"
    (pending / f"{control_id}.json").write_text(
        json.dumps(
            {
                "control_id": control_id,
                "command_type": "stop",
                "args": {},
                "platform": "twitter",
                "platforms": ["twitter", "reddit"],
                "attempt_id": "attempt-current",
                "fencing_token": 7,
            }
        ),
        encoding="utf-8",
    )

    assert _store(tmp_path).claim_next("twitter") is None
    assert (pending / f"{control_id}.json").exists()


def test_stale_attempt_cannot_claim_current_attempt_command(tmp_path):
    queued = _store(tmp_path).enqueue("stop", {}, ["twitter"])

    assert _store(tmp_path, "attempt-new", 8).claim_next("twitter") is None
    claimed = _store(tmp_path).claim_next("twitter")
    assert claimed["control_id"] == queued["control_id"]
    assert claimed["attempt_id"] == "attempt-current"
    assert claimed["fencing_token"] == 7


def test_idempotency_key_reuses_same_current_attempt_control(tmp_path):
    store = _store(tmp_path)
    first = store.enqueue(
        "stop",
        {},
        ["twitter", "reddit"],
        idempotency_key="stop-attempt-current",
    )
    second = store.enqueue(
        "stop",
        {},
        ["twitter", "reddit"],
        idempotency_key="stop-attempt-current",
    )

    assert second["control_id"] == first["control_id"]
    assert len(list((tmp_path / "runtime_controls" / "manifests").glob("*.json"))) == 1


def test_same_idempotency_key_cannot_replace_different_manifest(tmp_path):
    store = _store(tmp_path)
    first = store.enqueue(
        "inject_post",
        {"content": "first"},
        ["twitter"],
        idempotency_key="same-key",
    )

    with pytest.raises(ValueError, match="idempotency_key_conflict"):
        store.enqueue(
            "inject_post",
            {"content": "different"},
            ["twitter"],
            idempotency_key="same-key",
        )

    manifest = json.loads(
        (
            tmp_path
            / "runtime_controls"
            / "manifests"
            / f"{first['control_id']}.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["args"] == {"content": "first"}


def test_concurrent_conflicting_idempotency_fingerprints_never_replace_manifest(
    tmp_path,
):
    script = (
        "import sys; "
        "from app.services.runtime_control_store import RuntimeControlStore; "
        "store=RuntimeControlStore(sys.argv[1], attempt_id='attempt-current', fencing_token=7); "
        "store.enqueue('inject_post', {'content': sys.argv[2]}, ['twitter'], idempotency_key='same-key')"
    )
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(tmp_path), content],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for content in ("first", "second")
    ]
    results = [worker.communicate(timeout=15) for worker in workers]
    return_codes = sorted(worker.returncode for worker in workers)

    assert return_codes == [0, 1], results
    manifests = list(_store(tmp_path).manifests_dir.glob("*.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["args"]["content"] in {"first", "second"}


def test_receipt_publication_is_no_overwrite_atomic(tmp_path):
    store = _store(tmp_path)
    queued = store.enqueue("inject_post", {"content": "notice"}, ["twitter"])
    command = store.claim_next("twitter")

    with ThreadPoolExecutor(max_workers=2) as pool:
        returned = list(
            pool.map(
                lambda value: store.complete("twitter", command, {"winner": value}),
                ["a", "b"],
            )
        )

    persisted = store.get_status(queued["control_id"])["result"]["twitter"]
    assert persisted in ({"winner": "a"}, {"winner": "b"})
    assert all(receipt["result"] == persisted for receipt in returned)


def test_claim_order_uses_persisted_sequence_not_mutable_mtime(tmp_path):
    store = _store(tmp_path)
    first = store.enqueue("resume", {}, ["twitter"])
    second = store.enqueue("resume", {}, ["twitter"])
    first_path = (
        tmp_path / "runtime_controls" / "pending" / "twitter" / f"{first['control_id']}.json"
    )
    second_path = (
        tmp_path / "runtime_controls" / "pending" / "twitter" / f"{second['control_id']}.json"
    )
    os.utime(first_path, (2_000_000_000, 2_000_000_000))
    os.utime(second_path, (1_000_000_000, 1_000_000_000))

    assert store.claim_next("twitter")["control_id"] == first["control_id"]


def test_process_crash_leaves_diagnostic_processing_copy_without_replay(tmp_path):
    control = _store(tmp_path).enqueue("stop", {}, ["twitter"])
    script = (
        "import os,sys; "
        "from app.services.runtime_control_store import RuntimeControlStore; "
        "item=RuntimeControlStore(sys.argv[1], attempt_id='attempt-current', fencing_token=7).claim_next('twitter'); "
        "os._exit(0 if item else 3)"
    )
    worker = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert worker.returncode == 0, worker.stderr
    assert _store(tmp_path).claim_next("twitter") is None
    assert (
        tmp_path
        / "runtime_controls"
        / "processing"
        / "twitter"
        / f"{control['control_id']}.json"
    ).exists()


@pytest.fixture
def control_client(monkeypatch, tmp_path):
    from app import create_app
    from app.config import Config

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    simulation_dir = tmp_path / "sim-control"
    simulation_dir.mkdir()
    (simulation_dir / "state.json").write_text("{}", encoding="utf-8")

    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _patch_active_run(monkeypatch, *, twitter=True, reddit=True, status=RunnerStatus.RUNNING):
    from app.api.routes import execution_routes

    simulation = SimpleNamespace(
        simulation_id="sim-control",
        status=SimulationStatus.RUNNING,
        enable_twitter=twitter,
        enable_reddit=reddit,
    )
    run_state = SimpleNamespace(
        runner_status=status,
        twitter_running=twitter,
        reddit_running=reddit,
        active_platforms=[
            platform
            for platform, enabled in (("twitter", twitter), ("reddit", reddit))
            if enabled
        ],
        attempt_id="attempt-current",
        fencing_token=7,
    )
    monkeypatch.setattr(
        execution_routes.SimulationManager,
        "get_simulation",
        lambda _self, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        execution_routes.SimulationRunner,
        "get_run_state",
        lambda _simulation_id: run_state,
    )
    return simulation, run_state


def test_control_routes_enqueue_and_query_aggregate_status(control_client, monkeypatch):
    _patch_active_run(monkeypatch)

    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={"command_type": "inject_post", "args": {"content": "Notice"}},
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "queued"
    assert payload["data"]["platforms"] == ["twitter", "reddit"]

    queried = control_client.get(
        f"/api/simulation/sim-control/control/{payload['data']['control_id']}"
    )
    assert queried.status_code == 200
    assert queried.get_json()["data"]["status"] == "queued"


def test_control_route_rejects_terminal_run(control_client, monkeypatch):
    _patch_active_run(monkeypatch, status=RunnerStatus.COMPLETED)
    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={"command_type": "stop", "args": {}},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "simulation_not_active"


def test_control_request_schema_rejects_unknown_command(control_client, monkeypatch):
    _patch_active_run(monkeypatch)
    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={"command_type": "rewind", "args": {}},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {
            "command_type": "inject_event",
            "args": {"event_type": "unsupported", "payload": {}},
        },
        {
            "command_type": "inject_event",
            "args": {"event_type": "topic_spike", "payload": {}},
        },
        {"command_type": "pause_after_round", "args": {"decorative": True}},
    ],
)
def test_control_request_schema_rejects_noop_or_extra_args(
    control_client, monkeypatch, body
):
    _patch_active_run(monkeypatch)
    response = control_client.post(
        "/api/simulation/sim-control/control",
        json=body,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "event_type",
    [
        "persona_modification",
        "persona_change",
        "dynamic_instruction",
        "inject_post",
    ],
)
def test_inject_event_rejects_instruction_and_command_variants(
    control_client,
    monkeypatch,
    event_type,
):
    _patch_active_run(monkeypatch)

    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={
            "command_type": "inject_event",
            "args": {
                "event_type": event_type,
                "payload": {"content": "Untrusted event content"},
            },
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("event_type", "payload", "targeting"),
    [
        ("seed_post", {"summary": "A bounded seed update."}, {}),
        (
            "official_statement",
            {"statement": "The agency published a revised schedule."},
            {},
        ),
        (
            "media_breaking_news",
            {"summary": "Local media reported a service disruption."},
            {},
        ),
        ("topic_spike", {"topics": ["service", "commute"]}, {}),
        ("follow_wave", {}, {"source_roles": ["media"]}),
    ],
)
def test_inject_event_accepts_one_runtime_consumed_fixture_per_event(
    control_client,
    monkeypatch,
    event_type,
    payload,
    targeting,
):
    _patch_active_run(monkeypatch)

    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={
            "command_type": "inject_event",
            "args": {
                "event_type": event_type,
                "payload": payload,
                "targeting": targeting,
            },
        },
    )

    assert response.status_code == 202


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        ("seed_post", {}),
        ("seed_post", {"headline": "Ignored by seed runtime"}),
        ("official_statement", {"text": "Ignored text alias"}),
        ("media_breaking_news", {"headline": ""}),
        ("follow_wave", {"content": "Follow these accounts"}),
        ("topic_spike", {"topics": []}),
        ("topic_spike", {"topics": ["one", "two", "three", "four"]}),
        ("topic_spike", {"topics": ["x" * 201]}),
        ("seed_post", {"content": "x" * 8001}),
    ],
)
def test_inject_event_rejects_ignored_empty_or_unbounded_payloads(
    control_client,
    monkeypatch,
    event_type,
    payload,
):
    _patch_active_run(monkeypatch)

    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={
            "command_type": "inject_event",
            "args": {"event_type": event_type, "payload": payload},
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "args",
    [
        {"content": "Notice", "agent_id": "4"},
        {"content": "Notice", "agent_ids": [4, -1]},
        {"content": "Notice", "roles": ["official", ""]},
    ],
)
def test_inject_post_rejects_malformed_target_fields(
    control_client, monkeypatch, args
):
    _patch_active_run(monkeypatch)

    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={"command_type": "inject_post", "args": args},
    )

    assert response.status_code == 422


def test_legacy_stop_request_rejects_extra_fields(control_client, monkeypatch):
    _patch_active_run(monkeypatch, twitter=True, reddit=False)

    response = control_client.post(
        "/api/simulation/stop",
        json={"simulation_id": "sim-control", "force": True},
    )

    assert response.status_code == 422


def test_control_route_rejects_configured_but_inactive_platforms(
    control_client, monkeypatch
):
    simulation, run_state = _patch_active_run(monkeypatch)
    simulation.enable_twitter = True
    simulation.enable_reddit = True
    run_state.active_platforms = []
    run_state.twitter_running = False
    run_state.reddit_running = False

    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={"command_type": "stop", "args": {}},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "runtime_platform_not_active"


def test_parallel_run_rejects_partial_platform_stop(control_client, monkeypatch):
    _patch_active_run(monkeypatch, twitter=True, reddit=True)

    response = control_client.post(
        "/api/simulation/sim-control/control",
        json={
            "command_type": "stop",
            "args": {},
            "platforms": ["twitter"],
        },
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "stop_requires_all_active_platforms"


def test_stop_route_forces_attempt_scoped_idempotency_across_headers(
    control_client, monkeypatch
):
    _patch_active_run(monkeypatch, twitter=True, reddit=False)

    first = control_client.post(
        "/api/simulation/stop",
        json={"simulation_id": "sim-control"},
        headers={"Idempotency-Key": "caller-stop-one"},
    )
    second = control_client.post(
        "/api/simulation/stop",
        json={"simulation_id": "sim-control"},
        headers={"Idempotency-Key": "caller-stop-two"},
    )

    assert first.status_code == second.status_code == 202
    assert first.get_json()["data"]["control_id"] == second.get_json()["data"]["control_id"]
    assert first.headers["Location"] == second.headers["Location"]
    assert "stopped" not in first.get_data(as_text=True).lower()
    assert "applied" not in first.get_data(as_text=True).lower()


def test_stop_retry_after_terminalization_returns_existing_completed_control(
    control_client,
    monkeypatch,
    tmp_path,
):
    _patch_active_run(
        monkeypatch,
        twitter=True,
        reddit=False,
        status=RunnerStatus.STOPPED,
    )
    simulation_dir = tmp_path / "sim-control"
    store = RuntimeControlStore(
        str(simulation_dir),
        attempt_id="attempt-current",
        fencing_token=7,
    )
    control = store.enqueue(
        "stop",
        {},
        ["twitter"],
        idempotency_key="stop:attempt-current:7:twitter",
    )
    command = store.claim_next("twitter")
    store.write_platform_state(
        "twitter",
        {
            "status": "stopped",
            "decision": "stop",
            "last_control_id": control["control_id"],
        },
    )
    store.complete(
        "twitter",
        command,
        {"state": "stopped", "decision": "stop", "round_num": 4},
    )

    response = control_client.post(
        "/api/simulation/stop",
        json={"simulation_id": "sim-control"},
        headers={"Idempotency-Key": "lost-client-response-retry"},
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["data"]["control_id"] == control["control_id"]
    assert payload["data"]["status"] == "completed"
    assert response.headers["Location"].endswith(control["control_id"])
    assert len(list(store.manifests_dir.glob("*.json"))) == 1

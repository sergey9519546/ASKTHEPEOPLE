"""Truthful, privacy-safe health attestation for the Celery worker."""

from __future__ import annotations

import importlib.util
import http.client
import io
import json
import subprocess
import sys
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKER_HEALTH_SCRIPT = REPOSITORY_ROOT / "backend/scripts/worker_health.py"
REVISION = "a" * 40


def _valid_startup_environment() -> dict[str, str]:
    return {
        "ZEP_API_KEY": "zep-test-secret",
        "LLM_API_KEY": "llm-test-secret",
        "REDIS_URL": "rediss://user:redis-secret@redis.internal:6379/0",
        "BUILD_REVISION": REVISION,
    }


def _load_worker_health_module():
    spec = importlib.util.spec_from_file_location(
        "worker_health_attestation_test_module", WORKER_HEALTH_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_health_script_resolves_app_without_editable_install() -> None:
    probe = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import runpy; "
                f"module = runpy.run_path({str(WORKER_HEALTH_SCRIPT)!r}); "
                "assert callable(module['evaluate_worker_health'])"
            ),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert probe.returncode == 0, probe.stderr


def _evaluate(module, environment, *, now_epoch, process_exists):
    evaluate = getattr(module, "evaluate_worker_health", None)
    assert callable(evaluate), "worker health evaluation is not implemented"
    return evaluate(
        environment,
        now_epoch=now_epoch,
        process_exists=process_exists,
    )


def _environment(marker_path: Path) -> dict[str, str]:
    return {
        "BUILD_REVISION": REVISION,
        "WORKER_HEALTH_MARKER": str(marker_path),
        "WORKER_PARENT_PID": "4242",
        # These values must never be reflected by the health endpoint.
        "ZEP_API_KEY": "zep-secret-that-must-not-appear",
        "LLM_API_KEY": "llm-secret-that-must-not-appear",
        "REDIS_URL": "redis://user:password@private-host:6379/0",
    }


def _write_marker(
    marker_path: Path,
    *,
    heartbeat_at: float = 100.0,
    worker_pid: int = 4242,
    revision: str = REVISION,
) -> None:
    marker_path.write_text(
        json.dumps(
            {
                "schema_version": "askthepeople-worker-ready/v1",
                "worker_pid": worker_pid,
                "revision": revision,
                "heartbeat_at": heartbeat_at,
            }
        ),
        encoding="utf-8",
    )


def test_worker_health_is_unavailable_before_worker_ready_marker(tmp_path):
    module = _load_worker_health_module()
    status, payload = _evaluate(
        module,
        _environment(tmp_path / "worker-ready.json"),
        now_epoch=100.0,
        process_exists=lambda _pid: True,
    )

    assert status == 503
    assert payload == {
        "status": "unavailable",
        "service": "celery-worker",
        "revision": REVISION,
    }


def test_worker_health_is_available_only_for_fresh_matching_live_worker_marker(
    tmp_path,
):
    module = _load_worker_health_module()
    marker_path = tmp_path / "worker-ready.json"
    _write_marker(marker_path)

    status, payload = _evaluate(
        module,
        _environment(marker_path),
        now_epoch=101.0,
        process_exists=lambda pid: pid == 4242,
    )

    assert status == 200
    assert payload == {
        "status": "ok",
        "service": "celery-worker",
        "revision": REVISION,
    }
    rendered = json.dumps(payload)
    assert "zep-secret" not in rendered
    assert "llm-secret" not in rendered
    assert "private-host" not in rendered


def test_worker_health_becomes_unavailable_when_marker_is_stale(tmp_path):
    module = _load_worker_health_module()
    marker_path = tmp_path / "worker-ready.json"
    _write_marker(marker_path, heartbeat_at=80.0)

    status, _payload = _evaluate(
        module,
        _environment(marker_path),
        now_epoch=100.0,
        process_exists=lambda _pid: True,
    )

    assert status == 503


def test_worker_health_becomes_unavailable_when_worker_parent_is_absent(tmp_path):
    module = _load_worker_health_module()
    marker_path = tmp_path / "worker-ready.json"
    _write_marker(marker_path)

    status, _payload = _evaluate(
        module,
        _environment(marker_path),
        now_epoch=101.0,
        process_exists=lambda _pid: False,
    )

    assert status == 503


def test_worker_health_rejects_marker_for_another_revision_or_process(tmp_path):
    module = _load_worker_health_module()
    marker_path = tmp_path / "worker-ready.json"
    environment = _environment(marker_path)

    _write_marker(marker_path, revision="b" * 40)
    assert _evaluate(
        module,
        environment,
        now_epoch=101.0,
        process_exists=lambda _pid: True,
    )[0] == 503

    _write_marker(marker_path, worker_pid=4343)
    assert _evaluate(
        module,
        environment,
        now_epoch=101.0,
        process_exists=lambda _pid: True,
    )[0] == 503


def test_worker_health_becomes_unavailable_after_shutdown_removes_marker(tmp_path):
    module = _load_worker_health_module()
    marker_path = tmp_path / "worker-ready.json"
    environment = _environment(marker_path)
    _write_marker(marker_path)

    assert _evaluate(
        module,
        environment,
        now_epoch=101.0,
        process_exists=lambda _pid: True,
    )[0] == 200

    marker_path.unlink()
    assert _evaluate(
        module,
        environment,
        now_epoch=102.0,
        process_exists=lambda _pid: True,
    )[0] == 503


def test_worker_startup_accepts_complete_no_network_configuration(monkeypatch):
    import socket

    from app.utils import worker_startup

    validate = getattr(worker_startup, "validate_worker_configuration", None)
    assert callable(validate), "complete worker startup validation is not implemented"

    def fail_if_network_is_touched(*_args, **_kwargs):
        raise AssertionError("startup validation attempted network I/O")

    monkeypatch.setattr(socket, "create_connection", fail_if_network_is_touched)
    assert validate(_valid_startup_environment()) is None


@pytest.mark.parametrize("missing_name", ["ZEP_API_KEY", "LLM_API_KEY", "REDIS_URL"])
def test_worker_startup_fails_closed_for_required_task_configuration(missing_name):
    from app.utils import worker_startup

    validate = getattr(worker_startup, "validate_worker_configuration", None)
    assert callable(validate), "complete worker startup validation is not implemented"
    environment = _valid_startup_environment()
    del environment[missing_name]

    with pytest.raises(worker_startup.WorkerStartupConfigurationError) as raised:
        validate(environment)

    rendered = str(raised.value)
    assert missing_name in rendered
    assert "zep-test-secret" not in rendered
    assert "llm-test-secret" not in rendered
    assert "redis-secret" not in rendered


@pytest.mark.parametrize(
    ("name", "unsafe_url"),
    [
        ("REDIS_URL", "memory://"),
        ("CELERY_BROKER_URL", "memory://"),
        ("CELERY_RESULT_BACKEND", "cache+memory://"),
    ],
)
def test_worker_startup_rejects_in_memory_worker_dependencies(name, unsafe_url):
    from app.utils import worker_startup

    validate = getattr(worker_startup, "validate_worker_configuration", None)
    assert callable(validate), "complete worker startup validation is not implemented"
    environment = _valid_startup_environment()
    environment[name] = unsafe_url

    with pytest.raises(
        worker_startup.WorkerStartupConfigurationError,
        match=rf"{name} must use redis:// or rediss://",
    ):
        validate(environment)


def test_worker_startup_url_error_does_not_chain_configuration_values():
    from app.utils import worker_startup

    environment = _valid_startup_environment()
    environment["CELERY_BROKER_URL"] = "redis://user:private-value@[broken"

    with pytest.raises(worker_startup.WorkerStartupConfigurationError) as raised:
        worker_startup.validate_worker_configuration(environment)

    assert raised.value.__cause__ is None
    assert "private-value" not in str(raised.value)


@pytest.mark.parametrize("revision", ["", "unknown", "main", "abc1234"])
def test_worker_startup_requires_an_immutable_runtime_revision(revision):
    from app.utils import worker_startup

    validate = getattr(worker_startup, "validate_worker_configuration", None)
    assert callable(validate), "complete worker startup validation is not implemented"
    environment = _valid_startup_environment()
    environment["BUILD_REVISION"] = revision

    with pytest.raises(
        worker_startup.WorkerStartupConfigurationError,
        match="immutable runtime revision is required",
    ):
        validate(environment)


def test_worker_startup_rejects_a_destructive_marker_target():
    from app.utils import worker_startup

    environment = _valid_startup_environment() | {
        "WORKER_HEALTH_MARKER": "/etc/passwd",
    }

    with pytest.raises(
        worker_startup.WorkerStartupConfigurationError,
        match="WORKER_HEALTH_MARKER must use the dedicated runtime marker path",
    ):
        worker_startup.validate_worker_configuration(environment)


def test_worker_startup_rejects_runtime_revision_override_of_image(tmp_path):
    from app.utils import worker_startup

    revision_path = tmp_path / "build-revision"
    revision_path.write_text(f"{REVISION}\n", encoding="ascii")

    assert (
        worker_startup.resolve_worker_runtime_revision(
            {"BUILD_REVISION": "b" * 40},
            image_revision_path=revision_path,
        )
        == ""
    )


def test_worker_preflight_script_checks_more_than_zep_configuration():
    script_path = REPOSITORY_ROOT / "backend/scripts/check_worker_zep_config.py"
    spec = importlib.util.spec_from_file_location(
        "worker_preflight_attestation_test_module", script_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output = io.StringIO()
    result = module.main(
        {"ZEP_API_KEY": "configured-but-not-enough"},
        stderr=output,
    )

    assert result == 78
    assert "LLM_API_KEY" in output.getvalue()
    assert "configured-but-not-enough" not in output.getvalue()


def test_worker_ready_marker_is_atomic_revision_bound_and_secret_free(tmp_path):
    from app.utils import worker_startup

    publish = getattr(worker_startup, "publish_worker_ready_marker", None)
    assert callable(publish), "worker-ready marker publication is not implemented"
    marker_path = tmp_path / "worker-ready.json"
    environment = _valid_startup_environment() | {
        "WORKER_HEALTH_MARKER": str(marker_path),
    }

    publish(environment, worker_pid=4242, now_epoch=100.0)

    assert not list(tmp_path.glob("*.tmp"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker == {
        "schema_version": "askthepeople-worker-ready/v1",
        "worker_pid": 4242,
        "revision": REVISION,
        "heartbeat_at": 100.0,
    }
    rendered = marker_path.read_text(encoding="utf-8")
    assert "zep-test-secret" not in rendered
    assert "llm-test-secret" not in rendered
    assert "redis-secret" not in rendered


def test_worker_shutdown_removes_only_its_own_readiness_marker(tmp_path):
    from app.utils import worker_startup

    publish = getattr(worker_startup, "publish_worker_ready_marker", None)
    remove = getattr(worker_startup, "remove_worker_ready_marker", None)
    assert callable(publish), "worker-ready marker publication is not implemented"
    assert callable(remove), "worker-ready marker cleanup is not implemented"
    marker_path = tmp_path / "worker-ready.json"
    environment = _valid_startup_environment() | {
        "WORKER_HEALTH_MARKER": str(marker_path),
    }
    publish(environment, worker_pid=4242, now_epoch=100.0)

    assert remove(environment, worker_pid=4343) is False
    assert marker_path.is_file()
    assert remove(environment, worker_pid=4242) is True
    assert not marker_path.exists()


def test_worker_boot_validates_target_before_clearing_stale_marker(
    tmp_path, monkeypatch
):
    from app import celery_app as celery_module

    marker_path = tmp_path / "worker-ready.json"
    _write_marker(marker_path, worker_pid=9999)
    environment = _valid_startup_environment() | {
        "WORKER_HEALTH_MARKER": str(marker_path),
    }
    order: list[str] = []
    monkeypatch.setattr(
        celery_module,
        "_worker_health_environment",
        lambda: environment,
    )
    clear = getattr(celery_module, "clear_worker_ready_marker", None)
    assert callable(clear), "unconditional stale marker cleanup is not implemented"
    original_clear = clear
    monkeypatch.setattr(
        celery_module,
        "clear_worker_ready_marker",
        lambda env: (order.append("clear"), original_clear(env))[1],
    )
    monkeypatch.setattr(
        celery_module,
        "validate_worker_configuration",
        lambda _env: order.append("validate"),
    )

    celery_module._validate_worker_boot_configuration()

    assert order == ["validate", "clear"]
    assert not marker_path.exists()


def test_celery_signals_publish_refresh_and_remove_worker_attestation(monkeypatch):
    from app import celery_app as celery_module

    ready = getattr(celery_module, "_on_worker_ready", None)
    heartbeat = getattr(celery_module, "_on_worker_heartbeat", None)
    shutdown = getattr(celery_module, "_on_worker_shutdown", None)
    assert callable(ready), "Celery worker_ready integration is not implemented"
    assert callable(heartbeat), "Celery heartbeat refresh is not implemented"
    assert callable(shutdown), "Celery shutdown cleanup is not implemented"

    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(celery_module.os, "getpid", lambda: 4242)
    monkeypatch.setattr(
        celery_module,
        "_worker_health_environment",
        lambda: _valid_startup_environment(),
    )
    monkeypatch.setattr(
        celery_module,
        "publish_worker_ready_marker",
        lambda _environment, *, worker_pid: calls.append(("publish", worker_pid)),
    )
    monkeypatch.setattr(
        celery_module,
        "remove_worker_ready_marker",
        lambda _environment, *, worker_pid: calls.append(("remove", worker_pid)),
    )
    monkeypatch.setattr(celery_module, "_ready_worker_pid", None)

    heartbeat(sender=None)
    assert calls == []
    ready(sender=None)
    heartbeat(sender=None)
    shutdown(sender=None)

    assert calls == [
        ("publish", 4242),
        ("publish", 4242),
        ("remove", 4242),
    ]
    assert celery_module._ready_worker_pid is None


def test_celery_boot_preflight_uses_complete_worker_configuration(monkeypatch):
    from app import celery_app as celery_module

    validate = getattr(celery_module, "_validate_worker_boot_configuration", None)
    assert callable(validate), "complete Celery boot preflight is not implemented"
    captured: list[dict[str, object]] = []
    monkeypatch.setattr(
        celery_module,
        "validate_worker_configuration",
        lambda environment: captured.append(dict(environment)),
    )
    monkeypatch.setattr(
        celery_module,
        "_worker_health_environment",
        _valid_startup_environment,
    )
    monkeypatch.setattr(celery_module, "clear_worker_ready_marker", lambda _env: None)

    validate()

    assert captured == [_valid_startup_environment()]


def test_celery_boot_does_not_treat_config_defaults_as_deployed_dependencies(
    monkeypatch,
):
    from app import celery_app as celery_module

    required_names = (
        "ZEP_API_KEY",
        "LLM_API_KEY",
        "REDIS_URL",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
    )
    for name in required_names:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(celery_module.Config, name, "redis://default.invalid:6379/0")

    environment = celery_module._worker_health_environment()

    assert {name: environment[name] for name in required_names} == {
        name: None for name in required_names
    }


def test_worker_wrapper_binds_health_to_celery_pid_and_cleans_up():
    wrapper = (REPOSITORY_ROOT / "backend/scripts/worker_wrapper.sh").read_text(
        encoding="utf-8"
    )

    preflight = wrapper.index("check_worker_zep_config.py")
    stale_cleanup = wrapper.index('rm -f -- "$WORKER_HEALTH_MARKER"', preflight)
    celery_start = wrapper.index("celery -A app.celery_app worker")
    celery_pid = wrapper.index("CELERY_PID=$!", celery_start)
    parent_export = wrapper.index('export WORKER_PARENT_PID="$CELERY_PID"')
    health_start = wrapper.index("worker_health.py")

    assert preflight < stale_cleanup < celery_start < celery_pid
    assert celery_pid < parent_export < health_start
    assert "exec celery" not in wrapper
    assert "trap cleanup EXIT" in wrapper
    assert 'kill -TERM "$CELERY_PID"' in wrapper
    assert 'kill "$HEALTH_PID"' in wrapper
    assert 'wait "$CELERY_PID"' in wrapper


def test_worker_wrapper_logs_no_configuration_or_identity_values():
    wrapper = (REPOSITORY_ROOT / "backend/scripts/worker_wrapper.sh").read_text(
        encoding="utf-8"
    )

    echo_lines = [
        line.strip()
        for line in wrapper.splitlines()
        if line.strip().startswith(("echo ", "printf "))
    ]
    rendered = "\n".join(echo_lines)
    for sensitive_name in (
        "ZEP_API_KEY",
        "LLM_API_KEY",
        "REDIS_URL",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
        "WORKER_PARENT_PID",
    ):
        assert sensitive_name not in rendered


def test_worker_http_health_exposes_no_runtime_server_fingerprint(monkeypatch):
    module = _load_worker_health_module()
    monkeypatch.setattr(
        module,
        "evaluate_worker_health",
        lambda: (
            200,
            {
                "status": "ok",
                "service": "celery-worker",
                "revision": REVISION,
            },
        ),
    )
    server = HTTPServer(("127.0.0.1", 0), module.HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{server.server_port}/health",
            timeout=2,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
            headers = dict(response.headers.items())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload == {
        "status": "ok",
        "service": "celery-worker",
        "revision": REVISION,
    }
    assert headers["Cache-Control"] == "no-store"
    assert headers["Content-Type"] == "application/json"
    assert "Server" not in headers
    assert "Date" not in headers


@pytest.mark.parametrize("method", ["HEAD", "POST"])
def test_worker_http_health_bounds_unsupported_method_responses(method):
    module = _load_worker_health_module()
    server = HTTPServer(("127.0.0.1", 0), module.HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=2
        )
        connection.request(method, "/health")
        response = connection.getresponse()
        headers = dict(response.getheaders())
        body = response.read()
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == 501
    assert body == b""
    assert headers["Cache-Control"] == "no-store"
    assert "Server" not in headers
    assert "Date" not in headers

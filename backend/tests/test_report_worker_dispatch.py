"""Focused route-to-worker dispatch tests for report generation."""

import builtins
from types import SimpleNamespace

import pytest

from app import create_app
from app.api import report as report_api
from app.config import Config
from app.models.task import TaskIdempotencyConflict, TaskManager
from app.services.report_agent import ReportConsoleLogger, ReportManager
from app.services.zep_tools import ZepToolsService
from app.tasks import report_tasks
from app.utils.response import mark_public_safe_error


class _TaskManager:
    def __init__(self) -> None:
        self.created = []
        self.failures = []

    def create_task(self, *args, **kwargs):
        self.created.append((args, kwargs))
        return kwargs.get("task_id", "route-report-task-id")

    def fail_task(self, task_id, error, **kwargs) -> None:
        self.failures.append((task_id, error, kwargs))


class _Coordinator:
    def __init__(self) -> None:
        self.lease = SimpleNamespace(task_id=None)
        self.acquisitions = []
        self.releases = []

    def acquire(self, simulation_id, report_id):
        self.acquisitions.append((simulation_id, report_id))
        return self.lease, None

    def release(self, lease) -> None:
        self.releases.append(lease)


@pytest.fixture
def report_client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def test_route_enqueues_only_server_ids_with_explicit_celery_identity(
    report_client,
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-route-dispatch",
        project_id="project-route-dispatch",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _TaskManager()
    coordinator = _Coordinator()
    dispatches = []
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **options: dispatches.append(("apply_async", options)),
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "delay",
        lambda **payload: dispatches.append(("delay", payload)),
    )

    response = report_client.post(
        "/api/report/generate",
        json={
            "simulation_id": simulation.simulation_id,
            "user_prompt": "PRIVATE_USER_PROMPT",
            "custom_instructions": "PRIVATE_CUSTOM_INSTRUCTIONS",
            "graph_id": "payload-graph",
            "decision_text": "payload-decision",
            "simulation_requirement": "payload-requirement",
        },
    )

    assert response.status_code == 202
    body = response.get_json()
    assert dispatches == [
        (
            "apply_async",
            {
                "kwargs": {
                    "simulation_id": simulation.simulation_id,
                    "report_id": body["data"]["report_id"],
                },
                "task_id": body["data"]["task_id"],
            },
        )
    ]
    assert coordinator.lease.task_id == body["data"]["task_id"]
    assert coordinator.releases == [coordinator.lease]


def test_route_does_not_enqueue_when_idempotent_create_returns_existing_task(
    report_client,
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-route-duplicate",
        project_id="project-route-duplicate",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    existing_task = SimpleNamespace(
        task_id="existing-report-task-id",
        metadata={"report_id": "existing-report-id"},
    )

    class _ExistingTaskManager:
        def __init__(self) -> None:
            self.create_kwargs = None

        def create_task(self, **kwargs):
            self.create_kwargs = kwargs
            return existing_task.task_id

        def get_task(self, task_id):
            return existing_task if task_id == existing_task.task_id else None

    task_manager = _ExistingTaskManager()
    coordinator = _Coordinator()
    dispatches = []
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **options: dispatches.append(options),
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 202
    assert response.get_json() == {
        "success": True,
        "data": {
            "report_id": "existing-report-id",
            "task_id": "existing-report-task-id",
            "status": "pending",
            "already_queued": True,
        },
    }
    assert task_manager.create_kwargs["idempotency_key"] == (
        "report_generate:simulation-route-duplicate"
    )
    assert task_manager.create_kwargs["task_id"] != existing_task.task_id
    assert dispatches == []
    assert coordinator.releases == [coordinator.lease]


def test_route_rejects_graph_scope_mismatch_before_task_or_lease(
    report_client,
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-route-graph-mismatch",
        project_id="project-route-graph-mismatch",
        graph_id="simulation-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _TaskManager()
    coordinator = _Coordinator()
    dispatches = []
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **options: dispatches.append(options),
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": "report_graph_scope_mismatch",
    }
    assert task_manager.created == []
    assert coordinator.acquisitions == []
    assert dispatches == []


def test_dispatch_failure_fails_task_releases_lease_and_returns_sanitized_503(
    report_client,
    monkeypatch,
):
    report_client.application.config["DEBUG"] = False
    broker_canary = "PRIVATE_BROKER_RESPONSE_CANARY"
    credential_canary = "redis://user:PRIVATE_PASSWORD@broker.invalid/0"
    instruction_canary = "PRIVATE_ROUTE_INSTRUCTION_CANARY"
    simulation = SimpleNamespace(
        simulation_id="simulation-route-dispatch-failure",
        project_id="project-route-dispatch-failure",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _TaskManager()
    coordinator = _Coordinator()

    class _RecordingLogger:
        def __init__(self) -> None:
            self.records = []

        def error(self, message, *args, **_kwargs) -> None:
            self.records.append(message % args if args else message)

    recording_logger = _RecordingLogger()

    def reject_dispatch(**_options):
        raise ConnectionError(f"{broker_canary} | {credential_canary}")

    monkeypatch.setattr(report_api, "logger", recording_logger)
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        reject_dispatch,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "delay",
        reject_dispatch,
    )

    response = report_client.post(
        "/api/report/generate",
        json={
            "simulation_id": simulation.simulation_id,
            "custom_instructions": instruction_canary,
        },
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "report_dispatch_failed",
    }
    assert task_manager.failures == [
        (
            coordinator.lease.task_id,
            "report_dispatch_failed",
            {"public_error": "report_dispatch_failed"},
        )
    ]
    assert coordinator.releases == [coordinator.lease]
    observable_text = repr(
        (response.get_json(), task_manager.failures, recording_logger.records)
    )
    for sensitive_value in (
        broker_canary,
        credential_canary,
        instruction_canary,
    ):
        assert sensitive_value not in observable_text


def test_production_scrubber_rejects_forged_public_safe_marker_and_raw_detail(
    report_client,
):
    raw_canary = "PRIVATE_FORGED_PUBLIC_ERROR_DETAIL"
    app = report_client.application
    app.config["DEBUG"] = False

    @app.get("/api/_forged-report-public-error")
    def _forged_report_public_error():
        response = report_api.jsonify({
            "success": False,
            "error": raw_canary,
        })
        response._askthepeople_public_safe_error = (
            object(),
            "report_dispatch_failed",
        )
        return response, 503

    response = report_client.get("/api/_forged-report-public-error")

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "internal_server_error",
    }
    assert raw_canary not in response.get_data(as_text=True)


def test_public_safe_error_allowlist_rejects_arbitrary_code_and_wrong_status(
    report_client,
):
    raw_canary = "PRIVATE_WRONG_STATUS_DETAIL"
    app = report_client.application
    app.config["DEBUG"] = False

    with app.test_request_context():
        response = report_api.jsonify({"success": False, "error": raw_canary})
        with pytest.raises(
            ValueError,
            match="^public_safe_error_code_not_allowed$",
        ):
            mark_public_safe_error(response, "arbitrary_provider_error")

    @app.get("/api/_wrong-status-report-public-error")
    def _wrong_status_report_public_error():
        response = report_api.jsonify({
            "success": False,
            "error": raw_canary,
        })
        return mark_public_safe_error(response, "report_dispatch_failed"), 500

    response = report_client.get("/api/_wrong-status-report-public-error")

    assert response.status_code == 500
    assert response.get_json() == {
        "success": False,
        "error": "internal_server_error",
    }
    assert raw_canary not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "request_kwargs",
    [
        pytest.param(
            {"data": "{malformed-json", "content_type": "application/json"},
            id="malformed-json",
        ),
        pytest.param({"json": ["not", "an", "object"]}, id="non-object"),
    ],
)
def test_route_rejects_malformed_or_non_object_json_with_stable_400(
    report_client,
    request_kwargs,
):
    response = report_client.post("/api/report/generate", **request_kwargs)

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "report_request_invalid",
    }


@pytest.mark.parametrize(
    ("missing_resource", "expected_code"),
    [
        pytest.param(
            "simulation",
            "report_simulation_not_found",
            id="simulation",
        ),
        pytest.param("project", "report_project_not_found", id="project"),
    ],
)
def test_route_missing_server_record_uses_stable_code_before_enqueue(
    report_client,
    monkeypatch,
    missing_resource,
    expected_code,
):
    simulation_id = f"simulation-missing-{missing_resource}"
    simulation = SimpleNamespace(
        simulation_id=simulation_id,
        project_id="project-missing",
        graph_id="project-graph",
    )
    task_manager = _TaskManager()
    coordinator = _Coordinator()
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: (
            None if missing_resource == "simulation" else simulation
        ),
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: None,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation_id},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": expected_code,
    }
    assert task_manager.created == []
    assert coordinator.acquisitions == []


def test_route_missing_simulation_id_uses_stable_code(report_client):
    response = report_client.post("/api/report/generate", json={})

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "report_simulation_id_missing",
    }


def test_worker_import_failure_fails_created_task_and_releases_lease(
    report_client,
    monkeypatch,
):
    import_canary = "PRIVATE_REPORT_WORKER_IMPORT_FAILURE"
    simulation = SimpleNamespace(
        simulation_id="simulation-worker-import-failure",
        project_id="project-worker-import-failure",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _TaskManager()
    coordinator = _Coordinator()
    original_import = builtins.__import__
    import_rejected = []

    def reject_worker_import(name, globals=None, locals=None, fromlist=(), level=0):
        if (
            name == "tasks.report_tasks"
            and level == 2
            and "generate_report_task" in fromlist
        ):
            import_rejected.append(True)
            raise ImportError(import_canary)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(builtins, "__import__", reject_worker_import)

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    created_task_id = task_manager.created[0][1]["task_id"]
    assert import_rejected == [True]
    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "report_dispatch_failed",
    }
    assert task_manager.failures == [
        (
            created_task_id,
            "report_dispatch_failed",
            {"public_error": "report_dispatch_failed"},
        )
    ]
    assert coordinator.releases == [coordinator.lease]
    assert import_canary not in repr(
        (response.get_json(), task_manager.failures)
    )


def test_success_response_survives_lease_release_exception_without_raw_detail(
    report_client,
    monkeypatch,
):
    release_canary = "PRIVATE_REPORT_LEASE_RELEASE_FAILURE"
    simulation = SimpleNamespace(
        simulation_id="simulation-lease-release-failure",
        project_id="project-lease-release-failure",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _TaskManager()
    dispatches = []
    log_messages = []

    class _ReleaseFailingCoordinator(_Coordinator):
        def release(self, lease) -> None:
            self.releases.append(lease)
            raise RuntimeError(release_canary)

    class _RecordingLogger:
        def error(self, message, *args, **_kwargs) -> None:
            log_messages.append(message % args if args else message)

    coordinator = _ReleaseFailingCoordinator()
    monkeypatch.setattr(report_api, "logger", _RecordingLogger())
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **options: dispatches.append(options),
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 202
    assert len(dispatches) == 1
    assert coordinator.releases == [coordinator.lease]
    assert release_canary not in repr((response.get_json(), log_messages))


def test_task_creation_failure_releases_lease_without_traceback_or_raw_error(
    report_client,
    monkeypatch,
):
    task_store_canary = "PRIVATE_TASK_STORE_RESPONSE_CANARY"
    simulation = SimpleNamespace(
        simulation_id="simulation-route-task-store-failure",
        project_id="project-route-task-store-failure",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    coordinator = _Coordinator()

    class _FailingTaskManager:
        def create_task(self, *args, **kwargs):
            raise RuntimeError(task_store_canary)

    class _RecordingLogger:
        def __init__(self) -> None:
            self.records = []

        def error(self, message, *args, **_kwargs) -> None:
            self.records.append(message % args if args else message)

    recording_logger = _RecordingLogger()
    monkeypatch.setattr(report_api, "logger", recording_logger)
    monkeypatch.setattr(report_api, "TaskManager", _FailingTaskManager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "report_dispatch_failed",
    }
    assert coordinator.releases == [coordinator.lease]
    assert task_store_canary not in repr(
        (response.get_json(), recording_logger.records)
    )


def test_idempotency_payload_conflict_returns_stable_409_and_no_phantom_task(
    report_client,
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-idempotency-conflict",
        project_id="project-idempotency-conflict",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    coordinator = _Coordinator()

    class _ConflictTaskManager:
        def create_task(self, *_args, **_kwargs):
            raise TaskIdempotencyConflict()

        def get_task(self, _task_id):
            return None

        def fail_task(self, *_args, **_kwargs):
            raise AssertionError("conflicting candidate must not become a task")

    monkeypatch.setattr(report_api, "TaskManager", _ConflictTaskManager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": "idempotency_key_conflict",
    }
    assert coordinator.releases == [coordinator.lease]


def test_unavailable_durable_task_state_never_returns_phantom_queued_task(
    report_client,
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-post-write-audit-failure",
        project_id="project-post-write-audit-failure",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    coordinator = _Coordinator()
    real_task_manager = TaskManager()
    idempotency_key = f"report_generate:{simulation.simulation_id}"
    dispatches = []
    task_ids_before_request = set(real_task_manager._tasks)

    monkeypatch.setattr(real_task_manager, "_get_redis", lambda: None)
    monkeypatch.setattr(report_api, "TaskManager", lambda: real_task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **options: dispatches.append(options),
    )
    try:
        first = report_client.post(
            "/api/report/generate",
            json={"simulation_id": simulation.simulation_id},
        )
        second = report_client.post(
            "/api/report/generate",
            json={"simulation_id": simulation.simulation_id},
        )

        matching_tasks = [
            task
            for task in real_task_manager._tasks.values()
            if task.idempotency_key == idempotency_key
        ]
        assert first.status_code == 503
        assert second.status_code == 503
        assert first.get_json()["error"] == "report_dispatch_failed"
        assert second.get_json()["error"] == "report_dispatch_failed"
        assert all("already_queued" not in response.get_data(as_text=True) for response in (first, second))
        # Idempotent admission now fails before any process-local write when
        # Redis cannot provide the shared reservation transaction.
        assert matching_tasks == []
        assert set(real_task_manager._tasks) == task_ids_before_request
        assert dispatches == []
    finally:
        with real_task_manager._task_lock:
            for task_id in [
                task.task_id
                for task in real_task_manager._tasks.values()
                if task.idempotency_key == idempotency_key
            ]:
                real_task_manager._tasks.pop(task_id, None)


def test_report_console_endpoint_never_returns_raw_zep_exception(
    report_client,
    monkeypatch,
    tmp_path,
):
    raw_canary = "PRIVATE_ZEP_CONSOLE_PROVIDER_BODY"
    report_id = "report-zep-console-sanitization"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(
        ReportManager,
        "REPORTS_DIR",
        str(tmp_path / "reports"),
    )
    console_logger = ReportConsoleLogger(report_id)
    service = ZepToolsService.__new__(ZepToolsService)
    service.MAX_RETRIES = 1
    service.RETRY_DELAY = 0

    try:
        with pytest.raises(RuntimeError, match=raw_canary):
            service._call_with_retry(
                lambda: (_ for _ in ()).throw(RuntimeError(raw_canary)),
                "report_console_probe",
                max_retries=1,
            )
    finally:
        console_logger.close()
        del console_logger

    response = report_client.get(
        f"/api/report/{report_id}/console-log/stream"
    )

    assert response.status_code == 200
    rendered = response.get_data(as_text=True)
    assert raw_canary not in rendered
    assert "report_console_probe" in rendered
    assert "RuntimeError" in rendered


def test_post_create_lease_assignment_failure_fails_exact_task_and_cleans_up(
    report_client,
    monkeypatch,
):
    assignment_canary = "PRIVATE_LEASE_ASSIGNMENT_FAILURE"
    simulation = SimpleNamespace(
        simulation_id="simulation-route-lease-assignment-failure",
        project_id="project-route-lease-assignment-failure",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _TaskManager()

    class _FailingLease:
        @property
        def task_id(self):
            return None

        @task_id.setter
        def task_id(self, _value) -> None:
            raise RuntimeError(assignment_canary)

    class _FailingAssignmentCoordinator:
        def __init__(self) -> None:
            self.lease = _FailingLease()
            self.releases = []

        def acquire(self, _simulation_id, _report_id):
            return self.lease, None

        def release(self, lease) -> None:
            self.releases.append(lease)

    coordinator = _FailingAssignmentCoordinator()
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    created_task_id = task_manager.created[0][1]["task_id"]
    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "report_dispatch_failed",
    }
    assert task_manager.failures == [
        (
            created_task_id,
            "report_dispatch_failed",
            {"public_error": "report_dispatch_failed"},
        )
    ]
    assert coordinator.releases == [coordinator.lease]
    assert assignment_canary not in repr(
        (response.get_json(), task_manager.failures)
    )


def test_route_rejects_padded_project_graph_before_task_or_lease(
    report_client,
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-route-padded-graph",
        project_id="project-route-padded-graph",
        graph_id=None,
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="  project-graph  ",
        simulation_requirement="Canonical decision.",
    )
    task_manager = _TaskManager()
    coordinator = _Coordinator()
    dispatches = []
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **options: dispatches.append(options),
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "report_graph_id_missing",
    }
    assert task_manager.created == []
    assert coordinator.acquisitions == []
    assert dispatches == []


def test_route_rejects_blank_project_requirement_before_task_or_lease(
    report_client,
    monkeypatch,
):
    simulation = SimpleNamespace(
        simulation_id="simulation-route-blank-requirement",
        project_id="project-route-blank-requirement",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="  \t\r\n  ",
    )
    task_manager = _TaskManager()
    coordinator = _Coordinator()
    dispatches = []
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **options: dispatches.append(options),
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "report_simulation_requirement_missing",
    }
    assert task_manager.created == []
    assert coordinator.acquisitions == []
    assert dispatches == []


def test_dispatch_failure_releases_lease_when_task_failure_persistence_raises(
    report_client,
    monkeypatch,
):
    persistence_canary = "PRIVATE_ROUTE_FAIL_TASK_STORAGE_CANARY"
    simulation = SimpleNamespace(
        simulation_id="simulation-route-fail-task-error",
        project_id="project-route-fail-task-error",
        graph_id="project-graph",
    )
    project = SimpleNamespace(
        project_id=simulation.project_id,
        graph_id="project-graph",
        simulation_requirement="Canonical decision.",
    )

    class _FailurePersistenceUnavailable(_TaskManager):
        def fail_task(self, task_id, error, **kwargs) -> None:
            raise RuntimeError(persistence_canary)

    class _RecordingLogger:
        def __init__(self) -> None:
            self.records = []

        def error(self, message, *args, **_kwargs) -> None:
            self.records.append(message % args if args else message)

    task_manager = _FailurePersistenceUnavailable()
    coordinator = _Coordinator()
    recording_logger = _RecordingLogger()
    monkeypatch.setattr(report_api, "logger", recording_logger)
    monkeypatch.setattr(report_api, "TaskManager", lambda: task_manager)
    monkeypatch.setattr(
        report_api.SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(
        report_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        report_api,
        "report_generation_coordinator",
        coordinator,
    )
    monkeypatch.setattr(
        report_tasks.generate_report_task,
        "apply_async",
        lambda **_options: (_ for _ in ()).throw(
            ConnectionError("private broker response")
        ),
    )

    response = report_client.post(
        "/api/report/generate",
        json={"simulation_id": simulation.simulation_id},
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "report_dispatch_failed",
    }
    assert coordinator.releases == [coordinator.lease]
    assert persistence_canary not in repr(recording_logger.records)

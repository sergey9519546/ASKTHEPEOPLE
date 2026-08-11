"""
Celery Report Tasks (Gate 2 Refactor)
Background execution for synthetic report generation.
"""

import uuid

from ..celery_app import celery_app
from ..models.task import TaskExecutionConflict, TaskManager, TaskStatus
from ..services.report_agent import ReportAgent, ReportManager, ReportStatus
from ..utils.logger import get_logger

logger = get_logger("askthepeople.tasks.report_tasks")


class _ReportContextError(RuntimeError):
    """Stable failure raised only for server-owned report context defects."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _ReportCompletionStateAmbiguous(_ReportContextError):
    """Completion may already be durable, so failure must not overwrite it."""

    def __init__(self) -> None:
        super().__init__("report_generation_failed")


class _ReportExecutionInProgress(_ReportContextError):
    """A sibling delivery owns the durable report worker fence."""

    def __init__(self) -> None:
        super().__init__("report_generation_in_progress")


def _completed_task_matches_delivery(
    task,
    simulation_id: str,
    report_id: str,
    graph_id: str | None = None,
) -> bool:
    sources = [
        source
        for source in (
            getattr(task, "result", None),
            getattr(task, "metadata", None),
        )
        if isinstance(source, dict)
    ]
    required_identities = [
        ("simulation_id", simulation_id),
        ("report_id", report_id),
    ]
    if graph_id is not None:
        required_identities.append(("graph_id", graph_id))
    for key, expected in required_identities:
        persisted_values = [source[key] for source in sources if key in source]
        if not persisted_values or any(value != expected for value in persisted_values):
            return False
    return True


def _generated_report_matches_context(
    report,
    *,
    report_id: str,
    simulation_id: str,
    graph_id: str,
    simulation_requirement: str,
) -> bool:
    """Require the generated artifact to retain every authoritative identity."""
    return (
        getattr(report, "status", None) is ReportStatus.COMPLETED
        and getattr(report, "report_id", None) == report_id
        and getattr(report, "simulation_id", None) == simulation_id
        and getattr(report, "graph_id", None) == graph_id
        and getattr(report, "simulation_requirement", None)
        == simulation_requirement
    )


def _persisted_report_matches_context(
    *,
    report_id: str,
    simulation_id: str,
    graph_id: str,
    simulation_requirement: str,
) -> bool:
    """Verify that the terminal task still has its canonical report artifact."""
    try:
        report = ReportManager.get_report(report_id)
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return _generated_report_matches_context(
        report,
        report_id=report_id,
        simulation_id=simulation_id,
        graph_id=graph_id,
        simulation_requirement=simulation_requirement,
    )


def _complete_task_with_fence(
    task_manager,
    task_id: str,
    result: dict,
    execution_owner: str | None,
) -> None:
    if execution_owner is None:
        task_manager.complete_task(task_id, result=result)
    else:
        task_manager.complete_task(
            task_id,
            result=result,
            execution_owner=execution_owner,
        )


def _fail_task_with_fence(
    task_manager,
    task_id: str,
    failure_code: str,
    execution_owner: str | None,
) -> None:
    kwargs = {"public_error": failure_code}
    if execution_owner is not None:
        kwargs["execution_owner"] = execution_owner
    task_manager.fail_task(task_id, failure_code, **kwargs)


@celery_app.task(
    name="tasks.generate_report_task",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_report_task(
    self,
    simulation_id: str,
    report_id: str,
    user_prompt: str | None = None,
    custom_instructions: str | None = None,
    task_id: str | None = None,
    **ignored_payload,
):
    """Celery task for async report generation."""
    # Legacy payload fields remain accepted for queue compatibility but must
    # never influence report context or cross the ReportAgent boundary.
    del user_prompt, custom_instructions, ignored_payload

    request_task_id = getattr(self.request, "id", None)
    effective_task_id = request_task_id or task_id
    task_manager = TaskManager()
    completed_delivery = None
    queued_task = None
    execution_owner = None
    generation_fence = None

    logger.info(
        "Celery report task started: task_id=%s, report_id=%s, simulation_id=%s",
        effective_task_id,
        report_id,
        simulation_id,
    )

    try:
        if not effective_task_id:
            raise _ReportContextError("report_task_identity_missing")

        queued_task = task_manager.get_task(effective_task_id)
        if getattr(queued_task, "status", None) is TaskStatus.COMPLETED:
            if not _completed_task_matches_delivery(
                queued_task,
                simulation_id,
                report_id,
            ):
                raise _ReportCompletionStateAmbiguous()
            completed_delivery = queued_task
        else:
            claim_execution = getattr(
                task_manager,
                "claim_task_execution",
                None,
            )
            if callable(claim_execution):
                execution_owner = uuid.uuid4().hex
                try:
                    queued_task = claim_execution(
                        effective_task_id,
                        execution_owner,
                        expected_task_type="report_generate",
                        expected_idempotency_key=(
                            f"report_generate:{simulation_id}"
                        ),
                        expected_metadata={
                            "simulation_id": simulation_id,
                            "report_id": report_id,
                        },
                        progress=5,
                        message="Initializing report generation agent...",
                    )
                except TaskExecutionConflict as exc:
                    if str(exc) == "task_execution_in_progress":
                        raise _ReportExecutionInProgress() from None
                    raise _ReportContextError(
                        "report_task_identity_mismatch"
                    ) from None
                if getattr(queued_task, "status", None) is TaskStatus.COMPLETED:
                    if not _completed_task_matches_delivery(
                        queued_task,
                        simulation_id,
                        report_id,
                    ):
                        raise _ReportCompletionStateAmbiguous()
                    completed_delivery = queued_task
                    execution_owner = None
                else:
                    generation_fence = task_manager.execution_fence(
                        effective_task_id,
                        execution_owner,
                    )
            else:
                # Compatibility for narrow injected test managers. Production
                # TaskManager always takes the durable branch above.
                task_manager.update_task(
                    effective_task_id,
                    status=TaskStatus.PROCESSING,
                    progress=5,
                    message="Initializing report generation agent...",
                )

        # Resolve required parameters from the simulation
        from ..services.simulation_manager import SimulationManager
        simulation = SimulationManager().get_simulation(simulation_id)
        if not simulation:
            raise _ReportContextError("report_simulation_not_found")

        from ..models.project import ProjectManager
        project = ProjectManager.get_project(simulation.project_id)
        if not project:
            raise _ReportContextError("report_project_not_found")

        persisted_requirement = getattr(project, "simulation_requirement", None)
        if not isinstance(persisted_requirement, str):
            raise _ReportContextError("report_simulation_requirement_missing")
        simulation_requirement = persisted_requirement.strip()
        if not simulation_requirement:
            raise _ReportContextError("report_simulation_requirement_missing")

        project_graph_id = getattr(project, "graph_id", None)
        if (
            not isinstance(project_graph_id, str)
            or not project_graph_id.strip()
            or project_graph_id != project_graph_id.strip()
        ):
            raise _ReportContextError("report_graph_id_missing")

        simulation_graph_id = getattr(simulation, "graph_id", None)
        if (
            simulation_graph_id not in (None, "")
            and simulation_graph_id != project_graph_id
        ):
            raise _ReportContextError("report_graph_scope_mismatch")

        queued_metadata = getattr(queued_task, "metadata", None)
        if queued_task is not None:
            if not isinstance(queued_metadata, dict) or not queued_metadata:
                raise _ReportContextError("report_task_identity_missing")
            if (
                queued_metadata.get("simulation_id") != simulation_id
                or queued_metadata.get("report_id") != report_id
            ):
                raise _ReportContextError("report_task_identity_mismatch")
            if queued_metadata.get("graph_id") != project_graph_id:
                raise _ReportContextError("report_graph_scope_mismatch")

        persisted_report_is_exact = _persisted_report_matches_context(
            report_id=report_id,
            simulation_id=simulation_id,
            graph_id=project_graph_id,
            simulation_requirement=simulation_requirement,
        )
        if completed_delivery is not None and not _completed_task_matches_delivery(
            completed_delivery,
            simulation_id,
            report_id,
            project_graph_id,
        ):
            raise _ReportCompletionStateAmbiguous()

        completion_result = {
            "report_id": report_id,
            "simulation_id": simulation_id,
            "graph_id": project_graph_id,
            "status": "completed",
        }
        if persisted_report_is_exact:
            if effective_task_id and completed_delivery is None:
                try:
                    _complete_task_with_fence(
                        task_manager,
                        effective_task_id,
                        completion_result,
                        execution_owner,
                    )
                except Exception:
                    try:
                        persisted_task = task_manager.get_task(effective_task_id)
                    except Exception:
                        raise _ReportCompletionStateAmbiguous() from None
                    if not (
                        getattr(persisted_task, "status", None)
                        is TaskStatus.COMPLETED
                        and _completed_task_matches_delivery(
                            persisted_task,
                            simulation_id,
                            report_id,
                            project_graph_id,
                        )
                    ):
                        raise _ReportCompletionStateAmbiguous() from None
            return {"success": True, "report_id": report_id}

        if completed_delivery is not None:
            raise _ReportCompletionStateAmbiguous()

        agent = ReportAgent(
            graph_id=project_graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement,
        )

        generated_report = agent.generate_report(
            report_id=report_id,
            generation_lease=generation_fence,
        )
        if not _generated_report_matches_context(
            generated_report,
            report_id=report_id,
            simulation_id=simulation_id,
            graph_id=project_graph_id,
            simulation_requirement=simulation_requirement,
        ):
            raise _ReportContextError("report_generation_failed")

        if effective_task_id:
            try:
                _complete_task_with_fence(
                    task_manager,
                    effective_task_id,
                    completion_result,
                    execution_owner,
                )
            except Exception:
                try:
                    persisted_task = task_manager.get_task(effective_task_id)
                except Exception:
                    raise _ReportCompletionStateAmbiguous() from None
                persisted_status = getattr(persisted_task, "status", None)
                if persisted_status is TaskStatus.COMPLETED:
                    if not _completed_task_matches_delivery(
                        persisted_task,
                        simulation_id,
                        report_id,
                        project_graph_id,
                    ) or not _persisted_report_matches_context(
                        report_id=report_id,
                        simulation_id=simulation_id,
                        graph_id=project_graph_id,
                        simulation_requirement=simulation_requirement,
                    ):
                        raise _ReportCompletionStateAmbiguous() from None
                elif persisted_status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
                    raise _ReportContextError("report_generation_failed") from None
                else:
                    raise _ReportCompletionStateAmbiguous() from None
        return {"success": True, "report_id": report_id}

    except Exception as exc:
        failure_code = (
            exc.code
            if isinstance(exc, _ReportContextError)
            else "report_generation_failed"
        )
        logger.error(
            "generate_report_task failed: code=%s",
            failure_code,
            extra={"privacy_safe": True},
        )
        if (
            effective_task_id
            and completed_delivery is None
            and not isinstance(
                exc,
                (_ReportCompletionStateAmbiguous, _ReportExecutionInProgress),
            )
        ):
            try:
                _fail_task_with_fence(
                    task_manager,
                    effective_task_id,
                    failure_code,
                    execution_owner,
                )
            except Exception:
                logger.error(
                    "Report task failure persistence failed: "
                    "code=report_failure_persistence_failed",
                    extra={"privacy_safe": True},
                )
        raise RuntimeError(failure_code) from None

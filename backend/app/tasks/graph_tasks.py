"""
Celery Graph Tasks (Gate 2 Refactor)
Background execution for ontology generation and Zep graph building.
"""

import hashlib
from functools import wraps
from typing import Optional

from celery.exceptions import Retry

from ..celery_app import celery_app
from ..models.project import ProjectManager, ProjectStatus
from ..models.task import TaskManager, TaskStatus
from ..services.graph_builder import GraphBuilderService, GraphBuildProviderError
from ..services.ontology_generator import OntologyGenerator
from ..services.project_repository import CanonicalSourceReadError
from ..utils.logger import get_logger
from ..utils.task_retry import is_retryable_task_exception

logger = get_logger('askthepeople.tasks.graph_tasks')

_GRAPH_BUILD_FAILED = "graph_build_failed"
_GRAPH_BUILD_PERSISTENCE_FAILED = "graph_build_persistence_failed"
_GRAPH_BUILD_RETRY_DISPATCH_FAILED = "graph_build_retry_dispatch_failed"
_GRAPH_BUILD_SUPERSEDED = "graph_build_superseded"
_GRAPH_TASK_COMPLETION_PERSISTENCE_FAILED = (
    "graph_task_completion_persistence_failed"
)
_ONTOLOGY_GENERATION_FAILED = "ontology_generation_failed"
_SPECIFIC_TERMINAL_PROVIDER_ERRORS = {
    "graph_create_conflict_unsafe",
    "graph_episode_submission_unconfirmed",
    "graph_processing_failed",
    "graph_processing_timeout",
}


class GraphBuildPersistenceError(RuntimeError):
    """The derived Zep graph was created but its canonical record was not."""


class GraphTaskPersistenceError(RuntimeError):
    """Task progress persistence failed outside the provider boundary."""


class GraphTaskCompletionPersistenceError(RuntimeError):
    """Project completion persisted but the task envelope did not."""


class GraphRetryDispatchError(RuntimeError):
    """A safe provider retry could not be published to the broker."""


class CanonicalGraphInputReadError(RuntimeError):
    """A retryable canonical project/ontology read failed before mutation."""

    def __init__(self) -> None:
        super().__init__("canonical_graph_input_read_failed")


def _serialize_graph_delivery(task_function):
    """Fence one immutable Celery delivery before any provider mutation."""

    @wraps(task_function)
    def fenced(self, project_id: str, *args, **kwargs):
        request_task_id = getattr(self.request, "id", None)
        effective_task_id = request_task_id or kwargs.get("task_id")
        if not effective_task_id:
            return task_function(self, project_id, *args, **kwargs)
        with ProjectManager.graph_build_delivery_fence(
            project_id,
            effective_task_id,
        ):
            return task_function(self, project_id, *args, **kwargs)

    return fenced


def _stable_graph_id(project_id: str, build_id: str) -> str:
    """Derive a provider-safe ID that remains stable across Celery retries."""
    digest = hashlib.sha256(f"{project_id}:{build_id}".encode()).hexdigest()[:16]
    return f"atp_{digest}"


def _is_exact_graph_completion(project, task_id: str, graph_id: str) -> bool:
    """Return whether canonical state proves this exact delivery completed."""
    return bool(
        project
        and project.status == ProjectStatus.GRAPH_COMPLETED
        and project.graph_build_task_id == task_id
        and project.graph_id == graph_id
    )


def _complete_task_envelope(task_manager, task_id: str, result: dict, project_id: str) -> None:
    """Complete the task envelope without ever downgrading canonical success."""
    try:
        task_manager.complete_task(task_id, result=result)
    except Exception as exc:
        logger.error(
            "%s project_id=%s task_id=%s",
            _GRAPH_TASK_COMPLETION_PERSISTENCE_FAILED,
            project_id,
            task_id,
        )
        try:
            persisted_task = task_manager.get_task(task_id)
        except Exception:
            persisted_task = None
            logger.error(
                "graph task completion reread failed project_id=%s task_id=%s",
                project_id,
                task_id,
            )
        if (
            persisted_task is not None
            and persisted_task.status == TaskStatus.COMPLETED
        ):
            return
        if (
            persisted_task is not None
            and persisted_task.status in {TaskStatus.PENDING, TaskStatus.PROCESSING}
        ):
            try:
                task_manager.fail_task(
                    task_id,
                    _GRAPH_TASK_COMPLETION_PERSISTENCE_FAILED,
                    public_error=_GRAPH_TASK_COMPLETION_PERSISTENCE_FAILED,
                )
            except Exception:
                logger.error(
                    "graph task completion recovery failed project_id=%s task_id=%s",
                    project_id,
                    task_id,
                )
        raise GraphTaskCompletionPersistenceError(
            _GRAPH_TASK_COMPLETION_PERSISTENCE_FAILED
        ) from exc


@celery_app.task(
    name='tasks.generate_ontology_task',
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_ontology_task(
    self,
    project_id: str,
    text: str,
    requirements: Optional[str] = None,
    task_id: Optional[str] = None,
    **kwargs
):
    """Celery task for async ontology generation."""
    effective_task_id = getattr(self.request, 'id', None) or task_id
    task_manager = None
    project = None
    ontology_persisted = False

    logger.info(f"Celery task generate_ontology_task started: task_id={effective_task_id}, project_id={project_id}")

    try:
        task_manager = TaskManager()
        if effective_task_id:
            task_manager.update_task(
                effective_task_id,
                status=TaskStatus.PROCESSING,
                progress=10,
                message="Analyzing document structure for ontology generation..."
            )

        project = ProjectManager.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        generator = OntologyGenerator()
        result = generator.generate(text, requirements=requirements)

        if result.get("success"):
            ontology_data = result.get("ontology", {})
            summary = result.get("summary", "")

            project.ontology = ontology_data
            project.analysis_summary = summary
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            ProjectManager.save_project(
                project,
                _ontology_task_id=effective_task_id,
            )
            ontology_persisted = True

            if effective_task_id:
                task_manager.complete_task(
                    effective_task_id,
                    result={
                        "project_id": project_id,
                        "ontology": ontology_data,
                        "summary": summary
                    }
                )
            return {"success": True, "project_id": project_id}
        else:
            project.status = ProjectStatus.FAILED
            project.error = _ONTOLOGY_GENERATION_FAILED
            ProjectManager.save_project(project)
            if effective_task_id:
                task_manager.fail_task(
                    effective_task_id,
                    _ONTOLOGY_GENERATION_FAILED,
                    public_error=_ONTOLOGY_GENERATION_FAILED,
                )
            return {"success": False, "error": _ONTOLOGY_GENERATION_FAILED}

    except Exception as exc:
        logger.error(
            "ontology generation failed exception_type=%s",
            type(exc).__name__,
        )
        if project is not None and not ontology_persisted:
            project.status = ProjectStatus.FAILED
            project.error = _ONTOLOGY_GENERATION_FAILED
            try:
                ProjectManager.save_project(project)
            except Exception:
                logger.error("ontology failure persistence unavailable")
        if effective_task_id and task_manager is not None:
            try:
                task_manager.fail_task(
                    effective_task_id,
                    _ONTOLOGY_GENERATION_FAILED,
                    public_error=_ONTOLOGY_GENERATION_FAILED,
                )
            except Exception:
                logger.error("ontology task failure persistence unavailable")
        raise RuntimeError(_ONTOLOGY_GENERATION_FAILED) from None


@celery_app.task(
    name='tasks.build_graph_task',
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
@_serialize_graph_delivery
def build_graph_task(
    self,
    project_id: str,
    graph_name: Optional[str] = None,
    task_id: Optional[str] = None,
    **kwargs
):
    """Celery task for async Zep graph building."""
    # Celery's delivery identity is immutable across a retry. ``task_id`` is
    # retained only as a direct-unit-test fallback; production dispatch sets
    # the Celery ID explicitly and sends no identity in kwargs.
    request_task_id = getattr(self.request, "id", None)
    effective_task_id = request_task_id or task_id
    task_manager = TaskManager()

    logger.info(f"Celery task build_graph_task started: task_id={effective_task_id}, project_id={project_id}")

    project = None
    provider_failure = None
    incomplete_graph_id = None
    try:
        try:
            project = ProjectManager.get_project(project_id)
        except Exception as read_exc:
            if is_retryable_task_exception(read_exc):
                raise CanonicalGraphInputReadError() from None
            raise
        if not project:
            raise ValueError("project_not_found")

        if not effective_task_id:
            raise ValueError("graph_task_identity_missing")

        incomplete_graph_id = _stable_graph_id(project_id, effective_task_id)

        if _is_exact_graph_completion(
            project,
            effective_task_id,
            incomplete_graph_id,
        ):
            existing_result = {
                "success": True,
                "graph_id": incomplete_graph_id,
                "status": "completed",
            }
            _complete_task_envelope(
                task_manager,
                effective_task_id,
                existing_result,
                project_id,
            )
            return existing_result

        persisted_task_id = project.graph_build_task_id
        if (
            persisted_task_id
            and effective_task_id
            and persisted_task_id != effective_task_id
        ):
            task_manager.fail_task(
                effective_task_id,
                _GRAPH_BUILD_SUPERSEDED,
                public_error=_GRAPH_BUILD_SUPERSEDED,
            )
            raise RuntimeError(_GRAPH_BUILD_SUPERSEDED)

        if not ProjectManager.ensure_graph_build_owner(project_id, effective_task_id):
            task_manager.fail_task(
                effective_task_id,
                _GRAPH_BUILD_SUPERSEDED,
                public_error=_GRAPH_BUILD_SUPERSEDED,
            )
            raise RuntimeError(_GRAPH_BUILD_SUPERSEDED)

        task_manager.update_task(
            effective_task_id,
            status=TaskStatus.PROCESSING,
            progress=5,
            message="Initializing graph build...",
        )

        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            raise ValueError("extracted_source_not_found")
        if not project.ontology:
            raise ValueError("ontology_not_found")

        project_name = project.name.strip() if isinstance(project.name, str) else ""
        authoritative_graph_name = project_name or "Source graph"

        def progress_callback(percentage: int, message: str):
            if effective_task_id:
                try:
                    task_manager.update_task(
                        effective_task_id,
                        status=TaskStatus.PROCESSING,
                        progress=percentage,
                        message=message,
                    )
                except Exception as exc:
                    raise GraphTaskPersistenceError(
                        "graph_task_progress_persistence_failed"
                    ) from exc

        try:
            service = GraphBuilderService()
            build_res = service.build_graph(
                graph_id=incomplete_graph_id,
                text=text,
                ontology=project.ontology,
                graph_name=authoritative_graph_name,
                chunk_size=project.chunk_size,
                chunk_overlap=project.chunk_overlap,
                progress_callback=progress_callback,
            )
        except Exception as exc:
            provider_failure = exc
            raise

        if build_res.get("success"):
            build_res["graph_id"] = incomplete_graph_id
            try:
                completed = ProjectManager.complete_graph_build(
                    project_id,
                    effective_task_id,
                    incomplete_graph_id,
                )
            except Exception as exc:
                try:
                    persisted = ProjectManager.get_project(project_id)
                except Exception:
                    persisted = None
                if _is_exact_graph_completion(
                    persisted,
                    effective_task_id,
                    incomplete_graph_id,
                ):
                    completed = True
                else:
                    raise GraphBuildPersistenceError from exc
            if not completed:
                task_manager.fail_task(
                    effective_task_id,
                    _GRAPH_BUILD_SUPERSEDED,
                    public_error=_GRAPH_BUILD_SUPERSEDED,
                )
                raise RuntimeError(_GRAPH_BUILD_SUPERSEDED)

            _complete_task_envelope(
                task_manager,
                effective_task_id,
                build_res,
                project_id,
            )
            return build_res

        raise RuntimeError(_GRAPH_BUILD_FAILED)

    except Exception as exc:
        if str(exc) == _GRAPH_BUILD_SUPERSEDED:
            raise RuntimeError(_GRAPH_BUILD_SUPERSEDED) from None

        if isinstance(exc, GraphTaskCompletionPersistenceError):
            # The canonical project is already complete. Never attempt a
            # compensating downgrade because only the task envelope failed.
            raise RuntimeError(_GRAPH_TASK_COMPLETION_PERSISTENCE_FAILED) from None

        provider_retryable = False
        if provider_failure is exc:
            classified_exception = (
                exc.__cause__
                if isinstance(exc, GraphBuildProviderError) and exc.__cause__ is not None
                else exc
            )
            provider_retryable = bool(
                getattr(exc, "retry_safe", True)
                and is_retryable_task_exception(classified_exception)
            )
        canonical_source_retryable = bool(
            isinstance(exc, CanonicalSourceReadError) and exc.retryable
        )
        canonical_input_retryable = isinstance(exc, CanonicalGraphInputReadError)
        if (
            (
                provider_retryable
                or canonical_source_retryable
                or canonical_input_retryable
            )
            and self.request.retries < 3
        ):
            logger.warning(
                "build_graph_task hit a transient replay-safe dependency failure "
                "(attempt %s/3) for project_id=%s",
                self.request.retries + 1,
                project_id,
            )
            try:
                retry_signal = self.retry(
                    exc=exc,
                    countdown=int(2 ** self.request.retries),
                )
            except Retry:
                raise
            except Exception as retry_publish_exc:
                logger.error(
                    "%s project_id=%s task_id=%s exception_type=%s",
                    _GRAPH_BUILD_RETRY_DISPATCH_FAILED,
                    project_id,
                    effective_task_id,
                    type(retry_publish_exc).__name__,
                )
                dispatch_error = GraphRetryDispatchError(
                    _GRAPH_BUILD_RETRY_DISPATCH_FAILED
                )
                dispatch_error.__cause__ = retry_publish_exc
                exc = dispatch_error
            else:
                if isinstance(retry_signal, Retry):
                    raise retry_signal
                dispatch_error = GraphRetryDispatchError(
                    _GRAPH_BUILD_RETRY_DISPATCH_FAILED
                )
                exc = dispatch_error

        if isinstance(exc, GraphBuildPersistenceError):
            error_code = _GRAPH_BUILD_PERSISTENCE_FAILED
        elif isinstance(exc, GraphRetryDispatchError):
            error_code = _GRAPH_BUILD_RETRY_DISPATCH_FAILED
        elif (
            isinstance(exc, GraphBuildProviderError)
            and str(exc) in _SPECIFIC_TERMINAL_PROVIDER_ERRORS
        ):
            error_code = str(exc)
        else:
            error_code = _GRAPH_BUILD_FAILED

        reconciliation_required = bool(
            incomplete_graph_id
            and (
                provider_failure is not None
                or isinstance(exc, GraphBuildPersistenceError)
            )
        )
        if reconciliation_required:
            logger.warning(
                "incomplete derived graph may require reconciliation project_id=%s graph_id=%s",
                project_id,
                incomplete_graph_id,
            )

        if effective_task_id:
            try:
                failed = ProjectManager.fail_graph_build(
                    project_id,
                    effective_task_id,
                    error_code,
                )
            except Exception:
                logger.error(
                    "build_graph_task could not persist terminal failure for project_id=%s",
                    project_id,
                )
            else:
                if not failed and project is not None:
                    try:
                        task_manager.fail_task(
                            effective_task_id,
                            _GRAPH_BUILD_SUPERSEDED,
                            public_error=_GRAPH_BUILD_SUPERSEDED,
                        )
                    except Exception:
                        logger.error(
                            "build_graph_task could not persist superseded task state task_id=%s",
                            effective_task_id,
                        )
                    raise RuntimeError(_GRAPH_BUILD_SUPERSEDED) from None
                if not failed:
                    logger.error(
                        "graph build owner-fenced terminal recovery was not "
                        "persisted project_id=%s task_id=%s",
                        project_id,
                        effective_task_id,
                    )

        logger.error(
            "build_graph_task failed terminally for project_id=%s error=%s",
            project_id,
            error_code,
        )
        if effective_task_id:
            try:
                task_manager.fail_task(
                    effective_task_id,
                    error_code,
                    public_error=_GRAPH_BUILD_FAILED,
                )
            except Exception:
                logger.error(
                    "build_graph_task could not persist terminal task state task_id=%s",
                    effective_task_id,
                )
        raise RuntimeError(error_code) from None

"""
Celery Report Tasks (Gate 2 Refactor)
Background execution for synthetic report generation.
"""

from typing import Optional, Dict, Any
from ..celery_app import celery_app
from ..models.task import TaskManager, TaskStatus
from ..services.report_agent import ReportAgent
from ..utils.logger import get_logger

logger = get_logger('askthepeople.tasks.report_tasks')


@celery_app.task(name='tasks.generate_report_task', bind=True)
def generate_report_task(
    self,
    simulation_id: str,
    report_id: str,
    user_prompt: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    task_id: Optional[str] = None,
    **kwargs
):
    """Celery task for async report generation."""
    effective_task_id = task_id or getattr(self.request, 'id', None)
    task_manager = TaskManager()

    logger.info(f"Celery task generate_report_task started: task_id={effective_task_id}, report_id={report_id}, simulation_id={simulation_id}")

    if effective_task_id:
        task_manager.update_task(
            effective_task_id,
            status=TaskStatus.PROCESSING,
            progress=5,
            message="Initializing report generation agent..."
        )

    try:
        def progress_callback(progress: int, message: str, stage: Optional[str] = None):
            if effective_task_id:
                task_manager.update_task(
                    effective_task_id,
                    status=TaskStatus.PROCESSING,
                    progress=progress,
                    message=message,
                    progress_detail={"stage": stage} if stage else None
                )

        agent = ReportAgent(
            simulation_id=simulation_id,
            report_id=report_id,
            user_prompt=user_prompt,
            custom_instructions=custom_instructions,
            progress_callback=progress_callback
        )

        report_result = agent.generate_report()

        if effective_task_id:
            task_manager.complete_task(
                effective_task_id,
                result={
                    "report_id": report_id,
                    "simulation_id": simulation_id,
                    "status": "completed"
                }
            )
        return {"success": True, "report_id": report_id}

    except Exception as e:
        logger.error(f"generate_report_task failed for report_id={report_id}: {str(e)}")
        if effective_task_id:
            task_manager.fail_task(effective_task_id, str(e))
        raise

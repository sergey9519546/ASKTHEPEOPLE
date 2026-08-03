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
        # Resolve required parameters from the simulation
        from ..services.simulation_manager import SimulationManager
        simulation = SimulationManager().get_simulation(simulation_id)
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        from ..models.project import ProjectManager
        project = ProjectManager.get_project(simulation.project_id)
        if not project:
            raise ValueError(f"Project {simulation.project_id} not found")
        
        agent = ReportAgent(
            graph_id=project.graph_id,
            simulation_id=simulation_id,
            simulation_requirement=project.decision_text or "Analyze the simulation outcomes"
        )

        report_result = agent.generate_report(
            report_id=report_id,
            generation_lease=None  # FIXME: lease should come from coordinator, not None
        )

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

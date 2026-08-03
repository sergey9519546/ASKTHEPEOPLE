"""
Celery Graph Tasks (Gate 2 Refactor)
Background execution for ontology generation and Zep graph building.
"""

from typing import Optional
from ..celery_app import celery_app
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..utils.logger import get_logger

logger = get_logger('askthepeople.tasks.graph_tasks')


@celery_app.task(name='tasks.generate_ontology_task', bind=True)
def generate_ontology_task(
    self,
    project_id: str,
    text: str,
    requirements: Optional[str] = None,
    task_id: Optional[str] = None,
    **kwargs
):
    """Celery task for async ontology generation."""
    effective_task_id = task_id or getattr(self.request, 'id', None)
    task_manager = TaskManager()

    logger.info(f"Celery task generate_ontology_task started: task_id={effective_task_id}, project_id={project_id}")

    if effective_task_id:
        task_manager.update_task(
            effective_task_id,
            status=TaskStatus.PROCESSING,
            progress=10,
            message="Analyzing document structure for ontology generation..."
        )

    try:
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
            ProjectManager.save_project(project)

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
            err_msg = result.get("error", "Ontology generation failed")
            project.status = ProjectStatus.FAILED
            ProjectManager.save_project(project)
            if effective_task_id:
                task_manager.fail_task(effective_task_id, err_msg)
            return {"success": False, "error": err_msg}

    except Exception as e:
        logger.error(f"generate_ontology_task failed: {str(e)}")
        if effective_task_id:
            task_manager.fail_task(effective_task_id, str(e))
        raise


@celery_app.task(name='tasks.build_graph_task', bind=True)
def build_graph_task(
    self,
    project_id: str,
    graph_name: Optional[str] = None,
    task_id: Optional[str] = None,
    **kwargs
):
    """Celery task for async Zep graph building."""
    effective_task_id = task_id or getattr(self.request, 'id', None)
    task_manager = TaskManager()

    logger.info(f"Celery task build_graph_task started: task_id={effective_task_id}, project_id={project_id}")

    if effective_task_id:
        task_manager.update_task(
            effective_task_id,
            status=TaskStatus.PROCESSING,
            progress=5,
            message="Initializing graph build..."
        )

    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        project.status = ProjectStatus.GRAPH_BUILDING
        ProjectManager.save_project(project)

        def progress_callback(percentage: int, message: str):
            if effective_task_id:
                task_manager.update_task(
                    effective_task_id,
                    status=TaskStatus.PROCESSING,
                    progress=percentage,
                    message=message
                )

        service = GraphBuilderService()
        build_res = service.build_graph_for_project(
            project_id,
            graph_name=graph_name,
            progress_callback=progress_callback
        )

        if build_res.get("success"):
            project.status = ProjectStatus.GRAPH_COMPLETED
            project.graph_id = build_res.get("graph_id")
            ProjectManager.save_project(project)

            if effective_task_id:
                task_manager.complete_task(effective_task_id, result=build_res)
            return build_res
        else:
            err_msg = build_res.get("error", "Graph build failed")
            project.status = ProjectStatus.FAILED
            ProjectManager.save_project(project)
            if effective_task_id:
                task_manager.fail_task(effective_task_id, err_msg)
            return {"success": False, "error": err_msg}

    except Exception as e:
        logger.error(f"build_graph_task failed: {str(e)}")
        if effective_task_id:
            task_manager.fail_task(effective_task_id, str(e))
        raise

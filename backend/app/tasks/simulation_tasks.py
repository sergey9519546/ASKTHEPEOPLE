"""
Celery Simulation Tasks
Background execution wrapper for OASIS simulations.
"""

import time
from typing import Dict, Any, Optional
from ..celery_app import celery_app
from ..models.task import TaskManager, TaskStatus
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..utils.logger import get_logger

logger = get_logger('askthepeople.tasks.simulation_tasks')


@celery_app.task(name='tasks.run_simulation_task', bind=True)
def run_simulation_task(
    self,
    simulation_id: str,
    platform: str = "parallel",
    max_rounds: Optional[int] = None,
    enable_graph_memory_update: bool = False,
    graph_id: Optional[str] = None,
    enable_followers: bool = False,
    follower_count: int = 100,
    follower_distribution: Optional[Dict[str, float]] = None,
    source_graph_id: Optional[str] = None,
    task_id: Optional[str] = None,
    config_path: Optional[str] = None,
    **kwargs
):
    """
    Celery task wrapper for initializing, executing, and monitoring OASIS simulations.

    Updates task state and progress in Celery result backend and TaskManager (shared storage).
    """
    effective_task_id = task_id or getattr(self.request, 'id', None)
    task_manager = TaskManager()

    logger.info(
        f"Celery task run_simulation_task started: task_id={effective_task_id}, "
        f"simulation_id={simulation_id}, platform={platform}"
    )

    if effective_task_id:
        task_manager.update_task(
            effective_task_id,
            status=TaskStatus.PROCESSING,
            progress=5,
            message="Initializing simulation execution..."
        )

    try:
        # Start simulation execution using SimulationRunner
        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform=platform,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory_update,
            graph_id=graph_id,
            enable_followers=enable_followers,
            follower_count=follower_count,
            follower_distribution=follower_distribution,
            source_graph_id=source_graph_id,
        )

        # Monitor execution until complete, failed, or stopped
        last_round = -1
        while True:
            current_state = SimulationRunner.get_run_state(simulation_id) or run_state
            status = current_state.runner_status

            total_rounds = max(1, current_state.total_rounds)
            current_round = current_state.current_round
            progress_pct = min(100, int((current_round / total_rounds) * 100))

            if current_round != last_round:
                last_round = current_round
                msg = f"Simulation executing: round {current_round}/{total_rounds}"

                # Update Celery result backend state if running under Celery request
                if hasattr(self, 'update_state'):
                    try:
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'simulation_id': simulation_id,
                                'current_round': current_round,
                                'total_rounds': total_rounds,
                                'progress': progress_pct,
                                'status': status.value if hasattr(status, 'value') else str(status),
                                'message': msg,
                            }
                        )
                    except Exception as meta_exc:
                        logger.debug(f"Celery update_state bypassed: {meta_exc}")

                # Update shared TaskManager state
                if effective_task_id:
                    task_manager.update_task(
                        effective_task_id,
                        status=TaskStatus.PROCESSING,
                        progress=progress_pct,
                        message=msg,
                        progress_detail={
                            'current_round': current_round,
                            'total_rounds': total_rounds,
                            'runner_status': status.value if hasattr(status, 'value') else str(status),
                            'simulated_hours': current_state.simulated_hours,
                        }
                    )

            if status in [RunnerStatus.COMPLETED, RunnerStatus.STOPPED, RunnerStatus.FAILED]:
                break

            time.sleep(0.5)

        final_state = SimulationRunner.get_run_state(simulation_id) or run_state
        if final_state.runner_status == RunnerStatus.FAILED:
            err_msg = final_state.error or "Simulation execution failed"
            if effective_task_id:
                task_manager.fail_task(effective_task_id, error=err_msg)
            raise RuntimeError(err_msg)

        result_dict = final_state.to_dict()
        if effective_task_id:
            task_manager.complete_task(effective_task_id, result=result_dict)

        return {
            "success": True,
            "simulation_id": simulation_id,
            "task_id": effective_task_id,
            "status": "completed",
            "result": result_dict,
        }

    except Exception as exc:
        logger.error(f"Celery task run_simulation_task failed: {exc}", exc_info=True)
        if effective_task_id:
            task_manager.fail_task(effective_task_id, error=str(exc))
        raise

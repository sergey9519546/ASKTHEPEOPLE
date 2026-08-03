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


# Stage weights for the prepare progress callback. The percentages are
# used only to produce a 0-100 progress number; they carry no quantitative
# meaning about the run's expected outcome or duration.
_PREPARE_STAGE_WEIGHTS = {
    "reading": (0, 20),
    "generating_profiles": (20, 70),
    "generating_config": (70, 90),
    "copying_scripts": (90, 100),
}

_PREPARE_STAGE_NAMES = {
    "reading": "Reading graph entities",
    "generating_profiles": "Generating Agent personas",
    "generating_config": "Generating simulation configuration",
    "copying_scripts": "Preparing simulation scripts",
}


@celery_app.task(name='tasks.prepare_simulation_task', bind=True)
def prepare_simulation_task(
    self,
    simulation_id: str,
    task_id: str,
    entity_types,
    use_llm_for_profiles: bool,
    parallel_profile_count: int,
    use_archetypes: bool,
    archetype_count: int,
    expansion_factor: int,
    document_text: str,
):
    """Celery task wrapper for the simulation preparation work.

    The previous implementation started a `threading.Thread(..., daemon=True)`
    inside the web route. That route is now an enqueue-and-return boundary;
    the work runs in a worker process. Full durable workflow (idempotency
    keys, leases, fencing tokens, heartbeats, cancellation) lands with
    gate 2 in `adr/ADR-0003-durable-run-orchestration.md`; this commit
    closes the P0 path-escape-by-daemon-thread finding by removing the
    in-process thread and routing the work through the existing Celery
    infrastructure.
    """
    from ..services.simulation_manager import SimulationManager
    from ..config import Config
    task_manager = TaskManager()
    manager = SimulationManager()
    effective_task_id = task_id or getattr(self.request, 'id', None)

    logger.info(
        f"Celery task prepare_simulation_task started: task_id={effective_task_id}, "
        f"simulation_id={simulation_id}"
    )

    if effective_task_id:
        task_manager.update_task(
            effective_task_id,
            status=TaskStatus.PROCESSING,
            progress=0,
            message="Starting simulation environment preparation..."
        )

    def progress_callback(stage, progress, message, **kwargs):
        start, end = _PREPARE_STAGE_WEIGHTS.get(stage, (0, 100))
        current_progress = int(start + (end - start) * progress / 100)

        stage_index = (
            list(_PREPARE_STAGE_WEIGHTS).index(stage) + 1
            if stage in _PREPARE_STAGE_WEIGHTS else 1
        )
        total_stages = len(_PREPARE_STAGE_WEIGHTS)

        progress_detail_data = {
            "current_stage": stage,
            "current_stage_name": _PREPARE_STAGE_NAMES.get(stage, stage),
            "stage_index": stage_index,
            "total_stages": total_stages,
            "stage_progress": progress,
            "current_item": kwargs.get("current", 0),
            "total_items": kwargs.get("total", 0),
            "item_description": message,
        }

        stage_name = _PREPARE_STAGE_NAMES.get(stage, stage)
        total_items = kwargs.get("total", 0)
        if total_items > 0:
            current_item = kwargs.get("current", 0)
            detailed_message = (
                f"[{stage_index}/{total_stages}] {stage_name}: "
                f"{current_item}/{total_items} - {message}"
            )
        else:
            detailed_message = f"[{stage_index}/{total_stages}] {stage_name}: {message}"

        # Cross-process progress: Celery result backend.
        if hasattr(self, 'update_state'):
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'simulation_id': simulation_id,
                        'progress': current_progress,
                        'message': detailed_message,
                        'progress_detail': progress_detail_data,
                    }
                )
            except Exception as meta_exc:
                logger.debug(f"Celery update_state bypassed: {meta_exc}")

        # Best-effort in-process mirror (the worker process is a
        # different process from the web; the in-memory dict is
        # per-process. The web reads from the same Redis snapshot
        # when available.)
        if effective_task_id:
            task_manager.update_task(
                effective_task_id,
                progress=current_progress,
                message=detailed_message,
                progress_detail=progress_detail_data,
            )

    try:
        result_state = manager.prepare_simulation(
            simulation_id=simulation_id,
            simulation_requirement="",
            document_text=document_text,
            defined_entity_types=list(entity_types) if entity_types else [],
            use_llm_for_profiles=use_llm_for_profiles,
            progress_callback=progress_callback,
            parallel_profile_count=parallel_profile_count,
            use_archetypes=use_archetypes,
            archetype_count=archetype_count,
            expansion_factor=expansion_factor,
        )
        if effective_task_id:
            task_manager.complete_task(
                effective_task_id,
                result=result_state.to_simple_dict()
            )
        return {
            "success": True,
            "simulation_id": simulation_id,
            "task_id": effective_task_id,
            "status": "completed",
        }
    except Exception as exc:
        logger.error(
            f"Celery task prepare_simulation_task failed: {exc}",
            exc_info=True,
        )
        
        # Check if this is a ProfileValidationError (Gate 1 requirement)
        from ..services.profile_validators import ProfileValidationError
        
        if isinstance(exc, ProfileValidationError):
            # Handle validation errors with user-friendly message
            public_error = "Unable to generate diverse profiles. Please try again or modify your decision parameters."
            logger.warning(
                f"Profile validation failed for simulation {simulation_id}: {exc.validation_type}",
                extra={
                    "validation_type": exc.validation_type,
                    "details": exc.details
                }
            )
        else:
            public_error = "simulation_prepare_failed"
        
        if effective_task_id:
            task_manager.fail_task(
                effective_task_id,
                str(exc),
                public_error=public_error,
            )
        # Mirror the in-process failure path: mark the simulation
        # state as FAILED so the GET endpoints can surface it.
        try:
            from ..config import Config
            state = manager.get_simulation(simulation_id)
            if state:
                state.status = SimulationManager.SimulationStatus.FAILED
                state.error = (
                    str(exc) if Config.DEBUG else public_error
                )
                manager._save_simulation_state(state)
        except Exception:
            pass
        raise


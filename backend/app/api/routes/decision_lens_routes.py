"""Strict review routes for immutable functional decision lenses."""

from __future__ import annotations

import uuid
from http import HTTPStatus

from flask import current_app, jsonify, request
from kombu.exceptions import OperationalError
from pydantic import ValidationError

from ...domain.decision_lens import DecisionLensV1, LensDispositionV1
from ...models.task import (
    TaskIdempotencyConflict,
    TaskManager,
    TaskStateError,
)
from ...services.decision_lens_repository import DecisionLensRepositoryError
from ...services.decision_lens_review_service import (
    DecisionLensReviewService,
    DecisionLensReviewServiceError,
)
from ...services.simulation_manager import SimulationManager, SimulationStatus
from .. import simulation_bp
from ..decision_lens_schemas import (
    DecisionLensEditRequest,
    DecisionLensReviewRequest,
)


def _context(simulation_id: str):
    manager = SimulationManager()
    state = manager.get_simulation(simulation_id)
    if state is None:
        return None, None, None
    production = not (
        current_app.config.get("DEBUG", False)
        or current_app.config.get("TESTING", False)
    )
    service = DecisionLensReviewService(
        manager._get_simulation_dir(simulation_id),
        production=production,
    )
    return manager, state, service


def _error(code: str, status: int, *, task_id: str | None = None):
    payload = {"success": False, "error": code}
    if task_id is not None:
        payload["task_id"] = task_id
    return jsonify(payload), status


@simulation_bp.get("/<simulation_id>/decision-lenses")
def get_decision_lenses(simulation_id: str):
    _manager, state, service = _context(simulation_id)
    if state is None or service is None:
        return _error("simulation_not_found", HTTPStatus.NOT_FOUND)
    try:
        snapshot = service.snapshot()
    except DecisionLensRepositoryError as exc:
        return _error(exc.code, HTTPStatus.CONFLICT)
    if snapshot["artifact"] is None:
        return _error("decision_lens_review_required", HTTPStatus.CONFLICT)
    return jsonify({"success": True, "data": snapshot})


@simulation_bp.patch("/<simulation_id>/decision-lenses/<lens_id>")
def patch_decision_lens(simulation_id: str, lens_id: str):
    manager, state, service = _context(simulation_id)
    if manager is None or state is None or service is None:
        return _error("simulation_not_found", HTTPStatus.NOT_FOUND)
    try:
        edit = DecisionLensEditRequest.model_validate(request.get_json() or {})
        artifact = service.repository.get_current_artifact()
        if artifact is None:
            return _error("decision_lens_review_required", HTTPStatus.CONFLICT)
        reference_by_id = {
            reference.ref_id: reference for reference in artifact.input_refs
        }
        if len(set(edit.input_ref_ids)) != len(edit.input_ref_ids):
            return _error("decision_lens_invalid", HTTPStatus.UNPROCESSABLE_ENTITY)
        try:
            references = tuple(reference_by_id[ref_id] for ref_id in edit.input_ref_ids)
        except KeyError:
            return _error(
                "decision_lens_input_reference_unresolved",
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        replacement = DecisionLensV1(
            lens_id=lens_id,
            title=edit.title,
            purpose=edit.purpose,
            context=edit.context,
            goals=edit.goals,
            constraints=edit.constraints,
            access_conditions=edit.access_conditions,
            incentives=edit.incentives,
            switching_costs=edit.switching_costs,
            information_conditions=edit.information_conditions,
            decision_criteria=edit.decision_criteria,
            excluded_inferences=edit.excluded_inferences,
            uncertainty_notes=edit.uncertainty_notes,
            input_refs=references,
            sensitive_attributes=edit.sensitive_attributes,
        )
        service.revise_lens(lens_id, replacement)
        state.status = SimulationStatus.NEEDS_REVIEW
        state.config_generated = False
        state.error = None
        manager._save_simulation_state(state)
        return jsonify({"success": True, "data": service.snapshot()})
    except ValidationError:
        return _error("decision_lens_invalid", HTTPStatus.UNPROCESSABLE_ENTITY)
    except DecisionLensReviewServiceError as exc:
        status = (
            HTTPStatus.NOT_FOUND
            if exc.code == "decision_lens_not_found"
            else HTTPStatus.UNPROCESSABLE_ENTITY
        )
        return _error(exc.code, status)
    except DecisionLensRepositoryError as exc:
        return _error(exc.code, HTTPStatus.CONFLICT)


@simulation_bp.put("/<simulation_id>/decision-lens-review")
def put_decision_lens_review(simulation_id: str):
    manager, state, service = _context(simulation_id)
    if manager is None or state is None or service is None:
        return _error("simulation_not_found", HTTPStatus.NOT_FOUND)
    try:
        body = DecisionLensReviewRequest.model_validate(request.get_json() or {})
        dispositions = tuple(
            LensDispositionV1.model_validate(item.model_dump(mode="json"))
            for item in body.dispositions
        )
        authentication_strength = (
            "application_bearer_self_attested_reviewer"
            if current_app.config.get("APP_TOKEN")
            else "development_no_auth_self_attested_reviewer"
        )
        review, status = service.submit_review(
            reviewer_assertion=body.reviewer_assertion,
            authentication_strength=authentication_strength,
            dispositions=dispositions,
        )
    except ValidationError:
        return _error("decision_lens_invalid", HTTPStatus.UNPROCESSABLE_ENTITY)
    except DecisionLensReviewServiceError as exc:
        return _error(exc.code, HTTPStatus.UNPROCESSABLE_ENTITY)
    except DecisionLensRepositoryError as exc:
        return _error(exc.code, HTTPStatus.CONFLICT)

    state.status = SimulationStatus.NEEDS_REVIEW
    state.config_generated = False
    state.error = None
    manager._save_simulation_state(state)
    snapshot = service.snapshot()
    if not status.approved:
        return jsonify({"success": True, "data": snapshot})

    task_manager = TaskManager()
    idempotency_key = (
        f"decision-lens-finalize:{simulation_id}:{review.review_sha256}"
    )
    candidate_task_id = str(uuid.uuid4())
    task_metadata = {
        "simulation_id": simulation_id,
        "review_id": review.review_id,
        "artifact_id": review.lens_artifact_id,
    }
    try:
        task_id = task_manager.create_task(
            "decision_lens_finalize",
            task_id=candidate_task_id,
            metadata=task_metadata,
            idempotency_key=idempotency_key,
            idempotency_identity={
                "simulation_id": simulation_id,
                "review_sha256": review.review_sha256,
            },
        )
    except TaskIdempotencyConflict:
        return _error("idempotency_key_conflict", HTTPStatus.CONFLICT)
    except TaskStateError:
        return _error(
            "decision_lens_task_state_unavailable",
            HTTPStatus.SERVICE_UNAVAILABLE,
        )

    if task_id == candidate_task_id:
        from ...tasks.simulation_tasks import (
            finalize_decision_lens_preparation_task,
        )

        try:
            finalize_decision_lens_preparation_task.apply_async(
                kwargs={
                    "simulation_id": simulation_id,
                    "task_id": task_id,
                },
                task_id=task_id,
            )
        except (ConnectionError, OSError, OperationalError, RuntimeError) as exc:
            public_code = "decision_lens_finalization_dispatch_unavailable"
            task_manager.fail_task(
                task_id,
                str(exc),
                public_error=public_code,
            )
            return _error(public_code, HTTPStatus.SERVICE_UNAVAILABLE, task_id=task_id)

    snapshot["task_id"] = task_id
    response = jsonify({"success": True, "data": snapshot})
    return response, HTTPStatus.ACCEPTED, {"Location": f"/api/jobs/{task_id}"}


__all__ = [
    "get_decision_lenses",
    "patch_decision_lens",
    "put_decision_lens_review",
]

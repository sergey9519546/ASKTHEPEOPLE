"""Immutable revision, review, and finalization services for decision lenses."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import Config
from ..domain.decision_lens import (
    DecisionLensArtifactV1,
    DecisionLensReviewV1,
    DecisionLensV1,
    LensDispositionV1,
)
from .decision_lens_repository import (
    DecisionLensAdmissionError,
    DecisionLensRepository,
    DecisionLensRepositoryError,
    DecisionLensReviewStatus,
)
from .simulation_manager import SimulationManager, SimulationState, SimulationStatus


class DecisionLensReviewServiceError(ValueError):
    def __init__(self, code: str, details: Any | None = None):
        self.code = code
        self.details = details
        super().__init__(code)


class DecisionLensFinalizationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class DecisionLensReviewService:
    """Create immutable revisions and hash-bound reviews."""

    def __init__(
        self,
        simulation_dir: str | Path,
        *,
        production: bool = False,
        now: Callable[[], datetime] | None = None,
        artifact_id_factory: Callable[[], str] | None = None,
        review_id_factory: Callable[[], str] | None = None,
    ):
        self.repository = DecisionLensRepository(
            simulation_dir,
            production=production,
        )
        self._now = now or (lambda: datetime.now(UTC))
        self._artifact_id_factory = artifact_id_factory or (
            lambda: f"dla_{uuid.uuid4().hex}"
        )
        self._review_id_factory = review_id_factory or (
            lambda: f"dlr_{uuid.uuid4().hex}"
        )

    def snapshot(self) -> dict[str, Any]:
        artifact = self.repository.get_current_artifact()
        review = self.repository.get_current_review()
        status = self.repository.review_status()
        return {
            "artifact": (
                artifact.model_dump(mode="json") if artifact is not None else None
            ),
            "review": review.model_dump(mode="json") if review is not None else None,
            "review_status": asdict(status),
        }

    def revise_lens(
        self,
        lens_id: str,
        replacement: DecisionLensV1,
    ) -> DecisionLensArtifactV1:
        artifact = self.repository.get_current_artifact()
        if artifact is None:
            raise DecisionLensReviewServiceError("decision_lens_review_required")
        if replacement.lens_id != lens_id:
            raise DecisionLensReviewServiceError("decision_lens_id_mismatch")

        canonical_refs = {reference.ref_id: reference for reference in artifact.input_refs}
        if any(
            canonical_refs.get(reference.ref_id) != reference
            for reference in replacement.input_refs
        ):
            raise DecisionLensReviewServiceError(
                "decision_lens_input_reference_unresolved"
            )

        lenses = list(artifact.lenses)
        try:
            index = next(
                index
                for index, existing in enumerate(lenses)
                if existing.lens_id == lens_id
            )
        except StopIteration as exc:
            raise DecisionLensReviewServiceError(
                "decision_lens_not_found"
            ) from exc
        lenses[index] = replacement
        payload = artifact.model_dump(mode="json")
        payload.update(
            {
                "artifact_id": self._artifact_id_factory(),
                "revision": artifact.revision + 1,
                "created_at": self._now(),
                "lenses": [lens.model_dump(mode="json") for lens in lenses],
                "artifact_sha256": None,
            }
        )
        try:
            revised = DecisionLensArtifactV1.model_validate(payload)
        except ValueError as exc:
            raise DecisionLensReviewServiceError("decision_lens_invalid") from exc
        return self.repository.save_artifact(revised)

    def submit_review(
        self,
        *,
        reviewer_assertion: str,
        authentication_strength: str,
        dispositions: Sequence[LensDispositionV1],
    ) -> tuple[DecisionLensReviewV1, DecisionLensReviewStatus]:
        artifact = self.repository.get_current_artifact()
        if artifact is None:
            raise DecisionLensReviewServiceError("decision_lens_review_required")
        disposition_tuple = tuple(
            LensDispositionV1.model_validate(disposition)
            for disposition in dispositions
        )
        overall_status = (
            "approved"
            if all(
                item.disposition == "approved"
                and all(
                    sensitive.disposition == "approved"
                    for sensitive in item.sensitive_attribute_dispositions
                )
                for item in disposition_tuple
            )
            else "rejected"
        )

        current = self.repository.get_current_review()
        if current is not None and self._same_review_semantics(
            current,
            artifact,
            reviewer_assertion,
            authentication_strength,
            disposition_tuple,
            overall_status,
        ):
            return current, self.repository.review_status()

        try:
            review = DecisionLensReviewV1(
                review_id=self._review_id_factory(),
                simulation_id=artifact.simulation_id,
                lens_artifact_id=artifact.artifact_id,
                lens_artifact_sha256=artifact.artifact_sha256,
                reviewed_at=self._now(),
                reviewer_assertion=reviewer_assertion,
                authentication_strength=authentication_strength,
                dispositions=disposition_tuple,
                overall_status=overall_status,
            )
        except ValueError as exc:
            raise DecisionLensReviewServiceError("decision_lens_invalid") from exc
        persisted = self.repository.save_review(review)
        return persisted, self.repository.review_status()

    @staticmethod
    def _same_review_semantics(
        review: DecisionLensReviewV1,
        artifact: DecisionLensArtifactV1,
        reviewer_assertion: str,
        authentication_strength: str,
        dispositions: tuple[LensDispositionV1, ...],
        overall_status: str,
    ) -> bool:
        return (
            review.lens_artifact_id == artifact.artifact_id
            and review.lens_artifact_sha256 == artifact.artifact_sha256
            and review.reviewer_assertion == reviewer_assertion
            and review.authentication_strength == authentication_strength
            and review.dispositions == dispositions
            and review.overall_status == overall_status
        )


def finalize_decision_lens_preparation(
    simulation_id: str,
    *,
    manager: SimulationManager | None = None,
    runtime_pipeline: Callable[..., Mapping[str, Any]] | None = None,
) -> SimulationState:
    """Recheck approval, run the adapter/config pipeline, then move to READY."""

    manager = manager or SimulationManager()
    state = manager.get_simulation(simulation_id)
    if state is None:
        raise DecisionLensFinalizationError("simulation_not_found")
    sim_dir = manager._get_simulation_dir(simulation_id)
    repository = DecisionLensRepository(sim_dir, production=not Config.DEBUG)
    try:
        repository.assert_execution_approved()
    except DecisionLensAdmissionError as exc:
        raise DecisionLensFinalizationError(exc.code) from exc
    artifact = repository.get_current_artifact()
    review = repository.get_current_review()
    if artifact is None or review is None:
        raise DecisionLensFinalizationError("decision_lens_review_required")

    pipeline = runtime_pipeline or _default_runtime_pipeline
    try:
        outcome = pipeline(
            artifact=artifact,
            review=review,
            simulation_dir=Path(sim_dir),
            state=state,
        )
        if not isinstance(outcome, Mapping):
            raise DecisionLensFinalizationError(
                "decision_lens_finalization_invalid"
            )
        preflight = outcome.get("preflight")
        if not isinstance(preflight, Mapping) or preflight.get("status") != "passed":
            raise DecisionLensFinalizationError(
                "decision_lens_preflight_failed"
            )
        repository.assert_execution_approved()
    except DecisionLensFinalizationError:
        state.status = SimulationStatus.FAILED
        state.error = "decision_lens_finalization_failed"
        manager._save_simulation_state(state)
        raise
    except (DecisionLensAdmissionError, DecisionLensRepositoryError) as exc:
        state.status = SimulationStatus.NEEDS_REVIEW
        state.error = getattr(exc, "code", "decision_lens_review_stale")
        manager._save_simulation_state(state)
        raise DecisionLensFinalizationError(state.error) from exc
    except Exception as exc:
        state.status = SimulationStatus.FAILED
        state.error = "decision_lens_finalization_failed"
        manager._save_simulation_state(state)
        raise DecisionLensFinalizationError(state.error) from exc

    state.config_generated = True
    state.config_reasoning = str(outcome.get("config_reasoning", ""))
    state.status = SimulationStatus.READY
    state.error = None
    manager._save_simulation_state(state)
    return state


def _default_runtime_pipeline(
    *,
    artifact: DecisionLensArtifactV1,
    review: DecisionLensReviewV1,
    simulation_dir: Path,
    state: SimulationState,
) -> Mapping[str, Any]:
    from .decision_lens_runtime_adapter import build_runtime_adapters
    from .simulation_artifacts import write_json
    from .simulation_config_generator import SimulationConfigGenerator
    from .simulation_preflight import run_preflight

    adapters = build_runtime_adapters(artifact, review)
    write_json(
        str(simulation_dir / "decision_lens_runtime.v1.json"),
        {
            "schema_version": "decision-lens-runtime/v1",
            "source_artifact_sha256": artifact.artifact_sha256,
            "source_review_sha256": review.review_sha256,
            "adapters": [
                adapter.model_dump(mode="json") for adapter in adapters
            ],
        },
    )
    params = SimulationConfigGenerator.generate_from_decision_lenses(
        simulation_id=state.simulation_id,
        project_id=state.project_id,
        graph_id=state.graph_id,
        simulation_requirement="Approved functional decision-lens scenario.",
        adapters=adapters,
        enable_twitter=state.enable_twitter,
        enable_reddit=state.enable_reddit,
    )
    (simulation_dir / "simulation_config.json").write_text(
        params.to_json(),
        encoding="utf-8",
    )
    return {
        "preflight": run_preflight(str(simulation_dir)),
        "config_reasoning": params.generation_reasoning,
    }


__all__ = [
    "DecisionLensFinalizationError",
    "DecisionLensReviewService",
    "DecisionLensReviewServiceError",
    "finalize_decision_lens_preparation",
]

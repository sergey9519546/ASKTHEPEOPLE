"""Immutable TRANSITION repository for decision-lens artifacts and reviews.

PostgreSQL remains the production persistence TARGET. This repository provides
atomic local semantics while the canonical persistence gate is unfinished.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.decision_lens import (
    DecisionLensArtifactV1,
    DecisionLensReviewV1,
    canonical_payload_sha256,
)

_ARTIFACT_ID = re.compile(r"^dla_[a-f0-9]{32}$")
_REVIEW_ID = re.compile(r"^dlr_[a-f0-9]{32}$")


class DecisionLensRepositoryError(ValueError):
    """Raised when immutable repository state is invalid or conflicting."""

    def __init__(self, code: str, details: Any | None = None):
        self.code = code
        self.details = details
        super().__init__(code)


class DecisionLensAdmissionError(ValueError):
    """Bounded execution-admission error safe for API translation."""

    def __init__(
        self,
        code: str,
        remediation: str,
        status: DecisionLensReviewStatus | None = None,
    ):
        self.code = code
        self.remediation = remediation
        self.status = status
        super().__init__(code)


@dataclass(frozen=True)
class DecisionLensReviewStatus:
    approved: bool
    code: str
    remediation: str
    artifact_id: str | None = None
    review_id: str | None = None


class DecisionLensRepository:
    """Persist immutable records with atomic current-record pointers."""

    def __init__(self, simulation_dir: str | Path, *, production: bool = False):
        self.simulation_dir = Path(simulation_dir).resolve()
        self.production = production
        self.artifact_dir = self.simulation_dir / "decision_lens_artifacts"
        self.review_dir = self.simulation_dir / "decision_lens_reviews"
        self.artifact_pointer = self.simulation_dir / "decision_lenses.current.json"
        self.review_pointer = (
            self.simulation_dir / "decision_lens_review.current.json"
        )

    def save_artifact(
        self, artifact: DecisionLensArtifactV1
    ) -> DecisionLensArtifactV1:
        digest = canonical_payload_sha256(artifact)
        persisted = DecisionLensArtifactV1.model_validate(
            artifact.model_copy(
                update={"artifact_sha256": digest}
            ).model_dump(mode="json")
        )
        path = self._record_path(
            self.artifact_dir,
            persisted.artifact_id,
            _ARTIFACT_ID,
        )
        _write_immutable_json(
            path,
            persisted.model_dump(mode="json"),
            conflict_code="artifact_id_conflict",
        )
        _atomic_write_json(
            self.artifact_pointer,
            {
                "artifact_id": persisted.artifact_id,
                "revision": persisted.revision,
                "artifact_sha256": digest,
                "updated_at": _now_iso(),
            },
        )
        return persisted

    def get_artifact(self, artifact_id: str) -> DecisionLensArtifactV1:
        path = self._record_path(self.artifact_dir, artifact_id, _ARTIFACT_ID)
        payload = _read_json(path, missing_code="decision_lens_artifact_missing")
        artifact = _model_validate(
            DecisionLensArtifactV1,
            payload,
            code="decision_lens_artifact_invalid",
        )
        if artifact.artifact_id != artifact_id:
            raise DecisionLensRepositoryError("decision_lens_artifact_id_mismatch")
        return artifact

    def get_current_artifact(self) -> DecisionLensArtifactV1 | None:
        try:
            pointer = _read_json(
                self.artifact_pointer,
                missing_code="decision_lens_pointer_missing",
                transient_retries=50,
            )
        except DecisionLensRepositoryError as exc:
            if exc.code != "decision_lens_pointer_missing":
                raise
            return None
        _require_exact_keys(
            pointer,
            {"artifact_id", "revision", "artifact_sha256", "updated_at"},
            "decision_lens_pointer_invalid",
        )
        artifact = self.get_artifact(str(pointer["artifact_id"]))
        if (
            pointer["revision"] != artifact.revision
            or pointer["artifact_sha256"] != artifact.artifact_sha256
        ):
            raise DecisionLensRepositoryError("decision_lens_pointer_mismatch")
        return artifact

    def save_review(self, review: DecisionLensReviewV1) -> DecisionLensReviewV1:
        artifact = self.get_current_artifact()
        if artifact is None:
            raise DecisionLensRepositoryError("decision_lens_artifact_missing")
        if review.simulation_id != artifact.simulation_id:
            raise DecisionLensRepositoryError("review_simulation_mismatch")
        if review.lens_artifact_id != artifact.artifact_id:
            raise DecisionLensRepositoryError("review_artifact_mismatch")
        if review.lens_artifact_sha256 != artifact.artifact_sha256:
            raise DecisionLensRepositoryError("review_artifact_hash_mismatch")

        lens_by_id = {lens.lens_id: lens for lens in artifact.lenses}
        disposition_by_id = {
            disposition.lens_id: disposition for disposition in review.dispositions
        }
        if set(disposition_by_id) != set(lens_by_id):
            raise DecisionLensRepositoryError("review_lens_set_mismatch")

        for lens_id, lens in lens_by_id.items():
            expected = {item.attribute for item in lens.sensitive_attributes}
            actual = {
                item.attribute
                for item in disposition_by_id[
                    lens_id
                ].sensitive_attribute_dispositions
            }
            if actual != expected:
                raise DecisionLensRepositoryError(
                    "sensitive_attribute_review_set_mismatch",
                    {"lens_id": lens_id},
                )

        digest = canonical_payload_sha256(review)
        persisted = DecisionLensReviewV1.model_validate(
            review.model_copy(update={"review_sha256": digest}).model_dump(
                mode="json"
            )
        )
        path = self._record_path(self.review_dir, persisted.review_id, _REVIEW_ID)
        _write_immutable_json(
            path,
            persisted.model_dump(mode="json"),
            conflict_code="review_id_conflict",
        )
        _atomic_write_json(
            self.review_pointer,
            {
                "review_id": persisted.review_id,
                "lens_artifact_id": persisted.lens_artifact_id,
                "lens_artifact_sha256": persisted.lens_artifact_sha256,
                "review_sha256": digest,
                "updated_at": _now_iso(),
            },
        )
        return persisted

    def get_review(self, review_id: str) -> DecisionLensReviewV1:
        path = self._record_path(self.review_dir, review_id, _REVIEW_ID)
        payload = _read_json(path, missing_code="decision_lens_review_missing")
        review = _model_validate(
            DecisionLensReviewV1,
            payload,
            code="decision_lens_review_invalid",
        )
        if review.review_id != review_id:
            raise DecisionLensRepositoryError("decision_lens_review_id_mismatch")
        return review

    def get_current_review(self) -> DecisionLensReviewV1 | None:
        try:
            pointer = _read_json(
                self.review_pointer,
                missing_code="decision_lens_review_pointer_missing",
                transient_retries=50,
            )
        except DecisionLensRepositoryError as exc:
            if exc.code != "decision_lens_review_pointer_missing":
                raise
            return None
        _require_exact_keys(
            pointer,
            {
                "review_id",
                "lens_artifact_id",
                "lens_artifact_sha256",
                "review_sha256",
                "updated_at",
            },
            "decision_lens_review_pointer_invalid",
        )
        review = self.get_review(str(pointer["review_id"]))
        if (
            pointer["lens_artifact_id"] != review.lens_artifact_id
            or pointer["lens_artifact_sha256"] != review.lens_artifact_sha256
            or pointer["review_sha256"] != review.review_sha256
        ):
            raise DecisionLensRepositoryError(
                "decision_lens_review_pointer_mismatch"
            )
        return review

    def review_status(self) -> DecisionLensReviewStatus:
        artifact = self.get_current_artifact()
        if artifact is None:
            return DecisionLensReviewStatus(
                approved=False,
                code="decision_lens_review_required",
                remediation="regenerate_decision_lenses",
            )
        review = self.get_current_review()
        if review is None:
            return DecisionLensReviewStatus(
                approved=False,
                code="decision_lens_review_required",
                remediation="review_current_decision_lenses",
                artifact_id=artifact.artifact_id,
            )
        if (
            review.lens_artifact_id != artifact.artifact_id
            or review.lens_artifact_sha256 != artifact.artifact_sha256
        ):
            return DecisionLensReviewStatus(
                approved=False,
                code="decision_lens_review_stale",
                remediation="review_current_decision_lenses",
                artifact_id=artifact.artifact_id,
                review_id=review.review_id,
            )
        if review.overall_status != "approved":
            return DecisionLensReviewStatus(
                approved=False,
                code="decision_lens_review_required",
                remediation="revise_or_approve_decision_lenses",
                artifact_id=artifact.artifact_id,
                review_id=review.review_id,
            )
        if (
            self.production
            and review.authentication_strength
            == "development_no_auth_self_attested_reviewer"
        ):
            return DecisionLensReviewStatus(
                approved=False,
                code="decision_lens_review_required",
                remediation="authenticate_and_review_decision_lenses",
                artifact_id=artifact.artifact_id,
                review_id=review.review_id,
            )
        return DecisionLensReviewStatus(
            approved=True,
            code="decision_lens_review_approved",
            remediation="none",
            artifact_id=artifact.artifact_id,
            review_id=review.review_id,
        )

    def assert_execution_approved(self) -> DecisionLensReviewStatus:
        status = self.review_status()
        if not status.approved:
            raise DecisionLensAdmissionError(
                status.code,
                status.remediation,
                status,
            )
        return status

    def _record_path(
        self,
        directory: Path,
        record_id: str,
        pattern: re.Pattern[str],
    ) -> Path:
        if pattern.fullmatch(record_id) is None:
            raise DecisionLensRepositoryError("decision_lens_record_id_invalid")
        directory.mkdir(parents=True, exist_ok=True)
        path = (directory / f"{record_id}.json").resolve()
        if path.parent != directory.resolve():
            raise DecisionLensRepositoryError("decision_lens_record_path_invalid")
        return path


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_immutable_json(
    path: Path,
    payload: dict[str, Any],
    *,
    conflict_code: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json_bytes(payload)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        try:
            existing = path.read_bytes()
        except OSError as read_exc:
            raise DecisionLensRepositoryError(conflict_code) from read_exc
        if existing != encoded:
            raise DecisionLensRepositoryError(conflict_code) from exc
        return

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        _replace_pointer(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _replace_pointer(temp_name: str, path: Path) -> None:
    """Replace a pointer atomically, tolerating brief Windows read locks."""

    for attempt in range(200):
        try:
            os.replace(temp_name, path)
            return
        except PermissionError:
            if attempt == 199:
                raise
            time.sleep(0.005)


def _read_json(
    path: Path,
    *,
    missing_code: str,
    transient_retries: int = 0,
) -> dict[str, Any]:
    for attempt in range(transient_retries + 1):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            break
        except (OSError, json.JSONDecodeError) as exc:
            if attempt < transient_retries:
                time.sleep(0.005)
                continue
            if isinstance(exc, FileNotFoundError):
                raise DecisionLensRepositoryError(missing_code) from exc
            raise DecisionLensRepositoryError(
                "decision_lens_repository_corrupt"
            ) from exc
    if not isinstance(payload, dict):
        raise DecisionLensRepositoryError("decision_lens_repository_corrupt")
    return payload


def _model_validate(model_type, payload: dict[str, Any], *, code: str):
    try:
        return model_type.model_validate(payload)
    except Exception as exc:
        raise DecisionLensRepositoryError(code) from exc


def _require_exact_keys(
    payload: dict[str, Any], expected: set[str], code: str
) -> None:
    if set(payload) != expected:
        raise DecisionLensRepositoryError(code)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "DecisionLensAdmissionError",
    "DecisionLensRepository",
    "DecisionLensRepositoryError",
    "DecisionLensReviewStatus",
]

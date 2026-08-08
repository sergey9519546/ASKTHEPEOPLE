"""Registered, fail-closed generation of functional decision lenses."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..domain.decision_lens import (
    DecisionLensArtifactV1,
    DecisionLensV1,
    InputReferenceV1,
    PromptRecordV1,
)
from ..domain.decision_workspace import TruthBundle
from ..utils.llm_client import LLMClient


class RegistryPromptClient(Protocol):
    def chat_with_registry_prompt(self, **kwargs: Any) -> dict[str, Any]: ...


class DecisionLensGenerationError(ValueError):
    """Bounded generation failure safe for task-level classification."""

    def __init__(self, code: str, details: Any | None = None):
        self.code = code
        self.details = details
        super().__init__(code)


class _DecisionLensOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lenses: tuple[DecisionLensV1, ...] = Field(min_length=4, max_length=8)
    truth_fields: TruthBundle


class DecisionLensGenerator:
    """Generate one reviewable artifact under the registered prompt contract."""

    def __init__(
        self,
        llm_client: RegistryPromptClient | None = None,
        *,
        now: Callable[[], datetime] | None = None,
        artifact_id_factory: Callable[[], str] | None = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self._now = now or (lambda: datetime.now(UTC))
        self._artifact_id_factory = artifact_id_factory or (
            lambda: f"dla_{uuid.uuid4().hex}"
        )

    def generate(
        self,
        *,
        simulation_id: str,
        revision: int,
        simulation_requirement: str,
        input_references: Sequence[InputReferenceV1],
        allowed_reference_ids: set[str],
        context_records: Sequence[Mapping[str, Any]],
    ) -> DecisionLensArtifactV1:
        references = tuple(
            InputReferenceV1.model_validate(reference)
            for reference in input_references
        )
        reference_by_id = {reference.ref_id: reference for reference in references}
        if len(reference_by_id) != len(references):
            raise DecisionLensGenerationError("decision_lens_input_reference_duplicate")
        if not references or not set(reference_by_id).issubset(allowed_reference_ids):
            raise DecisionLensGenerationError(
                "decision_lens_input_reference_unresolved"
            )

        context_ref_ids = {
            str(record.get("ref_id"))
            for record in context_records
            if isinstance(record, Mapping) and record.get("ref_id")
        }
        if not set(reference_by_id).issubset(context_ref_ids):
            raise DecisionLensGenerationError(
                "decision_lens_context_reference_missing"
            )

        result = self.llm_client.chat_with_registry_prompt(
            prompt_id="decision_lens_generation",
            prompt_version="1.0.0",
            simulation_requirement=simulation_requirement,
            input_reference_allowlist=json.dumps(
                [reference.model_dump(mode="json") for reference in references],
                ensure_ascii=False,
                sort_keys=True,
            ),
            untrusted_context=json.dumps(
                list(context_records),
                ensure_ascii=False,
                sort_keys=True,
            ),
            temperature=0.0,
            max_tokens=8192,
            complexity="complex",
        )
        self._require_clean_truth_audit(result)

        try:
            output = _DecisionLensOutput.model_validate(result.get("data"))
        except (TypeError, ValidationError, ValueError) as exc:
            raise DecisionLensGenerationError(
                "decision_lens_output_invalid"
            ) from exc
        if output.truth_fields != TruthBundle.synthetic():
            raise DecisionLensGenerationError(
                "decision_lens_truth_contract_failed"
            )

        for lens in output.lenses:
            for reference in lens.input_refs:
                canonical = reference_by_id.get(reference.ref_id)
                if (
                    reference.ref_id not in allowed_reference_ids
                    or canonical is None
                    or reference != canonical
                ):
                    raise DecisionLensGenerationError(
                        "decision_lens_input_reference_unresolved"
                    )

        try:
            prompt_record = PromptRecordV1.model_validate(
                {
                    "prompt_id": result.get("prompt_id"),
                    "prompt_version": result.get("prompt_version"),
                    "prompt_sha256": result.get("prompt_sha256"),
                    "model": result.get("model"),
                    "system_prompt_sha256": result.get("system_prompt_sha256"),
                    "user_prompt_sha256": result.get("user_prompt_sha256"),
                    "context_prompt_sha256s": result.get(
                        "context_prompt_sha256s", []
                    ),
                    "output_sha256": result.get("output_sha256"),
                    "temperature": result.get("temperature"),
                    "max_tokens": result.get("max_tokens"),
                    "structured_output": result.get("structured_output"),
                    "tools_bound": result.get("tools_bound"),
                }
            )
            return DecisionLensArtifactV1(
                artifact_id=self._artifact_id_factory(),
                simulation_id=simulation_id,
                revision=revision,
                created_at=self._now(),
                prompt_record=prompt_record,
                input_refs=references,
                lenses=output.lenses,
                truth_fields=output.truth_fields,
            )
        except (TypeError, ValidationError, ValueError) as exc:
            raise DecisionLensGenerationError(
                "decision_lens_output_invalid"
            ) from exc

    @staticmethod
    def _require_clean_truth_audit(result: Mapping[str, Any]) -> None:
        audit = result.get("truth_audit")
        if not isinstance(audit, Mapping):
            raise DecisionLensGenerationError(
                "decision_lens_truth_contract_failed"
            )
        prohibited = audit.get("prohibited_term_hits")
        missing = audit.get("required_keyword_misses")
        if (
            not isinstance(prohibited, list)
            or not isinstance(missing, list)
            or prohibited
            or missing
        ):
            raise DecisionLensGenerationError(
                "decision_lens_truth_contract_failed",
                {
                    "prohibited_term_hits": prohibited,
                    "required_keyword_misses": missing,
                },
            )


__all__ = ["DecisionLensGenerationError", "DecisionLensGenerator"]

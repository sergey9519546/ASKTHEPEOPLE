"""Domain contracts for decision workspaces and functional lenses."""

from .actor_context import ActorContext, ActorType, AuthenticationMethod
from .authorization import (
    FOUNDATION_POLICY_VERSION,
    FoundationCapability,
    MembershipRole,
    derive_foundation_capabilities,
)
from .decision_lens import (
    DecisionLensArtifactV1,
    DecisionLensReviewV1,
    DecisionLensV1,
    DecisionLensValidationError,
    InputReferenceV1,
    LensDispositionV1,
    LensStatus,
    PromptRecordV1,
    SensitiveAttributeDispositionV1,
    SensitiveAttributeV1,
    canonical_payload_bytes,
    canonical_payload_sha256,
)
from .identifiers import (
    PublicIdKind,
    new_public_id,
    new_uuid7,
    validate_legacy_project_public_id,
)

__all__ = [
    "FOUNDATION_POLICY_VERSION",
    "ActorContext",
    "ActorType",
    "AuthenticationMethod",
    "DecisionLensArtifactV1",
    "DecisionLensReviewV1",
    "DecisionLensV1",
    "DecisionLensValidationError",
    "FoundationCapability",
    "InputReferenceV1",
    "LensDispositionV1",
    "LensStatus",
    "MembershipRole",
    "PromptRecordV1",
    "PublicIdKind",
    "SensitiveAttributeDispositionV1",
    "SensitiveAttributeV1",
    "canonical_payload_bytes",
    "canonical_payload_sha256",
    "derive_foundation_capabilities",
    "new_public_id",
    "new_uuid7",
    "validate_legacy_project_public_id",
]

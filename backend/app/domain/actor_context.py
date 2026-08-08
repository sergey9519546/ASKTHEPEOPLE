"""Immutable server-derived authorization context for one tenant scope."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Self
from uuid import RFC_4122, UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .authorization import (
    FoundationCapability,
    MembershipRole,
    derive_foundation_capabilities,
)


class ActorType(str, Enum):
    USER = "USER"
    SERVICE = "SERVICE"


class AuthenticationMethod(str, Enum):
    OIDC = "OIDC"
    LEGACY_DEV = "LEGACY_DEV"


class ActorContext(BaseModel):
    """Frozen identity, scope, and policy grants derived by trusted services."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    actor_type: ActorType
    actor_id: UUID
    user_id: UUID | None
    organization_id: UUID
    workspace_id: UUID
    project_id: UUID | None
    organization_role: MembershipRole
    workspace_role: MembershipRole
    capabilities: frozenset[FoundationCapability]
    authentication_method: AuthenticationMethod
    request_id: UUID
    authenticated_at: datetime

    @field_validator(
        "actor_id",
        "user_id",
        "organization_id",
        "workspace_id",
        "project_id",
    )
    @classmethod
    def require_physical_uuid7(cls, value: UUID | None) -> UUID | None:
        if value is None:
            return value
        if value.version != 7 or value.variant != RFC_4122:
            raise ValueError("physical_id_must_be_uuid7")
        return value

    @field_validator("authenticated_at")
    @classmethod
    def require_timezone_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authenticated_at_must_be_timezone_aware")
        return value

    @model_validator(mode="after")
    def require_server_scope_invariants(self) -> Self:
        if self.actor_type is ActorType.USER and self.user_id != self.actor_id:
            raise ValueError("user_actor_id_mismatch")
        if self.actor_type is ActorType.SERVICE and self.user_id is not None:
            raise ValueError("service_actor_must_not_have_user_id")

        expected_capabilities = derive_foundation_capabilities(
            organization_role=self.organization_role,
            workspace_role=self.workspace_role,
        )
        if self.capabilities != expected_capabilities:
            raise ValueError("capabilities_do_not_match_policy")
        return self

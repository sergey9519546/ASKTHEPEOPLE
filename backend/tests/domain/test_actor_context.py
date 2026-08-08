from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError


def test_actor_context_is_frozen_strict_and_server_scoped() -> None:
    from app.domain import (
        ActorContext,
        ActorType,
        AuthenticationMethod,
        FoundationCapability,
        MembershipRole,
        derive_foundation_capabilities,
        new_uuid7,
    )

    actor_id = new_uuid7(clock=lambda: 1_700_000_000, randbits=lambda _: 1)
    organization_id = new_uuid7(clock=lambda: 1_700_000_001, randbits=lambda _: 2)
    workspace_id = new_uuid7(clock=lambda: 1_700_000_002, randbits=lambda _: 3)
    project_id = new_uuid7(clock=lambda: 1_700_000_003, randbits=lambda _: 4)
    capabilities = derive_foundation_capabilities(
        organization_role=MembershipRole.OWNER,
        workspace_role=MembershipRole.VIEWER,
    )
    values: dict[str, object] = {
        "actor_type": ActorType.USER,
        "actor_id": actor_id,
        "user_id": actor_id,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "project_id": project_id,
        "organization_role": MembershipRole.OWNER,
        "workspace_role": MembershipRole.VIEWER,
        "capabilities": capabilities,
        "authentication_method": AuthenticationMethod.OIDC,
        "request_id": uuid4(),
        "authenticated_at": datetime(2026, 8, 8, 18, 0, tzinfo=UTC),
    }

    actor = ActorContext(**values)

    assert actor.user_id == actor.actor_id
    assert actor.capabilities == capabilities
    assert FoundationCapability.PROJECT_UPDATE not in actor.capabilities

    with pytest.raises(ValidationError, match="frozen_instance"):
        actor.workspace_id = organization_id  # type: ignore[misc]
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ActorContext(**values, requested_workspace_id=workspace_id)
    with pytest.raises(ValidationError, match="is_instance_of"):
        ActorContext(**{**values, "actor_id": str(actor_id)})
    with pytest.raises(ValidationError, match="user_actor_id_mismatch"):
        ActorContext(**{**values, "user_id": workspace_id})
    with pytest.raises(
        ValidationError, match="invalid_organization_membership_role"
    ):
        ActorContext(**{**values, "organization_role": MembershipRole.EDITOR})
    with pytest.raises(ValidationError, match="capabilities_do_not_match_policy"):
        ActorContext(
            **{
                **values,
                "capabilities": frozenset(
                    capability
                    for capability in capabilities
                    if capability is not FoundationCapability.PROJECT_READ
                ),
            }
        )
    with pytest.raises(ValidationError, match="physical_id_must_be_uuid7"):
        ActorContext(**{**values, "workspace_id": uuid4()})
    with pytest.raises(
        ValidationError, match="authenticated_at_must_be_timezone_aware"
    ):
        ActorContext(
            **{
                **values,
                "authenticated_at": datetime(
                    2026, 8, 8, 18, 0, tzinfo=UTC
                ).replace(tzinfo=None),
            }
        )

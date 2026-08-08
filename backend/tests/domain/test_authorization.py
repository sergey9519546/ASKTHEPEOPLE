from itertools import product

import pytest


def test_role_policy_cartesian_matrix_is_closed() -> None:
    from app.domain.authorization import (
        FOUNDATION_POLICY_VERSION,
        FoundationCapability,
        MembershipRole,
        derive_foundation_capabilities,
    )

    assert FOUNDATION_POLICY_VERSION == "foundation-policy/v1"
    assert {role.value for role in MembershipRole} == {
        "OWNER",
        "ADMIN",
        "EDITOR",
        "REVIEWER",
        "VIEWER",
        "SECURITY",
    }
    assert {capability.value for capability in FoundationCapability} == {
        "organization:read",
        "organization:manage",
        "organization_membership:read",
        "organization_membership:manage",
        "workspace:read",
        "workspace:manage",
        "workspace_membership:read",
        "workspace_membership:manage",
        "project:read",
        "project:create",
        "project:update",
        "project:archive",
        "audit:read",
    }

    def capabilities(*values: str) -> frozenset[FoundationCapability]:
        return frozenset(FoundationCapability(value) for value in values)

    organization_grants = {
        MembershipRole.OWNER: capabilities(
            "organization:read",
            "organization:manage",
            "organization_membership:read",
            "organization_membership:manage",
            "workspace:read",
            "workspace:manage",
        ),
        MembershipRole.ADMIN: capabilities(
            "organization:read",
            "organization:manage",
            "organization_membership:read",
            "organization_membership:manage",
            "workspace:read",
            "workspace:manage",
        ),
        MembershipRole.SECURITY: capabilities(
            "organization:read",
            "organization_membership:read",
            "workspace:read",
            "audit:read",
        ),
    }
    workspace_grants = {
        MembershipRole.OWNER: capabilities(
            "workspace:read",
            "workspace:manage",
            "workspace_membership:read",
            "workspace_membership:manage",
            "project:read",
            "project:create",
            "project:update",
            "project:archive",
            "audit:read",
        ),
        MembershipRole.ADMIN: capabilities(
            "workspace:read",
            "workspace:manage",
            "workspace_membership:read",
            "workspace_membership:manage",
            "project:read",
            "project:create",
            "project:update",
            "project:archive",
            "audit:read",
        ),
        MembershipRole.EDITOR: capabilities(
            "workspace:read",
            "workspace_membership:read",
            "project:read",
            "project:create",
            "project:update",
        ),
        MembershipRole.REVIEWER: capabilities("workspace:read", "project:read"),
        MembershipRole.VIEWER: capabilities("workspace:read", "project:read"),
        MembershipRole.SECURITY: capabilities(
            "workspace:read",
            "workspace_membership:read",
            "project:read",
            "audit:read",
        ),
    }

    for organization_role, workspace_role in product(
        organization_grants, workspace_grants
    ):
        assert derive_foundation_capabilities(
            organization_role=organization_role,
            workspace_role=workspace_role,
        ) == organization_grants[organization_role] | workspace_grants[workspace_role]

    with pytest.raises(ValueError, match="invalid_organization_membership_role"):
        derive_foundation_capabilities(
            organization_role=MembershipRole.EDITOR,
            workspace_role=MembershipRole.VIEWER,
        )
    with pytest.raises(TypeError, match="membership_roles_must_be_enum_members"):
        derive_foundation_capabilities(
            organization_role="OWNER",  # type: ignore[arg-type]
            workspace_role=MembershipRole.VIEWER,
        )

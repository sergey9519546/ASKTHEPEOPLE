"""Closed foundation roles, capabilities, and policy derivation."""

from __future__ import annotations

from enum import Enum

FOUNDATION_POLICY_VERSION = "foundation-policy/v1"


class MembershipRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"
    SECURITY = "SECURITY"


class FoundationCapability(str, Enum):
    ORGANIZATION_READ = "organization:read"
    ORGANIZATION_MANAGE = "organization:manage"
    ORGANIZATION_MEMBERSHIP_READ = "organization_membership:read"
    ORGANIZATION_MEMBERSHIP_MANAGE = "organization_membership:manage"
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_MANAGE = "workspace:manage"
    WORKSPACE_MEMBERSHIP_READ = "workspace_membership:read"
    WORKSPACE_MEMBERSHIP_MANAGE = "workspace_membership:manage"
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_ARCHIVE = "project:archive"
    AUDIT_READ = "audit:read"


_ORGANIZATION_GRANTS: dict[MembershipRole, frozenset[FoundationCapability]] = {
    MembershipRole.OWNER: frozenset(
        {
            FoundationCapability.ORGANIZATION_READ,
            FoundationCapability.ORGANIZATION_MANAGE,
            FoundationCapability.ORGANIZATION_MEMBERSHIP_READ,
            FoundationCapability.ORGANIZATION_MEMBERSHIP_MANAGE,
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.WORKSPACE_MANAGE,
        }
    ),
    MembershipRole.ADMIN: frozenset(
        {
            FoundationCapability.ORGANIZATION_READ,
            FoundationCapability.ORGANIZATION_MANAGE,
            FoundationCapability.ORGANIZATION_MEMBERSHIP_READ,
            FoundationCapability.ORGANIZATION_MEMBERSHIP_MANAGE,
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.WORKSPACE_MANAGE,
        }
    ),
    MembershipRole.SECURITY: frozenset(
        {
            FoundationCapability.ORGANIZATION_READ,
            FoundationCapability.ORGANIZATION_MEMBERSHIP_READ,
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.AUDIT_READ,
        }
    ),
}

_WORKSPACE_GRANTS: dict[MembershipRole, frozenset[FoundationCapability]] = {
    MembershipRole.OWNER: frozenset(
        {
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.WORKSPACE_MANAGE,
            FoundationCapability.WORKSPACE_MEMBERSHIP_READ,
            FoundationCapability.WORKSPACE_MEMBERSHIP_MANAGE,
            FoundationCapability.PROJECT_READ,
            FoundationCapability.PROJECT_CREATE,
            FoundationCapability.PROJECT_UPDATE,
            FoundationCapability.PROJECT_ARCHIVE,
            FoundationCapability.AUDIT_READ,
        }
    ),
    MembershipRole.ADMIN: frozenset(
        {
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.WORKSPACE_MANAGE,
            FoundationCapability.WORKSPACE_MEMBERSHIP_READ,
            FoundationCapability.WORKSPACE_MEMBERSHIP_MANAGE,
            FoundationCapability.PROJECT_READ,
            FoundationCapability.PROJECT_CREATE,
            FoundationCapability.PROJECT_UPDATE,
            FoundationCapability.PROJECT_ARCHIVE,
            FoundationCapability.AUDIT_READ,
        }
    ),
    MembershipRole.EDITOR: frozenset(
        {
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.WORKSPACE_MEMBERSHIP_READ,
            FoundationCapability.PROJECT_READ,
            FoundationCapability.PROJECT_CREATE,
            FoundationCapability.PROJECT_UPDATE,
        }
    ),
    MembershipRole.REVIEWER: frozenset(
        {
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.PROJECT_READ,
        }
    ),
    MembershipRole.VIEWER: frozenset(
        {
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.PROJECT_READ,
        }
    ),
    MembershipRole.SECURITY: frozenset(
        {
            FoundationCapability.WORKSPACE_READ,
            FoundationCapability.WORKSPACE_MEMBERSHIP_READ,
            FoundationCapability.PROJECT_READ,
            FoundationCapability.AUDIT_READ,
        }
    ),
}


def derive_foundation_capabilities(
    *,
    organization_role: MembershipRole,
    workspace_role: MembershipRole,
) -> frozenset[FoundationCapability]:
    """Return policy-v1 grants for one organization/workspace membership pair."""

    if (
        type(organization_role) is not MembershipRole
        or type(workspace_role) is not MembershipRole
    ):
        raise TypeError("membership_roles_must_be_enum_members")
    if organization_role not in _ORGANIZATION_GRANTS:
        raise ValueError("invalid_organization_membership_role")
    return _ORGANIZATION_GRANTS[organization_role] | _WORKSPACE_GRANTS[workspace_role]

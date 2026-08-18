"""Dev/test-only installer for the server-derived actor context.

The canonical source-persistence boundary reads ``g.actor_context``
(``app/api/routes/source_routes.py``), but the production OIDC/membership
resolver behind ADR-0009 does not exist yet. Without an installer, every
canonical source operation returns 503 ``tenant_context_unavailable`` the
moment Supabase persistence is configured, and the repository wiring can never
be exercised end-to-end.

This module installs a *stable* LEGACY_DEV SERVICE scope so repeated requests
resolve the same organization/workspace/project — a requirement for the
persistence seam to round-trip (create in one request, look up in the next).
It is strictly gated:

- ``Config.DEV_ACTOR_CONTEXT_ENABLED`` must be true; and
- ``Config.DEBUG`` must be true (production never installs a synthetic scope).

``Config.validate()`` additionally refuses ``DEV_ACTOR_CONTEXT_ENABLED=true``
when ``DEBUG`` is false, so a misconfigured deployment fails startup rather
than silently bypassing tenant derivation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from flask import Flask, g

from ..config import Config
from ..domain.actor_context import ActorContext, ActorType, AuthenticationMethod
from ..domain.authorization import MembershipRole, derive_foundation_capabilities
from ..domain.identifiers import new_uuid7

# Versioned namespace so a scope can be rotated deliberately without silently
# changing the ids a developer's local data was written under.
_DEV_SCOPE_NAMESPACE = "askthepeople-dev-actor-scope-v1"


def _derive_scope_uuid7(salt: str) -> UUID:
    """Deterministic, valid UUIDv7 derived from a fixed dev namespace.

    Reuses ``new_uuid7``'s trusted entropy seams so the bit layout and
    validation stay in one place; only the entropy source is fixed.
    """
    digest = hashlib.sha256(
        f"{_DEV_SCOPE_NAMESPACE}:{salt}".encode("utf-8")
    ).digest()
    unix_ms = int.from_bytes(digest[:6], "big")
    rand_value = int.from_bytes(digest[6:16], "big") & ((1 << 74) - 1)
    return new_uuid7(
        clock=lambda: unix_ms / 1000.0,
        randbits=lambda _bits: rand_value,
    )


def build_dev_actor_context() -> ActorContext:
    """Construct the stable dev/test single-tenant scope."""
    role = MembershipRole.OWNER
    return ActorContext(
        actor_type=ActorType.SERVICE,
        actor_id=_derive_scope_uuid7("actor"),
        user_id=None,
        organization_id=_derive_scope_uuid7("organization"),
        workspace_id=_derive_scope_uuid7("workspace"),
        project_id=_derive_scope_uuid7("project"),
        organization_role=role,
        workspace_role=role,
        capabilities=derive_foundation_capabilities(
            organization_role=role,
            workspace_role=role,
        ),
        authentication_method=AuthenticationMethod.LEGACY_DEV,
        request_id=new_uuid7(),
        authenticated_at=datetime.now(timezone.utc),
    )


def install_dev_actor_context(app: Flask) -> None:
    """Register a before_request hook that installs the dev/test scope.

    Reads the flags at request time (not registration time) so tests that
    monkeypatch ``Config`` after ``create_app()`` behave as expected, matching
    how the source routes read their own feature flags.
    """

    @app.before_request
    def _install_dev_actor_context() -> None:
        if not (Config.DEBUG and Config.DEV_ACTOR_CONTEXT_ENABLED):
            return None
        if getattr(g, "actor_context", None) is not None:
            # A real (or test-injected) context wins; never overwrite it.
            return None
        g.actor_context = build_dev_actor_context()
        return None

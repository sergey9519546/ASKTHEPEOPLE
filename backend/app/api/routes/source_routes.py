"""Source ingestion V1 API routes (Task 4 Checkpoint 4B).

Controlled TXT source ingestion and review, gated behind
``SOURCE_INGESTION_V1_ENABLED``. The domain kernel
(``app/domain/source_ingestion.py``) defines the closed 11-state lifecycle,
candidate review, and deletion fencing. These routes expose that domain as
HTTP endpoints — **but every mutating endpoint returns 503 UNAVAILABLE
while the feature flag is off.**

The capability endpoint (``GET /api/sources/v1/capabilities``) is always
available so the frontend can discover what the server supports without
guessing. It reports ``source_review=UNAVAILABLE`` and an empty format list
when the flag is disabled.

Per Task 4 §5: "The domain kernel and ports may land behind the disabled
flag before the production blockers are complete. Their existence must not
change ``source_review=UNAVAILABLE``, expose a production route, or support
a security claim."
"""

from flask import g, request

from ...config import Config
from ...domain.source_ingestion import (
    CandidateDisposition,
    SourceIngestionState,
    SourceCommandKind,
)
from ...utils.logger import get_logger
from ..presentation import error_response, present

logger = get_logger('askthepeople.api.routes.source')


def _source_ingestion_enabled() -> bool:
    """Whether the V1 source-ingestion boundary is live."""
    return bool(
        Config.SOURCE_INGESTION_V1_ENABLED
        and Config.SOURCE_INGESTION_V1_FORMATS
    )


def _persistence_configured() -> bool:
    """Whether the canonical Supabase store is available for source operations."""
    try:
        from ...services.supabase_client import is_storage_configured
        return is_storage_configured()
    except Exception:
        return False


def _unavailable():
    """Standard 503 returned by every mutating route while the flag is off."""
    return error_response(
        "source_ingestion_unavailable",
        status=503,
        message=(
            "Source ingestion V1 is not enabled. The ingestion boundary "
            "(quarantine, scanning, isolated parsing, review) is not yet "
            "production-ready."
        ),
        source_review="UNAVAILABLE",
    )


def _actor_context():
    """Return the trusted request scope, if the auth layer installed one."""
    from ...domain.actor_context import ActorContext

    context = getattr(g, "actor_context", None)
    return context if isinstance(context, ActorContext) else None


def _tenant_context_unavailable():
    return error_response(
        "tenant_context_unavailable",
        status=503,
        message="Canonical source operations require a server-derived tenant and actor context.",
    )


def _actor_context_ready(context) -> bool:
    """Whether the trusted context contains the complete source scope."""
    return context is not None and context.project_id is not None


def _record_in_actor_scope(record, context) -> bool:
    """Check every canonical source scope dimension against trusted context."""
    return _actor_context_ready(context) and all(
        record.get(field) == getattr(context, field)
        for field in ("organization_id", "workspace_id", "project_id")
    )


# --- Capability advertisement (always available) --- #


def register_source_routes(simulation_bp):
    """Register the V1 source-ingestion routes on the simulation blueprint.

    A separate blueprint would be cleaner, but the existing app structure
    registers everything through ``simulation_bp`` / the blueprints in
    ``api/__init__.py``. These routes sit under ``/api/sources/v1/`` so they
    are visually distinct from the legacy ``/api/sources/fetch`` path.
    """

    @simulation_bp.route('/sources/v1/capabilities', methods=['GET'])
    def get_source_capabilities():
        """Advertise what source-ingestion formats the server supports.

        Always available (even when the flag is off) so the frontend can
        render the correct state without guessing. Reports
        ``source_review=UNAVAILABLE`` when disabled.
        """
        enabled = _source_ingestion_enabled()
        return present({
            "source_review": "AVAILABLE" if enabled else "UNAVAILABLE",
            "enabled": enabled,
            "formats": Config.SOURCE_INGESTION_V1_FORMATS if enabled else [],
            "max_file_size_bytes": 10 * 1024 * 1024 if enabled else 0,
            "review_required": True,
        })

    @simulation_bp.route('/sources/v1/upload-intent', methods=['POST'])
    def create_upload_intent():
        """Request a short-lived upload intent for a source file.

        Two distinct refusals, both deliberate:

        - 503 UNAVAILABLE while `SOURCE_INGESTION_V1_ENABLED` is off. The
          feature is switched off, which is a different fact from "the feature
          is on and unfinished".
        - 501 NOT IMPLEMENTED when the flag is on but persistence is not
          configured. The previous behaviour returned 200 with every field
          null, which is the most misleading shape available: it reported that
          an upload had been prepared and handed back nothing usable. No
          frontend code calls this route in that mode.

        With persistence configured the handler creates a real source and
        version record and reaches the server-derived tenant gate, which is
        genuine behaviour covered by `tests/test_actor_context_installer.py`.
        The `upload_url` and `object_key` fields remain null because object
        storage is the unfinished part of the boundary (ADR-0012); they are not
        removed, because a client that already handles direct upload will want
        them once storage exists.
        """
        if not _source_ingestion_enabled():
            return _unavailable()

        data = request.get_json(silent=True) or {}
        filename = (data.get("filename") or "").strip()
        content_type = (data.get("content_type") or "").strip()
        byte_length = data.get("byte_length")

        if not filename:
            return error_response("filename_required", status=400)

        # Format gate: only enabled formats are accepted.
        import os
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in Config.SOURCE_INGESTION_V1_FORMATS:
            return error_response(
                "format_not_enabled",
                status=422,
                allowed_formats=Config.SOURCE_INGESTION_V1_FORMATS,
            )

        if not isinstance(byte_length, int) or byte_length <= 0:
            return error_response("invalid_byte_length", status=400)

        # When persistence is configured, create a real source + version record.
        if _persistence_configured():
            actor_context = _actor_context()
            if not _actor_context_ready(actor_context):
                return _tenant_context_unavailable()
            from ...services.source_repository import SourceRepository
            try:
                source = SourceRepository.create_source(
                    organization_id=actor_context.organization_id,
                    workspace_id=actor_context.workspace_id,
                    project_id=actor_context.project_id,
                    display_name=filename,
                    created_by_actor_id=actor_context.actor_id,
                )
                version = SourceRepository.create_source_version(
                    source_id=source["id"],
                    organization_id=source["organization_id"],
                    workspace_id=source["workspace_id"],
                    project_id=source["project_id"],
                    version_number=1,
                    state=SourceIngestionState.UPLOADING,
                    original_filename_display=filename,
                    declared_media_type=content_type or "text/plain",
                    created_by_actor_id=source["created_by_actor_id"],
                )
                return present({
                    "source_id": source["public_id"],
                    "source_version_id": version["public_id"],
                    "state": version["state"],
                    "format": ext,
                    "byte_length": byte_length,
                    "content_type": content_type,
                    "upload_url": None,  # signed URL from object storage (§5 blocker)
                    "object_key": None,  # server-generated key (§5 blocker)
                    "expires_in_seconds": 300,
                })
            except Exception as exc:
                logger.error("Source creation failed: %s", exc, exc_info=True)
                return error_response("source_creation_failed", status=500)

        # Flag on, no persistence: this used to return 200 with every field null.
        return error_response(
            "upload_intent_not_implemented",
            status=501,
            detail=(
                "Direct upload needs canonical persistence and object storage. "
                "Neither is available here, so no upload intent can be prepared."
            ),
        )

    @simulation_bp.route('/sources/v1/<source_id>/status', methods=['GET'])
    def get_source_status(source_id: str):
        """Get the current review state of a source.

        503 UNAVAILABLE while the flag is off. When persistence is configured,
        looks up the source via SourceRepository.
        """
        if not _source_ingestion_enabled():
            return _unavailable()

        if not _persistence_configured():
            return error_response(
                "source_persistence_not_configured",
                status=501,
                message=(
                    "Set USE_SUPABASE_PERSISTENCE=true and DATABASE_URL to "
                    "enable source status lookup."
                ),
            )

        actor_context = _actor_context()
        if not _actor_context_ready(actor_context):
            return _tenant_context_unavailable()

        from ...services.source_repository import SourceRepository
        source = SourceRepository.get_source_by_public_id(
            source_id,
            organization_id=actor_context.organization_id,
            workspace_id=actor_context.workspace_id,
            project_id=actor_context.project_id,
        )
        if not source or not _record_in_actor_scope(source, actor_context):
            return error_response("source_not_found", status=404)

        # Load the current version for its state.
        version_id = source.get("current_version_id")
        version = None
        if version_id:
            version = SourceRepository.get_source_version(
                version_id,
                organization_id=actor_context.organization_id,
                workspace_id=actor_context.workspace_id,
                project_id=actor_context.project_id,
            )
            if (
                not version
                or version.get("source_id") != source.get("id")
                or not _record_in_actor_scope(version, actor_context)
            ):
                return error_response("source_version_not_found", status=404)

        return present({
            "source_id": source["public_id"],
            "display_name": source.get("display_name"),
            "version": source.get("version"),
            "current_state": version["state"] if version else "UPLOADING",
            "current_version_number": version.get("version_number") if version else None,
            "source_review": "AVAILABLE",
        })

    @simulation_bp.route('/sources/v1/<source_id>/review', methods=['POST'])
    def submit_source_review(source_id: str):
        """Submit a human review disposition for a source's candidates.

        Accepts a disposition (ACCEPTED_UNCHANGED, REVISED, EXCLUDED) and
        optional revised text. 503 UNAVAILABLE while the flag is off.
        """
        if not _source_ingestion_enabled():
            return _unavailable()

        data = request.get_json(silent=True) or {}
        disposition = (data.get("disposition") or "").strip().upper()

        try:
            CandidateDisposition(disposition)
        except ValueError:
            return error_response(
                "invalid_disposition",
                status=422,
                allowed=[d.value for d in CandidateDisposition],
            )

        if not _persistence_configured():
            return error_response(
                "source_persistence_not_configured",
                status=501,
                message=(
                    "Set USE_SUPABASE_PERSISTENCE=true and DATABASE_URL to "
                    "enable source review."
                ),
            )

        actor_context = _actor_context()
        if not _actor_context_ready(actor_context):
            return _tenant_context_unavailable()

        # When persistence is configured, load the source and update its
        # version state through the review disposition. The domain kernel's
        # candidate-review logic (accept/revise/exclude) is pure and tested;
        # this is the persistence seam.
        from ...services.source_repository import SourceRepository
        source = SourceRepository.get_source_by_public_id(
            source_id,
            organization_id=actor_context.organization_id,
            workspace_id=actor_context.workspace_id,
            project_id=actor_context.project_id,
        )
        if not source or not _record_in_actor_scope(source, actor_context):
            return error_response("source_not_found", status=404)

        version_id = source.get("current_version_id")
        if not version_id:
            return error_response("source_version_not_found", status=404)

        version = SourceRepository.get_source_version(
            version_id,
            organization_id=actor_context.organization_id,
            workspace_id=actor_context.workspace_id,
            project_id=actor_context.project_id,
        )
        if (
            not version
            or version.get("source_id") != source.get("id")
            or not _record_in_actor_scope(version, actor_context)
        ):
            return error_response("source_version_not_found", status=404)

        # Map the disposition to the next source-version state.
        # ACCEPTED_SOURCE_CONDITION → READY; REVISED → READY; EXCLUDED → REJECTED.
        _DISPOSITION_TO_STATE = {
            CandidateDisposition.ACCEPTED_SOURCE_CONDITION: SourceIngestionState.READY,
            CandidateDisposition.REVISED_USER_CONDITION: SourceIngestionState.READY,
            CandidateDisposition.EXCLUDED: SourceIngestionState.REJECTED,
            CandidateDisposition.PENDING: SourceIngestionState.NEEDS_REVIEW,
            CandidateDisposition.REPORTED_SUSPICIOUS: SourceIngestionState.FLAGGED,
        }
        new_state = _DISPOSITION_TO_STATE.get(
            CandidateDisposition(disposition), SourceIngestionState.NEEDS_REVIEW
        )

        updated = SourceRepository.update_source_version_state(
            version_id,
            new_state=new_state,
            expected_version=version["version"],
        )
        return present({
            "source_id": source_id,
            "version_id": version["public_id"],
            "new_state": updated["state"],
            "disposition": disposition,
        })

    @simulation_bp.route('/sources/v1/<source_id>/deletion', methods=['POST'])
    def request_source_deletion(source_id: str):
        """Request deletion of a source and all its derivatives.

        503 UNAVAILABLE while the flag is off.
        """
        if not _source_ingestion_enabled():
            return _unavailable()

        # Deletion requires the deletion ledger and worker (§5 blocker).
        return error_response(
            "deletion_ledger_not_wired",
            status=501,
            message=(
                "Source deletion requires the durable deletion ledger and "
                "worker (ADR-0012, Task 4 §5). The domain fencing logic is "
                "implemented; the persistence + worker layer is not."
            ),
        )

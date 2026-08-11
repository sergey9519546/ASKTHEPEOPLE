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

from flask import jsonify, request

from ...config import Config
from ...domain.source_ingestion import (
    CandidateDisposition,
    SourceIngestionState,
    SourceCommandKind,
)
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.routes.source')


def _source_ingestion_enabled() -> bool:
    """Whether the V1 source-ingestion boundary is live."""
    return bool(
        Config.SOURCE_INGESTION_V1_ENABLED
        and Config.SOURCE_INGESTION_V1_FORMATS
    )


def _unavailable():
    """Standard 503 returned by every mutating route while the flag is off."""
    return jsonify({
        "success": False,
        "error": "source_ingestion_unavailable",
        "message": (
            "Source ingestion V1 is not enabled. The ingestion boundary "
            "(quarantine, scanning, isolated parsing, review) is not yet "
            "production-ready."
        ),
        "source_review": "UNAVAILABLE",
    }), 503


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
        return jsonify({
            "success": True,
            "data": {
                "source_review": "AVAILABLE" if enabled else "UNAVAILABLE",
                "enabled": enabled,
                "formats": Config.SOURCE_INGESTION_V1_FORMATS if enabled else [],
                "max_file_size_bytes": 10 * 1024 * 1024 if enabled else 0,
                "review_required": True,
            },
        })

    @simulation_bp.route('/sources/v1/upload-intent', methods=['POST'])
    def create_upload_intent():
        """Request a short-lived upload intent for a source file.

        Returns the intended object key, expiry, and the source's initial
        state (UPLOADING). 503 UNAVAILABLE while the flag is off.
        """
        if not _source_ingestion_enabled():
            return _unavailable()

        data = request.get_json(silent=True) or {}
        filename = (data.get("filename") or "").strip()
        content_type = (data.get("content_type") or "").strip()
        byte_length = data.get("byte_length")

        if not filename:
            return jsonify({"success": False, "error": "filename_required"}), 400

        # Format gate: only enabled formats are accepted.
        import os
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in Config.SOURCE_INGESTION_V1_FORMATS:
            return jsonify({
                "success": False,
                "error": "format_not_enabled",
                "allowed_formats": Config.SOURCE_INGESTION_V1_FORMATS,
            }), 422

        if not isinstance(byte_length, int) or byte_length <= 0:
            return jsonify({"success": False, "error": "invalid_byte_length"}), 400

        # The actual object-store intent (signed URL, key generation) is a
        # Task 4 §5 production blocker. The route returns the structured
        # intent shape the domain expects; the storage adapter fills it in
        # when that blocker lands.
        return jsonify({
            "success": True,
            "data": {
                "source_id": None,  # assigned by the persistence layer
                "state": SourceIngestionState.UPLOADING.value,
                "format": ext,
                "byte_length": byte_length,
                "content_type": content_type,
                "upload_url": None,  # signed URL from object storage (§5 blocker)
                "object_key": None,  # server-generated key (§5 blocker)
                "expires_in_seconds": 300,
            },
        })

    @simulation_bp.route('/sources/v1/<source_id>/status', methods=['GET'])
    def get_source_status(source_id: str):
        """Get the current review state of a source.

        503 UNAVAILABLE while the flag is off.
        """
        if not _source_ingestion_enabled():
            return _unavailable()

        # Without the persistence layer (§5 blocker) we cannot resolve a real
        # source record. Return a transparent not-implemented rather than a
        # fabricated record.
        return jsonify({
            "success": False,
            "error": "source_persistence_not_wired",
            "message": (
                "The canonical source persistence layer (ADR-0012) is not "
                "wired. Source status lookup requires the PostgreSQL source "
                "aggregate."
            ),
        }), 501

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
            return jsonify({
                "success": False,
                "error": "invalid_disposition",
                "allowed": [d.value for d in CandidateDisposition],
            }), 422

        # The candidate-review domain logic (accept_candidate_unchanged,
        # revise_candidate, candidate_review_is_finalizable) is implemented
        # in the domain kernel. Wiring it to a persistence-backed source
        # record is a §5 production blocker.
        return jsonify({
            "success": False,
            "error": "source_persistence_not_wired",
            "message": (
                "Candidate review requires the persistence-backed source "
                "aggregate. The domain kernel is implemented; the "
                "persistence adapter is not yet wired."
            ),
        }), 501

    @simulation_bp.route('/sources/v1/<source_id>/deletion', methods=['POST'])
    def request_source_deletion(source_id: str):
        """Request deletion of a source and all its derivatives.

        503 UNAVAILABLE while the flag is off.
        """
        if not _source_ingestion_enabled():
            return _unavailable()

        # Deletion requires the deletion ledger and worker (§5 blocker).
        return jsonify({
            "success": False,
            "error": "deletion_ledger_not_wired",
            "message": (
                "Source deletion requires the durable deletion ledger and "
                "worker (ADR-0012, Task 4 §5). The domain fencing logic is "
                "implemented; the persistence + worker layer is not."
            ),
        }), 501

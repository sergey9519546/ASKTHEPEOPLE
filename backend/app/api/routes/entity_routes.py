"""
Entity Query API Routes (Decomposed from simulation.py)
"""

from flask import request

from ...config import Config
from ...services.claim_boundary import (
    graph_record_disclosure,
    synthetic_output_disclosure,
)
from ...services.graph_association import (
    GraphAssociationError,
    resolve_project_graph,
)
from ...services.zep_entity_reader import ZepEntityReader
from ...utils.logger import get_logger
from ...utils.response import truth_metadata
from .. import simulation_bp
from ..presentation import error_response, present

logger = get_logger('askthepeople.api.routes.entity')


def _resolve_requested_graph(graph_id: str):
    try:
        association = resolve_project_graph(
            request.args.get("project_id"),
            graph_id,
        )
    except GraphAssociationError as exc:
        return None, error_response(exc.code, status=exc.status_code)
    return association.graph_id, None


@simulation_bp.route('/entities/<graph_id>', methods=['GET'])
def get_graph_entities(graph_id: str):
    """
    Get all entities in the graph (filtered)
    
    Only return nodes matching predefined entity types.
    """
    canonical_graph_id, association_error = _resolve_requested_graph(graph_id)
    if association_error is not None:
        return association_error

    if not Config.ZEP_API_KEY:
        return error_response("graph_dependency_unavailable", status=503)

    try:
        
        entity_types_param = request.args.get('entity_types')
        target_entity_types = None
        if entity_types_param:
            target_entity_types = [t.strip() for t in entity_types_param.split(',') if t.strip()]
        
        reader = ZepEntityReader()
        enrich = request.args.get('enrich', 'true').lower() == 'true'

        result = reader.filter_defined_entities(
            graph_id=canonical_graph_id,
            defined_entity_types=target_entity_types,
            enrich_with_edges=enrich
        )
        
        entities = result.entities

        return present(
            {
                "graph_id": canonical_graph_id,
                "entities": entities,
                "count": len(entities)
            },
            extra={
                "disclosure": synthetic_output_disclosure(),
                "record_provenance": graph_record_disclosure(),
                **truth_metadata(),
            },
        )

    except Exception as exc:
        logger.warning(
            "graph entity read unavailable exception_type=%s",
            type(exc).__name__,
        )
        return error_response("graph_entity_read_unavailable", status=503)


@simulation_bp.route('/entities/<graph_id>/<entity_uuid>', methods=['GET'])
def get_entity_detail(graph_id: str, entity_uuid: str):
    """Get entity details by UUID."""
    canonical_graph_id, association_error = _resolve_requested_graph(graph_id)
    if association_error is not None:
        return association_error

    if not Config.ZEP_API_KEY:
        return error_response("graph_dependency_unavailable", status=503)

    try:
        reader = ZepEntityReader()
        entity = reader.get_entity_with_context(canonical_graph_id, entity_uuid)

        if not entity:
            return error_response("entity_not_found", status=404)

        return present(
            entity,
            extra={
                "disclosure": synthetic_output_disclosure(),
                "record_provenance": graph_record_disclosure(),
                **truth_metadata(),
            },
        )

    except Exception as exc:
        logger.warning(
            "graph entity detail unavailable exception_type=%s",
            type(exc).__name__,
        )
        return error_response("graph_entity_read_unavailable", status=503)


@simulation_bp.route('/entities/<graph_id>/by-type/<entity_type>', methods=['GET'])
def get_entities_by_type(graph_id: str, entity_type: str):
    """Get entities by entity type."""
    canonical_graph_id, association_error = _resolve_requested_graph(graph_id)
    if association_error is not None:
        return association_error

    if not Config.ZEP_API_KEY:
        return error_response("graph_dependency_unavailable", status=503)

    try:
        reader = ZepEntityReader()
        entities = reader.get_entities_by_type(canonical_graph_id, entity_type)

        return present(
            {
                "graph_id": canonical_graph_id,
                "entity_type": entity_type,
                "entities": entities,
                "count": len(entities)
            },
            extra={
                "disclosure": synthetic_output_disclosure(),
                "record_provenance": graph_record_disclosure(),
                # This sibling never carried truth_metadata, even before the
                # decomposition. It returns the same class of graph records as
                # the two routes above, so it carries the same contract.
                **truth_metadata(),
            },
        )

    except Exception as exc:
        logger.warning(
            "graph entities-by-type unavailable exception_type=%s",
            type(exc).__name__,
        )
        return error_response("graph_entity_read_unavailable", status=503)

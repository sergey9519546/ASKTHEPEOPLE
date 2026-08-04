"""
Entity Query API Routes (Decomposed from simulation.py)
"""

from flask import jsonify, request
from .. import simulation_bp
from ...config import Config
from ...services.claim_boundary import (
    graph_record_disclosure,
    synthetic_output_disclosure,
)
from ...services.zep_entity_reader import ZepEntityReader
from ...utils.logger import get_logger
from ...utils.response import truth_metadata

logger = get_logger('askthepeople.api.routes.entity')


@simulation_bp.route('/entities/<graph_id>', methods=['GET'])
def get_graph_entities(graph_id: str):
    """
    Get all entities in the graph (filtered)
    
    Only return nodes matching predefined entity types.
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 400
        
        entity_types_param = request.args.get('entity_types')
        target_entity_types = None
        if entity_types_param:
            target_entity_types = [t.strip() for t in entity_types_param.split(',') if t.strip()]
        
        reader = ZepEntityReader()
        enrich = request.args.get('enrich', 'true').lower() == 'true'

        result = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=target_entity_types,
            enrich_with_edges=enrich
        )
        
        entities = result.entities

        return jsonify({
            "success": True,
            "data": {
                "graph_id": graph_id,
                "entities": entities,
                "count": len(entities)
            },
            "disclosure": synthetic_output_disclosure(),
            "record_provenance": graph_record_disclosure(),
            **truth_metadata(),
        })

    except Exception as e:
        logger.error(f"Failed to get graph entities for {graph_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/entities/<graph_id>/<entity_uuid>', methods=['GET'])
def get_entity_detail(graph_id: str, entity_uuid: str):
    """Get entity details by UUID."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 400

        reader = ZepEntityReader()
        entity = reader.get_entity_with_context(graph_id, entity_uuid)

        if not entity:
            return jsonify({
                "success": False,
                "error": f"Entity not found: {entity_uuid}"
            }), 404

        return jsonify({
            "success": True,
            "data": entity,
            "disclosure": synthetic_output_disclosure(),
            "record_provenance": graph_record_disclosure(),
            **truth_metadata(),
        })

    except Exception as e:
        logger.error(f"Failed to get entity detail for {entity_uuid}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/entities/<graph_id>/by-type/<entity_type>', methods=['GET'])
def get_entities_by_type(graph_id: str, entity_type: str):
    """Get entities by entity type."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 400

        reader = ZepEntityReader()
        entities = reader.get_entities_by_type(graph_id, entity_type)

        return jsonify({
            "success": True,
            "data": {
                "graph_id": graph_id,
                "entity_type": entity_type,
                "entities": entities,
                "count": len(entities)
            },
            "disclosure": synthetic_output_disclosure(),
            "record_provenance": graph_record_disclosure(),
            # This sibling never carried truth_metadata, even before the
            # decomposition. It returns the same class of graph records as the
            # two routes above, so it carries the same contract.
            **truth_metadata(),
        })

    except Exception as e:
        logger.error(f"Failed to get entities by type {entity_type}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

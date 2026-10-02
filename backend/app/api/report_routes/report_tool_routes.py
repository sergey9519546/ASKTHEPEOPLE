"""Graph query tools exposed alongside reports.

Moved out of app/api/report.py by exec-plan T25 (ADR-0011).
"""

from flask import jsonify, request

from ...config import Config

from ...services.claim_boundary import (
    graph_record_disclosure, synthetic_output_disclosure,
)

from ...services.graph_association import (
    GraphAssociationError, resolve_project_graph,
)

from ...services.zep_tools import ZepToolsService

from ...utils.input_policy import (
    GRAPH_QUERY_MAX, InputPolicyError, bounded_integer, bounded_text,
)

from .. import limiter
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.report')



@limiter.limit(Config.RATELIMIT_LLM_MEDIUM)
def search_graph_tool():
    """
    Graph search tool interface (for debugging)
    
    Request (JSON):
        {
            "project_id": "proj_xxxx",
            "graph_id": "atp_xxxx",
            "query": "Search query",
            "limit": 10
        }
    """
    try:
        data = request.get_json() or {}
        
        try:
            query = bounded_text(
                data.get('query'),
                field="query",
                max_length=GRAPH_QUERY_MAX,
                required=True,
            )
            limit = bounded_integer(
                data.get('limit', 10),
                field="limit",
                minimum=1,
                maximum=50,
            )
        except InputPolicyError as exc:
            return jsonify({
                "success": False,
                "error": exc.code,
                "message": exc.message,
            }), 400

        association = resolve_project_graph(
            data.get('project_id'),
            data.get('graph_id'),
        )
        graph_id = association.graph_id
        
        tools = ZepToolsService()
        result = tools.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit
        )
        search_payload = result.to_dict()
        search_payload["records"] = [
            graph_record_disclosure(record)
            for record in search_payload.get("facts", [])
        ]
        search_payload["edges"] = [
            {
                **edge,
                **graph_record_disclosure(edge.get("fact", "")),
            }
            for edge in search_payload.get("edges", [])
        ]
        search_payload["facts_deprecated"] = True
        search_payload.update(graph_record_disclosure())

        return jsonify({
            "success": True,
            "data": search_payload,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except GraphAssociationError as exc:
        return jsonify({"success": False, "error": exc.code}), exc.status_code
    except Exception as exc:
        logger.warning(
            "graph search unavailable exception_type=%s",
            type(exc).__name__,
        )
        return jsonify({
            "success": False,
            "error": "graph_search_unavailable",
        }), 503


def get_graph_statistics_tool():
    """
    Graph statistics tool interface (for debugging)
    
    Request (JSON):
        {
            "project_id": "proj_xxxx",
            "graph_id": "atp_xxxx"
        }
    """
    try:
        data = request.get_json() or {}
        
        association = resolve_project_graph(
            data.get('project_id'),
            data.get('graph_id'),
        )
        graph_id = association.graph_id
        
        tools = ZepToolsService()
        result = tools.get_graph_statistics(graph_id)
        
        return jsonify({
            "success": True,
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except GraphAssociationError as exc:
        return jsonify({"success": False, "error": exc.code}), exc.status_code
    except Exception as exc:
        logger.warning(
            "graph statistics unavailable exception_type=%s",
            type(exc).__name__,
        )
        return jsonify({
            "success": False,
            "error": "graph_statistics_unavailable",
        }), 503

ROUTES = (
    ("/tools/search", ['POST'], "search_graph_tool"),
    ("/tools/statistics", ['POST'], "get_graph_statistics_tool"),
)

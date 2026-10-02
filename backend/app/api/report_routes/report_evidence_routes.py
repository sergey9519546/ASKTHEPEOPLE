"""Post-hoc run records served for a report. Never citations or evidence.

Moved out of app/api/report.py by exec-plan T25 (ADR-0011).
"""

import traceback

from flask import jsonify

from ...services.claim_boundary import synthetic_output_disclosure

from ...services.report_agent import ReportManager

from ...services.report_evidence import load_report_evidence

from ...utils.response import truth_metadata

from ...utils.safe_path import SafePathError
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.report')



def get_report_evidence(report_id: str):
    """Get post-hoc keyword-related run records, never citations or evidence."""
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return jsonify({
                "success": False,
                "error": f"Report does not exist: {report_id}"
            }), 404

        report_dir = ReportManager._get_report_folder(report_id)
        evidence = load_report_evidence(report_dir)

        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "count": len(evidence),
                "selection_method": "post_hoc_keyword_overlap",
                "relationship": "related_example_not_citation",
                "evidence": evidence
            },
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get report evidence: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

ROUTES = (
    ("/<report_id>/related-records", ['GET'], "get_report_evidence"),
    ("/<report_id>/evidence", ['GET'], "get_report_evidence"),
)

"""Report downloads and server-rendered exports (PDF, CSV, executive).

Moved out of app/api/report.py by exec-plan T25 (ADR-0011).
"""

import os

import traceback

from flask import jsonify, send_file

from ...services.export_service import (
    CSVExporter, ExecutiveExporter, PDFGenerator,
)

from ...services.report_agent import ReportManager

from ...services.zep_tools import ZepToolsService

from ...utils.safe_path import SafePathError
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.report')



def download_report(report_id: str):
    """
    Download report (Markdown format)
    
    Return Markdown file
    """
    try:
        report = ReportManager.get_report(report_id)
        
        if not report:
            return jsonify({
                "success": False,
                "error": f"Report does not exist: {report_id}"
            }), 404
        
        md_path = ReportManager._get_report_markdown_path(report_id)
        
        if not os.path.exists(md_path):
            # If the MD file doesn't exist, send it from memory using BytesIO
            from io import BytesIO
            md_bytes = report.markdown_content.encode('utf-8')
            return send_file(
                BytesIO(md_bytes),
                as_attachment=True,
                download_name=f"{report_id}.md",
                mimetype='text/markdown'
            )
        
        return send_file(
            md_path,
            as_attachment=True,
            download_name=f"{report_id}.md"
        )

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to download report: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def export_report_pdf(report_id: str):
    """
    Export report as PDF (Bauhaus Style)
    """
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report does not exist: {report_id}"}), 404
            
        generator = PDFGenerator()
        pdf_bytes = generator.generate(report.to_dict())
        
        from io import BytesIO
        return send_file(
            BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f"ATP_REPORT_{report_id}.pdf",
            mimetype='application/pdf'
        )
    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to export PDF: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def export_report_csv(report_id: str):
    """
    Export simulation graph data as CSV
    """
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report does not exist: {report_id}"}), 404
            
        graph_id = report.graph_id
        if not graph_id:
            return jsonify({"success": False, "error": "No graph associated with this report"}), 400
            
        zep = ZepToolsService()
        exporter = CSVExporter(zep)
        csv_data = exporter.export_graph(graph_id)
        csv_bytes = csv_data.encode('utf-8')
        
        from io import BytesIO
        return send_file(
            BytesIO(csv_bytes),
            as_attachment=True,
            download_name=f"ATP_DATA_{report_id}.csv",
            mimetype='text/csv'
        )
    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to export CSV: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def export_report_executive(report_id: str):
    """
    Export report as executive HTML presentation slide deck
    """
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report does not exist: {report_id}"}), 404
            
        metrics_data = None
        if report.simulation_id:
            from ...services.validation_engine import ValidationEngine
            metrics_data = ValidationEngine.load_metrics(report.simulation_id)

        exporter = ExecutiveExporter()
        html_deck = exporter.generate_html_deck(report.to_dict(), metrics_data=metrics_data)
        
        from io import BytesIO
        return send_file(
            BytesIO(html_deck.encode('utf-8')),
            as_attachment=True,
            download_name=f"ATP_EXECUTIVE_PRESENTATION_{report_id}.html",
            mimetype='text/html'
        )
    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to export executive presentation: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

ROUTES = (
    ("/<report_id>/download", ['GET'], "download_report"),
    ("/<report_id>/export/pdf", ['GET'], "export_report_pdf"),
    ("/<report_id>/export/csv", ['GET'], "export_report_csv"),
    ("/<report_id>/export/executive", ['GET'], "export_report_executive"),
)

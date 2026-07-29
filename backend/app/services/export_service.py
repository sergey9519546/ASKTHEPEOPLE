"""
Export Service
Handles PDF and CSV generation for simulation reports and data.
"""

import os
import io
import html
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from typing import List, Dict, Any, Optional

from ..config import Config
from ..utils.logger import get_logger
from .claim_boundary import (
    GRAPH_RECORD_INTERPRETATION,
    SYNTHETIC_OUTPUT_DISCLOSURE_TEXT,
    synthetic_output_disclosure,
)
from .zep_tools import ZepToolsService

logger = get_logger('askthepeople.export_service')

# Compatibility name retained for callers; content comes from the shared
# product-truth contract.
SYNTHETIC_DISCLOSURE = SYNTHETIC_OUTPUT_DISCLOSURE_TEXT
UNVERIFIED_GRAPH_ORIGIN = "GRAPH_RECORD_ORIGIN_UNVERIFIED"
UNVERIFIED_GRAPH_INTERPRETATION = GRAPH_RECORD_INTERPRETATION


def _spreadsheet_safe(value: Any) -> Any:
    """Neutralize strings spreadsheet programs may execute as formulas."""
    if not isinstance(value, str):
        return value
    visible = value.lstrip()
    if visible.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + value
    return value


def _safe_csv_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {key: _spreadsheet_safe(value) for key, value in record.items()}
        for record in records
    ]


class BauhausPDF(FPDF):
    """Bauhaus-themed PDF generator using FPDF2"""
    
    def header(self):
        # Bauhaus geometric accent
        self.set_fill_color(0, 0, 0) # Black
        self.rect(0, 0, 10, 297, "F") # Left bar
        
        # ATP Logo/Header
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 5)
        self.cell(10, 10, "ATP", align="C")
        
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(15, 10)
        self.cell(0, 0, "ASKTHEPEOPLE // SIMULATION_REPORT", align="L")
        
        # Right aligned page number
        self.set_xy(-30, 10)
        self.cell(20, 0, f"PAGE {self.page_no()}", align="R")
        
        self.ln(20)

    def footer(self):
        # Bottom geometric line
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.5)
        self.line(15, 285, 200, 285)
        
        self.set_y(-15)
        self.set_font("Courier", "I", 8)
        self.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Confidential", align="C")

class PDFGenerator:
    """Converts Markdown reports to Bauhaus-styled PDFs"""
    
    def __init__(self):
        self.pdf = BauhausPDF()
        self.pdf.set_auto_page_break(auto=True, margin=20)
        self.pdf.add_page()
        
    def generate(self, report_data: Dict[str, Any]) -> bytes:
        """
        Convert report data to PDF bytes
        
        Args:
            report_data: Report dictionary containing title, summary, and markdown_content
            
        Returns:
            PDF file content as bytes
        """
        title = report_data.get('title', 'Simulation Report')
        summary = report_data.get('summary', '')
        content = report_data.get('markdown_content', '')
        
        # 1. Title Page Segment
        self.pdf.set_font("Helvetica", "B", 24)
        self.pdf.set_xy(20, 40)
        self.pdf.multi_cell(0, 12, title.upper())
        
        self.pdf.ln(10)
        self.pdf.set_draw_color(255, 51, 31) # ATP Red
        self.pdf.set_line_width(2)
        self.pdf.line(20, self.pdf.get_y(), 100, self.pdf.get_y())
        self.pdf.ln(15)

        # Truth status travels with the exported file.
        self.pdf.set_fill_color(229, 194, 29)
        self.pdf.set_text_color(17, 21, 19)
        self.pdf.set_font("Helvetica", "B", 9)
        self.pdf.multi_cell(0, 7, SYNTHETIC_DISCLOSURE, fill=True)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(8)
        
        # 2. Summary Block
        if summary:
            self.pdf.set_fill_color(229, 255, 0) # ATP Yellow
            self.pdf.set_font("Helvetica", "B", 10)
            self.pdf.cell(0, 8, " EXECUTIVE_SUMMARY", fill=True, ln=True)
            self.pdf.ln(2)
            self.pdf.set_font("Helvetica", "", 11)
            self.pdf.multi_cell(0, 6, summary)
            self.pdf.ln(10)
            
        # 3. Content Breakdown
        self._parse_markdown(content)
        
        return self.pdf.output()

    def _parse_markdown(self, md_content: str):
        """Simple Markdown to FPDF parser for restricted report structure"""
        lines = md_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                self.pdf.ln(4)
                continue
                
            # Headers (Simulation headers are usually # and ##)
            if line.startswith('### '):
                self.pdf.set_font("Helvetica", "B", 14)
                self.pdf.set_text_color(0, 38, 254) # ATP Blue
                self.pdf.cell(0, 10, line[4:].upper(), ln=True)
                self.pdf.set_text_color(0, 0, 0)
                self.pdf.ln(2)
            elif line.startswith('## '):
                self.pdf.set_font("Helvetica", "B", 16)
                self.pdf.set_fill_color(0, 0, 0)
                self.pdf.set_text_color(255, 255, 255)
                self.pdf.cell(0, 10, f" {line[3:].upper()}", fill=True, ln=True)
                self.pdf.set_text_color(0, 0, 0)
                self.pdf.ln(4)
            elif line.startswith('# '):
                # Major title already handled or skip if inside body
                pass
                
            # Blockquotes (Citations)
            elif line.startswith('> '):
                self.pdf.set_font("Courier", "I", 10)
                self.pdf.set_fill_color(249, 249, 249) # Light Gray
                self.pdf.set_draw_color(0, 0, 0)
                self.pdf.set_line_width(0.5)
                
                # Draw left border for quote
                curr_x = self.pdf.get_x()
                curr_y = self.pdf.get_y()
                
                # Get text without quote marker
                text = line[2:].strip()
                # Simple multi-cell for quote
                self.pdf.set_x(curr_x + 5)
                self.pdf.multi_cell(0, 6, text, border=0, fill=True)
                
                # Vertical line on the left
                new_y = self.pdf.get_y()
                self.pdf.line(curr_x + 2, curr_y, curr_x + 2, new_y)
                self.pdf.ln(2)
                
            # Bold content **text**
            elif '**' in line:
                self.pdf.set_font("Helvetica", "B", 11)
                text = line.replace('**', '')
                self.pdf.multi_cell(0, 6, text)
                
            # Default text
            else:
                self.pdf.set_font("Helvetica", "", 11)
                self.pdf.multi_cell(0, 6, line)

class CSVExporter:
    """Export graph records without upgrading unknown provenance to evidence."""
    
    def __init__(self, zep_service: ZepToolsService):
        self.zep = zep_service
        
    def export_graph(self, graph_id: str) -> str:
        """
        Export graph nodes and edges to a CSV string
        
        Args:
            graph_id: Zep Graph ID
            
        Returns:
            CSV formatted string
        """
        logger.info(f"Exporting graph data to CSV: {graph_id}")
        
        # 1. Fetch nodes
        nodes = self.zep.get_all_nodes(graph_id)
        # 2. Fetch edges
        edges = self.zep.get_all_edges(graph_id)
        
        # 3. Build a unified set of provenance-unverified graph records.
        data = []
        
        for edge in edges:
            data.append({
                "Type": "RELATIONSHIP",
                "Source": edge.source_node_name or edge.source_node_uuid,
                "Target": edge.target_node_name or edge.target_node_uuid,
                "Action": edge.name,
                "Graph_Record": edge.fact,
                "Time": edge.valid_at or edge.created_at,
                "Status": "EXPIRED" if edge.is_expired else "ACTIVE",
                "Record_Origin": UNVERIFIED_GRAPH_ORIGIN,
                "Permitted_Interpretation": UNVERIFIED_GRAPH_INTERPRETATION,
                "Human_Respondents": 0,
                "Causal_Evidence": False,
                "Calibration": "NOT_CALIBRATED",
            })
            
        for node in nodes:
            entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entity")
            data.append({
                "Type": f"ENTITY_{entity_type.upper()}",
                "Source": node.name,
                "Target": "",
                "Action": "SUMMARY",
                "Graph_Record": node.summary,
                "Time": "",
                "Status": "ACTIVE",
                "Record_Origin": UNVERIFIED_GRAPH_ORIGIN,
                "Permitted_Interpretation": UNVERIFIED_GRAPH_INTERPRETATION,
                "Human_Respondents": 0,
                "Causal_Evidence": False,
                "Calibration": "NOT_CALIBRATED",
            })
            
        df = pd.DataFrame(_safe_csv_records(data))
        
        # Generate CSV string
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    def export_survey_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Convert model-generated profile responses into a disclosed CSV string.

        The method name is retained for API compatibility; the returned records
        are not responses from human participants.
        
        Args:
            results: List of dicts, each containing agent_name, profession, and answer.
            
        Returns:
            CSV formatted string.
        """
        if not results:
            return (
                "agent_name,profession,answer,response_origin,"
                "human_respondents,population_represented,"
                "public_opinion_status,forecast_status,causal_evidence,"
                "calibration\n"
            )

        disclosure = synthetic_output_disclosure()
        disclosed_results = [
            {
                **result,
                "response_origin": "MODEL_GENERATED",
                "human_respondents": disclosure["human_respondents"],
                "population_represented": disclosure["population_represented"],
                "public_opinion_status": disclosure["public_opinion_status"],
                "forecast_status": disclosure["forecast_status"],
                "causal_evidence": False,
                "calibration": "NOT_CALIBRATED",
            }
            for result in results
        ]
        df = pd.DataFrame(_safe_csv_records(disclosed_results))
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()


class ExecutiveExporter:
    """Generates an executive presentation slide deck (HTML format) with metrics visualization."""

    def generate_html_deck(self, report_data: Dict[str, Any], metrics_data: Optional[Dict[str, Any]] = None) -> str:
        title = html.escape(str(report_data.get("title", "Executive Simulation Brief")), quote=True)
        summary = html.escape(
            str(report_data.get("summary", "No executive summary provided.")),
            quote=True,
        )
        sections = report_data.get("sections", [])
        
        pol_q = html.escape(str(metrics_data.get("polarization_index", "N/A") if metrics_data else "N/A"), quote=True)
        echo_score = html.escape(str(metrics_data.get("echo_chamber_score", "N/A") if metrics_data else "N/A"), quote=True)
        gini = html.escape(str(metrics_data.get("engagement_gini", "N/A") if metrics_data else "N/A"), quote=True)

        slides_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
    <title>{title} — Executive Presentation</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #111513; color: #f1eee6; margin: 0; padding: 40px; }}
        .disclosure {{ background: #e5c21d; color: #111513; border: 2px solid #111513; padding: 14px 18px; margin-bottom: 24px; font-size: 12px; font-weight: 900; letter-spacing: 0.08em; text-transform: uppercase; }}
        .slide {{ background: #1a1f1d; border: 1px solid #59605c; border-radius: 0; padding: 40px; margin-bottom: 30px; }}
        .slide-title {{ font-size: 24px; font-weight: 900; color: #e5c21d; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 20px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 20px 0; }}
        .metric-card {{ background: #111513; border: 1px solid #59605c; border-radius: 0; padding: 20px; text-align: center; }}
        .metric-val {{ font-size: 32px; font-weight: 900; color: #f1eee6; font-family: monospace; }}
        .metric-lbl {{ font-size: 11px; font-weight: 700; color: #bcb8ad; text-transform: uppercase; margin-top: 6px; }}
        .summary-box {{ background: #f1eee6; border-left: 6px solid #e5c21d; padding: 20px; border-radius: 0; font-size: 14px; line-height: 1.6; color: #111513; }}
        .section-body {{ font-size: 13px; line-height: 1.6; color: #d8d3c8; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="disclosure">{SYNTHETIC_DISCLOSURE}</div>
    <div class="slide">
        <div class="slide-title">{title}</div>
        <div class="summary-box">
            <strong>EXECUTIVE SUMMARY</strong><br><br>
            {summary}
        </div>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-val">{pol_q}</div>
                <div class="metric-lbl">Network Modularity (Q)</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{echo_score}</div>
                <div class="metric-lbl">Synthetic Echo Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{gini}</div>
                <div class="metric-lbl">Synthetic Engagement Gini</div>
            </div>
        </div>
    </div>
"""

        for sec in sections:
            sec_title = html.escape(str(sec.get("title", "Section")), quote=True)
            sec_content = html.escape(str(sec.get("content", "")), quote=True)
            slides_html += f"""
    <div class="slide">
        <div class="slide-title">{sec_title}</div>
        <div class="section-body">{sec_content}</div>
    </div>"""

        slides_html += "\n</body>\n</html>"
        return slides_html

"""
Export Service
Handles PDF and CSV generation for simulation reports and data.
"""

import os
import io
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from typing import List, Dict, Any, Optional

from ..config import Config
from ..utils.logger import get_logger
from .zep_tools import ZepToolsService

logger = get_logger('askthepeople.export_service')

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
    """Exports simulation graph data to CSV"""
    
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
        
        # 3. Build unified data structure
        # We'll create a "Facts" list which is the most valuable part of the simulation
        data = []
        
        for edge in edges:
            data.append({
                "Type": "RELATIONSHIP",
                "Source": edge.source_node_name or edge.source_node_uuid,
                "Target": edge.target_node_name or edge.target_node_uuid,
                "Action": edge.name,
                "Fact": edge.fact,
                "Time": edge.valid_at or edge.created_at,
                "Status": "EXPIRED" if edge.is_expired else "ACTIVE"
            })
            
        for node in nodes:
            entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entity")
            data.append({
                "Type": f"ENTITY_{entity_type.upper()}",
                "Source": node.name,
                "Target": "",
                "Action": "SUMMARY",
                "Fact": node.summary,
                "Time": "",
                "Status": "ACTIVE"
            })
            
        df = pd.DataFrame(data)
        
        # Generate CSV string
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    def export_survey_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Convert batch interview (survey) results into a CSV string.
        
        Args:
            results: List of dicts, each containing agent_name, profession, and answer.
            
        Returns:
            CSV formatted string.
        """
        if not results:
            return "agent_name,profession,answer\n"
            
        df = pd.DataFrame(results)
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()


class ExecutiveExporter:
    """Generates an executive presentation slide deck (HTML format) with metrics visualization."""

    def generate_html_deck(self, report_data: Dict[str, Any], metrics_data: Optional[Dict[str, Any]] = None) -> str:
        title = report_data.get("title", "Executive Simulation Brief")
        summary = report_data.get("summary", "No executive summary provided.")
        sections = report_data.get("sections", [])
        
        pol_q = metrics_data.get("polarization_index", "N/A") if metrics_data else "N/A"
        echo_score = metrics_data.get("echo_chamber_score", "N/A") if metrics_data else "N/A"
        gini = metrics_data.get("engagement_gini", "N/A") if metrics_data else "N/A"

        slides_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} — Executive Presentation</title>
    <style>
        body {{ font-family: 'Outfit', -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }}
        .slide {{ background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 40px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }}
        .slide-title {{ font-size: 24px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 20px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 20px 0; }}
        .metric-card {{ background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 20px; text-align: center; }}
        .metric-val {{ font-size: 32px; font-weight: 800; color: #f43f5e; font-family: monospace; }}
        .metric-lbl {{ font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 6px; }}
        .summary-box {{ background: rgba(56, 189, 248, 0.1); border-left: 4px solid #38bdf8; padding: 20px; border-radius: 8px; font-size: 14px; line-height: 1.6; color: #e2e8f0; }}
        .section-body {{ font-size: 13px; line-height: 1.6; color: #cbd5e1; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="slide">
        <div class="slide-title">{title}</div>
        <div class="summary-box">
            <strong>EXECUTIVE SUMMARY</strong><br><br>
            {summary}
        </div>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-val">{pol_q}</div>
                <div class="metric-lbl">Polarization Index (Q)</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{echo_score}</div>
                <div class="metric-lbl">Echo Chamber Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{gini}</div>
                <div class="metric-lbl">Engagement Gini</div>
            </div>
        </div>
    </div>
"""

        for sec in sections:
            sec_title = sec.get("title", "Section")
            sec_content = sec.get("content", "")
            slides_html += f"""
    <div class="slide">
        <div class="slide-title">{sec_title}</div>
        <div class="section-body">{sec_content}</div>
    </div>"""

        slides_html += "\n</body>\n</html>"
        return slides_html

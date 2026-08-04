"""
Simulation API Routes
Step 2: Zep Entity Reading & Filtering, OASIS Simulation Preparation & Running (Fully Automated)
"""

import os
import io
import json
import traceback
from datetime import datetime
from flask import request, jsonify, send_file

from .. import simulation_bp
from ..simulation import _with_config_truth
from ...services.simulation_manager import SimulationManager
from ...services.export_service import CSVExporter
from ...services.zep_tools import ZepToolsService
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.simulation')

from ...utils.safe_path import SafePathError


# P0 path-escape fix (audit §5 P0). The platform identifier is a request-
# controlled value; it MUST be parsed as a strict enum and resolved to a
# fixed filename. Do NOT interpolate request text into a filename.
ALLOWED_PLATFORMS = {
    "reddit": "reddit_simulation.db",
    "twitter": "twitter_simulation.db",
}



@simulation_bp.route('/<simulation_id>/config/download', methods=['GET'])
def download_simulation_config(simulation_id: str):
    """Download simulation configuration file"""
    try:
        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return jsonify({
                "success": False,
                "error": "Configuration file does not exist, please call /prepare interface first"
            }), 404
        
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = _with_config_truth(json.load(handle))
        payload = io.BytesIO(
            json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
        )
        payload.seek(0)

        return send_file(
            payload,
            mimetype="application/json",
            as_attachment=True,
            download_name="simulation_config.json"
        )

    except SafePathError:
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to download configuration: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/script/<script_name>/download', methods=['GET'])
def download_simulation_script(script_name: str):
    """
    Download simulation run script file (generic script, located in backend/scripts/)
    
    script_name options:
        - run_twitter_simulation.py
        - run_reddit_simulation.py
        - run_parallel_simulation.py
        - action_logger.py
    """
    try:
        # Scripts are located in backend/scripts/ directory
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        # Validate script name
        allowed_scripts = [
            "run_twitter_simulation.py",
            "run_reddit_simulation.py", 
            "run_parallel_simulation.py",
            "action_logger.py"
        ]
        
        if script_name not in allowed_scripts:
            return jsonify({
                "success": False,
                "error": f"Unknown script: {script_name}, available options: {allowed_scripts}"
            }), 400
        
        script_path = os.path.join(scripts_dir, script_name)
        
        if not os.path.exists(script_path):
            return jsonify({
                "success": False,
                "error": f"Script file does not exist: {script_name}"
            }), 404
        
        return send_file(
            script_path,
            as_attachment=True,
            download_name=script_name
        )
        
    except Exception as e:
        logger.error(f"Failed to download script: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/<simulation_id>/export/generated-responses', methods=['POST'])
@simulation_bp.route('/<simulation_id>/export/survey', methods=['POST'])
def export_survey_csv(simulation_id: str):
    """
    Export model-generated profile responses as CSV.

    The legacy ``/export/survey`` route remains as a compatibility alias. These
    records are synthetic model outputs, not survey responses from people.
    
    Request (JSON):
        {
            "results": [
                {"agent_name": "...", "profession": "...", "answer": "..."},
                ...
            ]
        }
    """
    try:
        data = request.get_json() or {}
        results = data.get('results', [])
        
        if not results:
            return jsonify({
                "success": False,
                "error": "No results to export"
            }), 400
            
        exporter = CSVExporter(ZepToolsService())
        csv_content = exporter.export_survey_results(results)
        
        # Create bytes stream for file download
        mem = io.BytesIO()
        mem.write(csv_content.encode('utf-8'))
        mem.seek(0)
        
        filename = (
            f"ATP_GENERATED_RESPONSES_{simulation_id}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Failed to export generated-response CSV: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

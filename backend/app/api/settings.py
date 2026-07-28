"""
Settings API Routes
Allows reading, saving, and testing LLM and Zep configurations dynamically
"""

import os
import traceback
from flask import Blueprint, request, jsonify
from ..config import Config
from ..utils.llm_client import LLMClient

from . import settings_bp

@settings_bp.route('', methods=['GET'])
def get_settings():
    """Get current configuration settings"""
    try:
        data = {
            "LLM_API_KEY": Config.LLM_API_KEY,
            "LLM_BASE_URL": Config.LLM_BASE_URL,
            "LLM_MODEL_NAME": Config.LLM_MODEL_NAME,
            "ZEP_API_KEY": Config.ZEP_API_KEY,
            "BRAVE_SEARCH_API_KEY": os.environ.get('BRAVE_SEARCH_API_KEY', ''),
            "LLM_BOOST_API_KEY": os.environ.get('LLM_BOOST_API_KEY', ''),
            "LLM_BOOST_BASE_URL": os.environ.get('LLM_BOOST_BASE_URL', ''),
            "LLM_BOOST_MODEL_NAME": os.environ.get('LLM_BOOST_MODEL_NAME', '')
        }
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@settings_bp.route('', methods=['POST'])
def update_settings():
    """Update configuration settings in memory and persist in .env"""
    try:
        data = request.get_json() or {}
        
        # Validations (make sure values are string)
        settings_dict = {}
        for key in [
            "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_NAME", 
            "ZEP_API_KEY", "BRAVE_SEARCH_API_KEY", 
            "LLM_BOOST_API_KEY", "LLM_BOOST_BASE_URL", "LLM_BOOST_MODEL_NAME"
        ]:
            if key in data:
                settings_dict[key] = str(data[key]).strip()
        
        # Write to .env
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        updated_keys = set()
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in line:
                parts = stripped.split('=', 1)
                k = parts[0].strip()
                if k in settings_dict:
                    new_lines.append(f"{k}={settings_dict[k]}\n")
                    updated_keys.add(k)
                    continue
            new_lines.append(line)
            
        for k, v in settings_dict.items():
            if k not in updated_keys:
                # Add a newline if needed
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines[-1] = new_lines[-1] + '\n'
                new_lines.append(f"{k}={v}\n")
                
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        # Update in-memory os.environ
        for k, v in settings_dict.items():
            os.environ[k] = v
            
        # Update in-memory Config class
        if 'LLM_API_KEY' in settings_dict:
            Config.LLM_API_KEY = settings_dict['LLM_API_KEY']
        if 'LLM_BASE_URL' in settings_dict:
            Config.LLM_BASE_URL = settings_dict['LLM_BASE_URL']
        if 'LLM_MODEL_NAME' in settings_dict:
            Config.LLM_MODEL_NAME = settings_dict['LLM_MODEL_NAME']
        if 'ZEP_API_KEY' in settings_dict:
            Config.ZEP_API_KEY = settings_dict['ZEP_API_KEY']
        if 'BRAVE_SEARCH_API_KEY' in settings_dict:
            os.environ['BRAVE_SEARCH_API_KEY'] = settings_dict['BRAVE_SEARCH_API_KEY']
        if 'LLM_BOOST_API_KEY' in settings_dict:
            os.environ['LLM_BOOST_API_KEY'] = settings_dict['LLM_BOOST_API_KEY']
        if 'LLM_BOOST_BASE_URL' in settings_dict:
            os.environ['LLM_BOOST_BASE_URL'] = settings_dict['LLM_BOOST_BASE_URL']
        if 'LLM_BOOST_MODEL_NAME' in settings_dict:
            os.environ['LLM_BOOST_MODEL_NAME'] = settings_dict['LLM_BOOST_MODEL_NAME']
            
        return jsonify({
            "success": True,
            "message": "Settings saved successfully",
            "data": {
                "LLM_API_KEY": Config.LLM_API_KEY,
                "LLM_BASE_URL": Config.LLM_BASE_URL,
                "LLM_MODEL_NAME": Config.LLM_MODEL_NAME,
                "ZEP_API_KEY": Config.ZEP_API_KEY,
                "BRAVE_SEARCH_API_KEY": os.environ.get('BRAVE_SEARCH_API_KEY', ''),
                "LLM_BOOST_API_KEY": os.environ.get('LLM_BOOST_API_KEY', ''),
                "LLM_BOOST_BASE_URL": os.environ.get('LLM_BOOST_BASE_URL', ''),
                "LLM_BOOST_MODEL_NAME": os.environ.get('LLM_BOOST_MODEL_NAME', '')
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@settings_bp.route('/test', methods=['POST'])
def test_settings():
    """Test connection with provided LLM settings without saving them"""
    try:
        data = request.get_json() or {}
        
        api_key = data.get('LLM_API_KEY')
        base_url = data.get('LLM_BASE_URL')
        model = data.get('LLM_MODEL_NAME')
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API Key is required to run test"
            }), 400
        if not base_url:
            return jsonify({
                "success": False,
                "error": "Base URL is required to run test"
            }), 400
        if not model:
            return jsonify({
                "success": False,
                "error": "Model Name is required to run test"
            }), 400
            
        # Create client with temporary params (timeout = 10s to fail fast)
        client = LLMClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=15.0
        )
        
        test_messages = [{"role": "user", "content": "Respond with only one word: Connected"}]
        response = client.chat(messages=test_messages, max_tokens=10)
        
        return jsonify({
            "success": True,
            "message": "Connection test succeeded",
            "response": response
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 200  # Return 200 with success: false to handle cleanly in the UI

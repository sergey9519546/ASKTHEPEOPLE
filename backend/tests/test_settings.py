import os
import json
import pytest
from app import create_app
from app.config import Config

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_get_settings(client):
    """Test retrieving current configuration settings"""
    response = client.get('/api/settings')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'LLM_API_KEY' in data['data']
    assert 'LLM_BASE_URL' in data['data']
    assert 'LLM_MODEL_NAME' in data['data']

def test_update_settings(client):
    """Test updating configuration settings and restoring original env"""
    # 1. Back up current .env file content
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
    original_env_content = None
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            original_env_content = f.read()

    # Back up Config values in-memory
    orig_api_key = Config.LLM_API_KEY
    orig_base_url = Config.LLM_BASE_URL
    orig_model_name = Config.LLM_MODEL_NAME

    try:
        # 2. Perform test update
        test_payload = {
            "LLM_API_KEY": "test-nvapi-key",
            "LLM_BASE_URL": "https://integrate.api.nvidia.com/v1",
            "LLM_MODEL_NAME": "nvidia/llama-3.1-nemotron-70b-instruct",
            "ZEP_API_KEY": "test-zep-key",
            "BRAVE_SEARCH_API_KEY": "test-brave-key",
            "LLM_BOOST_API_KEY": "test-boost-key",
            "LLM_BOOST_BASE_URL": "https://integrate.api.nvidia.com/v1",
            "LLM_BOOST_MODEL_NAME": "meta/llama-3.1-405b-instruct"
        }
        
        response = client.post('/api/settings', json=test_payload)
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data['success'] is True
        
        # Verify in-memory values were updated
        assert Config.LLM_API_KEY == "test-nvapi-key"
        assert Config.LLM_BASE_URL == "https://integrate.api.nvidia.com/v1"
        assert Config.LLM_MODEL_NAME == "nvidia/llama-3.1-nemotron-70b-instruct"
        assert os.environ.get("LLM_BOOST_API_KEY") == "test-boost-key"
        
    finally:
        # 3. Restore original .env file content and in-memory config
        if original_env_content is not None:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(original_env_content)
        elif os.path.exists(env_path):
            os.remove(env_path)

        Config.LLM_API_KEY = orig_api_key
        Config.LLM_BASE_URL = orig_base_url
        Config.LLM_MODEL_NAME = orig_model_name
        if orig_api_key is not None:
            os.environ['LLM_API_KEY'] = orig_api_key
        if orig_base_url is not None:
            os.environ['LLM_BASE_URL'] = orig_base_url
        if orig_model_name is not None:
            os.environ['LLM_MODEL_NAME'] = orig_model_name

def test_connection_test_invalid_inputs(client):
    """Test connection endpoint with invalid inputs"""
    # Test missing parameters
    response = client.post('/api/settings/test', json={
        "LLM_BASE_URL": "https://integrate.api.nvidia.com/v1"
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False

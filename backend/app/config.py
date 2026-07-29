"""
Configuration Management
Uniformly loads configuration from the .env file in the project root directory
"""

import os
import subprocess
from dotenv import load_dotenv

# Load the .env file from the project root directory
# Path: ASKTHEPEOPLE/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If there is no .env in the root directory, try loading environment variables (for production environment)
    load_dotenv(override=True)


def _resolve_github_models_token() -> None:
    """
    Auto-resolve a GitHub Models LLM token so the app works with zero manual setup.

    GitHub Models (https://docs.github.com/github-models) provides free,
    OpenAI-compatible LLM inference authenticated with any GitHub token that
    has `models:read`. If `.env` carries the placeholder credential, we try to
    pull a live token from the local `gh` CLI (the user is already authed).
    On servers without `gh`, set a real LLM_API_KEY in `.env` instead.

    Mutates os.environ in place. Failures are silent — the placeholder remains
    and the LLMClient will raise a clear error at call time if still unresolved.
    """
    placeholder = "gho_GITHUB_MODELS_TOKEN_PLACEHOLDER"
    needs_primary = os.environ.get("LLM_API_KEY", "") == placeholder
    needs_boost = os.environ.get("LLM_BOOST_API_KEY", "") == placeholder
    if not (needs_primary or needs_boost):
        return
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=5,
        )
        token = result.stdout.strip() if result.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        token = ""
    if not token:
        return  # leave placeholder; LLMClient will surface a clear error later
    if needs_primary:
        os.environ["LLM_API_KEY"] = token
    if needs_boost:
        os.environ["LLM_BOOST_API_KEY"] = token


_resolve_github_models_token()


class Config:
    """Flask Configuration Class"""

    # Flask Configuration
    # SECRET_KEY: fail-fast in production; allow random-per-restart only in dev.
    if os.environ.get('SECRET_KEY'):
        SECRET_KEY = os.environ.get('SECRET_KEY')
    elif os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
        # Dev: random per-restart is fine (no persistent sessions to protect)
        SECRET_KEY = os.urandom(24).hex()
    else:
        raise RuntimeError(
            "SECRET_KEY must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\" "
            "and add it to your .env file."
        )
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

    # Optional bearer-token auth for all /api/* routes.
    # If set, requests must include: Authorization: Bearer <APP_TOKEN>.
    # If unset (default), the API is open (local dev only).
    APP_TOKEN = os.environ.get('APP_TOKEN')
    
    # JSON Configuration - Disable ASCII escaping to display characters directly (instead of \uXXXX format)
    JSON_AS_ASCII = False
    
    # LLM Configuration (Uniformly use OpenAI format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    LLM_TIMEOUT = float(os.environ.get('LLM_TIMEOUT', '120'))
    
    # Zep Configuration
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # Text Processing Configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default overlap size
    
    # OASIS Simulation Configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS Platform Available Actions Configuration
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Archetype Compression Configuration
    ARCHETYPE_DEFAULT_COUNT = int(os.environ.get('ARCHETYPE_DEFAULT_COUNT', '10'))
    ARCHETYPE_DEFAULT_EXPANSION_FACTOR = int(os.environ.get('ARCHETYPE_DEFAULT_EXPANSION_FACTOR', '10'))

    # Follower Engine Configuration
    FOLLOWER_DEFAULT_COUNT = int(os.environ.get('FOLLOWER_DEFAULT_COUNT', '100'))
    FOLLOWER_ID_BASE = int(os.environ.get('FOLLOWER_ID_BASE', '1000'))

    # Report Agent Configuration
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    REPORT_GENERATION_TIMEOUT = int(os.environ.get('REPORT_GENERATION_TIMEOUT', '900'))  # 15 minutes

    # Rate Limiting
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '200 per day;50 per hour')
    RATELIMIT_LLM_HEAVY = os.environ.get('RATELIMIT_LLM_HEAVY', '10 per hour')
    RATELIMIT_LLM_MEDIUM = os.environ.get('RATELIMIT_LLM_MEDIUM', '20 per hour')
    
    @classmethod
    def validate(cls):
        """Validate necessary configurations"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY is not configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is not configured")
        # H3: reject wildcard CORS in production — exposes the API to any origin.
        # Tests/local dev set FLASK_DEBUG=true; production deploys must list
        # explicit origins (comma-separated) in CORS_ORIGINS.
        if not cls.DEBUG and cls.CORS_ORIGINS.strip() == '*':
            errors.append(
                "CORS_ORIGINS='*' is not allowed in production (DEBUG=False). "
                "Set CORS_ORIGINS to an explicit comma-separated allowlist, e.g. "
                "CORS_ORIGINS=https://your-app.vercel.app"
            )
        return errors


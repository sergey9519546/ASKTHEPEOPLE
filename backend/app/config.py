"""
Configuration Management
Uniformly loads configuration from the .env file in the project root directory
"""

import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

# Load the .env file from the project root directory
# Path: ASKTHEPEOPLE/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    # Platform-managed process variables must win over any mounted/stale file.
    load_dotenv(project_root_env, override=False)
else:
    # If there is no .env in the root directory, try loading environment variables (for production environment)
    load_dotenv(override=False)


_PLACEHOLDER_CREDENTIALS = {"gho_GITHUB_MODELS_TOKEN_PLACEHOLDER"}
for _credential_name in ("LLM_API_KEY", "LLM_BOOST_API_KEY"):
    if os.environ.get(_credential_name) in _PLACEHOLDER_CREDENTIALS:
        # Never silently repurpose the developer's `gh auth token` as a model
        # credential. It may carry materially broader GitHub permissions and
        # must not be sent to a provider endpoint without an explicit choice.
        os.environ.pop(_credential_name, None)


_MIN_PRIVATE_CREDENTIAL_LENGTH = 32
_INSECURE_CREDENTIAL_MARKERS = (
    "build-smoke",
    "changeme",
    "change-me",
    "example",
    "placeholder",
    "test-only",
)

# CI smoke test keys that are intentionally weak but allowed for build validation
_CI_SMOKE_TEST_KEYS = {
    "build-validation-model-key",
    "build-validation-zep-key",
}


def credential_validation_error(name: str, value: str | None) -> str | None:
    """Return a safe validation error for a private application credential."""
    if not value:
        return f"{name} is required"
    normalized = value.strip()
    
    # Allow CI smoke test keys to pass validation
    if normalized in _CI_SMOKE_TEST_KEYS:
        return None
    
    if len(normalized) < _MIN_PRIVATE_CREDENTIAL_LENGTH:
        return (
            f"{name} must be at least {_MIN_PRIVATE_CREDENTIAL_LENGTH} "
            "characters"
        )
    lowered = normalized.lower()
    if any(marker in lowered for marker in _INSECURE_CREDENTIAL_MARKERS):
        return f"{name} must not use a documented placeholder"
    if len(set(normalized)) < 8:
        return f"{name} does not contain enough variation"
    return None


def _trusted_hosts(debug: bool) -> list[str] | None:
    """Build Flask's exact Host allowlist from explicit deployment settings."""
    configured = os.environ.get("TRUSTED_HOSTS", "")
    railway_runtime = bool(os.environ.get("RAILWAY_ENVIRONMENT_ID"))
    candidates = [
        item.strip()
        for item in configured.split(",")
        if item.strip()
    ]

    if not candidates and (not debug or railway_runtime):
        for origin in os.environ.get("CORS_ORIGINS", "").split(","):
            parsed = urlsplit(origin.strip())
            if parsed.hostname:
                candidates.append(parsed.hostname)
        for variable in (
            "RAILWAY_PUBLIC_DOMAIN",
            "RAILWAY_PRIVATE_DOMAIN",
            "RAILWAY_STATIC_URL",
        ):
            value = os.environ.get(variable, "").strip()
            if not value:
                continue
            parsed = urlsplit(value if "://" in value else f"https://{value}")
            if parsed.hostname:
                candidates.append(parsed.hostname)

    if debug and not configured and not railway_runtime:
        return None

    # Railway readiness probes deliberately use this Host value rather than
    # the service's public domain. Keep the exception exact and platform-bound;
    # a wildcard would weaken Host-header validation for normal traffic.
    if railway_runtime:
        candidates.append("healthcheck.railway.app")

    candidates.extend(["localhost", "127.0.0.1", "::1"])
    return list(dict.fromkeys(candidates))


class Config:
    """Flask Configuration Class"""

    # Flask Configuration
    # SECRET_KEY: fail-fast in production; allow random-per-restart only in dev.
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    if os.environ.get('SECRET_KEY'):
        SECRET_KEY = os.environ.get('SECRET_KEY')
        if not DEBUG:
            _secret_error = credential_validation_error("SECRET_KEY", SECRET_KEY)
            if _secret_error:
                raise RuntimeError(_secret_error)
    elif DEBUG:
        # Dev: random per-restart is fine (no persistent sessions to protect)
        SECRET_KEY = os.urandom(24).hex()
    else:
        raise RuntimeError(
            "SECRET_KEY must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\" "
            "and add it to your .env file."
        )
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    TRUSTED_HOSTS = _trusted_hosts(DEBUG)
    # Railway injects this identifier only inside its private service runtime;
    # there X-Real-IP is set by the edge proxy. Other deployments must opt in.
    TRUST_X_REAL_IP = (
        bool(os.environ.get("RAILWAY_ENVIRONMENT_ID"))
        or os.environ.get("TRUST_X_REAL_IP", "False").lower() == "true"
    )

    # Optional bearer-token auth for all /api/* routes.
    # If set, requests must include: Authorization: Bearer <APP_TOKEN>.
    # If unset (default), the API is open (local dev only).
    APP_TOKEN = os.environ.get('APP_TOKEN')
    REQUIRE_APP_AUTH = os.environ.get(
        'REQUIRE_APP_AUTH',
        'False' if DEBUG else 'True',
    ).lower() == 'true'

    # Span-verified Big Five trait inference during profile generation.
    #
    # Off by default for two reasons: it costs one additional model call per
    # generated profile, and it is the only path that can move engine
    # behavioural controls off their neutral defaults. With this off, agent
    # behaviour is identical to before the trait layer existed.
    #
    # When on, a trait is attached only if the model cites a verbatim span that
    # is then confirmed by literal substring match against the supplied source
    # (see services/trait_inference.py). Unverifiable claims are discarded, so
    # enabling this cannot introduce ungrounded personality.
    ENABLE_TRAIT_INFERENCE = os.environ.get(
        'ENABLE_TRAIT_INFERENCE', 'False'
    ).lower() == 'true'

    # Runtime provider settings are a privileged local-development control
    # plane, not a general application feature.  They are disabled unless an
    # operator opts in explicitly.  In production APP_TOKEN must also be set,
    # which keeps the mutation/test routes behind the existing single-user
    # bearer-token guard.
    ALLOW_RUNTIME_SETTINGS = os.environ.get(
        'ALLOW_RUNTIME_SETTINGS', 'False'
    ).lower() == 'true'
    ALLOW_PRIVATE_LLM_ENDPOINTS = os.environ.get(
        'ALLOW_PRIVATE_LLM_ENDPOINTS', 'False'
    ).lower() == 'true'
    RUNTIME_SETTINGS_ENV_PATH = os.path.abspath(project_root_env)
    
    # JSON Configuration - Disable ASCII escaping to display characters directly (instead of \uXXXX format)
    JSON_AS_ASCII = False
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'text')
    
    # LLM Configuration (Uniformly use OpenAI format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    LLM_TIMEOUT = float(os.environ.get('LLM_TIMEOUT', '120'))
    _configured_llm_urls = [
        url for url in (
            LLM_BASE_URL,
            os.environ.get('LLM_BOOST_BASE_URL', ''),
        )
        if url
    ]
    LLM_ALLOWED_BASE_URLS = os.environ.get(
        'LLM_ALLOWED_BASE_URLS',
        ','.join(_configured_llm_urls),
    )
    
    # Zep Configuration
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB (Security: P0 file upload limit)
    # abspath wraps the *resolved* value, not just the default: an operator
    # supplying a relative UPLOAD_FOLDER would otherwise leave every storage
    # path relative to the process cwd, which differs between the web process
    # and the worker and makes safe_join's containment check cwd-dependent.
    UPLOAD_FOLDER = os.path.abspath(
        os.environ.get(
            'UPLOAD_FOLDER',
            os.path.join(os.path.dirname(__file__), '../uploads'),
        )
    )
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # Text Processing Configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default overlap size
    
    # OASIS Simulation Configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    # Defaults *under* UPLOAD_FOLDER rather than recomputing the repo-relative
    # path, so relocating storage with UPLOAD_FOLDER alone moves simulation
    # run-state with it. Setting this explicitly still overrides.
    OASIS_SIMULATION_DATA_DIR = os.path.abspath(
        os.environ.get(
            'OASIS_SIMULATION_DATA_DIR',
            os.path.join(UPLOAD_FOLDER, 'simulations'),
        )
    )
    # Controlled transition: all new preparation runs stop at a reviewed,
    # functional decision-lens boundary. Disabling the boundary fails closed;
    # it never reactivates legacy persona generation.
    DECISION_LENS_V1_ENABLED = os.environ.get(
        'DECISION_LENS_V1_ENABLED', 'True'
    ).lower() == 'true'
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
    # Explicit opt-in only. Defaulting this to REDIS_URL would silently move
    # rate-limit storage off memory:// on every deployment that sets REDIS_URL
    # for Celery, which (a) contradicts docs/security/THREAT_MODEL.md and
    # (b) lets a Redis outage surface as 5xx on /api/* where memory:// could
    # not. Operators running multiple web workers set this deliberately.
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')

    # Celery & Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
    
    # Database Configuration
    # For sync SQLAlchemy with psycopg3, use postgresql:// or postgresql+psycopg://
    # Falls back to SQLite for local development if DATABASE_URL not set
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./askthepeople.db')
    
    # Convert postgres:// to postgresql:// (common in deployment platforms like Heroku/Railway)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


    
    @classmethod
    def validate(cls):
        """Validate necessary configurations"""
        errors = []
        
        # Allow CI smoke test keys to pass validation
        llm_key = cls.LLM_API_KEY
        zep_key = cls.ZEP_API_KEY
        
        if not llm_key or (llm_key not in _CI_SMOKE_TEST_KEYS and not llm_key.strip()):
            errors.append("LLM_API_KEY is not configured")
        if not zep_key or (zep_key not in _CI_SMOKE_TEST_KEYS and not zep_key.strip()):
            errors.append("ZEP_API_KEY is not configured")
        if cls.REQUIRE_APP_AUTH and not cls.APP_TOKEN:
            errors.append(
                "APP_TOKEN is required when REQUIRE_APP_AUTH=true. "
                "Generate a private access key and provide it at runtime; "
                "never compile it into the frontend bundle."
            )
        elif cls.REQUIRE_APP_AUTH:
            token_error = credential_validation_error("APP_TOKEN", cls.APP_TOKEN)
            if token_error:
                errors.append(token_error)
        if not cls.DEBUG:
            secret_error = credential_validation_error("SECRET_KEY", cls.SECRET_KEY)
            if secret_error:
                errors.append(secret_error)
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

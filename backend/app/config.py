"""
Configuration Management
Uniformly loads configuration from the .env file in the project root directory
"""

import math
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

def credential_validation_error(name: str, value: str | None) -> str | None:
    """Return a safe validation error for a private application credential."""
    if not value:
        return f"{name} is required"
    normalized = value.strip()
    
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


def _strict_float(name: str, default: str) -> float:
    """Read a numeric setting that has no safe fallback.

    `Config` reads its environment in the class body, so a malformed value
    cannot be repaired after the fact. Falling back to the default would
    silently substitute one number for another, and for a ceiling that is the
    dangerous direction: a budget of `12.50` misread as `0.0` turns "refuse
    this run" into "no ceiling at all". Refusing to build the configuration is
    the only outcome that cannot understate a limit.

    `nan` and `inf` are rejected alongside unparseable text for the same
    reason. Both survive `float()` and both fail every comparison, so a `nan`
    ceiling would read as "never breached" and stay unlimited while looking
    configured.
    """
    raw = os.environ.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = None
    if value is None or not math.isfinite(value):
        raise RuntimeError(
            f"{name} must be a finite number, got {raw!r}. Unset {name} to use "
            f"the default ({default})."
        )
    return value


def _strict_int(name: str, default: str) -> int:
    """Whole-number variant of `_strict_float`, built on it so the failure
    mode of the two cannot diverge."""
    value = _strict_float(name, default)
    if value != int(value):
        raise RuntimeError(
            f"{name} must be a whole number, got {value!r}. Unset {name} to "
            f"use the default ({default})."
        )
    return int(value)


# The only breach actions that name a real behaviour. 'warn' records and
# continues. 'refuse' would stop the run -- correct for a pre-release product
# with no cost meter, but it cannot be honoured until one exists, so it is
# refused at the gateway rather than accepted as an unkeepable promise.
# 'degrade' is deliberately absent: there is no reduced-fidelity run mode.
COST_BUDGET_BREACH_ACTIONS = ('warn', 'refuse')


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
    # docx/xlsx are OOXML zip containers; FileParser extracts them stdlib-only
    # with declared uncompressed-size ceilings and a DTD rejection guard.
    # Legacy binary .doc has no safe stdlib parser and stays refused.
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown', 'docx', 'xlsx'}
    
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

    # Source ingestion V1 — controlled TXT source ingestion and review
    # (Task 4). Disabled by default; the domain kernel exists but is not
    # wired to production routes, persistence, or workers. Enabling in
    # production requires all Task 4 §5 production blockers to be resolved.
    SOURCE_INGESTION_V1_ENABLED = os.environ.get(
        'SOURCE_INGESTION_V1_ENABLED', 'False'
    ).lower() == 'true'
    # Comma-separated enabled formats. Eligible formats are exactly those
    # FileParser extracts under declared ceilings: txt, md, markdown, pdf,
    # docx, xlsx. Empty means no formats are accepted even if the master
    # flag is on.
    SOURCE_INGESTION_V1_FORMATS = [
        f.strip().lower()
        for f in os.environ.get('SOURCE_INGESTION_V1_FORMATS', '').split(',')
        if f.strip()
    ]

    # Dev/test-only actor-context installer (see services/actor_context_installer.py).
    # The canonical source-persistence boundary reads ``g.actor_context``, but
    # the production OIDC/membership resolver behind ADR-0009 is not built yet.
    # This flag lets local dev and CI install a stable LEGACY_DEV SERVICE scope
    # so the persistence seam can be exercised end-to-end. It is a no-op unless
    # DEBUG is also true, and Config.validate() refuses it in production.
    DEV_ACTOR_CONTEXT_ENABLED = os.environ.get(
        'DEV_ACTOR_CONTEXT_ENABLED', 'False'
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

    # Population Tier 4 (MASS_POPULATION) — the 50,000-character tier per
    # docs/plans/2026-10-01-50k-character-scale-plan.md. Fail-closed: the
    # default run stays at the current 1,000-character ceiling, and every
    # bound below only takes effect when this flag is explicitly true at
    # runtime. A deployment must opt in; nothing defaults to tier 4.
    POPULATION_TIER_4_ENABLED = os.environ.get(
        'POPULATION_TIER_4_ENABLED', 'False'
    ).lower() == 'true'
    # 250 archetypes x 20 profiles/archetype (1 centroid + 19 variants)
    # = 5,000 LLM-tier characters.
    TIER4_ARCHETYPE_COUNT = int(os.environ.get('TIER4_ARCHETYPE_COUNT', '250'))
    TIER4_EXPANSION_FACTOR = int(os.environ.get('TIER4_EXPANSION_FACTOR', '20'))
    TIER4_PREPARED_PROFILE_MAX = int(
        os.environ.get('TIER4_PREPARED_PROFILE_MAX', '5000')
    )
    # 45,000 rule-based crowd characters, computed outside the OASIS
    # subprocess (FollowerEngine). The composition lands exactly 50,000.
    TIER4_FOLLOWER_COUNT = int(os.environ.get('TIER4_FOLLOWER_COUNT', '45000'))
    TIER4_FOLLOWER_COUNT_MAX = int(
        os.environ.get('TIER4_FOLLOWER_COUNT_MAX', '50000')
    )
    # Crowd participation cap: the follower round callback must not emit more
    # than this many actions per round regardless of follower count, so crowd
    # work stays bounded inside the monitor loop.
    TIER4_CROWD_ACTIONS_PER_ROUND_MAX = int(
        os.environ.get('TIER4_CROWD_ACTIONS_PER_ROUND_MAX', '2000')
    )

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

    # ============================================================
    # Service level objectives and cost budgets (Gate 4, exec-plan T29)
    # ============================================================
    # Configuration only. No module in the tree consumes these values yet, so
    # every default below leaves runtime behaviour byte-identical. That is
    # deliberate: declaring an SLO and enforcing one are different changes,
    # and the enforcement half needs a cost meter that does not exist.
    # docs/observability/SLO_AND_COST_BUDGET.md records which half is which.
    #
    # The objectives are declared over the series that `app/utils/metrics.py`
    # actually exposes at GET /health/metrics, not over invented metric names.
    # The latency threshold must therefore be one of that module's bucket
    # boundaries: the histogram can only answer "what share finished under
    # X", so a threshold between two buckets would describe a percentile the
    # metrics endpoint cannot report. `validate_production_gates` refuses any
    # other value.
    SLO_ENABLED = os.environ.get('SLO_ENABLED', 'False').lower() == 'true'
    # 1.0s is the boundary between "a person is still waiting" and "they have
    # navigated away"; it is also a real bucket in LATENCY_BUCKETS.
    SLO_LATENCY_BUCKET_SECONDS = _strict_float('SLO_LATENCY_BUCKET_SECONDS', '1.0')
    # 99%: one request in a hundred may be slow because a provider was cold,
    # which is normal operation, not an incident.
    SLO_LATENCY_TARGET_RATIO = _strict_float('SLO_LATENCY_TARGET_RATIO', '0.99')
    # Stricter than the latency objective on purpose. A slow answer is a
    # degraded experience; a 5xx is a broken contract. The error rate is
    # measured over the same request counter, so the two objectives cannot be
    # satisfied by dropping traffic.
    SLO_ERROR_RATE_MAX_RATIO = _strict_float('SLO_ERROR_RATE_MAX_RATIO', '0.001')
    # 30 days, the standard rolling SLO window: it spans a weekly cycle so a
    # quiet weekend cannot pass an objective that a busy Monday would fail.
    SLO_WINDOW_SECONDS = _strict_int('SLO_WINDOW_SECONDS', '2592000')
    # Below this many requests in the window the ratios are arithmetic on a
    # handful of points, and an objective evaluated on them is noise wearing a
    # compliance number.
    SLO_MIN_REQUESTS = _strict_int('SLO_MIN_REQUESTS', '20')

    # Cost ceilings are declared per run and per day because they fail
    # independently: a single expensive run is refused by the operator, while
    # many cheap runs are only visible in the daily total that the provider
    # invoice arrives as. 0.0 means "no ceiling declared for that scope", not
    # "free" -- an enabled budget with both ceilings at 0.0 declares nothing
    # and is refused.
    COST_BUDGET_ENABLED = os.environ.get(
        'COST_BUDGET_ENABLED', 'False'
    ).lower() == 'true'
    COST_BUDGET_MAX_USD_PER_RUN = _strict_float('COST_BUDGET_MAX_USD_PER_RUN', '0.0')
    COST_BUDGET_MAX_USD_PER_DAY = _strict_float('COST_BUDGET_MAX_USD_PER_DAY', '0.0')
    # 'warn' or 'refuse'. Default 'warn' because it is the only action that is
    # honest today: no run's cost is measured anywhere in the tree, so 'warn'
    # cannot overstate what is known. See COST_BUDGET_BREACH_ACTIONS and the
    # refusal in `_slo_and_cost_budget_errors`.
    COST_BUDGET_BREACH_ACTION = os.environ.get(
        'COST_BUDGET_BREACH_ACTION', 'warn'
    ).strip().lower()

    # Celery & Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
    
    # Database Configuration
    # For sync SQLAlchemy with psycopg3, use postgresql:// or postgresql+psycopg://
    # Falls back to SQLite for local development if DATABASE_URL not set
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./askthepeople.db')

    # ============================================================
    # Supabase — Postgres + Storage backend (ADR-0012)
    # ============================================================
    # When SUPABASE_URL is set, the backend expects the rest of the
    # Supabase env vars and a non-sqlite DATABASE_URL. The
    # USE_SUPABASE_PERSISTENCE master switch keeps the legacy
    # filesystem path available for local dev / tests that don't want
    # to talk to a real Supabase project.
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    # Bucket names are operator-configurable so prod / dev / different
    # workspaces can isolate their uploads + reports. They must be
    # PRIVATE on the Supabase side; signed URLs are the only access path.
    SUPABASE_STORAGE_BUCKET_UPLOADS = os.environ.get(
        'SUPABASE_STORAGE_BUCKET_UPLOADS', 'askthepeople-uploads',
    )
    SUPABASE_STORAGE_BUCKET_REPORTS = os.environ.get(
        'SUPABASE_STORAGE_BUCKET_REPORTS', 'askthepeople-reports',
    )
    # Default false: local dev keeps using filesystem + the existing
    # SQLite. Set to true in production once the Supabase project is
    # provisioned and the alembic head revision is applied.
    USE_SUPABASE_PERSISTENCE = os.environ.get(
        'USE_SUPABASE_PERSISTENCE', 'False',
    ).lower() == 'true'
    # S3-compatible local stand-in for Supabase Storage in dev when the
    # full local Supabase stack is not available (the full stack uses
    # Docker secrets which fail on some Windows hosts; MinIO + Postgres
    # alone is a clean dev path that exercises the same code paths).
    SUPABASE_S3_ENDPOINT = os.environ.get('SUPABASE_S3_ENDPOINT')
    SUPABASE_S3_ACCESS_KEY = os.environ.get('SUPABASE_S3_ACCESS_KEY')
    SUPABASE_S3_SECRET_KEY = os.environ.get('SUPABASE_S3_SECRET_KEY')
    SUPABASE_S3_REGION = os.environ.get('SUPABASE_S3_REGION', 'us-east-1')
    
    # Convert postgres:// to postgresql:// (common in deployment platforms like Heroku/Railway)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


    
    @classmethod
    def _slo_and_cost_budget_errors(cls) -> list[str]:
        """Refusals for the Gate 4 SLO and cost-budget settings.

        Shared by `validate_production_gates` and `validate` so the two cannot
        drift into disagreeing about what makes an unsafe SLO or cost budget;
        `test_startup_production_gate.py` asserts that relationship, and it has
        caught exactly this kind of drift before.

        Every check here is about a well-formed value that is nonetheless the
        wrong value -- a threshold the histogram cannot answer, a ratio outside
        its domain, an enabled budget with nothing to enforce. Unparseable text
        never reaches this method: `_strict_float` and `_strict_int` refuse it
        while the class body is still executing.
        """
        errors = []

        if cls.SLO_ENABLED:
            # Imported here rather than at module scope: `app.config` is
            # imported by `app/__init__.py` while the `app` package is still
            # initialising, and this keeps that import window closed. The lazy
            # import is also what keeps one source of truth for the bucket
            # list -- a copy of LATENCY_BUCKETS here would drift silently the
            # next time the histogram changes.
            from .utils.metrics import LATENCY_BUCKETS

            if cls.SLO_LATENCY_BUCKET_SECONDS not in LATENCY_BUCKETS:
                errors.append(
                    f"SLO_LATENCY_BUCKET_SECONDS={cls.SLO_LATENCY_BUCKET_SECONDS} "
                    "is not a latency bucket boundary. The metrics endpoint can "
                    f"only answer at {sorted(LATENCY_BUCKETS)} seconds, so any "
                    "other threshold names a percentile it cannot report. See "
                    "docs/observability/SLO_AND_COST_BUDGET.md."
                )
            if not 0 < cls.SLO_LATENCY_TARGET_RATIO <= 1:
                errors.append(
                    "SLO_LATENCY_TARGET_RATIO must be greater than 0 and at "
                    f"most 1, got {cls.SLO_LATENCY_TARGET_RATIO}. It is the "
                    "share of requests that must finish inside the bucket, so "
                    "a value above 1 would be met by any traffic at all."
                )
            if not 0 <= cls.SLO_ERROR_RATE_MAX_RATIO < 1:
                errors.append(
                    "SLO_ERROR_RATE_MAX_RATIO must be at least 0 and below 1, "
                    f"got {cls.SLO_ERROR_RATE_MAX_RATIO}. A value of 1 would "
                    "permit every request to fail and still report compliance."
                )
            if cls.SLO_WINDOW_SECONDS <= 0:
                errors.append(
                    "SLO_WINDOW_SECONDS must be positive, got "
                    f"{cls.SLO_WINDOW_SECONDS}. The window is the period the "
                    "objective is evaluated over."
                )
            if cls.SLO_MIN_REQUESTS < 1:
                errors.append(
                    "SLO_MIN_REQUESTS must be at least 1, got "
                    f"{cls.SLO_MIN_REQUESTS}. A window below one request can "
                    "never be evaluated, which would make the objective "
                    "permanently unreportable rather than strict."
                )

        if cls.COST_BUDGET_ENABLED:
            ceilings = (
                ('COST_BUDGET_MAX_USD_PER_RUN', cls.COST_BUDGET_MAX_USD_PER_RUN),
                ('COST_BUDGET_MAX_USD_PER_DAY', cls.COST_BUDGET_MAX_USD_PER_DAY),
            )
            negative = [name for name, value in ceilings if value < 0]
            if negative:
                errors.append(
                    f"{', '.join(negative)} must not be negative. Use 0.0 to "
                    "declare that scope unbounded."
                )
            elif all(value == 0 for _, value in ceilings):
                errors.append(
                    "COST_BUDGET_ENABLED=true with both ceilings at 0.0 declares "
                    "a budget of nothing and enforces nothing. Set "
                    "COST_BUDGET_MAX_USD_PER_RUN, COST_BUDGET_MAX_USD_PER_DAY, "
                    "or both, or turn COST_BUDGET_ENABLED off."
                )
            if cls.COST_BUDGET_BREACH_ACTION not in COST_BUDGET_BREACH_ACTIONS:
                errors.append(
                    f"COST_BUDGET_BREACH_ACTION={cls.COST_BUDGET_BREACH_ACTION!r} "
                    f"is not a supported breach action. Supported: "
                    f"{list(COST_BUDGET_BREACH_ACTIONS)}."
                )
            elif cls.COST_BUDGET_BREACH_ACTION == 'refuse':
                errors.append(
                    "COST_BUDGET_BREACH_ACTION=refuse is not implemented and is "
                    "refused rather than accepted as a promise. A run's cost is "
                    "not measured anywhere in the tree: the provider response is "
                    "read for content only (app/utils/llm_client.py) and its "
                    "usage is discarded, so nothing can compare a run against a "
                    "ceiling. Selecting 'refuse' today would advertise a "
                    "guarantee the code does not make. Until a meter exists, "
                    "run_preflight (app/services/simulation_preflight.py:421) "
                    "is where the refusal must be wired. Keep 'warn'. See "
                    "docs/observability/SLO_AND_COST_BUDGET.md."
                )

        return errors

    @classmethod
    def validate_production_gates(cls):
        """Refusals that must stop the process from booting.

        These are the subset of `validate()` that describes a *production
        gateway*: a configuration under which the app would accept traffic it
        cannot serve safely. They are separated from the rest of `validate()`
        because that method also carries ordinary capability checks --
        `LLM_API_KEY` and `ZEP_API_KEY` must be present -- and turning those
        into boot requirements would impose a new restriction on deployments
        that currently run without them.

        `validate()` had exactly one non-test call site
        (`services/simulation_preflight.py`), so none of these refusals were
        enforced at startup. `create_app` re-implemented two credential checks
        and nothing else, which meant `SOURCE_INGESTION_V1_ENABLED=true` in
        production activated the mutating source routes with no boot-time
        objection -- the exact outcome the flag exists to prevent.
        """
        if cls.DEBUG:
            return []
        errors = []
        if cls.SOURCE_INGESTION_V1_ENABLED:
            errors.append(
                "SOURCE_INGESTION_V1_ENABLED=true is not allowed in production. "
                "The source-ingestion boundary (quarantine, scanning, isolated "
                "parsing, tenant auth, object storage, outbox) is not complete. "
                "See Task 4 section 5 production blockers."
            )
        if cls.DEV_ACTOR_CONTEXT_ENABLED:
            errors.append(
                "DEV_ACTOR_CONTEXT_ENABLED=true is not allowed in production. "
                "It installs a synthetic LEGACY_DEV actor scope that bypasses "
                "the server-derived tenant context required by ADR-0009."
            )
        eligible = {'txt', 'md', 'markdown', 'pdf', 'docx', 'xlsx'}
        if cls.SOURCE_INGESTION_V1_FORMATS:
            invalid = [
                f for f in cls.SOURCE_INGESTION_V1_FORMATS if f not in eligible
            ]
            if invalid:
                errors.append(
                    f"SOURCE_INGESTION_V1_FORMATS contains unsupported format(s) "
                    f"{invalid}. V1 extraction supports: {sorted(eligible)}."
                )
        # An SLO whose threshold the metrics cannot answer, and a cost budget
        # that declares nothing or names an action nothing implements, are the
        # same class of defect as an unsafe flag: an operator would read a
        # guarantee the process does not provide. Both stay inert unless the
        # operator opts in, so neither changes a deployment that never sets
        # them.
        errors.extend(cls._slo_and_cost_budget_errors())
        return errors

    @classmethod
    def validate(cls):
        """Validate necessary configurations"""
        errors = []
        
        llm_key = cls.LLM_API_KEY
        zep_key = cls.ZEP_API_KEY
        
        if not llm_key or not llm_key.strip():
            errors.append("LLM_API_KEY is not configured")
        if not zep_key or not zep_key.strip():
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
        # Source ingestion V1 production gate (Task 4 §5). The domain kernel
        # may exist behind the flag, but enabling it in production requires
        # the full ingestion boundary (PostgreSQL, object storage, isolated
        # scanner, tenant auth, transactional outbox). Refuse startup if the
        # flag is on in production — no production blocker may be absent.
        if not cls.DEBUG and cls.SOURCE_INGESTION_V1_ENABLED:
            errors.append(
                "SOURCE_INGESTION_V1_ENABLED=true is not allowed in production. "
                "The source-ingestion boundary (quarantine, scanning, isolated "
                "parsing, tenant auth, object storage, outbox) is not complete. "
                "See Task 4 §5 production blockers."
            )
        # The dev/test actor-context installer must never run in production:
        # it would fabricate a tenant scope and bypass the real OIDC/membership
        # resolver that ADR-0009 requires.
        if not cls.DEBUG and cls.DEV_ACTOR_CONTEXT_ENABLED:
            errors.append(
                "DEV_ACTOR_CONTEXT_ENABLED=true is not allowed in production. "
                "It installs a synthetic LEGACY_DEV actor scope that bypasses "
                "the server-derived tenant context required by ADR-0009."
            )
        # Format eligibility: every configured format must be one FileParser
        # can extract under the declared ceilings (char cap, PDF pages, OOXML
        # zip size/structure). The master flag stays fail-closed off by
        # default; widening eligibility does not enable ingestion.
        eligible = {'txt', 'md', 'markdown', 'pdf', 'docx', 'xlsx'}
        if cls.SOURCE_INGESTION_V1_FORMATS:
            invalid = [
                f for f in cls.SOURCE_INGESTION_V1_FORMATS if f not in eligible
            ]
            if invalid:
                errors.append(
                    f"SOURCE_INGESTION_V1_FORMATS contains unsupported format(s) "
                    f"{invalid}. V1 extraction supports: {sorted(eligible)}."
                )
        # Gate 4 SLO and cost-budget refusals. DEBUG-exempt for the same reason
        # the ingestion checks are: a production safety rule must not make
        # local development impossible, and the gateway is what stops a
        # process from booting under an unsafe production configuration.
        if not cls.DEBUG:
            errors.extend(cls._slo_and_cost_budget_errors())
        return errors

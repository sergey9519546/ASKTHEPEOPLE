"""
API Routes Module
"""

import ipaddress

from flask import Blueprint, current_app, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..config import Config

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
settings_bp = Blueprint('settings', __name__)
auth_bp = Blueprint('auth', __name__)
from .health import health_bp


# Module-level Limiter instance. Initialized against the Flask app inside
# create_app() via `limiter.init_app(app)`. `default_limits` and `storage_uri`
# are constructor arguments in flask-limiter; init_app() only takes the app.
# In-memory storage is intentional while the application remains a
# single-worker runtime. Blueprints import this directly so they can decorate
# routes at definition time.
def _rate_limit_key() -> str:
    """Return a verified client IP when running behind Railway's edge."""
    if current_app.config.get("TRUST_X_REAL_IP", False):
        candidate = request.headers.get("X-Real-IP", "").strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    return get_remote_address()


limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=[Config.RATELIMIT_DEFAULT],
    # Liveness/static delivery must never consume the API abuse budget.
    default_limits_exempt_when=lambda: not request.path.startswith("/api/"),
    storage_uri="memory://",
)

from . import graph  # noqa: E402, F401
from . import templates  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import settings  # noqa: E402, F401
from . import auth  # noqa: E402, F401
from . import branching_routes  # noqa: E402, F401

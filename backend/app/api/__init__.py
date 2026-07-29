"""
API Routes Module
"""

from flask import Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..config import Config

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
settings_bp = Blueprint('settings', __name__)

# Module-level Limiter instance. Initialized against the Flask app inside
# create_app() via `limiter.init_app(app)`. `default_limits` and `storage_uri`
# are constructor arguments in flask-limiter; init_app() only takes the app.
# In-memory storage is used (no Redis dependency). Blueprints import this
# directly so they can decorate routes at definition time.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[Config.RATELIMIT_DEFAULT],
    storage_uri="memory://",
)

from . import graph  # noqa: E402, F401
from . import templates  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import settings  # noqa: E402, F401

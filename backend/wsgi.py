"""
WSGI entry point for Gunicorn.
Usage: gunicorn --chdir /app/backend wsgi:app
"""

import os
import sys

# Ensure the backend directory is on the path so `from app import ...` works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config

_configuration_errors = Config.validate()
if _configuration_errors:
    raise RuntimeError(
        "Invalid production configuration: " + "; ".join(_configuration_errors)
    )

app = create_app()

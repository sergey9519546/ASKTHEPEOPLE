"""
WSGI entry point for Gunicorn.
Usage: gunicorn --chdir /app/backend wsgi:app
"""

import os
import sys

# Ensure the backend directory is on the path so `from app import ...` works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

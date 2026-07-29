"""
ASKTHEPEOPLE Backend Entry Point
"""

import os
import sys

# Solve Windows console encoding issues: set UTF-8 encoding before all imports
if sys.platform == 'win32':
    # Set environment variable to ensure Python uses UTF-8
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # Reconfigure standard output stream to UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def _create_validated_app():
    """Validate every module-level server entry point before serving traffic."""
    errors = Config.validate()
    if errors:
        raise RuntimeError(
            "Invalid application configuration: " + "; ".join(errors)
        )
    return create_app()


# Module-level app for Gunicorn: gunicorn --chdir backend run:app
app = _create_validated_app()


def main():
    """Main function"""
    # Get runtime configuration
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG

    # Start service
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()


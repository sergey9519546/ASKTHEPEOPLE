"""
Flask extension singletons.

Instantiated here and initialised with the app in create_app() via
``ext.init_app(app)``.  Import from here everywhere else to avoid
circular imports.
"""

from flask_sock import Sock

sock = Sock()

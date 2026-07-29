"""
Force backend test isolation by clearing imported env paths.

Some local execution contexts inherit PYTHONPATH from parent shells /
IDE settings, which can bypass this project's venv when pytest imports
backend modules from the project root. This file unsets PYTHONPATH as
early as possible in test collection so imports resolve via the active
Python's sys.path/venv only.
"""

import os
import sys


def _clear_pythonpath() -> None:
    keys = [key for key in os.environ if key.upper() == "PYTHONPATH"]
    for key in keys:
        del os.environ[key]

    # A defensive fallback for environments that still inject it downstream.
    try:
        sys.path = [part for part in sys.path if part not in (
            r"C:\Users\serge\AppData\Local\Temp\hermes_sandbox_hmt84lxd",
            r"C:\Users\serge\AppData\Local\hermes\hermes-agent",
            r"C:\Users\serge\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages",
        )]
    except Exception:
        pass


_clear_pythonpath()

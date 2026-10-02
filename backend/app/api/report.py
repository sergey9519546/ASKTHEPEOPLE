"""
Report API helper module.

The 23 route handlers that used to live here were decomposed into
``app/api/report_routes/`` by exec-plan T25 (ADR-0011), which finished the
Gate 1 route decomposition that had already been applied to
``api/simulation.py``.

This module is retained for two reasons:

* ``tests/test_task5_run_control_fixes.py`` imports ``ReportManager`` through
  this path, and
* ``api/__init__.py`` keeps a module-level import of every route package, so
  dropping this one would be an unrelated behavioural change.

**No route decorator may be added back here.** Adding a handler to this file
registers nothing unless it is also listed in ``report_routes``' ``ROUTES``,
which is exactly the ``entity_routes`` defect that shipped once already.
``tests/test_report_route_decomposition.py`` fails if a handler reappears.
"""

from ..services.report_agent import ReportManager  # noqa: F401

__all__ = ["ReportManager"]
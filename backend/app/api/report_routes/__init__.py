"""Decomposed Report API Route Modules (exec-plan T25, ADR-0011).

These modules replace the 23 route handlers that lived in
``app/api/report.py``. Each module declares plain functions plus a ``ROUTES``
tuple; registration is explicit through :func:`register_report_routes` rather
than an import-time side effect.

Why explicit registration rather than ``@blueprint.route`` at import time:
Flask 3 refuses to add rules to a blueprint that has already been registered on
an application, and ``api/__init__.py`` imports every route module eagerly. With
import-time decorators there would be no way to obtain an *unregistered*
blueprint, so the 404-before/200-after property the exec plan requires would be
untestable -- the "before" state could not be constructed.

The same defect class this guards against is real and has happened here:
``entity_routes`` shipped unimported and ``GET /api/simulation/entities/...``
answered 404 from that commit until the import was restored. Every module in
this package must appear in ``_MODULES`` below.
"""

_MODULES = (
    "report_lifecycle_routes",
    "report_read_routes",
    "report_export_routes",
    "report_evidence_routes",
    "report_interaction_routes",
    "report_log_routes",
    "report_tool_routes",
)


def register_report_routes(blueprint):
    """Attach every decomposed report route to ``blueprint``.

    Idempotent with respect to module import (Python caches the import), but not
    with respect to the blueprint: Flask raises if the same rule is added twice.
    Call this once per blueprint, before the blueprint is registered on an app.
    """
    import importlib

    for module_name in _MODULES:
        module = importlib.import_module(f".{module_name}", __name__)
        for rule, methods, endpoint_suffix in module.ROUTES:
            view_func = getattr(module, endpoint_suffix)
            blueprint.add_url_rule(
                rule,
                # Blueprint endpoints must not carry the blueprint name; Flask
                # prepends it, yielding "report.<handler>" exactly as the
                # former @report_bp.route decorators did.
                endpoint=endpoint_suffix,
                view_func=view_func,
                methods=list(methods),
            )
    return blueprint


__all__ = ["register_report_routes"]
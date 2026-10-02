"""Guard the report-route decomposition (exec-plan T25, ADR-0011).

`backend/app/api/report.py` was a 1,437-line module holding 23 route
decorators. This module pins the properties that make the decomposition real
rather than cosmetic:

1. `api/report.py` declares no route handlers at all. It is a helper module.
2. Every handler is defined inside `app.api.report_routes`, not in the
   monolith. Asserted on the handler's ``__module__``, because the Flask
   endpoint name is ``report.<func>`` regardless of which module defines the
   function -- an endpoint-name check alone would have passed before the
   refactor.
3. Registration is explicit and observable: a blueprint with no rules answers
   404 for every report URL, and the same blueprint answers with all 23 rules
   once ``register_report_routes`` has run on it. This is the
   404-before/200-after property the exec plan requires. It is testable only
   because registration is a function rather than an import side effect --
   Flask 3 refuses to add rules to a blueprint that has already been
   registered on an app, so an import-decorated design would make the
   "before" state unconstructable.
4. The production app really is wired: `api/__init__.py` calls
   `register_report_routes(report_bp)`, and `create_app()` serves all 23 URLs.
5. No module in the package may be left unregistered. `entity_routes` shipped
   unimported and `GET /api/simulation/entities/...` answered 404 from that
   commit until the import was restored; that is the exact bug class guarded
   here.
"""

import uuid
from pathlib import Path

import pytest
from flask import Blueprint, Flask

from app.api.report_routes import register_report_routes

REPORT_BP_URL_PREFIX = "/api/report"
BLUEPRINT_NAME = "report"

# (rule, methods, handler name) for every route the monolith served.
# `/related-records` and `/evidence` are two stacked decorators on ONE handler,
# `get_report_evidence`; both must survive the split.
EXPECTED_REPORT_ROUTES = [
    ("/generate", frozenset({"POST"}), "generate_report"),
    ("/generate/status", frozenset({"GET", "POST"}), "get_generate_status"),
    ("/<report_id>/related-records", frozenset({"GET"}), "get_report_evidence"),
    ("/<report_id>/evidence", frozenset({"GET"}), "get_report_evidence"),
    ("/<report_id>", frozenset({"GET"}), "get_report"),
    ("/by-simulation/<simulation_id>", frozenset({"GET"}), "get_report_by_simulation"),
    ("/list", frozenset({"GET"}), "list_reports"),
    ("/<report_id>/download", frozenset({"GET"}), "download_report"),
    ("/<report_id>/export/pdf", frozenset({"GET"}), "export_report_pdf"),
    ("/<report_id>/export/csv", frozenset({"GET"}), "export_report_csv"),
    ("/<report_id>/export/executive", frozenset({"GET"}), "export_report_executive"),
    ("/<report_id>", frozenset({"DELETE"}), "delete_report"),
    ("/chat", frozenset({"POST"}), "chat_with_report_agent"),
    ("/<report_id>/progress", frozenset({"GET"}), "get_report_progress"),
    ("/<report_id>/sections", frozenset({"GET"}), "get_report_sections"),
    ("/<report_id>/section/<int:section_index>", frozenset({"GET"}), "get_single_section"),
    ("/check/<simulation_id>", frozenset({"GET"}), "check_report_status"),
    ("/<report_id>/agent-log", frozenset({"GET"}), "get_agent_log"),
    ("/<report_id>/agent-log/stream", frozenset({"GET"}), "stream_agent_log"),
    ("/<report_id>/console-log", frozenset({"GET"}), "get_console_log"),
    ("/<report_id>/console-log/stream", frozenset({"GET"}), "stream_console_log"),
    ("/tools/search", frozenset({"POST"}), "search_graph_tool"),
    ("/tools/statistics", frozenset({"POST"}), "get_graph_statistics_tool"),
]

API_DIR = Path(__file__).resolve().parents[1] / "app" / "api"
PACKAGE_DIR = API_DIR / "report_routes"
MONOLITH = API_DIR / "report.py"


def _build_app(with_registration: bool):
    """Build a throwaway app on a fresh, private blueprint.

    A private blueprint is required: the shared `report_bp` is populated during
    `app.api` import, so it cannot represent the unregistered state.
    """
    blueprint = Blueprint(BLUEPRINT_NAME, __name__)
    if with_registration:
        register_report_routes(blueprint)
    app = Flask(f"t25_{uuid.uuid4().hex}")
    app.register_blueprint(blueprint, url_prefix=REPORT_BP_URL_PREFIX)
    return app


def _report_rules(app):
    """Map each report URL to the union of its methods.

    A union, not a plain assignment: `/api/report/<report_id>` is registered
    twice -- once for GET (`get_report`) and once for DELETE (`delete_report`)
    -- and collapsing them would hide one of the two.
    """
    rules = {}
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith(REPORT_BP_URL_PREFIX):
            rules[rule.rule] = rules.get(rule.rule, set()) | set(rule.methods or ())
    return rules


def test_report_monolith_declares_no_route_handlers():
    """api/report.py must hold zero route decorators after the split."""
    source = MONOLITH.read_text(encoding="utf-8")
    assert "@report_bp.route" not in source, (
        "api/report.py still declares route handlers; the T25 decomposition is "
        "incomplete. Handlers belong in app/api/report_routes/."
    )


def test_evidence_handler_serves_both_routes_from_one_function():
    """The stacked decorator pair must keep both endpoints.

    `/<report_id>/related-records` and `/<report_id>/evidence` share one
    handler. Losing one leaves the other answering 200, so a per-route existence
    check that did not assert the pairing would pass on a half-finished split.
    """
    handlers = [name for _, _, name in EXPECTED_REPORT_ROUTES]
    assert handlers.count("get_report_evidence") == 2, (
        "expected /related-records and /evidence to share get_report_evidence"
    )


def test_unregistered_blueprint_answers_404_for_every_report_route():
    """404-before: with no registration, none of the 23 URLs exist."""
    app = _build_app(with_registration=False)
    rules = _report_rules(app)
    for rule, _methods, _name in EXPECTED_REPORT_ROUTES:
        full = REPORT_BP_URL_PREFIX + rule
        assert full not in rules, (
            f"{full} is present before register_report_routes() ran; the "
            "'before' state is not constructable, so this test proves nothing."
        )


def test_registration_adds_every_rule_with_its_methods():
    """200-after: registration adds all 23 rules with the expected methods."""
    app = _build_app(with_registration=True)
    rules = _report_rules(app)
    for rule, methods, _name in EXPECTED_REPORT_ROUTES:
        full = REPORT_BP_URL_PREFIX + rule
        assert full in rules, f"{full} missing after register_report_routes()"
        assert methods <= rules[full], (
            f"{full} registered with {sorted(rules[full])}, expected {sorted(methods)}"
        )


@pytest.mark.parametrize(
    "rule,methods,name",
    EXPECTED_REPORT_ROUTES,
    ids=[r for r, _, _ in EXPECTED_REPORT_ROUTES],
)
def test_each_handler_lives_in_the_report_routes_package(rule, methods, name):
    """Each handler resolves, and its defining module is the new package.

    The endpoint name is unchanged by this refactor -- it is `report.<func>`
    because the blueprint is still `report` -- so asserting only that the
    endpoint resolves would have passed before the split. Asserting on
    ``__module__`` is what makes this fail without the change.
    """
    app = _build_app(with_registration=True)
    endpoint = f"{BLUEPRINT_NAME}.{name}"
    assert endpoint in app.view_functions, f"{endpoint} not registered"
    handler = app.view_functions[endpoint]
    assert handler.__module__.startswith("app.api.report_routes"), (
        f"{endpoint} is still defined in {handler.__module__}; it must be moved "
        "into app/api/report_routes/"
    )


def test_every_module_in_the_package_is_registered():
    """The entity_routes guard: no module may exist but stay unregistered."""
    init_source = (PACKAGE_DIR / "__init__.py").read_text(encoding="utf-8")
    modules = sorted(p.stem for p in PACKAGE_DIR.glob("*_routes.py"))
    assert modules, "no route modules found; the package is empty"
    unregistered = [m for m in modules if m not in init_source]
    assert not unregistered, (
        f"route module(s) {unregistered} exist but are not named in "
        "app/api/report_routes/__init__.py; their routes would answer 404"
    )


def test_api_package_registers_the_routes():
    """api/__init__.py must call register_report_routes(report_bp).

    Without this the routes are registered nowhere and every report endpoint
    404s in production while every other test in this file -- which builds its
    own blueprint -- still passes.
    """
    api_init = (API_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "register_report_routes" in api_init, (
        "app/api/__init__.py never calls register_report_routes(report_bp)"
    )


def test_real_application_serves_every_report_route():
    """The real app factory serves all 23 URLs and none of them 404.

    The only test that exercises `create_app()` end to end, so it is what
    catches a route that exists on a synthetic blueprint but was never wired
    into the application that actually answers requests.
    """
    from app import create_app

    app = create_app()
    rules = _report_rules(app)
    missing = [
        REPORT_BP_URL_PREFIX + rule
        for rule, _m, _n in EXPECTED_REPORT_ROUTES
        if REPORT_BP_URL_PREFIX + rule not in rules
    ]
    assert not missing, f"routes missing from the real app: {missing}"

    client = app.test_client()
    for url in (
        "/api/report/list",
        "/api/report/generate/status?simulation_id=nope",
        "/api/report/check/nope",
    ):
        response = client.get(url)
        assert response.status_code != 404, f"{url} answered 404 on the real app"
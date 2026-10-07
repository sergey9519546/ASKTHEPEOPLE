"""SLO and cost-budget configuration (Gate 4, exec-plan T29).

Two separable claims are under test, and the second is the one that usually
gets skipped.

**The declaration is honest.** Every SLO is stated over a series that
`GET /health/metrics` actually exports, over a threshold that the exposed
histogram can actually answer. A percentile the metrics module cannot produce is
not an objective, so the latency threshold is pinned to `LATENCY_BUCKETS` rather
than to a number that merely looks plausible. The cost budget's breach action is
pinned to what the tree can do: a run's cost is not measured anywhere, so an
action that claims to stop one is refused rather than accepted.

**The refusal is enforced where it matters.** `Config.validate()` had exactly
one non-test call site, which is why `create_app` calls
`validate_production_gates()` directly. Asserting on the validator in isolation
would pass against code that enforces nothing at boot, so the refusal tests boot
the real application factory.

Scope: these settings are inert by default. A test that only checked the
defaults would also pass against a file that added a dozen knobs and wired
nothing, so every test below either sets a value, breaks one, or asserts a
default's inertness.
"""

from __future__ import annotations

import importlib

import pytest

from app import config as config_module
from app import create_app
from app.config import COST_BUDGET_BREACH_ACTIONS, Config

SECRET = "strong-secret-key-7b9f3d2c8a6e4f10"
TOKEN = "private-access-key-7b9f3d2c8a6e4f10"


def _read_with_env(monkeypatch, attr: str, env: dict[str, str]):
    """Reload `app.config` with `env` applied, read `attr`, then restore.

    `Config` reads its environment in the class body, so patching
    `os.environ` after import has no effect and the module has to be reloaded.
    The module is reloaded back unconditionally in `finally`: a value that
    raises while the class body executes must not leave the module
    half-initialised for the next test.

    Returns `(ok, value)`, where `value` is the attribute on success and the
    raised message on failure.
    """
    try:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        try:
            importlib.reload(config_module)
            return True, getattr(config_module.Config, attr)
        except RuntimeError as exc:
            return False, str(exc)
    finally:
        for key in env:
            monkeypatch.delenv(key, raising=False)
        importlib.reload(config_module)


def production_config(**overrides):
    """A Config subclass shaped like a real production deployment.

    Subclassing rather than patching means the shared `Config` is never
    mutated, and `validate_production_gates` is a classmethod so it reads the
    subclass's own attributes.
    """
    base = {
        "DEBUG": False,
        "SECRET_KEY": SECRET,
        "REQUIRE_APP_AUTH": True,
        "APP_TOKEN": TOKEN,
        "CORS_ORIGINS": "https://app.example.test",
        "TRUSTED_HOSTS": ["app.example.test", "localhost"],
    }
    base.update(overrides)
    return type("ProductionConfig", (Config,), base)


# --- defaults ------------------------------------------------------------- #


class TestDefaultsAreInert:
    def test_slo_is_off_and_declares_nothing(self):
        assert Config.SLO_ENABLED is False

    def test_cost_budget_is_off_with_no_ceiling(self):
        assert Config.COST_BUDGET_ENABLED is False
        assert Config.COST_BUDGET_MAX_USD_PER_RUN == 0.0
        assert Config.COST_BUDGET_MAX_USD_PER_DAY == 0.0

    def test_breach_action_defaults_to_the_only_honest_value(self):
        assert Config.COST_BUDGET_BREACH_ACTION == "warn"

    def test_documented_default_values(self):
        """The defaults are the ones `.env.example` and the doc publish."""
        assert Config.SLO_LATENCY_BUCKET_SECONDS == 1.0
        assert Config.SLO_LATENCY_TARGET_RATIO == 0.99
        assert Config.SLO_ERROR_RATE_MAX_RATIO == 0.001
        assert Config.SLO_WINDOW_SECONDS == 2592000
        assert Config.SLO_MIN_REQUESTS == 20

    def test_defaults_report_no_production_gate_failure(self):
        """Inert means inert: a deployment that sets nothing still boots."""
        assert production_config().validate_production_gates() == []

    def test_default_production_configuration_boots(self):
        assert create_app(production_config()) is not None


# --- the objectives reference metrics that exist ------------------------- #


class TestObjectivesAreMeasurable:
    def test_latency_threshold_is_a_bucket_the_histogram_has(self):
        from app.utils.metrics import LATENCY_BUCKETS

        assert Config.SLO_LATENCY_BUCKET_SECONDS in LATENCY_BUCKETS

    def test_every_series_named_by_the_objectives_is_exported(self):
        """The SLO formulas name four series. If one is not in the
        exposition, the objective is unmeasurable and the doc is fiction."""
        from app.utils.metrics import MetricsRegistry, render_prometheus

        registry = MetricsRegistry()
        registry.observe("GET", "health_bp.health", 200, 0.02)
        registry.observe("GET", "health_bp.health", 500, 4.0)
        out = render_prometheus(registry)

        assert "askthepeople_http_requests_total" in out
        assert 'status_class="5xx"' in out, "the error objective needs a 5xx series"
        assert "askthepeople_http_request_duration_bucket" in out
        assert 'le="+Inf"' in out, "the denominator needs the +Inf bucket"
        assert f'le="{Config.SLO_LATENCY_BUCKET_SECONDS}"' in out, (
            "the default latency threshold has no bucket line to divide by"
        )

    def test_the_5xx_series_a_run_would_raise_is_counted_not_swallowed(self):
        """A failing request must appear in the denominator too, or an
        objective could be met by failing everything."""
        from app.utils.metrics import MetricsRegistry

        registry = MetricsRegistry()
        registry.observe("GET", "a", 200, 0.01)
        registry.observe("GET", "a", 500, 0.01)
        rows = {(r["status_class"]): r["count"] for r in registry.snapshot()["requests"]}
        assert rows == {"2xx": 1, "5xx": 1}


# --- overrides ------------------------------------------------------------ #


class TestOperatorOverrides:
    @pytest.mark.parametrize(
        "attr,env,expected",
        [
            ("SLO_ENABLED", {"SLO_ENABLED": "true"}, True),
            ("SLO_ENABLED", {"SLO_ENABLED": "TRUE"}, True),
            ("SLO_ENABLED", {"SLO_ENABLED": "false"}, False),
            ("SLO_ENABLED", {"SLO_ENABLED": "1"}, False),
            ("SLO_LATENCY_BUCKET_SECONDS", {"SLO_LATENCY_BUCKET_SECONDS": "0.5"}, 0.5),
            ("SLO_LATENCY_BUCKET_SECONDS", {"SLO_LATENCY_BUCKET_SECONDS": "10"}, 10.0),
            ("SLO_LATENCY_TARGET_RATIO", {"SLO_LATENCY_TARGET_RATIO": "0.95"}, 0.95),
            ("SLO_ERROR_RATE_MAX_RATIO", {"SLO_ERROR_RATE_MAX_RATIO": "0.01"}, 0.01),
            ("SLO_ERROR_RATE_MAX_RATIO", {"SLO_ERROR_RATE_MAX_RATIO": "0"}, 0.0),
            ("SLO_WINDOW_SECONDS", {"SLO_WINDOW_SECONDS": "86400"}, 86400),
            ("SLO_MIN_REQUESTS", {"SLO_MIN_REQUESTS": "5"}, 5),
            ("COST_BUDGET_ENABLED", {"COST_BUDGET_ENABLED": "true"}, True),
            ("COST_BUDGET_MAX_USD_PER_RUN", {"COST_BUDGET_MAX_USD_PER_RUN": "2.5"}, 2.5),
            ("COST_BUDGET_MAX_USD_PER_DAY", {"COST_BUDGET_MAX_USD_PER_DAY": "50"}, 50.0),
        ],
    )
    def test_env_changes_the_resolved_value(self, monkeypatch, attr, env, expected):
        ok, value = _read_with_env(monkeypatch, attr, env)
        assert ok, value
        assert value == expected
        assert type(value) is type(expected)

    @pytest.mark.parametrize("raw", ["warn", "WARN", "  warn  "])
    def test_breach_action_is_normalised(self, monkeypatch, raw):
        ok, value = _read_with_env(
            monkeypatch, "COST_BUDGET_BREACH_ACTION", {"COST_BUDGET_BREACH_ACTION": raw}
        )
        assert ok, value
        assert value == "warn"

    def test_a_valid_operator_configuration_boots(self):
        config = production_config(
            SLO_ENABLED=True,
            SLO_LATENCY_BUCKET_SECONDS=0.5,
            SLO_LATENCY_TARGET_RATIO=0.95,
            SLO_ERROR_RATE_MAX_RATIO=0.005,
            SLO_WINDOW_SECONDS=86400,
            SLO_MIN_REQUESTS=50,
            COST_BUDGET_ENABLED=True,
            COST_BUDGET_MAX_USD_PER_RUN=2.5,
            COST_BUDGET_MAX_USD_PER_DAY=50.0,
            COST_BUDGET_BREACH_ACTION="warn",
        )
        assert config.validate_production_gates() == []
        assert create_app(config) is not None


# --- malformed values ----------------------------------------------------- #


class TestMalformedValuesAreRefused:
    @pytest.mark.parametrize(
        "attr,env",
        [
            ("SLO_LATENCY_BUCKET_SECONDS", {"SLO_LATENCY_BUCKET_SECONDS": "fast"}),
            ("SLO_LATENCY_BUCKET_SECONDS", {"SLO_LATENCY_BUCKET_SECONDS": ""}),
            ("SLO_LATENCY_BUCKET_SECONDS", {"SLO_LATENCY_BUCKET_SECONDS": "1,0"}),
            ("SLO_LATENCY_TARGET_RATIO", {"SLO_LATENCY_TARGET_RATIO": "99%"}),
            ("SLO_ERROR_RATE_MAX_RATIO", {"SLO_ERROR_RATE_MAX_RATIO": "none"}),
            ("SLO_WINDOW_SECONDS", {"SLO_WINDOW_SECONDS": "thirty days"}),
            ("SLO_MIN_REQUESTS", {"SLO_MIN_REQUESTS": "many"}),
            ("COST_BUDGET_MAX_USD_PER_RUN", {"COST_BUDGET_MAX_USD_PER_RUN": "$5"}),
            ("COST_BUDGET_MAX_USD_PER_DAY", {"COST_BUDGET_MAX_USD_PER_DAY": "50 USD"}),
        ],
    )
    def test_unparseable_number_names_the_variable_and_raises(self, monkeypatch, attr, env):
        """A malformed ceiling must not fall back to the default. Substituting
        0.0 for a mistyped ceiling turns "refuse this run" into "no ceiling"."""
        ok, message = _read_with_env(monkeypatch, attr, env)
        assert ok is False
        assert list(env)[0] in message

    @pytest.mark.parametrize(
        "attr,env",
        [
            ("SLO_LATENCY_TARGET_RATIO", {"SLO_LATENCY_TARGET_RATIO": "nan"}),
            ("SLO_LATENCY_TARGET_RATIO", {"SLO_LATENCY_TARGET_RATIO": "NaN"}),
            ("SLO_ERROR_RATE_MAX_RATIO", {"SLO_ERROR_RATE_MAX_RATIO": "inf"}),
            ("SLO_ERROR_RATE_MAX_RATIO", {"SLO_ERROR_RATE_MAX_RATIO": "-inf"}),
            ("COST_BUDGET_MAX_USD_PER_RUN", {"COST_BUDGET_MAX_USD_PER_RUN": "nan"}),
            ("COST_BUDGET_MAX_USD_PER_DAY", {"COST_BUDGET_MAX_USD_PER_DAY": "Infinity"}),
        ],
    )
    def test_nan_and_infinity_are_refused(self, monkeypatch, attr, env):
        """`nan` and `inf` parse. Both also fail every comparison, so a `nan`
        ceiling would read as never breached and stay unlimited while looking
        configured."""
        ok, message = _read_with_env(monkeypatch, attr, env)
        assert ok is False
        assert "finite" in message

    def test_fractional_count_is_refused(self, monkeypatch):
        ok, message = _read_with_env(
            monkeypatch, "SLO_MIN_REQUESTS", {"SLO_MIN_REQUESTS": "20.5"}
        )
        assert ok is False
        assert "whole number" in message

    def test_the_module_is_usable_after_a_refused_reload(self, monkeypatch):
        """A class body that raises leaves the previous binding intact. If that
        ever stopped being true, one bad env var would poison the process."""
        assert not _read_with_env(
            monkeypatch, "SLO_WINDOW_SECONDS", {"SLO_WINDOW_SECONDS": "soon"}
        )[0]
        assert Config.SLO_WINDOW_SECONDS == 2592000
        assert create_app(production_config()) is not None


# --- refusals ------------------------------------------------------------- #


class TestProductionGatewayRefusesUnusableSlo:
    @pytest.mark.parametrize(
        "overrides,expected",
        [
            ({"SLO_ENABLED": True, "SLO_LATENCY_BUCKET_SECONDS": 0.75}, "0.75"),
            ({"SLO_ENABLED": True, "SLO_LATENCY_BUCKET_SECONDS": 30.0}, "30.0"),
            ({"SLO_ENABLED": True, "SLO_LATENCY_TARGET_RATIO": 1.5}, "1.5"),
            ({"SLO_ENABLED": True, "SLO_LATENCY_TARGET_RATIO": 0.0}, "0.0"),
            ({"SLO_ENABLED": True, "SLO_ERROR_RATE_MAX_RATIO": 1.0}, "1.0"),
            ({"SLO_ENABLED": True, "SLO_ERROR_RATE_MAX_RATIO": -0.1}, "-0.1"),
            ({"SLO_ENABLED": True, "SLO_WINDOW_SECONDS": 0}, "SLO_WINDOW_SECONDS"),
            ({"SLO_ENABLED": True, "SLO_MIN_REQUESTS": 0}, "SLO_MIN_REQUESTS"),
        ],
    )
    def test_bad_slo_values_refuse_to_boot(self, overrides, expected):
        config = production_config(**overrides)
        assert any(expected in error for error in config.validate_production_gates())
        with pytest.raises(RuntimeError) as caught:
            create_app(config)
        assert expected in str(caught.value)

    def test_the_off_flag_is_not_subject_to_the_slo_refusals(self):
        """A malformed objective that nobody enabled asserts nothing."""
        config = production_config(SLO_LATENCY_BUCKET_SECONDS=0.75)
        assert config.validate_production_gates() == []


class TestProductionGatewayRefusesUnusableCostBudget:
    def test_enabled_with_no_ceiling_refuses_to_boot(self):
        """The false-assurance case: a budget of nothing that reads as a
        budget."""
        config = production_config(COST_BUDGET_ENABLED=True)
        with pytest.raises(RuntimeError) as caught:
            create_app(config)
        message = str(caught.value)
        assert "COST_BUDGET_ENABLED" in message
        assert "COST_BUDGET_MAX_USD_PER_RUN" in message

    def test_negative_ceiling_refuses_to_boot(self):
        config = production_config(
            COST_BUDGET_ENABLED=True,
            COST_BUDGET_MAX_USD_PER_RUN=-1.0,
        )
        with pytest.raises(RuntimeError) as caught:
            create_app(config)
        assert "COST_BUDGET_MAX_USD_PER_RUN" in str(caught.value)

    def test_unknown_breach_action_refuses_to_boot(self):
        config = production_config(
            COST_BUDGET_ENABLED=True,
            COST_BUDGET_MAX_USD_PER_RUN=5.0,
            COST_BUDGET_BREACH_ACTION="degrade",
        )
        with pytest.raises(RuntimeError) as caught:
            create_app(config)
        assert "degrade" in str(caught.value)

    def test_refusing_a_run_refuses_to_boot_and_says_why(self):
        """`refuse` is the right target and is not selectable yet. The refusal
        has to be louder than a documentation note, because the alternative is
        an operator reading a control as active when nothing reads the ceiling.
        """
        config = production_config(
            COST_BUDGET_ENABLED=True,
            COST_BUDGET_MAX_USD_PER_RUN=5.0,
            COST_BUDGET_BREACH_ACTION="refuse",
        )
        with pytest.raises(RuntimeError) as caught:
            create_app(config)
        message = str(caught.value)
        assert "COST_BUDGET_BREACH_ACTION=refuse" in message
        # The message must point at the seam, or the operator cannot act on it.
        assert "run_preflight" in message

    def test_refuse_is_in_the_accepted_set_so_the_refusal_is_about_the_meter(self):
        """If `refuse` were merely unknown, this test would pass for the wrong
        reason: it must be a recognised action that is refused for being
        unkeepable."""
        assert "refuse" in COST_BUDGET_BREACH_ACTIONS
        assert "degrade" not in COST_BUDGET_BREACH_ACTIONS

    def test_every_breach_failure_is_reported_at_once(self):
        """An operator fixing their config should see the whole list, not
        discover it one restart at a time."""
        config = production_config(
            SLO_ENABLED=True,
            SLO_LATENCY_BUCKET_SECONDS=0.75,
            COST_BUDGET_ENABLED=True,
            COST_BUDGET_BREACH_ACTION="degrade",
        )
        with pytest.raises(RuntimeError) as caught:
            create_app(config)
        message = str(caught.value)
        assert "0.75" in message
        assert "degrade" in message


# --- the refusals cannot drift apart -------------------------------------- #


class TestGatewayAndFullValidatorAgree:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"SLO_ENABLED": True, "SLO_LATENCY_BUCKET_SECONDS": 0.75},
            {"SLO_ENABLED": True, "SLO_ERROR_RATE_MAX_RATIO": 1.0},
            {"SLO_ENABLED": True, "SLO_WINDOW_SECONDS": 0},
            {"COST_BUDGET_ENABLED": True},
            {"COST_BUDGET_ENABLED": True, "COST_BUDGET_MAX_USD_PER_DAY": -3.0},
            {
                "COST_BUDGET_ENABLED": True,
                "COST_BUDGET_MAX_USD_PER_RUN": 1.0,
                "COST_BUDGET_BREACH_ACTION": "shrug",
            },
            {
                "COST_BUDGET_ENABLED": True,
                "COST_BUDGET_MAX_USD_PER_RUN": 1.0,
                "COST_BUDGET_BREACH_ACTION": "refuse",
            },
        ],
    )
    def test_every_gateway_refusal_is_also_in_the_full_validator(self, overrides):
        config = production_config(**overrides)
        gateway = config.validate_production_gates()
        full = config.validate()
        assert gateway, "the gateway must report the unsafe configuration"
        for message in gateway:
            assert any(message in candidate for candidate in full), (
                f"gateway refusal absent from validate(): {message}"
            )

    def test_debug_is_exempt_from_the_slo_and_budget_refusals(self):
        """A production safety rule must not make local development
        impossible."""
        config = production_config(
            DEBUG=True,
            SLO_ENABLED=True,
            SLO_LATENCY_BUCKET_SECONDS=0.75,
            COST_BUDGET_ENABLED=True,
            COST_BUDGET_BREACH_ACTION="refuse",
        )
        assert config.validate_production_gates() == []
        assert not any(
            "SLO_" in error or "COST_BUDGET" in error for error in config.validate()
        )

    def test_the_refusals_are_reported_by_a_single_helper(self):
        """Both validators call `_slo_and_cost_budget_errors`, which is what
        makes the agreement above structural rather than coincidental."""
        config = production_config(COST_BUDGET_ENABLED=True)
        helper = config._slo_and_cost_budget_errors()
        assert helper, "an enabled budget with no ceiling must be reported"
        assert helper == config.validate_production_gates()
        assert all(error in config.validate() for error in helper)

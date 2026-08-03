"""Acceptance tests for the resource-constraint / feasibility engine.

These are behavioral tests, not coverage theatre. The central claim under test
is the HARD / SOFT / PROBABILISTIC split: a hard violation must block, a soft
violation must be reported without blocking, and probabilistic pressure must
multiply into a success probability while leaving feasibility alone. If those
three cases ever collapse into each other the module is worthless, so each is
pinned from both directions.
"""

from __future__ import annotations

import pytest

from app.services.constraint_engine import (
    PUBLIC_KNOWLEDGE_KEY,
    Action,
    CircularDependencyError,
    Constraint,
    ConstraintType,
    Enforcement,
    actor_capacities,
    can_act_on_information,
    check_feasibility,
    degrade_action,
    normalize_constraints,
    resolve_dependencies,
    visible_facts,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def actor(actor_id: str, *constraints: Constraint, knowledge=None) -> dict:
    """Return a plain-dict actor. The engine must never require a dataclass."""
    payload: dict = {"id": actor_id, "constraints": list(constraints)}
    if knowledge is not None:
        payload["knowledge"] = set(knowledge)
    return payload


def budget(capacity: float, enforcement: Enforcement, label: str = "budget") -> Constraint:
    return Constraint(
        type=ConstraintType.BUDGET,
        capacity=capacity,
        enforcement=enforcement,
        label=label,
    )


def spend(amount: float, label: str = "buy ads", **kwargs) -> Action:
    return Action(label=label, costs={ConstraintType.BUDGET: amount}, **kwargs)


# ---------------------------------------------------------------------------
# 1. HARD blocks; SOFT does not block but is reported
# ---------------------------------------------------------------------------


def test_hard_budget_violation_blocks_the_action():
    result = check_feasibility(
        actor("city_council", budget(1_000.0, Enforcement.HARD, "statutory budget cap")),
        spend(5_000.0),
    )

    assert result.feasible is False
    assert len(result.blocking) == 1
    assert result.blocking[0].type is ConstraintType.BUDGET
    assert result.blocking[0].enforcement is Enforcement.HARD
    # A hard violation is never silently downgraded into a penalty.
    assert result.penalties == []
    assert result.penalty_cost == 0.0
    assert result.expected_to_succeed is False
    assert "statutory budget cap" in result.reason
    assert "BLOCKED" in result.reason


def test_soft_budget_violation_does_not_block_but_is_reported():
    result = check_feasibility(
        actor("startup", budget(1_000.0, Enforcement.SOFT, "internal budget guidance")),
        spend(5_000.0),
    )

    # The whole point of the module: over budget, still allowed.
    assert result.feasible is True
    assert result.blocking == []
    assert len(result.penalties) == 1

    penalty = result.penalties[0]
    assert penalty.constraint.enforcement is Enforcement.SOFT
    assert penalty.required == 5_000.0
    assert penalty.capacity == 1_000.0
    assert penalty.overage == 4_000.0
    assert result.penalty_cost == 4_000.0
    assert result.expected_to_succeed is True
    assert "internal budget guidance" in result.reason


def test_hard_and_soft_on_the_same_actor_are_reported_separately():
    result = check_feasibility(
        actor(
            "agency",
            budget(1_000.0, Enforcement.HARD, "appropriation ceiling"),
            Constraint(
                type=ConstraintType.TIME,
                capacity=8.0,
                enforcement=Enforcement.SOFT,
                label="staff hours",
            ),
        ),
        Action(
            label="emergency procurement",
            costs={ConstraintType.BUDGET: 4_000.0, ConstraintType.TIME: 40.0},
        ),
    )

    assert result.feasible is False
    assert [constraint.type for constraint in result.blocking] == [ConstraintType.BUDGET]
    assert [penalty.constraint.type for penalty in result.penalties] == [ConstraintType.TIME]
    assert result.penalties[0].overage == 32.0


def test_cost_within_capacity_is_neither_blocked_nor_penalised():
    for enforcement in (Enforcement.HARD, Enforcement.SOFT):
        result = check_feasibility(actor("a", budget(1_000.0, enforcement)), spend(999.0))
        assert result.feasible is True, enforcement
        assert result.blocking == [], enforcement
        assert result.penalties == [], enforcement
        assert result.success_probability == 1.0, enforcement


def test_cost_exactly_at_capacity_is_allowed_not_violated():
    result = check_feasibility(actor("a", budget(1_000.0, Enforcement.HARD)), spend(1_000.0))
    assert result.feasible is True
    assert result.blocking == []


def test_constraint_on_a_resource_the_action_does_not_use_is_never_violated():
    result = check_feasibility(
        actor("a", Constraint(ConstraintType.LEGAL, 0.0, Enforcement.HARD, "no permit")),
        spend(10.0),
    )
    assert result.feasible is True
    assert result.blocking == []


def test_result_serializes_hard_and_soft_distinctly():
    payload = check_feasibility(
        actor(
            "mixed",
            budget(10.0, Enforcement.HARD, "hard cap"),
            Constraint(ConstraintType.SOCIAL, 1.0, Enforcement.SOFT, "reputation"),
        ),
        Action(
            label="risky push",
            costs={ConstraintType.BUDGET: 50.0, ConstraintType.SOCIAL: 9.0},
        ),
    ).as_dict()

    assert payload["feasible"] is False
    assert [entry["label"] for entry in payload["blocking"]] == ["hard cap"]
    assert [entry["label"] for entry in payload["penalties"]] == ["reputation"]
    assert payload["penalties"][0]["overage"] == 8.0


# ---------------------------------------------------------------------------
# 2. PROBABILISTIC constraints multiply
# ---------------------------------------------------------------------------


def test_probabilistic_constraints_multiply_into_success_probability():
    subject = actor(
        "lobbyist",
        # needs 100, has 50  -> factor 0.5
        Constraint(ConstraintType.SOCIAL, 50.0, Enforcement.PROBABILISTIC, "coalition"),
        # needs 100, has 25  -> factor 0.25
        Constraint(ConstraintType.LEGAL, 25.0, Enforcement.PROBABILISTIC, "waiver odds"),
    )
    action = Action(
        label="pass amendment",
        costs={ConstraintType.SOCIAL: 100.0, ConstraintType.LEGAL: 100.0},
    )

    result = check_feasibility(subject, action)

    assert result.success_probability == pytest.approx(0.125)  # 0.5 * 0.25
    # Probabilistic pressure is not a block and not a penalty.
    assert result.feasible is True
    assert result.blocking == []
    assert result.penalties == []
    assert result.expected_to_succeed is True


def test_probabilistic_constraint_within_capacity_contributes_one():
    result = check_feasibility(
        actor("a", Constraint(ConstraintType.SOCIAL, 100.0, Enforcement.PROBABILISTIC)),
        Action(label="ask", costs={ConstraintType.SOCIAL: 40.0}),
    )
    assert result.success_probability == 1.0


def test_zero_capacity_probabilistic_yields_zero_probability_without_blocking():
    result = check_feasibility(
        actor("a", Constraint(ConstraintType.LEGAL, 0.0, Enforcement.PROBABILISTIC, "odds")),
        Action(label="sue", costs={ConstraintType.LEGAL: 5.0}),
    )

    # Feasible means "not forbidden"; it deliberately does not mean "will work".
    assert result.feasible is True
    assert result.success_probability == 0.0
    assert result.expected_to_succeed is False


def test_probability_is_clamped_to_unit_interval():
    result = check_feasibility(
        actor(
            "a",
            Constraint(ConstraintType.SOCIAL, 10.0, Enforcement.PROBABILISTIC),
            Constraint(ConstraintType.TIME, 10.0, Enforcement.PROBABILISTIC),
        ),
        Action(label="x", costs={ConstraintType.SOCIAL: 1_000.0, ConstraintType.TIME: 1.0}),
    )
    assert 0.0 <= result.success_probability <= 1.0
    assert result.success_probability == pytest.approx(0.01)


def test_hard_block_and_probabilistic_degradation_coexist():
    result = check_feasibility(
        actor(
            "a",
            budget(10.0, Enforcement.HARD, "cap"),
            Constraint(ConstraintType.SOCIAL, 50.0, Enforcement.PROBABILISTIC, "support"),
        ),
        Action(label="push", costs={ConstraintType.BUDGET: 99.0, ConstraintType.SOCIAL: 100.0}),
    )

    assert result.feasible is False
    assert result.success_probability == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 3. Dependency waves
# ---------------------------------------------------------------------------


def test_chain_dependencies_produce_sequential_waves():
    waves = resolve_dependencies(
        {
            "A": Action(label="draft"),
            "B": Action(label="review", requires_approval_from=["A"]),
            "C": Action(label="sign", requires_approval_from=["B"]),
        }
    )
    assert waves == [["A"], ["B"], ["C"]]


def test_diamond_dependencies_put_independent_actors_in_the_same_wave():
    waves = resolve_dependencies(
        {
            "A": Action(label="propose"),
            "B": Action(label="legal review", requires_approval_from=["A"]),
            "C": Action(label="finance review", requires_approval_from=["A"]),
            "D": Action(label="execute", requires_approval_from=["B", "C"]),
        }
    )
    assert waves == [["A"], ["B", "C"], ["D"]]


def test_independent_actors_all_land_in_one_wave():
    waves = resolve_dependencies(
        {"A": Action(label="a"), "B": Action(label="b"), "C": Action(label="c")}
    )
    assert waves == [["A", "B", "C"]]


def test_every_actor_appears_exactly_once_across_waves():
    waves = resolve_dependencies(
        {
            "A": Action(label="a"),
            "B": Action(label="b", requires_approval_from=["A"]),
            "C": Action(label="c", requires_approval_from=["A"]),
            "D": Action(label="d", requires_approval_from=["B", "C"]),
            "E": Action(label="e", requires_approval_from=["D"]),
        }
    )
    flattened = [actor_id for wave in waves for actor_id in wave]
    assert sorted(flattened) == ["A", "B", "C", "D", "E"]
    assert len(flattened) == len(set(flattened))


def test_approvals_from_multiple_actions_are_unioned():
    waves = resolve_dependencies(
        {
            "A": Action(label="a"),
            "B": Action(label="b"),
            "C": [
                Action(label="c1", requires_approval_from=["A"]),
                Action(label="c2", requires_approval_from=["B"]),
            ],
        }
    )
    assert waves == [["A", "B"], ["C"]]


def test_unmodelled_approver_is_surfaced_in_the_first_wave():
    waves = resolve_dependencies(
        {"B": Action(label="build", requires_approval_from=["regulator"])}
    )
    assert waves == [["regulator"], ["B"]]


# ---------------------------------------------------------------------------
# 4. Circular approval chains
# ---------------------------------------------------------------------------


def test_circular_approval_chain_raises_and_names_the_actors():
    with pytest.raises(CircularDependencyError) as excinfo:
        resolve_dependencies(
            {
                "A": Action(label="a", requires_approval_from=["C"]),
                "B": Action(label="b", requires_approval_from=["A"]),
                "C": Action(label="c", requires_approval_from=["B"]),
            }
        )

    message = str(excinfo.value)
    for name in ("A", "B", "C"):
        assert name in message, message
    assert set(excinfo.value.actors) == {"A", "B", "C"}
    assert "Circular" in message


def test_two_actor_deadlock_raises_with_both_names():
    with pytest.raises(CircularDependencyError) as excinfo:
        resolve_dependencies(
            {
                "mayor": Action(label="fund", requires_approval_from=["treasurer"]),
                "treasurer": Action(label="release", requires_approval_from=["mayor"]),
            }
        )

    assert set(excinfo.value.actors) == {"mayor", "treasurer"}
    assert "mayor" in str(excinfo.value)
    assert "treasurer" in str(excinfo.value)


def test_self_approval_is_a_cycle():
    with pytest.raises(CircularDependencyError) as excinfo:
        resolve_dependencies({"A": Action(label="a", requires_approval_from=["A"])})

    assert excinfo.value.actors == ("A",)
    assert "A" in str(excinfo.value)


def test_cycle_is_detected_even_when_acyclic_actors_exist():
    with pytest.raises(CircularDependencyError) as excinfo:
        resolve_dependencies(
            {
                "clean_1": Action(label="ok"),
                "clean_2": Action(label="ok2", requires_approval_from=["clean_1"]),
                "loop_x": Action(label="x", requires_approval_from=["loop_y"]),
                "loop_y": Action(label="y", requires_approval_from=["loop_x"]),
            }
        )

    assert set(excinfo.value.actors) == {"loop_x", "loop_y"}
    # The clean actors are not blamed for the deadlock.
    assert "clean_1" not in excinfo.value.actors


# ---------------------------------------------------------------------------
# 5. Information asymmetry
# ---------------------------------------------------------------------------


def test_identical_actors_with_different_knowledge_get_different_feasibility():
    action = Action(
        label="short the stock",
        costs={ConstraintType.BUDGET: 100.0},
        requires_knowledge={"merger_is_failing"},
    )
    constraint = budget(1_000.0, Enforcement.HARD)

    informed = check_feasibility(
        actor("insider", constraint, knowledge={"merger_is_failing"}), action
    )
    uninformed = check_feasibility(actor("outsider", constraint), action)

    # Same constraints, same action, same budget headroom. Only knowledge differs.
    assert informed.feasible is True
    assert uninformed.feasible is False
    assert uninformed.missing_knowledge == {"merger_is_failing"}
    assert "merger_is_failing" in uninformed.reason
    assert uninformed.blocking[0].type is ConstraintType.INFORMATION
    assert uninformed.blocking[0].enforcement is Enforcement.HARD


def test_partial_knowledge_still_blocks():
    action = Action(label="act", requires_knowledge={"fact_a", "fact_b"})
    result = check_feasibility(actor("partial", knowledge={"fact_a"}), action)

    assert result.feasible is False
    assert result.missing_knowledge == {"fact_b"}


def test_visible_facts_respects_private_public_and_shared_knowledge():
    graph = {
        PUBLIC_KNOWLEDGE_KEY: {"published_budget"},
        "alice": {"facts": {"secret_plan"}, "shares_with": ["bob"]},
        "carol": {"carol_only"},
    }

    assert visible_facts("alice", graph) == {"published_budget", "secret_plan"}
    assert visible_facts("bob", graph) == {"published_budget", "secret_plan"}
    assert visible_facts("carol", graph) == {"published_budget", "carol_only"}
    # An actor nobody modelled sees only what is public.
    assert visible_facts("stranger", graph) == {"published_budget"}


def test_visible_facts_does_not_mutate_the_graph():
    graph = {"alice": {"a"}, PUBLIC_KNOWLEDGE_KEY: {"p"}}
    before = {key: set(value) for key, value in graph.items()}
    visible_facts("alice", graph)
    assert {key: set(value) for key, value in graph.items()} == before


def test_can_act_on_information_reads_from_a_knowledge_graph():
    action = Action(label="trade", requires_knowledge={"secret_plan"})
    graph = {"alice": {"facts": {"secret_plan"}, "shares_with": ["bob"]}}

    assert can_act_on_information({"id": "alice"}, action, graph) is True
    assert can_act_on_information({"id": "bob"}, action, graph) is True
    assert can_act_on_information({"id": "dave"}, action, graph) is False


def test_can_act_on_information_accepts_a_flat_fact_collection():
    action = Action(label="trade", requires_knowledge={"x"})
    assert can_act_on_information({"id": "a"}, action, {"x", "y"}) is True
    assert can_act_on_information({"id": "a"}, action, {"y"}) is False


def test_action_requiring_no_knowledge_is_always_informationally_permitted():
    assert can_act_on_information({"id": "a"}, Action(label="breathe"), None) is True
    assert can_act_on_information({"id": "a"}, Action(label="breathe"), {}) is True


# ---------------------------------------------------------------------------
# 6. Degradation
# ---------------------------------------------------------------------------


def test_degrade_returns_the_original_action_when_fully_affordable():
    action = spend(100.0)
    assert degrade_action(action, {ConstraintType.BUDGET: 500.0}) is action


def test_degrade_scales_down_to_what_is_affordable():
    action = Action(
        label="ad campaign",
        costs={ConstraintType.BUDGET: 1_000.0, ConstraintType.TIME: 20.0},
        min_scale=0.1,
    )

    degraded = degrade_action(action, {ConstraintType.BUDGET: 250.0})

    assert degraded is not None
    assert degraded.scale == pytest.approx(0.25)
    assert degraded.costs[ConstraintType.BUDGET] == pytest.approx(250.0)
    # Every cost scales together, not just the binding one.
    assert degraded.costs[ConstraintType.TIME] == pytest.approx(5.0)
    assert "scaled" in degraded.label
    # The original is untouched.
    assert action.costs[ConstraintType.BUDGET] == 1_000.0
    assert action.scale == 1.0


def test_degrade_uses_the_tightest_binding_resource():
    action = Action(
        label="outreach",
        costs={ConstraintType.BUDGET: 100.0, ConstraintType.TIME: 100.0},
        min_scale=0.1,
    )

    degraded = degrade_action(
        action, {ConstraintType.BUDGET: 80.0, ConstraintType.TIME: 30.0}
    )

    assert degraded is not None
    assert degraded.scale == pytest.approx(0.3)
    assert degraded.costs[ConstraintType.BUDGET] == pytest.approx(30.0)


def test_degraded_action_is_actually_feasible_for_the_actor():
    subject = actor("frugal", budget(250.0, Enforcement.HARD, "hard cap"))
    action = spend(1_000.0, min_scale=0.1)

    assert check_feasibility(subject, action).feasible is False

    degraded = degrade_action(action, actor_capacities(subject))
    assert degraded is not None
    # The compromise must clear the same hard constraint that blocked the original.
    assert check_feasibility(subject, degraded).feasible is True


def test_degrade_returns_none_when_even_the_minimum_is_unaffordable():
    action = Action(
        label="build hospital",
        costs={ConstraintType.BUDGET: 1_000_000.0},
        min_scale=0.5,
    )

    assert degrade_action(action, {ConstraintType.BUDGET: 100.0}) is None


def test_degrade_returns_none_with_zero_capacity():
    action = spend(1_000.0, min_scale=0.01)
    assert degrade_action(action, {ConstraintType.BUDGET: 0.0}) is None


def test_degrade_at_exactly_min_scale_is_accepted():
    action = Action(
        label="pilot", costs={ConstraintType.BUDGET: 1_000.0}, min_scale=0.25
    )
    degraded = degrade_action(action, {ConstraintType.BUDGET: 250.0})

    assert degraded is not None
    assert degraded.scale == pytest.approx(0.25)


def test_indivisible_action_cannot_be_degraded():
    action = Action(
        label="acquire the company",
        costs={ConstraintType.BUDGET: 1_000.0},
        divisible=False,
    )

    assert degrade_action(action, {ConstraintType.BUDGET: 999.0}) is None
    # Still returned intact when fully affordable.
    assert degrade_action(action, {ConstraintType.BUDGET: 1_000.0}) is action


def test_degrade_ignores_resources_with_no_stated_capacity():
    action = Action(
        label="mixed", costs={ConstraintType.BUDGET: 100.0, ConstraintType.SOCIAL: 999.0}
    )
    # SOCIAL is unconstrained, so only BUDGET binds; BUDGET is affordable.
    assert degrade_action(action, {ConstraintType.BUDGET: 100.0}) is action


def test_degrade_accepts_string_keys_and_constraint_values():
    action = spend(1_000.0, min_scale=0.1)

    from_strings = degrade_action(action, {"budget": 200.0})
    from_constraints = degrade_action(
        action, {ConstraintType.BUDGET: budget(200.0, Enforcement.HARD)}
    )

    assert from_strings is not None and from_constraints is not None
    assert from_strings.scale == pytest.approx(0.2)
    assert from_constraints.scale == pytest.approx(0.2)


def test_degrade_preserves_approval_and_knowledge_requirements():
    action = Action(
        label="joint venture",
        costs={ConstraintType.BUDGET: 1_000.0},
        requires_approval_from=["board"],
        requires_knowledge={"term_sheet"},
        min_scale=0.1,
    )

    degraded = degrade_action(action, {ConstraintType.BUDGET: 500.0})

    assert degraded is not None
    assert degraded.requires_approval_from == ["board"]
    assert degraded.requires_knowledge == {"term_sheet"}
    # Mutating the copy must not reach back into the original.
    degraded.requires_approval_from.append("regulator")
    assert action.requires_approval_from == ["board"]


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------


def test_zero_cost_action_is_feasible_against_zero_capacity():
    result = check_feasibility(
        actor("broke", budget(0.0, Enforcement.HARD, "no money")),
        Action(label="say nothing", costs={ConstraintType.BUDGET: 0.0}),
    )

    assert result.feasible is True
    assert result.blocking == []
    assert result.penalties == []
    assert result.success_probability == 1.0


def test_action_with_no_costs_at_all_is_feasible():
    result = check_feasibility(
        actor("broke", budget(0.0, Enforcement.HARD)), Action(label="abstain")
    )
    assert result.feasible is True


def test_actor_with_no_constraints_can_do_anything():
    result = check_feasibility(
        {"id": "unbounded"},
        Action(
            label="buy the election",
            costs={ConstraintType.BUDGET: 1e12, ConstraintType.TIME: 1e9},
        ),
    )

    assert result.feasible is True
    assert result.blocking == []
    assert result.penalties == []
    assert result.success_probability == 1.0


def test_actor_with_empty_constraint_list_is_unconstrained():
    assert normalize_constraints({"id": "a", "constraints": []}) == []
    assert check_feasibility({"id": "a", "constraints": []}, spend(1e9)).feasible is True


def test_empty_dependency_graph_returns_no_waves():
    assert resolve_dependencies({}) == []


def test_single_actor_with_no_dependencies_returns_one_wave():
    assert resolve_dependencies({"solo": Action(label="act")}) == [["solo"]]


def test_infinite_capacity_never_blocks():
    result = check_feasibility(
        actor("sovereign", budget(float("inf"), Enforcement.HARD, "unlimited")),
        spend(1e18),
    )
    assert result.feasible is True


def test_degrade_action_with_no_costs_is_returned_unchanged():
    action = Action(label="free speech")
    assert degrade_action(action, {}) is action
    assert degrade_action(action, None) is action


def test_visible_facts_tolerates_an_empty_or_missing_graph():
    assert visible_facts("anyone", {}) == set()
    assert visible_facts("anyone", None) == set()


# ---------------------------------------------------------------------------
# Input normalization and validation
# ---------------------------------------------------------------------------


def test_constraints_can_be_authored_as_dicts_and_bare_numbers():
    from_dicts = check_feasibility(
        {
            "id": "json_actor",
            "constraints": [
                {"type": "budget", "capacity": 10.0, "enforcement": "hard", "label": "cap"}
            ],
        },
        spend(50.0),
    )
    assert from_dicts.feasible is False
    assert from_dicts.blocking[0].label == "cap"

    from_mapping = check_feasibility(
        {"id": "terse_actor", "constraints": {"budget": 10.0}}, spend(50.0)
    )
    # A bare number defaults to HARD enforcement.
    assert from_mapping.feasible is False


def test_actor_knowledge_accepts_alternate_key_spellings():
    action = Action(label="act", requires_knowledge={"fact"})
    for key in ("knowledge", "knows", "known_facts", "facts"):
        assert check_feasibility({"id": "a", key: {"fact"}}, action).feasible is True, key


def test_actor_capacities_keeps_the_tightest_limit_per_resource():
    capacities = actor_capacities(
        actor("a", budget(500.0, Enforcement.HARD), budget(100.0, Enforcement.SOFT))
    )
    assert capacities == {ConstraintType.BUDGET: 100.0}


def test_negative_capacity_and_cost_are_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        Constraint(ConstraintType.BUDGET, -1.0)
    with pytest.raises(ValueError, match="non-negative"):
        Action(label="refund", costs={ConstraintType.BUDGET: -5.0})


def test_invalid_min_scale_is_rejected():
    with pytest.raises(ValueError, match="min_scale"):
        Action(label="x", min_scale=0.0)
    with pytest.raises(ValueError, match="min_scale"):
        Action(label="x", min_scale=1.5)


def test_unknown_enforcement_or_constraint_type_is_rejected_clearly():
    with pytest.raises(ValueError, match="Unknown enforcement"):
        normalize_constraints(
            {"id": "a", "constraints": [{"type": "budget", "capacity": 1, "enforcement": "maybe"}]}
        )
    with pytest.raises(ValueError, match="Unknown constraint type"):
        normalize_constraints({"id": "a", "constraints": {"vibes": 1.0}})


def test_non_action_inputs_are_rejected():
    with pytest.raises(TypeError):
        check_feasibility({"id": "a"}, "buy ads")
    with pytest.raises(TypeError):
        resolve_dependencies([("A", Action(label="a"))])
    with pytest.raises(TypeError):
        resolve_dependencies({"A": "not an action"})


def test_module_imports_only_the_standard_library():
    """The engine must stay standard-library-only and side-effect free.

    Checked against the parsed import statements rather than the raw source, so
    prose in the docstrings cannot make this pass or fail spuriously.
    """
    import ast
    import inspect
    import sys

    from app.services import constraint_engine

    tree = ast.parse(inspect.getsource(constraint_engine))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # a relative import would couple us to app.*
                raise AssertionError(f"relative import found: level={node.level}")
            if node.module:
                imported_roots.add(node.module.split(".")[0])

    assert imported_roots, "expected at least one import to verify"
    non_stdlib = imported_roots - sys.stdlib_module_names
    assert non_stdlib == set(), f"non-stdlib imports: {sorted(non_stdlib)}"
    for banned in ("app", "flask", "requests", "sqlalchemy", "pydantic", "celery"):
        assert banned not in imported_roots, banned

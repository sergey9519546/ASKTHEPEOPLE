"""Protection and provider-sequence tests for the worker-owned Zep canary."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest


RUN_ID = "11111111-1111-4111-8111-111111111111"
OTHER_RUN_ID = "22222222-2222-4222-8222-222222222222"


class TrackingEnvironment(dict):
    """Mapping that proves the provider credential is read only at the last gate."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads: list[str] = []

    def get(self, key, default=None):
        self.reads.append(key)
        return super().get(key, default)


class FakeClock:
    def __init__(self) -> None:
        self.wall = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
        self.elapsed = 0.0

    def utcnow(self) -> datetime:
        return self.wall + timedelta(seconds=self.elapsed)

    def monotonic(self) -> float:
        return self.elapsed

    def sleep(self, seconds: float) -> None:
        self.elapsed += seconds


class FakeRedis:
    def __init__(
        self,
        *,
        lock_available: bool = True,
        fail_journal_states: set[str] | None = None,
    ) -> None:
        self.data: dict[str, str] = {}
        self.lock_available = lock_available
        self.fail_journal_states = fail_journal_states or set()
        self.journal_writes: list[dict] = []

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value: str, *, nx=False, ex=None):
        del ex
        if nx and (not self.lock_available or key in self.data):
            return False
        if key.endswith(":journal"):
            record = json.loads(value)
            if record["state"] in self.fail_journal_states:
                raise ConnectionError("raw redis journal failure")
        self.data[key] = value
        if key.endswith(":journal"):
            self.journal_writes.append(record)
        return True

    def eval(self, _script: str, _numkeys: int, key: str, token: str):
        if self.data.get(key) == token:
            del self.data[key]
            return 1
        return 0


class ProviderNotFound(Exception):
    status_code = 404


class FakeZepClient:
    """A strict in-memory stand-in for exactly the SDK surface the canary uses."""

    def __init__(self, *, fail_at: str | None = None, owner_matches: bool = True):
        self.calls: list[tuple] = []
        self.fail_at = fail_at
        self.owner_matches = owner_matches
        self.created = False
        self.deleted = False
        self.graph_id: str | None = None
        self.owner_marker: str | None = None
        self.episode_uuid = str(uuid.UUID("11111111-1111-4111-8111-111111111111"))
        self.sensor_uuid = "sensor-node"
        self.hub_uuid = "hub-node"
        self.node_reads = 0
        self.edge_reads = 0
        self.graph = self.Graph(self)

    class Graph:
        def __init__(self, parent):
            self.parent = parent
            self.episode = self.Episode(parent)
            self.node = self.Node(parent)
            self.edge = self.Edge(parent)

        def create(self, **kwargs):
            parent = self.parent
            parent.calls.append(("create", kwargs))
            parent.created = True
            parent.graph_id = kwargs["graph_id"]
            parent.owner_marker = kwargs["description"]
            if parent.fail_at == "create_ambiguous":
                raise RuntimeError("raw provider create response")
            return SimpleNamespace(graph_id=parent.graph_id)

        def set_ontology(self, **kwargs):
            parent = self.parent
            parent.calls.append(("set_ontology", kwargs))
            if parent.fail_at == "ontology":
                raise RuntimeError("raw provider ontology response")

        def list_entity_types(self, **kwargs):
            parent = self.parent
            parent.calls.append(("list_entity_types", kwargs))
            if parent.fail_at == "ontology_readback":
                return SimpleNamespace(entity_types=[], edge_types=[])
            entity_types = [
                SimpleNamespace(name="CanarySensor"),
                SimpleNamespace(name="CanaryHub"),
            ]
            if parent.fail_at == "ontology_duplicate":
                entity_types.append(SimpleNamespace(name="CanarySensor"))
            return SimpleNamespace(
                entity_types=entity_types,
                edge_types=[
                    SimpleNamespace(
                        name="ReportsTo",
                        source_targets=[
                            SimpleNamespace(source="CanarySensor", target="CanaryHub")
                        ],
                    )
                ],
            )

        def add_batch(self, **kwargs):
            parent = self.parent
            parent.calls.append(("add_batch", kwargs))
            if parent.fail_at == "add_ambiguous":
                raise TimeoutError("raw fixture echoed by provider")
            if parent.fail_at == "ack":
                return [SimpleNamespace(uuid_="not-a-uuid")]
            return [SimpleNamespace(uuid_=parent.episode_uuid)]

        def get(self, graph_id, **kwargs):
            parent = self.parent
            parent.calls.append(("get", {"graph_id": graph_id, **kwargs}))
            if parent.deleted or not parent.created:
                raise ProviderNotFound("not found")
            description = (
                parent.owner_marker if parent.owner_matches else "foreign-owner"
            )
            return SimpleNamespace(graph_id=graph_id, description=description)

        def delete(self, graph_id, **kwargs):
            parent = self.parent
            parent.calls.append(("delete", {"graph_id": graph_id, **kwargs}))
            if parent.fail_at == "delete_ambiguous_present":
                raise TimeoutError("raw delete response")
            parent.deleted = True
            if parent.fail_at == "delete_ambiguous_deleted":
                raise TimeoutError("raw delete response")
            return SimpleNamespace(success=True)

        class Episode:
            def __init__(self, parent):
                self.parent = parent

            def get(self, uuid_, **kwargs):
                parent = self.parent
                parent.calls.append(("episode_get", {"uuid_": uuid_, **kwargs}))
                return SimpleNamespace(
                    uuid_=(
                        "22222222-2222-4222-8222-222222222222"
                        if parent.fail_at == "episode_identity"
                        else uuid_
                    ),
                    processed=parent.fail_at != "episode_timeout",
                )

        class Node:
            def __init__(self, parent):
                self.parent = parent

            def get_by_graph_id(self, graph_id, **kwargs):
                parent = self.parent
                parent.node_reads += 1
                parent.calls.append(("nodes", {"graph_id": graph_id, **kwargs}))
                if parent.fail_at == "graph_nodes":
                    return []
                if parent.fail_at == "graph_materializes" and parent.node_reads == 1:
                    return []
                return [
                    SimpleNamespace(
                        uuid_=parent.sensor_uuid,
                        name="CanarySensorAlpha",
                        labels=["Entity", "CanarySensor"],
                    ),
                    SimpleNamespace(
                        uuid_=parent.hub_uuid,
                        name="CanaryHubBeta",
                        labels=["Entity", "CanaryHub"],
                    ),
                ]

        class Edge:
            def __init__(self, parent):
                self.parent = parent

            def get_by_graph_id(self, graph_id, **kwargs):
                parent = self.parent
                parent.edge_reads += 1
                parent.calls.append(("edges", {"graph_id": graph_id, **kwargs}))
                if parent.fail_at == "graph_edges":
                    return []
                if parent.fail_at == "graph_materializes" and parent.edge_reads == 1:
                    return []
                return [
                    SimpleNamespace(
                        name="ReportsTo",
                        source_node_uuid=parent.sensor_uuid,
                        target_node_uuid=parent.hub_uuid,
                        episodes=[parent.episode_uuid],
                    )
                ]


def valid_evidence(**changes):
    evidence = {
        "schema_version": "zep-rotation-evidence/v1",
        "incident_id": "public-historical-provider-credentials-2026-07-29",
        "provider": "zep-cloud",
        "old_credentials_revoked": True,
        "old_credentials_revoked_at": "2026-08-08T08:00:00Z",
        "replacement_issued": True,
        "replacement_issued_at": "2026-08-08T08:05:00Z",
        "web_updated": True,
        "web_updated_at": "2026-08-08T08:10:00Z",
        "worker_updated": True,
        "worker_updated_at": "2026-08-08T08:11:00Z",
        "web_restarted": True,
        "web_restarted_at": "2026-08-08T08:12:00Z",
        "worker_restarted": True,
        "worker_restarted_at": "2026-08-08T08:13:00Z",
        "provider_usage_reviewed_through": "2026-08-08T08:14:00Z",
        "rotated_by": "release-operator",
        "independently_verified_by": "security-reviewer",
        "verified_at": "2026-08-08T08:15:00Z",
        "deployment_revision": "a" * 40,
        "restricted_evidence_ref": "incident://security/2026-07-29/rotation",
    }
    evidence.update(changes)
    return evidence


def runtime_env(evidence=None):
    evidence = evidence or valid_evidence()
    return TrackingEnvironment(
        {
            "ZEP_LIVE_CANARY_ENABLED": "true",
            "ZEP_CANARY_DEPLOYMENT_REVISION": evidence["deployment_revision"],
            "RAILWAY_GIT_COMMIT_SHA": evidence["deployment_revision"],
            "REDIS_URL": "redis://unit-test.invalid/0",
            "ZEP_API_KEY": "unit-test-noncredential-provider-value",
        }
    )


def run_canary(
    *,
    evidence=None,
    execute=True,
    env=None,
    redis=None,
    client=None,
    clock=None,
    run_id=RUN_ID,
):
    from app.services.zep_live_canary import run_protected_zep_canary

    evidence = evidence or valid_evidence()
    env = env or runtime_env(evidence)
    redis = redis or FakeRedis()
    client = client or FakeZepClient()
    clock = clock or FakeClock()
    factory_calls = []

    def client_factory(**kwargs):
        factory_calls.append(kwargs)
        return client

    result = run_protected_zep_canary(
        evidence=evidence,
        run_id=run_id,
        execute=execute,
        environ=env,
        redis_factory=lambda _url: redis,
        client_factory=client_factory,
        utcnow=clock.utcnow,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        token_hex=lambda size: "a" * (size * 2),
    )
    return result, env, redis, client, factory_calls


def test_graph_identity_and_owner_marker_are_exact_and_internal():
    from app.services.zep_live_canary import make_canary_graph_id, owner_marker

    graph_id = make_canary_graph_id(
        datetime(2026, 8, 8, 12, 34, 56, tzinfo=UTC),
        token_hex=lambda size: "b" * (size * 2),
    )

    assert graph_id == "atp_canary_v1_20260808t123456z_bbbbbbbbbbbbbbbbbbbbbbbb"
    assert re.fullmatch(r"atp_canary_v1_\d{8}t\d{6}z_[0-9a-f]{24}", graph_id)
    assert owner_marker(graph_id) == f"atp_zep_live_canary_owner:v1:{graph_id}"


def test_canary_ontology_models_serialize_with_zep_sdk_3_13():
    from app.services.zep_live_canary import CanaryHub, CanarySensor, ReportsTo

    assert CanarySensor.model_json_schema()["title"] == "CanarySensor"
    assert CanaryHub.model_json_schema()["title"] == "CanaryHub"
    assert ReportsTo.model_json_schema()["title"] == "ReportsTo"


@pytest.mark.parametrize(
    ("evidence_change", "env_change", "execute", "redis_setup", "reason", "code"),
    [
        ({}, {}, False, None, "explicit_execute_required", 5),
        (
            {"old_credentials_revoked": False},
            {},
            True,
            None,
            "rotation_evidence_invalid",
            4,
        ),
        (
            {"api_key": "must-never-be-accepted"},
            {},
            True,
            None,
            "rotation_evidence_invalid",
            4,
        ),
        (
            {"independently_verified_by": "release-operator"},
            {},
            True,
            None,
            "rotation_evidence_invalid",
            4,
        ),
        (
            {"deployment_revision": "revision-2026-08-08-abcdef123456"},
            {},
            True,
            None,
            "rotation_evidence_invalid",
            4,
        ),
        ({}, {"ZEP_LIVE_CANARY_ENABLED": "false"}, True, None, "canary_not_enabled", 5),
        (
            {},
            {"ZEP_CANARY_DEPLOYMENT_REVISION": "wrong-revision"},
            True,
            None,
            "deployment_revision_mismatch",
            5,
        ),
        ({}, {}, True, "lock_busy", "canary_lock_unavailable", 5),
    ],
)
def test_preflight_blocks_before_provider_credential_or_client(
    evidence_change,
    env_change,
    execute,
    redis_setup,
    reason,
    code,
):
    evidence = valid_evidence(**evidence_change)
    env = runtime_env(evidence)
    env.update(env_change)
    redis = FakeRedis(lock_available=redis_setup != "lock_busy")

    result, env, _redis, client, factory_calls = run_canary(
        evidence=evidence,
        execute=execute,
        env=env,
        redis=redis,
    )

    assert result["state"] == "BLOCKED"
    assert result["reason"] == reason
    assert result["exit_code"] == code
    assert "ZEP_API_KEY" not in env.reads
    assert factory_calls == []
    assert client.calls == []


def test_operator_expected_revision_cannot_override_stale_worker_revision():
    evidence = valid_evidence()
    env = runtime_env(evidence)
    env["RAILWAY_GIT_COMMIT_SHA"] = "stale-worker-revision"

    result, env, _redis, client, factory_calls = run_canary(
        evidence=evidence,
        env=env,
    )

    assert result == {
        "exit_code": 5,
        "state": "BLOCKED",
        "reason": "deployment_revision_mismatch",
    }
    assert "ZEP_API_KEY" not in env.reads
    assert factory_calls == []
    assert client.calls == []


def test_baked_build_revision_is_used_when_platform_revision_is_absent():
    evidence = valid_evidence()
    env = runtime_env(evidence)
    env.pop("ZEP_CANARY_DEPLOYMENT_REVISION")
    env.pop("RAILWAY_GIT_COMMIT_SHA", None)
    env["BUILD_REVISION"] = evidence["deployment_revision"]

    result, _env, _redis, _client, _factory_calls = run_canary(
        evidence=evidence,
        env=env,
    )

    assert result["exit_code"] == 0
    assert result["state"] == "CLEAN"


def test_cleanup_pending_journal_blocks_a_new_run_before_provider_access():
    from app.services.zep_live_canary import JOURNAL_KEY

    evidence = valid_evidence()
    env = runtime_env(evidence)
    redis = FakeRedis()
    redis.data[JOURNAL_KEY] = json.dumps(
        {
            "schema_version": "zep-live-canary-journal/v2",
            "state": "CLEANUP_PENDING",
            "run_id": OTHER_RUN_ID,
            "deployment_revision": evidence["deployment_revision"],
            "graph_id": "atp_canary_v1_20260808t000000z_aaaaaaaaaaaaaaaaaaaaaaaa",
            "owner_marker": "atp_zep_live_canary_owner:v1:atp_canary_v1_20260808t000000z_aaaaaaaaaaaaaaaaaaaaaaaa",
            "updated_at": "2026-08-08T09:00:00Z",
            "reason": "cleanup_not_confirmed",
            "terminal_result": None,
        }
    )

    result, env, _redis, client, factory_calls = run_canary(
        evidence=evidence,
        env=env,
        redis=redis,
    )

    assert result == {
        "exit_code": 3,
        "state": "CLEANUP_PENDING",
        "reason": "prior_cleanup_pending",
        "graph_id": "atp_canary_v1_20260808t000000z_aaaaaaaaaaaaaaaaaaaaaaaa",
    }
    assert "ZEP_API_KEY" not in env.reads
    assert factory_calls == []
    assert client.calls == []


def test_redelivery_reuses_the_preflighted_graph_identity_instead_of_creating_another():
    from app.services.zep_live_canary import JOURNAL_KEY, owner_marker

    evidence = valid_evidence()
    redis = FakeRedis()
    prior_graph_id = "atp_canary_v1_20260808t115959z_bbbbbbbbbbbbbbbbbbbbbbbb"
    redis.data[JOURNAL_KEY] = json.dumps(
        {
            "schema_version": "zep-live-canary-journal/v2",
            "state": "PREFLIGHTED",
            "run_id": RUN_ID,
            "deployment_revision": evidence["deployment_revision"],
            "graph_id": prior_graph_id,
            "owner_marker": owner_marker(prior_graph_id),
            "updated_at": "2026-08-08T11:59:59Z",
            "reason": "preflight_complete",
            "terminal_result": None,
        }
    )

    result, _env, _redis, client, _factory_calls = run_canary(
        evidence=evidence,
        redis=redis,
    )

    assert result["exit_code"] == 0
    assert result["graph_id"] == prior_graph_id
    assert client.calls[0][1]["graph_id"] == prior_graph_id


def test_happy_path_registers_exact_ontology_verifies_graph_and_deletes():
    from app.services.zep_live_canary import CANARY_FIXTURE, JOURNAL_KEY

    result, env, redis, client, factory_calls = run_canary()

    assert result["exit_code"] == 0
    assert result["state"] == "CLEAN"
    assert result["reason"] == "canary_passed"
    assert re.fullmatch(r"atp_canary_v1_\d{8}t\d{6}z_[0-9a-f]{24}", result["graph_id"])
    assert env.reads.index("ZEP_API_KEY") > env.reads.index("REDIS_URL")
    assert factory_calls == [
        {"api_key": "unit-test-noncredential-provider-value", "timeout": 10.0}
    ]
    assert [call[0] for call in client.calls] == [
        "create",
        "set_ontology",
        "list_entity_types",
        "add_batch",
        "episode_get",
        "nodes",
        "edges",
        "get",
        "delete",
        "get",
    ]

    create_kwargs = client.calls[0][1]
    assert create_kwargs["description"] == (
        f"atp_zep_live_canary_owner:v1:{result['graph_id']}"
    )
    ontology_kwargs = client.calls[1][1]
    assert set(ontology_kwargs["entities"]) == {"CanarySensor", "CanaryHub"}
    assert set(ontology_kwargs["edges"]) == {"ReportsTo"}
    edge_model, source_targets = ontology_kwargs["edges"]["ReportsTo"]
    assert edge_model.__name__ == "ReportsTo"
    assert [(item.source, item.target) for item in source_targets] == [
        ("CanarySensor", "CanaryHub")
    ]
    add_kwargs = client.calls[3][1]
    assert len(add_kwargs["episodes"]) == 1
    assert add_kwargs["episodes"][0].data == CANARY_FIXTURE
    assert all(
        call[1].get("request_options") == {"timeout_in_seconds": 10, "max_retries": 0}
        for call in client.calls
    )
    assert redis.get(JOURNAL_KEY) is not None
    assert [entry["state"] for entry in redis.journal_writes] == [
        "PREFLIGHTED",
        "CREATE_REQUESTED",
        "GRAPH_CREATED",
        "ONTOLOGY_REQUESTED",
        "ONTOLOGY_VERIFIED",
        "EPISODE_REQUESTED",
        "EPISODE_ACKNOWLEDGED",
        "EPISODE_PROCESSED",
        "GRAPH_VERIFIED",
        "DELETE_REQUESTED",
        "CLEAN",
    ]
    serialized = repr(result) + repr(redis.journal_writes)
    assert CANARY_FIXTURE not in serialized
    assert "unit-test-noncredential-provider-value" not in serialized
    assert "raw provider" not in serialized


def test_ambiguous_episode_submission_is_not_retried_and_is_cleaned():
    client = FakeZepClient(fail_at="add_ambiguous")

    result, _env, redis, client, _factory_calls = run_canary(client=client)

    assert result["exit_code"] == 2
    assert result["state"] == "CLEAN"
    assert result["reason"] == "episode_submission_unconfirmed"
    assert [call[0] for call in client.calls].count("add_batch") == 1
    assert [call[0] for call in client.calls][-3:] == ["get", "delete", "get"]
    assert [entry["state"] for entry in redis.journal_writes][-3:] == [
        "RECONCILING",
        "DELETE_REQUESTED",
        "CLEAN",
    ]
    assert "raw fixture" not in repr(result)
    assert "raw fixture" not in repr(redis.journal_writes)


def test_graph_verification_polls_until_materialized_within_total_deadline():
    client = FakeZepClient(fail_at="graph_materializes")
    clock = FakeClock()

    result, _env, _redis, client, _factory_calls = run_canary(
        client=client,
        clock=clock,
    )

    assert result["exit_code"] == 0
    assert client.node_reads == 2
    assert client.edge_reads == 2
    assert clock.elapsed >= 2


def test_journal_failure_after_mutation_never_prevents_owner_safe_cleanup():
    client = FakeZepClient(fail_at="add_ambiguous")
    redis = FakeRedis(fail_journal_states={"RECONCILING", "CLEAN", "CLEANUP_PENDING"})

    result, _env, _redis, client, _factory_calls = run_canary(
        client=client,
        redis=redis,
    )

    assert client.deleted is True
    assert [call[0] for call in client.calls].count("delete") == 1
    assert result["exit_code"] == 3
    assert result["state"] == "CLEANUP_PENDING"
    assert result["reason"] == "cleanup_journal_unavailable"
    assert "raw redis" not in repr(result)


def test_cleanup_refuses_to_delete_a_graph_without_the_exact_owner_marker():
    client = FakeZepClient(fail_at="add_ambiguous", owner_matches=False)

    result, _env, redis, client, _factory_calls = run_canary(client=client)

    assert result["exit_code"] == 3
    assert result["state"] == "CLEANUP_PENDING"
    assert result["reason"] == "cleanup_owner_unverified"
    assert "delete" not in [call[0] for call in client.calls]
    assert redis.journal_writes[-1]["state"] == "CLEANUP_PENDING"


def test_ambiguous_delete_is_never_replayed_and_confirmed_absent_when_it_landed():
    client = FakeZepClient(fail_at="delete_ambiguous_deleted")

    result, _env, _redis, client, _factory_calls = run_canary(client=client)

    assert result["exit_code"] == 0
    assert result["state"] == "CLEAN"
    assert [call[0] for call in client.calls].count("delete") == 1


def test_ambiguous_delete_that_remains_present_becomes_cleanup_pending():
    client = FakeZepClient(fail_at="delete_ambiguous_present")
    clock = FakeClock()

    result, _env, redis, client, _factory_calls = run_canary(
        client=client,
        clock=clock,
    )

    assert result["exit_code"] == 3
    assert result["state"] == "CLEANUP_PENDING"
    assert result["reason"] == "cleanup_not_confirmed"
    assert [call[0] for call in client.calls].count("delete") == 1
    assert redis.journal_writes[-1]["state"] == "CLEANUP_PENDING"
    assert clock.elapsed >= 60


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("ontology_readback", "ontology_verification_failed"),
        ("ack", "episode_submission_unconfirmed"),
        ("episode_timeout", "episode_processing_timeout"),
        ("graph_nodes", "graph_verification_failed"),
        ("graph_edges", "graph_verification_failed"),
    ],
)
def test_verification_failures_are_stable_and_cleaned(failure, reason):
    client = FakeZepClient(fail_at=failure)
    clock = FakeClock()

    result, _env, redis, client, _factory_calls = run_canary(
        client=client,
        clock=clock,
    )

    assert result["exit_code"] == 2
    assert result["state"] == "CLEAN"
    assert result["reason"] == reason
    assert [call[0] for call in client.calls][-3:] == ["get", "delete", "get"]
    assert redis.journal_writes[-1]["state"] == "CLEAN"
    if failure == "episode_timeout":
        assert clock.elapsed >= 120


def test_safe_reads_retry_only_transient_provider_failures():
    from app.services.zep_live_canary import _safe_read

    class ProviderError(Exception):
        def __init__(self, status_code):
            self.status_code = status_code

    forbidden_calls = 0
    forbidden_sleeps = []

    def forbidden():
        nonlocal forbidden_calls
        forbidden_calls += 1
        raise ProviderError(403)

    with pytest.raises(ProviderError):
        _safe_read(forbidden, sleep=forbidden_sleeps.append)

    assert forbidden_calls == 1
    assert forbidden_sleeps == []

    transient_calls = 0
    transient_sleeps = []

    def transient():
        nonlocal transient_calls
        transient_calls += 1
        if transient_calls < 3:
            raise ProviderError(503)
        return "available"

    assert _safe_read(transient, sleep=transient_sleeps.append) == "available"
    assert transient_calls == 3
    assert transient_sleeps == [0.5, 1.0]


def test_same_run_terminal_redelivery_returns_identical_result_without_provider_access():
    redis = FakeRedis()
    first, _env, redis, _client, _calls = run_canary(redis=redis)
    second_env = runtime_env()
    second_client = FakeZepClient()

    second, second_env, _redis, second_client, factory_calls = run_canary(
        redis=redis,
        env=second_env,
        client=second_client,
        run_id=RUN_ID,
    )

    assert second == first
    assert "ZEP_API_KEY" not in second_env.reads
    assert factory_calls == []
    assert second_client.calls == []


def test_different_run_may_start_only_after_prior_terminal_clean():
    redis = FakeRedis()
    first, *_ = run_canary(redis=redis, run_id=RUN_ID)
    second_client = FakeZepClient()

    second, _env, _redis, second_client, _calls = run_canary(
        redis=redis,
        client=second_client,
        run_id=OTHER_RUN_ID,
    )

    assert first["exit_code"] == second["exit_code"] == 0
    assert [call[0] for call in second_client.calls].count("create") == 1
    assert [call[0] for call in second_client.calls].count("add_batch") == 1


def test_older_terminal_run_redelivery_remains_idempotent_after_a_later_run():
    redis = FakeRedis()
    first, *_ = run_canary(redis=redis, run_id=RUN_ID)
    second, *_ = run_canary(
        redis=redis,
        client=FakeZepClient(),
        run_id=OTHER_RUN_ID,
    )
    redelivery_env = runtime_env()
    redelivery_client = FakeZepClient()

    redelivery, redelivery_env, _redis, redelivery_client, factory_calls = run_canary(
        redis=redis,
        env=redelivery_env,
        client=redelivery_client,
        run_id=RUN_ID,
    )

    assert first["exit_code"] == second["exit_code"] == 0
    assert redelivery == first
    assert "ZEP_API_KEY" not in redelivery_env.reads
    assert factory_calls == []
    assert redelivery_client.calls == []


def test_same_run_create_intent_reconciles_and_cleans_without_replaying_create():
    from app.services.zep_live_canary import JOURNAL_KEY, owner_marker

    evidence = valid_evidence()
    graph_id = "atp_canary_v1_20260808t115959z_bbbbbbbbbbbbbbbbbbbbbbbb"
    marker = owner_marker(graph_id)
    redis = FakeRedis()
    redis.data[JOURNAL_KEY] = json.dumps(
        {
            "schema_version": "zep-live-canary-journal/v2",
            "state": "CREATE_REQUESTED",
            "run_id": RUN_ID,
            "deployment_revision": evidence["deployment_revision"],
            "graph_id": graph_id,
            "owner_marker": marker,
            "updated_at": "2026-08-08T11:59:59Z",
            "reason": "create_requested",
            "terminal_result": None,
        }
    )
    client = FakeZepClient()
    client.created = True
    client.graph_id = graph_id
    client.owner_marker = marker

    result, _env, _redis, client, _calls = run_canary(
        evidence=evidence,
        redis=redis,
        client=client,
        run_id=RUN_ID,
    )

    assert result["exit_code"] == 2
    assert result["reason"] == "graph_create_unconfirmed"
    assert "create" not in [call[0] for call in client.calls]
    assert "add_batch" not in [call[0] for call in client.calls]
    assert [call[0] for call in client.calls] == ["get", "delete", "get"]


def test_same_run_delete_intent_never_replays_an_ambiguous_delete():
    from app.services.zep_live_canary import JOURNAL_KEY, owner_marker

    evidence = valid_evidence()
    graph_id = "atp_canary_v1_20260808t115959z_cccccccccccccccccccccccc"
    marker = owner_marker(graph_id)
    redis = FakeRedis()
    redis.data[JOURNAL_KEY] = json.dumps(
        {
            "schema_version": "zep-live-canary-journal/v2",
            "state": "DELETE_REQUESTED",
            "run_id": RUN_ID,
            "deployment_revision": evidence["deployment_revision"],
            "graph_id": graph_id,
            "owner_marker": marker,
            "updated_at": "2026-08-08T11:59:59Z",
            "reason": "delete_requested",
            "terminal_result": None,
        }
    )
    client = FakeZepClient()
    client.created = True
    client.graph_id = graph_id
    client.owner_marker = marker

    result, _env, _redis, client, _calls = run_canary(
        evidence=evidence,
        redis=redis,
        client=client,
        run_id=RUN_ID,
    )

    assert result["exit_code"] == 3
    assert result["reason"] == "cleanup_not_confirmed"
    assert [call[0] for call in client.calls] == ["get"]


def test_cleanup_confirmation_stops_immediately_on_deterministic_provider_error():
    from app.services.zep_live_canary import _cleanup_graph, owner_marker

    graph_id = "atp_canary_v1_20260808t120000z_dddddddddddddddddddddddd"
    marker = owner_marker(graph_id)
    clock = FakeClock()
    redis = FakeRedis()

    class Forbidden(Exception):
        status_code = 403

    class Graph:
        def __init__(self):
            self.gets = 0

        def get(self, _graph_id, **_kwargs):
            self.gets += 1
            if self.gets == 1:
                return SimpleNamespace(graph_id=graph_id, description=marker)
            raise Forbidden("raw provider response")

        def delete(self, _graph_id, **_kwargs):
            return None

    client = SimpleNamespace(graph=Graph())
    cleaned, reason, _journal_ok = _cleanup_graph(
        client=client,
        redis_client=redis,
        graph_id=graph_id,
        marker=marker,
        run_id=RUN_ID,
        deployment_revision=valid_evidence()["deployment_revision"],
        terminal_result={
            "exit_code": 0,
            "state": "CLEAN",
            "reason": "canary_passed",
            "graph_id": graph_id,
        },
        utcnow=clock.utcnow,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        normal_delete=True,
    )

    assert cleaned is False
    assert reason == "cleanup_verification_unavailable"
    assert client.graph.gets == 2
    assert clock.elapsed == 0


def test_rotation_usage_review_must_cover_both_restarted_services():
    from app.services.zep_live_canary import (
        RotationEvidenceError,
        validate_rotation_evidence,
    )

    evidence = valid_evidence(provider_usage_reviewed_through="2026-08-08T08:12:30Z")

    with pytest.raises(RotationEvidenceError, match="rotation_evidence_invalid"):
        validate_rotation_evidence(
            evidence,
            utcnow=lambda: datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("episode_identity", "episode_processing_failed"),
        ("ontology_duplicate", "ontology_verification_failed"),
    ],
)
def test_exact_provider_proof_rejects_identity_or_ontology_duplicates(failure, reason):
    result, *_ = run_canary(client=FakeZepClient(fail_at=failure))

    assert result["exit_code"] == 2
    assert result["reason"] == reason


def test_invalid_run_identity_blocks_before_key_or_client():
    env = runtime_env()

    result, env, _redis, client, factory_calls = run_canary(
        env=env,
        run_id="not a celery task id",
    )

    assert result == {
        "exit_code": 5,
        "state": "BLOCKED",
        "reason": "canary_run_identity_invalid",
    }
    assert "ZEP_API_KEY" not in env.reads
    assert factory_calls == []
    assert client.calls == []

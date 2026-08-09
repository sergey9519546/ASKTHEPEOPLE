import io
import sys
from types import SimpleNamespace

import pytest

from app import create_app
from app.api import graph as graph_api
from app.api.routes import prep_routes
from app.config import Config
from app.models.project import ProjectManager
from app.models.task import TaskManager, TaskStatus
from app.services import simulation_limits as simulation_limits_module
from app.services.simulation_limits import resolve_total_rounds
from app.services.simulation_manager import SimulationStatus
from app.utils.file_parser import (
    FileParser,
    FileParserLimitError,
    split_text_into_chunks,
)
from app.utils.input_policy import (
    ARCHETYPE_COUNT_MAX,
    ARCHETYPE_EXPANSION_MAX,
    ENTITY_TYPE_FILTER_MAX,
    EXTRACTED_TEXT_CHARACTERS_MAX,
    FOLLOWER_COUNT_MAX,
    PARALLEL_PROFILE_WORKERS_MAX,
    PREPARE_ENTITY_MAX,
    SIMULATION_ROUNDS_MAX,
)
from app.utils.zep_paging import fetch_all_edges, fetch_all_nodes
from scripts import run_parallel_simulation as parallel_runtime


def test_chunk_overlap_cannot_prevent_forward_progress():
    with pytest.raises(ValueError, match="smaller than chunk_size"):
        split_text_into_chunks("x" * 1000, chunk_size=100, overlap=100)
    with pytest.raises(ValueError, match="non-negative"):
        split_text_into_chunks("x" * 1000, chunk_size=100, overlap=-1)


def test_chunk_count_is_bounded():
    with pytest.raises(ValueError, match="more than 10000 chunks"):
        split_text_into_chunks("x" * 20_000, chunk_size=2, overlap=1)


class _PagingClient:
    def __init__(self, batch):
        self.calls = 0
        self.batch = batch
        self.graph = SimpleNamespace(
            node=SimpleNamespace(get_by_graph_id=self._fetch),
            edge=SimpleNamespace(get_by_graph_id=self._fetch),
        )

    def _fetch(self, _graph_id, **_kwargs):
        self.calls += 1
        return self.batch


def test_repeated_zep_cursor_stops_node_pagination():
    client = _PagingClient([
        SimpleNamespace(uuid_="node-a"),
        SimpleNamespace(uuid_="node-b"),
    ])
    result = fetch_all_nodes(client, "graph", page_size=2, max_items=10)
    assert client.calls == 2
    assert len(result) == 4


def test_edge_pagination_has_hard_item_cap():
    client = _PagingClient([
        SimpleNamespace(uuid_="edge-a"),
        SimpleNamespace(uuid_="edge-b"),
    ])
    result = fetch_all_edges(client, "graph", page_size=2, max_items=3)
    assert client.calls == 2
    assert len(result) == 3


def test_invalid_paging_limits_are_rejected_before_io():
    client = _PagingClient([])
    with pytest.raises(ValueError):
        fetch_all_nodes(client, "graph", page_size=0)
    with pytest.raises(ValueError):
        fetch_all_edges(client, "graph", max_items=10001)
    assert client.calls == 0


@pytest.fixture
def api_client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        (
            {
                "simulation_id": "sim_missing",
                "max_rounds": SIMULATION_ROUNDS_MAX + 1,
            },
            "integer_field_out_of_range",
        ),
        (
            {
                "simulation_id": "sim_missing",
                "enable_followers": True,
                "follower_count": FOLLOWER_COUNT_MAX + 1,
            },
            "integer_field_out_of_range",
        ),
        (
            {
                "simulation_id": "sim_missing",
                "enable_followers": True,
                "follower_distribution": {
                    "AMPLIFIER": 1.0,
                    "UNKNOWN": 1.0,
                },
            },
            "invalid_weight_distribution",
        ),
    ],
)
def test_simulation_start_rejects_unbounded_run_controls(
    api_client,
    payload,
    expected_code,
):
    response = api_client.post("/api/simulation/start", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == expected_code


@pytest.mark.parametrize(
    "payload",
    [
        {
            "simulation_id": "sim_missing",
            "parallel_profile_count": PARALLEL_PROFILE_WORKERS_MAX + 1,
        },
        {
            "simulation_id": "sim_missing",
            "use_archetypes": True,
            "archetype_count": ARCHETYPE_COUNT_MAX + 1,
        },
        {
            "simulation_id": "sim_missing",
            "use_archetypes": True,
            "expansion_factor": ARCHETYPE_EXPANSION_MAX + 1,
        },
        {
            "simulation_id": "sim_missing",
            "entity_types": [
                f"Type{index}" for index in range(ENTITY_TYPE_FILTER_MAX + 1)
            ],
        },
    ],
)
def test_prepare_rejects_unbounded_request_controls(api_client, payload):
    response = api_client.post("/api/simulation/prepare", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] in {
        "integer_field_out_of_range",
        "too_many_items",
    }


def test_prepare_rejects_graphs_with_too_many_profile_entities(
    api_client,
    monkeypatch,
):
    state = SimpleNamespace(
        simulation_id="sim-1",
        project_id="project-1",
        graph_id="source-graph",
        status=SimulationStatus.CREATED,
    )

    class FakeManager:
        def get_simulation(self, _simulation_id):
            return state

    class FakeReader:
        def filter_defined_entities(self, **_kwargs):
            return SimpleNamespace(
                filtered_count=PREPARE_ENTITY_MAX + 1,
                entity_types={"Person"},
            )

    monkeypatch.setattr(prep_routes, "SimulationManager", FakeManager)
    monkeypatch.setattr(prep_routes, "ZepEntityReader", FakeReader)
    monkeypatch.setattr(
        prep_routes,
        "_check_simulation_prepared",
        lambda _simulation_id: (False, {}),
    )
    monkeypatch.setattr(
        prep_routes.ProjectManager,
        "get_project",
        lambda _project_id: SimpleNamespace(
            simulation_requirement="What paths could follow?"
        ),
    )
    monkeypatch.setattr(
        prep_routes.ProjectManager,
        "get_extracted_text",
        lambda _project_id: "Source",
    )

    response = api_client.post(
        "/api/simulation/prepare",
        json={"simulation_id": "sim-1"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "entity_count_out_of_range"


def test_ontology_upload_rejects_excessive_extracted_text(
    api_client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))

    class FakeOntologyGenerator:
        def generate(self, **_kwargs):
            return {
                "entity_types": [],
                "edge_types": [],
                "analysis_summary": "",
            }

    monkeypatch.setattr(graph_api, "OntologyGenerator", FakeOntologyGenerator)
    response = api_client.post(
        "/api/graph/ontology/generate",
        data={
            "simulation_requirement": "What paths could follow?",
            "project_name": "Bounded upload",
            "intended_use": "scenario_planning",
            "use_policy_acknowledged": "true",
            "files": (
                io.BytesIO(b"x" * (EXTRACTED_TEXT_CHARACTERS_MAX + 1)),
                "large.txt",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    assert response.get_json()["error"] == "extracted_text_too_large"
    assert ProjectManager.list_projects() == []


def test_generated_time_configuration_cannot_bypass_round_limit():
    assert resolve_total_rounds(
        {
            "time_config": {
                "total_simulation_hours": 10_000,
                "minutes_per_round": 1,
            }
        }
    ) == SIMULATION_ROUNDS_MAX
    assert resolve_total_rounds(
        {
            "time_config": {
                "total_simulation_hours": 10_000,
                "minutes_per_round": 1,
            }
        },
        max_rounds=25,
    ) == 25
    assert resolve_total_rounds(
        {
            "time_config": {
                "total_simulation_hours": 1,
                "minutes_per_round": 40,
            }
        }
    ) == 2
    with pytest.raises(ValueError, match="minutes_per_round"):
        resolve_total_rounds(
            {
                "time_config": {
                    "total_simulation_hours": 72,
                    "minutes_per_round": 0,
                }
            }
        )


def _mock_parallel_platform_runtime(monkeypatch, applied_rounds):
    class FakeGraph:
        def get_agents(self):
            return []

    class FakeGuard:
        def verify(self, _agent_graph):
            return None

    class FakeEnvironment:
        def __init__(self, agent_graph):
            self.agent_graph = agent_graph

        async def reset(self):
            return None

    graph = FakeGraph()

    async def generate_agent_graph(**_kwargs):
        return graph

    async def apply_bootstrap(**_kwargs):
        return 0

    async def apply_scheduled(**kwargs):
        applied_rounds.append((kwargs["platform"], kwargs["current_round"]))
        return 0

    monkeypatch.setattr(
        parallel_runtime,
        "create_model",
        lambda *_args, **_kwargs: (object(), {"semaphore": 1}),
    )
    monkeypatch.setattr(
        parallel_runtime,
        "load_decision_lens_runtime_adapters",
        lambda _simulation_dir: [],
    )
    monkeypatch.setattr(
        parallel_runtime,
        "generate_decision_lens_agent_graph",
        generate_agent_graph,
    )
    monkeypatch.setattr(
        parallel_runtime,
        "InstructionIntegrityGuard",
        SimpleNamespace(capture=lambda _graph: FakeGuard()),
    )
    monkeypatch.setattr(
        parallel_runtime,
        "apply_network_topology",
        lambda _graph, _config: None,
    )
    monkeypatch.setattr(
        parallel_runtime,
        "build_agent_name_lookup",
        lambda _config: {},
    )
    monkeypatch.setattr(
        parallel_runtime,
        "oasis",
        SimpleNamespace(
            DefaultPlatformType=SimpleNamespace(TWITTER="twitter", REDDIT="reddit"),
            make=lambda **kwargs: FakeEnvironment(kwargs["agent_graph"]),
        ),
    )
    monkeypatch.setattr(parallel_runtime, "apply_bootstrap_actions", apply_bootstrap)
    monkeypatch.setattr(parallel_runtime, "apply_scheduled_events", apply_scheduled)
    monkeypatch.setattr(
        parallel_runtime,
        "fetch_new_actions_from_db",
        lambda _db_path, last_rowid, _agent_names: ([], last_rowid),
    )
    monkeypatch.setattr(
        parallel_runtime,
        "RedisEventConsumer",
        lambda **_kwargs: SimpleNamespace(consume_events=lambda: []),
    )
    monkeypatch.setattr(
        parallel_runtime,
        "bootstrap_boost_agent_ids",
        lambda *_args: [],
    )
    monkeypatch.setattr(
        parallel_runtime,
        "scheduled_event_boost_agent_ids",
        lambda *_args: [],
    )
    monkeypatch.setattr(
        parallel_runtime,
        "get_active_agents_for_round",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(parallel_runtime, "_shutdown_event", None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("platform", "runtime_entrypoint"),
    [
        ("twitter", parallel_runtime.run_twitter_simulation),
        ("reddit", parallel_runtime.run_reddit_simulation),
    ],
)
@pytest.mark.parametrize(
    ("time_config", "global_cap", "max_rounds", "expected_rounds"),
    [
        (
            {"total_simulation_hours": 1, "minutes_per_round": 40},
            10,
            None,
            2,
        ),
        (
            {"total_simulation_hours": 8, "minutes_per_round": 60},
            3,
            None,
            3,
        ),
        (
            {"total_simulation_hours": 8, "minutes_per_round": 60},
            20,
            2,
            2,
        ),
    ],
    ids=["ceil", "global-cap", "explicit-max"],
)
async def test_platform_loops_apply_exactly_the_resolved_round_count(
    monkeypatch,
    tmp_path,
    platform,
    runtime_entrypoint,
    time_config,
    global_cap,
    max_rounds,
    expected_rounds,
):
    applied_rounds = []
    _mock_parallel_platform_runtime(monkeypatch, applied_rounds)
    monkeypatch.setattr(
        simulation_limits_module,
        "SIMULATION_ROUNDS_MAX",
        global_cap,
    )

    await runtime_entrypoint(
        {"time_config": {**time_config, "reflection_interval_rounds": 0}},
        str(tmp_path),
        max_rounds=max_rounds,
    )

    assert applied_rounds == [
        (platform, round_num) for round_num in range(1, expected_rounds + 1)
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "runtime_entrypoint",
    [
        parallel_runtime.run_twitter_simulation,
        parallel_runtime.run_reddit_simulation,
    ],
)
@pytest.mark.parametrize(
    ("config", "error"),
    [
        ([], "simulation config must be an object"),
        ({"time_config": []}, "time_config must be an object"),
        (
            {
                "time_config": {
                    "total_simulation_hours": "many",
                    "minutes_per_round": 30,
                }
            },
            "must be numbers",
        ),
    ],
)
async def test_platform_loops_validate_timing_before_runtime_initialization(
    monkeypatch,
    tmp_path,
    runtime_entrypoint,
    config,
    error,
):
    def fail_if_initialized(*_args, **_kwargs):
        raise AssertionError("runtime initialized before timing validation")

    monkeypatch.setattr(parallel_runtime, "create_model", fail_if_initialized)

    with pytest.raises(ValueError, match=error):
        await runtime_entrypoint(config, str(tmp_path))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "error"),
    [
        ([], "simulation config must be an object"),
        ({"time_config": []}, "time_config must be an object"),
        (
            {
                "time_config": {
                    "total_simulation_hours": "many",
                    "minutes_per_round": 30,
                }
            },
            "must be numbers",
        ),
    ],
)
async def test_parallel_main_uses_shared_timing_validation(
    monkeypatch,
    tmp_path,
    config,
    error,
):
    config_path = tmp_path / "simulation_config.json"
    config_path.write_text("{}", encoding="utf-8")

    class QuietLogManager:
        def __init__(self, _simulation_dir):
            pass

        def get_twitter_logger(self):
            return None

        def get_reddit_logger(self):
            return None

        def info(self, _message):
            return None

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_parallel_simulation.py",
            "--config",
            str(config_path),
            "--twitter-only",
            "--no-wait",
        ],
    )
    monkeypatch.setattr(parallel_runtime, "load_config", lambda _path: config)
    monkeypatch.setattr(
        parallel_runtime,
        "init_logging_for_simulation",
        lambda _simulation_dir: None,
    )
    monkeypatch.setattr(parallel_runtime, "SimulationLogManager", QuietLogManager)

    with pytest.raises(ValueError, match=error):
        await parallel_runtime.main()


def test_graph_task_polling_never_returns_nested_tracebacks(api_client):
    task_manager = TaskManager()
    task_id = task_manager.create_task("Build Graph")
    private_trace = (
        "Traceback (most recent call last):\n"
        '  File "C:\\private\\graph_builder.py", line 42\n'
        "RuntimeError: provider body"
    )
    task_manager.update_task(
        task_id,
        status=TaskStatus.FAILED,
        error=private_trace,
        public_error="graph_build_failed",
    )

    response = api_client.get(f"/api/graph/task/{task_id}")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["error"] == "graph_build_failed"
    assert "Traceback" not in response.get_data(as_text=True)
    assert "C:\\private" not in response.get_data(as_text=True)


def test_pdf_extraction_stops_at_page_and_character_limits(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self.text = text

        def get_text(self):
            return self.text

    class FakeDocument:
        def __init__(self, pages):
            self.pages = pages
            self.iterated = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def __len__(self):
            return len(self.pages)

        def __iter__(self):
            for page in self.pages:
                self.iterated += 1
                yield page

    page_limited = FakeDocument([FakePage("x")] * 4)
    monkeypatch.setitem(
        sys.modules,
        "fitz",
        SimpleNamespace(open=lambda _path: page_limited),
    )
    with pytest.raises(FileParserLimitError, match="page limit"):
        FileParser._extract_from_pdf(
            "fake.pdf",
            max_characters=100,
            max_pages=3,
        )
    assert page_limited.iterated == 0

    character_limited = FakeDocument([FakePage("123456"), FakePage("abcdef")])
    monkeypatch.setitem(
        sys.modules,
        "fitz",
        SimpleNamespace(open=lambda _path: character_limited),
    )
    with pytest.raises(FileParserLimitError, match="character limit"):
        FileParser._extract_from_pdf(
            "fake.pdf",
            max_characters=10,
            max_pages=3,
        )
    assert character_limited.iterated == 2

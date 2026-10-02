"""Pins for the installed Zep Cloud SDK surface this codebase calls.

`zep-cloud==3.27.0` is pinned in ``backend/pyproject.toml``, but nothing
verified that the SDK actually exposes the methods our call sites use — the
upstream MiroFish project lost an entire integration this way when the SDK
renamed ``get_entity_edges`` to ``get_edges``, and this repository shipped
that exact breakage with it: ``zep_entity_reader.get_node_edges`` called
``get_entity_edges`` for the whole 3.27 pin and every call failed at
runtime, swallowed into ``graph_entity_edge_read_unavailable``.

Every method name below is a live production call site. When a Zep SDK bump
renames, moves, or re-shapes one of them, this file fails at CI time on the
new pin — not at runtime during a customer run.

The contract pinned here:
1. The installed SDK is exactly the pinned version (no silent drift).
2. Every Zep client method this repository calls exists on the client.
3. The pagination keyword (``uuid_cursor``) still exists on the paged reads
   — a rename there makes ``zep_paging`` fetch the first page forever.
4. The search endpoint still accepts the parameter names our profile and
   report tooling passes (``scope``/``reranker``/``graph_id``).
"""

import importlib.metadata
import inspect

import pytest
from zep_cloud import Zep


@pytest.fixture(scope="module")
def client():
    # Construction performs no I/O; it only wires the SDK's API namespaces.
    return Zep(api_key="sdk-contract-pin-probe-not-a-real-key")


def test_installed_sdk_is_the_pinned_version():
    """The lockfile pins zep-cloud==3.27.0; the environment must match it.

    A drifted venv (half-upgraded, stale cache, hand-edited) silently
    changes the API surface every other pin in this file measures.
    """
    installed = importlib.metadata.version("zep-cloud")
    assert installed.startswith("3.27."), (
        f"installed zep-cloud is {installed}, but backend/pyproject.toml "
        "pins ==3.27.0 — relock before trusting any other pin here"
    )


def test_pinned_version_matches_pyproject():
    """The pin in pyproject.toml must not drift from what these tests pin."""
    from pathlib import Path

    pyproject = (
        Path(__file__).resolve().parents[1] / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert 'zep-cloud==3.27.0' in pyproject, (
        "zep-cloud pin changed in pyproject.toml; update this test file's "
        "surface assertions against the new SDK in the same change"
    )


def test_graph_level_methods_exist(client):
    """graph.* call sites: graph_builder, zep_live_canary, zep_graph_memory_updater."""
    for method in (
        "create",
        "get",
        "delete",
        "set_ontology",
        "list_entity_types",
        "add",
        "add_batch",
        "search",
    ):
        assert callable(getattr(client.graph, method, None)), (
            f"client.graph.{method} is gone or not callable — a live call "
            "site in backend/app now points at a missing SDK method"
        )


def test_node_and_edge_read_methods_exist(client):
    """Paged/point reads: zep_paging, zep_entity_reader, zep_tools."""
    node = client.graph.node
    edge = client.graph.edge
    for method in ("get_by_graph_id", "get", "get_edges"):
        assert callable(getattr(node, method, None)), (
            f"client.graph.node.{method} is gone — zep_entity_reader/"
            "zep_paging read paths are broken on this SDK"
        )
    assert callable(getattr(edge, "get_by_graph_id", None)), (
        "client.graph.edge.get_by_graph_id is gone — zep_paging edge "
        "pagination is broken on this SDK"
    )


def test_entity_edge_read_uses_the_current_method_name(client):
    """The renamed-in-3.x method must stay dead.

    ``get_entity_edges`` was renamed to ``get_edges``; this repository (and
    upstream before the fix) shipped a call site the pinned SDK did not
    expose. Asserting the OLD name is absent guards a regression the other
    direction: code re-introduced by cherry-pick or merge conflict.
    """
    assert not hasattr(client.graph.node, "get_entity_edges"), (
        "the SDK now exposes get_entity_edges again — re-read the rename "
        "history before relying on either name, and update "
        "zep_entity_reader.get_node_edges to match"
    )


def test_paged_reads_still_accept_uuid_cursor(client):
    """zep_paging passes uuid_cursor= to both paged reads.

    The current SDK also accepts an opaque ``cursor``; ours deliberately
    uses ``uuid_cursor`` (typed as the last item's uuid) because a repeated
    cursor is detectable. If the SDK drops the parameter, pagination
    silently degrades to fetching page one forever.
    """
    node_sig = inspect.signature(client.graph.node.get_by_graph_id)
    edge_sig = inspect.signature(client.graph.edge.get_by_graph_id)
    assert "uuid_cursor" in node_sig.parameters
    assert "uuid_cursor" in edge_sig.parameters
    # zep_paging also passes limit=; both reads must keep accepting it.
    assert "limit" in node_sig.parameters
    assert "limit" in edge_sig.parameters


def test_search_keeps_the_parameter_names_we_pass(client):
    """Profile generation and report tooling call graph.search with
    query=/graph_id=/limit=/scope=/reranker=; a parameter rename in the SDK
    surfaces as a TypeError inside a retry loop, i.e. a 500."""
    params = inspect.signature(client.graph.search).parameters
    for name in ("query", "graph_id", "limit", "scope", "reranker"):
        assert name in params, (
            f"graph.search no longer accepts {name}= — update "
            "oasis_profile_generator/zep_tools search call sites"
        )


def test_add_batch_accepts_graph_id_and_episodes(client):
    """graph_builder submits episodes in batches with graph_id=/episodes=."""
    params = inspect.signature(client.graph.add_batch).parameters
    for name in ("graph_id", "episodes"):
        assert name in params, (
            f"graph.add_batch no longer accepts {name}= — the graph build "
            "path is broken on this SDK"
        )


def test_episode_reads_exist(client):
    """graph_builder polls episode.get; graph readiness polls get_by_graph_id."""
    episode = client.graph.episode
    assert callable(getattr(episode, "get", None))
    assert callable(getattr(episode, "get_by_graph_id", None))

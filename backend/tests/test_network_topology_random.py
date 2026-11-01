"""Offline topology replay and non-destructive validation checks."""

import asyncio
import random
import sqlite3
from types import SimpleNamespace

import pytest

from app.services.network_topology import apply_homophily_rewiring, apply_network_topology


class FakeAgentGraph:
    def __init__(self, agent_ids=range(30)):
        self.agent_ids = list(agent_ids)
        self.edges = {(0, 1), (1, 0)}
        self.removed = []

    def get_agents(self):
        return [(i, SimpleNamespace(name=f"Agent_{i}")) for i in self.agent_ids]

    def get_edges(self):
        return list(self.edges)

    def remove_edge(self, u, v):
        self.removed.append((u, v))
        self.edges.discard((u, v))

    def add_edge(self, u, v):
        self.edges.add((u, v))


@pytest.mark.parametrize("kind", ["small-world", "scale-free", "random", "complete"])
def test_seeded_topologies_replay_with_stable_agent_mapping(kind):
    config = {"seed": 42, "network_topology": {"type": kind}}
    first = FakeAgentGraph()
    second = FakeAgentGraph(reversed(range(30)))
    before = random.getstate()
    apply_network_topology(first, config)
    assert random.getstate() == before
    try:
        for _ in range(100):
            random.random()
        apply_network_topology(second, config)
    finally:
        random.setstate(before)
    assert first.edges == second.edges
    assert first.edges
    assert all(u != v for u, v in first.edges)
    assert all((v, u) in first.edges for u, v in first.edges)


@pytest.mark.parametrize("config", [{}, {"seed": 42}, {"seed": 42, "network_topology": {"type": "none"}}])
def test_seed_alone_does_not_enable_topology(config):
    graph = FakeAgentGraph()
    apply_network_topology(graph, config)
    assert graph.edges == {(0, 1), (1, 0)}
    assert graph.removed == []


@pytest.mark.parametrize("topology", [
    {"type": "unknown"},
    {"type": "small-world", "k": -1},
    {"type": "small-world", "k": 31},
    {"type": "small-world", "k": 2.5},
    {"type": "small-world", "k": True},
    {"type": "small-world", "p": -0.1},
    {"type": "random", "p": 1.1},
    {"type": "random", "p": "0.2"},
    {"type": "random", "p": float("nan")},
    {"type": "random", "p": float("inf")},
    {"type": "random", "p": True},
    {"type": "scale-free", "m": 0},
    {"type": "scale-free", "m": 30},
    {"type": "scale-free", "m": 1.5},
    {"type": "scale-free", "m": True},
    "random",
])
def test_invalid_topology_preserves_existing_graph(topology):
    graph = FakeAgentGraph()
    with pytest.raises(ValueError):
        apply_network_topology(graph, {"seed": 42, "network_topology": topology})
    assert graph.edges == {(0, 1), (1, 0)}
    assert graph.removed == []


@pytest.mark.parametrize("seed", [True, -1, 2**63, "42", None])
def test_invalid_seed_preserves_existing_graph(seed):
    graph = FakeAgentGraph()
    with pytest.raises(ValueError, match="seed"):
        apply_network_topology(graph, {"seed": seed, "network_topology": {"type": "random"}})
    assert graph.removed == []


def test_generator_failure_preserves_existing_graph(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("generator failed")

    monkeypatch.setattr("app.services.network_topology.nx.erdos_renyi_graph", fail)
    graph = FakeAgentGraph()
    with pytest.raises(RuntimeError, match="generator failed"):
        apply_network_topology(graph, {"network_topology": {"type": "random"}})
    assert graph.removed == []


def test_seeded_homophily_edge_sampling_replays_with_mocked_provider(tmp_path, monkeypatch):
    from app.services import network_topology as topology

    with sqlite3.connect(tmp_path / "simulation_observations.db") as connection:
        connection.execute("CREATE TABLE reflections (id INTEGER, agent_name TEXT, synthesis_text TEXT, round_num INTEGER)")
        connection.executemany(
            "INSERT INTO reflections VALUES (?, ?, ?, ?)",
            [(i, f"Agent_{i}", f"Fictional stance {i}", 1) for i in range(30)],
        )
    prompts = []

    class FakeLLM:
        def chat(self, prompt, **kwargs):
            prompts.append(prompt)
            return "NO"

    monkeypatch.setattr(topology, "LLMClient", FakeLLM)
    config = {"seed": 42, "homophily_rewiring": {"enabled": True, "max_edges_to_evaluate": 4}}
    graph = FakeAgentGraph()
    graph.edges = {(i, i + 1) for i in range(29)}
    before = random.getstate()
    asyncio.run(apply_homophily_rewiring(graph, str(tmp_path), 2, config))
    assert random.getstate() == before
    expected = prompts[:]
    prompts.clear()
    monkeypatch.setattr(graph, "get_edges", lambda: list(reversed(sorted(graph.edges))))
    asyncio.run(apply_homophily_rewiring(graph, str(tmp_path), 2, config))
    assert prompts == expected
    assert len(prompts) == 4

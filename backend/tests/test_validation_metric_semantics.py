import networkx as nx

from app.services.validation_engine import ValidationEngine


def test_within_community_share_uses_interaction_weights():
    graph = nx.DiGraph()
    graph.add_edge(1, 2, weight=100)
    graph.add_edge(2, 3, weight=1)

    score = ValidationEngine()._compute_echo_chamber_score(
        graph,
        [{1, 2}, {3}],
    )

    assert score == 100 / 101

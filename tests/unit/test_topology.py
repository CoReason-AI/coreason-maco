# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import networkx as nx
import pytest

from coreason_maco.engine.topology import (
    CyclicDependencyError,
    GraphIntegrityError,
    TopologyEngine,
)


@pytest.fixture  # type: ignore[misc]
def topology_engine() -> TopologyEngine:
    return TopologyEngine()


def test_linear_execution(topology_engine: TopologyEngine) -> None:
    """Test A -> B -> C"""
    g = nx.DiGraph()
    g.add_edges_from([("A", "B"), ("B", "C")])

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)

    # Layers should be [[A], [B], [C]]
    # Note: topological_generations return order of nodes in a layer is not guaranteed to be sorted,
    # but for single nodes it is trivial.
    assert layers == [["A"], ["B"], ["C"]]


def test_parallel_execution(topology_engine: TopologyEngine) -> None:
    """Test A -> B, A -> C, B -> D, C -> D (Diamond)"""
    g = nx.DiGraph()
    g.add_edges_from([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)

    # Layers should be [[A], [B, C] or [C, B], [D]]
    assert len(layers) == 3
    assert layers[0] == ["A"]
    assert set(layers[1]) == {"B", "C"}
    assert layers[2] == ["D"]


def test_cyclic_graph(topology_engine: TopologyEngine) -> None:
    """Test A -> B -> A"""
    g = nx.DiGraph()
    g.add_edges_from([("A", "B"), ("B", "A")])

    with pytest.raises(CyclicDependencyError):
        topology_engine.validate_graph(g)

    with pytest.raises(CyclicDependencyError):
        topology_engine.get_execution_layers(g)


def test_islands_graph(topology_engine: TopologyEngine) -> None:
    """Test A -> B, C -> D (Disconnected)"""
    g = nx.DiGraph()
    g.add_edges_from([("A", "B"), ("C", "D")])

    with pytest.raises(GraphIntegrityError):
        topology_engine.validate_graph(g)


def test_single_node(topology_engine: TopologyEngine) -> None:
    """Test A"""
    g = nx.DiGraph()
    g.add_node("A")

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)

    assert layers == [["A"]]


def test_empty_graph(topology_engine: TopologyEngine) -> None:
    """Test Empty"""
    g = nx.DiGraph()

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)
    assert layers == []

# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import random
from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.topology import (
    CyclicDependencyError,
    GraphIntegrityError,
    TopologyEngine,
)


@pytest.fixture  # type: ignore
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


# --- New Extended Tests ---


def test_self_loop(topology_engine: TopologyEngine) -> None:
    """Test A -> A"""
    g = nx.DiGraph()
    g.add_edge("A", "A")

    with pytest.raises(CyclicDependencyError):
        topology_engine.validate_graph(g)


def test_isolated_node_mixed(topology_engine: TopologyEngine) -> None:
    """Test A -> B, C (Isolated)"""
    g = nx.DiGraph()
    g.add_edge("A", "B")
    g.add_node("C")

    with pytest.raises(GraphIntegrityError):
        topology_engine.validate_graph(g)


def test_complex_parallel_paths(topology_engine: TopologyEngine) -> None:
    """
    Test uneven parallel paths merging back.
    Path 1: A -> B -> D
    Path 2: A -> C -> E -> D
    Layers expected:
    [A]
    [B, C]
    [E] (B is done, but E is needed for D) -> Wait, no.
    Standard topological generations:
    Gen 0: A
    Gen 1: B, C
    Gen 2: E
    Gen 3: D
    Wait, if B is done at Gen 1, does it wait?
    Topological generations groups nodes whose *dependencies* are met.
    A: {}
    B: {A}, C: {A} -> Gen 1
    E: {C} -> Gen 2 (B is already ready)
    D: {B, E} -> Needs E, so Gen 3.
    So yes: [[A], [B, C], [E], [D]] is one valid topological grouping,
    but `topological_generations` produces the *earliest* possible generation for each node?
    Actually networkx topological_generations produces:
    Stratification where all predecessors of a node in gen k are in generations < k.
    Let's verify the output.
    """
    g = nx.DiGraph()
    g.add_edges_from([("A", "B"), ("B", "D"), ("A", "C"), ("C", "E"), ("E", "D")])

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)

    # Expected:
    # 0: A
    # 1: B, C
    # 2: E (B is already processed in 1, so it doesn't appear again)
    # 3: D
    assert layers[0] == ["A"]
    assert set(layers[1]) == {"B", "C"}
    assert layers[2] == ["E"]
    assert layers[3] == ["D"]
    assert len(layers) == 4


def test_multi_root_multi_sink(topology_engine: TopologyEngine) -> None:
    """
    Roots: R1, R2
    R1 -> M1
    R2 -> M1
    M1 -> S1
    M1 -> S2
    """
    g = nx.DiGraph()
    g.add_edges_from([("R1", "M1"), ("R2", "M1"), ("M1", "S1"), ("M1", "S2")])

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)

    # 0: R1, R2
    # 1: M1
    # 2: S1, S2
    assert set(layers[0]) == {"R1", "R2"}
    assert layers[1] == ["M1"]
    assert set(layers[2]) == {"S1", "S2"}


def test_large_dag(topology_engine: TopologyEngine) -> None:
    """
    Programmatically generate a larger DAG to ensure stability.
    Structure: A "V" shape expanding and contracting.
    A -> [B1...B10] -> C
    """
    g = nx.DiGraph()
    g.add_node("A")
    g.add_node("C")
    intermediates: List[str] = [f"B{i}" for i in range(20)]

    for node in intermediates:
        g.add_edge("A", node)
        g.add_edge(node, "C")

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)

    # 0: A
    # 1: B0...B19
    # 2: C
    assert len(layers) == 3
    assert layers[0] == ["A"]
    assert len(layers[1]) == 20
    assert set(layers[1]) == set(intermediates)
    assert layers[2] == ["C"]


def test_random_large_dag(topology_engine: TopologyEngine) -> None:
    """
    Generate a random DAG and verify it validates.
    """
    # Create a random DAG
    # Start with nodes 0..19
    # Add edges only from i -> j where i < j to guarantee acyclic
    g = nx.DiGraph()
    nodes = [str(i) for i in range(20)]
    g.add_nodes_from(nodes)

    # Ensure connectivity: 0 -> 1 -> 2 ... -> 19
    for i in range(19):
        g.add_edge(str(i), str(i + 1))

    # Add random extra edges
    random.seed(42)
    for _ in range(10):
        u = random.randint(0, 18)
        v = random.randint(u + 1, 19)
        g.add_edge(str(u), str(v))

    topology_engine.validate_graph(g)
    layers = topology_engine.get_execution_layers(g)

    # Just verify we got layers and all nodes are present
    flat_nodes = [node for layer in layers for node in layer]
    assert len(flat_nodes) == 20
    assert set(flat_nodes) == set(nodes)

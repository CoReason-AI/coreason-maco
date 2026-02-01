# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import List

import pytest

from coreason_maco.core.manifest import AgentNode, Edge, Node, RecipeManifest, VisualMetadata
from coreason_maco.engine.topology import CyclicDependencyError, GraphIntegrityError, TopologyEngine


@pytest.fixture  # type: ignore
def topology_engine() -> TopologyEngine:
    return TopologyEngine()


def create_visual() -> VisualMetadata:
    return VisualMetadata(x_y_coordinates=[0.0, 0.0], label="Node", icon="box")


def create_manifest(nodes: List[Node], edges: List[Edge], name: str = "Test") -> RecipeManifest:
    return RecipeManifest(
        id="test-id",
        version="1.0.0",
        name=name,
        description="Test Description",
        topology={"nodes": nodes, "edges": edges},
        interface={"inputs": {}, "outputs": {}},
        state={"schema": {}},
        parameters={},
    )


def test_build_simple_linear_graph(topology_engine: TopologyEngine) -> None:
    manifest = create_manifest(
        name="Linear",
        nodes=[
            AgentNode(id="A", type="agent", agent_name="AgentA", visual=create_visual()),
            AgentNode(id="B", type="agent", agent_name="AgentB", visual=create_visual()),
        ],
        edges=[Edge(source_node_id="A", target_node_id="B")],
    )

    graph = topology_engine.build_graph(manifest)

    assert graph.name == "Linear"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.nodes["A"]["type"] == "agent"
    assert graph.has_edge("A", "B")


def test_build_branching_graph(topology_engine: TopologyEngine) -> None:
    manifest = create_manifest(
        name="Branching",
        nodes=[
            AgentNode(id="A", type="agent", agent_name="AgentA", visual=create_visual()),
            AgentNode(id="B", type="agent", agent_name="AgentB", visual=create_visual()),
            AgentNode(id="C", type="agent", agent_name="AgentC", visual=create_visual()),
            AgentNode(id="D", type="agent", agent_name="AgentD", visual=create_visual()),
        ],
        edges=[
            Edge(source_node_id="A", target_node_id="B"),
            Edge(source_node_id="A", target_node_id="C"),
            Edge(source_node_id="B", target_node_id="D"),
            Edge(source_node_id="C", target_node_id="D"),
        ],
    )

    graph = topology_engine.build_graph(manifest)

    assert len(graph.nodes) == 4
    assert len(graph.edges) == 4
    assert set(graph.successors("A")) == {"B", "C"}
    assert set(graph.predecessors("D")) == {"B", "C"}


def test_build_conditional_graph(topology_engine: TopologyEngine) -> None:
    manifest = create_manifest(
        name="Conditional",
        nodes=[
            AgentNode(id="A", type="agent", agent_name="AgentA", visual=create_visual()),
            AgentNode(id="B", type="agent", agent_name="AgentB", visual=create_visual()),
            AgentNode(id="C", type="agent", agent_name="AgentC", visual=create_visual()),
        ],
        edges=[
            Edge(source_node_id="A", target_node_id="B", condition="yes"),
            Edge(source_node_id="A", target_node_id="C", condition="no"),
        ],
    )

    graph = topology_engine.build_graph(manifest)

    edge_ab = graph.get_edge_data("A", "B")
    edge_ac = graph.get_edge_data("A", "C")

    assert edge_ab["condition"] == "yes"
    assert edge_ac["condition"] == "no"


def test_build_disconnected_graph_raises_error(topology_engine: TopologyEngine) -> None:
    manifest = create_manifest(
        name="Disconnected",
        nodes=[
            AgentNode(id="A", type="agent", agent_name="AgentA", visual=create_visual()),
            AgentNode(id="B", type="agent", agent_name="AgentB", visual=create_visual()),
        ],
        edges=[],
    )

    with pytest.raises(GraphIntegrityError):
        topology_engine.build_graph(manifest)


def test_build_cyclic_graph_raises_error(topology_engine: TopologyEngine) -> None:
    manifest = create_manifest(
        name="Cyclic",
        nodes=[
            AgentNode(id="A", type="agent", agent_name="AgentA", visual=create_visual()),
            AgentNode(id="B", type="agent", agent_name="AgentB", visual=create_visual()),
        ],
        edges=[Edge(source_node_id="A", target_node_id="B"), Edge(source_node_id="B", target_node_id="A")],
    )

    with pytest.raises(CyclicDependencyError):
        topology_engine.build_graph(manifest)


def test_node_config_preserved(topology_engine: TopologyEngine) -> None:
    # Use AgentNode and verify agent_name is preserved in config
    manifest = create_manifest(
        name="Config", nodes=[AgentNode(id="A", type="agent", agent_name="GPT-4", visual=create_visual())], edges=[]
    )

    graph = topology_engine.build_graph(manifest)

    node_a = graph.nodes["A"]
    # TopologyEngine now extracts agent_name into config
    assert node_a["config"]["agent_name"] == "GPT-4"

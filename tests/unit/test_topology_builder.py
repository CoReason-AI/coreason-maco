# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import pytest

from coreason_maco.core.manifest import AgentNode, Edge, GraphTopology, RecipeManifest
from coreason_maco.engine.topology import CyclicDependencyError, GraphIntegrityError, TopologyEngine


@pytest.fixture  # type: ignore
def topology_engine() -> TopologyEngine:
    return TopologyEngine()


def test_build_simple_linear_graph(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        id="linear-recipe",
        version="1.0.0",
        name="Linear",
        inputs={},
        graph=GraphTopology(
            nodes=[
                AgentNode(id="A", type="agent", agent_name="AgentA"),
                AgentNode(id="B", type="agent", agent_name="AgentB"),
            ],
            edges=[Edge(source_node_id="A", target_node_id="B")],
        ),
    )

    graph = topology_engine.build_graph(manifest)

    assert graph.name == "Linear"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.nodes["A"]["type"] == "agent"
    assert graph.has_edge("A", "B")


def test_build_branching_graph(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        id="branching-recipe",
        version="1.0.0",
        name="Branching",
        inputs={},
        graph=GraphTopology(
            nodes=[
                AgentNode(id="A", type="agent", agent_name="Start"),
                AgentNode(id="B", type="agent", agent_name="Process1"),
                AgentNode(id="C", type="agent", agent_name="Process2"),
                AgentNode(id="D", type="agent", agent_name="End"),
            ],
            edges=[
                Edge(source_node_id="A", target_node_id="B"),
                Edge(source_node_id="A", target_node_id="C"),
                Edge(source_node_id="B", target_node_id="D"),
                Edge(source_node_id="C", target_node_id="D"),
            ],
        ),
    )

    graph = topology_engine.build_graph(manifest)

    assert len(graph.nodes) == 4
    assert len(graph.edges) == 4
    assert set(graph.successors("A")) == {"B", "C"}
    assert set(graph.predecessors("D")) == {"B", "C"}


def test_build_conditional_graph(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        id="conditional-recipe",
        version="1.0.0",
        name="Conditional",
        inputs={},
        graph=GraphTopology(
            nodes=[
                AgentNode(id="A", type="agent", agent_name="Start"),
                AgentNode(id="B", type="agent", agent_name="PathB"),
                AgentNode(id="C", type="agent", agent_name="PathC"),
            ],
            edges=[
                Edge(source_node_id="A", target_node_id="B", condition="yes"),
                Edge(source_node_id="A", target_node_id="C", condition="no"),
            ],
        ),
    )

    graph = topology_engine.build_graph(manifest)

    edge_ab = graph.get_edge_data("A", "B")
    edge_ac = graph.get_edge_data("A", "C")

    assert edge_ab["condition"] == "yes"
    assert edge_ac["condition"] == "no"


def test_build_disconnected_graph_raises_error(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        id="disconnected-recipe",
        version="1.0.0",
        name="Disconnected",
        inputs={},
        graph=GraphTopology(
            nodes=[
                AgentNode(id="A", type="agent", agent_name="Start"),
                AgentNode(id="B", type="agent", agent_name="Island"),
            ],
            edges=[],
        ),
    )

    with pytest.raises(GraphIntegrityError):
        topology_engine.build_graph(manifest)


def test_build_cyclic_graph_raises_error(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        id="cyclic-recipe",
        version="1.0.0",
        name="Cyclic",
        inputs={},
        graph=GraphTopology(
            nodes=[
                AgentNode(id="A", type="agent", agent_name="NodeA"),
                AgentNode(id="B", type="agent", agent_name="NodeB"),
            ],
            edges=[Edge(source_node_id="A", target_node_id="B"), Edge(source_node_id="B", target_node_id="A")],
        ),
    )

    with pytest.raises(CyclicDependencyError):
        topology_engine.build_graph(manifest)


def test_node_config_preserved(topology_engine: TopologyEngine) -> None:
    # AgentNode fields are preserved in 'config'
    manifest = RecipeManifest(
        id="config-recipe",
        version="1.0.0",
        name="Config",
        inputs={},
        graph=GraphTopology(nodes=[AgentNode(id="A", type="agent", agent_name="gpt-4")], edges=[]),
    )

    graph = topology_engine.build_graph(manifest)

    node_a = graph.nodes["A"]
    # We expect agent_name to be in the config dictionary
    assert node_a["config"]["agent_name"] == "gpt-4"

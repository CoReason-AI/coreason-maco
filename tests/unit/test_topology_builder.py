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

from coreason_maco.core.manifest import EdgeModel, NodeModel, RecipeManifest
from coreason_maco.engine.topology import CyclicDependencyError, GraphIntegrityError, TopologyEngine


@pytest.fixture  # type: ignore
def topology_engine() -> TopologyEngine:
    return TopologyEngine()


def test_build_simple_linear_graph(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        name="Linear",
        nodes=[NodeModel(id="A", type="START"), NodeModel(id="B", type="END")],
        edges=[EdgeModel(source="A", target="B")],
    )

    graph = topology_engine.build_graph(manifest)

    assert graph.name == "Linear"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.nodes["A"]["type"] == "START"
    assert graph.has_edge("A", "B")


def test_build_branching_graph(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        name="Branching",
        nodes=[
            NodeModel(id="A", type="START"),
            NodeModel(id="B", type="PROCESS"),
            NodeModel(id="C", type="PROCESS"),
            NodeModel(id="D", type="END"),
        ],
        edges=[
            EdgeModel(source="A", target="B"),
            EdgeModel(source="A", target="C"),
            EdgeModel(source="B", target="D"),
            EdgeModel(source="C", target="D"),
        ],
    )

    graph = topology_engine.build_graph(manifest)

    assert len(graph.nodes) == 4
    assert len(graph.edges) == 4
    assert set(graph.successors("A")) == {"B", "C"}
    assert set(graph.predecessors("D")) == {"B", "C"}


def test_build_conditional_graph(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        name="Conditional",
        nodes=[NodeModel(id="A", type="START"), NodeModel(id="B", type="PROCESS"), NodeModel(id="C", type="PROCESS")],
        edges=[EdgeModel(source="A", target="B", condition="yes"), EdgeModel(source="A", target="C", condition="no")],
    )

    graph = topology_engine.build_graph(manifest)

    edge_ab = graph.get_edge_data("A", "B")
    edge_ac = graph.get_edge_data("A", "C")

    assert edge_ab["condition"] == "yes"
    assert edge_ac["condition"] == "no"


def test_build_disconnected_graph_raises_error(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        name="Disconnected", nodes=[NodeModel(id="A", type="START"), NodeModel(id="B", type="ISLAND")], edges=[]
    )

    with pytest.raises(GraphIntegrityError):
        topology_engine.build_graph(manifest)


def test_build_cyclic_graph_raises_error(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        name="Cyclic",
        nodes=[NodeModel(id="A", type="START"), NodeModel(id="B", type="PROCESS")],
        edges=[EdgeModel(source="A", target="B"), EdgeModel(source="B", target="A")],
    )

    with pytest.raises(CyclicDependencyError):
        topology_engine.build_graph(manifest)


def test_node_config_preserved(topology_engine: TopologyEngine) -> None:
    manifest = RecipeManifest(
        name="Config", nodes=[NodeModel(id="A", type="LLM", config={"model": "gpt-4", "temp": 0.7})], edges=[]
    )

    graph = topology_engine.build_graph(manifest)

    node_a = graph.nodes["A"]
    assert node_a["model"] == "gpt-4"
    assert node_a["temp"] == 0.7

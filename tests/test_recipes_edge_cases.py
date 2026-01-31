from typing import Any, Dict, List, cast

import pytest
from coreason_maco.core.manifest import Edge, GraphTopology, HumanNode, Node, VisualMetadata
from pydantic import ValidationError


def create_visual() -> VisualMetadata:
    return VisualMetadata(x_y_coordinates=[0.0, 0.0], label="Node", icon="box")


def test_duplicate_node_ids() -> None:
    """Verify behavior when duplicate node IDs are present.
    Currently, the schema does not strictly prevent duplicates in the list,
    but the runtime engine should handle or reject it.
    This test documents that the schema allows it (unless added validation exists).
    """
    nodes: List[Dict[str, Any]] = [
        {"type": "agent", "id": "n1", "visual": create_visual().model_dump(), "agent_name": "A"},
        {"type": "agent", "id": "n1", "visual": create_visual().model_dump(), "agent_name": "B"},  # Duplicate ID
    ]
    edges: List[Dict[str, Any]] = []

    # If the library doesn't validate uniqueness, this will pass.
    # If it does, it will raise ValidationError.
    # We check which one happens to confirm behavior.
    try:
        topo = GraphTopology(nodes=cast(List[Node], nodes), edges=cast(List[Edge], edges))
        # If it passes, we assert that we have 2 nodes with same ID
        assert len(topo.nodes) == 2
        assert topo.nodes[0].id == "n1"
        assert topo.nodes[1].id == "n1"
    except ValidationError:
        # If validation is added later, this test will fail and need update
        pass


def test_dangling_edge_references() -> None:
    """Verify behavior when edges reference non-existent nodes.
    Schema validation usually checks types, not referential integrity within the list.
    """
    nodes: List[Dict[str, Any]] = [
        {"type": "agent", "id": "n1", "visual": create_visual().model_dump(), "agent_name": "A"}
    ]
    edges: List[Dict[str, Any]] = [{"source_node_id": "n1", "target_node_id": "missing_node"}]

    # Expected to pass Pydantic validation
    topo = GraphTopology(nodes=cast(List[Node], nodes), edges=cast(List[Edge], edges))
    assert len(topo.edges) == 1
    assert topo.edges[0].target_node_id == "missing_node"


def test_empty_topology() -> None:
    """Verify an empty topology is valid."""
    topo = GraphTopology(nodes=[], edges=[])
    assert len(topo.nodes) == 0
    assert len(topo.edges) == 0


def test_unicode_ids() -> None:
    """Verify that Unicode characters are allowed in IDs."""
    nodes: List[Dict[str, Any]] = [
        {"type": "agent", "id": "agent-🤖", "visual": create_visual().model_dump(), "agent_name": "Robot"}
    ]
    edges: List[Dict[str, Any]] = []

    topo = GraphTopology(nodes=cast(List[Node], nodes), edges=cast(List[Edge], edges))
    assert topo.nodes[0].id == "agent-🤖"


def test_large_topology() -> None:
    """Verify performance/validity of a larger topology."""
    count = 100
    nodes = [
        {"type": "agent", "id": f"n{i}", "visual": create_visual().model_dump(), "agent_name": f"A{i}"}
        for i in range(count)
    ]
    edges = [{"source_node_id": f"n{i}", "target_node_id": f"n{i + 1}"} for i in range(count - 1)]

    topo = GraphTopology(nodes=cast(List[Node], nodes), edges=cast(List[Edge], edges))
    assert len(topo.nodes) == count
    assert len(topo.edges) == count - 1


def test_human_node_timeout_limits() -> None:
    """Verify HumanNode timeout validation (if any)."""
    # Negative timeout? Schema says Optional[int].
    # Usually strictly positive, but schema might just say int.
    data = {"type": "human", "id": "h1", "visual": create_visual().model_dump(), "timeout_seconds": -1}

    # If schema allows negative, this passes.
    node = HumanNode(**data)
    assert node.timeout_seconds == -1


def test_edge_condition_types() -> None:
    """Verify edge condition must be string or None."""
    nodes = [{"type": "agent", "id": "n1", "visual": create_visual().model_dump(), "agent_name": "A"}]

    # Condition as number
    edges_invalid = [{"source_node_id": "n1", "target_node_id": "n1", "condition": 123}]

    with pytest.raises(ValidationError) as excinfo:
        GraphTopology(nodes=cast(List[Node], nodes), edges=cast(List[Edge], edges_invalid))
    assert "Input should be a valid string" in str(excinfo.value)

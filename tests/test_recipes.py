from typing import Any, Dict, List, cast

import pytest
from coreason_maco.core.manifest import (
    AgentNode,
    CouncilConfig,
    Edge,
    GraphTopology,
    HumanNode,
    LogicNode,
    Node,
    RecipeManifest,
    VisualMetadata,
)
from pydantic import ValidationError


# Helpers
def create_visual(x: float = 0.0, y: float = 0.0, label: str = "Node", icon: str = "box") -> VisualMetadata:
    return VisualMetadata(x_y_coordinates=[x, y], label=label, icon=icon)


def create_council() -> CouncilConfig:
    return CouncilConfig(strategy="consensus", voters=["Alice", "Bob"])


# Tests


def test_polymorphism_nodes() -> None:
    """Verify that a list of mixed dictionaries correctly parses into specific Python classes."""
    data: List[Dict[str, Any]] = [
        {
            "type": "agent",
            "id": "agent-1",
            "visual": {"x_y_coordinates": [0.0, 0.0], "label": "Agent", "icon": "robot"},
            "agent_name": "Writer",
        },
        {
            "type": "human",
            "id": "human-1",
            "visual": {"x_y_coordinates": [1.0, 0.0], "label": "Reviewer", "icon": "user"},
            "timeout_seconds": 3600,
            "council_config": {"strategy": "majority", "voters": ["Manager"]},
        },
        {
            "type": "logic",
            "id": "logic-1",
            "visual": {"x_y_coordinates": [2.0, 0.0], "label": "Filter", "icon": "code"},
            "code": "return True",
        },
    ]

    # We can validate this list as part of a GraphTopology or strictly as a list of Nodes adapter
    # Let's use GraphTopology to test the whole structure
    topology = GraphTopology(nodes=cast(List[Node], data), edges=[])

    assert len(topology.nodes) == 3
    assert isinstance(topology.nodes[0], AgentNode)
    assert topology.nodes[0].agent_name == "Writer"

    assert isinstance(topology.nodes[1], HumanNode)
    assert topology.nodes[1].timeout_seconds == 3600
    assert topology.nodes[1].council_config is not None
    assert topology.nodes[1].council_config.strategy == "majority"

    assert isinstance(topology.nodes[2], LogicNode)
    assert topology.nodes[2].code == "return True"


def test_serialization() -> None:
    """Verify .model_dump_json() produces the correct type discriminator fields."""
    node = AgentNode(type="agent", id="a1", visual=create_visual(), agent_name="Bond")

    # Dump to JSON string
    json_str = node.model_dump_json()
    assert '"type":"agent"' in json_str or '"type": "agent"' in json_str

    # Parse back
    parsed = AgentNode.model_validate_json(json_str)
    assert parsed.agent_name == "Bond"


def test_version_validation() -> None:
    """Ensure version string validation works as expected (allowing v prefix and semver)."""
    valid_manifest: Dict[str, Any] = {
        "id": "recipe-1",
        "version": "1.0.0",
        "name": "Test Recipe",
        "description": "A test",
        "topology": {"nodes": [], "edges": []},
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
    }

    # Should pass
    RecipeManifest(**valid_manifest)

    # Valid variants (due to normalization or extended regex)
    # The external package allows 'v' prefix and prerelease tags
    valid_variants = ["v1.0.0", "1.0.0-beta", "v2.0.0-rc1"]
    for v in valid_variants:
        data = valid_manifest.copy()
        data["version"] = v
        # Should not raise
        RecipeManifest(**data)

    # Invalid versions
    invalid_versions = ["1.0", "one.point.oh", "invalid"]

    for v in invalid_versions:
        data = valid_manifest.copy()
        data["version"] = v
        with pytest.raises(ValidationError) as excinfo:
            RecipeManifest(**data)
        # Verify the error relates to the pattern
        assert "String should match pattern" in str(excinfo.value)


def test_extra_fields_forbidden() -> None:
    """Verify that extra fields are forbidden."""
    data: Dict[str, Any] = {
        "type": "agent",
        "id": "agent-1",
        "visual": {"x_y_coordinates": [0.0, 0.0], "label": "Agent", "icon": "robot"},
        "agent_name": "Writer",
        "extra_field": "I should not be here",
    }

    with pytest.raises(ValidationError) as excinfo:
        AgentNode(**data)
    assert "Extra inputs are not permitted" in str(excinfo.value)


def test_topology_validation() -> None:
    """Test full topology validation."""
    nodes: List[Dict[str, Any]] = [
        {"type": "agent", "id": "n1", "visual": create_visual().model_dump(), "agent_name": "A"},
        {"type": "logic", "id": "n2", "visual": create_visual().model_dump(), "code": "pass"},
    ]
    edges: List[Dict[str, Any]] = [{"source_node_id": "n1", "target_node_id": "n2", "condition": "x > 5"}]

    topo = GraphTopology(nodes=cast(List[Node], nodes), edges=cast(List[Edge], edges))
    assert len(topo.edges) == 1
    assert topo.edges[0].condition == "x > 5"

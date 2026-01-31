import pytest
from pydantic import ValidationError
from coreason_manifest.recipes import (
    RecipeManifest, GraphTopology, AgentNode, HumanNode, LogicNode,
    VisualMetadata, CouncilConfig, Edge, Node
)

# Helpers
def create_visual(x=0.0, y=0.0, label="Node", icon="box"):
    return VisualMetadata(x_y_coordinates=[x, y], label=label, icon=icon)

def create_council():
    return CouncilConfig(strategy="consensus", voters=["Alice", "Bob"])

# Tests

def test_polymorphism_nodes():
    """Verify that a list of mixed dictionaries correctly parses into specific Python classes."""
    data = [
        {
            "type": "agent",
            "id": "agent-1",
            "visual": {"x_y_coordinates": [0.0, 0.0], "label": "Agent", "icon": "robot"},
            "agent_name": "Writer"
        },
        {
            "type": "human",
            "id": "human-1",
            "visual": {"x_y_coordinates": [1.0, 0.0], "label": "Reviewer", "icon": "user"},
            "timeout_seconds": 3600,
            "council": {"strategy": "majority", "voters": ["Manager"]}
        },
        {
            "type": "logic",
            "id": "logic-1",
            "visual": {"x_y_coordinates": [2.0, 0.0], "label": "Filter", "icon": "code"},
            "code": "return True"
        }
    ]

    # We can validate this list as part of a GraphTopology or strictly as a list of Nodes adapter
    # Let's use GraphTopology to test the whole structure
    topology = GraphTopology(nodes=data, edges=[])

    assert len(topology.nodes) == 3
    assert isinstance(topology.nodes[0], AgentNode)
    assert topology.nodes[0].agent_name == "Writer"

    assert isinstance(topology.nodes[1], HumanNode)
    assert topology.nodes[1].timeout_seconds == 3600
    assert topology.nodes[1].council.strategy == "majority"

    assert isinstance(topology.nodes[2], LogicNode)
    assert topology.nodes[2].code == "return True"

def test_serialization():
    """Verify .model_dump_json() produces the correct type discriminator fields."""
    node = AgentNode(
        type="agent",
        id="a1",
        visual=create_visual(),
        agent_name="Bond"
    )

    # Dump to JSON string
    json_str = node.model_dump_json()
    assert '"type":"agent"' in json_str or '"type": "agent"' in json_str

    # Parse back
    parsed = AgentNode.model_validate_json(json_str)
    assert parsed.agent_name == "Bond"

def test_invalid_version():
    """Ensure an invalid version string raises a ValidationError."""
    valid_manifest = {
        "id": "recipe-1",
        "version": "1.0.0",
        "name": "Test Recipe",
        "description": "A test",
        "inputs": {},
        "graph": {"nodes": [], "edges": []}
    }

    # Should pass
    RecipeManifest(**valid_manifest)

    # Invalid versions
    invalid_versions = ["1.0", "v1.0.0", "1.0.0-beta", "one.point.oh"]

    for v in invalid_versions:
        data = valid_manifest.copy()
        data["version"] = v
        with pytest.raises(ValidationError) as excinfo:
            RecipeManifest(**data)
        # Verify the error relates to the pattern
        assert "String should match pattern" in str(excinfo.value)

def test_extra_fields_forbidden():
    """Verify that extra fields are forbidden."""
    data = {
        "type": "agent",
        "id": "agent-1",
        "visual": {"x_y_coordinates": [0.0, 0.0], "label": "Agent", "icon": "robot"},
        "agent_name": "Writer",
        "extra_field": "I should not be here"
    }

    with pytest.raises(ValidationError) as excinfo:
        AgentNode(**data)
    assert "Extra inputs are not permitted" in str(excinfo.value)

def test_topology_validation():
    """Test full topology validation."""
    nodes = [
        {"type": "agent", "id": "n1", "visual": create_visual().model_dump(), "agent_name": "A"},
        {"type": "logic", "id": "n2", "visual": create_visual().model_dump(), "code": "pass"}
    ]
    edges = [
        {"source": "n1", "target": "n2", "condition": "x > 5"}
    ]

    topo = GraphTopology(nodes=nodes, edges=edges)
    assert len(topo.edges) == 1
    assert topo.edges[0].condition == "x > 5"

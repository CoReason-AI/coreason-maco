from typing import Any

import pytest
from coreason_manifest.recipes import RecipeManifest
from pydantic import ValidationError

from coreason_maco.core.controller import WorkflowController
from coreason_maco.infrastructure.server_defaults import ServerRegistry


def test_manifest_missing_topology() -> None:
    """Test that manifest validation fails if 'topology' is missing."""
    data = {
        "id": "missing-topo",
        "version": "1.0.0",
        "name": "Missing Topology",
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
        # "topology" missing
    }
    with pytest.raises(ValidationError) as exc:
        RecipeManifest(**data)
    assert "topology" in str(exc.value)


def test_manifest_invalid_node_type() -> None:
    """Test that invalid node types are rejected."""
    data = {
        "id": "invalid-node",
        "version": "1.0.0",
        "name": "Invalid Node",
        "topology": {"nodes": [{"id": "A", "type": "INVALID_TYPE", "visual": {}}], "edges": []},
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
    }
    with pytest.raises(ValidationError) as exc:
        RecipeManifest(**data)
    # Pydantic union error
    assert "Input tag 'INVALID_TYPE' found using 'type' does not match" in str(exc.value)


@pytest.mark.asyncio
async def test_agent_node_config_extraction_edge_case(mock_user_context: Any) -> None:
    """
    Test that an AgentNode without council config works,
    and prompt resolution falls back (since AgentNode has no config).
    """
    services = ServerRegistry()
    controller = WorkflowController(services)

    manifest = {
        "id": "agent-no-config",
        "version": "1.0.0",
        "name": "Agent No Config",
        "topology": {
            "nodes": [
                {
                    "id": "A",
                    "type": "agent",
                    "agent_name": "Writer",
                    "visual": {"x_y_coordinates": [0, 0], "label": "A", "icon": "box"},
                }
            ],
            "edges": [],
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
    }
    inputs = {"trace_id": "t"}

    events = []
    async for event in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        events.append(event)

    # It should run successfullly (using mock executor default response)
    done = [e for e in events if e.event_type == "NODE_DONE"]
    assert len(done) == 1
    assert done[0].node_id == "A"


@pytest.mark.asyncio
async def test_logic_node_execution(mock_user_context: Any) -> None:
    """Test that LogicNode (mapped to tool) works using 'code' as tool name."""
    services = ServerRegistry()
    controller = WorkflowController(services)

    manifest = {
        "id": "logic-exec",
        "version": "1.0.0",
        "name": "Logic Exec",
        "topology": {
            "nodes": [
                {
                    "id": "LogicA",
                    "type": "logic",
                    "code": "SomeTool",
                    "visual": {"x_y_coordinates": [0, 0], "label": "L", "icon": "code"},
                }
            ],
            "edges": [],
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
    }
    inputs = {"trace_id": "t"}

    events = []
    async for event in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        events.append(event)

    done = [e for e in events if e.event_type == "NODE_DONE"]
    assert len(done) == 1
    assert done[0].node_id == "LogicA"

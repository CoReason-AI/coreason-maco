# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict

import pytest
from pydantic import ValidationError

from coreason_maco.core.manifest_schema import (
    AgentNode,
    HumanNode,
    LogicNode,
    RecipeManifest,
)


def test_valid_manifest_creation() -> None:
    """Test creating a valid RecipeManifest with all node types."""
    manifest_data: Dict[str, Any] = {
        "id": "recipe-123",
        "version": "1.0.0",
        "name": "Test Recipe",
        "description": "A test recipe",
        "inputs": {"user_query": "string"},
        "graph": {
            "nodes": [
                {
                    "id": "node-1",
                    "type": "agent",
                    "agent_name": "summarizer",
                    "visual": {"label": "Summarize", "x_y_coordinates": [10.0, 20.0]},
                },
                {
                    "id": "node-2",
                    "type": "human",
                    "timeout_seconds": 300,
                    "council_config": {
                        "strategy": "majority",
                        "voters": ["gpt-4", "claude-3"],
                    },
                },
                {
                    "id": "node-3",
                    "type": "logic",
                    "code": "return inputs['user_query'].upper()",
                },
            ],
            "edges": [
                {"source_node_id": "node-1", "target_node_id": "node-2"},
                {
                    "source_node_id": "node-2",
                    "target_node_id": "node-3",
                    "condition": "result == 'APPROVED'",
                },
            ],
        },
    }

    manifest = RecipeManifest(**manifest_data)
    assert manifest.id == "recipe-123"
    assert len(manifest.graph.nodes) == 3

    # Verify polymorphism
    agent_node = manifest.graph.nodes[0]
    assert isinstance(agent_node, AgentNode)
    assert agent_node.type == "agent"
    assert agent_node.agent_name == "summarizer"
    assert agent_node.visual is not None
    assert agent_node.visual.x_y_coordinates == [10.0, 20.0]

    human_node = manifest.graph.nodes[1]
    assert isinstance(human_node, HumanNode)
    assert human_node.type == "human"
    assert human_node.timeout_seconds == 300
    assert human_node.council_config is not None
    assert human_node.council_config.strategy == "majority"

    logic_node = manifest.graph.nodes[2]
    assert isinstance(logic_node, LogicNode)
    assert logic_node.type == "logic"
    assert logic_node.code == "return inputs['user_query'].upper()"

    assert len(manifest.graph.edges) == 2
    assert manifest.graph.edges[1].condition == "result == 'APPROVED'"


def test_invalid_node_type() -> None:
    """Test that an invalid node type raises a ValidationError."""
    manifest_data: Dict[str, Any] = {
        "id": "recipe-bad",
        "version": "1.0",
        "name": "Bad Recipe",
        "inputs": {},
        "graph": {
            "nodes": [
                {
                    "id": "node-1",
                    "type": "unknown_type",  # Invalid
                    "agent_name": "test",
                }
            ],
            "edges": [],
        },
    }

    with pytest.raises(ValidationError) as excinfo:
        RecipeManifest(**manifest_data)

    # Check that error relates to discriminator
    # The exact message depends on Pydantic version but should mention the tag
    assert "unknown_type" in str(excinfo.value)


def test_missing_required_field() -> None:
    """Test that missing required fields raise ValidationError."""
    # Missing agent_name for AgentNode
    node_data: Dict[str, Any] = {
        "id": "node-1",
        "type": "agent",
        # missing agent_name
    }

    with pytest.raises(ValidationError) as excinfo:
        AgentNode(**node_data)

    assert "agent_name" in str(excinfo.value)


def test_serialization() -> None:
    """Test JSON serialization of the manifest."""
    manifest_data: Dict[str, Any] = {
        "id": "recipe-json",
        "version": "1.0",
        "name": "JSON Recipe",
        "inputs": {},
        "graph": {
            "nodes": [
                {
                    "id": "node-1",
                    "type": "logic",
                    "code": "pass",
                }
            ],
            "edges": [],
        },
    }

    manifest = RecipeManifest(**manifest_data)
    json_str = manifest.model_dump_json()
    assert '"type":"logic"' in json_str or '"type": "logic"' in json_str
    assert '"code":"pass"' in json_str or '"code": "pass"' in json_str
    assert '"id":"recipe-json"' in json_str or '"id": "recipe-json"' in json_str


def test_extra_fields_forbidden() -> None:
    """Test that extra fields are forbidden."""
    node_data: Dict[str, Any] = {
        "id": "node-1",
        "type": "agent",
        "agent_name": "test",
        "extra_field": "not allowed",
    }

    with pytest.raises(ValidationError) as excinfo:
        AgentNode(**node_data)

    assert "extra_field" in str(excinfo.value)

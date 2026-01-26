# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


class ComplexObject:
    def __init__(self, name: str) -> None:
        self.name = name
        self.stats = {"score": 100}

    def __repr__(self) -> str:
        return f"ComplexObject({self.name})"


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    agent_executor = MagicMock()
    agent_executor.invoke = AsyncMock()

    # Mock tool registry
    async def mock_execute(name: str, args: Dict[str, Any]) -> Any:
        return args

    tool_registry = MagicMock()
    tool_registry.execute = AsyncMock(side_effect=mock_execute)

    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=tool_registry,
    )


@pytest.mark.asyncio  # type: ignore
async def test_workflow_complex_dot_notation(mock_context: ExecutionContext) -> None:
    """
    Integration test verifying that WorkflowRunner correctly resolves
    dot notation for complex, nested objects passing between nodes.
    """
    # 1. Setup Graph
    # Node A: Produces a complex object
    # Node B: Uses dot notation to access A's internals via Tool args
    graph = nx.DiGraph()

    # Mock output for Node A
    complex_data = {
        "user": {"profile": ComplexObject("Alice"), "metadata": {"roles": ["admin", "editor"]}},
        "system": "Linux",
    }

    graph.add_node("NodeA", type="TASK", mock_output=complex_data)

    # Node B accesses:
    # 1. user.profile.name -> "Alice"
    # 2. user.profile.stats.score -> 100
    # 3. system -> "Linux"
    # 4. user.metadata.roles (cannot index list, so gets list) -> ["admin", "editor"]

    tool_args = {
        "name": "{{ NodeA.user.profile.name }}",
        "score": "{{ NodeA.user.profile.stats.score }}",
        "os": "{{ NodeA.system }}",
        "roles": "{{ NodeA.user.metadata.roles }}",
    }

    graph.add_node("NodeB", type="TOOL", config={"tool_name": "verify", "args": tool_args})
    graph.add_edge("NodeA", "NodeB")

    # 2. Run Workflow
    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # 3. Verify Output
    node_b_event = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "NodeB")
    output = node_b_event.payload["output_summary"]

    # Output is string representation of args
    assert "'name': 'Alice'" in output
    assert "'score': 100" in output
    assert "'os': 'Linux'" in output
    # Lists are stringified
    assert "'roles': ['admin', 'editor']" in output or "'roles': ['admin', 'editor']" in output.replace('"', "'")

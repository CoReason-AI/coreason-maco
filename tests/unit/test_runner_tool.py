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

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


class MockToolExecutor:
    """Mock implementation of ToolExecutor for testing."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def execute(self, tool_name: str, args: Dict[str, Any], user_context: Any = None) -> Any:
        self.calls.append({"tool_name": tool_name, "args": args, "user_context": user_context})
        if tool_name == "calculator":
            op = args.get("op")
            a = args.get("a")
            b = args.get("b")
            if op == "add" and isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return a + b
        return "mock_tool_output"


@pytest.mark.asyncio  # type: ignore
async def test_tool_node_execution() -> None:
    """Test that a node with type='TOOL' invokes the tool registry."""
    # Setup
    tool_executor = MockToolExecutor()
    context = ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=tool_executor,
    )

    # Create Graph
    graph = nx.DiGraph()
    # Define a TOOL node
    graph.add_node("tool_node", type="TOOL", config={"tool_name": "calculator", "args": {"op": "add", "a": 5, "b": 3}})

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    # Execute
    async for event in runner.run_workflow(graph, context):
        events.append(event)

    # Verify Tool Execution
    assert len(tool_executor.calls) == 1
    call = tool_executor.calls[0]
    assert call["tool_name"] == "calculator"
    assert call["args"] == {"op": "add", "a": 5, "b": 3}

    # Verify Node Output in Events
    node_done_events = [e for e in events if e.event_type == "NODE_DONE" and e.node_id == "tool_node"]
    assert len(node_done_events) == 1
    payload = node_done_events[0].payload
    assert payload["output_summary"] == "8"


@pytest.mark.asyncio  # type: ignore
async def test_tool_node_missing_name() -> None:
    """Test that a node with type='TOOL' but no tool_name handles gracefully."""
    # Setup
    tool_executor = MockToolExecutor()
    context = ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=tool_executor,
    )

    # Create Graph
    graph = nx.DiGraph()
    # Define a TOOL node with missing config
    graph.add_node("tool_node_bad", type="TOOL", config={})

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    # Execute
    async for event in runner.run_workflow(graph, context):
        events.append(event)

    # Verify Tool Execution - Should be 0 calls
    assert len(tool_executor.calls) == 0

    # Verify Node Output in Events
    node_done_events = [e for e in events if e.event_type == "NODE_DONE" and e.node_id == "tool_node_bad"]
    assert len(node_done_events) == 1
    payload = node_done_events[0].payload
    assert payload["output_summary"] == "Completed"

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
from unittest.mock import MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=MagicMock(),
        agent_executor=MagicMock(),
    )


@pytest.mark.asyncio  # type: ignore
async def test_node_failure_emits_event(mock_context: ExecutionContext) -> None:
    """
    Test that a node failure emits a GraphEvent of type ERROR.
    We simulate failure by using a TOOL node and a mock ToolExecutor that raises.
    """
    graph = nx.DiGraph()
    # Configure node "A" to be a tool that fails
    graph.add_node("A", type="TOOL", config={"tool_name": "failing_tool"})

    # Setup mock tool registry to raise ValueError
    mock_context.tool_registry.execute.side_effect = ValueError("Tool Failed")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    # The runner re-raises exceptions from TaskGroup as ExceptionGroup
    with pytest.raises(ExceptionGroup) as excinfo:
        async for event in runner.run_workflow(graph, mock_context):
            events.append(event)

    # Check that we received the events
    # Expected: NODE_START -> ERROR
    node_starts = [e for e in events if e.event_type == "NODE_START"]
    error_events = [e for e in events if e.event_type == "ERROR"]

    assert len(node_starts) == 1
    assert len(error_events) == 1

    error_event = error_events[0]
    assert error_event.node_id == "A"

    payload = error_event.payload
    assert payload["status"] == "ERROR"
    assert payload["error_message"] == "Tool Failed"
    assert "stack_trace" in payload
    # stack trace should contain the ValueError
    assert "ValueError: Tool Failed" in payload["stack_trace"]

    # verify visual metadata
    assert error_event.visual_metadata["state"] == "ERROR"
    assert error_event.visual_metadata["color"] == "#RED"

    # Verify that the exception caught by pytest matches what we raised
    # ExceptionGroup usually wraps the exception
    assert isinstance(excinfo.value.exceptions[0], ValueError)
    assert str(excinfo.value.exceptions[0]) == "Tool Failed"

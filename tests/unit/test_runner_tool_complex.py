# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import asyncio
import time
from typing import Any, Dict
from unittest.mock import MagicMock

import networkx as nx
import pytest

from coreason_maco.core.interfaces import ToolExecutor
from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext


class MockComplexToolExecutor(ToolExecutor):
    """Mock ToolExecutor that supports delays and errors."""

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "slow_tool":
            delay = args.get("delay", 0.1)
            await asyncio.sleep(delay)
            return "done"

        if tool_name == "error_tool":
            raise ValueError("Tool Execution Failed")

        if tool_name == "json_tool":
            return {"key": "value", "number": 42}

        if tool_name == "decision_tool":
            return args.get("decision", "no")

        return "default"


@pytest.fixture  # type: ignore
def complex_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=MockComplexToolExecutor(),
        agent_executor=MagicMock(),
    )


@pytest.mark.asyncio  # type: ignore
async def test_tool_exception_propagation(complex_context: ExecutionContext) -> None:
    """Test that tool exceptions are propagated by the runner."""
    graph = nx.DiGraph()
    graph.add_node("node_fail", type="TOOL", config={"tool_name": "error_tool"})

    runner = WorkflowRunner()

    # We expect the exception to bubble up from the generator
    with pytest.raises(ExceptionGroup) as excinfo:
        async for _ in runner.run_workflow(graph, complex_context):
            pass

    # Check that at least one exception in the group is ValueError
    assert any(isinstance(e, ValueError) and str(e) == "Tool Execution Failed" for e in excinfo.value.exceptions)


@pytest.mark.asyncio  # type: ignore
async def test_parallel_tool_execution(complex_context: ExecutionContext) -> None:
    """Test that two slow tools run in parallel."""
    graph = nx.DiGraph()
    # A -> (B, C)
    graph.add_edge("Start", "Tool1")
    graph.add_edge("Start", "Tool2")

    # Configure tools to sleep 0.2s each
    delay = 0.2
    graph.nodes["Tool1"]["type"] = "TOOL"
    graph.nodes["Tool1"]["config"] = {"tool_name": "slow_tool", "args": {"delay": delay}}

    graph.nodes["Tool2"]["type"] = "TOOL"
    graph.nodes["Tool2"]["config"] = {"tool_name": "slow_tool", "args": {"delay": delay}}

    start_time = time.time()
    runner = WorkflowRunner()
    async for _ in runner.run_workflow(graph, complex_context):
        pass
    duration = time.time() - start_time

    # If sequential: > 0.4s. If parallel: ~0.2s + overhead.
    # Assert it takes less than sum of delays (allowing for some overhead)
    assert duration < (delay * 2)


@pytest.mark.asyncio  # type: ignore
async def test_tool_output_routing(complex_context: ExecutionContext) -> None:
    """Test that tool output drives conditional branching."""
    graph = nx.DiGraph()
    # Tool -> (PathA, PathB)
    graph.add_edge("Tool", "PathA", condition="go_a")
    graph.add_edge("Tool", "PathB", condition="go_b")

    graph.nodes["Tool"]["type"] = "TOOL"
    graph.nodes["Tool"]["config"] = {"tool_name": "decision_tool", "args": {"decision": "go_a"}}

    runner = WorkflowRunner()
    events = []
    async for event in runner.run_workflow(graph, complex_context):
        events.append(event)

    node_ids = {e.node_id for e in events if e.event_type == "NODE_DONE"}
    assert "Tool" in node_ids
    assert "PathA" in node_ids
    assert "PathB" not in node_ids


@pytest.mark.asyncio  # type: ignore
async def test_complex_tool_output(complex_context: ExecutionContext) -> None:
    """Test handling of dictionary outputs from tools."""
    graph = nx.DiGraph()
    graph.add_node("ToolJSON", type="TOOL", config={"tool_name": "json_tool"})

    runner = WorkflowRunner()
    events = []
    async for event in runner.run_workflow(graph, complex_context):
        events.append(event)

    done_event = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "ToolJSON")
    payload = done_event.payload

    # Check that output_summary contains the string representation of the dict
    assert "{'key': 'value', 'number': 42}" in payload["output_summary"]

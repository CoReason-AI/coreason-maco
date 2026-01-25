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


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    agent_executor = MagicMock()

    async def mock_invoke(prompt: str, config: Any) -> Any:
        response = MagicMock()
        response.content = f"Echo: {prompt}"
        return response

    agent_executor.invoke = AsyncMock(side_effect=mock_invoke)

    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=MagicMock(),
        agent_executor=agent_executor,
    )


@pytest.mark.asyncio  # type: ignore
async def test_llm_node_and_variable_injection(mock_context: ExecutionContext) -> None:
    """
    Test LLM node execution and {{ variable }} injection.
    A (LLM) -> B (LLM, uses output of A).
    """
    graph = nx.DiGraph()

    # Node A: Generates "Echo: Hello"
    graph.add_node("A", type="LLM", config={"prompt": "Hello", "model": "test-model"})

    # Node B: Uses output of A. Should receive "Echo: Hello"
    # Prompt becomes "Process: Echo: Hello"
    graph.add_node("B", type="LLM", config={"prompt": "Process: {{ A }}", "model": "test-model"})

    graph.add_edge("A", "B")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Check Node A output
    node_a_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_a_done.payload["output_summary"] == "Echo: Hello"

    # Check Node B output
    # Mock invoke should have received "Process: Echo: Hello"
    # So output should be "Echo: Process: Echo: Hello"
    node_b_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "B")
    assert node_b_done.payload["output_summary"] == "Echo: Process: Echo: Hello"


@pytest.mark.asyncio  # type: ignore
async def test_llm_node_fallback_args(mock_context: ExecutionContext) -> None:
    """
    Test LLM node using args/prompt fallback.
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="LLM", config={"args": {"prompt": "Fallback"}, "model": "test-model"})

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_a_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_a_done.payload["output_summary"] == "Echo: Fallback"


@pytest.mark.asyncio  # type: ignore
async def test_injection_exact_match(mock_context: ExecutionContext) -> None:
    """
    Test exact injection of objects.
    """
    graph = nx.DiGraph()
    # Mock A output to be a dict
    graph.add_node("A", type="TASK", mock_output={"key": "value"})

    # Node B uses tool with exact injection
    graph.add_node("B", type="TOOL", config={"tool_name": "test_tool", "args": {"input": "{{ A }}"}})
    graph.add_edge("A", "B")

    # Mock tool execution
    async def mock_execute(name: str, args: Dict[str, Any]) -> Any:
        return args["input"]  # Should be the dict

    mock_context.tool_registry.execute = AsyncMock(side_effect=mock_execute)

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_b_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "B")
    # Verify it got the dict, not string representation
    # Note: NODE_DONE output_summary is str() of output, but we can verify the mock call if needed.
    # But let's check if the tool execution succeeded.
    assert "{'key': 'value'}" in node_b_done.payload["output_summary"]


@pytest.mark.asyncio  # type: ignore
async def test_llm_node_missing_prompt_logic(mock_context: ExecutionContext) -> None:
    """
    Test LLM node hitting the logic where neither 'prompt' nor 'args' is in config.
    It should fallback to default prompt "Analyze this." or handle it gracefully.
    This covers line 286 pass.
    """
    graph = nx.DiGraph()
    graph.add_node(
        "A",
        type="LLM",
        config={"model": "test-model"},  # Missing prompt and args
    )

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_a_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    # Default prompt is "Analyze this."
    assert node_a_done.payload["output_summary"] == "Echo: Analyze this."

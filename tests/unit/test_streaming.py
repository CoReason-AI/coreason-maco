# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, AsyncGenerator, List
from unittest.mock import AsyncMock, MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def mock_agent_executor() -> Any:
    agent_executor = MagicMock()

    # Mock invoke
    async def mock_invoke(prompt: str, config: Any) -> Any:
        response = MagicMock()
        response.content = f"Echo: {prompt}"
        return response

    agent_executor.invoke = AsyncMock(side_effect=mock_invoke)

    # Mock stream
    async def mock_stream_gen(prompt: str, config: Any) -> AsyncGenerator[str, None]:
        chunks = ["Echo: ", prompt]
        for chunk in chunks:
            yield chunk

    def mock_stream(prompt: str, config: Any) -> AsyncGenerator[str, None]:
        return mock_stream_gen(prompt, config)

    agent_executor.stream = MagicMock(side_effect=mock_stream)
    return agent_executor


@pytest.fixture  # type: ignore
def mock_streaming_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=MagicMock(),
    )


@pytest.mark.asyncio  # type: ignore
async def test_llm_node_streaming(mock_streaming_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """
    Test that LLM node uses streaming when available.
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="LLM", config={"prompt": "Hello", "model": "test-model"})

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_streaming_context):
        events.append(event)

    # Check for NODE_STREAM events
    stream_events = [e for e in events if e.event_type == "NODE_STREAM" and e.node_id == "A"]

    # Assert we got stream events
    assert len(stream_events) > 0, "No NODE_STREAM events emitted"
    assert stream_events[0].payload["chunk"] == "Echo: "
    assert stream_events[1].payload["chunk"] == "Hello"

    # Check that stream method was called
    mock_agent_executor.stream.assert_called_once()

    # Check that invoke was NOT called
    mock_agent_executor.invoke.assert_not_called()

    # Check NODE_DONE has full output
    node_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_done.payload["output_summary"] == "Echo: Hello"


@pytest.mark.asyncio  # type: ignore
async def test_llm_node_stream_error_fallback(
    mock_streaming_context: ExecutionContext, mock_agent_executor: Any
) -> None:
    """
    Test fallback to invoke when stream raises error.
    """
    # Mock stream to raise NotImplementedError
    mock_agent_executor.stream.side_effect = NotImplementedError("Not implemented")

    # Mock invoke to work
    async def mock_invoke(prompt: str, config: Any) -> Any:
        response = MagicMock()
        response.content = f"Fallback: {prompt}"
        return response

    mock_agent_executor.invoke = AsyncMock(side_effect=mock_invoke)

    graph = nx.DiGraph()
    graph.add_node("A", type="LLM", config={"prompt": "Hello", "model": "test-model"})

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_streaming_context):
        events.append(event)

    node_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_done.payload["output_summary"] == "Fallback: Hello"

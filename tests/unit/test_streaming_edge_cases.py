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

    # Default invoke behavior
    async def mock_invoke(prompt: str, config: Any) -> Any:
        response = MagicMock()
        response.content = f"Invoke: {prompt}"
        return response

    agent_executor.invoke = AsyncMock(side_effect=mock_invoke)
    return agent_executor


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=MagicMock(),
    )


@pytest.mark.asyncio  # type: ignore
async def test_stream_returns_non_generator(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """
    Test fallback when stream() returns something that is not an async generator
    (e.g., a string, a list, or None).
    """
    # Mock stream to return a string instead of a generator
    mock_agent_executor.stream = MagicMock(return_value="Not a generator")

    graph = nx.DiGraph()
    graph.add_node("A", type="LLM", config={"prompt": "Hello"})

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Should fall back to invoke
    node_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_done.payload["output_summary"] == "Invoke: Hello"
    mock_agent_executor.invoke.assert_called_once()


@pytest.mark.asyncio  # type: ignore
async def test_stream_setup_type_error(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """
    Test fallback when stream() raises TypeError during call (e.g. invalid args).
    """
    # Mock stream to raise TypeError
    mock_agent_executor.stream = MagicMock(side_effect=TypeError("Invalid args"))

    graph = nx.DiGraph()
    graph.add_node("A", type="LLM", config={"prompt": "Hello"})

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Should fall back to invoke
    node_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_done.payload["output_summary"] == "Invoke: Hello"
    mock_agent_executor.invoke.assert_called_once()


@pytest.mark.asyncio  # type: ignore
async def test_stream_mid_execution_error(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """
    Test fallback when the generator raises a caught exception (AttributeError)
    during iteration.
    """

    async def broken_gen(prompt: str, config: Any) -> AsyncGenerator[str, None]:
        yield "Chunk1"
        raise AttributeError("Something missing")

    mock_agent_executor.stream = MagicMock(side_effect=broken_gen)

    graph = nx.DiGraph()
    graph.add_node("A", type="LLM", config={"prompt": "Hello"})

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Should receive Chunk1 event
    stream_events = [e for e in events if e.event_type == "NODE_STREAM" and e.node_id == "A"]
    assert len(stream_events) >= 1
    assert stream_events[0].payload["chunk"] == "Chunk1"

    # Should fall back to invoke and succeed
    node_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_done.payload["output_summary"] == "Invoke: Hello"
    mock_agent_executor.invoke.assert_called_once()


@pytest.mark.asyncio  # type: ignore
async def test_empty_stream(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """
    Test that an empty stream (yields nothing) returns empty string and does NOT
    fallback to invoke (because it was a valid generator).
    """

    async def empty_gen(prompt: str, config: Any) -> AsyncGenerator[str, None]:
        if False:
            yield "Nothing"

    mock_agent_executor.stream = MagicMock(side_effect=empty_gen)

    graph = nx.DiGraph()
    graph.add_node("A", type="LLM", config={"prompt": "Hello"})

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Output should be empty string
    node_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert node_done.payload["output_summary"] == ""

    # Invoke should NOT be called because stream succeeded (produced valid empty result)
    mock_agent_executor.invoke.assert_not_called()


@pytest.mark.asyncio  # type: ignore
async def test_parallel_streaming_nodes(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """
    Test multiple nodes streaming in parallel.
    """

    # Create a dynamic mock that returns different streams based on prompt
    async def dynamic_stream(prompt: str, config: Any) -> AsyncGenerator[str, None]:
        chunks = [f"{prompt}-1", f"{prompt}-2"]
        for c in chunks:
            await asyncio.sleep(0.01)  # Simulate network delay to encourage interleaving
            yield c

    mock_agent_executor.stream = MagicMock(side_effect=dynamic_stream)

    graph = nx.DiGraph()
    graph.add_node("START", type="START")
    graph.add_node("A", type="LLM", config={"prompt": "A"})
    graph.add_node("B", type="LLM", config={"prompt": "B"})
    graph.add_node("C", type="LLM", config={"prompt": "C"})

    graph.add_edge("START", "A")
    graph.add_edge("START", "B")
    graph.add_edge("START", "C")

    # Run them in parallel
    runner = WorkflowRunner(max_parallel_agents=3, agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Verify outputs
    results = {}
    for e in events:
        if e.event_type == "NODE_DONE":
            results[e.node_id] = e.payload["output_summary"]

    assert results["A"] == "A-1A-2"
    assert results["B"] == "B-1B-2"
    assert results["C"] == "C-1C-2"

    # Verify we got stream events for all
    stream_nodes = {e.node_id for e in events if e.event_type == "NODE_STREAM"}
    assert stream_nodes == {"A", "B", "C"}

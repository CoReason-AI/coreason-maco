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
from typing import Any, Dict, List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.engine.topology import CyclicDependencyError
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(user_id="test_user", trace_id="test_trace", secrets_map={}, tool_registry={})


@pytest.mark.asyncio  # type: ignore
async def test_sequential_execution(mock_context: ExecutionContext) -> None:
    """Test a simple linear graph A -> B -> C."""
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    assert len(events) == 6
    node_ids = [e.node_id for e in events]
    assert node_ids == ["A", "A", "B", "B", "C", "C"]


@pytest.mark.asyncio  # type: ignore
async def test_parallel_execution(mock_context: ExecutionContext) -> None:
    """Test a parallel graph A -> (B, C) -> D."""
    graph = nx.DiGraph()
    graph.add_edges_from([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    assert len(events) == 8


@pytest.mark.asyncio  # type: ignore
async def test_execution_error(mock_context: ExecutionContext) -> None:
    """Test that an exception in a node is propagated."""
    graph = nx.DiGraph()
    graph.add_node("A")

    runner = WorkflowRunner()

    async def failing_execute(
        node_id: str,
        run_id: str,
        queue: asyncio.Queue[GraphEvent | None],
        context: ExecutionContext,
        recipe: nx.DiGraph,
        node_outputs: Dict[str, Any],
    ) -> None:
        raise ValueError("Simulated Failure")

    runner._execute_node = failing_execute  # type: ignore

    with pytest.raises(ExceptionGroup) as excinfo:
        async for _ in runner.run_workflow(graph, mock_context):
            pass

    assert isinstance(excinfo.value.exceptions[0], ValueError)


@pytest.mark.asyncio  # type: ignore
async def test_runner_empty_graph(mock_context: ExecutionContext) -> None:
    """Test handling of an empty graph."""
    graph = nx.DiGraph()
    runner = WorkflowRunner()
    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)
    assert len(events) == 0


@pytest.mark.asyncio  # type: ignore
async def test_runner_validation_errors(mock_context: ExecutionContext) -> None:
    """Verify that topology validation errors are propagated."""
    runner = WorkflowRunner()

    g_cyclic = nx.DiGraph()
    g_cyclic.add_edges_from([("A", "B"), ("B", "A")])
    with pytest.raises(CyclicDependencyError):
        async for _ in runner.run_workflow(g_cyclic, mock_context):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_runner_cancellation(mock_context: ExecutionContext) -> None:
    """Verify clean cancellation when consumer stops early (GeneratorExit)."""
    graph = nx.DiGraph()
    graph.add_edges_from([("A", "B")])

    runner = WorkflowRunner()

    # We break after first event.
    # This triggers GeneratorExit in the generator.
    # The runner should cancel the producer.
    async for _ in runner.run_workflow(graph, mock_context):
        break


@pytest.mark.asyncio  # type: ignore
async def test_runner_consumer_throw(mock_context: ExecutionContext) -> None:
    """
    Verify clean cleanup when consumer throws an exception into generator.
    This triggers the `except Exception` block in runner.py.
    """
    graph = nx.DiGraph()
    graph.add_node("A")
    runner = WorkflowRunner()

    gen = runner.run_workflow(graph, mock_context)

    # Get first item
    await anext(gen)

    # Throw exception into generator
    with pytest.raises(ValueError, match="Injected Error"):
        await gen.athrow(ValueError("Injected Error"))

    # Verify generator is closed
    with pytest.raises(StopAsyncIteration):
        await anext(gen)


@pytest.mark.asyncio  # type: ignore
async def test_runner_fan_out_fan_in(mock_context: ExecutionContext) -> None:
    """Stress test: Root -> 50 Nodes -> Sink"""
    graph = nx.DiGraph()
    root = "Root"
    sink = "Sink"
    width = 50
    graph.add_node(root)
    graph.add_node(sink)

    for i in range(width):
        mid = f"M{i}"
        graph.add_edge(root, mid)
        graph.add_edge(mid, sink)

    runner = WorkflowRunner()
    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # 52 nodes * 2 events = 104
    assert len(events) == 104

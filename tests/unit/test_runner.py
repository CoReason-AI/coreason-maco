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
from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(user_id="test_user", trace_id="test_trace", secrets_map={}, tool_registry={})


@pytest.mark.asyncio  # type: ignore
async def test_sequential_execution(mock_context: ExecutionContext) -> None:
    """
    Test a simple linear graph A -> B -> C.
    """
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # We expect 2 events per node (START, DONE) * 3 nodes = 6 events
    assert len(events) == 6

    # Check order: A start -> A done -> B start -> B done -> C start -> C done
    event_types = [e.event_type for e in events]
    node_ids = [e.node_id for e in events]

    assert node_ids == ["A", "A", "B", "B", "C", "C"]
    assert event_types == [
        "NODE_START",
        "NODE_DONE",
        "NODE_START",
        "NODE_DONE",
        "NODE_START",
        "NODE_DONE",
    ]


@pytest.mark.asyncio  # type: ignore
async def test_parallel_execution(mock_context: ExecutionContext) -> None:
    """
    Test a parallel graph A -> (B, C) -> D.
    """
    graph = nx.DiGraph()
    graph.add_edges_from([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    assert len(events) == 8  # 4 nodes * 2 events

    # Analyze B and C. They are in the second layer.
    # We expect A done before B/C start.
    # We expect B/C done before D start.

    # Get indices
    a_done_idx = next(i for i, e in enumerate(events) if e.node_id == "A" and e.event_type == "NODE_DONE")
    b_start_idx = next(i for i, e in enumerate(events) if e.node_id == "B" and e.event_type == "NODE_START")
    c_start_idx = next(i for i, e in enumerate(events) if e.node_id == "C" and e.event_type == "NODE_START")
    d_start_idx = next(i for i, e in enumerate(events) if e.node_id == "D" and e.event_type == "NODE_START")

    assert a_done_idx < b_start_idx
    assert a_done_idx < c_start_idx

    b_done_idx = next(i for i, e in enumerate(events) if e.node_id == "B" and e.event_type == "NODE_DONE")
    c_done_idx = next(i for i, e in enumerate(events) if e.node_id == "C" and e.event_type == "NODE_DONE")

    assert b_done_idx < d_start_idx
    assert c_done_idx < d_start_idx


@pytest.mark.asyncio  # type: ignore
async def test_execution_error(mock_context: ExecutionContext) -> None:
    """
    Test that an exception in a node is propagated.
    """
    graph = nx.DiGraph()
    graph.add_node("A")

    runner = WorkflowRunner()

    # Mock _execute_node to raise an exception
    async def failing_execute(
        node_id: str,
        run_id: str,
        queue: asyncio.Queue[GraphEvent | None],
        context: ExecutionContext,
    ) -> None:
        raise ValueError("Simulated Failure")

    # We need to bind the method or just replace it on the instance
    # Since _execute_node is called as self._execute_node, replacing it on instance works
    runner._execute_node = failing_execute  # type: ignore

    # TaskGroup raises ExceptionGroup wrapping the actual exception
    with pytest.raises(ExceptionGroup) as excinfo:
        async for _ in runner.run_workflow(graph, mock_context):
            pass

    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], ValueError)
    assert str(excinfo.value.exceptions[0]) == "Simulated Failure"

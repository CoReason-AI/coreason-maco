from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(user_id="test_user", trace_id="test_trace", secrets_map={}, tool_registry={})


@pytest.mark.asyncio  # type: ignore
async def test_conditional_branching_path_a(mock_context: ExecutionContext) -> None:
    """
    Test branching: A -> B (cond=path_a), A -> C (cond=path_b).
    A returns "path_a".
    Expected: A runs, B runs, C skipped.
    """
    G = nx.DiGraph()
    # A returns "path_a"
    G.add_node("A", mock_output="path_a")
    G.add_node("B")
    G.add_node("C")

    G.add_edge("A", "B", condition="path_a")
    G.add_edge("A", "C", condition="path_b")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    node_ids = set(e.node_id for e in events)
    assert "A" in node_ids
    assert "B" in node_ids
    assert "C" not in node_ids


@pytest.mark.asyncio  # type: ignore
async def test_conditional_branching_path_b(mock_context: ExecutionContext) -> None:
    """
    Test branching: A -> B (cond=path_a), A -> C (cond=path_b).
    A returns "path_b".
    Expected: A runs, C runs, B skipped.
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="path_b")
    G.add_node("B")
    G.add_node("C")

    G.add_edge("A", "B", condition="path_a")
    G.add_edge("A", "C", condition="path_b")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    node_ids = set(e.node_id for e in events)
    assert "A" in node_ids
    assert "C" in node_ids
    assert "B" not in node_ids


@pytest.mark.asyncio  # type: ignore
async def test_conditional_default_path(mock_context: ExecutionContext) -> None:
    """
    Test branching with default path:
    A -> B (cond=path_a)
    A -> C (no condition)
    A returns "path_a".
    Expected: A runs, B runs (condition met), C runs (default).
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="path_a")
    G.add_node("B")
    G.add_node("C")

    G.add_edge("A", "B", condition="path_a")
    G.add_edge("A", "C")  # Default

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    node_ids = set(e.node_id for e in events)
    assert "A" in node_ids
    assert "B" in node_ids
    assert "C" in node_ids


@pytest.mark.asyncio  # type: ignore
async def test_chained_skipping(mock_context: ExecutionContext) -> None:
    """
    Test propagated skipping:
    A -> B (cond=no) -> D
    A -> C (cond=yes) -> E
    A returns "yes".
    Expected: A, C, E run. B, D skipped.
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="yes")
    G.add_node("B")
    G.add_node("C", mock_output="continue")
    G.add_node("D")
    G.add_node("E")

    G.add_edge("A", "B", condition="no")
    G.add_edge("B", "D")
    G.add_edge("A", "C", condition="yes")
    G.add_edge("C", "E")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    node_ids = set(e.node_id for e in events)
    assert "A" in node_ids
    assert "C" in node_ids
    assert "E" in node_ids
    assert "B" not in node_ids
    assert "D" not in node_ids


@pytest.mark.asyncio  # type: ignore
async def test_full_layer_skip(mock_context: ExecutionContext) -> None:
    """
    Test skipping an entire layer.
    A -> B (cond=yes) -> C.
    A returns "no".
    Expected: A runs. B skipped. C skipped.
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="no")
    G.add_node("B")
    G.add_node("C")

    G.add_edge("A", "B", condition="yes")
    G.add_edge("B", "C")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    node_ids = set(e.node_id for e in events)
    assert "A" in node_ids
    assert "B" not in node_ids
    assert "C" not in node_ids

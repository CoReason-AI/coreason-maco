from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import EdgeTraversed, GraphEvent
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


@pytest.mark.asyncio  # type: ignore
async def test_conditional_edge_events(mock_context: ExecutionContext) -> None:
    """
    Test that only the activated edge emits an EDGE_ACTIVE event.
    Graph: A -> B (cond="yes"), A -> C (cond="no")
    Output of A: "yes"
    Expected: Edge A->B traversed. Edge A->C NOT traversed.
    """
    graph = nx.DiGraph()
    graph.add_node("A", mock_output="yes")
    graph.add_node("B")
    graph.add_node("C")

    graph.add_edge("A", "B", condition="yes")
    graph.add_edge("A", "C", condition="no")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    edge_events = [e for e in events if e.event_type == "EDGE_ACTIVE"]

    # Only A->B should be present
    assert len(edge_events) == 1

    payload = edge_events[0].payload
    edge_data = EdgeTraversed(**payload)

    assert edge_data.source == "A"
    assert edge_data.target == "B"


@pytest.mark.asyncio  # type: ignore
async def test_broadcast_edge_events(mock_context: ExecutionContext) -> None:
    """
    Test that multiple activated edges emit multiple events.
    Graph: A -> B (no condition), A -> C (cond="yes")
    Output of A: "yes"
    Expected: Edge A->B traversed (default). Edge A->C traversed (matched).
    """
    graph = nx.DiGraph()
    graph.add_node("A", mock_output="yes")
    graph.add_node("B")
    graph.add_node("C")

    graph.add_edge("A", "B")  # Default
    graph.add_edge("A", "C", condition="yes")  # Matched

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    edge_events = [e for e in events if e.event_type == "EDGE_ACTIVE"]

    assert len(edge_events) == 2

    targets = sorted([EdgeTraversed(**e.payload).target for e in edge_events])
    assert targets == ["B", "C"]


@pytest.mark.asyncio  # type: ignore
async def test_no_edge_activation(mock_context: ExecutionContext) -> None:
    """
    Test that no edge events are emitted if condition fails.
    Graph: A -> B (cond="yes")
    Output of A: "no"
    Expected: Node A runs. No edge events. Node B skipped.
    """
    graph = nx.DiGraph()
    graph.add_node("A", mock_output="no")
    graph.add_node("B")

    graph.add_edge("A", "B", condition="yes")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    edge_events = [e for e in events if e.event_type == "EDGE_ACTIVE"]

    assert len(edge_events) == 0

    # Verify B did not run
    node_starts = [e for e in events if e.event_type == "NODE_START"]
    started_ids = [e.node_id for e in node_starts]
    assert "A" in started_ids
    assert "B" not in started_ids

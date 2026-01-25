from typing import List
from unittest.mock import MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import EdgeTraversed, ExecutionContext, GraphEvent


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
        agent_executor=MagicMock(),
    )


@pytest.mark.asyncio  # type: ignore
async def test_diamond_pattern_traversal(mock_context: ExecutionContext) -> None:
    """
    Test "Diamond" pattern: A -> B (cond=left), A -> C (cond=right), B -> D, C -> D.
    Condition: "left".
    Expected Path: A -> B -> D.
    Expected Edges: A->B, B->D.
    Edges A->C and C->D should NOT be traversed.
    """
    graph = nx.DiGraph()
    graph.add_node("A", mock_output="left")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")

    graph.add_edge("A", "B", condition="left")
    graph.add_edge("A", "C", condition="right")
    graph.add_edge("B", "D")
    graph.add_edge("C", "D")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    edge_events = [e for e in events if e.event_type == "EDGE_ACTIVE"]
    edges = [(EdgeTraversed(**e.payload).source, EdgeTraversed(**e.payload).target) for e in edge_events]

    assert len(edges) == 2
    assert ("A", "B") in edges
    assert ("B", "D") in edges
    assert ("A", "C") not in edges
    assert ("C", "D") not in edges


@pytest.mark.asyncio  # type: ignore
async def test_complex_output_condition(mock_context: ExecutionContext) -> None:
    """
    Test behavior when node output is a dictionary.
    Runner casts output to str() before comparing.
    Output: {"status": "ok"}
    Condition: "{'status': 'ok'}"
    """
    graph = nx.DiGraph()
    # Note: Python's str(dict) representation uses single quotes and is sensitive to spacing
    output_dict = {"status": "ok"}
    graph.add_node("A", mock_output=output_dict)
    graph.add_node("B")

    # Exact string representation of the dict
    graph.add_edge("A", "B", condition=str(output_dict))

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    edge_events = [e for e in events if e.event_type == "EDGE_ACTIVE"]

    assert len(edge_events) == 1
    edge_data = EdgeTraversed(**edge_events[0].payload)
    assert edge_data.source == "A"
    assert edge_data.target == "B"


@pytest.mark.asyncio  # type: ignore
async def test_fan_out_edge_events(mock_context: ExecutionContext) -> None:
    """
    Test high-volume edge emission.
    A -> 50 nodes.
    Expected: 50 EDGE_ACTIVE events.
    """
    graph = nx.DiGraph()
    graph.add_node("A")
    width = 50
    for i in range(width):
        graph.add_node(f"Leaf_{i}")
        graph.add_edge("A", f"Leaf_{i}")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    edge_events = [e for e in events if e.event_type == "EDGE_ACTIVE"]
    assert len(edge_events) == width

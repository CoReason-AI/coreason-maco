from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


def get_node_status(events: List[GraphEvent]) -> dict[str, str]:
    """Helper to extract the final status of nodes from events."""
    status = {}
    for event in events:
        if event.event_type == "NODE_DONE":
            status[event.node_id] = "DONE"
        elif event.event_type == "NODE_SKIPPED":
            status[event.node_id] = "SKIPPED"
    return status


@pytest.mark.asyncio  # type: ignore
async def test_complex_dag_routing(mock_context: ExecutionContext) -> None:
    """
    Constructs a complex DAG with multiple conditional splits and convergence points.

    Structure:
    Root -> A (Output: "path1")

    A -> B1 (Cond: "path1")
    A -> B2 (Cond: "path2")
    A -> B3 (Cond: "path1")

    B1 -> C1
    B2 -> C2
    B3 -> C3

    C1 -> D (Convergence)
    C2 -> D (Convergence)
    C3 -> D (Convergence)

    Expected:
    - A runs (Output: path1)
    - B1 runs.
    - B2 SKIPS (condition path2 failed).
    - B3 runs.

    - C1 runs (parent B1 ran).
    - C2 SKIPS (parent B2 skipped).
    - C3 runs (parent B3 ran).

    - D runs (parents C1, C3 ran. C2 skipped).
    """
    G = nx.DiGraph()
    G.add_node("Root")
    G.add_node("A", mock_output="path1")

    G.add_node("B1")
    G.add_node("B2")
    G.add_node("B3")

    G.add_node("C1")
    G.add_node("C2")
    G.add_node("C3")

    G.add_node("D")

    # Root -> A
    G.add_edge("Root", "A")

    # A splits
    G.add_edge("A", "B1", condition="path1")
    G.add_edge("A", "B2", condition="path2")
    G.add_edge("A", "B3", condition="path1")

    # B layer to C layer
    G.add_edge("B1", "C1")
    G.add_edge("B2", "C2")
    G.add_edge("B3", "C3")

    # C layer converges to D
    G.add_edge("C1", "D")
    G.add_edge("C2", "D")
    G.add_edge("C3", "D")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)

    # Verify Root and A
    assert status.get("Root") == "DONE"
    assert status.get("A") == "DONE"

    # Verify B Layer
    assert status.get("B1") == "DONE"
    assert status.get("B2") == "SKIPPED"
    assert status.get("B3") == "DONE"

    # Verify C Layer
    assert status.get("C1") == "DONE"
    assert status.get("C2") == "SKIPPED"
    assert status.get("C3") == "DONE"

    # Verify D
    assert status.get("D") == "DONE"


@pytest.mark.asyncio  # type: ignore
async def test_complex_dag_routing_all_skip_convergence(mock_context: ExecutionContext) -> None:
    """
    Same structure as above, but A outputs "path_none" so ALL branches skip.
    D should skip.
    """
    G = nx.DiGraph()
    G.add_node("Root")
    G.add_node("A", mock_output="path_none")

    G.add_node("B1")
    G.add_node("B2")
    G.add_node("B3")

    G.add_node("C1")
    G.add_node("C2")
    G.add_node("C3")

    G.add_node("D")

    # Root -> A
    G.add_edge("Root", "A")

    # A splits
    G.add_edge("A", "B1", condition="path1")
    G.add_edge("A", "B2", condition="path2")
    G.add_edge("A", "B3", condition="path1")

    # B layer to C layer
    G.add_edge("B1", "C1")
    G.add_edge("B2", "C2")
    G.add_edge("B3", "C3")

    # C layer converges to D
    G.add_edge("C1", "D")
    G.add_edge("C2", "D")
    G.add_edge("C3", "D")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)

    assert status.get("Root") == "DONE"
    assert status.get("A") == "DONE"

    assert status.get("B1") == "SKIPPED"
    assert status.get("B2") == "SKIPPED"
    assert status.get("B3") == "SKIPPED"

    assert status.get("C1") == "SKIPPED"
    assert status.get("C2") == "SKIPPED"
    assert status.get("C3") == "SKIPPED"

    assert status.get("D") == "SKIPPED"


@pytest.mark.asyncio  # type: ignore
async def test_redundant_parallel_execution(mock_context: ExecutionContext) -> None:
    """
    Redundant test: 50 parallel nodes from a single root.
    All should run.
    Verifies scalability/stability of the loop with many nodes.
    """
    G = nx.DiGraph()
    G.add_node("Root")

    num_nodes = 50
    for i in range(num_nodes):
        G.add_node(f"P{i}")
        G.add_edge("Root", f"P{i}")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)

    assert status.get("Root") == "DONE"
    for i in range(num_nodes):
        assert status.get(f"P{i}") == "DONE"

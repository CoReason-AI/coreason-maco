from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


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
async def test_diamond_partial_skip(mock_context: ExecutionContext) -> None:
    """
    Test Diamond Pattern where one path is skipped but the other is active.
    A -> B (cond=left) -> D
    A -> C (cond=right) -> D

    A returns "right".
    Expected:
    - A runs.
    - B skipped (condition failed).
    - C runs (condition met).
    - D runs (reachable via C).
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="right")
    G.add_node("B")
    G.add_node("C")
    G.add_node("D")

    G.add_edge("A", "B", condition="left")
    G.add_edge("B", "D")

    G.add_edge("A", "C", condition="right")
    G.add_edge("C", "D")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)

    assert status.get("A") == "DONE"
    assert status.get("B") == "SKIPPED"
    assert status.get("C") == "DONE"
    assert status.get("D") == "DONE"


@pytest.mark.asyncio  # type: ignore
async def test_diamond_full_skip(mock_context: ExecutionContext) -> None:
    """
    Test Diamond Pattern where BOTH paths are skipped.
    A -> B (cond=left) -> D
    A -> C (cond=right) -> D

    A returns "neither".
    Expected:
    - A runs.
    - B skipped.
    - C skipped.
    - D skipped (no active parents).
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="neither")
    G.add_node("B")
    G.add_node("C")
    G.add_node("D")

    G.add_edge("A", "B", condition="left")
    G.add_edge("B", "D")

    G.add_edge("A", "C", condition="right")
    G.add_edge("C", "D")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)

    assert status.get("A") == "DONE"
    assert status.get("B") == "SKIPPED"
    assert status.get("C") == "SKIPPED"
    assert status.get("D") == "SKIPPED"


@pytest.mark.asyncio  # type: ignore
async def test_deep_chain_skip(mock_context: ExecutionContext) -> None:
    """
    Test propagation of skipping down a long chain.
    A -> B (cond=go) -> C -> D -> E

    A returns "stop".
    Expected:
    - A runs.
    - B, C, D, E all skipped.
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="stop")
    G.add_node("B")
    G.add_node("C")
    G.add_node("D")
    G.add_node("E")

    G.add_edge("A", "B", condition="go")
    G.add_edge("B", "C")
    G.add_edge("C", "D")
    G.add_edge("D", "E")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)

    assert status.get("A") == "DONE"
    assert status.get("B") == "SKIPPED"
    assert status.get("C") == "SKIPPED"
    assert status.get("D") == "SKIPPED"
    assert status.get("E") == "SKIPPED"


@pytest.mark.asyncio  # type: ignore
async def test_multi_layer_convergence(mock_context: ExecutionContext) -> None:
    """
    Test a more complex convergence where parents are in different layers.
    A -> B
    A -> C
    B -> D
    C -> E

    D -> F
    E -> F

    A returns "run_all".
    But B output makes D skip.
    C output makes E run.

    So F has one skipped parent (D) and one running parent (E).
    F should RUN.
    """
    G = nx.DiGraph()
    G.add_node("A", mock_output="run_all")
    G.add_node("B", mock_output="skip_d")
    G.add_node("C", mock_output="run_e")
    G.add_node("D")
    G.add_node("E")
    G.add_node("F")

    G.add_edge("A", "B")
    G.add_edge("A", "C")

    G.add_edge("B", "D", condition="run_d")  # B returns skip_d, so this fails -> D skips
    G.add_edge("C", "E", condition="run_e")  # C returns run_e, so this passes -> E runs

    G.add_edge("D", "F")
    G.add_edge("E", "F")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)

    assert status.get("A") == "DONE"
    assert status.get("B") == "DONE"
    assert status.get("C") == "DONE"

    assert status.get("D") == "SKIPPED"
    assert status.get("E") == "DONE"

    # F should run because E ran and activated the edge to F (default edge)
    assert status.get("F") == "DONE"


@pytest.mark.asyncio  # type: ignore
async def test_convergence_prune_reachable(mock_context: ExecutionContext) -> None:
    """
    Test hitting lines 227-228 in runner.py (is_reachable = True break).
    Structure:
    A -> B
    A -> C
    B -> D (condition="pass") -> B returns "pass".
    C -> D (condition="fail") -> C returns "fail".
    """
    G = nx.DiGraph()
    G.add_node("A")
    G.add_node("B", mock_output="pass")
    G.add_node("C", mock_output="fail")
    G.add_node("D")

    G.add_edge("A", "B")
    G.add_edge("A", "C")

    G.add_edge("B", "D", condition="pass")
    G.add_edge("C", "D", condition="pass")  # Fails because C returns "fail"

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)
    assert status["D"] == "DONE"


@pytest.mark.asyncio  # type: ignore
async def test_overlapping_skip(mock_context: ExecutionContext) -> None:
    """
    Test hitting line 218 (already skipped) via overlapping recursive calls.
    Structure:
    Root -> B (fail).
    B -> D, B -> E.
    D -> G, D -> F.
    E -> G, E -> F.
    G -> F.

    When B skips D and E:
    D skips G and F.
    E skips G (which then skips F).
    E then tries to skip F directly (which was already skipped by G).
    This should hit line 218.
    """
    G = nx.DiGraph()
    G.add_node("Root", mock_output="fail")
    G.add_node("B")
    G.add_node("D")
    G.add_node("E")
    G.add_node("G")
    G.add_node("F")

    G.add_edge("Root", "B", condition="pass")

    G.add_edge("B", "D")
    G.add_edge("B", "E")

    G.add_edge("D", "G")
    G.add_edge("D", "F")

    G.add_edge("E", "G")
    G.add_edge("E", "F")

    G.add_edge("G", "F")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    status = get_node_status(events)
    assert status["B"] == "SKIPPED"
    assert status["F"] == "SKIPPED"

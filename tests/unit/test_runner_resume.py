# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


@pytest.fixture  # type: ignore
def runner() -> WorkflowRunner:
    return WorkflowRunner()


@pytest.mark.asyncio  # type: ignore
async def test_simple_resume(runner: WorkflowRunner, context: ExecutionContext) -> None:
    """
    Test simple resume: A -> B.
    A is restored. B runs.
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="TASK", mock_output="output_a")
    graph.add_node("B", type="TASK", mock_output="output_b")
    graph.add_edge("A", "B")

    snapshot = {"A": "output_a"}

    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, context, resume_snapshot=snapshot):
        events.append(event)

    # Check that A was restored
    restored_events = [e for e in events if e.event_type == "NODE_RESTORED"]
    assert len(restored_events) == 1
    assert restored_events[0].node_id == "A"
    assert restored_events[0].payload["output_summary"] == "output_a"

    # Check that B ran
    b_events = [e for e in events if e.node_id == "B"]
    assert any(e.event_type == "NODE_START" for e in b_events)
    assert any(e.event_type == "NODE_DONE" for e in b_events)


@pytest.mark.asyncio  # type: ignore
async def test_branching_resume(runner: WorkflowRunner, context: ExecutionContext) -> None:
    """
    Test branching resume: A -> (B, C) with condition.
    A is restored with output "go_b".
    B runs. C is skipped.
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="DECISION", mock_output="go_b")
    graph.add_node("B", type="TASK", mock_output="done_b")
    graph.add_node("C", type="TASK", mock_output="done_c")
    graph.add_edge("A", "B", condition="go_b")
    graph.add_edge("A", "C", condition="go_c")

    # Resume A with "go_b"
    snapshot = {"A": "go_b"}

    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, context, resume_snapshot=snapshot):
        events.append(event)

    # A restored
    assert any(e.event_type == "NODE_RESTORED" and e.node_id == "A" for e in events)

    # B ran
    assert any(e.node_id == "B" and e.event_type == "NODE_DONE" for e in events)

    # C skipped
    # With explicit skipping, C will be present but as NODE_SKIPPED
    skipped_nodes = {e.node_id for e in events if e.event_type == "NODE_SKIPPED"}
    done_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}

    assert "C" in skipped_nodes
    assert "C" not in done_nodes


@pytest.mark.asyncio  # type: ignore
async def test_chain_resume(runner: WorkflowRunner, context: ExecutionContext) -> None:
    """
    Test chain resume: A -> B -> C.
    A and B restored. C runs.
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="TASK", mock_output="out_a")
    graph.add_node("B", type="TASK", mock_output="out_b")
    graph.add_node("C", type="TASK", mock_output="out_c")
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")

    snapshot = {"A": "out_a", "B": "out_b"}

    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, context, resume_snapshot=snapshot):
        events.append(event)

    # A and B restored
    restored_ids = [e.node_id for e in events if e.event_type == "NODE_RESTORED"]
    assert "A" in restored_ids
    assert "B" in restored_ids

    # C ran
    assert any(e.node_id == "C" and e.event_type == "NODE_DONE" for e in events)

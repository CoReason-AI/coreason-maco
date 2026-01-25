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
async def test_edge_traversal_events(mock_context: ExecutionContext) -> None:
    """
    Test that EDGE_TRAVERSAL events are emitted when moving between nodes.
    Graph: A -> B
    Expected Events:
    1. NODE_START (A)
    2. NODE_DONE (A)
    3. EDGE_TRAVERSAL (A -> B)
    4. NODE_START (B)
    5. NODE_DONE (B)
    """
    graph = nx.DiGraph()
    graph.add_edge("A", "B")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Filter for edge events
    edge_events = [e for e in events if e.event_type == "EDGE_TRAVERSAL"]

    assert len(edge_events) == 1

    event = edge_events[0]
    assert event.event_type == "EDGE_TRAVERSAL"

    # Verify payload
    payload = event.payload
    # Since payload is a dict in GraphEvent, we can validate it against the model or check keys directly
    # Ideally we should be able to parse it back to EdgeTraversed
    edge_data = EdgeTraversed(**payload)
    assert edge_data.source == "A"
    assert edge_data.target == "B"

    # verify visual metadata
    assert event.visual_metadata.get("flow_speed") == "FAST"

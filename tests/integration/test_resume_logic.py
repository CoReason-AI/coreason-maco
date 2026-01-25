# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict, List
from unittest.mock import MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


@pytest.fixture
def context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
        agent_executor=MagicMock(),
    )


@pytest.mark.asyncio
async def test_crash_and_resume_workflow(context: ExecutionContext) -> None:
    """
    Integration test simulating a crash and resume scenario.
    1. Run a 5-step workflow (A -> B -> C -> D -> E).
    2. Simulate a crash after step B completes (so A and B are done).
    3. Resume with a new runner using the snapshot from A and B.
    4. Verify A and B are restored, and C, D, E are executed.
    """
    # 1. Define 5-step workflow
    graph = nx.DiGraph()
    nodes = ["A", "B", "C", "D", "E"]
    for i, node in enumerate(nodes):
        graph.add_node(node, type="DEFAULT", mock_output=f"output_{node}")
        if i > 0:
            graph.add_edge(nodes[i - 1], node)

    # 2. Run initially and "crash" after B
    initial_runner = WorkflowRunner()

    # We will collect outputs manually to simulate persistent storage
    persistent_store: Dict[str, Any] = {}

    # We stop the consumer loop when B is done to simulate crash
    async for event in initial_runner.run_workflow(graph, context):
        if event.event_type == "NODE_DONE":
            node_id = event.node_id
            output = event.payload["output_summary"]
            persistent_store[node_id] = output

            if node_id == "B":
                # Simulate Crash: Break the loop, effectively killing the process
                break

    # Verify we have state for A and B
    assert "A" in persistent_store
    assert "B" in persistent_store
    assert "C" not in persistent_store

    # 3. Resume with a new runner
    new_runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in new_runner.run_workflow(graph, context, resume_snapshot=persistent_store):
        events.append(event)

    # 4. Verification

    # Check Restored Nodes (A and B)
    restored_events = [e for e in events if e.event_type == "NODE_RESTORED"]
    restored_ids = {e.node_id for e in restored_events}
    assert "A" in restored_ids
    assert "B" in restored_ids
    assert "C" not in restored_ids

    # Check Executed Nodes (C, D, E)
    done_events = [e for e in events if e.event_type == "NODE_DONE"]
    done_ids = {e.node_id for e in done_events}

    # A and B should NOT have NODE_DONE events in the resumed run (they have NODE_RESTORED)
    assert "A" not in done_ids
    assert "B" not in done_ids

    # C, D, E should have executed
    assert "C" in done_ids
    assert "D" in done_ids
    assert "E" in done_ids

    # Verify sequence
    # Ensure C started after restoration
    c_start = next(e for e in events if e.node_id == "C" and e.event_type == "NODE_START")
    # Verify it happened after the last restore event (roughly)
    last_restore_index = max(i for i, e in enumerate(events) if e.event_type == "NODE_RESTORED")
    c_start_index = events.index(c_start)
    assert c_start_index > last_restore_index

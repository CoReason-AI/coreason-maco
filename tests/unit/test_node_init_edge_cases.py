# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent, NodeInit
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


@pytest.fixture  # type: ignore
def mock_agent_executor() -> Any:
    agent_executor = MagicMock()
    agent_executor.invoke = AsyncMock(return_value=MagicMock(content="Mocked Response"))
    return agent_executor


@pytest.mark.asyncio  # type: ignore
async def test_node_init_defaults(mock_context: ExecutionContext) -> None:
    """Test a graph with a node having no attributes. Verify defaults."""
    graph = nx.DiGraph()
    graph.add_node("A")  # No type specified

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Expect: 1 NODE_INIT, 1 NODE_START, 1 NODE_DONE
    assert len(events) == 3
    init_event = events[0]
    assert init_event.event_type == "NODE_INIT"

    # Check payload via Pydantic model
    payload = NodeInit(**init_event.payload)
    assert payload.node_id == "A"
    assert payload.type == "DEFAULT"
    assert payload.visual_cue == "IDLE"


@pytest.mark.asyncio  # type: ignore
async def test_node_init_custom_types(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """Test nodes with various custom types. Ensure graph is connected."""
    graph = nx.DiGraph()
    graph.add_node("AgentNode", type="LLM")
    graph.add_node("ToolNode", type="TOOL")
    graph.add_edge("AgentNode", "ToolNode")

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        if event.event_type == "NODE_INIT":
            events.append(event)

    assert len(events) == 2

    # Sort by node_id to ensure order for assertion
    events.sort(key=lambda e: e.node_id)

    p1 = NodeInit(**events[0].payload)
    assert p1.node_id == "AgentNode"
    assert p1.type == "LLM"

    p2 = NodeInit(**events[1].payload)
    assert p2.node_id == "ToolNode"
    assert p2.type == "TOOL"


@pytest.mark.asyncio  # type: ignore
async def test_node_init_with_resume(mock_context: ExecutionContext) -> None:
    """Verify NODE_INIT is emitted for all nodes, even restored ones."""
    graph = nx.DiGraph()
    graph.add_edge("A", "B")

    runner = WorkflowRunner()
    resume_snapshot = {"A": "Previously Computed"}
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context, resume_snapshot=resume_snapshot):
        events.append(event)

    # Filter for NODE_INIT
    init_events = [e for e in events if e.event_type == "NODE_INIT"]
    assert len(init_events) == 2
    node_ids = sorted([e.node_id for e in init_events])
    assert node_ids == ["A", "B"]

    # Verify execution flow:
    # A should emit NODE_RESTORED
    # B should emit NODE_START, NODE_DONE (and EDGE_ACTIVE from A->B logic)

    restored_events = [e for e in events if e.event_type == "NODE_RESTORED"]
    assert len(restored_events) == 1
    assert restored_events[0].node_id == "A"


@pytest.mark.asyncio  # type: ignore
async def test_complex_graph_initialization(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """Test a diamond graph with mixed types."""
    graph = nx.DiGraph()
    # A -> B, A -> C, B -> D, C -> D
    graph.add_node("A", type="INPUT")
    graph.add_node("B", type="LLM")
    graph.add_node("C", type="TOOL")
    graph.add_node("D", type="OUTPUT")

    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "D")

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # First 4 events must be NODE_INIT
    init_events = events[:4]
    for e in init_events:
        assert e.event_type == "NODE_INIT"

    # Verify all types are present
    init_map = {e.node_id: NodeInit(**e.payload).type for e in init_events}
    assert init_map == {"A": "INPUT", "B": "LLM", "C": "TOOL", "D": "OUTPUT"}

    # Verify total count:
    # 4 Init
    # 4 Nodes * 2 (Start+Done) = 8
    # 4 Edges * 1 = 4
    # Total = 16
    assert len(events) == 16

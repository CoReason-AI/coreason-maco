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
from coreason_identity.models import UserContext

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def mock_agent_executor() -> Any:
    agent_executor = MagicMock()

    # Mock invoke to return an object with .content
    async def mock_invoke(prompt: str, config: Any) -> Any:
        response = MagicMock()
        response.content = "Mock Response"
        return response

    agent_executor.invoke = AsyncMock(side_effect=mock_invoke)
    return agent_executor


@pytest.fixture  # type: ignore
def mock_context(mock_user_context: UserContext) -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=MagicMock(),
        user_context=mock_user_context,
    )


@pytest.mark.asyncio  # type: ignore
async def test_runner_executes_council_node(mock_context: ExecutionContext, mock_agent_executor: Any) -> None:
    """
    Test that the runner correctly executes a COUNCIL node.
    """
    graph = nx.DiGraph()

    # Updated to match new CouncilConfig schema
    council_config = {
        "strategy": "consensus",
        "voters": ["gpt-4", "claude-3"],
        "prompt": "Debate this.",
    }

    graph.add_node("CouncilNode", type="COUNCIL", config=council_config)

    runner = WorkflowRunner(agent_executor=mock_agent_executor)
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    # Verify COUNCIL_VOTE event
    vote_events = [e for e in events if e.event_type == "COUNCIL_VOTE"]
    assert len(vote_events) == 1

    vote_event = vote_events[0]
    assert vote_event.node_id == "CouncilNode"
    assert "gpt-4" in vote_event.payload["votes"]
    assert "claude-3" in vote_event.payload["votes"]

    # Verify NODE_DONE has the consensus
    done_events = [e for e in events if e.event_type == "NODE_DONE"]
    assert len(done_events) == 1
    assert done_events[0].payload["output_summary"] == "Mock Response"


@pytest.mark.asyncio  # type: ignore
async def test_runner_council_node_missing_context_in_handler(mock_agent_executor: Any) -> None:
    """Test that CouncilNodeHandler fails when UserContext is missing in ExecutionContext."""
    graph = nx.DiGraph()
    council_config = {
        "strategy": "consensus",
        "voters": ["gpt-4"],
    }
    graph.add_node("CouncilNode", type="COUNCIL", config=council_config)

    # Context without user_context
    context = ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=MagicMock(),
        user_context=None,
    )

    runner = WorkflowRunner(agent_executor=mock_agent_executor)

    with pytest.raises((ExceptionGroup, ValueError)) as excinfo:
        async for _ in runner.run_workflow(graph, context):
            pass

    # Check if ValueError is in the exception group or raised directly
    err = excinfo.value
    if isinstance(err, ExceptionGroup):
        assert any("UserContext is required" in str(e) for e in err.exceptions)
    else:
        assert "UserContext is required" in str(err)

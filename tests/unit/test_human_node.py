# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import asyncio
from typing import List
from unittest.mock import MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext, FeedbackManager


@pytest.mark.asyncio  # type: ignore
async def test_human_node_execution() -> None:
    """Test successful execution of a HUMAN node."""
    feedback_manager = FeedbackManager()
    context = ExecutionContext(
        user_id="u",
        trace_id="t",
        secrets_map={},
        tool_registry=MagicMock(),
        feedback_manager=feedback_manager,
    )

    graph = nx.DiGraph()
    graph.add_node("human_node", type="HUMAN")

    runner = WorkflowRunner()

    # We need to provide feedback asynchronously while the runner is waiting
    async def provide_feedback() -> None:
        # Wait a bit for the node to start and register future
        while "human_node" not in feedback_manager:
            await asyncio.sleep(0.01)
        # Set result
        feedback_manager.set_result("human_node", "Approved")

    events: List[GraphEvent] = []

    async with asyncio.TaskGroup() as tg:
        tg.create_task(provide_feedback())
        async for event in runner.run_workflow(graph, context):
            events.append(event)

    # Verify Output
    node_done = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "human_node")
    assert node_done.payload["output_summary"] == "Approved"


@pytest.mark.asyncio  # type: ignore
async def test_human_node_missing_manager() -> None:
    """Test that HUMAN node fails if FeedbackManager is missing."""
    # Context without feedback_manager (it has a default, so we must ensure it's None if we want to test that branch)
    # But ExecutionContext definition has a default_factory for feedback_manager.
    # To test the "not feedback_manager" branch in HumanNodeHandler, we'd need to mock getattr or pass something else.
    # Actually, in `HumanNodeHandler.execute`:
    # feedback_manager = getattr(context, "feedback_manager", None)
    # Since ExecutionContext always has it, this branch is hard to hit unless context is not ExecutionContext.
    # But type hint says context: ExecutionContext.

    # We can mock the context object to return None for feedback_manager
    mock_context = MagicMock()
    mock_context.feedback_manager = None

    graph = nx.DiGraph()
    graph.add_node("human_node", type="HUMAN")

    runner = WorkflowRunner()

    with pytest.raises(ExceptionGroup) as excinfo:
        async for _ in runner.run_workflow(graph, mock_context):
            pass

    assert any("FeedbackManager not available" in str(e) for e in excinfo.value.exceptions)

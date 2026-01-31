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
from typing import Any

import pytest

from coreason_maco.engine.handlers import HumanNodeHandler
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext, FeedbackManager


@pytest.fixture  # type: ignore
def base_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test-user",
        trace_id="test-trace",
        secrets_map={},
        tool_registry=None,
    )


@pytest.mark.asyncio  # type: ignore
async def test_human_node_handler_waits(base_context: ExecutionContext) -> None:
    loop = asyncio.get_running_loop()
    future: asyncio.Future[Any] = loop.create_future()

    # Inject future via Manager
    fm = FeedbackManager()
    fm.futures["node-1"] = future
    base_context.feedback_manager = fm

    handler = HumanNodeHandler()
    queue: asyncio.Queue[GraphEvent | None] = asyncio.Queue()

    # Task to resolve the future
    async def resolve_later() -> None:
        await asyncio.sleep(0.05)
        future.set_result("Approved")

    task = asyncio.create_task(resolve_later())

    result = await handler.execute(
        node_id="node-1", run_id="run-1", config={}, context=base_context, queue=queue, node_attributes={}
    )

    assert result == "Approved"
    await task


@pytest.mark.asyncio  # type: ignore
async def test_human_node_handler_missing_manager(base_context: ExecutionContext) -> None:
    handler = HumanNodeHandler()
    queue: asyncio.Queue[GraphEvent | None] = asyncio.Queue()

    # Ensure no manager
    base_context.feedback_manager = None  # type: ignore

    with pytest.raises(ValueError, match="FeedbackManager not available"):
        await handler.execute(
            node_id="node-1", run_id="run-1", config={}, context=base_context, queue=queue, node_attributes={}
        )


@pytest.mark.asyncio  # type: ignore
async def test_human_node_handler_lazy_creation(base_context: ExecutionContext) -> None:
    # Do NOT pre-inject the future
    fm = FeedbackManager()
    base_context.feedback_manager = fm

    handler = HumanNodeHandler()
    queue: asyncio.Queue[GraphEvent | None] = asyncio.Queue()

    # Task to resolve the future after it is created by handler
    async def resolve_later() -> None:
        await asyncio.sleep(0.05)
        # Verify it was created
        assert "node-1" in fm
        fm.set_result("node-1", "Approved")

    task = asyncio.create_task(resolve_later())

    result = await handler.execute(
        node_id="node-1", run_id="run-1", config={}, context=base_context, queue=queue, node_attributes={}
    )

    assert result == "Approved"
    await task

# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import time
from unittest.mock import AsyncMock

import pytest

from coreason_maco.events.protocol import GraphEvent
from coreason_maco.events.sink import LoggingEventSink, RedisEventSink


@pytest.fixture  # type: ignore
def sample_event() -> GraphEvent:
    return GraphEvent(
        event_type="NODE_START",
        run_id="test-run-123",
        node_id="node-1",
        timestamp=time.time(),
        payload={"node_id": "node-1", "status": "RUNNING"},
        visual_metadata={"state": "PULSING"},
    )


@pytest.mark.asyncio  # type: ignore
async def test_redis_event_sink(sample_event: GraphEvent) -> None:
    mock_redis = AsyncMock()
    sink = RedisEventSink(mock_redis)

    await sink.emit(sample_event)

    mock_redis.publish.assert_awaited_once()
    args = mock_redis.publish.await_args[0]
    channel = args[0]
    message = args[1]

    assert channel == "run:test-run-123"
    assert "NODE_START" in message
    assert "test-run-123" in message


@pytest.mark.asyncio  # type: ignore
async def test_logging_event_sink(sample_event: GraphEvent) -> None:
    sink = LoggingEventSink()
    # No assertion on logger currently, just ensuring it doesn't crash
    await sink.emit(sample_event)

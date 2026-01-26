# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Protocol

import redis.asyncio as redis
from loguru import logger

from coreason_maco.events.protocol import GraphEvent


class AsyncEventSink(Protocol):
    """
    Interface for event sinks.
    """

    async def emit(self, event: GraphEvent) -> None:
        """
        Emits an event to the sink.
        """
        ...


class RedisEventSink:
    """
    Event sink that publishes events to Redis Pub/Sub.
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    async def emit(self, event: GraphEvent) -> None:
        """
        Publishes the event to Redis.
        """
        # Publish to "run:{run_id}" channel
        await self.redis.publish(f"run:{event.run_id}", event.model_dump_json())


class LoggingEventSink:
    """
    Event sink that logs events to stdout/logger.
    Useful for local debugging and fallback.
    """

    async def emit(self, event: GraphEvent) -> None:
        """
        Logs the event.
        """
        logger.info(f"Event: {event.event_type} - {event.node_id} - {event.visual_metadata}")

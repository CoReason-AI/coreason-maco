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
import time
import uuid
from typing import AsyncGenerator

import networkx as nx

from coreason_maco.engine.topology import TopologyEngine
from coreason_maco.events.protocol import (
    ExecutionContext,
    GraphEvent,
    NodeCompleted,
    NodeStarted,
)


class WorkflowRunner:
    """
    The main execution engine that iterates through the DAG.
    """

    def __init__(self, topology: TopologyEngine | None = None) -> None:
        self.topology = topology or TopologyEngine()

    async def run_workflow(self, recipe: nx.DiGraph, context: ExecutionContext) -> AsyncGenerator[GraphEvent, None]:
        """
        Executes the workflow defined by the recipe.

        Args:
            recipe: The NetworkX DiGraph representing the workflow.
            context: The execution context.

        Yields:
            GraphEvent: Real-time telemetry events.
        """
        # Validate graph first
        self.topology.validate_graph(recipe)

        run_id = str(uuid.uuid4())
        layers = self.topology.get_execution_layers(recipe)

        # Queue to bridge execution tasks and the generator
        event_queue: asyncio.Queue[GraphEvent | None] = asyncio.Queue()

        async def _execution_task() -> None:
            try:
                for layer in layers:
                    async with asyncio.TaskGroup() as tg:
                        for node_id in layer:
                            tg.create_task(self._execute_node(node_id, run_id, event_queue, context))
                # Signal end of stream
                await event_queue.put(None)
            except Exception:
                # In a real implementation, we would yield an ERROR event here
                # For now, we ensure the queue is closed so the generator doesn't hang
                await event_queue.put(None)
                raise

        # Start execution in background
        producer = asyncio.create_task(_execution_task())

        try:
            # Consumer loop
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        except (GeneratorExit, Exception):
            # If the consumer stops iterating or crashes, cancel the producer
            producer.cancel()
            try:
                await producer
            except asyncio.CancelledError:
                pass
            raise
        finally:
            # Propagate any exceptions from the producer (if it wasn't cancelled)
            if not producer.cancelled():
                await producer

    async def _execute_node(
        self,
        node_id: str,
        run_id: str,
        queue: asyncio.Queue[GraphEvent | None],
        context: ExecutionContext,
    ) -> None:
        """
        Executes a single node.
        """
        # TODO: Use context.tool_registry to execute actual logic
        # 1. Emit NODE_START
        start_payload = NodeStarted(
            node_id=node_id,
            timestamp=time.time(),
            status="RUNNING",
            visual_cue="PULSE",
        )

        start_event = GraphEvent(
            event_type="NODE_START",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=start_payload.model_dump(),
            visual_metadata={"state": "PULSING", "anim": "BREATHE"},
        )
        await queue.put(start_event)

        # Simulate work
        await asyncio.sleep(0.01)

        # 2. Emit NODE_DONE
        end_payload = NodeCompleted(
            node_id=node_id,
            output_summary="Completed",
            status="SUCCESS",
            visual_cue="GREEN_GLOW",
        )

        end_event = GraphEvent(
            event_type="NODE_DONE",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=end_payload.model_dump(),
            visual_metadata={"state": "SOLID", "color": "#GREEN"},
        )
        await queue.put(end_event)

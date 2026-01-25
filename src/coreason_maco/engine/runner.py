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
from typing import Any, AsyncGenerator, Dict, Set

import networkx as nx

from coreason_maco.engine.topology import TopologyEngine
from coreason_maco.events.protocol import (
    ExecutionContext,
    GraphEvent,
    NodeCompleted,
    NodeRestored,
    NodeStarted,
)


class WorkflowRunner:
    """
    The main execution engine that iterates through the DAG.
    """

    def __init__(self, topology: TopologyEngine | None = None) -> None:
        self.topology = topology or TopologyEngine()

    async def run_workflow(
        self, recipe: nx.DiGraph, context: ExecutionContext, resume_snapshot: Dict[str, Any] | None = None
    ) -> AsyncGenerator[GraphEvent, None]:
        """
        Executes the workflow defined by the recipe.

        Args:
            recipe: The NetworkX DiGraph representing the workflow.
            context: The execution context.
            resume_snapshot: A dictionary mapping node IDs to their previous outputs.
                             If provided, these nodes will be restored instead of executed.

        Yields:
            GraphEvent: Real-time telemetry events.
        """
        # Validate graph first
        self.topology.validate_graph(recipe)

        run_id = str(uuid.uuid4())
        layers = self.topology.get_execution_layers(recipe)

        # Queue to bridge execution tasks and the generator
        event_queue: asyncio.Queue[GraphEvent | None] = asyncio.Queue()

        # Shared state for dynamic routing
        node_outputs: Dict[str, Any] = {}
        # Stores edges that have been activated by their source node
        # Format: (source, target)
        activated_edges: Set[tuple[str, str]] = set()

        async def _execution_task() -> None:
            try:
                for layer in layers:
                    nodes_to_run = []
                    nodes_restored = []

                    for node_id in layer:
                        # 1. Check Snapshot
                        if resume_snapshot and node_id in resume_snapshot:
                            nodes_restored.append(node_id)
                            continue

                        # 2. Check Predecessors
                        predecessors = list(recipe.predecessors(node_id))
                        if not predecessors:
                            # Root nodes always run
                            nodes_to_run.append(node_id)
                            continue

                        # Check if at least one incoming edge is activated
                        is_active = False
                        for pred in predecessors:
                            if (pred, node_id) in activated_edges:
                                is_active = True
                                break

                        if is_active:
                            nodes_to_run.append(node_id)
                        # Else: node is skipped implicitly

                    if not nodes_to_run and not nodes_restored:
                        continue

                    # Process Restored Nodes
                    for node_id in nodes_restored:
                        output = resume_snapshot[node_id]  # type: ignore
                        node_outputs[node_id] = output

                        # Emit NODE_RESTORED
                        restore_payload = NodeRestored(
                            node_id=node_id,
                            output_summary=str(output),
                            status="RESTORED",
                            visual_cue="INSTANT_GREEN",
                        )
                        restore_event = GraphEvent(
                            event_type="NODE_RESTORED",
                            run_id=run_id,
                            node_id=node_id,
                            timestamp=time.time(),
                            payload=restore_payload.model_dump(),
                            visual_metadata={"state": "RESTORED", "color": "#00FF00"},
                        )
                        await event_queue.put(restore_event)

                    # Execute Running Nodes
                    if nodes_to_run:
                        async with asyncio.TaskGroup() as tg:
                            for node_id in nodes_to_run:
                                tg.create_task(
                                    self._execute_node(node_id, run_id, event_queue, context, recipe, node_outputs)
                                )

                    # After layer completes, evaluate outgoing edges for all processed nodes
                    all_active_nodes = nodes_restored + nodes_to_run
                    for node_id in all_active_nodes:
                        if node_id not in node_outputs:
                            # Should not happen if _execute_node ran successfully
                            continue  # pragma: no cover

                        output = node_outputs[node_id]
                        successors = list(recipe.successors(node_id))
                        for succ in successors:
                            edge_data = recipe.get_edge_data(node_id, succ)
                            condition = edge_data.get("condition")

                            # Determine if edge should be activated
                            activate = False
                            if condition is None:
                                # Default edge always active
                                activate = True
                            elif output == condition:
                                # Simple equality match
                                activate = True

                            if activate:
                                activated_edges.add((node_id, succ))

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
        recipe: nx.DiGraph,
        node_outputs: Dict[str, Any],
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

        # Determine output
        # In a real scenario, this comes from the tool/agent execution
        # For testing, we look for 'mock_output' in node attributes
        output = recipe.nodes[node_id].get("mock_output", None)

        # Store output for routing
        node_outputs[node_id] = output

        # 2. Emit NODE_DONE
        end_payload = NodeCompleted(
            node_id=node_id,
            output_summary=str(output) if output else "Completed",
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

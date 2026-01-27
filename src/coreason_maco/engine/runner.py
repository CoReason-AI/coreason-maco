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
import traceback
import uuid
from typing import Any, AsyncGenerator, Dict, Set

import anyio
import networkx as nx

from coreason_maco.core.interfaces import AgentExecutor
from coreason_maco.engine.handlers import (
    CouncilNodeHandler,
    DefaultNodeHandler,
    HumanNodeHandler,
    LLMNodeHandler,
    NodeHandler,
    ToolNodeHandler,
)
from coreason_maco.engine.resolver import VariableResolver
from coreason_maco.engine.topology import TopologyEngine
from coreason_maco.events.protocol import (
    EdgeTraversed,
    GraphEvent,
    NodeCompleted,
    NodeInit,
    NodeRestored,
    NodeSkipped,
    NodeStarted,
    WorkflowErrorPayload,
)
from coreason_maco.utils.context import ExecutionContext


class WorkflowRunner:
    """The main execution engine that iterates through the DAG."""

    def __init__(
        self,
        topology: TopologyEngine | None = None,
        max_parallel_agents: int = 10,
        agent_executor: AgentExecutor | None = None,
    ) -> None:
        """Initializes the WorkflowRunner.

        Args:
            topology: Optional TopologyEngine instance.
            max_parallel_agents: Maximum number of concurrent agents.
            agent_executor: Executor for agents (LLMs).

        Raises:
            ValueError: If max_parallel_agents is less than 1.
        """
        if max_parallel_agents < 1:
            raise ValueError("max_parallel_agents must be >= 1")
        self.topology = topology or TopologyEngine()
        self.max_parallel_agents = max_parallel_agents
        self.semaphore = asyncio.Semaphore(max_parallel_agents)
        self.resolver = VariableResolver()
        self.handlers: Dict[str, NodeHandler] = {
            "TOOL": ToolNodeHandler(),
            "LLM": LLMNodeHandler(agent_executor),
            "COUNCIL": CouncilNodeHandler(agent_executor),
            "HUMAN": HumanNodeHandler(),
        }
        self.default_handler = DefaultNodeHandler()

    def _evaluate_edge_condition(
        self,
        condition: str | None,
        output: Any,
        node_outputs: Dict[str, Any],
    ) -> bool:
        """Evaluates a single edge condition.

        Args:
            condition: The condition string (possibly Jinja2).
            output: The output of the source node.
            node_outputs: The map of all node outputs.

        Returns:
            bool: True if the condition is met, False otherwise.
        """
        if condition is None:
            # Default edge always active
            return True
        elif "{{" in condition and "}}" in condition:
            # Jinja2 Expression
            return self.resolver.evaluate_boolean(condition, node_outputs)
        elif hasattr(output, "content") and str(output.content) == condition:
            # Automatic unwrapping for AgentResponse protocols
            return True
        elif str(output) == condition:
            # Simple equality match (casted to string for safety)
            return True
        return False

    async def run_workflow(
        self,
        recipe: nx.DiGraph,
        context: ExecutionContext,
        resume_snapshot: Dict[str, Any] | None = None,
        initial_inputs: Dict[str, Any] | None = None,
    ) -> AsyncGenerator[GraphEvent, None]:
        """Executes the workflow defined by the recipe.

        Args:
            recipe: The NetworkX DiGraph representing the workflow.
            context: The execution context.
            resume_snapshot: A dictionary mapping node IDs to their previous outputs.
                             If provided, these nodes will be restored instead of executed.
            initial_inputs: Initial input variables to be available for resolution.

        Yields:
            GraphEvent: Real-time telemetry events.

        Raises:
            Exception: Propagates any exception that occurs during execution.
        """
        # Validate graph first
        await anyio.to_thread.run_sync(self.topology.validate_graph, recipe)

        run_id = str(uuid.uuid4())
        layers = await anyio.to_thread.run_sync(self.topology.get_execution_layers, recipe)

        # Queue to bridge execution tasks and the generator
        event_queue: asyncio.Queue[GraphEvent | None] = asyncio.Queue()

        # Shared state for dynamic routing
        node_outputs: Dict[str, Any] = initial_inputs.copy() if initial_inputs else {}
        # Stores edges that have been activated by their source node
        # Format: (source, target)
        activated_edges: Set[tuple[str, str]] = set()
        # Stores nodes that have been explicitly skipped
        skipped_nodes: Set[str] = set()

        async def _execution_task() -> None:
            try:
                # Emit NODE_INIT for all nodes to populate the canvas
                for node_id, data in recipe.nodes(data=True):
                    node_type = data.get("type", "DEFAULT")
                    payload = NodeInit(
                        node_id=node_id,
                        type=node_type,
                        visual_cue="IDLE",
                    )
                    event = GraphEvent(
                        event_type="NODE_INIT",
                        run_id=run_id,
                        node_id=node_id,
                        timestamp=time.time(),
                        payload=payload.model_dump(),
                        visual_metadata={"state": "IDLE", "color": "#GREY"},
                    )
                    await event_queue.put(event)

                for layer in layers:
                    nodes_to_run = []
                    nodes_restored = []

                    for node_id in layer:
                        if node_id in skipped_nodes:
                            continue

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
                        # Else: node is skipped implicitly (but might have been pruned explicitly already)

                    if not nodes_to_run and not nodes_restored:
                        continue

                    # Process Restored Nodes
                    for node_id in nodes_restored:
                        output = resume_snapshot[node_id]  # type: ignore
                        node_outputs[node_id] = output

                        # Emit NODE_RESTORED
                        payload_restored = NodeRestored(
                            node_id=node_id,
                            output_summary=str(output),
                            status="RESTORED",
                            visual_cue="INSTANT_GREEN",
                        )
                        event_restored = GraphEvent(
                            event_type="NODE_RESTORED",
                            run_id=run_id,
                            node_id=node_id,
                            timestamp=time.time(),
                            payload=payload_restored.model_dump(),
                            visual_metadata={"state": "RESTORED", "color": "#00FF00"},
                        )
                        await event_queue.put(event_restored)

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
                            if self._evaluate_edge_condition(condition, output, node_outputs):
                                activated_edges.add((node_id, succ))

                                # Emit EDGE_ACTIVE
                                payload_edge = EdgeTraversed(
                                    source=node_id,
                                    target=succ,
                                    animation_speed="FAST",
                                )
                                event_edge = GraphEvent(
                                    event_type="EDGE_ACTIVE",
                                    run_id=run_id,
                                    node_id=node_id,
                                    timestamp=time.time(),
                                    payload=payload_edge.model_dump(),
                                    visual_metadata={"flow_speed": "FAST", "particle": "DOT"},
                                )
                                await event_queue.put(event_edge)
                            else:
                                # Attempt to prune the branch
                                await self._prune_branch(
                                    succ,
                                    run_id,
                                    event_queue,
                                    recipe,
                                    node_outputs,
                                    activated_edges,
                                    skipped_nodes,
                                )

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

    async def _prune_branch(
        self,
        node_id: str,
        run_id: str,
        queue: asyncio.Queue[GraphEvent | None],
        recipe: nx.DiGraph,
        node_outputs: Dict[str, Any],
        activated_edges: Set[tuple[str, str]],
        skipped_nodes: Set[str],
    ) -> None:
        """Recursively marks a branch as skipped if it is unreachable.

        Args:
            node_id: The ID of the node to check for pruning.
            run_id: The ID of the current run.
            queue: The event queue.
            recipe: The workflow graph.
            node_outputs: The current node outputs.
            activated_edges: The set of activated edges.
            skipped_nodes: The set of already skipped nodes.
        """
        if node_id in skipped_nodes or node_id in node_outputs:
            return

        # Check if node is reachable from any other active parent
        predecessors = list(recipe.predecessors(node_id))
        is_reachable = False

        for pred in predecessors:
            # If parent is active (output exists) AND edge is activated -> Reachable
            if pred in node_outputs and (pred, node_id) in activated_edges:
                is_reachable = True
                break

            # If parent is NOT done and NOT skipped -> Potentially reachable
            # We assume "not done" means it hasn't produced output yet and hasn't been skipped
            if pred not in node_outputs and pred not in skipped_nodes:
                # Parent is still pending, so we can't decide yet
                return

        # If we are here, it means all parents are either:
        # 1. Done but didn't activate the edge to us.
        # 2. Skipped themselves.
        # AND none of them activated the edge to us.

        if not is_reachable:
            skipped_nodes.add(node_id)
            payload = NodeSkipped(
                node_id=node_id,
                status="SKIPPED",
                visual_cue="GREY_OUT",
            )
            event = GraphEvent(
                event_type="NODE_SKIPPED",
                run_id=run_id,
                node_id=node_id,
                timestamp=time.time(),
                payload=payload.model_dump(),
                visual_metadata={"state": "SKIPPED", "color": "#GREY"},
            )
            await queue.put(event)

            # Recursively prune successors
            successors = list(recipe.successors(node_id))
            for succ in successors:
                await self._prune_branch(succ, run_id, queue, recipe, node_outputs, activated_edges, skipped_nodes)

    async def _execute_node(
        self,
        node_id: str,
        run_id: str,
        queue: asyncio.Queue[GraphEvent | None],
        context: ExecutionContext,
        recipe: nx.DiGraph,
        node_outputs: Dict[str, Any],
    ) -> None:
        """Executes a single node.

        Args:
            node_id: The ID of the node to execute.
            run_id: The ID of the current run.
            queue: The event queue.
            context: The execution context.
            recipe: The workflow graph.
            node_outputs: The dictionary to store node output.

        Raises:
            Exception: Re-raises any exception during execution after logging.
        """
        try:
            async with self.semaphore:
                # 1. Emit NODE_START
                payload_start = NodeStarted(
                    node_id=node_id,
                    timestamp=time.time(),
                    status="RUNNING",
                    visual_cue="PULSE",
                )
                event_start = GraphEvent(
                    event_type="NODE_START",
                    run_id=run_id,
                    node_id=node_id,
                    timestamp=time.time(),
                    payload=payload_start.model_dump(),
                    visual_metadata={"state": "PULSING", "anim": "BREATHE"},
                )
                await queue.put(event_start)

                node_data = recipe.nodes[node_id]
                node_type = node_data.get("type", "DEFAULT")
                raw_config = node_data.get("config", {})

                # 2. Resolve Inputs (Data Injection)
                config = self.resolver.resolve(raw_config, node_outputs)

                # 3. Delegate to Handler
                handler = self.handlers.get(node_type, self.default_handler)
                output = await handler.execute(
                    node_id=node_id,
                    run_id=run_id,
                    config=config,
                    context=context,
                    queue=queue,
                    node_attributes=node_data,
                )

            # Store output for routing
            node_outputs[node_id] = output

            # 4. Emit NODE_DONE
            payload_done = NodeCompleted(
                node_id=node_id,
                output_summary=str(output) if output is not None else "Completed",
                status="SUCCESS",
                visual_cue="GREEN_GLOW",
            )
            event_done = GraphEvent(
                event_type="NODE_DONE",
                run_id=run_id,
                node_id=node_id,
                timestamp=time.time(),
                payload=payload_done.model_dump(),
                visual_metadata={"state": "SOLID", "color": "#GREEN"},
            )
            await queue.put(event_done)

        except Exception as e:
            # Capture stack trace
            stack = traceback.format_exc()

            # Sanitize snapshot to prevent token leakage
            def _sanitize(data: Any) -> Any:
                if isinstance(data, dict):
                    return {k: _sanitize(v) for k, v in data.items() if k not in {"user_context", "downstream_token"}}
                elif isinstance(data, list):
                    return [_sanitize(v) for v in data]
                return data

            safe_snapshot = _sanitize(node_outputs.copy())

            # Emit Event
            payload_error = WorkflowErrorPayload(
                node_id=node_id,
                error_message=str(e),
                stack_trace=stack,
                input_snapshot=safe_snapshot,
            )
            event_error = GraphEvent(
                event_type="ERROR",
                run_id=run_id,
                node_id=node_id,
                timestamp=time.time(),
                payload=payload_error.model_dump(),
                visual_metadata={"state": "ERROR", "color": "#RED"},
            )
            await queue.put(event_error)

            # Re-raise to ensure workflow stops/bubbles up
            raise e

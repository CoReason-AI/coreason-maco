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
import inspect
import time
from typing import Any, Dict, Protocol

from coreason_maco.core.interfaces import AgentExecutor, ToolExecutor
from coreason_maco.events.protocol import (
    ArtifactGenerated,
    CouncilVotePayload,
    GraphEvent,
    NodeStream,
)
from coreason_maco.strategies.council import CouncilConfig, CouncilStrategy
from coreason_maco.utils.context import ExecutionContext


class NodeHandler(Protocol):
    """Interface for handling execution of a specific node type."""

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        """Executes the node logic.

        Args:
            node_id: The ID of the node.
            run_id: The ID of the current workflow run.
            config: The resolved configuration for the node.
            context: The execution context.
            queue: The event queue for emitting intermediate events.
            node_attributes: Raw attributes of the node from the graph.

        Returns:
            Any: The output of the node execution.
        """
        ...


class ToolNodeHandler:
    """Handler for executing tool nodes."""

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        """Executes a tool node.

        Args:
            node_id: The ID of the node.
            run_id: The ID of the current workflow run.
            config: The resolved configuration containing tool name and args.
            context: The execution context containing the tool registry.
            queue: The event queue for emitting intermediate events.
            node_attributes: Raw attributes of the node from the graph.

        Returns:
            Any: The result of the tool execution.
        """
        tool_name = config.get("tool_name")
        tool_args = config.get("args", {})

        if tool_name:
            # We cast to ToolExecutor protocol to satisfy type checker if possible,
            # but runtime duck typing works too.
            executor: ToolExecutor = context.tool_registry
            result = await executor.execute(tool_name, tool_args, user_context=context.user_context)

            # Check for Artifact
            artifact_type = None
            url = None

            if hasattr(result, "artifact_type") and hasattr(result, "url"):
                artifact_type = result.artifact_type
                url = result.url
            elif isinstance(result, dict) and "artifact_type" in result and "url" in result:
                artifact_type = result["artifact_type"]
                url = result["url"]

            if artifact_type and url:
                payload = ArtifactGenerated(
                    node_id=node_id,
                    artifact_type=artifact_type,
                    url=url,
                )
                event = GraphEvent(
                    event_type="ARTIFACT_GENERATED",
                    run_id=run_id,
                    node_id=node_id,
                    timestamp=time.time(),
                    payload=payload.model_dump(),
                    visual_metadata={"state": "ARTIFACT_GENERATED", "icon": "FILE"},
                )
                await queue.put(event)

            return result
        return None


class LLMNodeHandler:
    """Handler for executing LLM nodes."""

    def __init__(self, agent_executor: AgentExecutor | None = None) -> None:
        """Initializes the LLMNodeHandler.

        Args:
            agent_executor: The executor for running LLM agents.
        """
        self.agent_executor = agent_executor

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        """Executes an LLM node.

        Args:
            node_id: The ID of the node.
            run_id: The ID of the current workflow run.
            config: The resolved configuration containing prompt and model details.
            context: The execution context.
            queue: The event queue for emitting intermediate events.
            node_attributes: Raw attributes of the node from the graph.

        Returns:
            Any: The content generated by the LLM.

        Raises:
            ValueError: If agent_executor is not provided.
        """
        model_config = config.copy()
        # Assuming 'prompt' or 'input' is in config, fallback to args
        prompt = config.get("prompt", config.get("args", {}).get("prompt", "Analyze this."))

        if not self.agent_executor:
            raise ValueError("AgentExecutor is required for LLM nodes but was not provided.")

        agent_executor = self.agent_executor

        # Try streaming first
        try:
            if hasattr(agent_executor, "stream"):
                stream_gen = agent_executor.stream(prompt, model_config)

                if inspect.isasyncgen(stream_gen):
                    full_content = ""
                    async for chunk in stream_gen:
                        full_content += chunk
                        payload = NodeStream(
                            node_id=node_id,
                            chunk=chunk,
                            visual_cue="TEXT_BUBBLE",
                        )
                        event = GraphEvent(
                            event_type="NODE_STREAM",
                            run_id=run_id,
                            node_id=node_id,
                            timestamp=time.time(),
                            payload=payload.model_dump(),
                            visual_metadata={"overlay": "TEXT_BUBBLE"},
                        )
                        await queue.put(event)
                    return full_content
        except (TypeError, AttributeError, NotImplementedError):
            # Fallback to invoke if stream is not implemented or not iterable (e.g. Mock)
            pass

        result = await agent_executor.invoke(prompt, model_config)
        return result.content


class CouncilNodeHandler:
    """Handler for executing Council nodes."""

    def __init__(self, agent_executor: AgentExecutor | None = None) -> None:
        """Initializes the CouncilNodeHandler.

        Args:
            agent_executor: The executor for running agents within the council.
        """
        self.agent_executor = agent_executor

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        """Executes a Council node.

        Args:
            node_id: The ID of the node.
            run_id: The ID of the current workflow run.
            config: The resolved configuration for the council.
            context: The execution context.
            queue: The event queue for emitting intermediate events.
            node_attributes: Raw attributes of the node from the graph.

        Returns:
            Any: The consensus result of the council.

        Raises:
            ValueError: If agent_executor is not provided.
        """
        # Copy config to avoid modifying the graph
        c_config = config.copy()
        prompt = c_config.pop("prompt", "Please analyze.")
        council_config = CouncilConfig(**c_config)

        if not self.agent_executor:
            raise ValueError("AgentExecutor is required for Council nodes but was not provided.")

        strategy = CouncilStrategy(self.agent_executor)

        if context.user_context is None:
            raise ValueError("UserContext is required for CouncilNodeHandler")

        result = await strategy.execute(prompt, council_config, context=context.user_context)

        payload = CouncilVotePayload(
            node_id=node_id,
            votes=result.individual_votes,
        )
        event = GraphEvent(
            event_type="COUNCIL_VOTE",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=payload.model_dump(),
            visual_metadata={"widget": "VOTING_BOOTH"},
        )
        await queue.put(event)

        return result.consensus


class DefaultNodeHandler:
    """Handler for executing default/mock nodes."""

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        """Executes a default node.

        Simulates work and returns mock output if present.

        Args:
            node_id: The ID of the node.
            run_id: The ID of the current workflow run.
            config: The resolved configuration.
            context: The execution context.
            queue: The event queue.
            node_attributes: Raw attributes of the node from the graph.

        Returns:
            Any: The mock output or None.
        """
        # Fallback / Mock
        # Simulate work
        await asyncio.sleep(0.01)
        # Return mock_output from node attributes
        return node_attributes.get("mock_output", None)


class HumanNodeHandler:
    """Handler for executing human-in-the-loop nodes."""

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        """Executes a human node.

        Waits for feedback via the FeedbackManager.

        Args:
            node_id: The ID of the node.
            run_id: The ID of the current workflow run.
            config: The resolved configuration.
            context: The execution context containing the feedback manager.
            queue: The event queue.
            node_attributes: Raw attributes of the node from the graph.

        Returns:
            Any: The input provided by the human.

        Raises:
            ValueError: If FeedbackManager is not available in context.
        """
        feedback_manager = getattr(context, "feedback_manager", None)

        if not feedback_manager:
            raise ValueError("FeedbackManager not available in ExecutionContext")

        if node_id not in feedback_manager:
            loop = asyncio.get_running_loop()
            feedback_manager.create(node_id, loop)

        future = feedback_manager[node_id]

        # Wait for external input
        result = await future
        return result

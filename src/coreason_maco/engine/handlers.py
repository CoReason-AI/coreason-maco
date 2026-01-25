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
from typing import Any, Dict, Protocol

from coreason_maco.core.interfaces import AgentExecutor, ToolExecutor
from coreason_maco.events.factory import EventFactory
from coreason_maco.events.protocol import ExecutionContext, GraphEvent
from coreason_maco.strategies.council import CouncilConfig, CouncilStrategy


class NodeHandler(Protocol):
    """
    Interface for handling execution of a specific node type.
    """

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        """
        Executes the node logic.

        Args:
            node_id: The ID of the node.
            run_id: The ID of the current workflow run.
            config: The resolved configuration for the node.
            context: The execution context.
            queue: The event queue for emitting intermediate events.
            node_attributes: Raw attributes of the node from the graph.

        Returns:
            The output of the node execution.
        """
        ...


class ToolNodeHandler:
    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        tool_name = config.get("tool_name")
        tool_args = config.get("args", {})

        if tool_name:
            # We cast to ToolExecutor protocol to satisfy type checker if possible,
            # but runtime duck typing works too.
            executor: ToolExecutor = context.tool_registry
            return await executor.execute(tool_name, tool_args)
        return None


class LLMNodeHandler:
    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        model_config = config.copy()
        # Assuming 'prompt' or 'input' is in config, fallback to args
        prompt = config.get("prompt", config.get("args", {}).get("prompt", "Analyze this."))

        agent_executor: AgentExecutor = context.agent_executor
        result = await agent_executor.invoke(prompt, model_config)
        return result.content


class CouncilNodeHandler:
    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        # Copy config to avoid modifying the graph
        c_config = config.copy()
        prompt = c_config.pop("prompt", "Please analyze.")
        council_config = CouncilConfig(**c_config)

        agent_executor = context.agent_executor
        strategy = CouncilStrategy(agent_executor)

        result = await strategy.execute(prompt, council_config)

        await queue.put(EventFactory.create_council_vote(run_id, node_id, result.individual_votes))

        return result.consensus


class DefaultNodeHandler:
    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        # Fallback / Mock
        # Simulate work
        await asyncio.sleep(0.01)
        # Return mock_output from node attributes
        return node_attributes.get("mock_output", None)

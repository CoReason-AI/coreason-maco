# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, AsyncGenerator, Dict

from coreason_maco.core.interfaces import ServiceRegistry
from coreason_maco.core.manifest import RecipeManifest
from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.engine.topology import TopologyEngine
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


class WorkflowController:
    """
    The main entry point for executing workflows.
    Orchestrates validation, graph building, and execution.
    """

    def __init__(
        self,
        services: ServiceRegistry,
        topology: TopologyEngine | None = None,
        runner: WorkflowRunner | None = None,
        max_parallel_agents: int = 10,
    ) -> None:
        """
        Args:
            services: The service registry containing dependencies.
            topology: Optional TopologyEngine instance (for testing).
            runner: Optional WorkflowRunner instance (for testing).
            max_parallel_agents: Maximum number of concurrent agents.
        """
        self.services = services
        self.topology = topology or TopologyEngine()
        self.runner = runner or WorkflowRunner(
            topology=self.topology,
            max_parallel_agents=max_parallel_agents,
            agent_executor=services.agent_executor,
        )

    async def execute_recipe(
        self, manifest: Dict[str, Any], inputs: Dict[str, Any]
    ) -> AsyncGenerator[GraphEvent, None]:
        """
        Executes a recipe based on the provided manifest and inputs.

        Args:
            manifest: The raw recipe manifest dictionary.
            inputs: Input parameters for the execution.

        Yields:
            GraphEvent: Real-time telemetry events.
        """
        # 1. Validate Manifest
        recipe_manifest = RecipeManifest(**manifest)

        # 2. Build DAG
        graph = self.topology.build_graph(recipe_manifest)

        # 3. Build Context
        # Ensure inputs contain required fields for context or extract from services/inputs
        # For now, we assume inputs provides what ExecutionContext needs EXCEPT what services provide

        # We need to construct ExecutionContext.
        # ExecutionContext requires: user_id, trace_id, secrets_map, tool_registry

        user_id = inputs.get("user_id")
        trace_id = inputs.get("trace_id")
        secrets_map = inputs.get("secrets_map", {})

        if not user_id:
            raise ValueError("user_id is required in inputs")
        if not trace_id:
            raise ValueError("trace_id is required in inputs")

        context = ExecutionContext(
            user_id=user_id,
            trace_id=trace_id,
            secrets_map=secrets_map,
            tool_registry=self.services.tool_registry,
        )

        # 4. Run Workflow
        event_history = []
        run_id = None

        async for event in self.runner.run_workflow(graph, context, initial_inputs=inputs):
            if run_id is None:
                run_id = event.run_id
            event_history.append(event.model_dump())
            yield event

        # 5. Audit Logging
        if self.services.audit_logger:
            await self.services.audit_logger.log_workflow_execution(
                trace_id=context.trace_id,
                run_id=run_id or "unknown",
                manifest=manifest,
                inputs=inputs,
                events=event_history,
            )

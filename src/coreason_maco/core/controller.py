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

import anyio
from coreason_identity.models import UserContext

from coreason_maco.core.interfaces import ServiceRegistry
from coreason_maco.core.manifest import RecipeManifest
from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.engine.topology import TopologyEngine
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext, request_id_var
from coreason_maco.utils.logger import logger


class WorkflowController:
    """The main entry point for executing workflows.

    Orchestrates validation, graph building, and execution.
    It acts as the public API surface for the library.
    """

    def __init__(
        self,
        services: ServiceRegistry,
        topology: TopologyEngine | None = None,
        runner_cls: type[WorkflowRunner] | None = None,
        max_parallel_agents: int = 10,
    ) -> None:
        """Initializes the WorkflowController.

        Args:
            services: The service registry containing dependencies.
            topology: Optional TopologyEngine instance (for testing).
            runner_cls: Optional WorkflowRunner class (for testing).
            max_parallel_agents: Maximum number of concurrent agents.
        """
        self.services = services
        self.topology = topology or TopologyEngine()
        self.runner_cls = runner_cls or WorkflowRunner
        self.max_parallel_agents = max_parallel_agents

    async def execute_recipe(
        self,
        manifest: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        context: UserContext,
        resume_snapshot: Dict[str, Any] | None = None,
    ) -> AsyncGenerator[GraphEvent, None]:
        """Executes a recipe based on the provided manifest and inputs.

        Validates the manifest, builds the DAG, and streams execution events.

        Args:
            manifest: The raw recipe manifest dictionary.
            inputs: Input parameters for the execution.
            context: The user context (identity passport).
            resume_snapshot: Optional snapshot of a previous execution to resume from.
                             Maps node_id -> output.

        Yields:
            GraphEvent: Real-time telemetry events.

        Raises:
            ValueError: If required inputs are missing.
        """
        if context is None:
            raise ValueError("UserContext is required")

        # 1. Validate Manifest
        # Wrap CPU-heavy validation
        recipe_manifest = await anyio.to_thread.run_sync(lambda: RecipeManifest(**manifest))

        # 2. Build DAG
        # Wrap CPU-heavy graph building
        graph = await anyio.to_thread.run_sync(self.topology.build_graph, recipe_manifest)

        # 3. Instantiate WorkflowRunner
        # Strict Compliance: Runner must be instantiated here to ensure fresh state/config if needed
        runner = self.runner_cls(
            topology=self.topology,
            max_parallel_agents=self.max_parallel_agents,
            agent_executor=self.services.agent_executor,
        )

        # 4. Build Context
        # Ensure inputs contain required fields for context or extract from services/inputs
        # For now, we assume inputs provides what ExecutionContext needs EXCEPT what services provide

        # We need to construct ExecutionContext.
        # ExecutionContext requires: user_id, trace_id, secrets_map, tool_registry

        user_id = context.user_id
        trace_id = inputs.get("trace_id")
        secrets_map = inputs.get("secrets_map", {})
        feedback_manager = inputs.get("feedback_manager")

        if not trace_id:
            raise ValueError("trace_id is required in inputs")

        logger.info("Starting MACO session", user_id=user_id, session_id=trace_id)

        # Build kwargs dynamically to support optional feedback_manager
        ctx_kwargs = {
            "user_id": user_id,
            "trace_id": trace_id,
            "secrets_map": secrets_map,
            "tool_registry": self.services.tool_registry,
            "user_context": context,
        }
        if feedback_manager:
            ctx_kwargs["feedback_manager"] = feedback_manager

        execution_context = ExecutionContext(**ctx_kwargs)

        # Set ContextVar for tracing
        token = request_id_var.set(execution_context.trace_id)

        # 5. Run Workflow
        event_history = []
        run_id = None

        try:
            async for event in runner.run_workflow(
                graph,
                execution_context,
                resume_snapshot=resume_snapshot,
                initial_inputs=inputs,
            ):
                if run_id is None:
                    run_id = event.run_id
                event_history.append(event.model_dump())
                yield event
        finally:
            # Reset ContextVar
            request_id_var.reset(token)

            # 5. Audit Logging
            audit_logger = self.services.audit_logger
            if audit_logger:
                # Sanitize inputs to remove internal objects (like FeedbackManager) that are not JSON serializable
                # We also exclude 'secrets_map' to avoid logging sensitive data
                loggable_inputs = {k: v for k, v in inputs.items() if k not in ["feedback_manager", "secrets_map"]}
                await audit_logger.log_workflow_execution(
                    trace_id=execution_context.trace_id,
                    run_id=run_id or "unknown",
                    manifest=manifest,
                    inputs=loggable_inputs,
                    events=event_history,
                )

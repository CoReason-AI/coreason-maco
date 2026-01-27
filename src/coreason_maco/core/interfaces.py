# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, AsyncGenerator, Dict, List, Optional, Protocol

try:
    from coreason_identity.models import UserContext
except ImportError:  # pragma: no cover
    UserContext = Any


class AgentResponse(Protocol):
    """Response from an agent execution."""

    content: str
    metadata: dict[str, Any]


class AgentExecutor(Protocol):
    """Interface for the agent executor (coreason-cortex)."""

    async def invoke(self, prompt: str, model_config: dict[str, Any]) -> AgentResponse:
        """Invokes an agent.

        Args:
            prompt: The input prompt for the agent.
            model_config: Configuration for the model execution.

        Returns:
            AgentResponse: The response from the agent.
        """
        ...

    def stream(self, prompt: str, model_config: dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streams the agent response.

        Args:
            prompt: The input prompt for the agent.
            model_config: Configuration for the model execution.

        Yields:
            str: Chunks of the response.
        """
        ...


class ToolExecutor(Protocol):
    """Interface for the tool executor (coreason-mcp)."""

    async def execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        user_context: Optional[UserContext] = None,
    ) -> Any:
        """Executes a tool.

        Args:
            tool_name: The name of the tool to execute.
            args: Arguments for the tool.
            user_context: The user context (identity passport).

        Returns:
            Any: The result of the tool execution.
        """
        ...


class AuditLogger(Protocol):
    """Interface for the audit logger (coreason-veritas)."""

    async def log_workflow_execution(
        self,
        trace_id: str,
        run_id: str,
        manifest: Dict[str, Any],
        inputs: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> Any:
        """Logs the complete workflow execution.

        Args:
            trace_id: The trace ID associated with the execution.
            run_id: The run ID of the execution.
            manifest: The recipe manifest used.
            inputs: The inputs provided for the execution.
            events: The list of events generated during execution.

        Returns:
            Any: The result of the logging operation.
        """
        ...


class ServiceRegistry(Protocol):
    """Dependency Injection container."""

    @property
    def tool_registry(self) -> ToolExecutor:
        """Returns the tool registry service."""
        ...

    @property
    def auth_manager(self) -> Any:
        """Returns the auth manager service."""
        ...

    @property
    def audit_logger(self) -> AuditLogger:
        """Returns the audit logger service."""
        ...

    @property
    def agent_executor(self) -> AgentExecutor:
        """Returns the agent executor service."""
        ...

# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, AsyncGenerator, Dict, List, Protocol


class AgentResponse(Protocol):
    """
    Response from an agent execution.
    """

    content: str
    metadata: dict[str, Any]


class AgentExecutor(Protocol):
    """
    Interface for the agent executor (coreason-cortex).
    """

    async def invoke(self, prompt: str, model_config: dict[str, Any]) -> AgentResponse:
        """Invokes an agent."""
        ...

    def stream(self, prompt: str, model_config: dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streams the agent response."""
        ...


class ToolExecutor(Protocol):
    """
    Interface for the tool executor (coreason-mcp).
    """

    async def execute(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Executes a tool."""
        ...


class AuditLogger(Protocol):
    """
    Interface for the audit logger (coreason-veritas).
    """

    async def log_workflow_execution(
        self,
        trace_id: str,
        run_id: str,
        manifest: Dict[str, Any],
        inputs: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> Any:
        """Logs the complete workflow execution."""
        ...


class ServiceRegistry(Protocol):
    """
    Dependency Injection container.
    """

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

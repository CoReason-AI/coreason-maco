from typing import Any, AsyncGenerator, Dict, Optional

try:
    from coreason_identity.models import UserContext
except ImportError:  # pragma: no cover
    UserContext = Any

from coreason_maco.core.interfaces import (
    AgentExecutor,
    AgentResponse,
    AuditLogger,
    ServiceRegistry,
    ToolExecutor,
)
from coreason_maco.utils.logger import logger


class ServerToolExecutor(ToolExecutor):  # pragma: no cover
    """Mock ToolExecutor for server mode."""

    async def execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        user_context: Optional[UserContext] = None,
    ) -> Any:
        """Executes a mock tool.

        Args:
            tool_name: The name of the tool.
            args: The arguments for the tool.
            user_context: The user context.

        Returns:
            Any: Mock result.
        """
        logger.info(f"Executing tool: {tool_name} with args: {args} (user_context present: {user_context is not None})")
        return {
            "status": "executed",
            "tool": tool_name,
            "result": "Server execution placeholder",
        }


class ServerAgentExecutor(AgentExecutor):  # pragma: no cover
    """Mock AgentExecutor for server mode."""

    async def invoke(self, prompt: str, model_config: dict[str, Any]) -> AgentResponse:
        """Invokes a mock agent.

        Args:
            prompt: The input prompt.
            model_config: The model configuration.

        Returns:
            AgentResponse: Mock response.
        """
        logger.info(f"Agent invoked with prompt: {prompt[:50]}...")

        class Response:
            content = f"Processed: {prompt[:50]}..."
            metadata: Dict[str, Any] = {}

        return Response()

    def stream(self, prompt: str, model_config: dict[str, Any]) -> AsyncGenerator[str, None]:  # pragma: no cover
        """Streams a mock response.

        Args:
            prompt: The input prompt.
            model_config: The model configuration.

        Yields:
            str: Mock chunks.
        """

        async def _gen() -> AsyncGenerator[str, None]:
            yield "Streamed "
            yield "Response"

        return _gen()


class ServerAuditLogger(AuditLogger):  # pragma: no cover
    """Mock AuditLogger for server mode."""

    async def log_workflow_execution(
        self,
        trace_id: str,
        run_id: str,
        manifest: Any,
        inputs: Any,
        events: Any,
    ) -> Any:
        """Logs mock audit data.

        Args:
            trace_id: Trace ID.
            run_id: Run ID.
            manifest: Recipe manifest.
            inputs: Inputs.
            events: Events.

        Returns:
            Any: None.
        """
        logger.info(f"[AUDIT] Workflow {run_id} completed for trace {trace_id}")


class ServerRegistry(ServiceRegistry):  # pragma: no cover
    """ServiceRegistry implementation for server mode."""

    def __init__(self) -> None:
        """Initializes the ServerRegistry with mock services."""
        self._tools = ServerToolExecutor()
        self._agents = ServerAgentExecutor()
        self._audit = ServerAuditLogger()

    @property
    def tool_registry(self) -> ToolExecutor:
        """Returns the mock tool registry."""
        return self._tools

    @property
    def auth_manager(self) -> Any:
        """Returns None for auth manager."""
        return None

    @property
    def audit_logger(self) -> AuditLogger:
        """Returns the mock audit logger."""
        return self._audit

    @property
    def agent_executor(self) -> AgentExecutor:
        """Returns the mock agent executor."""
        return self._agents

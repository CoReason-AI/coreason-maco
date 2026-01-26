from typing import Any, AsyncGenerator, Dict

from coreason_maco.core.interfaces import (
    AgentExecutor,
    AgentResponse,
    AuditLogger,
    ServiceRegistry,
    ToolExecutor,
)
from coreason_maco.utils.logger import logger


class ServerToolExecutor(ToolExecutor):  # pragma: no cover
    async def execute(self, tool_name: str, args: dict[str, Any]) -> Any:
        logger.info(f"Executing tool: {tool_name} with args: {args}")
        return {
            "status": "executed",
            "tool": tool_name,
            "result": "Server execution placeholder",
        }


class ServerAgentExecutor(AgentExecutor):  # pragma: no cover
    async def invoke(self, prompt: str, model_config: dict[str, Any]) -> AgentResponse:
        logger.info(f"Agent invoked with prompt: {prompt[:50]}...")

        class Response:
            content = f"Processed: {prompt[:50]}..."
            metadata: Dict[str, Any] = {}

        return Response()

    def stream(self, prompt: str, model_config: dict[str, Any]) -> AsyncGenerator[str, None]:  # pragma: no cover
        async def _gen() -> AsyncGenerator[str, None]:
            yield "Streamed "
            yield "Response"

        return _gen()


class ServerAuditLogger(AuditLogger):  # pragma: no cover
    async def log_workflow_execution(
        self,
        trace_id: str,
        run_id: str,
        manifest: Any,
        inputs: Any,
        events: Any,
    ) -> Any:
        logger.info(f"[AUDIT] Workflow {run_id} completed for trace {trace_id}")


class ServerRegistry(ServiceRegistry):  # pragma: no cover
    def __init__(self) -> None:
        self._tools = ServerToolExecutor()
        self._agents = ServerAgentExecutor()
        self._audit = ServerAuditLogger()

    @property
    def tool_registry(self) -> ToolExecutor:
        return self._tools

    @property
    def auth_manager(self) -> Any:
        return None

    @property
    def audit_logger(self) -> AuditLogger:
        return self._audit

    @property
    def agent_executor(self) -> AgentExecutor:
        return self._agents

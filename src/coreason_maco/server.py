from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import core library components
from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import (
    AgentExecutor,
    AgentResponse,
    AuditLogger,
    ServiceRegistry,
    ToolExecutor,
)

app = FastAPI(title="CoReason MACO", version="0.1.0")


# --- 1. Define Request Models ---
class ExecuteRequest(BaseModel):
    manifest: Dict[str, Any]
    inputs: Dict[str, Any]


# --- 2. Define Infrastructure Implementations ---
# Minimal implementations to allow the server to run without external infrastructure.


class ServerToolExecutor(ToolExecutor):  # pragma: no cover
    async def execute(self, tool_name: str, args: dict[str, Any]) -> Any:
        return {
            "status": "executed",
            "tool": tool_name,
            "result": "Server execution placeholder",
        }


class ServerAgentExecutor(AgentExecutor):  # pragma: no cover
    async def invoke(self, prompt: str, model_config: dict[str, Any]) -> AgentResponse:
        class Response:
            content = f"Processed: {prompt[:50]}..."
            metadata: Dict[str, Any] = {}

        return Response()

    def stream(self, prompt: str, model_config: dict[str, Any]) -> AsyncGenerator[str, None]:
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
        print(f"[AUDIT] Workflow {run_id} completed for trace {trace_id}")


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


# --- 3. Initialize Controller ---
services = ServerRegistry()
controller = WorkflowController(services=services)


# --- 4. API Endpoints ---


@app.get("/health")  # type: ignore[misc]
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/execute")  # type: ignore[misc]
async def execute_workflow(request: ExecuteRequest) -> Dict[str, Any]:
    """
    Executes a workflow and collects all events to return JSON.
    """
    events = []
    try:
        async for event in controller.execute_recipe(request.manifest, request.inputs):
            events.append(event.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"run_id": events[0]["run_id"] if events else None, "events": events}

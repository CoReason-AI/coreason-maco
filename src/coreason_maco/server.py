from typing import Any, Dict

from coreason_identity.models import UserContext
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

# Import core library components
from coreason_maco.core.controller import WorkflowController
from coreason_maco.infrastructure.server_defaults import ServerRegistry

app = FastAPI(title="CoReason MACO", version="0.1.0")


# --- 1. Define Request Models ---
class ExecuteRequest(BaseModel):
    """Request model for workflow execution."""

    manifest: Dict[str, Any]
    inputs: Dict[str, Any]
    user_context: UserContext


# --- 2. Dependency Injection ---
def get_controller() -> WorkflowController:
    """Dependency to provide the WorkflowController.

    Allows for easier testing/overriding.

    Returns:
        WorkflowController: A configured WorkflowController instance.
    """
    services = ServerRegistry()
    return WorkflowController(services=services)


# --- 3. API Endpoints ---


@app.get("/health")  # type: ignore[untyped-decorator]
async def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict[str, str]: Status message.
    """
    return {"status": "healthy"}


@app.post("/execute")  # type: ignore[untyped-decorator]
async def execute_workflow(
    request: ExecuteRequest,
    controller: WorkflowController = Depends(get_controller),  # noqa: B008
) -> Dict[str, Any]:
    """Executes a workflow and collects all events to return JSON.

    Args:
        request: The execution request containing manifest and inputs.
        controller: The workflow controller dependency.

    Returns:
        Dict[str, Any]: The run ID and list of events.

    Raises:
        HTTPException: If execution fails.
    """
    events = []
    try:
        async for event in controller.execute_recipe(request.manifest, request.inputs, context=request.user_context):
            events.append(event.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"run_id": events[0]["run_id"] if events else None, "events": events}

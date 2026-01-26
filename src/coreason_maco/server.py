from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

# Import core library components
from coreason_maco.core.controller import WorkflowController
from coreason_maco.infrastructure.server_defaults import ServerRegistry

app = FastAPI(title="CoReason MACO", version="0.1.0")


# --- 1. Define Request Models ---
class ExecuteRequest(BaseModel):
    manifest: Dict[str, Any]
    inputs: Dict[str, Any]


# --- 2. Dependency Injection ---
def get_controller() -> WorkflowController:
    """
    Dependency to provide the WorkflowController.
    Allows for easier testing/overriding.
    """
    services = ServerRegistry()
    return WorkflowController(services=services)


# --- 3. API Endpoints ---


@app.get("/health")  # type: ignore[misc]
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/execute")  # type: ignore[misc]
async def execute_workflow(
    request: ExecuteRequest,
    controller: WorkflowController = Depends(get_controller),  # noqa: B008
) -> Dict[str, Any]:
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

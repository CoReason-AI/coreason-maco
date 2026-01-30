import os
from typing import Any, Dict, AsyncIterator
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from coreason_identity.models import UserContext
from coreason_maco.core.controller import WorkflowController
from coreason_maco.infrastructure.server_defaults import ServerRegistry, ServerAuditLogger

# Import Adapters
from coreason_maco.infrastructure.remote_mcp_adapter import RemoteMcpAdapter
from coreason_maco.infrastructure.cortex_adapter import RemoteCortexAdapter

# Global references
remote_mcp: RemoteMcpAdapter | None = None
remote_cortex: RemoteCortexAdapter | None = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global remote_mcp, remote_cortex
    
    # 1. Connect MCP
    gateway_url = os.getenv("MCP_GATEWAY_URL", "http://localhost:8080")
    if gateway_url:
        print(f"🔗 Connecting to Remote MCP Gateway at: {gateway_url}")
        remote_mcp = RemoteMcpAdapter(gateway_url)
    
    # 2. Connect Cortex
    cortex_url = os.getenv("CORTEX_URL", "http://localhost:9000")
    print(f"🧠 Connecting to Cortex Service at: {cortex_url}")
    remote_cortex = RemoteCortexAdapter(cortex_url)

    yield
    
    if remote_mcp: await remote_mcp.close()

app = FastAPI(title="CoReason MACO", version="0.1.0", lifespan=lifespan)

class RemoteRegistry(ServerRegistry):
    def __init__(self, mcp_adapter: RemoteMcpAdapter, cortex_adapter: RemoteCortexAdapter):
        self._tool_executor = mcp_adapter
        
        # --- FIX IS HERE ---
        # previously you likely had: self._agent_executor = ServerAgentExecutor()
        self._agent_executor = cortex_adapter 
        
        self._audit_logger = ServerAuditLogger()

    @property
    def tool_registry(self):
        return self._tool_executor

    @property
    def agent_registry(self):
        return self._agent_executor

    @property
    def audit_logger(self):
        return self._audit_logger

def get_controller() -> WorkflowController:
    # Pass both adapters if they exist
    if remote_mcp and remote_cortex:
        return WorkflowController(services=RemoteRegistry(remote_mcp, remote_cortex))
    
    print("⚠️ WARNING: Using local mock registry (Connections missing)")
    return WorkflowController(services=ServerRegistry())

# ... (Endpoints ExecuteRequest, health, execute, tools remain the same) ...
class ExecuteRequest(BaseModel):
    manifest: Dict[str, Any]
    inputs: Dict[str, Any]
    user_context: UserContext

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

@app.get("/tools")
async def get_available_tools():
    if remote_mcp:
        return await remote_mcp.list_tools()
    return []
# ... (imports and earlier code) ...

@app.post("/execute")
async def execute_workflow(
    request: ExecuteRequest,
    controller: WorkflowController = Depends(get_controller),
) -> Dict[str, Any]:
    events = []
    try:
        # Loop through events yielded by the controller
        async for event in controller.execute_recipe(request.manifest, request.inputs, context=request.user_context):
            
            # --- FIX IS HERE ---
            # The 'event' is already a dictionary. Do NOT call .model_dump().
            events.append(event) 
            
    except Exception as e:
        # This catches the error and returns it as HTTP 500
        raise HTTPException(status_code=500, detail=str(e)) from e
        
    return {"run_id": events[0]["run_id"] if events else None, "events": events}

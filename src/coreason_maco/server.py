# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import ServiceRegistry
from coreason_maco.events.protocol import FeedbackManager
from coreason_maco.events.sink import AsyncEventSink, LoggingEventSink, RedisEventSink
from coreason_maco.services import RemoteAgentExecutor, RemoteAuditLogger


# --- Data Models ---
class StartExecutionRequest(BaseModel):
    manifest: Dict[str, Any]
    inputs: Dict[str, Any]


class StartExecutionResponse(BaseModel):
    execution_id: str
    status: str


class ResumeExecutionRequest(BaseModel):
    node_id: str
    outcome: Any


# --- Service Registry ---
class ServiceRegistryImpl(ServiceRegistry):
    def __init__(self) -> None:
        self._agent_executor = RemoteAgentExecutor()
        self._audit_logger = RemoteAuditLogger()
        self._tool_registry: Any = None

    @property
    def tool_registry(self) -> Any:
        return self._tool_registry

    @property
    def auth_manager(self) -> Any:
        return None

    @property
    def audit_logger(self) -> Any:
        return self._audit_logger

    @property
    def agent_executor(self) -> Any:
        return self._agent_executor


# --- Global State ---
job_registry: Dict[str, Dict[str, Any]] = {}
redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    # Startup
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")

    yield

    # Shutdown
    if redis_client:
        await redis_client.aclose()


app = FastAPI(lifespan=lifespan)


async def run_workflow_background(
    execution_id: str,
    controller: WorkflowController,
    manifest: Dict[str, Any],
    inputs: Dict[str, Any],
    event_sink: AsyncEventSink,
) -> None:
    try:
        async for event in controller.execute_recipe(manifest, inputs):
            await event_sink.emit(event)
    except Exception as e:
        logger.exception(f"Workflow {execution_id} failed: {e}")
    finally:
        # Cleanup
        if execution_id in job_registry:
            del job_registry[execution_id]


@app.post("/execution/start", response_model=StartExecutionResponse)  # type: ignore
async def start_execution(req: StartExecutionRequest) -> StartExecutionResponse:
    execution_id = str(uuid.uuid4())

    # Initialize Feedback Mechanism
    feedback_manager = FeedbackManager()

    # Inject feedback_manager into inputs so Controller picks it up
    inputs = req.inputs.copy()
    inputs["feedback_manager"] = feedback_manager

    # Initialize Services
    services = ServiceRegistryImpl()

    # Initialize Controller
    controller = WorkflowController(services=services)

    # Initialize Event Sink
    sink: AsyncEventSink
    if redis_client:
        sink = RedisEventSink(redis_client)
    else:
        logger.warning("Redis client not available, using Logging sink")
        sink = LoggingEventSink()

    # Create Task
    # We use asyncio.create_task to hold the reference for cancellation
    task = asyncio.create_task(run_workflow_background(execution_id, controller, req.manifest, inputs, sink))

    # Store in Registry
    job_registry[execution_id] = {
        "feedback_manager": feedback_manager,
        "status": "running",
        "task": task,
    }

    return StartExecutionResponse(execution_id=execution_id, status="accepted")


@app.post("/execution/{execution_id}/resume")  # type: ignore
async def resume_execution(execution_id: str, req: ResumeExecutionRequest) -> Dict[str, str]:
    job = job_registry.get(execution_id)
    if not job:
        raise HTTPException(status_code=404, detail="Execution not found or already completed")

    feedback_manager: FeedbackManager = job["feedback_manager"]

    if req.node_id not in feedback_manager:
        # Create pre-approved future
        loop = asyncio.get_running_loop()
        f = feedback_manager.create(req.node_id, loop)
        f.set_result(req.outcome)
        return {"status": "resumed (pre-approved)"}

    future = feedback_manager[req.node_id]
    if future.done():
        raise HTTPException(status_code=400, detail=f"Node {req.node_id} already received feedback")

    future.set_result(req.outcome)
    return {"status": "resumed"}


@app.post("/execution/{execution_id}/cancel")  # type: ignore
async def cancel_execution(execution_id: str) -> Dict[str, str]:
    job = job_registry.get(execution_id)
    if not job:
        raise HTTPException(status_code=404, detail="Execution not found")

    task = job.get("task")
    if task:
        task.cancel()
        return {"status": "cancelled"}

    return {"status": "failed to cancel"}

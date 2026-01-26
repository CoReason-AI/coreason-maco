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
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from coreason_maco.events.protocol import FeedbackManager, GraphEvent
from coreason_maco.events.sink import RedisEventSink
from coreason_maco.server import app, job_registry
from coreason_maco.services import RemoteAgentExecutor, RemoteAuditLogger


@pytest.fixture  # type: ignore
def client() -> Generator[TestClient, None, None]:
    with patch("coreason_maco.server.redis.from_url") as mock_cls:
        mock_redis = AsyncMock()
        mock_cls.return_value = mock_redis
        with TestClient(app) as c:
            yield c


@pytest.fixture(autouse=True)  # type: ignore
def clean_registry() -> Generator[None, None, None]:
    job_registry.clear()
    yield
    job_registry.clear()


# --- Service Edge Cases ---


@pytest.mark.asyncio  # type: ignore
async def test_remote_agent_invoke_network_error() -> None:
    with patch("coreason_maco.services.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_client.post.side_effect = httpx.ConnectError("Connection failed")

        executor = RemoteAgentExecutor(base_url="http://mock")
        with pytest.raises(httpx.ConnectError):
            await executor.invoke("hi", {})


@pytest.mark.asyncio  # type: ignore
async def test_remote_agent_invoke_500_error() -> None:
    with patch("coreason_maco.services.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_resp)
        mock_client.post.return_value = mock_resp

        executor = RemoteAgentExecutor(base_url="http://mock")
        with pytest.raises(httpx.HTTPStatusError):
            await executor.invoke("hi", {})


@pytest.mark.asyncio  # type: ignore
async def test_remote_audit_logger_error() -> None:
    with patch("coreason_maco.services.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_client.post.side_effect = Exception("Log failure")

        logger_svc = RemoteAuditLogger(base_url="http://mock")
        with pytest.raises(Exception, match="Log failure"):
            await logger_svc.log_workflow_execution("t", "r", {}, {}, [])


# --- Sink Edge Cases ---


@pytest.mark.asyncio  # type: ignore
async def test_redis_sink_publish_error() -> None:
    mock_redis = AsyncMock()
    mock_redis.publish.side_effect = Exception("Redis down")

    sink = RedisEventSink(mock_redis)
    event = GraphEvent(
        event_type="NODE_START",
        run_id="r",
        node_id="n",
        timestamp=0.0,
        payload={"node_id": "n"},
        visual_metadata={"state": "x"},
    )

    # Should raise exception which bubble up to runner
    with pytest.raises(Exception, match="Redis down"):
        await sink.emit(event)


# --- Server Edge Cases ---


def test_resume_non_existent_execution(client: TestClient) -> None:
    resp = client.post("/execution/fake-id/resume", json={"node_id": "n", "outcome": "ok"})
    assert resp.status_code == 404
    assert "Execution not found" in resp.json()["detail"]


def test_cancel_non_existent_execution(client: TestClient) -> None:
    resp = client.post("/execution/fake-id/cancel")
    assert resp.status_code == 404
    assert "Execution not found" in resp.json()["detail"]


def test_resume_double_approval(client: TestClient) -> None:
    exec_id = "test-double"
    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result("first")

    fm = FeedbackManager()
    fm.futures["node-1"] = future

    job_registry[exec_id] = {"feedback_manager": fm, "status": "running"}

    resp = client.post(f"/execution/{exec_id}/resume", json={"node_id": "node-1", "outcome": "second"})
    assert resp.status_code == 400
    assert "already received feedback" in resp.json()["detail"]


@pytest.mark.asyncio  # type: ignore
async def test_server_background_task_exception_handling() -> None:
    # Verify that run_workflow_background handles exceptions gracefully
    from coreason_maco.server import run_workflow_background

    mock_controller = MagicMock()
    # execute_recipe raises exception immediately
    mock_controller.execute_recipe.side_effect = Exception("Workflow crashed")

    mock_sink = MagicMock()

    exec_id = "fail-job"
    job_registry[exec_id] = {"status": "running"}

    # Run directly
    await run_workflow_background(exec_id, mock_controller, {}, {}, mock_sink)

    # Should clean up registry
    assert exec_id not in job_registry

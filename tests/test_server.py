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
import time
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from coreason_maco.events.protocol import FeedbackManager
from coreason_maco.server import app, job_registry


@pytest.fixture  # type: ignore
def client() -> Generator[TestClient, None, None]:
    # Ensure redis is mocked with AsyncMock so lifespan works
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


def test_start_execution(client: TestClient) -> None:
    # Patch WorkflowController
    with patch("coreason_maco.server.WorkflowController") as mock_controller_cls:
        mock_controller = mock_controller_cls.return_value

        async def mock_execute(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
            from coreason_maco.events.protocol import GraphEvent

            yield GraphEvent(
                event_type="NODE_START",
                run_id="r",
                node_id="n",
                timestamp=time.time(),
                payload={"node_id": "n"},
                visual_metadata={"state": "PULSING"},
            )
            # Sleep to prevent immediate cleanup, so we can assert it exists in registry
            await asyncio.sleep(0.5)

        mock_controller.execute_recipe.side_effect = mock_execute

        resp = client.post(
            "/execution/start",
            json={
                "manifest": {"nodes": {}},
                "inputs": {"user_id": "u", "trace_id": "t"},
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"

        exec_id = data["execution_id"]
        assert exec_id in job_registry
        assert job_registry[exec_id]["status"] == "running"


def test_resume_execution(client: TestClient) -> None:
    exec_id = "test-resume"
    # Use MagicMock for future as it's shared across threads/loops potentially
    mock_future = MagicMock()
    mock_future.done.return_value = False

    fm = FeedbackManager()
    fm.futures["node-1"] = mock_future

    job_registry[exec_id] = {
        "feedback_manager": fm,
        "status": "running",
    }

    resp = client.post(
        f"/execution/{exec_id}/resume",
        json={"node_id": "node-1", "outcome": "approved"},
    )

    assert resp.status_code == 200
    mock_future.set_result.assert_called_with("approved")


def test_resume_execution_pre_approve(client: TestClient) -> None:
    exec_id = "test-resume-pre"
    fm = FeedbackManager()
    job_registry[exec_id] = {"feedback_manager": fm, "status": "running"}

    resp = client.post(
        f"/execution/{exec_id}/resume",
        json={"node_id": "node-2", "outcome": "approved"},
    )

    assert resp.status_code == 200
    assert "node-2" in fm
    # Here the server creates a real Future.
    # We assume it's set.
    future = fm["node-2"]
    assert future.done()
    # Check result safely if possible, or just assume done means done.
    # Since we set it in the handler (synchronously in TestClient context), it should be set.


def test_cancel_execution(client: TestClient) -> None:
    exec_id = "test-cancel"
    mock_task = MagicMock()
    job_registry[exec_id] = {"task": mock_task, "status": "running"}

    resp = client.post(f"/execution/{exec_id}/cancel")
    assert resp.status_code == 200
    mock_task.cancel.assert_called_once()

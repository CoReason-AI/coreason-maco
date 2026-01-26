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
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from coreason_maco.server import app, job_registry

# We need to test the full flow:
# Server -> Controller -> Runner -> Handlers -> Server Resume -> End
# This requires mocking external services (AgentExecutor) but using real Runner and Controller.


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


@pytest.mark.asyncio  # type: ignore
async def test_complex_workflow_integration() -> None:
    # 1. Define Manifest
    # Start -> LLM (Mocked) -> Human (Wait) -> LLM (Mocked) -> End
    manifest = {
        "name": "Complex Test Workflow",
        "nodes": [
            {"id": "start", "type": "DEFAULT", "config": {}},
            {"id": "step1", "type": "LLM", "config": {"prompt": "Hello"}},
            {"id": "human_approval", "type": "HUMAN", "config": {}},
            {"id": "step2", "type": "LLM", "config": {"prompt": "Goodbye"}},
        ],
        "edges": [
            {"source": "start", "target": "step1"},
            {"source": "step1", "target": "human_approval"},
            {"source": "human_approval", "target": "step2"},
        ],
    }

    inputs = {"user_id": "test_user", "trace_id": "test_trace"}

    # 2. Mock Agent Executor
    # We mock the class so that ServiceRegistry gets a mock instance
    with patch("coreason_maco.server.RemoteAgentExecutor") as mock_executor_cls:
        mock_executor = mock_executor_cls.return_value

        # Setup invoke return
        # Ensure invoke is an AsyncMock so it can be awaited
        mock_executor.invoke = AsyncMock()

        mock_response = MagicMock()
        mock_response.content = "Agent says OK"
        mock_executor.invoke.return_value = mock_response

        # Setup stream to fail so we fall back to invoke (or we could mock stream too)
        # LLMNodeHandler falls back on (TypeError, AttributeError, NotImplementedError)
        mock_executor.stream.side_effect = NotImplementedError

        # 3. Mock Redis Publish (to capture events)
        captured_events = []

        async def mock_publish(channel: str, message: str) -> None:
            captured_events.append(message)

        with patch("coreason_maco.server.redis.from_url") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.publish.side_effect = mock_publish
            mock_redis_cls.return_value = mock_redis

            with TestClient(app) as client:
                # 4. Start Execution
                resp = client.post("/execution/start", json={"manifest": manifest, "inputs": inputs})
                assert resp.status_code == 200
                exec_id = resp.json()["execution_id"]

                # 5. Wait for it to hit Human Node
                # We loop and check registry
                max_retries = 50
                waiting = False
                for _ in range(max_retries):
                    await asyncio.sleep(0.1)
                    if exec_id not in job_registry:
                        # Job died unexpectedly
                        break

                    fm = job_registry[exec_id]["feedback_manager"]
                    if "human_approval" in fm:
                        waiting = True
                        break

                if not waiting:
                    # Debug info
                    print(f"Captured Events: {captured_events}")
                    print(f"Job Registry: {job_registry}")

                assert waiting, "Workflow did not reach human_approval node. Check logs/stdout."

                # 6. Verify we are stuck
                # Check events captured so far
                # Ensure step1 is done but step2 hasn't started
                assert any("step1" in e and "NODE_DONE" in e for e in captured_events)
                assert not any("step2" in e and "NODE_START" in e for e in captured_events)

                # 7. Resume
                resp = client.post(
                    f"/execution/{exec_id}/resume", json={"node_id": "human_approval", "outcome": "Approved"}
                )
                assert resp.status_code == 200

                # 8. Wait for completion
                completed = False
                for _ in range(max_retries):
                    await asyncio.sleep(0.1)
                    if exec_id not in job_registry:
                        completed = True
                        break

                assert completed, "Workflow did not complete (registry entry not removed)"

                # 9. Verify final state
                assert any("step2" in e and "NODE_DONE" in e for e in captured_events)
                # Verify invoke calls
                assert mock_executor.invoke.call_count == 2

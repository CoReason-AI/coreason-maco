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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coreason_maco.events.protocol import FeedbackManager
from coreason_maco.services import RemoteAgentExecutor, RemoteAuditLogger


@pytest.mark.asyncio  # type: ignore
async def test_feedback_manager() -> None:
    fm = FeedbackManager()

    # Test create
    loop = asyncio.get_running_loop()
    f1 = fm.create("n1", loop)
    assert "n1" in fm
    assert fm["n1"] is f1
    assert fm.get("n1") is f1

    # Test create implicit loop
    _ = fm.create("n2")
    assert "n2" in fm

    # Test set_result
    fm.set_result("n1", "val")
    assert f1.done()
    assert f1.result() == "val"

    # Test set_result duplicate (should be ignored)
    fm.set_result("n1", "val2")
    assert f1.result() == "val"

    # Test setitem
    f3 = loop.create_future()
    fm["n3"] = f3
    assert fm.get("n3") is f3


def test_services_warnings() -> None:
    # Test constructor warnings when env vars missing
    with patch.dict("os.environ", {}, clear=True):
        with patch("coreason_maco.services.logger") as mock_logger:
            _ = RemoteAgentExecutor()
            mock_logger.warning.assert_called_with("NEXUS_URL not set for RemoteAgentExecutor")

            _ = RemoteAuditLogger()
            mock_logger.warning.assert_called_with("CORTEX_URL not set for RemoteAuditLogger")


@pytest.mark.asyncio  # type: ignore
async def test_server_redis_fail_on_startup() -> None:
    from coreason_maco.server import lifespan

    mock_app = AsyncMock()

    # Mock redis.from_url raising exception
    with patch("coreason_maco.server.redis.from_url", side_effect=Exception("Redis dead")):
        with patch("coreason_maco.server.logger") as mock_logger:
            async with lifespan(mock_app):
                pass
            mock_logger.error.assert_called()


@pytest.mark.asyncio  # type: ignore
async def test_server_no_redis_logging_sink() -> None:
    # Test that start_execution uses LoggingEventSink when redis is None
    from coreason_maco.server import StartExecutionRequest, start_execution

    req = StartExecutionRequest(manifest={}, inputs={"user_id": "u", "trace_id": "t"})

    with patch("coreason_maco.server.redis_client", None):
        with patch("coreason_maco.server.LoggingEventSink") as mock_sink_cls:
            with patch("coreason_maco.server.WorkflowController"):
                # We need to patch run_workflow_background so it doesn't run
                with patch("coreason_maco.server.run_workflow_background"):
                    await start_execution(req)
                    mock_sink_cls.assert_called_once()


def test_auth_manager_none() -> None:
    from coreason_maco.server import ServiceRegistryImpl

    registry = ServiceRegistryImpl()
    assert registry.auth_manager is None


@pytest.mark.asyncio  # type: ignore
async def test_cancel_job_no_task() -> None:
    from coreason_maco.server import cancel_execution, job_registry

    job_registry["no-task-job"] = {"status": "running"}  # No "task" key

    res = await cancel_execution("no-task-job")
    assert res["status"] == "failed to cancel"
    del job_registry["no-task-job"]


@pytest.mark.asyncio  # type: ignore
async def test_remote_agent_missing_url() -> None:
    # Use empty env
    with patch.dict("os.environ", {}, clear=True):
        executor = RemoteAgentExecutor(base_url=None)

        with pytest.raises(ValueError, match="NEXUS_URL is required"):
            await executor.invoke("p", {})

        with pytest.raises(ValueError, match="NEXUS_URL is required"):
            async for _ in executor.stream("p", {}):
                pass


@pytest.mark.asyncio  # type: ignore
async def test_remote_agent_stream_error() -> None:
    with patch("coreason_maco.services.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        # Make stream a MagicMock so it raises immediately on call,
        # mimicking a failure to start the stream context
        mock_client.stream = MagicMock()
        mock_client.stream.side_effect = Exception("Stream fail")

        executor = RemoteAgentExecutor(base_url="http://mock")
        with pytest.raises(Exception, match="Stream fail"):
            async for _ in executor.stream("p", {}):
                pass

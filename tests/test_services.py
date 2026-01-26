# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coreason_maco.services import RemoteAgentExecutor, RemoteAuditLogger


@pytest.mark.asyncio  # type: ignore
async def test_remote_agent_invoke() -> None:
    with patch("coreason_maco.services.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": "Hello", "metadata": {}}
        mock_client.post.return_value = mock_resp

        executor = RemoteAgentExecutor(base_url="http://mock")
        resp = await executor.invoke("hi", {})

        assert resp.content == "Hello"
        mock_client.post.assert_awaited()


@pytest.mark.asyncio  # type: ignore
async def test_remote_agent_stream() -> None:
    with patch("coreason_maco.services.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        # Mock aiter_text
        async def mock_aiter() -> Any:
            yield "chunk1"
            yield "chunk2"

        mock_resp.aiter_text.side_effect = mock_aiter

        # Configure stream to return a context manager
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None

        # We replace the auto-created AsyncMock with a MagicMock
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)

        executor = RemoteAgentExecutor(base_url="http://mock")
        chunks = []
        async for chunk in executor.stream("hi", {}):
            chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2"]
        mock_client.stream.assert_called()


@pytest.mark.asyncio  # type: ignore
async def test_remote_audit_log() -> None:
    with patch("coreason_maco.services.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_client.post.return_value = mock_resp

        logger = RemoteAuditLogger(base_url="http://mock")
        res = await logger.log_workflow_execution("t", "r", {}, {}, [])

        assert res["status"] == "ok"
        mock_client.post.assert_awaited()

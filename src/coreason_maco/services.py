# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import os
from typing import Any, AsyncGenerator, Dict, List

import httpx
from loguru import logger


class AgentResponseWrapper:
    """Wrapper for agent response to satisfy protocol."""

    def __init__(self, content: str, metadata: Dict[str, Any]) -> None:
        self.content = content
        self.metadata = metadata


class RemoteAgentExecutor:
    """
    Agent Executor that calls the Nexus service.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("NEXUS_URL")
        if not self.base_url:
            logger.warning("NEXUS_URL not set for RemoteAgentExecutor")

    async def invoke(self, prompt: str, model_config: Dict[str, Any]) -> Any:
        """Invokes an agent via HTTP."""
        if not self.base_url:
            raise ValueError("NEXUS_URL is required")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/agent/invoke",
                    json={"prompt": prompt, "config": model_config},
                    timeout=60.0,
                )
                resp.raise_for_status()
                data = resp.json()
                return AgentResponseWrapper(data.get("content", ""), data.get("metadata", {}))
            except Exception as e:
                logger.error(f"Failed to invoke agent: {e}")
                raise

    async def stream(self, prompt: str, model_config: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streams the agent response via HTTP."""
        if not self.base_url:
            raise ValueError("NEXUS_URL is required")

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/agent/stream",
                    json={"prompt": prompt, "config": model_config},
                    timeout=60.0,
                ) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_text():
                        yield chunk
            except Exception as e:
                logger.error(f"Failed to stream agent: {e}")
                raise


class RemoteAuditLogger:
    """
    Audit Logger that calls the Cortex service.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("CORTEX_URL")
        if not self.base_url:
            logger.warning("CORTEX_URL not set for RemoteAuditLogger")

    async def log_workflow_execution(
        self,
        trace_id: str,
        run_id: str,
        manifest: Dict[str, Any],
        inputs: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> Any:
        """Logs execution via HTTP."""
        if not self.base_url:
            # If not configured, maybe just log locally and return
            logger.warning("CORTEX_URL not configured, skipping remote audit log")
            return {"status": "skipped"}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/audit/log",
                    json={
                        "trace_id": trace_id,
                        "run_id": run_id,
                        "manifest": manifest,
                        "inputs": inputs,
                        "events": events,
                    },
                    timeout=30.0,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Failed to log audit: {e}")
                raise

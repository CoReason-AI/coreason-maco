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
from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import MagicMock

import pytest

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, AgentResponse, ServiceRegistry, ToolExecutor
from coreason_maco.events.protocol import GraphEvent

# --- Mocks ---


class MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.metadata: Dict[str, Any] = {}


class MockAgentExecutor(AgentExecutor):
    def __init__(self, responses: Dict[str, str] | None = None, delay: float = 0.0) -> None:
        self.responses = responses or {}
        self.delay = delay

    async def invoke(self, prompt: str, model_config: Dict[str, Any]) -> AgentResponse:
        await asyncio.sleep(self.delay)

        model_name = model_config.get("model", "unknown")

        # If it's a synthesis prompt (long), we detect it
        if "Original Query:" in prompt:
            return MockResponse("Consensus Reached")

        return MockResponse(self.responses.get(model_name, "Default Response"))

    def stream(self, prompt: str, model_config: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async def _gen() -> AsyncGenerator[str, None]:
            yield "Mock Stream"

        return _gen()


class MockToolExecutor(ToolExecutor):
    async def execute(self, tool_name: str, args: dict[str, Any], user_context: Any = None) -> Any:
        return "mock_tool_result"


class MockServiceRegistry(ServiceRegistry):
    def __init__(self, agent_executor: AgentExecutor | None = None):
        self._agent_executor = agent_executor or MockAgentExecutor()

    @property
    def tool_registry(self) -> ToolExecutor:
        return MockToolExecutor()

    @property
    def auth_manager(self) -> Any:
        return MagicMock()

    @property
    def audit_logger(self) -> Any:
        from unittest.mock import AsyncMock

        return AsyncMock()

    @property
    def agent_executor(self) -> AgentExecutor:
        return self._agent_executor


# --- Tests ---


@pytest.mark.asyncio  # type: ignore
async def test_runner_executes_council_node() -> None:
    # 1. Setup Services
    mock_agent_exec = MockAgentExecutor(responses={"gpt-4": "Blue", "claude": "Red"})
    services = MockServiceRegistry(agent_executor=mock_agent_exec)

    # 2. Setup Controller
    controller = WorkflowController(services)

    # 3. Define Manifest
    manifest = {
        "name": "Council Workflow",
        "nodes": [
            {
                "id": "council_node",
                "type": "COUNCIL",
                "config": {
                    "agents": [{"model": "gpt-4"}, {"model": "claude"}],
                    "synthesizer": {"model": "judge"},
                    "prompt": "What is the best color?",
                },
            },
        ],
        "edges": [],
    }

    inputs = {"user_id": "u", "trace_id": "t"}

    # 4. Execute
    events: List[GraphEvent] = []
    async for event in controller.execute_recipe(manifest, inputs):
        events.append(event)

    # 5. Verify
    # Should have NODE_START, COUNCIL_VOTE, NODE_DONE

    # Check for COUNCIL_VOTE
    vote_events = [e for e in events if e.event_type == "COUNCIL_VOTE"]
    assert len(vote_events) == 1
    vote_payload = vote_events[0].payload

    # Verify Votes
    assert "gpt-4" in vote_payload["votes"]
    assert vote_payload["votes"]["gpt-4"] == "Blue"
    assert "claude" in vote_payload["votes"]
    assert vote_payload["votes"]["claude"] == "Red"

    # Check for NODE_DONE
    done_events = [e for e in events if e.event_type == "NODE_DONE"]
    assert len(done_events) == 1
    assert done_events[0].node_id == "council_node"
    # Output summary should be consensus
    assert done_events[0].payload["output_summary"] == "Consensus Reached"

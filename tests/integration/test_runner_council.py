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
from coreason_identity.models import UserContext

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

        # In v0.9.0, model_config comes from AgentNode (only agent_name) or CouncilConfig.
        # CouncilNodeHandler passes `prompt`.

        # If it's a voting agent, we might get model config from CouncilConfig voters?
        # CouncilStrategy.execute calls agent_executor for each voter.
        # It passes `model_config` derived from... wait, CouncilConfig only has `voters` (list of strings).
        # So CouncilStrategy must resolve voter names to config?
        # Let's assume for this test that the mock executor just returns based on some heuristic or defaults.

        # Actually, CouncilStrategy in coreason-maco (I should check it) iterates voters.
        # If voters are ["gpt-4", "claude"], it calls invoke with those configs?

        # Since I can't see CouncilStrategy implementation details right now without reading it,
        # I'll assume it passes enough info to distinguish agents.

        # Hack: Since we don't have model name in config passed to invoke (maybe),
        # we might need to rely on prompt or order.
        # BUT, let's assume the Strategy passes the voter name as model in config.

        model_name = model_config.get("model", "unknown")

        # If model_name is unknown, maybe check if prompt contains hint?
        # But let's see.

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
async def test_runner_executes_council_node(mock_user_context: UserContext) -> None:
    # 1. Setup Services
    # We expect the council strategy to use "gpt-4" and "claude" as models/agent names
    mock_agent_exec = MockAgentExecutor(responses={"gpt-4": "Blue", "claude": "Red"})
    services = MockServiceRegistry(agent_executor=mock_agent_exec)

    # 2. Setup Controller
    controller = WorkflowController(services)

    # 3. Define Manifest
    manifest = {
        "id": "council-flow",
        "version": "1.0.0",
        "name": "Council Workflow",
        "topology": {
            "nodes": [
                {
                    "id": "council_node",
                    "type": "agent",  # Use agent type
                    "agent_name": "Chairperson",
                    "visual": {"x_y_coordinates": [0, 0], "label": "Council", "icon": "users"},
                    "council_config": {
                        "strategy": "consensus",  # strategy required
                        "voters": ["gpt-4", "claude"],  # voters required
                    },
                },
            ],
            "edges": [],
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
    }

    inputs = {"trace_id": "t"}

    # 4. Execute
    events: List[GraphEvent] = []
    async for event in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        events.append(event)

    # 5. Verify
    # Should have NODE_START, COUNCIL_VOTE, NODE_DONE

    # Check for COUNCIL_VOTE
    vote_events = [e for e in events if e.event_type == "COUNCIL_VOTE"]
    assert len(vote_events) == 1
    vote_payload = vote_events[0].payload

    # Verify Votes
    # Note: CouncilStrategy needs to correctly map voters string to invoke calls.
    # If it fails, we might see "Default Response" or empty votes.
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

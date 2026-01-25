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
from typing import Any, AsyncGenerator, Dict
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, AgentResponse, ServiceRegistry, ToolExecutor

# --- Mocks (Reusing similar mocks as test_runner_council.py) ---


class MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.metadata: Dict[str, Any] = {}


class MockAgentExecutor(AgentExecutor):
    def __init__(
        self, responses: Dict[str, str] | None = None, delay: float = 0.0, failure_on: str | None = None
    ) -> None:
        self.responses = responses or {}
        self.delay = delay
        self.failure_on = failure_on

    async def invoke(self, prompt: str, model_config: Dict[str, Any]) -> AgentResponse:
        await asyncio.sleep(self.delay)

        model_name = model_config.get("model", "unknown")

        if self.failure_on and self.failure_on == model_name:
            raise ValueError(f"Simulated failure for {model_name}")

        if "Original Query:" in prompt:
            # Synthesizer logic check
            if self.failure_on == "judge":
                raise ValueError("Simulated failure for judge")
            return MockResponse("Consensus Reached")

        return MockResponse(self.responses.get(model_name, "Default Response"))

    def stream(self, prompt: str, model_config: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async def _gen() -> AsyncGenerator[str, None]:
            yield "Mock Stream"

        return _gen()


class MockToolExecutor(ToolExecutor):
    async def execute(self, tool_name: str, args: dict[str, Any]) -> Any:
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
async def test_council_node_invalid_config() -> None:
    """Test that execution fails if the council config is invalid (missing fields)."""
    services = MockServiceRegistry()
    controller = WorkflowController(services)

    # Missing 'agents' and 'synthesizer'
    manifest = {
        "name": "Invalid Council",
        "nodes": [
            {"id": "bad_node", "type": "COUNCIL", "config": {"prompt": "Analyze"}},
        ],
        "edges": [],
    }
    inputs = {"user_id": "u", "trace_id": "t"}

    # Expect ValidationError from Pydantic when CouncilConfig is instantiated inside the runner
    # The runner catches exceptions in _execution_task? No, it raises them.
    # The task group in _execution_task will raise ExceptionGroup (Py3.11+) or the exception.

    with pytest.raises((ValidationError, ExceptionGroup)):
        async for _ in controller.execute_recipe(manifest, inputs):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_council_node_execution_failure() -> None:
    """Test that runner propagates errors when Council Strategy fails completely."""
    # Setup agent executor that fails for the only agent
    mock_exec = MockAgentExecutor(failure_on="gpt-4")
    services = MockServiceRegistry(agent_executor=mock_exec)
    controller = WorkflowController(services)

    manifest = {
        "name": "Failing Council",
        "nodes": [
            {
                "id": "fail_node",
                "type": "COUNCIL",
                "config": {"agents": [{"model": "gpt-4"}], "synthesizer": {"model": "judge"}, "prompt": "Analyze"},
            },
        ],
        "edges": [],
    }
    inputs = {"user_id": "u", "trace_id": "t"}

    # Expect RuntimeError: "All council agents failed..."
    with pytest.raises((RuntimeError, ExceptionGroup)):
        async for _ in controller.execute_recipe(manifest, inputs):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_parallel_council_nodes() -> None:
    """Test multiple Council nodes running in parallel."""
    # Setup
    mock_exec = MockAgentExecutor(
        responses={"gpt-4": "Blue", "claude": "Red"},
        delay=0.05,  # Add delay to ensure concurrency overlap
    )
    services = MockServiceRegistry(agent_executor=mock_exec)
    controller = WorkflowController(services)

    manifest = {
        "name": "Parallel Councils",
        "nodes": [
            {"id": "Start", "type": "START", "config": {}},
            {
                "id": "Council_A",
                "type": "COUNCIL",
                "config": {"agents": [{"model": "gpt-4"}], "synthesizer": {"model": "judge"}, "prompt": "Q1"},
            },
            {
                "id": "Council_B",
                "type": "COUNCIL",
                "config": {"agents": [{"model": "claude"}], "synthesizer": {"model": "judge"}, "prompt": "Q2"},
            },
        ],
        "edges": [
            {"source": "Start", "target": "Council_A"},
            {"source": "Start", "target": "Council_B"},
        ],
    }
    inputs = {"user_id": "u", "trace_id": "t"}

    events = []
    async for event in controller.execute_recipe(manifest, inputs):
        events.append(event)

    # Verification
    # 1. Both councils should have executed
    node_done_events = [e for e in events if e.event_type == "NODE_DONE" and e.node_id in ["Council_A", "Council_B"]]
    assert len(node_done_events) == 2

    # 2. Both should have votes
    vote_events = [e for e in events if e.event_type == "COUNCIL_VOTE"]
    assert len(vote_events) == 2

    # Check A
    vote_a = next(e for e in vote_events if e.node_id == "Council_A")
    assert "gpt-4" in vote_a.payload["votes"]

    # Check B
    vote_b = next(e for e in vote_events if e.node_id == "Council_B")
    assert "claude" in vote_b.payload["votes"]

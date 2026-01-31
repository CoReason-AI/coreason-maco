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
from coreason_identity.models import UserContext
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
    async def execute(self, tool_name: str, args: dict[str, Any], user_context: Any = None) -> Any:
        return "mock_tool_result"


class MockServiceRegistry(ServiceRegistry):
    def __init__(self, agent_executor: AgentExecutor | None = None):
        # Allow None for testing missing executor
        self._agent_executor = agent_executor if agent_executor is not None else MockAgentExecutor()
        self._force_none = agent_executor is None and isinstance(agent_executor, type(None))

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
async def test_council_node_invalid_config(mock_user_context: UserContext) -> None:
    """Test that execution fails if the council config is invalid (missing fields)."""
    services = MockServiceRegistry()
    controller = WorkflowController(services)

    # Missing 'voters'
    manifest = {
        "id": "invalid-council-recipe",
        "version": "1.0.0",
        "name": "Invalid Council",
        "inputs": {},
        "graph": {
            "nodes": [
                {
                    "id": "bad_node",
                    "type": "agent",
                    "agent_name": "BadCouncil",
                    "council_config": {
                        "strategy": "consensus",
                        # "voters": [...] Missing
                    },
                },
            ],
            "edges": [],
        },
    }
    inputs = {"trace_id": "t"}

    # Expect ValidationError from Pydantic when CouncilConfig is instantiated inside the runner
    # The runner catches exceptions in _execution_task? No, it raises them.
    # The task group in _execution_task will raise ExceptionGroup (Py3.11+) or the exception.

    with pytest.raises((ValidationError, ExceptionGroup)):
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_council_node_execution_failure(mock_user_context: UserContext) -> None:
    """Test that runner propagates errors when Council Strategy fails completely."""
    # Setup agent executor that fails for the only agent
    mock_exec = MockAgentExecutor(failure_on="gpt-4")
    services = MockServiceRegistry(agent_executor=mock_exec)
    controller = WorkflowController(services)

    manifest = {
        "id": "fail-council-recipe",
        "version": "1.0.0",
        "name": "Failing Council",
        "inputs": {},
        "graph": {
            "nodes": [
                {
                    "id": "fail_node",
                    "type": "agent",
                    "agent_name": "FailCouncil",
                    "council_config": {"strategy": "consensus", "voters": ["gpt-4"]},
                },
            ],
            "edges": [],
        },
    }
    inputs = {"trace_id": "t"}

    # Expect RuntimeError: "All council agents failed..."
    with pytest.raises((RuntimeError, ExceptionGroup)):
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_parallel_council_nodes(mock_user_context: UserContext) -> None:
    """Test multiple Council nodes running in parallel."""
    # Setup
    mock_exec = MockAgentExecutor(
        responses={"gpt-4": "Blue", "claude": "Red"},
        delay=0.05,  # Add delay to ensure concurrency overlap
    )
    services = MockServiceRegistry(agent_executor=mock_exec)
    controller = WorkflowController(services)

    manifest = {
        "id": "parallel-council-recipe",
        "version": "1.0.0",
        "name": "Parallel Councils",
        "inputs": {},
        "graph": {
            "nodes": [
                {"id": "Start", "type": "agent", "agent_name": "StartAgent"},
                {
                    "id": "Council_A",
                    "type": "agent",
                    "agent_name": "CouncilA",
                    "council_config": {"strategy": "consensus", "voters": ["gpt-4"]},
                },
                {
                    "id": "Council_B",
                    "type": "agent",
                    "agent_name": "CouncilB",
                    "council_config": {"strategy": "consensus", "voters": ["claude"]},
                },
            ],
            "edges": [
                {"source_node_id": "Start", "target_node_id": "Council_A"},
                {"source_node_id": "Start", "target_node_id": "Council_B"},
            ],
        },
    }
    inputs = {"trace_id": "t"}

    events = []
    async for event in controller.execute_recipe(manifest, inputs, context=mock_user_context):
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


@pytest.mark.asyncio  # type: ignore
async def test_council_node_missing_executor(mock_user_context: UserContext) -> None:
    """Test that missing agent_executor raises ValueError for Council node."""
    # To simulate missing executor, we need to pass None to WorkflowRunner.
    # We can do this by mocking ServiceRegistry to return None.

    # Custom registry that returns None
    class NoneExecutorRegistry(ServiceRegistry):
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
            return None  # type: ignore

    services = NoneExecutorRegistry()
    controller = WorkflowController(services)

    manifest = {
        "id": "missing-exec-recipe",
        "version": "1.0.0",
        "name": "Missing Exec Council",
        "inputs": {},
        "graph": {
            "nodes": [
                {
                    "id": "node",
                    "type": "agent",
                    "agent_name": "CouncilNode",
                    "council_config": {"strategy": "consensus", "voters": ["gpt-4"]},
                },
            ],
            "edges": [],
        },
    }
    inputs = {"trace_id": "t"}

    with pytest.raises((ValueError, ExceptionGroup)) as excinfo:
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass

    # Check error message
    # ExceptionGroup usually wraps it
    if isinstance(excinfo.value, ExceptionGroup):
        assert any("AgentExecutor is required" in str(e) for e in excinfo.value.exceptions)
    else:
        assert "AgentExecutor is required" in str(excinfo.value)

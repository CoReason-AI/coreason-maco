# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from coreason_identity.models import UserContext

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, ServiceRegistry, ToolExecutor


class VerifyingToolExecutor(ToolExecutor):
    """Tool Executor that verifies UserContext is passed."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(self, tool_name: str, args: Dict[str, Any], user_context: Any = None) -> Any:
        self.calls.append({"tool": tool_name, "user_context": user_context})
        return f"Executed {tool_name}"


class MockServiceRegistry(ServiceRegistry):
    def __init__(self, tool_executor: ToolExecutor) -> None:
        self._tool_executor = tool_executor
        self._agent_executor = MagicMock(spec=AgentExecutor)
        self._agent_executor.invoke = MagicMock()  # Needs to be awaitable

        async def mock_invoke(*args: Any, **kwargs: Any) -> Any:
            m = MagicMock()
            m.content = "Agent Output"
            return m

        self._agent_executor.invoke.side_effect = mock_invoke

        self._audit_logger = MagicMock()
        self._audit_logger.log_workflow_execution = MagicMock()

        async def mock_log(*args: Any, **kwargs: Any) -> None:
            pass

        self._audit_logger.log_workflow_execution.side_effect = mock_log

    @property
    def tool_registry(self) -> ToolExecutor:
        return self._tool_executor

    @property
    def auth_manager(self) -> Any:
        return MagicMock()

    @property
    def audit_logger(self) -> Any:
        return self._audit_logger

    @property
    def agent_executor(self) -> AgentExecutor:
        return self._agent_executor


@pytest.mark.asyncio  # type: ignore
async def test_propagation_sequential_workflow(mock_user_context: UserContext) -> None:
    """Test context flows through a chain of tools."""
    tool_executor = VerifyingToolExecutor()
    services = MockServiceRegistry(tool_executor)
    controller = WorkflowController(services)

    manifest = {
        "id": "seq-recipe",
        "version": "1.0.0",
        "name": "Sequential",
        "inputs": {},
        "graph": {
            "nodes": [
                {"id": "A", "type": "logic", "code": "ToolA"},
                {"id": "B", "type": "logic", "code": "ToolB"},
            ],
            "edges": [{"source_node_id": "A", "target_node_id": "B"}],
        },
    }
    inputs = {"trace_id": "t"}

    async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        pass

    assert len(tool_executor.calls) == 2
    assert tool_executor.calls[0]["user_context"] is mock_user_context
    assert tool_executor.calls[1]["user_context"] is mock_user_context


@pytest.mark.asyncio  # type: ignore
async def test_propagation_parallel_branching(mock_user_context: UserContext) -> None:
    """Test context flows to parallel branches."""
    tool_executor = VerifyingToolExecutor()
    services = MockServiceRegistry(tool_executor)
    controller = WorkflowController(services)

    manifest = {
        "id": "parallel-recipe",
        "version": "1.0.0",
        "name": "Parallel",
        "inputs": {},
        "graph": {
            "nodes": [
                {"id": "Start", "type": "logic", "code": "StartTool"},
                {"id": "Branch1", "type": "logic", "code": "Tool1"},
                {"id": "Branch2", "type": "logic", "code": "Tool2"},
            ],
            "edges": [
                {"source_node_id": "Start", "target_node_id": "Branch1"},
                {"source_node_id": "Start", "target_node_id": "Branch2"},
            ],
        },
    }
    inputs = {"trace_id": "t"}

    async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        pass

    assert len(tool_executor.calls) == 3
    # Check consistency
    for call in tool_executor.calls:
        assert call["user_context"] is mock_user_context


@pytest.mark.asyncio  # type: ignore
async def test_propagation_missing_context() -> None:
    """Test robust execution when UserContext is missing (Should raise error now)."""
    tool_executor = VerifyingToolExecutor()
    services = MockServiceRegistry(tool_executor)
    controller = WorkflowController(services)

    manifest = {
        "id": "none-context-recipe",
        "version": "1.0.0",
        "name": "None Context",
        "inputs": {},
        "graph": {
            "nodes": [{"id": "A", "type": "logic", "code": "ToolA"}],
            "edges": [],
        },
    }
    inputs = {"trace_id": "t"}

    # Pass None explicitly (default) - Should raise TypeError/ValueError
    with pytest.raises((TypeError, ValueError)):
        async for _ in controller.execute_recipe(manifest, inputs, context=None):
            pass

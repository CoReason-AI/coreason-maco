# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, AsyncGenerator
from unittest.mock import MagicMock

import pytest
from coreason_identity.models import UserContext

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, ServiceRegistry, ToolExecutor
from coreason_maco.events.protocol import GraphEvent


class MockToolExecutor(ToolExecutor):
    async def execute(self, tool_name: str, args: dict[str, Any], user_context: Any = None) -> Any:
        return "mock_result"


class MockServiceRegistry(ServiceRegistry):
    def __init__(self) -> None:
        from unittest.mock import AsyncMock

        self._audit_logger = AsyncMock()

    @property
    def tool_registry(self) -> ToolExecutor:
        return MockToolExecutor()

    @property
    def auth_manager(self) -> Any:
        return MagicMock()

    @property
    def audit_logger(self) -> Any:
        return self._audit_logger

    @property
    def agent_executor(self) -> AgentExecutor:
        return MagicMock()


@pytest.mark.asyncio  # type: ignore
async def test_controller_passes_resume_snapshot(mock_user_context: UserContext) -> None:
    """
    Verify that WorkflowController.execute_recipe correctly propagates
    the 'resume_snapshot' argument to WorkflowRunner.run_workflow.
    """
    # Setup
    services = MockServiceRegistry()
    mock_topology = MagicMock()
    mock_runner = MagicMock()

    # Mock the async generator
    async def mock_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        # Yield nothing or dummy event
        if False:
            yield
        return

    mock_runner.run_workflow.side_effect = mock_stream
    MockRunnerCls = MagicMock(return_value=mock_runner)

    controller = WorkflowController(services, topology=mock_topology, runner_cls=MockRunnerCls)

    manifest = {
        "id": "resume-recipe",
        "version": "1.0.0",
        "name": "Resume Test",
        "inputs": {},
        "graph": {
            "nodes": [{"id": "A", "type": "agent", "agent_name": "A"}],
            "edges": [],
        },
    }

    inputs = {
        "trace_id": "t",
        "some_input": "val",
    }

    resume_snapshot = {
        "A": "Existing Output",
        "B": {"complex": "state"},
    }

    # Execute with resume_snapshot
    async for _ in controller.execute_recipe(
        manifest, inputs, context=mock_user_context, resume_snapshot=resume_snapshot
    ):
        pass

    # Verify run_workflow was called with correct arguments
    # WorkflowRunner.run_workflow(graph, context, resume_snapshot=..., initial_inputs=...)
    mock_runner.run_workflow.assert_called_once()

    call_kwargs = mock_runner.run_workflow.call_args.kwargs

    # Check if resume_snapshot was passed correctly
    assert "resume_snapshot" in call_kwargs
    assert call_kwargs["resume_snapshot"] == resume_snapshot

    # Check that inputs are passed as initial_inputs
    assert "initial_inputs" in call_kwargs
    assert call_kwargs["initial_inputs"] == inputs

    # Ensure snapshot didn't leak into inputs
    assert "resume_snapshot" not in inputs

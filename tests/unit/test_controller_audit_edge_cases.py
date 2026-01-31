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
from unittest.mock import AsyncMock, MagicMock

import pytest
from coreason_identity.models import UserContext

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, AuditLogger, ServiceRegistry, ToolExecutor
from coreason_maco.events.protocol import FeedbackManager, GraphEvent


class MockServiceRegistry(ServiceRegistry):
    def __init__(self) -> None:
        self._audit_logger = AsyncMock()

    @property
    def tool_registry(self) -> ToolExecutor:
        return MagicMock()

    @property
    def auth_manager(self) -> Any:
        return MagicMock()

    @property
    def audit_logger(self) -> AuditLogger:
        return self._audit_logger

    @property
    def agent_executor(self) -> AgentExecutor:
        return MagicMock()


@pytest.mark.asyncio  # type: ignore
async def test_input_sanitization_complex(mock_user_context: UserContext) -> None:
    """
    Verify that audit logging sanitization strictly removes specific keys
    but preserves others, including complex nested data.
    """
    services = MockServiceRegistry()
    mock_runner = MagicMock()

    # Empty generator
    async def empty_gen(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        if False:
            yield

    mock_runner.run_workflow.side_effect = empty_gen
    MockRunnerCls = MagicMock(return_value=mock_runner)

    controller = WorkflowController(services, runner_cls=MockRunnerCls)

    # Complex inputs
    complex_data = {"nested": {"key": "val"}, "list": [1, 2, 3]}
    feedback_manager = FeedbackManager()

    inputs = {
        "trace_id": "t",
        "feedback_manager": feedback_manager,  # Should be removed
        "secrets_map": {"api_key": "123"},  # Should be removed
        "complex_data": complex_data,  # Should be kept
        "simple_param": "foo",  # Should be kept
    }

    manifest = {
        "id": "audit-edge-recipe",
        "version": "1.0.0",
        "name": "Test",
        "inputs": {},
        "graph": {
            "nodes": [],
            "edges": [],
        },
    }

    async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        pass

    # Verify Audit Log call
    # Cast to Any or ignore type because AuditLogger protocol doesn't have assert_called_once
    logger_mock: Any = services.audit_logger
    logger_mock.log_workflow_execution.assert_called_once()
    call_args = logger_mock.log_workflow_execution.call_args
    logged_inputs = call_args.kwargs["inputs"]

    assert "feedback_manager" not in logged_inputs
    assert "secrets_map" not in logged_inputs
    assert "complex_data" in logged_inputs
    assert logged_inputs["complex_data"] == complex_data
    assert "simple_param" in logged_inputs


@pytest.mark.asyncio  # type: ignore
async def test_audit_logging_on_workflow_failure(mock_user_context: UserContext) -> None:
    """
    Verify that audit logs are written even if the workflow runner raises an exception.
    This ensures partial executions are audited for debugging/compliance.
    """
    services = MockServiceRegistry()
    mock_runner = MagicMock()

    # Generator that yields one event then raises Exception
    event = GraphEvent(
        event_type="NODE_START",
        run_id="run-fail",
        node_id="A",
        timestamp=1.0,
        payload={"node_id": "A"},
        visual_metadata={"state": "RUNNING"},
    )

    async def crashing_gen(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        yield event
        raise RuntimeError("Workflow Crashed")

    mock_runner.run_workflow.side_effect = crashing_gen
    MockRunnerCls = MagicMock(return_value=mock_runner)

    controller = WorkflowController(services, runner_cls=MockRunnerCls)
    manifest = {
        "id": "audit-crash-recipe",
        "version": "1.0.0",
        "name": "Crash Test",
        "inputs": {},
        "graph": {
            "nodes": [],
            "edges": [],
        },
    }
    inputs = {"trace_id": "t"}

    # We expect the exception to bubble up
    with pytest.raises(RuntimeError, match="Workflow Crashed"):
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass

    # CRITICAL: Audit logger should still be called with the events collected so far
    logger_mock: Any = services.audit_logger
    logger_mock.log_workflow_execution.assert_called_once()

    call_args = logger_mock.log_workflow_execution.call_args
    assert call_args.kwargs["run_id"] == "run-fail"
    assert len(call_args.kwargs["events"]) == 1
    assert call_args.kwargs["events"][0]["event_type"] == "NODE_START"

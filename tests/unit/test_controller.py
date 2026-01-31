# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import time
from typing import Any, AsyncGenerator
from unittest.mock import MagicMock

import pytest
from coreason_identity.models import UserContext
from pydantic import ValidationError

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, ServiceRegistry, ToolExecutor
from coreason_maco.engine.topology import CyclicDependencyError
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import FeedbackManager


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
async def test_controller_execution_flow(mock_user_context: UserContext) -> None:
    # Setup
    services = MockServiceRegistry()
    mock_topology = MagicMock()
    mock_runner = MagicMock()

    # Create mock events
    event1 = GraphEvent(
        event_type="NODE_START",
        run_id="test_run",
        node_id="A",
        timestamp=time.time(),
        payload={"node_id": "A", "status": "RUNNING"},
        visual_metadata={"state": "RUNNING"},
    )
    event2 = GraphEvent(
        event_type="NODE_DONE",
        run_id="test_run",
        node_id="A",
        timestamp=time.time(),
        payload={"node_id": "A", "status": "SUCCESS"},
        visual_metadata={"state": "SUCCESS"},
    )

    async def mock_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        yield event1
        yield event2

    mock_runner.run_workflow.side_effect = mock_stream

    MockRunnerCls = MagicMock(return_value=mock_runner)
    controller = WorkflowController(services, topology=mock_topology, runner_cls=MockRunnerCls)

    manifest = {
        "id": "test-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Test Recipe",
        "graph": {
            "nodes": [
                {"id": "A", "type": "agent", "agent_name": "AgentA"},
            ],
            "edges": [],
        },
    }

    inputs = {"user_id": "user123", "trace_id": "trace123", "secrets_map": {}}

    # Execute
    events = []
    async for event in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        events.append(event)

    # Assert
    assert len(events) == 2
    assert events[0] == event1
    assert events[1] == event2

    # Verify calls
    mock_topology.build_graph.assert_called_once()
    mock_runner.run_workflow.assert_called_once()
    services.audit_logger.log_workflow_execution.assert_called_once()


@pytest.mark.asyncio  # type: ignore
async def test_controller_missing_inputs(mock_user_context: UserContext) -> None:
    services = MockServiceRegistry()
    controller = WorkflowController(services)

    manifest: dict[str, Any] = {
        "id": "test-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Test Recipe",
        "graph": {
            "nodes": [],
            "edges": [],
        },
    }

    # Missing trace_id
    inputs = {"user_id": "123"}

    with pytest.raises(ValueError, match="trace_id is required"):
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_controller_invalid_manifest(mock_user_context: UserContext) -> None:
    services = MockServiceRegistry()
    controller = WorkflowController(services)

    # Missing 'graph' (was 'nodes')
    manifest: dict[str, Any] = {
        "name": "Test Recipe",
        "edges": [],
    }

    inputs = {"user_id": "u", "trace_id": "t"}

    with pytest.raises(ValidationError):
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_controller_topology_error(mock_user_context: UserContext) -> None:
    services = MockServiceRegistry()
    mock_topology = MagicMock()
    mock_topology.build_graph.side_effect = CyclicDependencyError("Cycle detected")
    controller = WorkflowController(services, topology=mock_topology)

    manifest = {
        "id": "cyclic-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Cyclic Recipe",
        "graph": {
            "nodes": [{"id": "A", "type": "agent", "agent_name": "A"}],
            "edges": [{"source_node_id": "A", "target_node_id": "A"}],
        },
    }
    inputs = {"user_id": "u", "trace_id": "t"}

    with pytest.raises(CyclicDependencyError, match="Cycle detected"):
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_controller_runtime_error(mock_user_context: UserContext) -> None:
    services = MockServiceRegistry()
    mock_runner = MagicMock()
    mock_runner.run_workflow.side_effect = Exception("Runtime Failure")
    MockRunnerCls = MagicMock(return_value=mock_runner)
    controller = WorkflowController(services, runner_cls=MockRunnerCls)

    manifest = {
        "id": "broken-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Broken Recipe",
        "graph": {
            "nodes": [{"id": "A", "type": "agent", "agent_name": "A"}],
            "edges": [],
        },
    }
    inputs = {"user_id": "u", "trace_id": "t"}

    with pytest.raises(Exception, match="Runtime Failure"):
        async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_controller_empty_graph(mock_user_context: UserContext) -> None:
    """Test valid manifest with 0 nodes runs without error (if topology allows)."""
    services = MockServiceRegistry()
    mock_topology = MagicMock()
    mock_runner = MagicMock()

    async def mock_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        if False:
            yield

    mock_runner.run_workflow.side_effect = mock_stream
    MockRunnerCls = MagicMock(return_value=mock_runner)
    controller = WorkflowController(services, topology=mock_topology, runner_cls=MockRunnerCls)

    manifest = {
        "id": "empty-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Empty Recipe",
        "graph": {
            "nodes": [],
            "edges": [],
        },
    }
    inputs = {"user_id": "u", "trace_id": "t"}

    events = []
    async for event in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        events.append(event)

    assert len(events) == 0
    mock_topology.build_graph.assert_called_once()
    mock_runner.run_workflow.assert_called_once()


@pytest.mark.asyncio  # type: ignore
async def test_controller_context_construction() -> None:
    """Verify ExecutionContext is built correctly from inputs."""
    services = MockServiceRegistry()
    mock_runner = MagicMock()
    mock_runner.run_workflow.return_value = MagicMock()  # Mock generator

    # We need to mock return value as an async iterable to avoid errors if iterated
    async def empty_gen(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        if False:
            yield

    mock_runner.run_workflow.side_effect = empty_gen

    MockRunnerCls = MagicMock(return_value=mock_runner)
    controller = WorkflowController(services, runner_cls=MockRunnerCls)

    manifest = {
        "id": "context-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Context Test",
        "graph": {
            "nodes": [{"id": "A", "type": "agent", "agent_name": "A"}],
            "edges": [],
        },
    }
    inputs = {
        "user_id": "specific_user",
        "trace_id": "specific_trace",
        "secrets_map": {"api_key": "123"},
    }

    context = UserContext(
        user_id="specific_user",
        email="specific@example.com",
        roles=[],
        metadata={},
    )

    async for _ in controller.execute_recipe(manifest, inputs, context=context):
        pass

    # Verify run_workflow was called with correct context
    call_args = mock_runner.run_workflow.call_args
    assert call_args is not None
    # args[0] is graph, args[1] is context. But since we use position or keyword...
    # run_workflow(graph, context, ...) - we need to check how it was called.
    # The actual call in controller is:
    # runner.run_workflow(graph, context, resume_snapshot=resume_snapshot, initial_inputs=inputs)

    # We can inspect args
    args, kwargs = call_args
    # args[0] is graph, args[1] is context
    context_arg = args[1]

    assert context_arg.user_id == "specific_user"
    assert context_arg.trace_id == "specific_trace"
    assert context_arg.secrets_map == {"api_key": "123"}
    # Verify tool registry is from services
    assert isinstance(context_arg.tool_registry, MockToolExecutor)
    # agent_executor is no longer in context


@pytest.mark.asyncio  # type: ignore
async def test_controller_no_audit_logger(mock_user_context: UserContext) -> None:
    """Test controller execution when audit_logger is None."""
    services = MockServiceRegistry()
    services._audit_logger = None  # type: ignore

    mock_runner = MagicMock()
    mock_runner.run_workflow.return_value = MagicMock()

    async def empty_gen(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        if False:
            yield

    mock_runner.run_workflow.side_effect = empty_gen
    MockRunnerCls = MagicMock(return_value=mock_runner)

    controller = WorkflowController(services, runner_cls=MockRunnerCls)

    manifest = {
        "id": "no-audit-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "No Audit",
        "graph": {
            "nodes": [],
            "edges": [],
        },
    }
    inputs = {"user_id": "u", "trace_id": "t"}

    async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        pass

    # Should run without error and just skip logging
    mock_runner.run_workflow.assert_called_once()


@pytest.mark.asyncio  # type: ignore
async def test_controller_feedback_injection(mock_user_context: UserContext) -> None:
    """Test injecting feedback_manager via inputs."""
    services = MockServiceRegistry()
    mock_runner = MagicMock()
    mock_runner.run_workflow.return_value = MagicMock()

    async def empty_gen(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        if False:
            yield

    mock_runner.run_workflow.side_effect = empty_gen
    MockRunnerCls = MagicMock(return_value=mock_runner)

    controller = WorkflowController(services, runner_cls=MockRunnerCls)

    manifest = {
        "id": "feedback-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Feedback Test",
        "graph": {
            "nodes": [],
            "edges": [],
        },
    }

    # Mock FeedbackManager
    feedback_manager = FeedbackManager()
    inputs = {"user_id": "u", "trace_id": "t", "feedback_manager": feedback_manager}

    async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        pass

    # Verify context has feedback_manager
    call_args = mock_runner.run_workflow.call_args
    context_arg = call_args[0][1]
    assert context_arg.feedback_manager is feedback_manager


@pytest.mark.asyncio  # type: ignore
async def test_controller_context_var_propagation(mock_user_context: UserContext) -> None:
    """Verify that request_id_var is set correctly during execution."""
    from coreason_maco.utils.context import request_id_var

    services = MockServiceRegistry()
    mock_runner = MagicMock()

    # Check context var inside the execution
    async def mock_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
        assert request_id_var.get() == "trace-123"
        yield GraphEvent(
            event_type="NODE_START",
            run_id="test_run",
            node_id="A",
            timestamp=0.0,
            payload={"node_id": "A", "status": "OK"},
            visual_metadata={"state": "START"},
        )

    mock_runner.run_workflow.side_effect = mock_stream
    MockRunnerCls = MagicMock(return_value=mock_runner)

    controller = WorkflowController(services, runner_cls=MockRunnerCls)

    manifest = {
        "id": "ctx-recipe",
        "version": "1.0.0",
        "inputs": {},
        "name": "Ctx Test",
        "graph": {
            "nodes": [],
            "edges": [],
        },
    }
    inputs = {"user_id": "u", "trace_id": "trace-123"}

    async for _ in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        pass

    # Verify it is reset
    assert request_id_var.get() == ""

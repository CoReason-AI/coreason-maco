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
from pydantic import ValidationError

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import ServiceRegistry, ToolRegistry
from coreason_maco.events.protocol import GraphEvent


class MockToolRegistry(ToolRegistry):
    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        return "mock_result"


class MockServiceRegistry(ServiceRegistry):
    @property
    def tool_registry(self) -> ToolRegistry:
        return MockToolRegistry()

    @property
    def auth_manager(self) -> Any:
        return MagicMock()

    @property
    def audit_logger(self) -> Any:
        return MagicMock()


@pytest.mark.asyncio  # type: ignore
async def test_controller_execution_flow() -> None:
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

    controller = WorkflowController(services, topology=mock_topology, runner=mock_runner)

    manifest = {
        "name": "Test Recipe",
        "nodes": [
            {"id": "A", "type": "LLM", "config": {"mock_output": "Output A"}},
        ],
        "edges": [],
    }

    inputs = {"user_id": "user123", "trace_id": "trace123", "secrets_map": {}}

    # Execute
    events = []
    async for event in controller.execute_recipe(manifest, inputs):
        events.append(event)

    # Assert
    assert len(events) == 2
    assert events[0] == event1
    assert events[1] == event2

    # Verify calls
    mock_topology.build_graph.assert_called_once()
    mock_runner.run_workflow.assert_called_once()


@pytest.mark.asyncio  # type: ignore
async def test_controller_missing_inputs() -> None:
    services = MockServiceRegistry()
    controller = WorkflowController(services)

    manifest: dict[str, Any] = {
        "name": "Test Recipe",
        "nodes": [],
        "edges": [],
    }

    # Missing user_id
    inputs = {"trace_id": "123"}

    with pytest.raises(ValueError, match="user_id is required"):
        async for _ in controller.execute_recipe(manifest, inputs):
            pass

    # Missing trace_id
    inputs = {"user_id": "123"}

    with pytest.raises(ValueError, match="trace_id is required"):
        async for _ in controller.execute_recipe(manifest, inputs):
            pass


@pytest.mark.asyncio  # type: ignore
async def test_controller_invalid_manifest() -> None:
    services = MockServiceRegistry()
    controller = WorkflowController(services)

    # Missing 'nodes'
    manifest: dict[str, Any] = {
        "name": "Test Recipe",
        "edges": [],
    }

    inputs = {"user_id": "u", "trace_id": "t"}

    with pytest.raises(ValidationError):
        async for _ in controller.execute_recipe(manifest, inputs):
            pass

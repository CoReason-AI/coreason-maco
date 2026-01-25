from unittest.mock import AsyncMock, MagicMock

import pytest

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, AuditLogger, ServiceRegistry, ToolExecutor


@pytest.mark.asyncio  # type: ignore
async def test_audit_logging_integration() -> None:
    # Mocks
    mock_audit_logger = AsyncMock(spec=AuditLogger)

    mock_services = MagicMock(spec=ServiceRegistry)
    # Important: Property mock needs to return the AsyncMock
    # Since ServiceRegistry defines audit_logger as a property, we mock it as an attribute on the instance
    # or use PropertyMock if we were mocking the class.
    # Here mock_services is an instance of MagicMock, so we just set the attribute.
    mock_services.audit_logger = mock_audit_logger
    mock_services.tool_registry = MagicMock(spec=ToolExecutor)

    mock_agent_executor = MagicMock(spec=AgentExecutor)
    # Mock invoke to return something valid
    mock_response = MagicMock()
    mock_response.content = "mock content"
    mock_response.metadata = {}
    mock_agent_executor.invoke = AsyncMock(return_value=mock_response)

    mock_services.agent_executor = mock_agent_executor

    # Workflow setup
    controller = WorkflowController(services=mock_services)

    manifest = {"name": "Test Workflow", "nodes": [{"id": "node1", "type": "DEFAULT"}], "edges": []}
    inputs = {"user_id": "user123", "trace_id": "trace456"}

    # Run
    events = []
    async for event in controller.execute_recipe(manifest, inputs):
        events.append(event)

    # Verify Audit Log called
    assert mock_audit_logger.log_workflow_execution.called

    call_args = mock_audit_logger.log_workflow_execution.call_args
    assert call_args is not None
    kwargs = call_args.kwargs

    assert kwargs["trace_id"] == "trace456"
    assert kwargs["manifest"] == manifest
    assert kwargs["inputs"] == inputs
    assert len(kwargs["events"]) == len(events)

    # Check that events are passed as dicts (model_dump)
    assert isinstance(kwargs["events"][0], dict)
    assert kwargs["events"][0]["node_id"] == "node1"

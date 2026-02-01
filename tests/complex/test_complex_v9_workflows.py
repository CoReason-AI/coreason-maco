from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from coreason_identity.models import UserContext

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentExecutor, AgentResponse, ServiceRegistry, ToolExecutor
from coreason_maco.events.protocol import GraphEvent


class MockComplexAgentExecutor(AgentExecutor):
    async def invoke(self, prompt: str, model_config: Dict[str, Any]) -> AgentResponse:
        # Mock logic based on agent_name or model
        name = model_config.get("agent_name") or model_config.get("model", "unknown")

        content = f"Response from {name}"

        if "Original Query:" in prompt:  # Synthesis
            content = "Consensus Reached"

        response = MagicMock()
        response.content = content
        return response

    def stream(self, prompt: str, model_config: Dict[str, Any]) -> Any:
        # Not used
        pass


class MockComplexToolExecutor(ToolExecutor):
    async def execute(self, tool_name: str, args: Dict[str, Any], user_context: Any = None) -> Any:
        return f"Tool {tool_name} Result"


class MockComplexRegistry(ServiceRegistry):
    def __init__(self) -> None:
        self._agent = MockComplexAgentExecutor()
        self._tool = MockComplexToolExecutor()
        self._audit = MagicMock()
        self._audit.log_workflow_execution = MagicMock()  # Needs to be awaitable? No, protocol is async def

        async def log(*args: Any, **kwargs: Any) -> None:
            pass

        self._audit.log_workflow_execution.side_effect = log

    @property
    def tool_registry(self) -> ToolExecutor:
        return self._tool

    @property
    def auth_manager(self) -> Any:
        return MagicMock()

    @property
    def audit_logger(self) -> Any:
        return self._audit

    @property
    def agent_executor(self) -> AgentExecutor:
        return self._agent


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_complex_v9_workflow(mock_user_context: UserContext) -> None:
    services = MockComplexRegistry()
    controller = WorkflowController(services)

    manifest = {
        "id": "complex-v9",
        "version": "1.0.0",
        "name": "Complex V9",
        "topology": {
            "nodes": [
                {
                    "id": "Start",
                    "type": "agent",
                    "agent_name": "Initiator",
                    "visual": {"x_y_coordinates": [0, 0], "label": "Start", "icon": "box"},
                },
                {
                    "id": "Process",
                    "type": "logic",
                    "code": "DataProcessor",
                    "visual": {"x_y_coordinates": [0, 0], "label": "Logic", "icon": "code"},
                },
                {
                    "id": "ReviewCouncil",
                    "type": "agent",
                    "agent_name": "Chair",
                    "council_config": {"voters": ["VoterA", "VoterB"], "strategy": "consensus"},
                    "visual": {"x_y_coordinates": [0, 0], "label": "Council", "icon": "users"},
                },
                {
                    "id": "End",
                    "type": "agent",
                    "agent_name": "Finalizer",
                    "visual": {"x_y_coordinates": [0, 0], "label": "End", "icon": "flag"},
                },
            ],
            "edges": [
                {"source_node_id": "Start", "target_node_id": "Process"},
                {"source_node_id": "Process", "target_node_id": "ReviewCouncil"},
                {"source_node_id": "ReviewCouncil", "target_node_id": "End"},
            ],
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
    }
    inputs = {"trace_id": "t"}

    events: List[GraphEvent] = []
    async for event in controller.execute_recipe(manifest, inputs, context=mock_user_context):
        events.append(event)

    # Verification
    node_ids = [e.node_id for e in events if e.event_type == "NODE_DONE"]
    assert "Start" in node_ids
    assert "Process" in node_ids
    assert "ReviewCouncil" in node_ids
    assert "End" in node_ids

    # Verify Council Execution
    vote_event = next(e for e in events if e.event_type == "COUNCIL_VOTE")
    assert vote_event.node_id == "ReviewCouncil"
    # Mock executor returns "Response from {name}"
    assert vote_event.payload["votes"]["VoterA"] == "Response from VoterA"
    assert vote_event.payload["votes"]["VoterB"] == "Response from VoterB"

    # Verify outputs passed
    # This is implicit if execution order is correct and no crashes

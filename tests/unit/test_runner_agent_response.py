from dataclasses import dataclass
from typing import Any, Dict, List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


@dataclass
class MockAgentResponse:
    content: str
    metadata: Dict[str, Any]


@pytest.fixture
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


@pytest.mark.asyncio
async def test_agent_response_legacy_string_match(mock_context: ExecutionContext) -> None:
    """
    Test that the runner correctly unwraps an AgentResponse object
    when a legacy simple string condition is used.

    A (returns AgentResponse(content="yes")) -> B (condition="yes")

    Expected: B is executed.
    """
    G = nx.DiGraph()
    # Node A returns an AgentResponse-like object
    response = MockAgentResponse(content="yes", metadata={"tokens": 10})
    G.add_node("A", mock_output=response)
    G.add_node("B")

    # Legacy condition: expecting strict string match
    G.add_edge("A", "B", condition="yes")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}

    # Should run A
    assert "A" in executed_nodes
    # Should run B (because "yes" == response.content)
    assert "B" in executed_nodes


@pytest.mark.asyncio
async def test_agent_response_jinja_access(mock_context: ExecutionContext) -> None:
    """
    Test that the runner passes the FULL AgentResponse object to Jinja.

    A (returns AgentResponse(content="yes", metadata={"tokens": 100})) -> B
    Condition: {{ A.metadata.tokens > 50 }}

    Expected: B is executed.
    """
    G = nx.DiGraph()
    response = MockAgentResponse(content="yes", metadata={"tokens": 100})
    G.add_node("A", mock_output=response)
    G.add_node("B")

    # Jinja condition accessing metadata
    G.add_edge("A", "B", condition="{{ A.metadata.tokens > 50 }}")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}

    assert "A" in executed_nodes
    assert "B" in executed_nodes

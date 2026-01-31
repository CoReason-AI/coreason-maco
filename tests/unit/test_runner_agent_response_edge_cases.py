from dataclasses import dataclass
from typing import Any, Dict, List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


@dataclass
class MockAgentResponse:
    content: Any  # Can be non-string for testing
    metadata: Dict[str, Any]


@dataclass
class PlainObject:
    data: str


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


@pytest.mark.asyncio  # type: ignore
async def test_agent_response_non_string_content(mock_context: ExecutionContext) -> None:
    """
    Test 1: AgentResponse.content is not a string (e.g. int).
    It should be automatically cast to string for the legacy condition check.
    """
    G = nx.DiGraph()
    response = MockAgentResponse(content=123, metadata={})
    G.add_node("A", mock_output=response)
    G.add_node("B")

    # Legacy condition expecting string "123"
    G.add_edge("A", "B", condition="123")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}
    assert "A" in executed_nodes
    assert "B" in executed_nodes


@pytest.mark.asyncio  # type: ignore
async def test_jinja_deep_metadata_access(mock_context: ExecutionContext) -> None:
    """
    Test 2: Deeply nested metadata access in Jinja.
    """
    G = nx.DiGraph()
    response = MockAgentResponse(content="ok", metadata={"usage": {"total_tokens": 150, "cost": 0.02}})
    G.add_node("A", mock_output=response)
    G.add_node("B")

    G.add_edge("A", "B", condition="{{ A.metadata.usage.total_tokens > 100 }}")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}
    assert "B" in executed_nodes


@pytest.mark.asyncio  # type: ignore
async def test_mixed_types_graph(mock_context: ExecutionContext) -> None:
    """
    Test 3: Graph with mixed node outputs (Simple String vs AgentResponse).
    """
    G = nx.DiGraph()
    G.add_node("Root", mock_output="start")
    G.add_node("SimpleNode", mock_output="simple_val")
    G.add_node("AgentNode", mock_output=MockAgentResponse(content="agent_val", metadata={}))
    G.add_node("EndSimple")
    G.add_node("EndAgent")

    G.add_edge("Root", "SimpleNode")
    G.add_edge("Root", "AgentNode")

    # Simple node -> String Match
    G.add_edge("SimpleNode", "EndSimple", condition="simple_val")
    # Agent node -> String Match (unwrapped)
    G.add_edge("AgentNode", "EndAgent", condition="agent_val")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}
    assert "SimpleNode" in executed_nodes
    assert "AgentNode" in executed_nodes
    assert "EndSimple" in executed_nodes
    assert "EndAgent" in executed_nodes


@pytest.mark.asyncio  # type: ignore
async def test_missing_content_attribute_fallback(mock_context: ExecutionContext) -> None:
    """
    Test 4: Output object does NOT have 'content' attribute.
    Should fallback to str(object) comparison.
    """
    G = nx.DiGraph()
    # Plain object, str() representation might be unpredictable unless defined,
    # so we rely on the object instance string or use a string directly.
    # Let's use a dict, str(dict) is predictable.
    output_obj = {"key": "value"}
    G.add_node("A", mock_output=output_obj)
    G.add_node("B")

    # Condition matches str(dict) EXACTLY
    G.add_edge("A", "B", condition=str(output_obj))

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}
    assert "B" in executed_nodes


@pytest.mark.asyncio  # type: ignore
async def test_jinja_error_safety(mock_context: ExecutionContext) -> None:
    """
    Test 5: Jinja expression accessing non-existent key.
    Should NOT crash, but evaluate to False (safe default).
    """
    G = nx.DiGraph()
    response = MockAgentResponse(content="yes", metadata={})
    G.add_node("A", mock_output=response)
    G.add_node("B")

    # Accessing non-existent 'usage' key
    # In Jinja, undefined variables print empty string by default, or if strict, raise error.
    # Our PreserveUndefined might behave specifically.
    # If it raises error, evaluate_boolean catches it and returns False.
    # If it returns Undefined object, the comparison might be False.
    # Let's ensure it doesn't crash.
    G.add_edge("A", "B", condition="{{ A.metadata.usage.total_tokens > 100 }}")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}
    # B should be skipped because condition is False (or Error -> False)
    assert "B" not in executed_nodes

    # Verify no crash (A finished)
    assert "A" in executed_nodes

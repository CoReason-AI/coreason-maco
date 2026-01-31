import asyncio
from typing import Any, Dict

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


@pytest.mark.asyncio  # type: ignore
async def test_input_injection_resolution(mock_context: ExecutionContext) -> None:
    """
    Test that inputs provided to run_workflow are available for resolution
    in node configuration.
    """
    graph = nx.DiGraph()
    # Node config uses {{ user_name }} which should come from inputs
    graph.add_node("A", config={"prompt": "Hello {{ user_name }}"})

    runner = WorkflowRunner()

    # Mocking DefaultNodeHandler to return the config['prompt']
    async def mock_execute(
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        return config.get("prompt")

    runner.default_handler.execute = mock_execute  # type: ignore

    initial_inputs = {"user_name": "Alice"}

    events = []
    async for event in runner.run_workflow(graph, mock_context, initial_inputs=initial_inputs):
        if event.event_type == "NODE_DONE":
            events.append(event)

    assert len(events) == 1
    assert events[0].payload["output_summary"] == "Hello Alice"


@pytest.mark.asyncio  # type: ignore
async def test_input_injection_precedence(mock_context: ExecutionContext) -> None:
    """
    Test that if a node output and an input share the same name,
    VariableResolver priority depends on how node_outputs is updated.

    Currently, inputs are added at start. If a node executes and overwrites it,
    subsequent nodes should see the node output.
    """
    graph = nx.DiGraph()
    # Node "var" produces "NodeValue"
    # Node "B" consumes {{ var }}
    graph.add_edge("var", "B")

    graph.nodes["var"]["config"] = {}
    graph.nodes["B"]["config"] = {"prompt": "Value: {{ var }}"}

    runner = WorkflowRunner()

    async def mock_execute(
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        if node_id == "var":
            return "NodeValue"
        return config.get("prompt")

    runner.default_handler.execute = mock_execute  # type: ignore

    # Initial input "var" is "InputValue"
    initial_inputs = {"var": "InputValue"}

    events = []
    async for event in runner.run_workflow(graph, mock_context, initial_inputs=initial_inputs):
        if event.event_type == "NODE_DONE" and event.node_id == "B":
            events.append(event)

    # Logic:
    # 1. node_outputs initialized with {"var": "InputValue"}
    # 2. Node "var" executes. Its output is "NodeValue".
    # 3. node_outputs["var"] is updated to "NodeValue".
    # 4. Node "B" resolves {{ var }}. It should see "NodeValue".

    assert len(events) == 1
    assert events[0].payload["output_summary"] == "Value: NodeValue"

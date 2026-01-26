# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    agent_executor = MagicMock()

    # Mock invoke just echoes
    async def mock_invoke(prompt: str, config: Any) -> Any:
        response = MagicMock()
        response.content = f"Echo: {prompt}"
        return response

    agent_executor.invoke = AsyncMock(side_effect=mock_invoke)

    # Mock tool registry
    async def mock_execute(name: str, args: Dict[str, Any]) -> Any:
        # Return the args so we can inspect what was injected
        return args

    tool_registry = MagicMock()
    tool_registry.execute = AsyncMock(side_effect=mock_execute)

    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=tool_registry,
    )


@pytest.mark.asyncio  # type: ignore
async def test_multiple_variables_in_string(mock_context: ExecutionContext) -> None:
    """
    Test injecting two variables into one string: "{{ A }} and {{ B }}".
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="TASK", mock_output="Alpha")
    graph.add_node("B", type="TASK", mock_output="Beta")
    graph.add_node("C", type="TOOL", config={"tool_name": "test", "args": {"input": "{{ A }} and {{ B }}"}})
    graph.add_edge("A", "C")
    graph.add_edge("B", "C")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_c = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "C")
    # Output of tool is the args dict
    # We look at the string representation in output_summary, or we rely on the fact
    # that if it ran successfully, the mock returned args.
    # The output summary is `str(output)`.
    assert "'input': 'Alpha and Beta'" in node_c.payload["output_summary"]


@pytest.mark.asyncio  # type: ignore
async def test_unknown_variable_remains(mock_context: ExecutionContext) -> None:
    """
    Test referencing a non-existent variable: "{{ UNKNOWN }}".
    It should remain unresolved in the string.
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="TOOL", config={"tool_name": "test", "args": {"input": "Hello {{ UNKNOWN }}"}})

    runner = WorkflowRunner()
    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_a = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "A")
    assert "'input': 'Hello {{ UNKNOWN }}'" in node_a.payload["output_summary"]


@pytest.mark.asyncio  # type: ignore
async def test_special_characters_in_node_id(mock_context: ExecutionContext) -> None:
    """
    Test node IDs with hyphens and underscores: "{{ my-node_1 }}".
    """
    graph = nx.DiGraph()
    node_id = "my-node_1"
    graph.add_node(node_id, type="TASK", mock_output="Special")
    graph.add_node("B", type="TOOL", config={"tool_name": "test", "args": {"input": f"{{{{ {node_id} }}}}"}})
    graph.add_edge(node_id, "B")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_b = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "B")
    assert "'input': 'Special'" in node_b.payload["output_summary"]


@pytest.mark.asyncio  # type: ignore
async def test_deeply_nested_structure(mock_context: ExecutionContext) -> None:
    """
    Test injection in a nested list of dicts.
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="TASK", mock_output="ValueA")

    complex_args = {"list": [{"key": "{{ A }}"}, "Just {{ A }}", ["Nested", "{{ A }}"]], "meta": "{{ A }}"}

    graph.add_node("B", type="TOOL", config={"tool_name": "test", "args": complex_args})
    graph.add_edge("A", "B")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_b = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "B")
    summary = node_b.payload["output_summary"]

    # Check replacements
    assert "'key': 'ValueA'" in summary
    assert "'Just ValueA'" in summary
    assert "'Nested', 'ValueA'" in summary


@pytest.mark.asyncio  # type: ignore
async def test_inject_none_value(mock_context: ExecutionContext) -> None:
    """
    Test injecting a None value.
    If partial string: "Value is {{ A }}", A=None -> "Value is None"
    If exact match: "{{ A }}", A=None -> input=None
    """
    graph = nx.DiGraph()
    graph.add_node("A", type="TASK", mock_output=None)

    # 1. Exact match
    graph.add_node(
        "B", type="TOOL", config={"tool_name": "test", "args": {"exact": "{{ A }}", "partial": "Val: {{ A }}"}}
    )
    graph.add_edge("A", "B")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []
    async for event in runner.run_workflow(graph, mock_context):
        events.append(event)

    node_b = next(e for e in events if e.event_type == "NODE_DONE" and e.node_id == "B")
    summary = node_b.payload["output_summary"]

    # Check exact match is None (not string "None")
    # verification via string repr is tricky, "None" vs None.
    # But Python repr for dict {'exact': None} is "{'exact': None, ...}"
    assert "'exact': None" in summary

    # Check partial
    assert "'partial': 'Val: None'" in summary

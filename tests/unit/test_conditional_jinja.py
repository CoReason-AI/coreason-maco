from typing import List

import networkx as nx
import pytest

from coreason_maco.engine.resolver import VariableResolver
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
async def test_jinja_condition_complex(mock_context: ExecutionContext) -> None:
    """
    Test branching with Jinja2 expression:
    A -> B (cond="{{ A.score > 50 }}")
    A -> C (cond="{{ A.score <= 50 }}")
    A returns {"score": 60}.
    Expected: A runs, B runs (condition met), C skipped.
    """
    G = nx.DiGraph()
    # A returns a dict
    G.add_node("A", mock_output={"score": 60})
    G.add_node("B")
    G.add_node("C")

    # Use Jinja syntax for conditions.
    # Note: 'A' refers to the node ID in the context.
    G.add_edge("A", "B", condition="{{ A.score > 50 }}")
    G.add_edge("A", "C", condition="{{ A.score <= 50 }}")

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    async for event in runner.run_workflow(G, mock_context):
        events.append(event)

    executed_nodes = {e.node_id for e in events if e.event_type == "NODE_DONE"}
    skipped_nodes = {e.node_id for e in events if e.event_type == "NODE_SKIPPED"}

    assert "A" in executed_nodes
    assert "B" in executed_nodes
    assert "C" in skipped_nodes or "C" not in executed_nodes


def test_evaluate_boolean_error_handling() -> None:
    """
    Test that evaluate_boolean returns False on Jinja2 errors.
    """
    resolver = VariableResolver()
    # Syntax error in Jinja
    result = resolver.evaluate_boolean("{{ 1 + }}", {})
    assert result is False

    # Exception during rendering (e.g. division by zero, though jinja might handle it, let's try strict error)
    # Actually TemplateSyntaxError is easier to trigger.
    # "{{ 1 + }}" is a syntax error.

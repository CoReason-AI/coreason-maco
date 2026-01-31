from typing import Any, List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


@pytest.fixture  # type: ignore
def context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry={},
    )


class CrashingHandler:
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        raise ValueError("Simulated Crash")


@pytest.mark.asyncio  # type: ignore
async def test_node_execution_exception(context: ExecutionContext) -> None:
    """
    Test that an exception in a node handler is caught, emitted as ERROR,
    and then re-raised to stop the workflow.
    Also covers lines 175-179 (except Exception in execution_task).
    """
    runner = WorkflowRunner()
    # Inject crashing handler
    runner.handlers["CRASH"] = CrashingHandler()

    G = nx.DiGraph()
    G.add_node("A", type="CRASH")

    events: List[GraphEvent] = []

    # Add sensitive inputs to test sanitization
    initial_inputs = {
        "user_context": "sensitive_token",
        "downstream_token": "secret",
        "safe_list": ["a", "b"],
        "safe_dict": {"key": "value"},
    }

    with pytest.raises(ExceptionGroup) as exc_info:  # Python 3.11+ TaskGroup raises ExceptionGroup
        async for event in runner.run_workflow(G, context, initial_inputs=initial_inputs):
            events.append(event)

    # Check that error event was emitted before crash
    error_events = [e for e in events if e.event_type == "ERROR"]
    assert len(error_events) == 1
    payload = error_events[0].payload
    assert "Simulated Crash" in payload["error_message"]

    # Verify sanitization
    snapshot = payload["input_snapshot"]
    assert "user_context" not in snapshot
    assert "downstream_token" not in snapshot
    assert "safe_list" in snapshot
    assert snapshot["safe_list"] == ["a", "b"]

    # Check that exception bubbled up
    # ExceptionGroup will contain ValueError
    # Inspect exceptions in the group
    assert any("Simulated Crash" in str(e) for e in exc_info.value.exceptions)


@pytest.mark.asyncio  # type: ignore
async def test_consumer_cancellation(context: ExecutionContext) -> None:
    """
    Test consumer breaking the loop early.
    Covers lines 191-198 (GeneratorExit handling).
    """
    runner = WorkflowRunner()
    G = nx.DiGraph()
    G.add_node("A", mock_output="A")
    G.add_node("B", mock_output="B")
    G.add_edge("A", "B")

    events: List[GraphEvent] = []

    # Run only partially
    gen = runner.run_workflow(G, context)
    try:
        async for event in gen:
            events.append(event)
            if event.event_type == "NODE_START" and event.node_id == "A":
                break  # Cancel consumer
    finally:
        # Verify generator cleanup happens without error
        await gen.aclose()

    assert len(events) > 0

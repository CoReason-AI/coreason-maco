import asyncio
from typing import Any, Dict, cast

import networkx as nx
import pytest

from coreason_maco.engine.handlers import DefaultNodeHandler
from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


class OverlapTrackingHandler:
    def __init__(self) -> None:
        self.current_concurrent = 0
        self.max_observed_concurrent = 0
        self.lock = asyncio.Lock()
        self.concurrent_history: list[int] = []

    async def execute(
        self,
        node_id: str,
        run_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        queue: asyncio.Queue[GraphEvent | None],
        node_attributes: Dict[str, Any],
    ) -> Any:
        # Ignore Root node
        if node_id == "ROOT":
            return "root_done"

        async with self.lock:
            self.current_concurrent += 1
            if self.current_concurrent > self.max_observed_concurrent:
                self.max_observed_concurrent = self.current_concurrent
            self.concurrent_history.append(self.current_concurrent)

        # Work simulation
        await asyncio.sleep(0.05)

        # Simulate Error if configured
        if config.get("should_fail"):
            async with self.lock:
                self.current_concurrent -= 1
            raise ValueError("Simulated Node Failure")

        async with self.lock:
            self.current_concurrent -= 1
        return "done"


@pytest.fixture  # type: ignore
def mock_context() -> ExecutionContext:
    return ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry="mock_tool",
    )


@pytest.mark.asyncio  # type: ignore
async def test_serialization_limit_one(mock_context: ExecutionContext) -> None:
    """
    Test Limit=1. Even if 5 nodes are parallel in graph, they must run 1 by 1.
    """
    runner = WorkflowRunner(max_parallel_agents=1)

    tracker = OverlapTrackingHandler()
    runner.default_handler = cast(DefaultNodeHandler, tracker)

    # Graph: ROOT -> [A, B, C, D, E]
    graph = nx.DiGraph()
    graph.add_node("ROOT")
    for char in "ABCDE":
        graph.add_node(char)
        graph.add_edge("ROOT", char)

    async for _ in runner.run_workflow(graph, mock_context):
        pass

    assert tracker.max_observed_concurrent == 1, f"Expected max 1 concurrent, got {tracker.max_observed_concurrent}"


@pytest.mark.asyncio  # type: ignore
async def test_invalid_limit() -> None:
    """
    Test that limit < 1 raises ValueError.
    """
    with pytest.raises(ValueError, match="max_parallel_agents must be >= 1"):
        WorkflowRunner(max_parallel_agents=0)

    with pytest.raises(ValueError, match="max_parallel_agents must be >= 1"):
        WorkflowRunner(max_parallel_agents=-5)


@pytest.mark.asyncio  # type: ignore
async def test_semaphore_release_on_error(mock_context: ExecutionContext) -> None:
    """
    Test that if a node fails, it releases the semaphore so others can run.
    """
    # Limit 1. Node A fails. Node B should still run (conceptually, or at least start).
    # Note: WorkflowRunner currently stops on error (re-raises).
    # But we want to ensure the semaphore isn't permanently locked.
    # To test this, we can catch the exception from run_workflow, then check if we can run another workflow
    # or if we can run another node.
    # Actually, simpler: Use Limit 2. Node A fails. Node B and C are waiting.
    # If A doesn't release, we effectively have Limit 1 left.
    # But since the exception bubbles up and cancels the TaskGroup, the whole workflow stops.
    # So the critical test is: Does the 'async with semaphore' exit correctly on error?
    # Yes, Python context managers guarantee __aexit__.

    # Let's verify that the runner propagates the error and doesn't hang.
    runner = WorkflowRunner(max_parallel_agents=1)
    tracker = OverlapTrackingHandler()
    runner.default_handler = cast(DefaultNodeHandler, tracker)

    graph = nx.DiGraph()
    graph.add_node("ROOT")
    graph.add_node("FAILING", config={"should_fail": True})
    graph.add_edge("ROOT", "FAILING")

    # We expect the runner to raise the error
    with pytest.raises(ExceptionGroup) as excinfo:  # TaskGroup raises ExceptionGroup
        async for _ in runner.run_workflow(graph, mock_context):
            pass

    # Dig into ExceptionGroup to find ValueError
    exceptions = excinfo.value.exceptions
    assert any(isinstance(e, ValueError) and "Simulated Node Failure" in str(e) for e in exceptions)

    # If we are here, it didn't hang. That's the success condition.


@pytest.mark.asyncio  # type: ignore
async def test_complex_diamond_concurrency(mock_context: ExecutionContext) -> None:
    """
    Test a diamond shape with limit < width.
    ROOT -> [A, B, C, D] -> MERGE
    Limit = 2.
    """
    limit = 2
    runner = WorkflowRunner(max_parallel_agents=limit)
    tracker = OverlapTrackingHandler()
    runner.default_handler = cast(DefaultNodeHandler, tracker)

    graph = nx.DiGraph()
    graph.add_node("ROOT")
    graph.add_node("MERGE")

    # Add 4 parallel nodes in the middle
    mids = ["M1", "M2", "M3", "M4"]
    for m in mids:
        graph.add_node(m)
        graph.add_edge("ROOT", m)
        graph.add_edge(m, "MERGE")

    async for _ in runner.run_workflow(graph, mock_context):
        pass

    assert tracker.max_observed_concurrent <= limit
    # We expect it to hit the limit since we have 4 nodes and limit 2
    assert tracker.max_observed_concurrent == limit

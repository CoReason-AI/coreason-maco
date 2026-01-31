import asyncio
from typing import Any, Dict, cast

import networkx as nx
import pytest

from coreason_maco.engine.handlers import DefaultNodeHandler
from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.utils.context import ExecutionContext


class ConcurrencyTrackingHandler:
    def __init__(self) -> None:
        self.current_concurrent = 0
        self.max_observed_concurrent = 0
        # Use a lock to safely update counters
        self.lock = asyncio.Lock()

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

        # Sleep to ensure overlap if concurrency is allowed
        await asyncio.sleep(0.05)

        async with self.lock:
            self.current_concurrent -= 1
        return "done"


@pytest.mark.asyncio  # type: ignore
async def test_concurrency_limit_enforcement() -> None:
    """
    Verifies that the runner respects the max_parallel_agents limit.
    """
    limit = 3
    num_nodes = 10

    try:
        runner = WorkflowRunner(max_parallel_agents=limit)
    except TypeError:
        pytest.fail("WorkflowRunner does not accept max_parallel_agents yet.")

    tracking_handler = ConcurrencyTrackingHandler()
    runner.handlers["TEST"] = tracking_handler
    # Also override DEFAULT just in case, though we set type to TEST
    # We cast to avoid mypy error because tracking_handler is duck-typed compatible
    # but not explicitly inheriting. Since NodeHandler is a Protocol, it should be fine
    # if I typed tracking_handler correctly. But default_handler is likely inferred as strict class.
    runner.default_handler = cast(DefaultNodeHandler, tracking_handler)

    # Build a graph with 1 Root and 10 parallel children
    graph = nx.DiGraph()
    graph.add_node("ROOT", type="TEST", config={})
    for i in range(num_nodes):
        node_id = f"node_{i}"
        graph.add_node(node_id, type="TEST", config={})
        graph.add_edge("ROOT", node_id)

    context = ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry="mock_tool_registry",
    )

    # Run workflow
    async for _ in runner.run_workflow(graph, context):
        pass

    # Assertions
    print(f"Max observed concurrent: {tracking_handler.max_observed_concurrent}")
    assert tracking_handler.max_observed_concurrent <= limit, (
        f"Concurrency limit exceeded! Expected <={limit}, got {tracking_handler.max_observed_concurrent}"
    )

    # Also verify it processed everything
    # If the limit is 3, max observed should be 3
    # (unless system is super slow and serialized them by accident, but unlikely with sleep)
    assert tracking_handler.max_observed_concurrent == limit, (
        f"It didn't seem to reach saturation. Expected {limit}, got {tracking_handler.max_observed_concurrent}"
    )

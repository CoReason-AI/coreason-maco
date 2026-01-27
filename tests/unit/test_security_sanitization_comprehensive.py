# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, List

import networkx as nx
import pytest

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent

try:
    from coreason_identity.models import UserContext
except ImportError:

    class UserContext:  # type: ignore
        pass


@pytest.fixture  # type: ignore
def secure_context() -> ExecutionContext:
    # Create valid UserContext
    try:
        user_ctx = UserContext(sub="user_123", email="test@example.com", project_context={}, permissions=[])
    except Exception:
        user_ctx = None

    return ExecutionContext(
        user_id="test_user", trace_id="test_trace", secrets_map={}, tool_registry={}, user_context=user_ctx
    )


class CrashingTool:
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        raise ValueError("Sensitive Crash")


@pytest.mark.asyncio  # type: ignore
async def test_recursive_sanitization_in_error_payload(secure_context: ExecutionContext) -> None:
    """Test that user_context and downstream_token are removed from nested error snapshots."""

    # 1. Setup Inputs with sensitive data
    initial_inputs = {
        "user_context": secure_context.user_context,  # Should be removed
        "downstream_token": "very_secret",  # Should be removed
        "safe_data": "visible",
        "nested": {
            "level_1": {
                "user_context": "nested_secret",  # Should be removed
                "safe_nested": "nested_visible",
            },
            "list_data": [
                "safe_item",
                {"downstream_token": "list_secret"},  # Should be removed from dict in list
            ],
        },
    }

    # 2. Setup Graph that crashes
    runner = WorkflowRunner()
    runner.handlers["CRASH"] = CrashingTool()

    G = nx.DiGraph()
    G.add_node("CrashNode", type="CRASH")

    events: List[GraphEvent] = []

    # 3. Run and expect crash
    with pytest.raises(ExceptionGroup):
        async for event in runner.run_workflow(G, secure_context, initial_inputs=initial_inputs):
            events.append(event)

    # 4. Inspect Error Event
    error_event = next(e for e in events if e.event_type == "ERROR")
    snapshot = error_event.payload["input_snapshot"]

    # Assertions
    assert "user_context" not in snapshot
    assert "downstream_token" not in snapshot
    assert snapshot["safe_data"] == "visible"

    # Nested Dict
    assert "user_context" not in snapshot["nested"]["level_1"]
    assert snapshot["nested"]["level_1"]["safe_nested"] == "nested_visible"

    # Nested List
    assert snapshot["nested"]["list_data"][0] == "safe_item"
    assert isinstance(snapshot["nested"]["list_data"][1], dict)
    assert "downstream_token" not in snapshot["nested"]["list_data"][1]


@pytest.mark.asyncio  # type: ignore
async def test_sanitization_preserves_other_types(secure_context: ExecutionContext) -> None:
    """Test that sanitization doesn't break non-dict/list types."""
    initial_inputs = {
        "int_val": 123,
        "bool_val": True,
        "none_val": None,
        "obj_val": "some_string",  # Arbitrary object
    }

    runner = WorkflowRunner()
    runner.handlers["CRASH"] = CrashingTool()
    G = nx.DiGraph()
    G.add_node("CrashNode", type="CRASH")

    events: List[GraphEvent] = []

    with pytest.raises(ExceptionGroup):
        async for event in runner.run_workflow(G, secure_context, initial_inputs=initial_inputs):
            events.append(event)

    error_event = next(e for e in events if e.event_type == "ERROR")
    snapshot = error_event.payload["input_snapshot"]

    assert snapshot["int_val"] == 123
    assert snapshot["bool_val"] is True
    assert snapshot["none_val"] is None
    assert snapshot["obj_val"] == "some_string"

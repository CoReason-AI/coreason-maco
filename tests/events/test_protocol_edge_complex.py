# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict

import pytest
from pydantic import ValidationError

from coreason_maco.events.protocol import ExecutionContext, GraphEvent


class MockToolRegistry:
    def execute(self) -> str:
        return "executed"


def test_graph_event_edge_empty_strings() -> None:
    """Test that empty strings are accepted for ID fields if not strictly constrained."""
    event = GraphEvent(
        event_type="NODE_INIT",
        run_id="",
        node_id="",
        timestamp=100.0,
        payload={},
        visual_metadata={},
    )
    assert event.run_id == ""
    assert event.node_id == ""


def test_graph_event_edge_boundary_timestamps() -> None:
    """Test zero and negative timestamps."""
    event_zero = GraphEvent(
        event_type="NODE_INIT",
        run_id="r1",
        node_id="n1",
        timestamp=0.0,
        payload={},
        visual_metadata={},
    )
    assert event_zero.timestamp == 0.0

    event_neg = GraphEvent(
        event_type="NODE_INIT",
        run_id="r1",
        node_id="n1",
        timestamp=-1234567890.0,
        payload={},
        visual_metadata={},
    )
    assert event_neg.timestamp == -1234567890.0


def test_execution_context_edge_empty_map() -> None:
    """Test ExecutionContext with empty secrets map."""
    ctx = ExecutionContext(user_id="u1", trace_id="t1", secrets_map={}, tool_registry="something")
    assert ctx.secrets_map == {}


def test_execution_context_complex_object_registry() -> None:
    """Test that tool_registry can hold a complex object instance."""
    registry = MockToolRegistry()
    ctx = ExecutionContext(user_id="u1", trace_id="t1", secrets_map={}, tool_registry=registry)
    assert ctx.tool_registry is registry
    assert ctx.tool_registry.execute() == "executed"


def test_graph_event_complex_json_roundtrip() -> None:
    """Test serialization and deserialization round-trip."""
    original_event = GraphEvent(
        event_type="NODE_STREAM",
        run_id="run-complex-1",
        node_id="node-complex-1",
        timestamp=167888.88,
        trace_id="trace-x",
        sequence_id=999,
        payload={"key": "value", "numbers": [1, 2, 3]},
        visual_metadata={"color": "red"},
    )

    json_str = original_event.model_dump_json()
    restored_event = GraphEvent.model_validate_json(json_str)

    assert original_event == restored_event
    assert restored_event.payload["numbers"] == [1, 2, 3]


def test_graph_event_complex_nested_payload() -> None:
    """Test payload with deep nesting and mixed types."""
    complex_payload: Dict[str, Any] = {
        "level1": {
            "level2": {
                "level3": [
                    {"id": 1, "val": None},
                    {"id": 2, "val": True},
                    {"id": 3, "val": 3.14159},
                ]
            }
        },
        "tags": ["a", "b", "c"],
        "meta": None,
    }

    event = GraphEvent(
        event_type="NODE_DONE",
        run_id="r-nested",
        node_id="n-nested",
        timestamp=555.5,
        payload=complex_payload,
        visual_metadata={},
    )

    assert event.payload["level1"]["level2"]["level3"][0]["val"] is None
    assert event.payload["level1"]["level2"]["level3"][2]["val"] == 3.14159


def test_graph_event_edge_visual_metadata_types() -> None:
    """
    Test visual_metadata enforces Dict[str, str].
    Pydantic V2 appears to be strict regarding int -> str coercion in Dict values
    or the configuration implies it. We verify that it accepts strings and rejects ints
    if that is the observed behavior, ensuring strict adherence to the spec.
    """
    # Valid strings should pass
    event = GraphEvent(
        event_type="NODE_INIT",
        run_id="r1",
        node_id="n1",
        timestamp=1.0,
        payload={},
        visual_metadata={"progress": "0.5", "step": "1"},
    )
    assert event.visual_metadata["step"] == "1"

    # Invalid types (int) should fail validation
    with pytest.raises(ValidationError) as excinfo:
        GraphEvent(
            event_type="NODE_INIT",
            run_id="r1",
            node_id="n1",
            timestamp=1.0,
            payload={},
            visual_metadata={"step": 123},  # type: ignore[dict-item]
        )
    assert "Input should be a valid string" in str(excinfo.value)


def test_graph_event_edge_invalid_visual_metadata() -> None:
    """Test that a non-dict visual_metadata fails validation."""
    with pytest.raises(ValidationError):
        GraphEvent(
            event_type="NODE_INIT",
            run_id="r1",
            node_id="n1",
            timestamp=1.0,
            payload={},
            visual_metadata="not-a-dict",  # type: ignore[arg-type]
        )

# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import pytest
from pydantic import ValidationError

from coreason_maco.events.protocol import ExecutionContext, GraphEvent


def test_graph_event_valid() -> None:
    event = GraphEvent(
        event_type="NODE_START",
        run_id="run-123",
        node_id="node-A",
        timestamp=1234567890.0,
        payload={"input": "test"},
        visual_metadata={"color": "green", "animation": "pulse"},
    )
    assert event.event_type == "NODE_START"
    assert event.run_id == "run-123"
    assert event.payload == {"input": "test"}
    assert event.visual_metadata["color"] == "green"


def test_graph_event_invalid_type() -> None:
    with pytest.raises(ValidationError) as excinfo:
        GraphEvent(
            event_type="INVALID_TYPE",
            run_id="run-123",
            node_id="node-A",
            timestamp=1234567890.0,
            payload={},
            visual_metadata={},
        )
    # The error message depends on Pydantic version and Literal formatting
    assert "Input should be" in str(excinfo.value)


def test_graph_event_missing_fields() -> None:
    with pytest.raises(ValidationError) as excinfo:
        GraphEvent(
            event_type="NODE_START",
            run_id="run-123",
            # Missing node_id
            timestamp=1234567890.0,
            payload={},
            visual_metadata={},
        )
    assert "Field required" in str(excinfo.value)
    assert "node_id" in str(excinfo.value)


def test_graph_event_extra_fields() -> None:
    with pytest.raises(ValidationError):
        GraphEvent(
            event_type="NODE_START",
            run_id="run-123",
            node_id="node-A",
            timestamp=1234567890.0,
            payload={},
            visual_metadata={},
            extra_field="not_allowed",
        )


def test_graph_event_optional_fields() -> None:
    event = GraphEvent(
        event_type="NODE_DONE",
        run_id="run-123",
        node_id="node-B",
        timestamp=1234567890.0,
        payload={},
        visual_metadata={},
        trace_id="trace-xyz",
        sequence_id=1,
    )
    assert event.trace_id == "trace-xyz"
    assert event.sequence_id == 1


def test_execution_context_valid() -> None:
    ctx = ExecutionContext(
        user_id="user-1",
        trace_id="trace-1",
        secrets_map={"API_KEY": "secret"},
        tool_registry={"some": "tool"},
    )
    assert ctx.user_id == "user-1"
    assert ctx.secrets_map["API_KEY"] == "secret"


def test_execution_context_invalid() -> None:
    with pytest.raises(ValidationError):
        ExecutionContext(
            user_id="user-1",
            # Missing trace_id
            secrets_map={},
            tool_registry={},  # type: ignore[call-arg, unused-ignore]
        )

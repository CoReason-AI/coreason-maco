# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import time

import pytest
from pydantic import ValidationError

from coreason_maco.events.protocol import (
    ExecutionContext,
    GraphEvent,
    NodeCompletedPayload,
    NodeInitPayload,
    NodeStartedPayload,
)


def test_graph_event_creation_valid() -> None:
    """Test creating a valid GraphEvent."""
    event = GraphEvent(
        event_type="NODE_START",
        run_id="run-123",
        trace_id="trace-456",
        node_id="node-A",
        timestamp=time.time(),
        payload={"message": "starting"},
        visual_metadata={"color": "green", "animation": "pulse"},
    )
    assert event.run_id == "run-123"
    assert event.trace_id == "trace-456"
    assert event.event_type == "NODE_START"
    assert event.payload["message"] == "starting"
    assert event.visual_metadata["color"] == "green"


def test_graph_event_missing_fields() -> None:
    """Test that missing required fields raise ValidationError."""
    with pytest.raises(ValidationError) as excinfo:
        GraphEvent(
            event_type="NODE_START",
            # run_id missing
            # node_id missing
            trace_id="trace-456",
            timestamp=time.time(),
            payload={},
            visual_metadata={},
        )
    # Both run_id and node_id are required
    assert "run_id" in str(excinfo.value) or "node_id" in str(excinfo.value)


def test_graph_event_invalid_type() -> None:
    """Test that invalid types raise ValidationError."""
    with pytest.raises(ValidationError):
        GraphEvent(
            event_type="NODE_START",
            run_id="run-123",
            node_id="node-A",
            trace_id="trace-456",
            timestamp="not-a-float",
            payload={},
            visual_metadata={},
        )


def test_execution_context_creation() -> None:
    """Test creating a valid ExecutionContext."""
    context = ExecutionContext(
        user_id="user-1",
        trace_id="trace-1",
        secrets_map={"API_KEY": "secret"},
        tool_registry={"some_tool": "callable"},
    )
    assert context.user_id == "user-1"
    assert context.secrets_map["API_KEY"] == "secret"


def test_payload_helpers() -> None:
    """Test the payload helper models."""
    # NodeStartedPayload requires node_id and timestamp now
    payload = NodeStartedPayload(node_id="node-1", timestamp=123.45, input_tokens=100)
    assert payload.input_tokens == 100
    assert payload.node_id == "node-1"

    # NodeCompletedPayload requires node_id, output_summary
    payload_done = NodeCompletedPayload(node_id="node-1", output_summary="Done", cost=0.05)
    assert payload_done.cost == 0.05

    # NodeInitPayload
    payload_init = NodeInitPayload(node_id="node-1", type="LLM")
    assert payload_init.type == "LLM"
    assert payload_init.visual_cue == "IDLE"


def test_graph_event_sequence_id() -> None:
    """Test sequence_id optionality."""
    event = GraphEvent(
        event_type="EDGE_ACTIVE",
        run_id="run-1",
        trace_id="trace-1",
        node_id="node-X",
        timestamp=1234567890.0,
        payload={},
        visual_metadata={},
        sequence_id=10,
    )
    assert event.sequence_id == 10

    event_no_seq = GraphEvent(
        event_type="EDGE_ACTIVE",
        run_id="run-1",
        trace_id="trace-1",
        node_id="node-X",
        timestamp=1234567890.0,
        payload={},
        visual_metadata={},
    )
    assert event_no_seq.sequence_id is None

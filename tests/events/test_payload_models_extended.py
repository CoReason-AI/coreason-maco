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

from coreason_maco.events.protocol import (
    ArtifactGenerated,
    EdgeTraversed,
    ExecutionContext,
    GraphEvent,
    NodeCompleted,
    NodeStarted,
)

# --- Edge Cases ---


def test_empty_strings_allowed() -> None:
    """Verify that empty strings are accepted for string fields."""
    # NodeStarted
    ns = NodeStarted(node_id="", timestamp=1.0)
    assert ns.node_id == ""

    # NodeCompleted
    nc = NodeCompleted(node_id="A", output_summary="")
    assert nc.output_summary == ""

    # EdgeTraversed
    et = EdgeTraversed(source="", target="")
    assert et.source == ""
    assert et.target == ""

    # ArtifactGenerated
    ag = ArtifactGenerated(node_id="A", url="")
    assert ag.url == ""


def test_whitespace_strings_allowed() -> None:
    """Verify that whitespace strings are accepted and preserved."""
    ns = NodeStarted(node_id="   ", timestamp=1.0)
    assert ns.node_id == "   "

    nc = NodeCompleted(node_id="A", output_summary="  \n  ")
    assert nc.output_summary == "  \n  "


def test_type_coercion_strictness() -> None:
    """Verify that models are strict about types (no int-to-str coercion)."""
    # Int to Str - Should Fail
    with pytest.raises(ValidationError) as exc:
        NodeStarted(node_id=123, timestamp=1.0)  # type: ignore[arg-type]
    assert "Input should be a valid string" in str(exc.value)

    # Float to Str - Should Fail
    with pytest.raises(ValidationError) as exc:
        ArtifactGenerated(node_id="A", url=456.78)  # type: ignore[arg-type]
    assert "Input should be a valid string" in str(exc.value)

    # Int to Float - Usually allowed in Pydantic V2 Lax mode, but let's check.
    # If this fails, then strict mode is ON. If it passes, then Int->Str failure above is specific to Str.
    # The previous test run only showed failures for node_id (str).
    # Let's keep the timestamp test positive IF it works, or wrap in try/except to discover behavior?
    # Better: explicit test.
    # ns2 = NodeStarted(node_id="A", timestamp=100)
    # The error log didn't complain about timestamp=100 in the previous run?
    # Wait, the previous run failed at `ns = NodeStarted(node_id=123...`. It didn't reach `ns2`.

    # Let's test timestamp coercion.
    ns2 = NodeStarted(node_id="A", timestamp=100)
    assert ns2.timestamp == 100.0


def test_invalid_literals_strict() -> None:
    """Verify that invalid literals raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        NodeStarted(node_id="A", timestamp=1.0, status="INVALID")  # type: ignore[arg-type]
    assert "Input should be 'RUNNING'" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        NodeCompleted(node_id="A", output_summary="Done", status="PARTIAL")  # type: ignore[arg-type]
    assert "Input should be 'SUCCESS'" in str(exc.value)


# --- Complex / Redundant Tests ---


def test_integration_with_graph_event() -> None:
    """Verify that payload models can be used in GraphEvent payloads."""
    node_started = NodeStarted(node_id="step-1", timestamp=1234567890.0)

    # Create GraphEvent using the dump of NodeStarted
    event = GraphEvent(
        event_type="NODE_START",
        run_id="run-1",
        node_id=node_started.node_id,
        timestamp=node_started.timestamp,
        payload=node_started.model_dump(),
        visual_metadata={"color": "blue"},
    )

    assert event.payload["node_id"] == "step-1"
    assert event.payload["status"] == "RUNNING"


def test_json_round_trip() -> None:
    """Verify JSON serialization and deserialization."""
    # Create original instance
    original = EdgeTraversed(source="start", target="end", animation_speed="SLOW")

    # Serialize to JSON
    json_str = original.model_dump_json()

    # Deserialize back to object
    restored = EdgeTraversed.model_validate_json(json_str)

    assert original.source == restored.source
    assert original.target == restored.target
    assert original.animation_speed == restored.animation_speed
    assert original == restored


def test_equality() -> None:
    """Verify equality comparison works for identical models."""
    a1 = ArtifactGenerated(node_id="A", url="http://x.com", artifact_type="PDF")
    a2 = ArtifactGenerated(node_id="A", url="http://x.com", artifact_type="PDF")
    a3 = ArtifactGenerated(node_id="A", url="http://y.com", artifact_type="PDF")

    assert a1 == a2
    assert a1 != a3


def test_execution_context_strictness() -> None:
    """Verify ExecutionContext behaves strictly with types."""
    # Secrets map requires string values
    with pytest.raises(ValidationError) as exc:
        ExecutionContext(
            user_id="u1",
            trace_id="t1",
            secrets_map={"key": 123},  # type: ignore[dict-item]
            tool_registry={},
        )
    assert "Input should be a valid string" in str(exc.value)

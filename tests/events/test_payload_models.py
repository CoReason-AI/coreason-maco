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
    NodeCompleted,
    NodeStarted,
)


def test_node_started_defaults() -> None:
    event = NodeStarted(node_id="A", timestamp=100.0)
    assert event.node_id == "A"
    assert event.timestamp == 100.0
    assert event.status == "RUNNING"
    assert event.visual_cue == "PULSE"


def test_node_started_explicit() -> None:
    event = NodeStarted(node_id="B", timestamp=200.0, status="RUNNING", visual_cue="RED")
    assert event.node_id == "B"
    assert event.visual_cue == "RED"


def test_node_started_validation() -> None:
    with pytest.raises(ValidationError) as exc:
        NodeStarted(node_id="A")  # type: ignore[call-arg]
    assert "timestamp" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        NodeStarted(node_id="A", timestamp=100.0, extra="fail")  # type: ignore
    assert "Extra inputs are not permitted" in str(exc.value)


def test_node_completed_defaults() -> None:
    event = NodeCompleted(node_id="A", output_summary="Done")
    assert event.node_id == "A"
    assert event.output_summary == "Done"
    assert event.status == "SUCCESS"
    assert event.visual_cue == "GREEN_GLOW"


def test_node_completed_explicit() -> None:
    event = NodeCompleted(
        node_id="B",
        output_summary="Result",
        status="SUCCESS",
        visual_cue="BLUE_GLOW",
    )
    assert event.visual_cue == "BLUE_GLOW"


def test_node_completed_validation() -> None:
    with pytest.raises(ValidationError):
        NodeCompleted(node_id="A")  # type: ignore[call-arg]


def test_edge_traversed_defaults() -> None:
    event = EdgeTraversed(source="A", target="B")
    assert event.source == "A"
    assert event.target == "B"
    assert event.animation_speed == "FAST"


def test_edge_traversed_explicit() -> None:
    event = EdgeTraversed(source="A", target="B", animation_speed="SLOW")
    assert event.animation_speed == "SLOW"


def test_edge_traversed_validation() -> None:
    with pytest.raises(ValidationError):
        EdgeTraversed(source="A")  # type: ignore[call-arg]


def test_artifact_generated_defaults() -> None:
    event = ArtifactGenerated(node_id="A", url="http://example.com/doc.pdf")
    assert event.node_id == "A"
    assert event.url == "http://example.com/doc.pdf"
    assert event.artifact_type == "PDF"


def test_artifact_generated_explicit() -> None:
    event = ArtifactGenerated(node_id="B", url="http://example.com/image.png", artifact_type="IMAGE")
    assert event.artifact_type == "IMAGE"


def test_artifact_generated_validation() -> None:
    with pytest.raises(ValidationError):
        ArtifactGenerated(node_id="A")  # type: ignore[call-arg]

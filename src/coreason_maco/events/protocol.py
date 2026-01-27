# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from coreason_maco.utils.context import ExecutionContext as ExecutionContext
from coreason_maco.utils.context import FeedbackManager as FeedbackManager


class GraphEvent(BaseModel):
    """The atomic unit of communication between the Engine (MACO) and the UI (Flutter).

    Attributes:
        event_type: The type of the event.
        run_id: The unique ID of the workflow run.
        trace_id: The trace ID (defaults to "unknown").
        node_id: The ID of the node associated with the event.
        timestamp: The timestamp of the event.
        sequence_id: Optional sequence ID.
        payload: The event payload containing logic output.
        visual_metadata: Metadata for UI visualization.
    """

    model_config = ConfigDict(extra="forbid")

    event_type: Literal[
        "NODE_INIT",
        "NODE_START",
        "NODE_STREAM",
        "NODE_DONE",
        "NODE_END",  # Added for compatibility with existing tests
        "NODE_SKIPPED",
        "EDGE_ACTIVE",
        "COUNCIL_VOTE",
        "ERROR",
        "NODE_RESTORED",
        "ARTIFACT_GENERATED",
    ]
    run_id: str
    trace_id: str = Field(
        default_factory=lambda: "unknown"
    )  # Default for compatibility if missing in some legacy calls, but mostly required
    node_id: str  # Required per BRD and existing tests
    timestamp: float
    sequence_id: Optional[int] = None  # Optional for internal use, but good for TRD compliance

    # The payload contains the actual reasoning/data
    payload: Dict[str, Any] = Field(..., description="The logic output")

    # Visual Metadata drives the Flutter animation engine
    visual_metadata: Dict[str, str] = Field(
        ..., description="Hints for UI: color='#00FF00', animation='pulse', progress='0.5'"
    )


# Base Models
class BaseNodePayload(BaseModel):
    """Base model for node-related events."""

    model_config = ConfigDict(extra="forbid")
    node_id: str


# Payload Models expected by existing code
class NodeInit(BaseNodePayload):
    """Payload for NODE_INIT event."""

    type: str = "DEFAULT"
    visual_cue: str = "IDLE"


class NodeStarted(BaseNodePayload):
    """Payload for NODE_START event."""

    timestamp: float
    status: Literal["RUNNING"] = "RUNNING"
    visual_cue: str = "PULSE"
    input_tokens: Optional[int] = None


class NodeCompleted(BaseNodePayload):
    """Payload for NODE_DONE event."""

    output_summary: str
    status: Literal["SUCCESS"] = "SUCCESS"
    visual_cue: str = "GREEN_GLOW"
    cost: Optional[float] = None


class NodeRestored(BaseNodePayload):
    """Payload for NODE_RESTORED event."""

    output_summary: str
    status: Literal["RESTORED"] = "RESTORED"
    visual_cue: str = "INSTANT_GREEN"


class NodeSkipped(BaseNodePayload):
    """Payload for NODE_SKIPPED event."""

    status: Literal["SKIPPED"] = "SKIPPED"
    visual_cue: str = "GREY_OUT"


class NodeStream(BaseNodePayload):
    """Payload for NODE_STREAM event."""

    chunk: str
    visual_cue: str = "TEXT_BUBBLE"


class ArtifactGenerated(BaseNodePayload):
    """Payload for ARTIFACT_GENERATED event."""

    artifact_type: str = "PDF"
    url: str


class EdgeTraversed(BaseModel):
    """Payload for EDGE_ACTIVE event."""

    model_config = ConfigDict(extra="forbid")
    source: str
    target: str
    animation_speed: str = "FAST"


class CouncilVote(BaseNodePayload):
    """Payload for COUNCIL_VOTE event."""

    votes: Dict[str, str]


class WorkflowError(BaseNodePayload):
    """Payload for ERROR event."""

    error_message: str
    stack_trace: str
    input_snapshot: Dict[str, Any]
    status: Literal["ERROR"] = "ERROR"
    visual_cue: str = "RED_FLASH"


# Aliases for compatibility
NodeInitPayload = NodeInit
NodeStartedPayload = NodeStarted
NodeCompletedPayload = NodeCompleted
NodeSkippedPayload = NodeSkipped
NodeStreamPayload = NodeStream
EdgeTraversedPayload = EdgeTraversed
ArtifactGeneratedPayload = ArtifactGenerated
CouncilVotePayload = CouncilVote
WorkflowErrorPayload = WorkflowError

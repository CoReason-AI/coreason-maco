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

# Combined Event Types from BRD and TRD
EventType = Literal[
    "NODE_INIT",
    "NODE_START",
    "NODE_STREAM",
    "NODE_END",  # BRD
    "NODE_DONE",  # TRD
    "EDGE_TRAVERSAL",  # BRD
    "EDGE_ACTIVE",  # TRD
    "COUNCIL_VOTE",
    "ERROR",
]


class GraphEvent(BaseModel):
    """
    The atomic unit of communication between the Engine (MACO)
    and the UI (Flutter).
    """

    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    run_id: str
    node_id: str
    timestamp: float

    # Optional fields from TRD
    trace_id: Optional[str] = None
    sequence_id: Optional[int] = None

    # The payload contains the actual reasoning/data
    payload: Dict[str, Any] = Field(..., description="The logic output")

    # Visual Metadata drives the Flutter animation engine
    visual_metadata: Dict[str, str] = Field(
        ..., description="Hints for UI: color='#00FF00', animation='pulse', progress='0.5'"
    )


class ExecutionContext(BaseModel):
    """
    The Context Injection Object.
    Prevents MACO from needing direct access to Auth or DB drivers.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    trace_id: str
    secrets_map: Dict[str, str]  # Decrypted secrets passed from Vault
    tool_registry: Any  # Interface for coreason-mcp (The Tools)


class NodeStarted(BaseModel):
    """
    Event payload for when a node starts execution.
    """

    model_config = ConfigDict(extra="forbid")

    node_id: str
    timestamp: float
    status: Literal["RUNNING"] = "RUNNING"
    visual_cue: str = "PULSE"


class NodeCompleted(BaseModel):
    """
    Event payload for when a node completes execution.
    """

    model_config = ConfigDict(extra="forbid")

    node_id: str
    output_summary: str
    status: Literal["SUCCESS"] = "SUCCESS"
    visual_cue: str = "GREEN_GLOW"


class EdgeTraversed(BaseModel):
    """
    Event payload for when an edge is traversed.
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    animation_speed: str = "FAST"


class ArtifactGenerated(BaseModel):
    """
    Event payload for when an artifact is generated.
    """

    model_config = ConfigDict(extra="forbid")

    node_id: str
    artifact_type: str = "PDF"
    url: str

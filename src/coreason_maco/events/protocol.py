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
    agent_executor: Any  # Interface for coreason-cortex (The Agents)


class GraphEvent(BaseModel):
    """
    The atomic unit of communication between the Engine (MACO)
    and the UI (Flutter).
    """

    model_config = ConfigDict(extra="forbid")

    event_type: Literal[
        "NODE_INIT",
        "NODE_START",
        "NODE_STREAM",
        "NODE_DONE",
        "NODE_END",  # Added for compatibility with existing tests
        "EDGE_ACTIVE",
        "EDGE_TRAVERSAL",
        "COUNCIL_VOTE",
        "ERROR",
        "NODE_RESTORED",
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


# Payload Models expected by existing code
class NodeStarted(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    timestamp: float
    status: Literal["RUNNING"] = "RUNNING"
    visual_cue: str = "PULSE"
    input_tokens: Optional[int] = None


class NodeCompleted(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    output_summary: str
    status: Literal["SUCCESS"] = "SUCCESS"
    visual_cue: str = "GREEN_GLOW"
    cost: Optional[float] = None


class NodeRestored(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    output_summary: str
    status: Literal["RESTORED"] = "RESTORED"
    visual_cue: str = "INSTANT_GREEN"


class ArtifactGenerated(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    artifact_type: str = "PDF"
    url: str


class EdgeTraversed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str
    animation_speed: str = "FAST"


class CouncilVote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    votes: Dict[str, str]


# Aliases for compatibility
NodeStartedPayload = NodeStarted
NodeCompletedPayload = NodeCompleted
EdgeTraversedPayload = EdgeTraversed
ArtifactGeneratedPayload = ArtifactGenerated
CouncilVotePayload = CouncilVote

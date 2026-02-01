from coreason_manifest.definitions.events import (
    GraphEvent,
    NodeInit,
    NodeStarted,
    NodeCompleted,
    NodeSkipped,
    NodeStream,
    NodeRestored,
    EdgeTraversed,
    ArtifactGenerated,
    CouncilVote,
    WorkflowError
)

from coreason_maco.utils.context import ExecutionContext, FeedbackManager

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

__all__ = [
    "GraphEvent",
    "NodeInit",
    "NodeStarted",
    "NodeCompleted",
    "NodeSkipped",
    "NodeStream",
    "NodeRestored",
    "EdgeTraversed",
    "ArtifactGenerated",
    "CouncilVote",
    "WorkflowError",
    "NodeInitPayload",
    "NodeStartedPayload",
    "NodeCompletedPayload",
    "NodeSkippedPayload",
    "NodeStreamPayload",
    "EdgeTraversedPayload",
    "ArtifactGeneratedPayload",
    "CouncilVotePayload",
    "WorkflowErrorPayload",
    "ExecutionContext",
    "FeedbackManager",
]

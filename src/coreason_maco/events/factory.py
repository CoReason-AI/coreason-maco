import time
from typing import Any, Dict

from coreason_maco.events.protocol import (
    CouncilVotePayload,
    EdgeTraversed,
    GraphEvent,
    NodeCompleted,
    NodeRestored,
    NodeStarted,
    WorkflowErrorPayload,
)


class EventFactory:
    """
    Factory for creating standardized GraphEvents.
    Reduces boilerplate in the runner.
    """

    @staticmethod
    def create_node_start(run_id: str, node_id: str) -> GraphEvent:
        payload = NodeStarted(
            node_id=node_id,
            timestamp=time.time(),
            status="RUNNING",
            visual_cue="PULSE",
        )
        return GraphEvent(
            event_type="NODE_START",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=payload.model_dump(),
            visual_metadata={"state": "PULSING", "anim": "BREATHE"},
        )

    @staticmethod
    def create_node_done(run_id: str, node_id: str, output: Any) -> GraphEvent:
        payload = NodeCompleted(
            node_id=node_id,
            output_summary=str(output) if output is not None else "Completed",
            status="SUCCESS",
            visual_cue="GREEN_GLOW",
        )
        return GraphEvent(
            event_type="NODE_DONE",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=payload.model_dump(),
            visual_metadata={"state": "SOLID", "color": "#GREEN"},
        )

    @staticmethod
    def create_node_restored(run_id: str, node_id: str, output: Any) -> GraphEvent:
        payload = NodeRestored(
            node_id=node_id,
            output_summary=str(output),
            status="RESTORED",
            visual_cue="INSTANT_GREEN",
        )
        return GraphEvent(
            event_type="NODE_RESTORED",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=payload.model_dump(),
            visual_metadata={"state": "RESTORED", "color": "#00FF00"},
        )

    @staticmethod
    def create_edge_active(run_id: str, source: str, target: str) -> GraphEvent:
        payload = EdgeTraversed(
            source=source,
            target=target,
            animation_speed="FAST",
        )
        return GraphEvent(
            event_type="EDGE_ACTIVE",
            run_id=run_id,
            node_id=source,  # Edge events are associated with the source node in this schema
            timestamp=time.time(),
            payload=payload.model_dump(),
            visual_metadata={"flow_speed": "FAST", "particle": "DOT"},
        )

    @staticmethod
    def create_error(run_id: str, node_id: str, error: str, stack: str, input_snapshot: Dict[str, Any]) -> GraphEvent:
        payload = WorkflowErrorPayload(
            node_id=node_id,
            error_message=error,
            stack_trace=stack,
            input_snapshot=input_snapshot,
        )
        return GraphEvent(
            event_type="ERROR",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=payload.model_dump(),
            visual_metadata={"state": "ERROR", "color": "#RED"},
        )

    @staticmethod
    def create_council_vote(run_id: str, node_id: str, votes: Dict[str, str]) -> GraphEvent:
        payload = CouncilVotePayload(
            node_id=node_id,
            votes=votes,
        )
        return GraphEvent(
            event_type="COUNCIL_VOTE",
            run_id=run_id,
            node_id=node_id,
            timestamp=time.time(),
            payload=payload.model_dump(),
            visual_metadata={"widget": "VOTING_BOOTH"},
        )

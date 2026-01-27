# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict, List

import networkx as nx
import pytest
from pydantic import BaseModel

from coreason_maco.engine.runner import WorkflowRunner
from coreason_maco.events.protocol import ExecutionContext, GraphEvent


class MockArtifact(BaseModel):
    artifact_type: str
    url: str
    other_field: str = "ignored"


class MockToolExecutorArtifact:
    """Mock implementation of ToolExecutor that returns an artifact."""

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "pdf_generator":
            return MockArtifact(artifact_type="PDF", url="https://example.com/report.pdf")
        return "regular_output"


@pytest.mark.asyncio  # type: ignore
async def test_tool_generates_artifact_event() -> None:
    """Test that a tool returning an artifact object emits ARTIFACT_GENERATED event."""
    # Setup
    tool_executor = MockToolExecutorArtifact()
    context = ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=tool_executor,
    )

    # Create Graph
    graph = nx.DiGraph()
    graph.add_node("pdf_node", type="TOOL", config={"tool_name": "pdf_generator"})

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    # Execute
    async for event in runner.run_workflow(graph, context):
        events.append(event)

    # Verify ARTIFACT_GENERATED event
    artifact_events = [e for e in events if e.event_type == "ARTIFACT_GENERATED"]
    assert len(artifact_events) == 1

    event = artifact_events[0]
    assert event.node_id == "pdf_node"
    assert event.payload["artifact_type"] == "PDF"
    assert event.payload["url"] == "https://example.com/report.pdf"
    assert event.visual_metadata["state"] == "ARTIFACT_GENERATED"
    assert event.visual_metadata["icon"] == "FILE"

    # Verify Node Output is still the object
    node_done_events = [e for e in events if e.event_type == "NODE_DONE"]
    assert len(node_done_events) == 1
    # output_summary might be str(MockArtifact)
    assert "PDF" in node_done_events[0].payload["output_summary"]


class MockToolExecutorDictArtifact:
    """Mock implementation returning a dict."""

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        return {"artifact_type": "CSV", "url": "https://example.com/data.csv", "other": "data"}


@pytest.mark.asyncio  # type: ignore
async def test_tool_generates_artifact_event_dict() -> None:
    """Test that a tool returning a dict with artifact fields emits ARTIFACT_GENERATED event."""
    # Setup
    tool_executor = MockToolExecutorDictArtifact()
    context = ExecutionContext(
        user_id="test_user",
        trace_id="test_trace",
        secrets_map={},
        tool_registry=tool_executor,
    )

    # Create Graph
    graph = nx.DiGraph()
    graph.add_node("csv_node", type="TOOL", config={"tool_name": "csv_generator"})

    runner = WorkflowRunner()
    events: List[GraphEvent] = []

    # Execute
    async for event in runner.run_workflow(graph, context):
        events.append(event)

    # Verify ARTIFACT_GENERATED event
    artifact_events = [e for e in events if e.event_type == "ARTIFACT_GENERATED"]
    assert len(artifact_events) == 1

    event = artifact_events[0]
    assert event.node_id == "csv_node"
    assert event.payload["artifact_type"] == "CSV"
    assert event.payload["url"] == "https://example.com/data.csv"

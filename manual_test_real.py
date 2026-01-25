# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import asyncio
from typing import Any, Dict
from unittest.mock import MagicMock

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import AgentResponse


# Mock Services
class MockAgentExecutor:
    async def invoke(self, prompt: str, model_config: Dict[str, Any]) -> AgentResponse:
        print(f"\n[MockAgent] Invoked with prompt: '{prompt}'")
        response = MagicMock()
        # Return a fixed fact for the LLM node
        response.content = "Space is completely silent."
        response.metadata = {}
        return response


class MockToolExecutor:
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        print(f"\n[MockTool] Executing '{tool_name}' with args: {args}")
        if tool_name == "write_file":
            return f"Written to {args.get('path')}: {args.get('content')}"
        elif tool_name == "read_file":
            return f"Read from {args.get('path')}"
        return "Tool Executed"


class MockServiceRegistry:
    @property
    def tool_registry(self) -> MockToolExecutor:
        return MockToolExecutor()

    @property
    def agent_executor(self) -> MockAgentExecutor:
        return MockAgentExecutor()

    @property
    def auth_manager(self) -> Any:
        return MagicMock()

    @property
    def audit_logger(self) -> Any:
        return MagicMock()


async def main() -> None:
    services = MockServiceRegistry()
    controller = WorkflowController(services=services)

    manifest = {
        "name": "Real World Research Workflow",
        "nodes": [
            {
                "id": "1_Generate_Idea",
                "type": "LLM",
                "config": {
                    "model": "gpt-4o",
                    # ADD PROMPT HERE so the new runner knows what to ask
                    "prompt": "Generate a short, 1-sentence interesting fact about space.",
                },
            },
            {
                "id": "2_Save_To_Disk",
                "type": "TOOL",
                "config": {
                    "tool_name": "write_file",
                    "args": {
                        "path": "test_output.txt",
                        # THIS IS THE FIX: Dynamic Injection
                        "content": "{{ 1_Generate_Idea }}",
                    },
                },
            },
            {
                "id": "3_Read_From_Disk",
                "type": "TOOL",
                "config": {"tool_name": "read_file", "args": {"path": "test_output.txt"}},
            },
        ],
        "edges": [
            {"source": "1_Generate_Idea", "target": "2_Save_To_Disk"},
            {"source": "2_Save_To_Disk", "target": "3_Read_From_Disk"},
        ],
    }

    inputs = {"user_id": "test_user", "trace_id": "test_trace_123"}

    print("Starting Workflow Execution...")
    async for event in controller.execute_recipe(manifest, inputs):
        if event.event_type == "NODE_DONE":
            print(f"[Event] Node {event.node_id} Done. Output: {event.payload['output_summary']}")
        elif event.event_type == "ERROR":
            print(f"[Event] ERROR in Node {event.node_id}: {event.payload['error_message']}")


if __name__ == "__main__":
    asyncio.run(main())

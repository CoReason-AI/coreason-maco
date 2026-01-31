import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from coreason_identity.models import UserContext
from coreason_manifest.recipes import CouncilConfig

from coreason_maco.core.manifest import CouncilConfig as ManifestCouncilConfig
from coreason_maco.engine.handlers import LLMNodeHandler
from coreason_maco.utils.context import ExecutionContext

@pytest.mark.asyncio
async def test_llm_handler_delegates_to_council_with_dict(mock_user_context: UserContext):
    # Setup
    agent_executor = MagicMock()
    # Mock invoke to return a Council result format or just something valid
    # Since CouncilNodeHandler delegates to CouncilStrategy which calls invoke...
    # We can just check if CouncilNodeHandler.execute is called, but we can't easily mock inner class.
    # Instead we verify the outcome.

    # We mock AgentExecutor.invoke to ensure it's called by CouncilStrategy
    response = MagicMock()
    response.content = "Consensus"
    agent_executor.invoke = AsyncMock(return_value=response)

    handler = LLMNodeHandler(agent_executor)

    config = {
        "council_config": {
            "strategy": "consensus",
            "voters": ["A", "B"]
        },
        "prompt": "Test"
    }

    context = ExecutionContext(
        user_id="u",
        trace_id="t",
        secrets_map={},
        tool_registry=MagicMock(),
        user_context=mock_user_context
    )

    queue = asyncio.Queue()

    # Execute
    result = await handler.execute("node1", "run1", config, context, queue, {})

    # Verify
    assert result == "Consensus"
    # Verify AgentExecutor called for voters and synthesizer
    assert agent_executor.invoke.call_count >= 1

@pytest.mark.asyncio
async def test_llm_handler_delegates_to_council_with_pydantic_object(mock_user_context: UserContext):
    # Setup
    agent_executor = MagicMock()
    response = MagicMock()
    response.content = "Consensus"
    agent_executor.invoke = AsyncMock(return_value=response)

    handler = LLMNodeHandler(agent_executor)

    # Pass CouncilConfig object directly
    council_obj = ManifestCouncilConfig(strategy="consensus", voters=["A", "B"])

    config = {
        "council_config": council_obj,
        "prompt": "Test"
    }

    context = ExecutionContext(
        user_id="u",
        trace_id="t",
        secrets_map={},
        tool_registry=MagicMock(),
        user_context=mock_user_context
    )

    queue = asyncio.Queue()

    # Execute
    result = await handler.execute("node1", "run1", config, context, queue, {})

    # Verify
    assert result == "Consensus"

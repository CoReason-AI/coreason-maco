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
from typing import Any, AsyncGenerator, Dict

import pytest
from coreason_identity.models import UserContext

from coreason_maco.core.interfaces import AgentResponse
from coreason_maco.strategies.council import CouncilConfig, CouncilStrategy


class MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.metadata: Dict[str, Any] = {}


class MockAgentExecutor:
    def __init__(
        self, responses: Dict[str, str] | None = None, delay: float = 0.0, failure_on: str | None = None
    ) -> None:
        self.responses = responses or {}
        self.delay = delay
        self.failure_on = failure_on

    async def invoke(self, prompt: str, model_config: Dict[str, Any]) -> AgentResponse:
        await asyncio.sleep(self.delay)

        model_name = model_config.get("model", "unknown")

        if self.failure_on and self.failure_on == model_name:
            raise ValueError(f"Simulated failure for {model_name}")

        # If it's a synthesis prompt (long), we can detect it
        if "Original Query:" in prompt:
            # Check if synthesis model is set to fail
            # The strategy passes config.synthesizer to invoke
            # In our updated strategy, it uses default {"role": "synthesizer", "model": "judge"}
            if self.failure_on == "judge":
                raise ValueError("Simulated failure for judge")
            return MockResponse("Consensus Reached")

        return MockResponse(self.responses.get(model_name, "Default Response"))

    def stream(self, prompt: str, model_config: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async def _gen() -> AsyncGenerator[str, None]:
            yield "Mock Stream"

        return _gen()


@pytest.mark.asyncio  # type: ignore
async def test_council_success(mock_user_context: UserContext) -> None:
    config = CouncilConfig(voters=["gpt-4", "claude"], strategy="consensus")

    mock_exec = MockAgentExecutor(responses={"gpt-4": "Blue", "claude": "Red"})
    strategy = CouncilStrategy(mock_exec)

    result = await strategy.execute("Color?", config, context=mock_user_context)

    assert result.consensus == "Consensus Reached"
    assert "Blue" in result.individual_votes.values()
    assert "Red" in result.individual_votes.values()


@pytest.mark.asyncio  # type: ignore
async def test_council_partial_failure(mock_user_context: UserContext) -> None:
    config = CouncilConfig(voters=["gpt-4", "claude"], strategy="consensus")

    mock_exec = MockAgentExecutor(responses={"gpt-4": "Blue", "claude": "Red"}, failure_on="gpt-4")
    strategy = CouncilStrategy(mock_exec)

    result = await strategy.execute("Color?", config, context=mock_user_context)

    # GPT-4 failed, so only Claude's vote should be there
    assert "Red" in result.individual_votes.values()
    assert "Blue" not in result.individual_votes.values()
    assert len(result.individual_votes) == 1


@pytest.mark.asyncio  # type: ignore
async def test_council_all_fail(mock_user_context: UserContext) -> None:
    config = CouncilConfig(voters=["gpt-4"], strategy="consensus")

    mock_exec = MockAgentExecutor(failure_on="gpt-4")
    strategy = CouncilStrategy(mock_exec)

    with pytest.raises(RuntimeError, match="All council agents failed"):
        await strategy.execute("Color?", config, context=mock_user_context)


@pytest.mark.asyncio  # type: ignore
async def test_council_timeout(mock_user_context: UserContext) -> None:
    # Set strategy timeout low
    config = CouncilConfig(voters=["slow-poke"], strategy="consensus")

    mock_exec = MockAgentExecutor(responses={"slow-poke": "Slow"}, delay=0.1)
    strategy = CouncilStrategy(mock_exec, timeout=0.01)

    with pytest.raises(RuntimeError, match="All council agents failed"):
        await strategy.execute("Fast?", config, context=mock_user_context)


@pytest.mark.asyncio  # type: ignore
async def test_council_synthesizer_fail(mock_user_context: UserContext) -> None:
    config = CouncilConfig(voters=["gpt-4"], strategy="consensus")

    mock_exec = MockAgentExecutor(responses={"gpt-4": "Blue"}, failure_on="judge")
    strategy = CouncilStrategy(mock_exec)

    with pytest.raises(RuntimeError, match="Synthesizer agent failed"):
        await strategy.execute("Color?", config, context=mock_user_context)


@pytest.mark.asyncio  # type: ignore
async def test_council_missing_context() -> None:
    config = CouncilConfig(voters=["gpt-4"], strategy="consensus")
    mock_exec = MockAgentExecutor()
    strategy = CouncilStrategy(mock_exec)

    with pytest.raises(ValueError, match="UserContext is required"):
        await strategy.execute("Color?", config, context=None)
